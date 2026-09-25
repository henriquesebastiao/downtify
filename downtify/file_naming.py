"""How a name becomes a file or folder name - and, from that, when two names
are "the same name on disk".

A leaf module (it imports nothing from Downtify) so that both the
downloader, which writes the files, and the code that looks an artist up by
name on a streaming service can use the one rule without importing each
other.

Downloads store ``AC/DC`` as ``ACDC``: the characters a file name can't hold
are dropped. The library then takes an artist's name from the audio tag and,
for a track without one, from that file name - so the same artist can turn up
as ``AC/DC`` or as ``ACDC``. Matching a name against a service's search
results by :func:`file_name_key` treats both as the same, since to the disk
they are.
"""

from __future__ import annotations

import re

_INVALID_FS_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_WHITESPACE = re.compile(r'\s+')


def _without_invalid_chars(text: str) -> str:
    return _INVALID_FS_CHARS.sub('', text or '').strip().strip('.')


def sanitize_file_name(text: str) -> str:
    """*text* as a single file or folder name: the characters a file name
    can't hold are dropped, and so are surrounding whitespace and dots.
    ``'unknown'`` when nothing is left."""

    return _without_invalid_chars(text) or 'unknown'


def file_name_key(name: str) -> str:
    """*name* reduced to what the disk keeps of it, for comparing names:
    ``'AC/DC'`` and ``'ACDC'`` give the same key, as do ``'*NSYNC'`` and
    ``'NSYNC'`` or ``'M.I.A.'`` and ``'M.I.A'``. Case and runs of spaces
    are ignored too.

    Empty when nothing is left of *name* (``'???'``) - unlike
    :func:`sanitize_file_name` there is no ``'unknown'`` stand-in, so two
    such names can't be mistaken for each other or for a real one; callers
    should not match on an empty key.
    """

    return _WHITESPACE.sub(' ', _without_invalid_chars(name)).casefold()
