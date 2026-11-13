from pathlib import Path
from typing import Any, Optional

import pytest

from downtify import navidrome
from downtify.doctor import (
    STATUS_DIFFERENT,
    STATUS_MISSING,
    STATUS_RECENT,
    STATUS_UNMATCHED,
    STATUS_VERIFIED,
    M3UInfo,
    m3u_duplicate_groups,
    merge_m3u_files,
    navidrome_playlist_findings,
    navidrome_root,
    navidrome_song_duplicates,
    parse_extinf,
    relinked_tracks,
    summarize_copies,
    verify_copies,
    working_copy_rows,
)
from downtify.playlist_identity import (
    DOWNTIFY_COMMENT,
    imported_from,
    playlist_key,
)

NOW = 1_000_000.0


def _row(file: str, artist: str, title: str, duration: float, **extra):
    return {
        'file': file,
        'artist': artist,
        'title': title,
        'duration': duration,
        'size': 1000,
        **extra,
    }


# --- names -----------------------------------------------------------------


def test_playlist_key_matches_the_m3u_file_name():
    assert playlist_key('Chill: Vibes') == playlist_key('Chill Vibes')
    assert playlist_key('Café Mix') == playlist_key('cafe mix')
    assert playlist_key('Road Trip') != playlist_key('Road Trip 2')


def test_imported_from_reads_path_or_comment():
    assert imported_from({'path': '/music/A/A.m3u', 'sync': True}) == (
        '/music/A/A.m3u'
    )
    assert imported_from({'comment': "Auto-imported from 'A.m3u'"}) == 'A.m3u'
    assert not imported_from({'comment': DOWNTIFY_COMMENT})


# --- slskd leftovers -------------------------------------------------------


def test_working_copy_rows_keeps_referenced_slskd_files_in_the_library():
    rows = [
        _row('slskd/A/one.mp3', 'A', 'One', 200),
        _row('slskd/A/two.mp3', 'A', 'Two', 180),
        _row('Mix/A - One.mp3', 'A', 'One', 200),
    ]

    library, leftovers = working_copy_rows(
        rows,
        sources={},
        slskd_in_place=False,
        referenced={'slskd/A/two.mp3'},
    )

    assert [r['file'] for r in leftovers] == ['slskd/A/one.mp3']
    assert {r['file'] for r in library} == {
        'slskd/A/two.mp3',
        'Mix/A - One.mp3',
    }


def test_working_copy_rows_with_files_left_in_place_has_no_leftovers():
    rows = [_row('slskd/A/one.mp3', 'A', 'One', 200)]

    _library, leftovers = working_copy_rows(
        rows, sources={}, slskd_in_place=True, referenced=set()
    )

    assert leftovers == []


class _FakeFile:
    def __init__(self, size: int, mtime: float) -> None:
        self.st_size = size
        self.st_mtime = mtime
        self.st_mtime_ns = int(mtime * 1e9)


class _FakePath:
    def __init__(self, name: str, size: int = 1000, mtime: float = 0.0):
        self.name = name
        self._stat = _FakeFile(size, mtime)

    def stat(self):
        return self._stat

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _FakePath) and other.name == self.name

    def __hash__(self) -> int:
        return hash(self.name)


def _verify(leftovers, library, files, digests, now=NOW):
    def locate(stored: str) -> Optional[Any]:
        return files.get(stored)

    return {
        r.file: r
        for r in verify_copies(
            leftovers,
            library,
            locate=locate,
            digest=lambda p: digests.get(p.name),
            now=now,
        )
    }


def test_verify_copies_needs_identical_audio_in_the_library():
    leftovers = [
        _row('slskd/same.mp3', 'Band', 'Song', 200),
        _row('slskd/other.mp3', 'Band', 'Song', 200),
        _row('slskd/nothing.mp3', 'Nobody', 'Nothing', 50),
    ]
    library = [_row('Mix/Band - Song.mp3', 'Band', 'Song', 200.4)]
    files = {
        'slskd/same.mp3': _FakePath('a'),
        'slskd/other.mp3': _FakePath('b'),
        'slskd/nothing.mp3': _FakePath('c'),
        'Mix/Band - Song.mp3': _FakePath('lib'),
    }
    digests = {'a': 'x' * 32, 'b': 'y' * 32, 'c': 'z' * 32, 'lib': 'x' * 32}

    out = _verify(leftovers, library, files, digests)

    assert out['slskd/same.mp3'].status == STATUS_VERIFIED
    assert out['slskd/same.mp3'].match == 'Mix/Band - Song.mp3'
    assert out['slskd/other.mp3'].status == STATUS_DIFFERENT
    assert out['slskd/nothing.mp3'].status == STATUS_UNMATCHED


def test_verify_copies_matches_by_length_and_format_when_tags_differ():
    leftovers = [_row('slskd/01 track.mp3', '', '', 241.2)]
    library = [_row('Mix/Real Artist - Real Title.mp3', 'R', 'T', 241.0)]
    files = {
        'slskd/01 track.mp3': _FakePath('a'),
        'Mix/Real Artist - Real Title.mp3': _FakePath('lib'),
    }

    out = _verify(leftovers, library, files, {'a': 'h' * 32, 'lib': 'h' * 32})

    assert out['slskd/01 track.mp3'].status == STATUS_VERIFIED


def test_verify_copies_skips_recent_and_missing_files():
    leftovers = [
        _row('slskd/new.mp3', 'Band', 'Song', 200),
        _row('slskd/gone.mp3', 'Band', 'Song', 200),
    ]
    library = [_row('Mix/Band - Song.mp3', 'Band', 'Song', 200)]
    files = {
        'slskd/new.mp3': _FakePath('a', mtime=NOW - 60),
        'Mix/Band - Song.mp3': _FakePath('lib'),
    }

    out = _verify(leftovers, library, files, {'a': 'h' * 32, 'lib': 'h' * 32})

    assert out['slskd/new.mp3'].status == STATUS_RECENT
    assert out['slskd/gone.mp3'].status == STATUS_MISSING
    summary = summarize_copies(out.values())
    assert summary[STATUS_RECENT] == {'files': 1, 'bytes': 1000}


def test_verify_copies_never_matches_another_slskd_file():
    leftovers = [_row('slskd/a.mp3', 'Band', 'Song', 200)]
    library = [_row('slskd/b.mp3', 'Band', 'Song', 200)]
    files = {'slskd/a.mp3': _FakePath('a'), 'slskd/b.mp3': _FakePath('b')}

    out = _verify(leftovers, library, files, {'a': 'h' * 32, 'b': 'h' * 32})

    assert out['slskd/a.mp3'].status == STATUS_UNMATCHED


# --- playlists -------------------------------------------------------------


def _m3u(path: str, entries: list[str], **extra) -> M3UInfo:
    return M3UInfo(
        path=path,
        name=Path(path).stem,
        manual=extra.get('manual', False),
        entries=entries,
        lines=len(entries),
        cover=extra.get('cover', False),
        expected=extra.get('expected', False),
    )


def test_m3u_groups_join_same_name_in_two_places():
    full = [f'Road Trip/{i}.mp3' for i in range(10)]
    current = _m3u(
        'Road Trip/Road Trip.m3u', full[:6], cover=True, expected=True
    )
    old = _m3u('Playlists/Road Trip.m3u', full)

    (group,) = m3u_duplicate_groups([current, old])

    assert group.reason == 'name'
    assert group.keeper is current
    assert group.largest is old
    assert group.safe()
    assert group.merged() == full
    assert group.as_dict()['cover_from'] == 'Road Trip/Road Trip.m3u'


def test_m3u_groups_find_a_renamed_playlist_by_its_songs():
    songs = [f'x/{i}.mp3' for i in range(10)]
    first = _m3u('Gym/Gym.m3u', songs)
    renamed = _m3u('Gym 2024/Gym 2024.m3u', [*songs[:9], 'x/new.mp3'])

    (group,) = m3u_duplicate_groups([first, renamed])

    assert group.reason == 'songs'
    assert group.min_overlap() == 0.9


def test_m3u_groups_leave_unrelated_and_manual_playlists_alone():
    a = _m3u('A/A.m3u', [f'a/{i}.mp3' for i in range(8)])
    b = _m3u('B/B.m3u', [f'b/{i}.mp3' for i in range(8)])
    mine = _m3u(
        'Playlists/A.m3u', [f'a/{i}.mp3' for i in range(8)], manual=True
    )

    assert m3u_duplicate_groups([a, b, mine]) == []


def test_same_name_group_with_different_songs_is_not_safe():
    a = _m3u('A/Mix.m3u', [f'a/{i}.mp3' for i in range(10)])
    b = _m3u('Playlists/Mix.m3u', [f'b/{i}.mp3' for i in range(10)])

    (group,) = m3u_duplicate_groups([a, b])

    assert not group.safe()
    assert group.as_dict()['safe'] is False


def test_parse_extinf():
    assert parse_extinf('#EXTINF:215,Band A - Song (Live)') == {
        'duration': 215,
        'artist': 'Band A',
        'title': 'Song (Live)',
    }
    assert not parse_extinf('#EXTINF:-1,Just A Title')['artist']
    assert parse_extinf('') == {}


def test_merge_m3u_files_keeps_every_song_the_cover_and_a_backup(tmp_path):
    root = tmp_path / 'downloads'
    folder = root / 'Road Trip'
    folder.mkdir(parents=True)
    for name in ('One', 'Two', 'Three'):
        (folder / f'Band - {name}.mp3').write_bytes(b'x')
    keeper = folder / 'Road Trip.m3u'
    keeper.write_text(
        '#EXTM3U\n#EXTINF:20,Band - One\nBand - One.mp3\n', encoding='utf-8'
    )
    old = root / 'Playlists' / 'Road Trip.m3u'
    old.parent.mkdir()
    old.write_text(
        '#EXTM3U\n'
        '../Road Trip/Band - One.mp3\n'
        '#EXTINF:21,Band - Two\n../Road Trip/Band - Two.mp3\n'
        '../Road Trip/Band - Three.mp3\n',
        encoding='utf-8',
    )
    old.with_suffix('.jpg').write_bytes(b'cover')
    backup = tmp_path / 'backup'

    done = merge_m3u_files(
        [keeper, old],
        keeper,
        download_dir=root,
        slskd_dir=None,
        extra_dirs=(),
        backup_dir=backup,
    )

    lines = [
        line
        for line in keeper.read_text(encoding='utf-8').splitlines()
        if not line.startswith('#')
    ]
    assert lines == ['Band - One.mp3', 'Band - Two.mp3', 'Band - Three.mp3']
    assert '#EXTINF:21,Band - Two' in keeper.read_text(encoding='utf-8')
    assert keeper.with_suffix('.jpg').read_bytes() == b'cover'
    assert not old.exists()
    assert not old.with_suffix('.jpg').exists()
    assert (backup / 'Playlists' / 'Road Trip.m3u').is_file()
    assert (backup / 'Playlists' / 'Road Trip.jpg').read_bytes() == b'cover'
    assert (backup / 'Road Trip' / 'Road Trip.m3u').is_file()
    assert done['songs'] == 3
    assert done['cover_from'] == 'Playlists/Road Trip.jpg'
    assert sorted(done['removed']) == [
        'Playlists/Road Trip.jpg',
        'Playlists/Road Trip.m3u',
    ]


# --- Navidrome -------------------------------------------------------------


def _nd(pid: str, name: str, songs: int, **extra) -> dict[str, Any]:
    return {'id': pid, 'name': name, 'songCount': songs, **extra}


def test_navidrome_root_is_found_from_imported_paths():
    playlists = [
        _nd('1', 'Road Trip', 3, path='/music/Road Trip/Road Trip.m3u')
    ]

    assert navidrome_root(playlists, ['Road Trip/Road Trip.m3u']) == '/music/'
    assert not navidrome_root(playlists, ['Other/Other.m3u'])


def test_navidrome_findings_explain_duplicates_orphans_and_gaps():
    infos = [
        _m3u(
            'Road Trip/Road Trip.m3u',
            ['Road Trip/1.mp3', 'Road Trip/2.mp3', 'slskd/x/3.mp3'],
            expected=True,
        )
    ]
    playlists = [
        _nd(
            'imp',
            'Road Trip',
            2,
            owner='admin',
            path='/music/Road Trip/Road Trip.m3u',
            sync=True,
        ),
        _nd('api', 'Road Trip', 3, owner='downtify', comment=DOWNTIFY_COMMENT),
        _nd(
            'old',
            'Road Trip',
            1,
            owner='admin',
            path='/music/Playlists/Road Trip.m3u',
            sync=True,
        ),
        _nd('mine', 'Workout', 10, owner='me'),
    ]

    out = navidrome_playlist_findings(playlists, infos, root='/music/')

    (dup,) = out['duplicates']
    assert dup['reason'] == 'm3u_and_api'
    assert {m['kind'] for m in dup['members']} == {'import', 'downtify'}
    assert [o['id'] for o in out['orphans']] == ['old']
    (gap,) = out['incomplete']
    assert gap['id'] == 'imp'
    assert gap['missing'] == 1
    assert gap['outside'] == 1


def test_navidrome_song_duplicates_groups_by_song_and_length():
    songs = [
        {'artist': 'A', 'title': 'Song', 'duration': 200, 'path': 'Mix/A.mp3'},
        {
            'artist': 'A',
            'title': 'Song',
            'duration': 201,
            'path': 'slskd/A/Song.mp3',
        },
        {'artist': 'A', 'title': 'Song', 'duration': 320, 'path': 'Live.mp3'},
        {'artist': 'B', 'title': 'Other', 'duration': 100, 'path': 'B.mp3'},
    ]

    out = navidrome_song_duplicates(songs)

    assert out['groups'] == 1
    assert out['extra_copies'] == 1
    assert out['slskd_copies'] == 1


# --- monitored playlists ---------------------------------------------------


def test_relinked_tracks_finds_one_song_under_two_spotify_ids():
    rows = [
        {
            'playlist_id': 1,
            'track_spotify_id': 'a' * 22,
            'filename': 'P/x.mp3',
        },
        {
            'playlist_id': 1,
            'track_spotify_id': 'b' * 22,
            'filename': 'P/y.mp3',
        },
        {
            'playlist_id': 1,
            'track_spotify_id': 'c' * 22,
            'filename': 'P/z.mp3',
        },
        {
            'playlist_id': 2,
            'track_spotify_id': 'a' * 22,
            'filename': 'P/x.mp3',
        },
    ]
    listing = {
        'P/x.mp3': {'artist': 'Band', 'title': 'Song'},
        'P/y.mp3': {'artist': 'Band', 'title': 'Song - Remastered 2011'},
        'P/z.mp3': {'artist': 'Band', 'title': 'Other'},
    }

    out = relinked_tracks(rows, {1: 'Big Playlist', 2: 'Small'}, listing)

    assert out['songs'] == 1
    assert out['extra_files'] == 1
    assert out['playlists'] == {'Big Playlist': 1}
    assert out['examples'][0]['files'] == ['P/x.mp3', 'P/y.mp3']


# --- Navidrome sync with M3U import ----------------------------------------


@pytest.fixture
def fake_navidrome(monkeypatch):
    calls: dict[str, list] = {'created': [], 'deleted': [], 'scans': []}

    monkeypatch.setattr(navidrome.NavidromeClient, 'ping', lambda self: True)
    monkeypatch.setattr(
        navidrome.NavidromeClient,
        'list_playlists',
        lambda self, admin=False: [
            _nd(
                'own', 'Chill: Vibes', 3, owner='dt', comment=DOWNTIFY_COMMENT
            ),
            _nd('user', 'Chill Vibes', 3, owner='dt', comment='mine'),
            _nd('imp', 'Chill Vibes', 3, owner='admin'),
        ],
    )
    monkeypatch.setattr(
        navidrome.NavidromeClient,
        'delete_playlist',
        lambda self, pid, admin=False: calls['deleted'].append(pid),
    )
    monkeypatch.setattr(
        navidrome.NavidromeClient,
        'create_playlist',
        lambda self, name, ids: calls['created'].append(name) or 'new',
    )
    monkeypatch.setattr(
        navidrome,
        '_trigger_library_scan',
        lambda client, cfg, count: calls['scans'].append(count) or True,
    )
    return calls


def _settings(**navidrome_extra):
    return {
        'generate_m3u': True,
        'navidrome': {
            'enabled': True,
            'url': 'http://nd.invalid',
            'username': 'dt',
            'password': 'pw',
            **navidrome_extra,
        },
    }


def test_sync_with_m3u_import_creates_nothing_and_removes_its_own_copy(
    fake_navidrome,
):
    result = navidrome.sync_playlist_to_navidrome(
        'Chill Vibes',
        [{'name': 'Song', 'artists': ['A'], 'filename': 'x.mp3'}],
        _settings(m3u_import=True),
    )

    assert result is not None
    assert not result.playlist_id
    assert fake_navidrome['created'] == []
    assert fake_navidrome['deleted'] == ['own']
    assert fake_navidrome['scans'] == [1]


def test_m3u_import_is_off_by_default():
    cfg = navidrome._effective_navidrome_settings(_settings())
    assert cfg['m3u_import'] is False
