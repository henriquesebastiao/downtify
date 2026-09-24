"""Parse library-export CSV files (Soundiiz, TuneMyMusic, Exportify, ...)
into song dicts the download pipeline can resolve.

These tools all export "one row per track" CSVs, but use different column
names for the same data (e.g. Exportify's ``Track Name`` / ``Artist
Name(s)`` vs. a plain ``Title`` / ``Artist``). Rather than hard-coding one
tool's schema, headers are matched case-insensitively against a set of
known aliases, so the same importer works across exporters without the
user needing to rename columns.

Title and artist are required. Album is copied onto ``album_name``
when the CSV has a recognizable album column (Exportify's
``Album Name``, TuneMyMusic / Soundiiz ``Album``, ...). Other columns
some exporters include (ISRC, a Spotify track URI, duration) aren't
used here. Each row still goes through the same YouTube-Music
matching (:func:`downtify.providers.find_match`) that a free-text
search does today.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any

MAX_CSV_ROWS = 5000

_TITLE_HEADERS = {
    'title',
    'track',
    'track title',
    'track name',
    'song',
    'song title',
    'song name',
    'name',
}
_ARTIST_HEADERS = {
    'artist',
    'artists',
    'artist name',
    'artist name(s)',
    'track artist',
    'song artist',
    'performer',
}
_ALBUM_HEADERS = {
    'album',
    'album name',
    'album title',
    'release',
    'release name',
}

_ARTIST_SPLIT_RE = re.compile(r'[,;]')


class LibraryCsvError(ValueError):
    """Raised when a CSV can't be parsed into track/artist rows."""


def _find_column(fieldnames: list[str], aliases: set[str]) -> str | None:
    for name in fieldnames:
        if name and name.strip().lower() in aliases:
            return name
    return None


def _sniff_dialect(sample: str) -> type[csv.Dialect]:
    try:
        return csv.Sniffer().sniff(sample, delimiters=',;\t')
    except csv.Error:
        return csv.excel


def parse_library_csv(text: str) -> list[dict[str, Any]]:
    """Parse *text* (a CSV file's decoded content) into song dicts.

    Each returned dict has ``name`` (track title), ``artists`` (a list
    of one or more artist names), a synthetic ``song_id`` (``csv:0``,
    ``csv:1``, ...), and ``album_name`` when the CSV has a non-empty
    album cell. ``name``/``artists`` are the minimum shape
    :meth:`downtify.downloader.Downloader.download` needs to resolve a
    track via YouTube Music search when no direct video/Spotify URL is
    known; ``album_name`` is optional and is omitted rather than set
    blank so YouTube Music can still fill it. ``song_id`` exists
    because the frontend's queue/progress tracking keys every song by
    it and would otherwise conflate every CSV row into a single entry.

    Raises :class:`LibraryCsvError` when the file has no rows, or its
    header doesn't contain a recognizable title and artist column, or
    it exceeds :data:`MAX_CSV_ROWS` rows (a sanity cap, not a real-world
    library size limit).
    """
    dialect = _sniff_dialect(text[:4096])
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    fieldnames = reader.fieldnames or []
    title_col = _find_column(fieldnames, _TITLE_HEADERS)
    artist_col = _find_column(fieldnames, _ARTIST_HEADERS)
    album_col = _find_column(fieldnames, _ALBUM_HEADERS)
    if not title_col or not artist_col:
        raise LibraryCsvError(
            'Could not find title/artist columns in the CSV. '
            f'Columns found: {", ".join(fieldnames) or "(none)"}'
        )

    songs: list[dict[str, Any]] = []
    for row in reader:
        if len(songs) >= MAX_CSV_ROWS:
            raise LibraryCsvError(
                f'CSV has more than {MAX_CSV_ROWS} rows; split it into '
                'smaller files and import them separately.'
            )
        title = (row.get(title_col) or '').strip()
        artist_field = (row.get(artist_col) or '').strip()
        if not title or not artist_field:
            continue
        artists = [
            a.strip()
            for a in _ARTIST_SPLIT_RE.split(artist_field)
            if a.strip()
        ]
        if not artists:
            continue
        song: dict[str, Any] = {
            'song_id': f'csv:{len(songs)}',
            'name': title,
            'artists': artists,
        }
        album = (row.get(album_col) or '').strip() if album_col else ''
        if album:
            song['album_name'] = album
        songs.append(song)

    if not songs:
        raise LibraryCsvError('No track/artist rows found in the CSV.')
    return songs
