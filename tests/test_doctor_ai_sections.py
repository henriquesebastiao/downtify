"""The AI helper's tools for duplicate songs, slskd leftovers, Navidrome
and new-Spotify-id repeats (downtify/doctor_ai_sections.py)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from downtify import api, doctor_ai, doctor_ai_sections, doctor_routes
from downtify.doctor import CopyResult, M3UInfo

ORIGINAL = 'The Weeknd/After Hours/The Weeknd - Blinding Lights.mp3'
COPY = 'The Weeknd/Singles/The Weeknd - Blinding Lights.mp3'
REMIX = 'The Weeknd/Remixes/The Weeknd - Blinding Lights (Remix).mp3'
OTHER = 'Drake/Views/Drake - One Dance.mp3'


def _entry(file, title, seconds, size=5_000_000, **extra):
    return {
        'file': file,
        'artist': 'The Weeknd' if 'Weeknd' in file else 'Drake',
        'title': title,
        'album': extra.get('album', ''),
        'duration': seconds,
        'size': size,
        'codec': 'mp3',
        'bitrate': extra.get('bitrate', 320_000),
    }


ENTRIES = [
    _entry(ORIGINAL, 'Blinding Lights', 200.0, album='After Hours'),
    _entry(COPY, 'Blinding Lights', 200.5, size=3_000_000, bitrate=128_000),
    _entry(REMIX, 'Blinding Lights (Remix)', 258.0),
    _entry(OTHER, 'One Dance', 173.0),
]
GROUP = {
    'kind': 'likely',
    'artist': 'The Weeknd',
    'title': 'Blinding Lights',
    'bytes': 3_000_000,
    'files': [
        {
            'file': ORIGINAL,
            'bytes': 5_000_000,
            'provider': 'slskd',
            'codec': 'mp3',
            'bitrate': 320_000,
            'title': 'Blinding Lights',
            'artist': 'The Weeknd',
            'album': 'After Hours',
            'duration': 200.0,
            'playlists': ['Road Trip'],
        },
        {
            'file': COPY,
            'bytes': 3_000_000,
            'provider': 'youtube',
            'codec': 'mp3',
            'bitrate': 128_000,
            'title': 'Blinding Lights',
            'artist': 'The Weeknd',
            'album': '',
            'duration': 200.5,
            'playlists': [],
        },
    ],
}
ND = {
    'enabled': True,
    'reachable': True,
    'admin': True,
    'm3u_import': False,
    'playlists': 3,
    'songs': 4,
    'duplicates': [
        {
            'id': 'nd:road trip',
            'name': 'Road Trip',
            'reason': 'm3u_and_api',
            'members': [
                {
                    'id': 'imp1',
                    'name': 'Road Trip',
                    'songs': 10,
                    'kind': 'import',
                    'm3u': 'Road Trip/Road Trip.m3u',
                    'm3u_exists': True,
                },
                {
                    'id': 'api1',
                    'name': 'Road Trip',
                    'songs': 9,
                    'kind': 'downtify',
                    'm3u': '',
                    'm3u_exists': False,
                },
            ],
        }
    ],
    'orphans': [
        {
            'id': 'gone1',
            'name': 'Old Mix',
            'songs': 4,
            'kind': 'import',
            'm3u': 'Old/Old.m3u',
            'm3u_exists': False,
        }
    ],
    'incomplete': [],
    'song_duplicates': {'groups': 0},
}


@pytest.fixture
def doctor(monkeypatch, tmp_path):
    """The Doctor after a health check, its jobs and repairs faked."""

    infos = [
        M3UInfo(
            'Road Trip/Road Trip.m3u',
            'Road Trip',
            False,
            [ORIGINAL, OTHER],
            2,
            True,
            True,
        )
    ]
    monkeypatch.setattr(doctor_routes, '_ctx', lambda: None)
    monkeypatch.setattr(doctor_routes, '_m3u_infos', lambda _ctx: infos)
    health = {
        'duplicates': {'groups': [GROUP], 'kept_apart': 0, 'trash': True},
        'navidrome': ND,
        'slskd': {'in_place': False, 'leftovers': 2},
        'playlists': {'m3u': 1, 'groups': [], 'list': []},
    }
    monkeypatch.setattr(
        doctor_routes,
        '_last',
        {'health': {'at': '2026-11-21T10:00:00+00:00', 'result': health}},
    )
    monkeypatch.setattr(doctor_routes, '_stale', set())
    monkeypatch.setattr(doctor_routes, '_job', {})
    monkeypatch.setattr(
        doctor_routes,
        '_state',
        {
            'duplicates': {ORIGINAL: 0, COPY: 0},
            'flagged': {'api1', 'gone1'},
            'copies': {
                'slskd/a.mp3': CopyResult(
                    'slskd/a.mp3', 4_000_000, 'verified', ORIGINAL
                ),
                'slskd/b.mp3': CopyResult(
                    'slskd/b.mp3', 2_000_000, 'different', OTHER
                ),
            },
        },
    )
    monkeypatch.setattr(
        api,
        '_usage_library_inputs',
        lambda _ctx: {'entries': ENTRIES, 'providers': {ORIGINAL: 'slskd'}},
    )
    monkeypatch.setattr(api, 'library_context', lambda: None)
    monkeypatch.setattr(api.state, 'library_trash', object())
    monkeypatch.setattr(
        doctor_ai_sections, 'plan_merge', lambda keep, extras, ctx: None
    )
    files = {}
    for entry in ENTRIES:
        path = tmp_path / entry['file']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'audio-' + entry['title'].encode())
        files[entry['file']] = path
    monkeypatch.setattr(doctor_ai_sections, '_full_path', files.get)
    monkeypatch.setattr(doctor_ai, 'WAIT_IDLE', 5)

    calls: dict[str, list[Any]] = {
        'dedupe': [],
        'keep': [],
        'slskd': [],
        'nd': [],
    }
    counter = iter(range(1, 100))

    def start_job(kind):
        job = {
            'id': f'{kind}{next(counter)}',
            'kind': kind,
            'state': 'running',
        }
        doctor_routes._job.clear()
        doctor_routes._job.update(job)
        return dict(job)

    def start_dedupe(payload, user_id, *, grouped=True):
        calls['dedupe'].append((
            payload.keep,
            payload.remove,
            user_id,
            grouped,
        ))
        return start_job('dedupe')

    async def duplicates_keep(payload):
        calls['keep'].append(payload.files)
        return {'pairs': 1}

    async def slskd_clean(payload):
        calls['slskd'].append(payload.files)
        return start_job('slskd_clean')

    async def navidrome_repair(payload):
        calls['nd'].append((payload.delete, payload.enable_m3u_import))
        return start_job('navidrome')

    monkeypatch.setattr(doctor_routes, 'start_dedupe', start_dedupe)
    # The music trash knows every file (by its ISRC) unless a test says
    # otherwise.
    monkeypatch.setattr(
        doctor_ai_sections.trash_routes,
        '_selection',
        lambda payload: [
            {'stored': f, 'metadata': {'isrc': 'USUG11904206'}}
            for f in payload.files
        ],
    )
    monkeypatch.setattr(doctor_routes, 'duplicates_keep', duplicates_keep)
    monkeypatch.setattr(doctor_routes, 'slskd_clean', slskd_clean)
    monkeypatch.setattr(doctor_routes, 'navidrome_repair', navidrome_repair)
    fresh = doctor_ai.Helper()
    fresh.user_id = 7
    monkeypatch.setattr(doctor_ai, 'helper', fresh)
    monkeypatch.setattr(doctor_ai_sections, 'helper', fresh)
    return calls


def _call(name: str, **args: Any) -> dict[str, Any]:
    async def go():
        return await doctor_ai.handle({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'tools/call',
            'params': {'name': name, 'arguments': args},
        })

    return asyncio.run(go())['result']


def _data(result):
    assert result['isError'] is False, result['content'][0]['text']
    return json.loads(result['content'][0]['text'])


def _text(result):
    assert result['isError'] is True, result['content'][0]['text']
    return result['content'][0]['text']


def _states():
    return [s['state'] for s in doctor_ai.helper.status()['suggestions']]


def test_every_section_has_its_tools():
    names = {t['name'] for t in doctor_ai.TOOLS}
    assert {
        'list_duplicate_songs',
        'search_library',
        'song_details',
        'compare_audio',
        'lookup_musicbrainz',
        'suggest_keep_song',
        'suggest_different_songs',
        'list_new_spotify_id_repeats',
        'get_slskd_leftovers',
        'run_slskd_check',
        'suggest_slskd_clean',
        'get_navidrome_issues',
        'suggest_navidrome_cleanup',
    } <= names
    assert 'DUPLICATE SONGS' in doctor_ai.INSTRUCTIONS


# -- duplicate songs ------------------------------------------------------


def test_duplicate_songs_and_a_search_that_finds_the_remix(doctor):
    groups = _data(_call('list_duplicate_songs'))
    assert groups['total_groups'] == 1
    copies = groups['groups'][0]['files']
    assert [c['kbps'] for c in copies] == [320, 128]
    assert copies[0]['playlists'] == ['Road Trip']
    found = _data(_call('search_library', query='weeknd blinding'))
    assert {f['file'] for f in found['files']} == {ORIGINAL, COPY, REMIX}
    remix = next(f for f in found['files'] if f['file'] == REMIX)
    assert remix['seconds'] == 258.0


def test_song_details_and_audio_comparison(doctor, monkeypatch):
    details = _data(_call('song_details', files=[ORIGINAL, REMIX]))
    first = details['files'][0]
    assert first['exists'] is True
    assert first['playlists'] == ['Road Trip']
    assert first['kbps'] == 320

    def digest(path: Path) -> str:
        # The copy is the original's audio in another file.
        return 'B' if 'Remix' in path.read_bytes().decode() else 'A'

    monkeypatch.setattr(
        doctor_routes, '_hash_cache', lambda: SimpleNamespace(digest=digest)
    )
    same = _data(_call('compare_audio', files=[ORIGINAL, COPY, REMIX]))
    assert same['identical_audio_groups'] == [[ORIGINAL, COPY]]


def test_musicbrainz_lookup_reads_lengths_isrcs_and_release_kinds(
    doctor, monkeypatch
):
    asked = {}

    def fake_get(path, **params):
        asked.update(params, path=path)
        return {
            'recordings': [
                {
                    'title': 'Blinding Lights',
                    'length': 200040,
                    'disambiguation': '',
                    'isrcs': ['USUG11904206'],
                    'score': 100,
                    'artist-credit': [
                        {'name': 'The Weeknd', 'joinphrase': ''}
                    ],
                    'releases': [
                        {
                            'title': 'After Hours',
                            'status': 'Official',
                            'date': '2020-03-20',
                            'country': 'XW',
                            'release-group': {
                                'primary-type': 'Album',
                                'secondary-types': [],
                            },
                        }
                    ],
                },
                {
                    'title': 'Blinding Lights',
                    'length': 258000,
                    'disambiguation': 'Chromatics remix',
                    'artist-credit': [{'name': 'The Weeknd'}],
                    'releases': [],
                },
            ]
        }

    monkeypatch.setattr(doctor_ai_sections.musicbrainz, '_get', fake_get)
    data = _data(
        _call(
            'lookup_musicbrainz',
            title='Blinding "Lights"',
            artist='The Weeknd',
        )
    )
    assert asked['path'] == 'recording'
    # Quotes in the title can't break out of the search's own quotes.
    assert asked['query'] == (
        'recording:"Blinding  Lights" AND artist:"The Weeknd"'
    )
    original, remix = data['recordings']
    assert original['seconds'] == 200.0
    assert original['isrcs'] == ['USUG11904206']
    assert original['releases'][0]['status'] == 'Official'
    assert remix['disambiguation'] == 'Chromatics remix'


def test_keep_song_suggestions_and_their_checks(doctor, monkeypatch):
    # A remix the Doctor never grouped can still be folded in.
    made = _data(
        _call(
            'suggest_keep_song',
            keep=ORIGINAL,
            remove=[REMIX],
            reason='The remix is 58 s longer; you asked to keep originals.',
        )
    )
    assert made['found_by_doctor'] is False
    assert 'music trash' in made['removed_copies_go_to']
    entry = doctor_ai.helper.status()['suggestions'][0]
    assert entry['group']['kind'] == 'assistant'
    assert [f['file'] for f in entry['group']['files']] == [ORIGINAL, REMIX]
    assert entry['permanent'] is False
    # The same file can't wait in two suggestions.
    assert 'already in a waiting suggestion' in _text(
        _call('suggest_keep_song', keep=ORIGINAL, remove=[COPY], reason='x')
    )
    # "Different songs" only for what the Doctor grouped.
    assert 'did not group' in _text(
        _call('suggest_different_songs', files=[COPY, OTHER], reason='x')
    )
    # Strangers and out-of-date findings are refused.
    assert 'not a library file' in _text(
        _call('suggest_keep_song', keep=OTHER, remove=['nope.mp3'], reason='x')
    )
    monkeypatch.setattr(doctor_routes, '_stale', {'duplicates'})
    assert 'run_health_check' in _text(
        _call('suggest_keep_song', keep=OTHER, remove=[COPY], reason='x')
    )


def test_without_the_music_trash_the_card_warns_it_is_for_good(
    doctor, monkeypatch
):
    monkeypatch.setattr(api.state, 'library_trash', None)
    made = _data(
        _call('suggest_keep_song', keep=ORIGINAL, remove=[COPY], reason='x')
    )
    assert 'for good' in made['removed_copies_go_to']
    assert doctor_ai.helper.status()['suggestions'][0]['permanent'] is True
    assert made['found_by_doctor'] is True


def test_song_merges_run_one_after_the_other(doctor):
    async def scenario():
        keep = await doctor_ai.handle({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'tools/call',
            'params': {
                'name': 'suggest_keep_song',
                'arguments': {
                    'keep': ORIGINAL,
                    'remove': [COPY],
                    'reason': 'Same song, lower bitrate.',
                },
            },
        })
        assert keep['result']['isError'] is False
        doctor_ai.helper.add({
            'kind': 'songs',
            'decision': 'keep',
            'paths': [OTHER, REMIX],
            'keep': OTHER,
            'remove': [REMIX],
            'grouped': False,
            'reason': 'x',
            'group': {},
        })
        ids = [s['id'] for s in doctor_ai.helper.waiting()]
        result = await doctor_ai.apply(ids, by='page', user_id=3)
        assert result['jobs'] == 2
        # The first merge runs; the second waits its turn.
        assert _states() == ['applying', 'queued']
        assert doctor['dedupe'] == [(ORIGINAL, [COPY], 3, True)]
        doctor_routes._job['state'] = 'done'
        for _ in range(50):
            await asyncio.sleep(0.1)
            if len(doctor['dedupe']) == 2:
                break
        assert doctor['dedupe'][1] == (OTHER, [REMIX], 3, False)
        doctor_routes._job['state'] = 'done'
        for _ in range(50):
            await asyncio.sleep(0.1)
            if _states() == ['applied', 'applied']:
                break
        assert _states() == ['applied', 'applied']

    asyncio.run(scenario())


def test_different_songs_are_kept_apart_at_once(doctor):
    _data(
        _call(
            'suggest_different_songs',
            files=[ORIGINAL, COPY],
            reason='The single is a radio edit.',
        )
    )
    ids = [s['id'] for s in doctor_ai.helper.waiting()]
    result = asyncio.run(doctor_ai.apply(ids, by='page'))
    assert result['job'] is None
    assert doctor['keep'] == [[ORIGINAL, COPY]]
    assert _states() == ['applied']


def test_one_section_at_a_time(doctor):
    _data(_call('suggest_keep_song', keep=ORIGINAL, remove=[COPY], reason='x'))
    _data(_call('suggest_slskd_clean', all_verified=True, reason='x'))
    ids = [s['id'] for s in doctor_ai.helper.waiting()]
    with pytest.raises(doctor_ai.ToolError, match='one Doctor section'):
        asyncio.run(doctor_ai.apply(ids, by='page'))
    assert _states() == ['waiting', 'waiting']


def test_new_spotify_id_repeats_lists_everything(doctor, monkeypatch):
    db = SimpleNamespace(list_playlists=list, list_all_downloaded_tracks=list)
    monkeypatch.setattr(api.state, 'monitor_db', db)
    seen = {}

    def fake(rows, names, listing, limit):
        seen['limit'] = limit
        return {
            'songs': 1,
            'extra_files': 1,
            'playlists': {'Daily Mix': 1},
            'examples': [
                {'title': 'Blinding Lights', 'files': [ORIGINAL, COPY]}
            ],
        }

    monkeypatch.setattr(doctor_ai_sections, 'relinked_tracks', fake)
    data = _data(_call('list_new_spotify_id_repeats'))
    assert seen['limit'] is None  # the whole list, not the page's 50
    assert data['repeats'][0]['files'] == [ORIGINAL, COPY]


# -- slskd -----------------------------------------------------------------


def test_slskd_leftovers_only_verified_ones_are_deletable(doctor):
    data = _data(_call('get_slskd_leftovers'))
    assert data['summary']['verified'] == {'files': 1, 'bytes': 4_000_000}
    assert 'verified leftover' in _text(
        _call('suggest_slskd_clean', files=['slskd/b.mp3'], reason='x')
    )
    made = _data(
        _call(
            'suggest_slskd_clean', files=['slskd/a.mp3'], reason='Same audio.'
        )
    )
    assert made['files'] == 1
    ids = [s['id'] for s in doctor_ai.helper.waiting()]

    async def go():
        result = await doctor_ai.apply(ids, by='assistant')
        assert result['job']
        doctor_routes._job['state'] = 'done'
        await asyncio.sleep(1.5)

    asyncio.run(go())
    assert doctor['slskd'] == [['slskd/a.mp3']]
    assert _states() == ['applied']


def test_resume_downloads_releases_the_hold(doctor, monkeypatch):
    released = []

    async def release():
        released.append(True)
        doctor_routes._state.pop('hold', None)
        return {'queue': {'paused': False}}

    doctor_routes._state['hold'] = True
    monkeypatch.setattr(doctor_routes, 'slskd_release', release)
    data = _data(_call('resume_downloads'))
    assert released == [True]
    assert data['downloads_held'] is False


def test_clean_all_verified_sends_an_empty_list(doctor):
    _data(_call('suggest_slskd_clean', all_verified=True, reason='All same.'))
    ids = [s['id'] for s in doctor_ai.helper.waiting()]
    asyncio.run(doctor_ai.apply(ids, by='page'))
    assert doctor['slskd'] == [[]]


# -- Navidrome ------------------------------------------------------------


def test_navidrome_issues_and_the_page_plan(doctor):
    data = _data(_call('get_navidrome_issues'))
    assert data['deletable_ids'] == ['api1', 'gone1']
    plan = data['page_plan']
    # Downtify's copy has fewer songs than the import: it goes; the
    # import whose M3U is gone goes; M3U import gets switched on.
    assert sorted(plan['delete']) == ['api1', 'gone1']
    assert plan['enable_m3u_import'] is True


def test_navidrome_cleanup_only_flagged_playlists(doctor):
    assert 'not flagged' in _text(
        _call('suggest_navidrome_cleanup', delete=['imp1'], reason='x')
    )
    made = _data(
        _call(
            'suggest_navidrome_cleanup',
            delete=['api1', 'gone1'],
            enable_m3u_import=True,
            reason='Each playlist shows twice in Symfonium.',
        )
    )
    assert made['delete'] == 2
    entry = doctor_ai.helper.status()['suggestions'][0]
    assert [p['name'] for p in entry['playlists']] == ['Road Trip', 'Old Mix']
    ids = [s['id'] for s in doctor_ai.helper.waiting()]
    asyncio.run(doctor_ai.apply(ids, by='page'))
    assert doctor['nd'] == [(['api1', 'gone1'], True)]


def _trash_lookup(monkeypatch, metadata_by_file):
    """The trash's per-file lookup, faked: each file's library metadata."""

    def selection(payload):
        name = payload.files[0]
        if name not in metadata_by_file:
            raise doctor_ai_sections.TrashError('unsupported_collection')
        return [{'stored': name, 'metadata': metadata_by_file[name]}]

    monkeypatch.setattr(
        doctor_ai_sections.trash_routes, '_selection', selection
    )


def test_a_copy_the_trash_would_refuse_is_caught_before_apply(
    doctor, monkeypatch
):
    _trash_lookup(
        monkeypatch,
        {
            # An old download: no ids, and no album tag.
            COPY: {'title': 'Blinding Lights', 'artist': 'The Weeknd'},
            REMIX: {'isrc': 'USUG12000433'},
        },
    )
    text = _text(
        _call('suggest_keep_song', keep=ORIGINAL, remove=[COPY], reason='x')
    )
    assert 'would refuse' in text
    assert 'album' in text
    assert 'Upgrade library' in text
    assert doctor_ai.helper.status()['suggestions'] == []
    # A copy with an ISRC is fine.
    _data(
        _call('suggest_keep_song', keep=ORIGINAL, remove=[REMIX], reason='x')
    )


def test_title_artist_and_album_are_enough_without_ids(doctor, monkeypatch):
    _trash_lookup(
        monkeypatch,
        {
            COPY: {
                'title': 'Blinding Lights',
                'artist': 'The Weeknd',
                'album': 'Singles',
            }
        },
    )
    _data(_call('suggest_keep_song', keep=ORIGINAL, remove=[COPY], reason='x'))


def test_song_details_says_whether_the_trash_takes_each_copy(
    doctor, monkeypatch
):
    _trash_lookup(
        monkeypatch,
        {ORIGINAL: {'spotify_id': '4uLU6hMCjMI75M1A2tKUQC'}, COPY: {}},
    )
    files = _data(_call('song_details', files=[ORIGINAL, COPY, REMIX]))[
        'files'
    ]
    verdicts = [f['music_trash'] for f in files]
    assert verdicts[0] == 'can take it'
    assert verdicts[1].startswith('refuses: it has no Spotify')
    assert "isn't covered" in verdicts[2]


def test_with_the_trash_off_nothing_is_checked(doctor, monkeypatch):
    monkeypatch.setattr(api.state, 'library_trash', None)

    def boom(_payload):
        raise AssertionError('no trash lookup with the trash off')

    monkeypatch.setattr(doctor_ai_sections.trash_routes, '_selection', boom)
    files = _data(_call('song_details', files=[ORIGINAL]))['files']
    assert files[0]['music_trash'] == 'off'
    _data(_call('suggest_keep_song', keep=ORIGINAL, remove=[COPY], reason='x'))


def test_an_unexpected_lookup_error_does_not_block_a_suggestion(
    doctor, monkeypatch
):
    def broken(_payload):
        raise RuntimeError('library listing failed')

    monkeypatch.setattr(doctor_ai_sections.trash_routes, '_selection', broken)
    _data(_call('suggest_keep_song', keep=ORIGINAL, remove=[COPY], reason='x'))
