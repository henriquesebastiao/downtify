"""Download a track from YouTube and tag it with the chosen metadata."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Callable, Optional

import requests
import yt_dlp
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TPE2
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from .providers import find_match

logger = logging.getLogger(__name__)

_INVALID_FS_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

ProgressCallback = Callable[[float, str], None]


def _sanitize(text: str) -> str:
    safe = _INVALID_FS_CHARS.sub('', text or '').strip().strip('.')
    return safe or 'unknown'


class Downloader:
    """Wraps ``yt-dlp`` plus ``mutagen`` tagging."""

    def __init__(
        self,
        download_dir: Path | str,
        audio_format: str = 'mp3',
        audio_bitrate: str = '320',
        output_template: str = '{artists} - {title}',
    ):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.audio_format = audio_format
        self.audio_bitrate = audio_bitrate
        self.output_template = output_template

    def _format_basename(self, song: dict[str, Any]) -> str:
        artists = ', '.join(song.get('artists') or []) or 'Unknown Artist'
        template = self.output_template.replace('.{output-ext}', '')
        try:
            rendered = template.format(
                title=song.get('name', 'Unknown'),
                artists=artists,
                artist=artists,
                album=song.get('album_name', ''),
            )
        except (KeyError, IndexError):
            rendered = f'{artists} - {song.get("name", "Unknown")}'
        return _sanitize(rendered)

    def download(
        self,
        song: dict[str, Any],
        progress_cb: Optional[ProgressCallback] = None,
    ) -> str:
        """Download ``song`` and return the resulting file name."""

        video_id = song.get('youtube_id')
        if not video_id and (song.get('source') == 'youtube'):
            video_id = song.get('song_id')
        if not video_id:
            video_id = find_match(song)
        if not video_id:
            raise RuntimeError(
                f'Could not find a YouTube match for {song.get("name")!r}'
            )

        basename = self._format_basename(song)
        out_template = str(self.download_dir / f'{basename}.%(ext)s')

        def hook(data: dict[str, Any]) -> None:
            if progress_cb is None:
                return
            try:
                status = data.get('status')
                if status == 'downloading':
                    total = (
                        data.get('total_bytes')
                        or data.get('total_bytes_estimate')
                        or 0
                    )
                    downloaded = data.get('downloaded_bytes') or 0
                    if total:
                        progress_cb(
                            min(95.0, downloaded / total * 95.0),
                            'Downloading',
                        )
                elif status == 'finished':
                    progress_cb(96.0, 'Converting')
            except Exception:
                logger.debug('progress hook error', exc_info=True)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'quiet': True,
            'noprogress': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'overwrites': True,
            'progress_hooks': [hook],
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': self.audio_format,
                    'preferredquality': self.audio_bitrate,
                }
            ],
        }
        url = f'https://music.youtube.com/watch?v={video_id}'
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        final_path = self.download_dir / f'{basename}.{self.audio_format}'
        if not final_path.exists():
            # yt-dlp sometimes uses the upstream extension for opus/m4a
            for candidate in self.download_dir.glob(f'{basename}.*'):
                if candidate.is_file():
                    final_path = candidate
                    break

        try:
            embed_metadata(final_path, song)
        except Exception:
            logger.exception('Failed to embed metadata into %s', final_path)

        if progress_cb:
            progress_cb(100.0, 'Done')
        return final_path.name


def _download_cover(url: str) -> Optional[bytes]:
    if not url:
        return None
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception:
        logger.warning('Failed to fetch cover art %s', url, exc_info=True)
        return None
    return response.content


def embed_metadata(path: Path, song: dict[str, Any]) -> None:
    if not path.exists():
        return

    title = song.get('name', '')
    artists = song.get('artists') or []
    album = song.get('album_name', '') or ''
    year = str(song.get('year') or '').strip()
    cover_bytes = _download_cover(song.get('cover_url', ''))

    suffix = path.suffix.lower().lstrip('.')

    if suffix == 'mp3':
        _tag_mp3(path, title, artists, album, year, cover_bytes)
    elif suffix in {'m4a', 'mp4', 'aac'}:
        _tag_mp4(path, title, artists, album, year, cover_bytes)
    elif suffix == 'flac':
        _tag_flac(path, title, artists, album, year, cover_bytes)
    elif suffix in {'ogg', 'oga'}:
        _tag_ogg_vorbis(path, title, artists, album, year)
    elif suffix == 'opus':
        _tag_opus(path, title, artists, album, year)


def _tag_mp3(
    path: Path,
    title: str,
    artists: list[str],
    album: str,
    year: str,
    cover_bytes: Optional[bytes],
) -> None:
    audio = MP3(str(path), ID3=ID3)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.delall('APIC')
    audio.tags.add(TIT2(encoding=3, text=title))
    if artists:
        audio.tags.add(TPE1(encoding=3, text='/'.join(artists)))
        audio.tags.add(TPE2(encoding=3, text=artists[0]))
    if album:
        audio.tags.add(TALB(encoding=3, text=album))
    if year:
        audio.tags.add(TDRC(encoding=3, text=year))
    if cover_bytes:
        audio.tags.add(
            APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=cover_bytes,
            )
        )
    audio.save(v2_version=3)


def _tag_mp4(
    path: Path,
    title: str,
    artists: list[str],
    album: str,
    year: str,
    cover_bytes: Optional[bytes],
) -> None:
    audio = MP4(str(path))
    audio['\xa9nam'] = title
    if artists:
        audio['\xa9ART'] = artists
        audio['aART'] = [artists[0]]
    if album:
        audio['\xa9alb'] = album
    if year:
        audio['\xa9day'] = year
    if cover_bytes:
        audio['covr'] = [
            MP4Cover(cover_bytes, imageformat=MP4Cover.FORMAT_JPEG)
        ]
    audio.save()


def _tag_flac(
    path: Path,
    title: str,
    artists: list[str],
    album: str,
    year: str,
    cover_bytes: Optional[bytes],
) -> None:
    audio = FLAC(str(path))
    audio['title'] = title
    if artists:
        audio['artist'] = artists
        audio['albumartist'] = artists[0]
    if album:
        audio['album'] = album
    if year:
        audio['date'] = year
    if cover_bytes:
        picture = Picture()
        picture.data = cover_bytes
        picture.type = 3
        picture.mime = 'image/jpeg'
        audio.clear_pictures()
        audio.add_picture(picture)
    audio.save()


def _tag_ogg_vorbis(
    path: Path,
    title: str,
    artists: list[str],
    album: str,
    year: str,
) -> None:
    audio = OggVorbis(str(path))
    _apply_vorbis_comments(audio, title, artists, album, year)
    audio.save()


def _tag_opus(
    path: Path,
    title: str,
    artists: list[str],
    album: str,
    year: str,
) -> None:
    audio = OggOpus(str(path))
    _apply_vorbis_comments(audio, title, artists, album, year)
    audio.save()


def _apply_vorbis_comments(audio, title, artists, album, year):
    audio['title'] = title
    if artists:
        audio['artist'] = artists
        audio['albumartist'] = artists[0]
    if album:
        audio['album'] = album
    if year:
        audio['date'] = year
