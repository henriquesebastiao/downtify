"""Doctor: find and repair what older Downtify versions left behind.

New versions fix a problem from then on - slskd transfers are now
removed after import, playlist covers sit next to the M3U, Navidrome
playlists are synced - but files and playlists written by an older
version keep the old shape. The Doctor looks for that leftover state
and, where it can prove a repair is safe, offers to fix it:

* **slskd leftovers** (:func:`working_copy_rows`, :func:`verify_copies`) -
  transfers an older version left in slskd's folder after copying them
  into the library. A leftover is only ever offered for deletion once a
  library file holding bit-identical audio is found
  (:mod:`downtify.doctor_audio`).
* **Duplicate playlists** (:func:`m3u_duplicate_groups`) - two M3U files
  for one playlist, e.g. one left at the old ``Playlists/`` location.
  Merging keeps every song of both (only when they mostly overlap), the
  cover from whichever has one, and one file.
* **Navidrome** (:func:`navidrome_playlist_findings`) - what clients
  actually see: an M3U Navidrome imported *and* the playlist Downtify
  created through the API, imported playlists whose M3U is gone (Navidrome
  never removes those), and imported playlists missing songs Navidrome
  couldn't find.
* **Duplicate songs** (:func:`navidrome_song_duplicates`, plus
  :func:`downtify.library_usage.duplicates` for Downtify's own view).
* **Same song, new Spotify id** (:func:`relinked_tracks`) - a monitored
  playlist whose track got a new Spotify id is downloaded again.

Everything here is pure or takes its I/O as arguments; the routes
(:mod:`downtify.doctor_routes`) gather the inputs and run the repairs.
"""

from __future__ import annotations

import os
import shutil
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Optional

from .library_catalog import song_key
from .library_paths import SLSKD_LIBRARY_PREFIX
from .library_usage import split_working_copies
from .m3u import build_m3u_content, read_m3u_entries
from .playlist_identity import imported_from, made_by_downtify, playlist_key

#: A leftover changed this recently may still be written by slskd.
RECENT_SECONDS = 15 * 60
#: Two library files of one song whose lengths differ by more than this
#: (seconds) are not the same recording.
DURATION_TOLERANCE = 2.0
#: Library files hashed per leftover before giving up on it.
MAX_CANDIDATES = 8
#: Share of the smaller playlist that must be in the larger one before
#: two playlists are merged.
MIN_OVERLAP = 0.8

#: The Doctor's sections. The health check looks at all of them but
#: ``slskd``, which has its own (slower) check.
SECTIONS = (
    'slskd',
    'playlists',
    'navidrome',
    'duplicates',
    'relinked',
    'formats',
)
HEALTH_SECTIONS = frozenset(SECTIONS) - {'slskd', 'formats'}
#: The sections each check finds again.
CHECKS = {
    'health': HEALTH_SECTIONS,
    'slskd': frozenset({'slskd'}),
    'formats': frozenset({'formats'}),
}
#: The sections whose findings each repair can change. Merging duplicate
#: songs rewrites M3Us and removes library files a verified slskd
#: leftover may match; deleting slskd leftovers changes the songs the
#: duplicate and Navidrome checks counted; merging playlists changes the
#: M3Us the slskd check counts as references. Merging duplicates leaves
#: its own list usable - the server takes the merged copies out of it.
#: Converting files out of a format (``convert``) swaps library files
#: the way a duplicate merge does, and the files it left are still listed
#: (the server drops the converted ones from the format list).
REPAIR_IMPACT = {
    'slskd_clean': frozenset({
        'slskd',
        'duplicates',
        'navidrome',
        'relinked',
        'formats',
    }),
    'merge': frozenset({'slskd', 'playlists', 'navidrome', 'duplicates'}),
    'playlists': frozenset({'slskd', 'playlists', 'navidrome', 'duplicates'}),
    'navidrome': frozenset({'navidrome'}),
    'dedupe': frozenset({
        'slskd',
        'playlists',
        'navidrome',
        'relinked',
        'formats',
    }),
    'convert': frozenset({
        'slskd',
        'playlists',
        'navidrome',
        'duplicates',
        'relinked',
    }),
}


def stale_after(stale: Collection[str], kind: str) -> set[str]:
    """The sections out of date once a *kind* job has finished: a check
    brings its own sections up to date, a repair puts the ones it can
    change out of date until they are checked again."""

    now = set(stale) - CHECKS.get(kind, frozenset())
    return now | REPAIR_IMPACT.get(kind, frozenset())


STATUS_VERIFIED = 'verified'
STATUS_DIFFERENT = 'different'
STATUS_UNMATCHED = 'unmatched'
STATUS_UNREADABLE = 'unreadable'
STATUS_RECENT = 'recent'
STATUS_MISSING = 'missing'


# ---------------------------------------------------------------------------
# slskd leftovers
# ---------------------------------------------------------------------------


def norm(path: Any) -> str:
    return str(path or '').strip().replace('\\', '/')


def working_copy_rows(
    entries: Iterable[dict[str, Any]],
    *,
    sources: dict[str, int],
    slskd_in_place: bool,
    referenced: Collection[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """``(library rows, leftover rows)`` - the same split the storage
    usage page makes (:func:`downtify.library_usage.split_working_copies`),
    with each leftover's listing row (tags, length) kept for matching.

    A recorded transfer the listing doesn't know comes back as a bare
    ``{'file', 'size'}`` row.
    """

    rows = list(entries)
    library, working = split_working_copies(
        rows,
        sources=sources,
        slskd_in_place=slskd_in_place,
        referenced=referenced,
    )
    by_file = {norm(r.get('file')): r for r in rows}
    leftovers = [
        by_file.get(name) or {'file': name, 'size': size}
        for name, size in sorted(working.items())
    ]
    return library, leftovers


def _duration(row: dict[str, Any]) -> float:
    try:
        return float(row.get('duration') or 0)
    except (TypeError, ValueError):
        return 0.0


def _codec(row: dict[str, Any]) -> str:
    codec = str(row.get('codec') or '').strip().lower()
    if codec:
        return codec
    return PurePosixPath(norm(row.get('file'))).suffix.lstrip('.').lower()


class CandidateIndex:
    """Library rows reachable by song (artist/title) and by length."""

    def __init__(self, library: Iterable[dict[str, Any]]) -> None:
        self.by_song: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.by_second: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in library:
            name = norm(row.get('file'))
            if not name or name.startswith(SLSKD_LIBRARY_PREFIX):
                continue
            key = song_key(
                str(row.get('artist') or ''), str(row.get('title') or '')
            )
            if key != '|':
                self.by_song[key].append(row)
            length = _duration(row)
            if length:
                self.by_second[round(length)].append(row)

    def candidates(self, leftover: dict[str, Any]) -> list[dict[str, Any]]:
        """Library rows that could hold *leftover*'s recording, the most
        likely first: same song and length, then same length and format.
        """

        length = _duration(leftover)
        codec = _codec(leftover)
        found: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add(row: dict[str, Any]) -> None:
            name = norm(row.get('file'))
            if name not in seen:
                seen.add(name)
                found.append(row)

        key = song_key(
            str(leftover.get('artist') or ''),
            str(leftover.get('title') or ''),
        )
        for row in self.by_song.get(key, []) if key != '|' else []:
            other = _duration(row)
            if not length or not other or abs(other - length) <= 2:
                add(row)
        if length:
            second = round(length)
            for near in (second, second - 1, second + 1):
                for row in self.by_second.get(near, []):
                    if (
                        abs(_duration(row) - length) <= 1
                        and _codec(row) == codec
                    ):
                        add(row)
        return found[:MAX_CANDIDATES]


@dataclass
class CopyResult:
    file: str
    bytes: int
    status: str
    match: str = ''
    title: str = ''
    artist: str = ''
    mtime_ns: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            'file': self.file,
            'bytes': self.bytes,
            'status': self.status,
            'match': self.match,
            'title': self.title,
            'artist': self.artist,
        }


def verify_copies(
    leftovers: Sequence[dict[str, Any]],
    library: Iterable[dict[str, Any]],
    *,
    locate: Callable[[str], Optional[Path]],
    digest: Callable[[Path], Optional[str]],
    now: float,
    progress: Optional[Callable[[int, int], None]] = None,
    cancelled: Callable[[], bool] = lambda: False,
) -> list[CopyResult]:
    """Check each leftover against the library.

    ``verified`` means a library file outside slskd's folder holds
    bit-identical audio (same :func:`downtify.doctor_audio.audio_md5`) -
    the only status a cleanup acts on. Everything else is kept:
    ``different`` (look-alikes, none identical), ``unmatched`` (no
    library file looks like it), ``unreadable`` (ffmpeg couldn't read
    it), ``recent`` (changed in the last :data:`RECENT_SECONDS`) and
    ``missing`` (gone since the listing).
    """

    index = CandidateIndex(library)
    results: list[CopyResult] = []
    total = len(leftovers)
    for done, row in enumerate(leftovers):
        if cancelled():
            break
        if progress is not None:
            progress(done, total)
        name = norm(row.get('file'))
        size = int(row.get('size') or 0)
        base = CopyResult(
            name,
            size,
            STATUS_UNMATCHED,
            title=str(row.get('title') or ''),
            artist=str(row.get('artist') or ''),
        )
        path = locate(name)
        if path is None:
            base.status = STATUS_MISSING
            results.append(base)
            continue
        try:
            stat = path.stat()
        except OSError:
            base.status = STATUS_MISSING
            results.append(base)
            continue
        base.bytes = stat.st_size
        base.mtime_ns = stat.st_mtime_ns
        if now - stat.st_mtime < RECENT_SECONDS:
            base.status = STATUS_RECENT
            results.append(base)
            continue
        candidates = index.candidates(row)
        if not candidates:
            results.append(base)
            continue
        own = digest(path)
        if own is None:
            base.status = STATUS_UNREADABLE
            results.append(base)
            continue
        base.status = STATUS_DIFFERENT
        for candidate in candidates:
            other = locate(norm(candidate.get('file')))
            if other is None or other == path:
                continue
            if digest(other) == own:
                base.status = STATUS_VERIFIED
                base.match = norm(candidate.get('file'))
                break
        results.append(base)
    if progress is not None:
        progress(len(results), total)
    return results


def summarize_copies(results: Iterable[CopyResult]) -> dict[str, Any]:
    """``{status: {files, bytes}}`` for every status."""

    out: dict[str, dict[str, int]] = {}
    for result in results:
        bucket = out.setdefault(result.status, {'files': 0, 'bytes': 0})
        bucket['files'] += 1
        bucket['bytes'] += result.bytes
    return out


#: Files of each kind the slskd folder breakdown lists by name.
FOLDER_EXAMPLES = 25
#: Kinds of file in slskd's folder (:func:`slskd_folder_breakdown`).
FOLDER_LIBRARY = 'library'
FOLDER_LEFTOVER = 'leftover'
FOLDER_UNLISTED = 'unlisted_audio'
FOLDER_OTHER = 'other'
FOLDER_KINDS = (FOLDER_LIBRARY, FOLDER_LEFTOVER, FOLDER_UNLISTED, FOLDER_OTHER)


def slskd_folder_breakdown(
    files: Iterable[tuple[str, int]],
    *,
    library: Collection[str],
    leftovers: Collection[str],
    audio_extensions: Collection[str],
    examples: int = FOLDER_EXAMPLES,
) -> dict[str, Any]:
    """What slskd's folder holds, next to what Downtify counts.

    *files* are ``(stored path, size)`` for every file on disk under
    slskd's folder (``slskd/...``). Each is a library song (in
    *library*), a leftover the slskd check looks at (in *leftovers*),
    audio Downtify's listing doesn't know (never imported, or kept after
    a failed import), or another kind of file (covers, lyrics, slskd's
    own files). Library and leftovers are what the storage page counts;
    the other two explain why the folder looks bigger on disk.
    """

    audio = {e.lower().lstrip('.') for e in audio_extensions}
    lib = {norm(f) for f in library}
    left = {norm(f) for f in leftovers}
    totals = {kind: {'files': 0, 'bytes': 0} for kind in FOLDER_KINDS}
    by_ext: dict[str, dict[str, int]] = defaultdict(
        lambda: {'files': 0, 'bytes': 0}
    )
    listed: dict[str, list[tuple[int, str]]] = {
        FOLDER_UNLISTED: [],
        FOLDER_OTHER: [],
    }
    for raw, raw_size in files:
        name = norm(raw)
        size = max(0, int(raw_size or 0))
        ext = PurePosixPath(name).suffix.lstrip('.').lower()
        if name in lib:
            kind = FOLDER_LIBRARY
        elif name in left:
            kind = FOLDER_LEFTOVER
        elif ext in audio:
            kind = FOLDER_UNLISTED
        else:
            kind = FOLDER_OTHER
            bucket = by_ext[ext or '']
            bucket['files'] += 1
            bucket['bytes'] += size
        totals[kind]['files'] += 1
        totals[kind]['bytes'] += size
        if kind in listed:
            listed[kind].append((size, name))
    return {
        'total': {
            'files': sum(t['files'] for t in totals.values()),
            'bytes': sum(t['bytes'] for t in totals.values()),
        },
        'kinds': totals,
        'other_by_extension': sorted(
            ({'extension': ext, **row} for ext, row in by_ext.items()),
            key=lambda row: (-row['bytes'], row['extension']),
        )[:10],
        'examples': {
            kind: [
                {'file': name, 'bytes': size}
                for size, name in sorted(rows, key=lambda r: (-r[0], r[1]))[
                    :examples
                ]
            ]
            for kind, rows in listed.items()
        },
    }


def prune_empty_dirs(start: Path, stop: Path) -> int:
    """Remove *start* and its empty parents, never *stop* or above."""

    removed = 0
    stop = stop.resolve()
    current = start.resolve()
    while current != stop and stop in current.parents:
        try:
            current.rmdir()
        except OSError:
            break
        removed += 1
        current = current.parent
    return removed


# ---------------------------------------------------------------------------
# Playlists
# ---------------------------------------------------------------------------


@dataclass
class M3UInfo:
    """One M3U file in Downtify's folder."""

    path: str  # relative to the downloads folder, POSIX
    name: str
    manual: bool
    entries: list[str]  # library paths of the songs that exist
    lines: int  # every track line, found or not
    cover: bool
    expected: bool  # where Downtify writes this playlist today

    def as_dict(self) -> dict[str, Any]:
        return {
            'path': self.path,
            'name': self.name,
            'manual': self.manual,
            'songs': len(self.entries),
            'lines': self.lines,
            'cover': self.cover,
            'expected': self.expected,
        }


def overlap(small: Collection[str], large: Collection[str]) -> float:
    """Share of *small* that is also in *large* (1.0 for an empty one)."""

    if not small:
        return 1.0
    big = set(large)
    return sum(1 for item in small if item in big) / len(small)


@dataclass
class PlaylistGroup:
    """M3U files that hold one playlist."""

    key: str
    members: list[M3UInfo]
    reason: str  # 'name' or 'songs'
    keeper: M3UInfo = field(init=False)
    largest: M3UInfo = field(init=False)

    def __post_init__(self) -> None:
        self.largest = max(
            self.members, key=lambda m: (len(m.entries), m.cover)
        )
        expected = [m for m in self.members if m.expected]
        self.keeper = expected[0] if expected else self.largest

    def merged(self) -> list[str]:
        """Every song of every member, the largest member's order first."""

        order = [
            self.largest,
            *[m for m in self.members if m is not self.largest],
        ]
        seen: set[str] = set()
        out: list[str] = []
        for member in order:
            for entry in member.entries:
                if entry not in seen:
                    seen.add(entry)
                    out.append(entry)
        return out

    def min_overlap(self) -> float:
        """The worst overlap of a member with the largest one."""

        return min(
            (
                overlap(m.entries, self.largest.entries)
                for m in self.members
                if m is not self.largest
            ),
            default=1.0,
        )

    def safe(self) -> bool:
        return self.min_overlap() >= MIN_OVERLAP

    def as_dict(self) -> dict[str, Any]:
        cover_from = (
            self.keeper.path
            if self.keeper.cover
            else next((m.path for m in self.members if m.cover), '')
        )
        return {
            'id': self.key,
            'reason': self.reason,
            'members': [m.as_dict() for m in self.members],
            'keeper': self.keeper.path,
            'songs_after': len(self.merged()),
            'cover_from': cover_from,
            'overlap': round(self.min_overlap(), 3),
            'safe': self.safe(),
        }


def name_key(name: str) -> str:
    """:func:`playlist_key` without spaces: a name and the file name
    written for it compare equal however their punctuation was dropped
    (``DAMNN...its already 3am🥵`` and ``DAMNNits already 3am``,
    ``Rajju patel's playlist`` and ``Rajju patels playlist``)."""

    return playlist_key(name).replace(' ', '')


def same_songs(a: Collection[str], b: Collection[str]) -> bool:
    """Whether two playlists hold nearly the same songs: at least
    :data:`MIN_OVERLAP` of *each* one is in the other, and at least 5.

    Both ways, not just the smaller one: a 50-song mix is almost all
    inside a 7,000-song liked-songs backup, but they aren't one
    playlist.
    """

    first, second = set(a), set(b)
    if min(len(first), len(second)) < 5:
        return False
    shared = len(first & second)
    return shared >= MIN_OVERLAP * len(first) and shared >= MIN_OVERLAP * len(
        second
    )


def m3u_duplicate_groups(infos: Sequence[M3UInfo]) -> list[PlaylistGroup]:
    """M3U files that look like one playlist.

    Same name (:func:`name_key`) groups them; so does holding nearly
    the same songs under different names (:func:`same_songs`) - a
    playlist renamed on Spotify. A playlist joins a songs group only
    when it holds nearly the same songs as *every* playlist already in
    it, so one huge playlist can't chain unrelated ones together.
    Playlists you created in the Library are left out: they are yours,
    not a sync's.
    """

    auto = [m for m in infos if not m.manual and m.entries]
    by_name: dict[str, list[M3UInfo]] = defaultdict(list)
    for info in auto:
        by_name[name_key(info.name)].append(info)
    groups: list[PlaylistGroup] = []
    placed: set[str] = set()
    for members in by_name.values():
        if len(members) > 1:
            groups.append(_group(members, 'name'))
            placed.update(m.path for m in members)
    rest = sorted(
        (m for m in auto if m.path not in placed),
        key=lambda m: (-len(m.entries), m.path),
    )
    for i, first in enumerate(rest):
        if first.path in placed:
            continue
        members = [first]
        for second in rest[i + 1 :]:
            if second.path in placed:
                continue
            if all(same_songs(m.entries, second.entries) for m in members):
                members.append(second)
        if len(members) > 1:
            groups.append(_group(members, 'songs'))
            placed.update(m.path for m in members)
    groups.sort(key=lambda g: g.key)
    return groups


def _group(members: list[M3UInfo], reason: str) -> PlaylistGroup:
    members = sorted(members, key=lambda m: m.path)
    return PlaylistGroup('m3u:' + members[0].path, members, reason)


def parse_extinf(extinf: str) -> dict[str, Any]:
    """``{duration, artist, title}`` from an ``#EXTINF`` line."""

    text = str(extinf or '').strip()
    if not text.startswith('#EXTINF'):
        return {}
    head, _sep, label = text.partition(',')
    try:
        duration = int(head.split(':', 1)[1])
    except (IndexError, ValueError):
        duration = -1
    artist, sep, title = label.partition(' - ')
    if not sep:
        artist, title = '', label
    return {
        'duration': duration if duration >= 0 else None,
        'artist': artist.strip(),
        'title': title.strip(),
    }


def merge_m3u_files(
    members: Sequence[Path],
    keeper: Path,
    *,
    download_dir: Path,
    slskd_dir: Optional[Path],
    extra_dirs: Sequence[Path],
    backup_dir: Path,
) -> dict[str, Any]:
    """Merge *members* into *keeper*: every song once, largest first.

    Every member and its cover are copied to *backup_dir* (keeping their
    path under the downloads folder) before anything changes. The keeper
    is written atomically, gets the first cover found if it has none,
    and the other members and their covers are removed.
    """

    entries_by_member = {
        member: read_m3u_entries(member, download_dir, slskd_dir, extra_dirs)
        for member in members
    }
    order = sorted(members, key=lambda m: -len(entries_by_member[m]))
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for member in order:
        for stored, extinf in entries_by_member[member]:
            if stored in seen:
                continue
            seen.add(stored)
            merged.append({'filename': stored, **parse_extinf(extinf)})

    root = Path(download_dir)
    for member in members:
        for path in (member, member.with_suffix('.jpg')):
            if not path.is_file():
                continue
            target = backup_dir / path.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)

    content, kept = build_m3u_content(
        merged,
        download_dir=root,
        m3u_dir=keeper.parent,
        slskd_dir=slskd_dir,
        extra_dirs=extra_dirs,
    )
    keeper.parent.mkdir(parents=True, exist_ok=True)
    temp = keeper.with_name(keeper.name + '.doctor.tmp')
    temp.write_text(content, encoding='utf-8')
    os.replace(temp, keeper)

    cover = keeper.with_suffix('.jpg')
    cover_from = ''
    if not cover.is_file():
        for member in order:
            candidate = member.with_suffix('.jpg')
            if candidate.is_file():
                shutil.copy2(candidate, cover)
                cover_from = candidate.relative_to(root).as_posix()
                break
    removed: list[str] = []
    for member in members:
        if member == keeper:
            continue
        for path in (member, member.with_suffix('.jpg')):
            if path.is_file() and path != cover:
                path.unlink()
                removed.append(path.relative_to(root).as_posix())
    return {
        'keeper': keeper.relative_to(root).as_posix(),
        'songs': kept,
        'removed': removed,
        'cover_from': cover_from,
    }


# ---------------------------------------------------------------------------
# Navidrome
# ---------------------------------------------------------------------------


def navidrome_root(
    playlists: Iterable[dict[str, Any]], m3u_paths: Collection[str]
) -> str:
    """Where Navidrome sees Downtify's downloads folder.

    Found from imported playlists whose path ends with an M3U Downtify
    has: ``/music/Road Trip/Road Trip.m3u`` and ``Road Trip/Road
    Trip.m3u`` put it at ``/music/``. ``''`` when no path says.
    """

    votes: dict[str, int] = defaultdict(int)
    known = set(m3u_paths)
    for playlist in playlists:
        path = norm(playlist.get('path'))
        if not path.startswith('/'):
            continue
        for rel in known:
            if path.endswith('/' + rel):
                votes[path[: len(path) - len(rel)]] += 1
    if not votes:
        return ''
    return max(votes.items(), key=lambda item: (item[1], len(item[0])))[0]


def navidrome_playlist_findings(
    playlists: Sequence[dict[str, Any]],
    m3us: Sequence[M3UInfo],
    *,
    root: str,
) -> dict[str, Any]:
    """What a Navidrome client sees wrong in the playlists.

    * ``duplicates`` - two or more playlists one name folds to
      (:func:`playlist_key`), with why: an imported M3U *and* Downtify's
      own playlist (``m3u_and_api``), several imports (``imports``), or
      several of Downtify's (``api``).
    * ``orphans`` - imported playlists whose M3U is no longer in
      Downtify's folder. Navidrome keeps those forever.
    * ``incomplete`` - imported playlists with fewer songs than their
      M3U lists; ``outside`` counts the songs in slskd's folder or an
      extra folder, which Navidrome can't see unless its library covers
      them.
    """

    by_path = {m.path: m for m in m3us}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for playlist in playlists:
        groups[playlist_key(str(playlist.get('name') or ''))].append(playlist)

    duplicates: list[dict[str, Any]] = []
    for key, members in sorted(groups.items()):
        if len(members) < 2 or not key:
            continue
        imported = [p for p in members if imported_from(p)]
        ours = [p for p in members if made_by_downtify(p)]
        if imported and ours:
            reason = 'm3u_and_api'
        elif len(imported) > 1:
            reason = 'imports'
        elif len(ours) > 1:
            reason = 'api'
        else:
            reason = 'name'
        duplicates.append({
            'id': 'nd:' + key,
            'name': str(members[0].get('name') or ''),
            'reason': reason,
            'members': [_nd_row(p, root, by_path) for p in members],
        })

    orphans: list[dict[str, Any]] = []
    incomplete: list[dict[str, Any]] = []
    for playlist in playlists:
        source = imported_from(playlist)
        if not source:
            continue
        rel = _relative_to_root(source, root)
        if rel is None:
            continue
        info = by_path.get(rel)
        if info is None:
            orphans.append(_nd_row(playlist, root, by_path))
            continue
        songs = int(playlist.get('songCount') or 0)
        if songs < len(info.entries):
            outside = sum(
                1
                for entry in info.entries
                if entry.startswith(SLSKD_LIBRARY_PREFIX)
                or entry.startswith('ext/')
            )
            incomplete.append({
                **_nd_row(playlist, root, by_path),
                'missing': len(info.entries) - songs,
                'outside': outside,
            })
    return {
        'duplicates': duplicates,
        'orphans': orphans,
        'incomplete': incomplete,
    }


def _relative_to_root(path: str, root: str) -> Optional[str]:
    if not root or not path.startswith(root):
        return None
    return path[len(root) :]


def _nd_row(
    playlist: dict[str, Any], root: str, by_path: dict[str, M3UInfo]
) -> dict[str, Any]:
    source = imported_from(playlist)
    rel = _relative_to_root(source, root) if source else None
    info = by_path.get(rel or '') if rel else None
    return {
        'id': str(playlist.get('id') or ''),
        'name': str(playlist.get('name') or ''),
        'songs': int(playlist.get('songCount') or 0),
        'owner': str(playlist.get('owner') or playlist.get('ownerName') or ''),
        'kind': 'import'
        if source
        else ('downtify' if made_by_downtify(playlist) else 'other'),
        'm3u': rel or '',
        'm3u_exists': info is not None,
        'm3u_songs': len(info.entries) if info else None,
    }


def navidrome_song_duplicates(
    songs: Iterable[dict[str, Any]], *, limit: int = 50
) -> dict[str, Any]:
    """Songs Navidrome lists more than once: same artist and title
    (:func:`downtify.library_catalog.song_key`), lengths within
    :data:`DURATION_TOLERANCE`. ``slskd`` counts copies whose path is in a
    folder named ``slskd``."""

    by_song: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for song in songs:
        key = song_key(
            str(song.get('artist') or ''), str(song.get('title') or '')
        )
        if key != '|':
            by_song[key].append(song)
    groups: list[dict[str, Any]] = []
    for rows in by_song.values():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda r: float(r.get('duration') or 0))
        run: list[dict[str, Any]] = []
        for row in [*rows, None]:
            length = float(row.get('duration') or 0) if row else None
            if run and (
                row is None
                or not length
                or length - float(run[-1].get('duration') or 0)
                > DURATION_TOLERANCE
            ):
                if len(run) > 1:
                    groups.append(_song_group(run))
                run = []
            if row is not None and length:
                run.append(row)
    groups.sort(key=lambda g: (-len(g['copies']), g['artist'], g['title']))
    return {
        'groups': len(groups),
        'extra_copies': sum(len(g['copies']) - 1 for g in groups),
        'slskd_copies': sum(g['slskd'] for g in groups),
        'examples': groups[:limit],
    }


def _song_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = rows[0]
    paths = [norm(r.get('path')) for r in rows]
    return {
        'artist': str(first.get('artist') or ''),
        'title': str(first.get('title') or ''),
        'copies': paths,
        'slskd': sum(1 for p in paths if '/slskd/' in f'/{p}'.casefold()),
    }


# ---------------------------------------------------------------------------
# Monitored playlists: the same song under a new Spotify id
# ---------------------------------------------------------------------------


def relinked_tracks(
    rows: Iterable[dict[str, Any]],
    playlists: dict[int, str],
    listing: dict[str, dict[str, Any]],
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """Watches holding one song under two or more Spotify ids, in two
    or more files.

    Spotify replaces a playlist's track with another id now and then (a
    re-release, a region swap). Downtify remembers a watch's tracks by
    id, so the replacement looks new and, unless the library already
    has a file *for that id*, is downloaded again - a duplicate nobody
    added. *rows* are ``downloaded_tracks`` rows (``playlist_id``,
    ``track_spotify_id``, ``filename``); *listing* maps a library path
    to its listing row (artist/title).
    """

    by_watch: dict[int, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    ids: dict[tuple[int, str], set[str]] = defaultdict(set)
    for row in rows:
        name = norm(row.get('filename'))
        entry = listing.get(name)
        if not entry:
            continue
        key = song_key(
            str(entry.get('artist') or ''), str(entry.get('title') or '')
        )
        if key == '|':
            continue
        watch = int(row.get('playlist_id') or 0)
        by_watch[watch][key].add(name)
        ids[(watch, key)].add(str(row.get('track_spotify_id') or ''))
    found: list[dict[str, Any]] = []
    for watch, songs in by_watch.items():
        for key, files in songs.items():
            if len(files) > 1 and len(ids[(watch, key)]) > 1:
                entry = listing[sorted(files)[0]]
                found.append({
                    'playlist': playlists.get(watch, ''),
                    'artist': str(entry.get('artist') or ''),
                    'title': str(entry.get('title') or ''),
                    'files': sorted(files),
                    'spotify_ids': sorted(ids[(watch, key)]),
                })
    found.sort(key=lambda f: (f['playlist'], f['artist'], f['title']))
    per_playlist: dict[str, int] = defaultdict(int)
    for item in found:
        per_playlist[item['playlist']] += len(item['files']) - 1
    return {
        'songs': len(found),
        'extra_files': sum(len(f['files']) - 1 for f in found),
        'playlists': dict(sorted(per_playlist.items())),
        'examples': found[:limit],
    }
