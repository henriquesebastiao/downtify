"""Download a track from YouTube and tag it with the chosen metadata."""

from __future__ import annotations

import os
import re
import re as _re
from pathlib import Path
from typing import Any, Callable, Optional

import requests
import yt_dlp
from loguru import logger
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, TALB, TCON, TDRC, TIT2, TPE1, TPE2, USLT
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from . import lyrics as lyrics_mod
from .m3u import sanitize_playlist_name
from .providers import enrich_from_match, find_match, find_match_for_video

_INVALID_FS_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

ProgressCallback = Callable[[float, str], None]


def _sanitize(text: str) -> str:
    safe = _INVALID_FS_CHARS.sub('', text or '').strip().strip('.')
    return safe or 'unknown'


# Order matters — yt-dlp tries clients top-to-bottom and uses the first one
# that yields usable formats. `ios` and `android` lead because they still
# provide audio formats in containers without a JS runtime, even though
# YouTube now requires a GVS PO Token for their HTTPS/HLS formats (those
# are skipped with a warning, but lower-quality streams remain available).
# `web_embedded` and `web` need a JS runtime for signature/n-challenge
# solving; without one, they yield no audio at all — so they're kept as
# last-resort fallbacks only. `mweb` and `tv` are included as hail-mary
# clients: `mweb` needs a PO Token too, and `tv` is affected by a DRM
# experiment (yt-dlp #12563), but including them costs nothing.
_DEFAULT_YT_PLAYER_CLIENTS = (
    'ios',
    'android',
    'web_embedded',
    'mweb',
    'web',
    'tv',
)

# Warning substrings emitted by yt-dlp that are known-harmless: they mean
# some optional format sources are skipped, but other clients in the list
# still serve usable audio. Suppressed to keep logs readable.
_SUPPRESSED_YT_WARNING_FRAGMENTS = (
    'GVS PO Token which was not provided',
    'Some tv client https formats have been skipped as they are DRM',
    'Signature solving failed: Some formats may be missing',
    'n challenge solving failed: Some formats may be missing',
)


class _YtdlpLogger:
    @staticmethod
    def debug(msg: str) -> None:
        pass

    @staticmethod
    def info(msg: str) -> None:
        pass

    @staticmethod
    def warning(msg: str) -> None:
        if not any(frag in msg for frag in _SUPPRESSED_YT_WARNING_FRAGMENTS):
            logger.warning('yt-dlp: {}', msg)

    @staticmethod
    def error(msg: str) -> None:
        logger.error('yt-dlp: {}', msg)


def _yt_player_clients() -> list[str]:
    raw = os.getenv('DOWNTIFY_YT_PLAYER_CLIENTS', '').strip()
    if not raw:
        return list(_DEFAULT_YT_PLAYER_CLIENTS)
    clients = [c.strip() for c in raw.split(',') if c.strip()]
    return clients or list(_DEFAULT_YT_PLAYER_CLIENTS)


def _yt_po_tokens() -> list[str]:
    """Comma-separated PO Tokens, each in the form ``<client>.<context>+<token>``.

    Example: ``mweb.gvs+ABC123,web.gvs+XYZ987``
    """
    raw = os.getenv('DOWNTIFY_YT_PO_TOKEN', '').strip()
    if not raw:
        return []
    return [t.strip() for t in raw.split(',') if t.strip()]


class Downloader:
    """Wraps ``yt-dlp`` plus ``mutagen`` tagging."""

    def __init__(
        self,
        download_dir: Path | str,
        audio_format: str = 'mp3',
        audio_bitrate: str = '320',
        output_template: str = '{artists} - {title}',
        lyrics_providers: Optional[list[str]] = None,
    ):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.audio_format = audio_format
        self.audio_bitrate = audio_bitrate
        self.output_template = output_template
        self.lyrics_providers = list(lyrics_providers or [])

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

    def existing_filename_for(
        self,
        song: dict[str, Any],
        subdir: Optional[str] = None,
    ) -> Optional[str]:
        """Return the on-disk filename for ``song`` if any matching file exists.

        Mirrors :meth:`download`'s post-conversion path resolution: prefers
        ``{basename}.{audio_format}`` and falls back to any
        ``{basename}.*`` since yt-dlp occasionally keeps the upstream
        extension (opus, m4a). Returns ``None`` when no file matches.

        When ``subdir`` is given the lookup is scoped to that
        sub-directory and the returned name is relative to
        ``download_dir`` (``<subdir>/<file>.<ext>``).
        """

        basename = self._format_basename(song)
        target_dir, prefix = self._resolve_target_dir(subdir)
        primary = target_dir / f'{basename}.{self.audio_format}'
        if primary.exists():
            return f'{prefix}{primary.name}'
        for candidate in target_dir.glob(f'{basename}.*'):
            if candidate.is_file():
                return f'{prefix}{candidate.name}'
        return None

    def _resolve_target_dir(self, subdir: Optional[str]) -> tuple[Path, str]:
        """Return ``(target_dir, relative_prefix)`` for an optional subdir.

        ``relative_prefix`` is empty when ``subdir`` is not used and
        otherwise terminates with ``'/'`` so callers can build the
        download-dir-relative path with simple concatenation.
        """

        if not subdir:
            return self.download_dir, ''
        safe = sanitize_playlist_name(subdir)
        return self.download_dir / safe, f'{safe}/'

    def download(
        self,
        song: dict[str, Any],
        progress_cb: Optional[ProgressCallback] = None,
        subdir: Optional[str] = None,
    ) -> str:
        """Download ``song`` and return the resulting file name.

        When ``subdir`` is provided the file is written under
        ``download_dir/<sanitized_subdir>/`` and the returned name is
        relative to ``download_dir`` (``<subdir>/<file>.<ext>``). This
        is how playlist downloads are grouped into per-playlist folders.
        """

        video_id = song.get('youtube_id')
        if not video_id and (song.get('source') == 'youtube'):
            video_id = song.get('song_id')

        match: Optional[dict[str, Any]] = None
        if not video_id:
            video_id, match = find_match(song)
        elif not song.get('album_name') or not song.get('cover_url'):
            # We already have a target video, but the metadata is incomplete.
            # Look up the YT Music entry for THIS specific videoId so we
            # don't risk switching to a karaoke / cover that happens to
            # rank higher.
            try:
                match = find_match_for_video(song, video_id)
            except Exception:
                logger.opt(exception=True).debug('enrichment match failed')
                match = None

        if not video_id:
            raise RuntimeError(
                f'Could not find a YouTube match for {song.get("name")!r}'
            )

        song = enrich_from_match(song, match)

        basename = self._format_basename(song)
        target_dir, rel_prefix = self._resolve_target_dir(subdir)
        target_dir.mkdir(parents=True, exist_ok=True)
        out_template = str(target_dir / f'{basename}.%(ext)s')

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
                logger.opt(exception=True).debug('progress hook error')

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'quiet': True,
            'noprogress': True,
            'logger': _YtdlpLogger(),
            'noplaylist': True,
            'nocheckcertificate': True,
            'overwrites': True,
            'progress_hooks': [hook],
            # Resilience against flaky DNS/network in containers.
            # googlevideo.com CDN hosts are short-lived shards and a single
            # transient EAI_AGAIN/timeout used to abort the whole download.
            'retries': 10,
            'fragment_retries': 10,
            'extractor_retries': 3,
            'socket_timeout': 30,
            # The default `web` player_client is the one most aggressively
            # gated by YouTube's "Sign in to confirm you're not a bot"
            # check on datacenter IPs. `tv` and `mweb` almost always
            # bypass it. Order matters — yt-dlp tries them in sequence.
            'extractor_args': {
                'youtube': {'player_client': _yt_player_clients()}
            },
            # Light pacing so we don't trigger 429 rate limits when the
            # user fires off multiple downloads back-to-back.
            'sleep_interval_requests': 1,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': self.audio_format,
                    'preferredquality': self.audio_bitrate,
                }
            ],
        }
        # Many container setups have IPv6 advertised but unroutable for
        # googlevideo.com, which surfaces as EAI_AGAIN on the AAAA lookup.
        # Setting DOWNTIFY_FORCE_IPV4=1 binds yt-dlp to IPv4 only.
        if os.getenv('DOWNTIFY_FORCE_IPV4', '').strip() in {
            '1',
            'true',
            'yes',
        }:
            ydl_opts['source_address'] = '0.0.0.0'

        # Optional cookie support for the rare case where even alternate
        # player_clients get challenged. DOWNTIFY_COOKIES_FILE points at a
        # Netscape-format cookies.txt; DOWNTIFY_COOKIES_FROM_BROWSER takes
        # "<browser>" or "<browser>:<profile>" (e.g. "firefox" or
        # "chrome:Default").
        cookies_file = os.getenv('DOWNTIFY_COOKIES_FILE', '').strip()
        if cookies_file:
            ydl_opts['cookiefile'] = cookies_file
        cookies_browser = os.getenv(
            'DOWNTIFY_COOKIES_FROM_BROWSER', ''
        ).strip()
        if cookies_browser:
            parts = cookies_browser.split(':', 1)
            ydl_opts['cookiesfrombrowser'] = (
                (parts[0],) if len(parts) == 1 else (parts[0], parts[1])
            )

        url = f'https://music.youtube.com/watch?v={video_id}'
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        final_path = target_dir / f'{basename}.{self.audio_format}'
        if not final_path.exists():
            # yt-dlp sometimes uses the upstream extension for opus/m4a
            for candidate in target_dir.glob(f'{basename}.*'):
                if candidate.is_file():
                    final_path = candidate
                    break

        try:
            embed_metadata(final_path, song)
        except Exception:
            logger.exception('Failed to embed metadata into {}', final_path)

        if self.lyrics_providers:
            try:
                fetched = lyrics_mod.fetch(song, self.lyrics_providers)
            except Exception:
                logger.exception('Lyrics fetch crashed for {}', final_path)
                fetched = None
            if fetched is not None:
                try:
                    embed_lyrics(final_path, fetched)
                except Exception:
                    logger.exception(
                        'Failed to embed lyrics into {}', final_path
                    )

        if progress_cb:
            progress_cb(100.0, 'Done')
        return f'{rel_prefix}{final_path.name}'


def _download_cover(url: str) -> Optional[bytes]:
    if not url:
        return None
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception:
        logger.opt(exception=True).warning('Failed to fetch cover art {}', url)
        return None
    return response.content


def embed_metadata(path: Path, song: dict[str, Any]) -> None:
    if not path.exists():
        return

    title = song.get('name', '')
    artists = song.get('artists') or []
    album = song.get('album_name', '') or ''
    year = str(song.get('year') or '').strip()
    genre = (song.get('genre') or '').strip()
    cover_bytes = _download_cover(song.get('cover_url', ''))

    suffix = path.suffix.lower().lstrip('.')

    if suffix == 'mp3':
        _tag_mp3(path, title, artists, album, year, genre, cover_bytes)
    elif suffix in {'m4a', 'mp4', 'aac'}:
        _tag_mp4(path, title, artists, album, year, genre, cover_bytes)
    elif suffix == 'flac':
        _tag_flac(path, title, artists, album, year, genre, cover_bytes)
    elif suffix in {'ogg', 'oga'}:
        _tag_ogg_vorbis(path, title, artists, album, year, genre)
    elif suffix == 'opus':
        _tag_opus(path, title, artists, album, year, genre)


def _tag_mp3(
    path: Path,
    title: str,
    artists: list[str],
    album: str,
    year: str,
    genre: str,
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
    if genre:
        audio.tags.add(TCON(encoding=3, text=genre))
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
    genre: str,
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
    if genre:
        audio['\xa9gen'] = genre
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
    genre: str,
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
    if genre:
        audio['genre'] = genre
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
    genre: str,
) -> None:
    audio = OggVorbis(str(path))
    _apply_vorbis_comments(audio, title, artists, album, year, genre)
    audio.save()


def _tag_opus(
    path: Path,
    title: str,
    artists: list[str],
    album: str,
    year: str,
    genre: str,
) -> None:
    audio = OggOpus(str(path))
    _apply_vorbis_comments(audio, title, artists, album, year, genre)
    audio.save()


def _apply_vorbis_comments(audio, title, artists, album, year, genre):
    audio['title'] = title
    if artists:
        audio['artist'] = artists
        audio['albumartist'] = artists[0]
    if album:
        audio['album'] = album
    if year:
        audio['date'] = year
    if genre:
        audio['genre'] = genre


def embed_lyrics(path: Path, lyrics: 'lyrics_mod.Lyrics') -> None:
    """Embed plain lyrics into the audio tag and write a .lrc sidecar
    next to it when synced lyrics are available."""

    if not path.exists() or not lyrics.has_any():
        return

    if lyrics.synced:
        sidecar = path.with_suffix('.lrc')
        try:
            sidecar.write_text(lyrics.synced, encoding='utf-8')
        except OSError:
            logger.opt(exception=True).warning(
                'Could not write LRC sidecar {}', sidecar
            )

    text = lyrics.plain or _strip_lrc_timestamps(lyrics.synced or '')
    if not text:
        return

    suffix = path.suffix.lower().lstrip('.')
    if suffix == 'mp3':
        audio = MP3(str(path), ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        audio.tags.delall('USLT')
        audio.tags.add(USLT(encoding=3, lang='eng', desc='', text=text))
        audio.save(v2_version=3)
    elif suffix in {'m4a', 'mp4', 'aac'}:
        audio = MP4(str(path))
        audio['\xa9lyr'] = text
        audio.save()
    elif suffix == 'flac':
        audio = FLAC(str(path))
        audio['lyrics'] = text
        audio.save()
    elif suffix in {'ogg', 'oga'}:
        audio = OggVorbis(str(path))
        audio['lyrics'] = text
        audio.save()
    elif suffix == 'opus':
        audio = OggOpus(str(path))
        audio['lyrics'] = text
        audio.save()


def _strip_lrc_timestamps(synced: str) -> str:
    cleaned = _re.sub(r'\[\d{1,2}:\d{2}(?:\.\d{1,3})?\]', '', synced)
    return '\n'.join(
        line.strip() for line in cleaned.splitlines() if line.strip()
    )
