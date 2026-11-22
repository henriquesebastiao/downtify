"""The Doctor's AI helper: its MCP endpoint, tools and suggestions."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import main
from downtify import api, doctor_ai, doctor_routes
from downtify.doctor import M3UInfo, PlaylistGroup

MCP = '/api/doctor/ai/mcp'


def _m3u(path: str, entries: list[str], **extra: Any) -> M3UInfo:
    return M3UInfo(
        path=path,
        name=extra.pop('name', path.rsplit('/', 1)[-1].rsplit('.', 1)[0]),
        manual=extra.pop('manual', False),
        entries=entries,
        lines=extra.pop('lines', len(entries)),
        cover=extra.pop('cover', False),
        expected=extra.pop('expected', False),
    )


SONGS = [f'Artist {n}/Album/Artist {n} - Song {n}.mp3' for n in range(10)]
OLD = _m3u('Playlists/Road Trip.m3u', SONGS[:9], cover=True)
NEW = _m3u('Road Trip/Road Trip.m3u', SONGS, expected=True)
OTHER = _m3u('Gym/Gym.m3u', SONGS[:3] + ['X/Y/Z - Other.mp3'] * 1)
MINE = _m3u('Mine/Mine.m3u', SONGS[:5], manual=True)


@pytest.fixture
def doctor(monkeypatch):
    """The Doctor with three playlist files and a health check behind it."""

    infos = [OLD, NEW, OTHER, MINE]
    monkeypatch.setattr(doctor_routes, '_ctx', lambda: None)
    monkeypatch.setattr(doctor_routes, '_m3u_infos', lambda _ctx: infos)
    group = PlaylistGroup('name:road trip', [OLD, NEW], 'name')
    health = {
        'playlists': {
            'm3u': len(infos),
            'groups': [group.as_dict()],
            'kept_apart': 0,
            'list': [i.as_dict() for i in infos],
        }
    }
    monkeypatch.setattr(
        doctor_routes,
        '_last',
        {'health': {'at': '2026-11-20T10:00:00+00:00', 'result': health}},
    )
    monkeypatch.setattr(doctor_routes, '_stale', set())
    monkeypatch.setattr(doctor_routes, '_job', {})
    applied: list[Any] = []

    async def fake_apply(payload):
        applied.append(payload)
        return {'job': {'id': 'job1'} if payload.merge else None}

    monkeypatch.setattr(doctor_routes, 'playlists_apply', fake_apply)
    fresh = doctor_ai.Helper()
    monkeypatch.setattr(doctor_ai, 'helper', fresh)
    monkeypatch.setattr('downtify.doctor_ai_routes.helper', fresh)
    return applied


def _call(name: str, **args: Any) -> dict[str, Any]:
    answer = asyncio.run(
        doctor_ai.handle({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'tools/call',
            'params': {'name': name, 'arguments': args},
        })
    )
    return answer['result']


def _data(result: dict[str, Any]) -> dict[str, Any]:
    assert result['isError'] is False, result['content'][0]['text']
    return json.loads(result['content'][0]['text'])


def _text(result: dict[str, Any]) -> str:
    assert result['isError'] is True
    return result['content'][0]['text']


# -- the protocol -------------------------------------------------------


def test_initialize_names_the_server_and_tells_the_assistant_how():
    answer = asyncio.run(
        doctor_ai.handle({
            'jsonrpc': '2.0',
            'id': 0,
            'method': 'initialize',
            'params': {
                'protocolVersion': '2025-06-18',
                'capabilities': {},
                'clientInfo': {'name': 'claude-code', 'version': '2.1'},
            },
        })
    )
    result = answer['result']
    assert result['protocolVersion'] == '2025-06-18'
    assert result['capabilities'] == {'tools': {'listChanged': False}}
    assert result['serverInfo']['name'] == 'downtify-doctor'
    assert 'DUPLICATE PLAYLISTS' in result['instructions']


def test_an_unknown_protocol_version_gets_the_newest():
    answer = asyncio.run(
        doctor_ai.handle({
            'jsonrpc': '2.0',
            'id': 0,
            'method': 'initialize',
            'params': {'protocolVersion': '1999-01-01'},
        })
    )
    assert (
        answer['result']['protocolVersion'] == doctor_ai.PROTOCOL_VERSIONS[0]
    )


def test_tools_list_hides_the_python_side():
    answer = asyncio.run(
        doctor_ai.handle({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
    )
    tools = answer['result']['tools']
    names = [t['name'] for t in tools]
    assert names[0] == 'get_overview'
    assert {'suggest_merge', 'apply_suggestions'} <= set(names)
    assert all('run' not in t and 'inputSchema' in t for t in tools)
    apply = next(t for t in tools if t['name'] == 'apply_suggestions')
    assert apply['annotations']['destructiveHint'] is True


def test_notifications_ping_and_unknowns():
    handle = doctor_ai.handle
    assert (
        asyncio.run(
            handle({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        )
        is None
    )
    assert (
        asyncio.run(handle({'jsonrpc': '2.0', 'id': 3, 'method': 'ping'}))[
            'result'
        ]
        == {}
    )
    missing = asyncio.run(handle({'jsonrpc': '2.0', 'id': 4, 'method': 'x'}))
    assert missing['error']['code'] == doctor_ai.METHOD_NOT_FOUND
    tool = asyncio.run(
        handle({
            'jsonrpc': '2.0',
            'id': 5,
            'method': 'tools/call',
            'params': {'name': 'nope'},
        })
    )
    assert tool['error']['code'] == doctor_ai.INVALID_PARAMS
    bad = asyncio.run(handle({'id': 6, 'method': 'ping'}))
    assert bad['error']['code'] == doctor_ai.INVALID_REQUEST


# -- running and the key ------------------------------------------------


def test_the_helper_stops_by_itself_after_being_idle():
    now = [1000.0]
    helper = doctor_ai.Helper(clock=lambda: now[0])
    key = helper.start()
    assert helper.check(f'Bearer {key}')
    now[0] += doctor_ai.IDLE_STOP - 1
    assert helper.check(f'Bearer {key}')  # use keeps it going
    now[0] += doctor_ai.IDLE_STOP + 1
    assert not helper.running
    assert not helper.check(f'Bearer {key}')
    assert not helper.status()['key']


def test_a_new_start_makes_a_new_key_and_switches_applying_off():
    helper = doctor_ai.Helper()
    first = helper.start()
    helper.can_apply = True
    second = helper.start()
    assert first != second
    assert not helper.check(f'Bearer {first}')
    assert helper.check(f'Bearer {second}')
    assert helper.can_apply is False
    helper.stop()
    assert not helper.check(f'Bearer {second}')


@pytest.fixture
def app(tmp_path, monkeypatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', tmp_path / 'downloads')
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    for name in ('auth', 'activity', 'identity', 'downloader', 'settings'):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    return main.build_app()


@pytest.fixture
def client(app):
    return TestClient(app, base_url='http://testserver')


def _admin(client: TestClient) -> TestClient:
    response = client.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    assert response.status_code == 200, response.text
    return client


def _rpc(client, key, payload):
    return client.post(
        MCP, json=payload, headers={'Authorization': f'Bearer {key}'}
    )


def test_mcp_endpoint_is_closed_while_off_and_needs_the_key(client, doctor):
    hello = {'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}
    off = client.post(MCP, json=hello)
    assert off.status_code == 503
    assert 'Settings > Doctor > AI helper' in off.json()['error']

    key = _admin(client).post('/api/doctor/ai/start').json()['key']
    assert key.startswith('dtai_')
    client.cookies.clear()  # the assistant has no browser session
    assert client.post(MCP, json=hello).status_code == 401
    assert _rpc(client, 'dtai_wrong', hello).status_code == 401
    ok = _rpc(client, key, hello)
    assert ok.status_code == 200
    assert ok.json() == {'jsonrpc': '2.0', 'id': 1, 'result': {}}
    note = _rpc(client, key, {'jsonrpc': '2.0', 'method': 'notified'})
    assert note.status_code == 202
    stream = client.get(MCP, headers={'Authorization': f'Bearer {key}'})
    assert stream.status_code == 405
    broken = client.post(
        MCP,
        content=b'{not json',
        headers={
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
        },
    )
    assert broken.status_code == 400
    assert broken.json()['error']['code'] == doctor_ai.PARSE_ERROR


def test_the_page_routes_are_admin_only(client, doctor):
    assert client.get('/api/doctor/ai').status_code == 401
    assert client.post('/api/doctor/ai/start').status_code == 401
    status = _admin(client).get('/api/doctor/ai').json()
    assert status['running'] is False
    assert status['mcp_path'] == MCP


def test_the_assistant_s_name_shows_on_the_page(client, doctor):
    key = _admin(client).post('/api/doctor/ai/start').json()['key']
    _rpc(
        client,
        key,
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'initialize',
            'params': {'clientInfo': {'name': 'claude-code', 'version': '2'}},
        },
    )
    status = client.get('/api/doctor/ai').json()
    assert status['client'] == 'claude-code 2'
    assert status['last_used_at']


# -- tools ---------------------------------------------------------------


def test_overview_and_the_duplicate_groups(doctor):
    overview = _data(_call('get_overview'))
    assert overview['duplicate_playlist_groups'] == 1
    assert overview['ai_can_apply'] is False
    groups = _data(_call('list_duplicate_playlists'))
    assert groups['total_groups'] == 1
    group = groups['groups'][0]
    assert group['keeper'] == NEW.path
    assert group['can_merge'] is True
    assert {m['path'] for m in group['members']} == {OLD.path, NEW.path}


def test_compare_lists_what_only_one_playlist_has(doctor):
    data = _data(_call('compare_playlists', paths=[OLD.path, NEW.path]))
    assert data['keeper'] == NEW.path
    assert data['in_all_of_them'] == 9
    by_path = {m['path']: m for m in data['members']}
    assert by_path[NEW.path]['only_here'] == ['Artist 9 - Song 9']
    assert by_path[OLD.path]['only_here_count'] == 0
    assert by_path[NEW.path]['kept'] is True


def test_list_and_read_playlists(doctor):
    found = _data(_call('list_playlists', query='road'))
    assert found['total'] == 2
    page = _data(_call('get_playlist', path=NEW.path, offset=8, limit=5))
    assert [s['song'] for s in page['songs']] == [
        'Artist 8 - Song 8',
        'Artist 9 - Song 9',
    ]
    assert 'No playlist file' in _text(_call('get_playlist', path='x.m3u'))


def test_suggestions_check_what_they_suggest(doctor):
    # A reason is required, for the user.
    assert 'reason' in _text(
        _call('suggest_merge', paths=[OLD.path, NEW.path])
    )
    # Too few shared songs: no merge, but "different" is fine.
    assert 'too few songs' in _text(
        _call('suggest_merge', paths=[NEW.path, OTHER.path], reason='x')
    )
    # Playlists made in the Library are never merged.
    assert 'made in the Library' in _text(
        _call('suggest_different', paths=[NEW.path, MINE.path], reason='x')
    )
    made = _data(
        _call(
            'suggest_merge',
            paths=[OLD.path, NEW.path],
            reason='Same road trip mix; the old file misses one song.',
        )
    )
    assert made['keeper'] == NEW.path
    # The health check's own reason for the group, for the card.
    group = doctor_ai.helper.status()['suggestions'][0]['group']
    assert group['reason'] == 'name'
    # The same playlist can't wait in two suggestions.
    assert 'already in a waiting suggestion' in _text(
        _call('suggest_different', paths=[NEW.path, OTHER.path], reason='x')
    )
    listed = _data(_call('list_suggestions'))['suggestions']
    assert [(s['decision'], s['state']) for s in listed] == [
        ('merge', 'waiting')
    ]
    gone = _data(_call('withdraw_suggestion', ids=[made['suggestion']]))
    assert gone == {'withdrawn': 1}


def test_no_suggestions_on_out_of_date_findings(doctor, monkeypatch):
    monkeypatch.setattr(doctor_routes, '_stale', {'playlists'})
    assert 'run_health_check' in _text(
        _call('suggest_merge', paths=[OLD.path, NEW.path], reason='x')
    )


def test_the_assistant_applies_only_when_allowed_and_agreed(doctor):
    merge = _data(
        _call('suggest_merge', paths=[OLD.path, NEW.path], reason='same')
    )['suggestion']
    refused = _text(_call('apply_suggestions', ids=[merge], user_agreed=True))
    assert 'switched off' in refused
    assert doctor == []
    doctor_ai.helper.can_apply = True
    assert 'user_agreed' in _text(
        _call('apply_suggestions', ids=[merge], user_agreed=False)
    )
    done = _data(_call('apply_suggestions', ids=[merge], user_agreed=True))
    assert done['merging'] == 1
    assert done['job'] == 'job1'
    assert doctor[0].merge == [[OLD.path, NEW.path]]
    assert doctor[0].apart == []
    state = doctor_ai.helper.status()['suggestions'][0]
    assert (state['state'], state['job'], state['applied_by']) == (
        'applying',
        'job1',
        'assistant',
    )


def test_applying_from_the_page_and_the_job_s_outcome(client, doctor):
    _admin(client).post('/api/doctor/ai/start')
    merge = _data(
        _call('suggest_merge', paths=[OLD.path, NEW.path], reason='same')
    )['suggestion']
    response = client.post('/api/doctor/ai/apply', json={'ids': [merge]})
    assert response.status_code == 200, response.text
    assert doctor[0].merge == [[OLD.path, NEW.path]]
    # The Doctor job finishes: the suggestion reads "applied".
    doctor_routes._job.update(id='job1', state='done')
    status = client.get('/api/doctor/ai').json()
    assert status['suggestions'][0]['state'] == 'applied'
    assert client.post('/api/doctor/ai/clear').json()['suggestions'] == []
    # Nothing waiting any more: applying again is refused.
    again = client.post('/api/doctor/ai/apply', json={'ids': [merge]})
    assert again.status_code == 409


def test_different_playlists_are_settled_at_once(doctor):
    doctor_ai.helper.can_apply = True
    apart = _data(
        _call(
            'suggest_different',
            paths=[NEW.path, OTHER.path],
            reason='A road trip mix and a gym mix.',
        )
    )['suggestion']
    done = _data(_call('apply_suggestions', ids=[apart], user_agreed=True))
    assert (done['kept_apart'], done['merging'], done['job']) == (1, 0, None)
    assert doctor[0].apart == [[NEW.path, OTHER.path]]
    assert doctor_ai.helper.status()['suggestions'][0]['state'] == 'applied'


def test_a_group_the_assistant_put_together_says_so(doctor):
    _data(_call('suggest_different', paths=[NEW.path, OTHER.path], reason='x'))
    group = doctor_ai.helper.status()['suggestions'][0]['group']
    assert group['reason'] == 'assistant'


def test_a_refused_apply_marks_the_suggestion_failed(doctor, monkeypatch):
    async def stale(_payload):
        raise HTTPException(409, detail={'code': 'rescan_first'})

    monkeypatch.setattr(doctor_routes, 'playlists_apply', stale)
    doctor_ai.helper.can_apply = True
    merge = _data(
        _call('suggest_merge', paths=[OLD.path, NEW.path], reason='same')
    )['suggestion']
    text = _text(_call('apply_suggestions', ids=[merge], user_agreed=True))
    assert 'run_health_check' in text
    state = doctor_ai.helper.status()['suggestions'][0]
    assert state['state'] == 'failed'
    # The page shows the Doctor's own message for the code.
    assert state['error_code'] == 'rescan_first'


def test_the_switch_needs_a_running_helper(client, doctor):
    _admin(client)
    off = client.put('/api/doctor/ai/settings', json={'can_apply': True})
    assert off.status_code == 409
    client.post('/api/doctor/ai/start')
    on = client.put('/api/doctor/ai/settings', json={'can_apply': True})
    assert on.json()['can_apply'] is True


def test_a_failed_job_leaves_its_code_for_the_page(client, doctor):
    _admin(client).post('/api/doctor/ai/start')
    merge = _data(
        _call('suggest_merge', paths=[OLD.path, NEW.path], reason='same')
    )['suggestion']
    client.post('/api/doctor/ai/apply', json={'ids': [merge]})
    doctor_routes._job.update(
        id='job1',
        state='failed',
        error={'code': 'dedupe_trash', 'reason': 'identity_uncertain'},
    )
    entry = client.get('/api/doctor/ai').json()['suggestions'][0]
    assert entry['state'] == 'failed'
    assert entry['error_code'] == 'dedupe_trash'
    assert 'identity_uncertain' in entry['error']
