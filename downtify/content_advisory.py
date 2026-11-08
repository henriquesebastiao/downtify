"""The "explicit" mark of a song, as it is stored in an audio file.

Spotify, YouTube Music and Deezer all say whether a song has explicit
lyrics. Downtify keeps that in the file itself, the way iTunes does and the
media servers that read it (Navidrome among them) expect: the ``rtng`` atom
in MP4 (1 = explicit, 2 = clean) and an ``ITUNESADVISORY`` text everywhere
else - a TXXX frame in ID3, a comment in Vorbis, FLAC and Opus.

Only the explicit mark is written: a song the service doesn't flag is left
as it is, since nobody has said it is clean. Writing is in
:mod:`downtify.downloader`, reading in :mod:`downtify.library_metadata`.
"""

from __future__ import annotations

ADVISORY_TAG = 'ITUNESADVISORY'
MP4_ADVISORY_ATOM = 'rtng'

#: What gets written for an explicit song.
ADVISORY_EXPLICIT = '1'

#: What marks one when read: 1, and the older 4. (2 is "clean".)
EXPLICIT_VALUES = frozenset({'1', '4'})
