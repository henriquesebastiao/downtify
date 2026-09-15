"""Parse library-export CSV files (Soundiiz, TuneMyMusic, Exportify, ...)
into song dicts the download pipeline can resolve.

These tools all export "one row per track" CSVs, but use different column
names for the same data (e.g. Exportify's ``Track Name`` / ``Artist
Name(s)`` vs. a plain ``Title`` / ``Artist``). Rather than hard-coding one
tool's schema, headers are matched case-insensitively against a set of
known aliases, so the same importer works across exporters without the
user needing to rename columns.

Only title and artist are read. Other columns some exporters include
(album, ISRC, a Spotify track URI, duration) aren't used here — the
importer intentionally sticks to the exact "track + artist" scope the
feature was requested for; each row still goes through the same
YouTube-Music matching (:func:`downtify.providers.find_match`) that a
free-text search does today.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any

MAX_CSV_ROWS = 2000

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
    of one or more artist names), and a synthetic ``song_id`` (``csv:0``,
    ``csv:1``, ...). ``name``/``artists`` are the minimum shape
    :meth:`downtify.downloader.Downloader.download` needs to resolve a
    track via YouTube Music search when no direct video/Spotify URL is
    known; ``song_id`` exists because the frontend's queue/progress
    tracking keys every song by it and would otherwise conflate every
    CSV row into a single entry.

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
        songs.append({
            'song_id': f'csv:{len(songs)}',
            'name': title,
            'artists': artists,
        })

    if not songs:
        raise LibraryCsvError('No track/artist rows found in the CSV.')
    return songs
