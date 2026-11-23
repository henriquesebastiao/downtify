"""Where each downloaded file's audio came from, and the sources that
turned out wrong for a song (issue #582).

Two things a library file carries no mark of:

* **Which upload it is.** When a YouTube / YouTube Music / SoundCloud
  download finishes, the video id (or SoundCloud track URL) is kept here,
  by library path, with the song's identity (:func:`track_keys`) and a
  signature of the audio as written (:func:`audio_signature`: codec,
  sample rate, channels and length - tag rewrites leave it alone).
* **Which uploads are wrong for a song.** When an admin replaces a
  track's audio (Replace audio, or by swapping the file on disk), the
  upload it came from is *rejected* for that song: the matcher never picks
  it for the song again, from any playlist, artist watch or download
  (``providers.excluding_sources``). Otherwise the next download of the
  song, from another playlist, finds the same wrong video.

A file swapped on disk outside Downtify (a CD rip or a Soulseek download
saved under the same name) is told apart by its audio signature: when it
no longer matches what Downtify wrote, :meth:`DownloadSources.replaced_on_disk`
says so, and the downloader keeps the file as if it had been replaced
through Replace audio (``downtify/hand_replaced.py``), even with
**Download again if the file exists** on.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Optional

from loguru import logger
from mutagen import File as MutagenFile

from .db.config import Dialect
from .db.core import Database, as_database

#: Lengths (seconds) closer than this are the same audio: what a tag
#: rewrite can shift in a VBR estimate, far below any other recording.
LENGTH_TOLERANCE = 0.5

_SPACES_RE = re.compile(r'\s+')


def _key(file: str) -> str:
    return str(file or '').replace('\\', '/').strip('/')


def _fold(text: Any) -> str:
    value = unicodedata.normalize('NFKC', str(text or '')).casefold()
    return _SPACES_RE.sub(' ', value).strip()


def track_keys(song: dict[str, Any]) -> list[str]:
    """The keys a song is known by: its Spotify id, its ISRC, and its
    lead artist + title. A rejection is kept under every one, so it holds
    whichever of them the next download of the song carries."""

    keys: list[str] = []
    spotify_id = str(song.get('spotify_id') or '').strip()
    if not spotify_id and song.get('source') in {None, '', 'spotify'}:
        spotify_id = str(song.get('song_id') or '').strip()
    if re.fullmatch(r'[0-9A-Za-z]{22}', spotify_id):
        keys.append(f'spotify:{spotify_id}')
    isrc = str(song.get('isrc') or '').strip().upper()
    if isrc:
        keys.append(f'isrc:{isrc}')
    artists = song.get('artists') or []
    if isinstance(artists, str):
        artists = [artists]
    artist = _fold(artists[0] if artists else song.get('artist'))
    title = _fold(song.get('name') or song.get('title'))
    if artist and title:
        keys.append(f'name:{artist}|{title}')
    return keys


def audio_signature(path: Path) -> Optional[dict[str, Any]]:
    """What the audio of *path* is, independent of its tags: ``{codec,
    sample_rate, channels, length}``; ``None`` when it can't be read."""

    try:
        audio = MutagenFile(str(path))
    except Exception:
        return None
    info = getattr(audio, 'info', None)
    if audio is None or info is None:
        return None
    return {
        'codec': type(info).__name__,
        'sample_rate': int(getattr(info, 'sample_rate', 0) or 0),
        'channels': int(getattr(info, 'channels', 0) or 0),
        'length': round(float(getattr(info, 'length', 0) or 0), 3),
    }


def same_audio(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Whether two :func:`audio_signature` results are the same audio."""

    return (
        a.get('codec') == b.get('codec')
        and a.get('sample_rate') == b.get('sample_rate')
        and a.get('channels') == b.get('channels')
        and abs(float(a.get('length') or 0) - float(b.get('length') or 0))
        < LENGTH_TOLERANCE
    )


class DownloadSources:
    """The source of each downloaded file and the sources rejected per
    song, in the library database."""

    def __init__(self, path_or_db: str | Path | Database) -> None:
        self.db = as_database(path_or_db, 'library')
        # The Postgres schema is created by migrations; only SQLite needs DDL.
        if self.db.dialect is Dialect.SQLITE:
            with self.db.connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS file_download_sources (
                        file TEXT PRIMARY KEY,
                        source TEXT NOT NULL DEFAULT '',
                        track_keys TEXT NOT NULL DEFAULT '[]',
                        signature TEXT NOT NULL DEFAULT '',
                        recorded_at REAL NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rejected_sources (
                        track_key TEXT NOT NULL,
                        source TEXT NOT NULL,
                        rejected_at REAL NOT NULL,
                        PRIMARY KEY (track_key, source)
                    )
                """)

    # -- per file -------------------------------------------------------

    def record(
        self,
        file: str,
        full_path: Optional[Path],
        source: str,
        keys: Iterable[str],
    ) -> None:
        """*file* was just written from *source* (a video id, a SoundCloud
        URL, or ``''`` for an uploaded file) for the song known by *keys*."""

        signature = audio_signature(full_path) if full_path else None
        with self.db.connect() as conn:
            conn.execute(
                """INSERT INTO file_download_sources
                   (file, source, track_keys, signature, recorded_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(file) DO UPDATE SET
                     source = excluded.source,
                     track_keys = excluded.track_keys,
                     signature = excluded.signature,
                     recorded_at = excluded.recorded_at""",
                (
                    _key(file),
                    str(source or '').strip(),
                    json.dumps(sorted(set(keys))),
                    json.dumps(signature) if signature else '',
                    time.time(),
                ),
            )

    def get(self, file: str) -> Optional[dict[str, Any]]:
        """``{file, source, track_keys, signature, recorded_at}`` or
        ``None`` when nothing was recorded for *file*."""

        with self.db.connect() as conn:
            row = conn.execute(
                'SELECT file, source, track_keys, signature, recorded_at '
                'FROM file_download_sources WHERE file = ?',
                (_key(file),),
            ).fetchone()
        if row is None:
            return None
        found = dict(row)
        try:
            found['track_keys'] = list(json.loads(found['track_keys']))
        except (TypeError, ValueError):
            found['track_keys'] = []
        try:
            found['signature'] = (
                json.loads(found['signature']) if found['signature'] else None
            )
        except (TypeError, ValueError):
            found['signature'] = None
        return found

    def files_for_sources(self, sources: Iterable[str]) -> dict[str, str]:
        """``{source: file}`` for the files downloaded from *sources*
        (video ids, SoundCloud URLs); the newest file when several were."""

        wanted = sorted({str(s).strip() for s in sources if str(s).strip()})
        found: dict[str, str] = {}
        # A few hundred at a time keeps under SQLite's bound-parameter cap.
        for start in range(0, len(wanted), 500):
            chunk = wanted[start : start + 500]
            marks = ', '.join('?' for _ in chunk)
            with self.db.connect() as conn:
                rows = conn.execute(
                    'SELECT source, file FROM file_download_sources '
                    f'WHERE source IN ({marks}) ORDER BY recorded_at',
                    tuple(chunk),
                ).fetchall()
            found.update({
                str(row['source']): str(row['file']) for row in rows
            })
        return found

    def replaced_on_disk(self, file: str, full_path: Path) -> bool:
        """Whether the audio at *full_path* is no longer what Downtify
        wrote to *file*: someone swapped the file outside Downtify. A file
        Downtify never recorded, or can't read, says no."""

        row = self.get(file)
        if row is None or not row['signature'] or not full_path.is_file():
            return False
        current = audio_signature(full_path)
        if current is None:
            return False
        return not same_audio(row['signature'], current)

    # -- rejections -----------------------------------------------------

    def reject_file_source(
        self,
        file: str,
        extra_keys: Iterable[str] = (),
        keep: str = '',
        why: str = 'its audio was replaced',
    ) -> Optional[str]:
        """The upload *file* came from was wrong: never pick it again for
        its song (known by the recorded keys plus *extra_keys*). Returns
        the rejected source, or ``None`` when none is known (or it is
        *keep*, the source that replaces it)."""

        row = self.get(file)
        source = str((row or {}).get('source') or '').strip()
        if not source or source == str(keep or '').strip():
            return None
        keys = {*((row or {}).get('track_keys') or []), *extra_keys}
        self.reject(source, keys)
        logger.info('Source {} rejected for {} ({})', source, file, why)
        return source

    def reject(self, source: str, keys: Iterable[str]) -> None:
        source = str(source or '').strip()
        rows = [(key, source, time.time()) for key in set(keys) if key]
        if not source or not rows:
            return
        with self.db.connect() as conn:
            for row in rows:
                conn.execute(
                    """INSERT INTO rejected_sources
                       (track_key, source, rejected_at) VALUES (?, ?, ?)
                       ON CONFLICT(track_key, source) DO UPDATE SET
                         rejected_at = excluded.rejected_at""",
                    row,
                )

    def allow(self, source: str, keys: Iterable[str]) -> None:
        """Take back *source*'s rejection for the song known by *keys*
        (an admin picked it again by hand)."""

        source = str(source or '').strip()
        keys = [key for key in set(keys) if key]
        if not source or not keys:
            return
        marks = ', '.join('?' for _ in keys)
        with self.db.connect() as conn:
            conn.execute(
                'DELETE FROM rejected_sources WHERE source = ? '
                f'AND track_key IN ({marks})',
                (source, *keys),
            )

    def rejected_for(self, song: dict[str, Any]) -> set[str]:
        """Every source rejected for *song* under any of its keys."""

        keys = track_keys(song)
        if not keys:
            return set()
        marks = ', '.join('?' for _ in keys)
        with self.db.connect() as conn:
            rows = conn.execute(
                'SELECT DISTINCT source FROM rejected_sources '
                f'WHERE track_key IN ({marks})',
                tuple(keys),
            ).fetchall()
        return {str(row['source']) for row in rows}

    def forget_rejections(self, keys: Iterable[str]) -> int:
        """Allow every rejected source of the song known by *keys* again."""

        keys = [key for key in set(keys) if key]
        if not keys:
            return 0
        marks = ', '.join('?' for _ in keys)
        with self.db.connect() as conn:
            cursor = conn.execute(
                f'DELETE FROM rejected_sources WHERE track_key IN ({marks})',
                tuple(keys),
            )
        return cursor.rowcount
