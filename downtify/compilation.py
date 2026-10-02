"""Marking a library album as a various-artists compilation by hand, and
remembering the mark for the album's later downloads.

Whether an album is a compilation comes from its source (see
``album_artist.py``): only an album the source credits to "Various
Artists" is one. A source can be wrong for a given release - a single
credited to its first artist though four share it equally - so an admin
can mark the album from its page, or unmark one the source got wrong the
other way.

Marking rewrites every track's album-artist tag to "Various Artists" and
adds the compilation flag (``TCMP`` / ``COMPILATION`` / ``cpil``); unmarking
puts the album artist back and removes the flag. Only those two tags
change. Files stay where they are: "Organize by artist" files a
compilation's track under its own first artist anyway
(:func:`downtify.album_artist.filing_artist`), and media servers group
albums by the tags. Each file is rewritten through a working copy that
must still read as the same audio before it replaces the original, and
keeps its modification time - as the library upgrade does.

The mark is kept in :class:`CompilationMarks`, keyed by the album's title
and the album artist it was downloaded with, so a track of the same album
downloaded later gets the same tags (:meth:`CompilationMarks.override_for`,
applied by the downloader).
"""

from __future__ import annotations

import os
import shutil
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from mutagen import File as MutagenFile
from mutagen.flac import FLAC
from mutagen.id3 import ID3, TCMP, TPE2, ID3NoHeaderError
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from .album_artist import VARIOUS_ARTISTS, is_various_artists
from .file_naming import file_name_key
from .library_metadata import read_audio_metadata
from .library_upgrade import staging_path
from .sqlite_utils import connect_sqlite

#: A rewritten file must still play for as long as the original did.
_DURATION_TOLERANCE_SECONDS = 1.0

#: The formats tagged with Vorbis comments, by extension.
_VORBIS_READERS = {
    'flac': FLAC,
    'ogg': OggVorbis,
    'oga': OggVorbis,
    'opus': OggOpus,
}


class CompilationError(ValueError):
    """The request can't be applied (no tracks, several albums, ...)."""


# ── The remembered marks ──────────────────────────────────────────────
class CompilationMarks:
    """Albums whose compilation status an admin set by hand.

    One row per album, keyed by the album artist its tracks were
    downloaded with and its title (both compared as
    :func:`~downtify.file_naming.file_name_key`): ``compilation`` 1 with
    ``album_artist`` "Various Artists" for a marked album, 0 with the
    album artist to use instead for one unmarked against its source.
    """

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self):
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS album_compilation_marks (
                    artist_key TEXT NOT NULL,
                    album_key TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    album TEXT NOT NULL,
                    compilation INTEGER NOT NULL,
                    album_artist TEXT NOT NULL,
                    marked_at TEXT NOT NULL,
                    PRIMARY KEY (artist_key, album_key)
                )
            """)

    def set(
        self, artist: str, album: str, *, compilation: bool, album_artist: str
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO album_compilation_marks
                   (artist_key, album_key, artist, album, compilation,
                    album_artist, marked_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(artist_key, album_key) DO UPDATE SET
                     artist = excluded.artist,
                     album = excluded.album,
                     compilation = excluded.compilation,
                     album_artist = excluded.album_artist,
                     marked_at = excluded.marked_at""",
                (
                    file_name_key(artist),
                    file_name_key(album),
                    artist,
                    album,
                    1 if compilation else 0,
                    album_artist,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def remove(self, artist: str, album: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """DELETE FROM album_compilation_marks
                   WHERE artist_key = ? AND album_key = ?""",
                (file_name_key(artist), file_name_key(album)),
            )

    def marked_albums(self, album: str) -> list[dict[str, Any]]:
        """The albums titled *album* marked as compilations by hand."""

        with self._connect() as conn:
            rows = conn.execute(
                """SELECT artist, album, album_artist
                   FROM album_compilation_marks
                   WHERE album_key = ? AND compilation = 1
                   ORDER BY marked_at""",
                (file_name_key(album),),
            ).fetchall()
        return [dict(row) for row in rows]

    def override_for(self, song: dict[str, Any]) -> dict[str, Any]:
        """``album_artist`` / ``compilation`` for a *song* about to be
        downloaded, when its album was marked or unmarked by hand - else
        ``{}``. The song is matched by the album artist its source gave it
        (else its first artist) and its album title."""

        album = str(song.get('album_name') or '').strip()
        if not album:
            return {}
        artist = str(song.get('album_artist') or '').strip()
        if not artist:
            artists = song.get('artists') or []
            artist = str(artists[0]).strip() if artists else ''
        if song.get('compilation'):
            artist = VARIOUS_ARTISTS
        if not file_name_key(artist) or not file_name_key(album):
            return {}
        with self._connect() as conn:
            row = conn.execute(
                """SELECT compilation, album_artist
                   FROM album_compilation_marks
                   WHERE artist_key = ? AND album_key = ?""",
                (file_name_key(artist), file_name_key(album)),
            ).fetchone()
        if row is None:
            return {}
        return {
            'album_artist': str(row['album_artist']),
            'compilation': bool(row['compilation']),
        }


# ── Rewriting the two tags ────────────────────────────────────────────
def write_album_artist_tags(
    path: Path, album_artist: str, *, compilation: bool
) -> None:
    """Set *path*'s album-artist tag (removed when blank) and add or
    remove its compilation flag, leaving every other tag as it is - the
    same frames/keys :func:`downtify.downloader.embed_metadata` writes."""

    suffix = path.suffix.lower().lstrip('.')
    if suffix == 'mp3':
        try:
            tags = ID3(str(path))
        except ID3NoHeaderError:
            tags = ID3()
        tags.delall('TPE2')
        tags.delall('TCMP')
        if album_artist:
            tags.add(TPE2(encoding=3, text=album_artist))
        if compilation:
            tags.add(TCMP(encoding=3, text='1'))
        # v2.4, as embed_metadata saves (v2.3 corrupts UTF-8 frames).
        tags.save(str(path), v2_version=4)
        return
    if suffix in {'m4a', 'mp4', 'aac'}:
        audio = MP4(str(path))
        for key in ('aART', 'cpil'):
            audio.pop(key, None)
        if album_artist:
            audio['aART'] = [album_artist]
        if compilation:
            audio['cpil'] = True
        audio.save()
        return
    reader = _VORBIS_READERS.get(suffix)
    if reader is None:
        raise CompilationError(f'Unsupported format: {path.suffix}')
    audio = reader(str(path))
    for key in ('albumartist', 'compilation'):
        audio.pop(key, None)
    if album_artist:
        audio['albumartist'] = album_artist
    if compilation:
        audio['compilation'] = '1'
    audio.save()


def _length(path: Path) -> float:
    try:
        audio = MutagenFile(str(path))
    except Exception:
        return 0.0
    info = getattr(audio, 'info', None)
    return float(getattr(info, 'length', 0.0) or 0.0)


def retag_file(path: Path, album_artist: str, *, compilation: bool) -> None:
    """:func:`write_album_artist_tags` on a working copy of *path* that
    must still be readable audio of the same length before it replaces
    the original; keeps the original modification time. Raises when it
    fails, leaving the original untouched."""

    stat = path.stat()
    expected = _length(path)
    staged = staging_path(path)
    shutil.copy2(str(path), str(staged))
    try:
        write_album_artist_tags(staged, album_artist, compilation=compilation)
        length = _length(staged)
        if length <= 0 or (
            expected > 0
            and abs(length - expected) > _DURATION_TOLERANCE_SECONDS
        ):
            raise CompilationError('The rewritten file did not verify')
        os.replace(str(staged), str(path))
    finally:
        staged.unlink(missing_ok=True)
    try:
        os.utime(str(path), ns=(stat.st_atime_ns, stat.st_mtime_ns))
    except OSError:
        pass


# ── Marking / unmarking an album ──────────────────────────────────────
@dataclass
class _Track:
    stored_path: str
    full: Path
    album: str
    album_artist: str
    artists: list[str]

    @property
    def credited_as(self) -> str:
        """The album artist the Library shows it under: the tag, else its
        first artist (``normalizeTrack`` in ``frontend/src/lib/library.js``)."""

        return self.album_artist or (self.artists[0] if self.artists else '')


@dataclass
class CompilationResult:
    album: str
    album_artist: str
    compilation: bool
    changed: list[str] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)


def _most_common(names: list[str]) -> str:
    counts = Counter(name for name in names if name)
    return counts.most_common(1)[0][0] if counts else ''


def _read_tracks(files: list[tuple[str, Path]]) -> list[_Track]:
    tracks = []
    for stored_path, full in files:
        meta = read_audio_metadata(full)
        tracks.append(
            _Track(
                stored_path=stored_path,
                full=full,
                album=str(meta.get('album') or '').strip(),
                album_artist=str(meta.get('album_artist') or '').strip(),
                artists=[
                    str(a).strip()
                    for a in meta.get('artists') or []
                    if str(a).strip()
                ],
            )
        )
    return tracks


def _restored_album_artist(
    tracks: list[_Track], album: str, marks: CompilationMarks
) -> tuple[str, Optional[str]]:
    """``(album artist to put back, marked artist to forget)`` when
    unmarking: the album artist the album had when it was marked by hand,
    else - a compilation by its source - the artist most of its tracks
    list first."""

    first_artists = [t.artists[0] for t in tracks if t.artists]
    credited = {file_name_key(a) for t in tracks for a in t.artists}
    for mark in marks.marked_albums(album):
        if file_name_key(mark['artist']) in credited:
            return mark['artist'], mark['artist']
    return _most_common(first_artists), None


def set_album_compilation(
    files: list[tuple[str, Path]],
    *,
    compilation: bool,
    marks: CompilationMarks,
) -> CompilationResult:
    """Mark (*compilation* true) or unmark the album whose tracks are
    *files* (``(stored path, full path)`` pairs), rewrite their tags and
    remember it. Raises :class:`CompilationError` when *files* is empty,
    isn't one album, or is already in the asked state."""

    if not files:
        raise CompilationError('No tracks given')
    tracks = _read_tracks(files)
    albums = {file_name_key(t.album) for t in tracks}
    if len(albums) != 1 or not next(iter(albums)):
        raise CompilationError('The tracks must all be from one album')
    album = _most_common([t.album for t in tracks])
    current = _most_common([t.credited_as for t in tracks])
    is_compilation = is_various_artists(current)
    if compilation == is_compilation:
        raise CompilationError(
            'The album is already a compilation'
            if compilation
            else 'The album is not a compilation'
        )

    marked_artist: Optional[str] = None
    if compilation:
        album_artist = VARIOUS_ARTISTS
    else:
        album_artist, marked_artist = _restored_album_artist(
            tracks, album, marks
        )
        if not album_artist:
            raise CompilationError('No artist to give the album back')

    result = CompilationResult(
        album=album, album_artist=album_artist, compilation=compilation
    )
    for track in tracks:
        try:
            retag_file(track.full, album_artist, compilation=compilation)
        except Exception as exc:
            logger.opt(exception=True).warning(
                'Could not retag {} as a compilation', track.stored_path
            )
            result.failed.append({
                'file': track.stored_path,
                'error': str(exc)[:200],
            })
            continue
        result.changed.append(track.stored_path)

    if not result.changed:
        return result
    # Remembered only once a file actually changed.
    if compilation:
        marks.set(current, album, compilation=True, album_artist=album_artist)
    elif marked_artist is not None:
        marks.remove(marked_artist, album)
    else:
        # A compilation by its source: the next download of it must not
        # be marked as one again.
        marks.set(
            VARIOUS_ARTISTS,
            album,
            compilation=False,
            album_artist=album_artist,
        )
    return result
