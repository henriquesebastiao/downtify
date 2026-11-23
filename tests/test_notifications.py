"""Notifications (downtify/notifications.py, discord_bot.py and
notification_routes.py), offline: HTTP goes to an httpx mock."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from downtify import discord_bot, notification_routes, notifications
from downtify.notifications import Dispatcher, Message, Task

WEBHOOK = 'https://discord.com/api/webhooks/1/secret-token'


def _cfg(**discord):
    ch = {'enabled': True, 'webhook_url': WEBHOOK, **discord}
    return notifications.effective({
        'enabled': True,
        'progress_seconds': 30,
        'channels': {'discord': ch},
    })


class Recorder:
    """An httpx transport that records every request."""

    def __init__(self, status=200):
        self.requests: list[httpx.Request] = []
        self.status = status
        self._next = 100

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        self._next += 1
        return httpx.Response(self.status, json={'id': str(self._next)})

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self))

    def bodies(self):
        return [json.loads(r.content or b'{}') for r in self.requests]


@pytest.fixture(autouse=True)
def _no_gap(monkeypatch):
    monkeypatch.setattr(notifications, 'CHANNEL_GAP', 0)


def _dispatcher(cfg, tasks):
    d = Dispatcher()
    d.configure(cfg)
    d.register_source('fake', lambda: list(tasks))
    return d


def _run(coro):
    return asyncio.run(coro)


# ── settings ────────────────────────────────────────────────────────────


def test_off_by_default_and_nothing_configured():
    cfg = notifications.effective({})
    assert cfg['enabled'] is False
    assert all(not ch['enabled'] for ch in cfg['channels'].values())
    d = Dispatcher()
    d.configure(cfg)
    assert d.channels() == []


def test_bad_values_fall_back():
    cfg = notifications.effective({
        'enabled': 'yes',
        'progress_seconds': 7,
        'channels': {
            'discord': {
                'mode': 'telepathy',
                'channel_id': '12ab',
                'tasks': ['doctor', 'nope'],
                'allowed_users': '1, 2 x 3',
            }
        },
    })
    assert cfg['enabled'] is False
    assert cfg['progress_seconds'] == notifications.DEFAULT_PROGRESS_SECONDS
    discord = cfg['channels']['discord']
    assert discord['mode'] == 'webhook'
    assert not discord['channel_id']
    assert discord['tasks'] == ['doctor']
    assert discord['allowed_users'] == '1 2 3'


def test_public_hides_secrets_and_blank_keeps_them():
    cfg = _cfg(bot_token='bot-secret')
    shown = notifications.public(cfg)
    text = json.dumps(shown)
    assert 'secret-token' not in text
    assert 'bot-secret' not in text
    assert shown['channels']['discord']['webhook_url_set'] is True
    assert shown['channels']['discord']['bot_token_set'] is True

    kept = notifications.merge_update(
        cfg, {'channels': {'discord': {'webhook_url': '', 'mode': 'bot'}}}
    )
    assert kept['channels']['discord']['webhook_url'] == WEBHOOK
    assert kept['channels']['discord']['mode'] == 'bot'

    cleared = notifications.merge_update(
        cfg, {}, clear=('discord.bot_token', 'discord.mode')
    )
    assert not cleared['channels']['discord']['bot_token']
    assert cleared['channels']['discord']['mode'] == 'webhook'


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / notifications.FILE_NAME
    notifications.save(path, _cfg())
    assert notifications.load(path) == _cfg()
    assert notifications.load(tmp_path / 'missing.json')['enabled'] is False


# ── messages ────────────────────────────────────────────────────────────


def test_progress_bar():
    assert notifications.progress_bar(0, 0) == '…'
    assert notifications.progress_bar(5, 0) == '5'
    assert notifications.progress_bar(1, 4, width=4) == '▓░░░ 25% (1/4)'
    assert notifications.progress_bar(9, 4, width=4).startswith('▓▓▓▓ 100%')


def test_batch_message_groups_and_caps():
    one = notifications.batch_message('download_failed', [('A', 'why')])
    assert one.title == 'Download failed: A'
    assert one.level == 'error'
    many = notifications.batch_message(
        'download_failed', [(f'Song {i}', '') for i in range(13)]
    )
    assert many.title == '13 downloads failed'
    assert many.text.count('•') == notifications.BATCH_LINES
    assert '… and 3 more' in many.text


# ── the dispatcher ──────────────────────────────────────────────────────


def test_task_lifecycle_edits_one_message():
    tasks = [Task('doctor:1', 'doctor', 'Doctor health check', 'running')]
    d = _dispatcher(_cfg(), tasks)
    rec = Recorder()

    async def go():
        async with rec.client() as client:
            await d.tick(client)  # started
            tasks[0] = Task(
                'doctor:1', 'doctor', 'Doctor health check', 'running', 5, 10
            )
            d._live[('discord', 'doctor:1')].sent_at -= 60
            await d.tick(client)  # progress: an edit
            tasks[0] = Task(
                'doctor:1',
                'doctor',
                'Doctor health check',
                'done',
                10,
                10,
                summary=[('Problems', '3')],
            )
            await d.tick(client)  # finished: settle + announce

    _run(go())
    methods = [r.method for r in rec.requests]
    assert methods == ['POST', 'PATCH', 'PATCH', 'POST']
    assert rec.requests[1].url.path.endswith('/messages/101')
    embeds = [b['embeds'][0] for b in rec.bodies()]
    assert embeds[0]['title'] == 'Doctor health check: started'
    assert '50%' in embeds[1]['description']
    assert embeds[3]['title'] == 'Doctor health check: finished'
    assert embeds[3]['fields'][0] == {
        'name': 'Problems',
        'value': '3',
        'inline': True,
    }


def test_progress_is_rate_limited():
    tasks = [Task('t:1', 'doctor', 'Doctor', 'running', 1, 100)]
    d = _dispatcher(_cfg(), tasks)
    rec = Recorder()

    async def go():
        async with rec.client() as client:
            await d.tick(client)
            for done in range(2, 20):
                tasks[0] = Task(
                    't:1', 'doctor', 'Doctor', 'running', done, 100
                )
                await d.tick(client)

    _run(go())
    # Only the start: every later change came within progress_seconds.
    assert [r.method for r in rec.requests] == ['POST']


def test_jobs_finished_before_start_are_not_announced():
    tasks = [Task('t:old', 'doctor', 'Doctor', 'done')]
    d = _dispatcher(_cfg(), tasks)
    rec = Recorder()

    async def go():
        async with rec.client() as client:
            await d.tick(client)
            await d.tick(client)

    _run(go())
    assert rec.requests == []


def test_filters_per_channel():
    cfg = _cfg(tasks=['ratings'], phases=['finish'])
    tasks = [Task('d:1', 'doctor', 'Doctor', 'running')]
    d = _dispatcher(cfg, tasks)
    rec = Recorder()

    async def go():
        async with rec.client() as client:
            await d.tick(client)
            tasks[0] = Task('d:1', 'doctor', 'Doctor', 'failed', error='x')
            await d.tick(client)

    _run(go())
    assert rec.requests == []


def test_events_are_grouped_then_sent():
    d = _dispatcher(_cfg(), [])
    rec = Recorder()
    for i in range(3):
        d.emit('download_failed', f'Song {i}', 'No match')
    d.emit('download_done', 'Not wanted')  # not in the default events

    async def go():
        async with rec.client() as client:
            await d.tick(client)  # still gathering
            assert rec.requests == []
            await d.tick(client, flush=True)

    _run(go())
    assert len(rec.requests) == 1
    assert rec.bodies()[0]['embeds'][0]['title'] == '3 downloads failed'


def test_emit_while_off_queues_nothing():
    d = Dispatcher()
    d.emit('download_failed', 'Song')
    assert d._pending == {}


def test_short_task_report():
    d = _dispatcher(_cfg(), [])
    rec = Recorder()
    d.task_finished('backup', 'Backup', summary=[('Songs', '12')])

    async def go():
        async with rec.client() as client:
            await d.tick(client)

    _run(go())
    assert rec.bodies()[0]['embeds'][0]['title'] == 'Backup: finished'


def test_send_failure_is_recorded_without_the_url():
    d = _dispatcher(_cfg(), [])
    rec = Recorder(status=404)
    d.emit('download_failed', 'Song')

    async def go():
        async with rec.client() as client:
            await d.tick(client, flush=True)

    _run(go())
    assert d.errors() == {'discord': 'Discord answered HTTP 404'}
    assert 'secret' not in json.dumps(d.errors())


def test_non_editable_channel_gets_quarters():
    cfg = notifications.effective({
        'enabled': True,
        'progress_seconds': 30,
        'channels': {
            'ntfy': {
                'enabled': True,
                'topic': 'downtify-test',
                'phases': ['progress'],
            }
        },
    })
    tasks = [Task('u:1', 'upgrade', 'Library upgrade', 'running', 0, 100)]
    d = _dispatcher(cfg, tasks)
    rec = Recorder()

    async def go():
        async with rec.client() as client:
            await d.tick(client)
            for done in (10, 30, 35, 60, 99):
                tasks[0] = Task(
                    'u:1', 'upgrade', 'Library upgrade', 'running', done, 100
                )
                d._live[('ntfy', 'u:1')].sent_at -= 60
                await d.tick(client)

    _run(go())
    # 30 -> first quarter, 60 -> second, 99 -> third.
    assert len(rec.requests) == 3
    body = rec.bodies()[0]
    assert body['topic'] == 'downtify-test'
    assert str(rec.requests[0].url) == 'https://ntfy.sh'


@pytest.mark.parametrize(
    ('name', 'ch', 'url', 'header'),
    [
        (
            'gotify',
            {'server': 'https://gotify.example', 'token': 'tok'},
            'https://gotify.example/message',
            ('x-gotify-key', 'tok'),
        ),
        (
            'webhook',
            {'url': 'https://apprise.example/notify/k'},
            'https://apprise.example/notify/k',
            None,
        ),
        (
            'ntfy',
            {'topic': 't', 'token': 'tk', 'server': 'https://n.example/'},
            'https://n.example',
            ('authorization', 'Bearer tk'),
        ),
    ],
)
def test_other_channels(name, ch, url, header):
    cfg = notifications.effective({'channels': {name: ch}})['channels'][name]
    rec = Recorder()
    msg = Message(title='T', text='x', level='error', event='download_failed')

    async def go():
        async with rec.client() as client:
            await notifications.make_channel(name, cfg).send(client, msg)

    _run(go())
    request = rec.requests[0]
    assert str(request.url) == url
    if header:
        assert request.headers[header[0]] == header[1]
    if name == 'webhook':
        body = rec.bodies()[0]
        assert body['title'] == 'T'
        assert body['type'] == 'failure'
        assert body['body'] == 'x'


def test_bot_channel_posts_to_the_channel():
    cfg = _cfg(mode='bot', bot_token='bot-secret', channel_id='42')
    d = _dispatcher(cfg, [])
    rec = Recorder()
    d.emit('new_releases', 'Artist', 'Album')

    async def go():
        async with rec.client() as client:
            await d.tick(client, flush=True)

    _run(go())
    request = rec.requests[0]
    assert request.url.path == '/api/v10/channels/42/messages'
    assert request.headers['authorization'] == 'Bot bot-secret'


# ── the Discord bot ─────────────────────────────────────────────────────


def test_refusal_rules():
    inter = {'channel_id': '1', 'member': {'user': {'id': '7'}}}
    assert discord_bot.refusal(inter, '1', set()) is None
    assert discord_bot.refusal(inter, '2', set())
    assert discord_bot.refusal(inter, '1', {'8'})
    assert discord_bot.refusal(inter, '1', {'7'}) is None


def test_invite_url_has_commands_scope():
    url = discord_bot.invite_url('123')
    assert 'client_id=123' in url
    assert 'applications.commands' in url


class FakeSocket:
    """Plays a gateway session: HELLO, READY, one command, then closes."""

    def __init__(self, events):
        self.events = [json.dumps(e) for e in events]
        self.sent = []
        self.close_code = 1000

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def recv(self):
        return self.events.pop(0)

    async def send(self, data):
        self.sent.append(json.loads(data))

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.events:
            raise StopAsyncIteration
        return self.events.pop(0)


def test_bot_session_registers_and_answers():
    command = {
        'op': 0,
        's': 2,
        't': 'INTERACTION_CREATE',
        'd': {
            'id': '9',
            'token': 'itoken',
            'type': 2,
            'channel_id': '42',
            'data': {'name': 'help'},
        },
    }
    ready = {
        'op': 0,
        's': 1,
        't': 'READY',
        'd': {'application': {'id': '555'}, 'user': {'username': 'dt'}},
    }
    sock = FakeSocket([
        {'op': 10, 'd': {'heartbeat_interval': 60000}},
        ready,
        command,
    ])
    rec = Recorder()
    bot = discord_bot.DiscordBot(
        lambda name, opts: Message(title=f'answer {name}'),
        connect=lambda url: sock,
    )
    bot._channel_id = '42'

    async def go():
        async with rec.client() as client:
            return await bot._session(client, 'bot-secret')

    assert _run(go()) is None
    identify = sock.sent[0]
    assert identify['op'] == 2
    assert identify['d']['intents'] == 0
    assert bot.state == 'connected'
    assert bot.status()['invite_url']
    paths = [r.url.path for r in rec.requests]
    assert paths == [
        '/api/v10/applications/555/commands',
        '/api/v10/interactions/9/itoken/callback',
    ]
    names = {c['name'] for c in rec.bodies()[0]}
    assert {'status', 'progress', 'queue', 'help', 'lyrics'} <= names
    reply = rec.bodies()[1]
    assert reply['type'] == discord_bot.REPLY
    assert reply['data']['embeds'][0]['title'] == 'answer help'


def test_rejected_token_is_fatal():
    sock = FakeSocket([{'op': 10, 'd': {'heartbeat_interval': 60000}}])
    sock.close_code = 4004
    bot = discord_bot.DiscordBot(
        lambda n, o: Message(title='x'), connect=lambda url: sock
    )

    async def go():
        async with Recorder().client() as client:
            return await bot._session(client, 'bad')

    assert _run(go()) == 'Discord rejected the bot token'


def test_apply_starts_and_stops_only_when_asked():
    bot = discord_bot.DiscordBot(lambda n, o: Message(title='x'))
    started = []

    async def fake_run(token):
        started.append(token)
        await asyncio.sleep(3600)

    bot._run = fake_run

    async def go():
        bot.apply(_cfg())  # webhook mode: no bot
        assert bot._task is None
        bot.apply(_cfg(mode='bot', bot_token='tok', channel_id='1'))
        await asyncio.sleep(0)
        assert started == ['tok']
        bot.apply(_cfg(mode='bot', bot_token='tok', channel_id='1'))
        await asyncio.sleep(0)
        assert started == ['tok']  # same token: left running
        bot.apply(notifications.effective({}))
        assert bot.state == 'off'
        await bot.stop()

    _run(go())


# ── sources and answers ─────────────────────────────────────────────────


def test_doctor_source_reads_the_job(monkeypatch):
    job = {
        'id': 'abc',
        'kind': 'health',
        'state': 'running',
        'progress': {'done': 3, 'total': 9, 'step': 'files'},
    }
    monkeypatch.setattr(notification_routes.doctor_routes, '_job', job)
    (task,) = notification_routes.doctor_tasks()
    assert task.key == 'doctor:abc'
    assert task.title == 'Doctor health check'
    assert (task.state, task.done, task.total, task.step) == (
        'running',
        3,
        9,
        'files',
    )
    job.update(state='failed', error={'code': 'x', 'message': 'boom'})
    (task,) = notification_routes.doctor_tasks()
    assert (task.state, task.error) == ('failed', 'boom')


def test_summary_fields():
    fields = notification_routes.summary_fields({
        'rated': 12,
        'skipped': 3,
        'changes': [1, 2],
        'problems': [1, 2, 3],
        'preview': True,
    })
    assert ('Rated', '12') in fields
    assert ('Problems', '3') in fields
    assert all(label != 'Preview' for label, _v in fields)


def test_upgrade_source_splits_scan_and_run(monkeypatch):
    class Runner:
        def __init__(self, status):
            self._status = status

        def status(self):
            return self._status

    run = {'id': 4, 'categories': ['artwork', 'lyrics']}
    scanning = {'state': 'scanning', 'run': run, 'scan': {'scanned': 5}}
    monkeypatch.setattr(
        notification_routes.api.state, 'upgrade_runner', Runner(scanning)
    )
    (scan,) = notification_routes.upgrade_tasks()
    assert scan.key == 'upgrade:4:scan'
    assert scan.title == 'Library upgrade (cover art, lyrics) scan'
    running = {
        'state': 'running',
        'run': run,
        'counts': {'total': 10, 'finished': 4, 'completed': 3},
        'lyrics': {'added': 2},
    }
    monkeypatch.setattr(
        notification_routes.api.state, 'upgrade_runner', Runner(running)
    )
    scan, work = notification_routes.upgrade_tasks()
    assert scan.state == 'done'
    assert (work.state, work.done, work.total) == ('running', 4, 10)
    assert ('Lyrics added', '2') in work.summary


def test_help_and_unknown_progress():
    assert '/status' in notification_routes.answer('help', {}).text
    assert notification_routes.answer(
        'progress', {'task': 'x'}
    ).title.startswith('Pick a task')


def test_queue_answer(monkeypatch):
    jobs = {
        'a': {'status': 'downloading', 'progress': 40, 'song': {'name': 'A'}},
        'b': {'status': 'queued', 'song': {}},
        'c': {'status': 'error', 'song': {}},
    }
    monkeypatch.setattr(notification_routes.api.state, 'download_jobs', jobs)
    msg = notification_routes.answer('queue', {})
    fields = dict(msg.fields)
    assert fields['Downloading'] == '1'
    assert fields['Waiting'] == '1'
    assert fields['Failed'] == '1'
    assert '40%' in msg.text


# ── the routes ──────────────────────────────────────────────────────────


@pytest.fixture
def routes(tmp_path, monkeypatch):
    monkeypatch.setattr(
        notification_routes.api.state, 'settings_path', tmp_path / 's.json'
    )
    d = Dispatcher()
    monkeypatch.setattr(notification_routes, 'dispatcher', d)
    return d


def test_save_never_returns_secrets(routes, tmp_path):
    body = notification_routes.SaveRequest(
        settings={
            'enabled': True,
            'channels': {'discord': {'enabled': True, 'webhook_url': WEBHOOK}},
        }
    )
    view = _run(notification_routes.notifications_save(body))
    assert 'secret-token' not in json.dumps(view)
    assert view['settings']['channels']['discord']['webhook_url_set'] is True
    saved = json.loads((tmp_path / notifications.FILE_NAME).read_text())
    assert saved['channels']['discord']['webhook_url'] == WEBHOOK
    # Saving again without the secret keeps it.
    body = notification_routes.SaveRequest(
        settings={'channels': {'discord': {'webhook_url': ''}}}
    )
    _run(notification_routes.notifications_save(body))
    assert routes.cfg['channels']['discord']['webhook_url'] == WEBHOOK


def test_test_route_uses_unsaved_values(routes, monkeypatch):
    sent = []

    async def fake_test(name, ch):
        sent.append((name, ch['topic']))

    monkeypatch.setattr(routes, 'test', fake_test)
    body = notification_routes.TestRequest(channel={'topic': 'mine'})
    assert _run(notification_routes.notifications_test('ntfy', body)) == {
        'ok': True
    }
    assert sent == [('ntfy', 'mine')]


def test_test_route_reports_failure(routes):
    body = notification_routes.TestRequest(channel={})
    with pytest.raises(notification_routes.HTTPException) as err:
        _run(notification_routes.notifications_test('gotify', body))
    assert err.value.status_code == 400
    with pytest.raises(notification_routes.HTTPException) as err:
        _run(notification_routes.notifications_test('pigeon', body))
    assert err.value.status_code == 404


def test_health_summary_counts_what_was_found():
    result = {
        'slskd': {'leftovers': 3},
        'duplicates': {
            'totals': {'exact': {'groups': 2}, 'likely': {'groups': 1}}
        },
        'playlists': {'groups': [{}, {}]},
        'relinked': {'songs': 5},
    }
    assert notification_routes.health_summary(result) == [
        ('slskd leftovers', '3'),
        ('Duplicate songs', '3'),
        ('Duplicate playlists', '2'),
        ('Songs to relink', '5'),
    ]
    assert notification_routes.health_summary(None) == []
