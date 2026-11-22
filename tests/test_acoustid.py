"""AcoustID: identify by sound, opt-in and confident or nothing.

Every AcoustID and MusicBrainz answer here is a recorded-shape fake: no
test reaches the network or needs fpcalc.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mutagen.id3 import ID3

from downtify import acoustid, acoustid_routes, api, auth, isrc, musicbrainz
from downtify import library_upgrade as lu
from downtify.admin_access import admin_user
from downtify.library_upgrade import (
    ACOUSTID_LOOKUP_ONLY,
    CATEGORY_ACOUSTID,
    UpgradeOptions,
    normalize_categories,
)
from tests.test_library_upgrade import _context, _runner, _wait, _write_track

KEY = 'TestKey123'
CODE = 'INT101500123'
SONG = {'name': 'Track', 'artists': ['Artist'], 'duration': 200.0}


def _result(score: float, *recordings: dict[str, Any]) -> dict[str, Any]:
    return {'id': 'acoustid-1', 'score': score, 'recordings': list(recordings)}


def _recording(
    rec_id: str = 'mbid-1',
    title: str = 'Track',
    artist: str = 'Artist',
    duration: Any = 200,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        'id': rec_id,
        'title': title,
        'artists': [{'id': 'artist-1', 'name': artist}],
    }
    if duration is not None:
        row['duration'] = duration
    return row


class _Resp:
    def __init__(self, status: int, body: Any) -> None:
        self.status_code = status
        self._body = body

    def json(self) -> Any:
        return self._body


@pytest.fixture(autouse=True)
def slept(monkeypatch: Any) -> list[float]:
    slept: list[float] = []
    monkeypatch.setattr(acoustid.time, 'sleep', slept.append)
    return slept


def _answers(monkeypatch: Any, *answers: Any) -> list[dict[str, Any]]:
    """Fake AcoustID: each request gets the next answer."""

    sent: list[dict[str, Any]] = []
    queue = list(answers)

    def post(url, data=None, headers=None, timeout=None):
        assert url == acoustid.LOOKUP_URL
        sent.append(dict(data or {}))
        answer = queue.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(acoustid.httpx, 'post', post)
    return sent


def _ok(*results: dict[str, Any]) -> _Resp:
    return _Resp(200, {'status': 'ok', 'results': list(results)})


def _isrcs(monkeypatch: Any, by_recording: dict[str, list[str]]) -> list:
    asked: list[str] = []

    def get(path, **params):
        rec_id = path.rsplit('/', 1)[-1]
        asked.append(rec_id)
        assert params == {'inc': 'isrcs'}
        return {'id': rec_id, 'isrcs': by_recording.get(rec_id, [])}

    monkeypatch.setattr(musicbrainz, '_get', get)
    return asked


def _fingerprint(monkeypatch: Any) -> None:
    monkeypatch.setattr(acoustid, 'fingerprint', lambda _p: (200, 'AQADtF'))
    monkeypatch.setattr(acoustid, 'fingerprinter', lambda: 'fpcalc')


# ── The key ─────────────────────────────────────────────────────────────


def test_keys_are_checked_masked_and_kept_in_their_own_file(
    tmp_path: Path,
) -> None:
    assert acoustid.clean_key('  abcDEF-12_3 ') == 'abcDEF-12_3'
    assert not acoustid.clean_key('has space')
    assert not acoustid.clean_key('x' * 65)
    assert not acoustid.clean_key('ab')
    store = acoustid.KeyStore(tmp_path / '.acoustid_key')
    assert not store.get()
    assert not store.hint()
    store.set(KEY)
    assert store.get() == KEY
    assert store.hint() == '••••y123'
    store.set('')
    assert not (tmp_path / '.acoustid_key').exists()


# ── Judging AcoustID's answer ───────────────────────────────────────────


def test_a_sure_match_with_the_tags_own_song_is_confirmed() -> None:
    found = acoustid.judge([_result(0.97, _recording())], SONG)
    assert found.verdict == 'confirmed'
    assert found.recordings == ['mbid-1']
    assert found.artist == 'Artist'
    assert found.title == 'Track'


def test_names_compare_like_the_library_and_any_credited_artist() -> None:
    rec = _recording(title='Track (feat. Guest)', artist='Guest')
    rec['artists'].append({'id': 'artist-1', 'name': 'ARTIST'})
    found = acoustid.judge([_result(0.93, rec)], SONG)
    assert found.verdict == 'confirmed'


def test_a_low_score_is_never_trusted() -> None:
    found = acoustid.judge([_result(0.89, _recording())], SONG)
    assert found.verdict == 'unknown'
    assert acoustid.judge([], SONG).verdict == 'unknown'


def test_a_sure_match_with_another_song_is_reported_not_trusted() -> None:
    other = _recording(title='Tum Hi Ho', artist='Arijit Singh')
    found = acoustid.judge([_result(0.95, other)], SONG)
    assert found.verdict == 'different'
    assert found.recordings == []
    assert (found.artist, found.title) == ('Arijit Singh', 'Tum Hi Ho')


def test_a_length_far_from_the_files_is_not_the_same_recording() -> None:
    far = _recording(duration=230)
    assert acoustid.judge([_result(0.95, far)], SONG).verdict == 'different'
    # MusicBrainz without a length: the fingerprint and names decide.
    bare = _recording(duration=None)
    assert acoustid.judge([_result(0.95, bare)], SONG).verdict == 'confirmed'


def test_a_file_without_artist_or_title_is_never_confirmed() -> None:
    blank = {'name': '', 'artists': [], 'duration': 200.0}
    found = acoustid.judge([_result(0.99, _recording())], blank)
    assert found.verdict == 'different'


def test_fingerprints_without_recordings_are_unknown() -> None:
    found = acoustid.judge([_result(0.99)], SONG)
    assert found.verdict == 'unknown'


# ── identify(): AcoustID, then MusicBrainz for the ISRC ─────────────────


def test_identify_sends_the_fingerprint_and_takes_the_one_isrc(
    tmp_path: Path, monkeypatch: Any
) -> None:
    _fingerprint(monkeypatch)
    sent = _answers(monkeypatch, _ok(_result(0.96, _recording())))
    _isrcs(monkeypatch, {'mbid-1': [CODE]})
    found = acoustid.identify(tmp_path / 'x.mp3', SONG, KEY)
    assert found.isrc == CODE
    assert sent == [
        {
            'client': KEY,
            'format': 'json',
            'duration': '200',
            'fingerprint': 'AQADtF',
            'meta': 'recordings',
        }
    ]


def test_recordings_that_disagree_on_the_isrc_give_none(
    tmp_path: Path, monkeypatch: Any
) -> None:
    _fingerprint(monkeypatch)
    _answers(
        monkeypatch,
        _ok(_result(0.96, _recording('a'), _recording('b'))),
    )
    _isrcs(monkeypatch, {'a': [CODE], 'b': ['GBUM71029604']})
    found = acoustid.identify(tmp_path / 'x.mp3', SONG, KEY)
    assert found.verdict == 'confirmed'
    assert not found.isrc


def test_another_song_is_never_looked_up_on_musicbrainz(
    tmp_path: Path, monkeypatch: Any
) -> None:
    _fingerprint(monkeypatch)
    _answers(
        monkeypatch, _ok(_result(0.96, _recording(title='Something else')))
    )
    asked = _isrcs(monkeypatch, {})
    found = acoustid.identify(tmp_path / 'x.mp3', SONG, KEY)
    assert found.verdict == 'different'
    assert asked == []


def test_a_refused_key_says_so(monkeypatch: Any) -> None:
    _answers(
        monkeypatch,
        _Resp(
            400,
            {
                'status': 'error',
                'error': {'code': 4, 'message': 'invalid API key'},
            },
        ),
    )
    with pytest.raises(acoustid.InvalidKey):
        acoustid.lookup('bad-key', 200, 'AQAD')


def test_a_busy_acoustid_is_asked_again_after_a_pause(
    monkeypatch: Any, slept: list[float]
) -> None:
    _answers(
        monkeypatch,
        _Resp(503, {}),
        httpx.ConnectError('down'),
        _ok(_result(0.95, _recording())),
    )
    rows = acoustid.lookup(KEY, 200, 'AQAD')
    assert rows[0]['score'] == 0.95
    # Paused after each failure (longer each time).
    pauses = [s for s in slept if s >= 1]
    assert pauses == [2, 4]


def test_requests_keep_to_three_a_second(
    monkeypatch: Any, slept: list[float]
) -> None:
    _answers(monkeypatch, _ok(), _ok())
    monkeypatch.setattr(acoustid, '_last_request', 0.0)
    acoustid.lookup(KEY, 200, 'AQAD')
    acoustid.lookup(KEY, 200, 'AQAD')
    waits = [s for s in slept if 0 < s <= acoustid._INTERVAL]
    assert waits
    assert acoustid._INTERVAL >= 1 / 3


def test_giving_up_after_the_retries(monkeypatch: Any) -> None:
    _answers(monkeypatch, *[_Resp(503, {})] * acoustid._RETRIES)
    with pytest.raises(acoustid.AcoustIDError, match='busy'):
        acoustid.lookup(KEY, 200, 'AQAD')


def test_checking_a_key_accepts_an_unreadable_test_fingerprint(
    monkeypatch: Any,
) -> None:
    _answers(
        monkeypatch,
        _Resp(
            400,
            {
                'status': 'error',
                'error': {'code': 3, 'message': 'invalid fingerprint'},
            },
        ),
        _Resp(
            400,
            {
                'status': 'error',
                'error': {'code': 4, 'message': 'invalid API key'},
            },
        ),
    )
    acoustid.check_key(KEY)
    with pytest.raises(acoustid.InvalidKey):
        acoustid.check_key('bad-key')


# ── Fingerprinting tools ────────────────────────────────────────────────


def test_no_tool_means_no_fingerprint(tmp_path: Path, monkeypatch: Any):
    monkeypatch.delenv('DOWNTIFY_FPCALC', raising=False)
    monkeypatch.setattr(acoustid.shutil, 'which', lambda _name: None)
    assert not acoustid.fingerprinter()
    with pytest.raises(acoustid.NoFingerprinter):
        acoustid.fingerprint(tmp_path / 'x.mp3')
    status = acoustid.status(True, acoustid.KeyStore(tmp_path / 'k'))
    assert status['ready'] is False
    assert not status['fingerprinter']


def test_ffmpeg_with_chromaprint_is_used_without_fpcalc(
    monkeypatch: Any,
) -> None:
    monkeypatch.delenv('DOWNTIFY_FPCALC', raising=False)
    monkeypatch.setattr(
        acoustid.shutil,
        'which',
        lambda name: '/usr/bin/ffmpeg' if name == 'ffmpeg' else None,
    )
    monkeypatch.setattr(acoustid, '_ffmpeg_checked', {})

    class _Run:
        stdout = ' E  chromaprint     Chromaprint\n E  mp3   MP3\n'

    monkeypatch.setattr(acoustid.subprocess, 'run', lambda *a, **k: _Run())
    assert acoustid.fingerprinter() == 'ffmpeg'
    _Run.stdout = ' E  mp3   MP3\n'
    monkeypatch.setattr(acoustid, '_ffmpeg_checked', {})
    assert not acoustid.fingerprinter()


# ── The library upgrade ─────────────────────────────────────────────────


def _library(tmp_path: Path, settings: dict[str, Any]):
    ctx = _context(tmp_path)
    old = _write_track(ctx.download_dir / 'old.mp3')
    tagged = _write_track(ctx.download_dir / 'tagged.mp3')
    isrc.write(tagged, 'GBUM71029604')
    runner = _runner(tmp_path, ctx)
    runner.deps.settings = lambda: settings
    runner.deps.acoustid_key = lambda: KEY
    return runner, old


def _identified(monkeypatch: Any, found: acoustid.Identity) -> list:
    asked: list[tuple[Path, dict[str, Any], str]] = []

    def identify(path, song, key):
        asked.append((path, song, key))
        return found

    monkeypatch.setattr(lu.acoustid_mod, 'identify', identify)
    monkeypatch.setattr(lu.acoustid_mod, 'fingerprinter', lambda: 'fpcalc')
    return asked


def _run(runner, categories) -> dict[str, Any]:
    runner.start_scan(UpgradeOptions(categories=categories))
    _wait(runner)
    runner.start(categories)
    _wait(runner)
    return runner.db.jobs(runner.db.latest_run()['id'])[0]


CONFIRMED = acoustid.Identity(
    'confirmed', score=0.97, artist='Artist', title='Track', isrc=CODE
)


def test_acoustid_categories_are_a_run_of_their_own() -> None:
    assert normalize_categories(['acoustid', 'artwork']) == (
        CATEGORY_ACOUSTID,
    )
    assert normalize_categories(['acoustid_lookup']) == (
        CATEGORY_ACOUSTID,
        ACOUSTID_LOOKUP_ONLY,
    )
    assert CATEGORY_ACOUSTID not in normalize_categories(None)


def test_looking_up_by_sound_writes_nothing(
    tmp_path: Path, monkeypatch: Any
) -> None:
    runner, old = _library(tmp_path, {'acoustid_enabled': True})
    before = old.read_bytes()
    asked = _identified(monkeypatch, CONFIRMED)
    job = _run(runner, (CATEGORY_ACOUSTID, ACOUSTID_LOOKUP_ONLY))
    assert job['file'] == 'old.mp3'
    assert job['status'] == 'done'
    assert job['detail'] == f'Confirmed by sound (97%); would add ISRC {CODE}'
    assert old.read_bytes() == before
    assert asked[0][1]['name'] == 'Track'
    assert asked[0][2] == KEY
    # Only the file without an ISRC was queued, and it isn't marked.
    runner.start_scan(UpgradeOptions(categories=(CATEGORY_ACOUSTID,)))
    _wait(runner)
    assert runner.status()['counts']['total'] == 1


def test_a_confirmed_file_gets_only_its_isrc(
    tmp_path: Path, monkeypatch: Any
) -> None:
    runner, old = _library(tmp_path, {'acoustid_enabled': True})
    _identified(monkeypatch, CONFIRMED)
    job = _run(runner, (CATEGORY_ACOUSTID,))
    assert job['status'] == 'done'
    assert isrc.read(old) == CODE
    frames = {key.split(':')[0] for key in ID3(str(old)).keys()}
    # No MusicBrainz IDs (UFID / TXXX:MusicBrainz ...) ever.
    assert 'UFID' not in frames
    assert not [k for k in ID3(str(old)).keys() if 'MusicBrainz' in k]


@pytest.mark.parametrize(
    ('found', 'detail'),
    [
        (
            acoustid.Identity('unknown'),
            'No sure match by sound; left as it is',
        ),
        (
            acoustid.Identity(
                'different', score=0.95, artist='Other', title='Song'
            ),
            'Sounds like Other - Song (95%), not what the tags say; '
            'left as it is',
        ),
        (
            acoustid.Identity('confirmed', score=0.92, artist='Artist'),
            'Confirmed by sound (92%), but no single ISRC; left as it is',
        ),
    ],
)
def test_anything_less_than_sure_leaves_the_file_alone(
    tmp_path: Path, monkeypatch: Any, found: Any, detail: str
) -> None:
    runner, old = _library(tmp_path, {'acoustid_enabled': True})
    before = old.read_bytes()
    _identified(monkeypatch, found)
    job = _run(runner, (CATEGORY_ACOUSTID,))
    assert job['status'] == 'skipped'
    assert job['detail'] == detail
    assert old.read_bytes() == before


def test_nothing_is_asked_while_acoustid_is_off(
    tmp_path: Path, monkeypatch: Any
) -> None:
    runner, old = _library(tmp_path, {'acoustid_enabled': False})
    before = old.read_bytes()
    asked = _identified(monkeypatch, CONFIRMED)
    job = _run(runner, (CATEGORY_ACOUSTID,))
    assert job['status'] == 'skipped'
    assert job['detail'] == 'AcoustID is turned off in Settings'
    assert asked == []
    assert old.read_bytes() == before


def test_a_refused_key_fails_the_track_and_writes_nothing(
    tmp_path: Path, monkeypatch: Any
) -> None:
    runner, old = _library(tmp_path, {'acoustid_enabled': True})
    before = old.read_bytes()

    def refuse(*_args):
        raise acoustid.InvalidKey('nope')

    monkeypatch.setattr(lu.acoustid_mod, 'identify', refuse)
    monkeypatch.setattr(lu.acoustid_mod, 'fingerprinter', lambda: 'fpcalc')
    job = _run(runner, (CATEGORY_ACOUSTID,))
    assert job['status'] == 'failed'
    assert job['detail'] == 'AcoustID refused the API key'
    assert old.read_bytes() == before


def test_a_look_up_scan_never_turns_into_a_writing_run(
    tmp_path: Path, monkeypatch: Any
) -> None:
    runner, old = _library(tmp_path, {'acoustid_enabled': True})
    _identified(monkeypatch, CONFIRMED)
    runner.start_scan(
        UpgradeOptions(categories=(CATEGORY_ACOUSTID, ACOUSTID_LOOKUP_ONLY))
    )
    _wait(runner)
    runner.start((CATEGORY_ACOUSTID,))
    _wait(runner)
    assert not isrc.read(old)


# ── The API ─────────────────────────────────────────────────────────────


@pytest.fixture
def client(tmp_path: Path, monkeypatch: Any) -> TestClient:
    monkeypatch.setattr(api.state, 'settings_path', tmp_path / 'settings.json')
    monkeypatch.setattr(api.state, 'settings', {'acoustid_enabled': True})
    monkeypatch.setattr(acoustid, 'fingerprinter', lambda: 'ffmpeg')
    app = FastAPI()
    app.include_router(acoustid_routes.router)
    app.dependency_overrides[admin_user] = lambda: 1
    return TestClient(app)


def test_the_key_is_saved_apart_and_never_sent_back(
    client: TestClient, tmp_path: Path
) -> None:
    assert client.get('/api/acoustid').json() == {
        'enabled': True,
        'key_set': False,
        'key_hint': '',
        'fingerprinter': 'ffmpeg',
        'ready': False,
    }
    saved = client.put('/api/acoustid/key', json={'key': KEY}).json()
    assert saved['key_set'] is True
    assert saved['ready'] is True
    assert KEY not in str(saved)
    assert (tmp_path / '.acoustid_key').read_text('utf-8') == KEY
    assert KEY not in str(api.state.settings)
    bad = client.put('/api/acoustid/key', json={'key': 'not a key!'})
    assert bad.status_code == 400
    assert (
        client.put('/api/acoustid/key', json={'key': ''}).json()['key_set']
        is False
    )


def test_testing_the_key(client: TestClient, monkeypatch: Any) -> None:
    assert client.post('/api/acoustid/test').json()['ok'] is False
    client.put('/api/acoustid/key', json={'key': KEY})
    checked: list[str] = []
    monkeypatch.setattr(acoustid, 'check_key', checked.append)
    assert client.post('/api/acoustid/test').json() == {
        'ok': True,
        'detail': 'AcoustID accepted the key',
    }
    assert checked == [KEY]

    def refuse(_key):
        raise acoustid.InvalidKey('nope')

    monkeypatch.setattr(acoustid, 'check_key', refuse)
    assert client.post('/api/acoustid/test').json()['ok'] is False


def test_only_admins_reach_the_acoustid_routes() -> None:
    for method, path in (
        ('GET', '/api/acoustid'),
        ('PUT', '/api/acoustid/key'),
        ('POST', '/api/acoustid/test'),
    ):
        assert auth.rule_for(method, path) == auth.ADMIN


def test_acoustid_is_off_by_default() -> None:
    assert api.DEFAULT_SETTINGS['acoustid_enabled'] is False
