"""The audio formats a user can keep out of the library.

Shared by the "Formats to avoid" setting (downloads never bring a file
in one of them into the library; see ``slskd_provider`` and
``Downloader``) and the Doctor's "Formats to convert" (see
:mod:`downtify.format_convert`). No imports from the rest of Downtify, so
the download code can use it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

#: Formats a user can avoid or convert, lossless first. MP3 is the format
#: the conversion writes, so it is never one of them.
FORMATS = ('flac', 'wav', 'aiff', 'ape', 'wv', 'm4a', 'ogg', 'opus')
#: Extensions that count as each format.
_EXTENSIONS = {
    'flac': ('flac',),
    'wav': ('wav',),
    'aiff': ('aiff', 'aif'),
    'ape': ('ape',),
    'wv': ('wv',),
    'm4a': ('m4a', 'mp4', 'aac'),
    'ogg': ('ogg', 'oga'),
    'opus': ('opus',),
}


def normalize_formats(raw: Any, *, exclude: Iterable[str] = ()) -> list[str]:
    """*raw* as a list of known formats, in :data:`FORMATS` order, with
    *exclude* (the Downloads format, which can't be avoided) left out."""

    if isinstance(raw, str):
        raw = raw.split(',')
    if not isinstance(raw, (list, tuple, set, frozenset)):
        return []
    wanted = {str(item).strip().lower().lstrip('.') for item in raw}
    wanted = {format_of_extension(item) or item for item in wanted}
    skip = {format_of_extension(str(e).lower()) or str(e) for e in exclude}
    return [f for f in FORMATS if f in wanted and f not in skip]


def format_of_extension(ext: str) -> str:
    ext = ext.lower().lstrip('.')
    for fmt, extensions in _EXTENSIONS.items():
        if ext in extensions:
            return fmt
    return ''


def extensions_of(formats: Iterable[str]) -> frozenset[str]:
    """Every file extension that belongs to one of *formats*."""

    return frozenset(
        ext for fmt in formats for ext in _EXTENSIONS.get(str(fmt), ())
    )


def avoided(path_or_name: Any, formats: Iterable[str]) -> bool:
    """Whether a file is in one of the avoided *formats* (by extension)."""

    ext = Path(str(path_or_name)).suffix.lower().lstrip('.')
    return bool(ext) and ext in extensions_of(formats)
