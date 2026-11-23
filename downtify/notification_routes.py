"""``/api/notifications`` (admins): Settings > Notifications.

* ``GET  /api/notifications`` - the settings (secrets only say whether
  they are set), each channel's last error and the Discord bot's state.
* ``PUT  /api/notifications`` - save them; ``clear`` lists the secrets
  to remove (``discord.bot_token``...).
* ``POST /api/notifications/test/{channel}`` - send a test message, with
  the page's unsaved values (a blank secret uses the saved one).

This module also connects :mod:`downtify.notifications` to the jobs: the
task sources read the live job records the Doctor, Library upgrade,
star ratings and Wanted routes keep for their pages, and
:func:`answer` builds the replies to the Discord commands from the same
records.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import (
    api,
    doctor_routes,
    navidrome_ratings_routes,
    notifications,
    wanted_routes,
)
from .admin_access import admin_user
from .discord_bot import DiscordBot
from .notifications import Message, Task, dispatcher, progress_bar

router = APIRouter(
    prefix='/api/notifications', dependencies=[Depends(admin_user)]
)

DOCTOR_TITLES = {
    'health': 'Doctor health check',
    'slskd': 'Doctor slskd check',
    'slskd_clean': 'Doctor slskd cleanup',
    'merge': 'Doctor duplicate merge',
    'playlists': 'Doctor playlist repair',
    'navidrome': 'Doctor Navidrome repair',
    'dedupe': 'Doctor Navidrome duplicates',
}

UPGRADE_CATEGORIES = {
    'artwork': 'cover art',
    'lyrics': 'lyrics',
    'metadata': 'tags',
    'isrc': 'ISRC codes',
    'audio': 'audio',
}

#: Result fields worth a line in a finish message, with their labels.
_LABELS = {
    'rated': 'Rated',
    'skipped': 'Skipped',
    'not_found': 'Not found',
    'removed': 'Removed',
    'deleted': 'Deleted',
    'merged': 'Merged',
    'fixed': 'Fixed',
    'repaired': 'Repaired',
    'checked': 'Checked',
    'found': 'Found',
    'problems': 'Problems',
    'issues': 'Issues',
    'completed': 'Updated',
    'failed': 'Failed',
    'total': 'Total',
}


def _data_dir() -> Path:
    path = api.state.settings_path
    return Path(path).parent if path else Path('/data')


def _path() -> Path:
    return _data_dir() / notifications.FILE_NAME


# ---------------------------------------------------------------------------
# Task sources
# ---------------------------------------------------------------------------


def summary_fields(result: Any, limit: int = 6) -> list[tuple[str, str]]:
    """A few counts from a job's *result* for a finish message."""

    if not isinstance(result, dict):
        return []
    fields: list[tuple[str, str]] = []
    for key, label in _LABELS.items():
        value = result.get(key)
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float)):
            fields.append((label, f'{value:,}'))
        elif isinstance(value, (list, dict)) and key in {
            'problems',
            'issues',
            'removed',
            'deleted',
            'merged',
            'fixed',
        }:
            fields.append((label, f'{len(value):,}'))
        if len(fields) >= limit:
            break
    return fields


def _error_text(error: Any) -> str:
    if isinstance(error, dict):
        return str(error.get('message') or error.get('code') or '')[:300]
    return str(error or '')[:300]


def _job_task(
    source: str, kind: str, title: str, job: dict[str, Any]
) -> Optional[Task]:
    """A Doctor or ratings style job record (``state``, ``progress``,
    ``result``, ``error``) as a :class:`Task`."""

    if not job or not job.get('id'):
        return None
    state = str(job.get('state') or '')
    state = {'running': 'running', 'done': 'done', 'stopped': 'stopped'}.get(
        state, 'failed' if state == 'failed' else 'done'
    )
    progress = job.get('progress') or {}
    return Task(
        key=f'{source}:{job["id"]}',
        kind=kind,
        title=title,
        state=state,
        done=int(progress.get('done') or 0),
        total=int(progress.get('total') or 0),
        step=str(progress.get('step') or ''),
        summary=summary_fields(job.get('result')),
        error=_error_text(job.get('error')),
    )


def _count(value: Any) -> int:
    if isinstance(value, (list, dict)):
        return len(value)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def health_summary(result: Any) -> list[tuple[str, str]]:
    """What the Doctor's health check found, in four counts."""

    if not isinstance(result, dict):
        return []
    slskd = result.get('slskd') or {}
    totals = (result.get('duplicates') or {}).get('totals') or {}
    groups = sum(
        _count((totals.get(kind) or {}).get('groups'))
        for kind in ('exact', 'likely')
    )
    playlists = (result.get('playlists') or {}).get('groups')
    relinked = (result.get('relinked') or {}).get('songs')
    return [
        ('slskd leftovers', f'{_count(slskd.get("leftovers")):,}'),
        ('Duplicate songs', f'{groups:,}'),
        ('Duplicate playlists', f'{_count(playlists):,}'),
        ('Songs to relink', f'{_count(relinked):,}'),
    ]


def doctor_tasks() -> list[Task]:
    job = dict(doctor_routes._job)
    kind = str(job.get('kind') or '')
    task = _job_task(
        'doctor', 'doctor', DOCTOR_TITLES.get(kind, 'Doctor'), job
    )
    if task is not None and kind == 'health':
        task.summary = health_summary(job.get('result'))
    return [task] if task else []


def ratings_tasks() -> list[Task]:
    job = dict(navidrome_ratings_routes._job)
    title = 'Star ratings preview' if job.get('preview') else 'Star ratings'
    task = _job_task('ratings', 'ratings', title, job)
    if task is not None and isinstance(job.get('result'), dict):
        task.summary = summary_fields(job['result'])
    return [task] if task else []


def wanted_tasks() -> list[Task]:
    job = dict(wanted_routes._job)
    if not job.get('id'):
        return []
    if job.get('running'):
        state = 'running'
    elif job.get('stopped'):
        state = 'stopped'
    else:
        state = 'done'
    title = (
        'Wanted: download missing'
        if job.get('kind') == 'download'
        else 'Wanted: check releases'
    )
    return [
        Task(
            key=f'wanted:{job["id"]}',
            kind='wanted',
            title=title,
            state=state,
            done=int(job.get('done') or 0),
            total=int(job.get('total') or 0),
            step=str(job.get('current') or ''),
            summary=[
                ('Done', f'{int(job.get("done") or 0):,}'),
                ('Failed', f'{int(job.get("failed") or 0):,}'),
                ('Skipped', f'{int(job.get("skipped") or 0):,}'),
            ],
        )
    ]


def upgrade_title(run: dict[str, Any]) -> str:
    names = [UPGRADE_CATEGORIES.get(c, c) for c in run.get('categories') or []]
    return 'Library upgrade' + (f' ({", ".join(names)})' if names else '')


def upgrade_tasks() -> list[Task]:
    """The Library upgrade's latest run: its scan and its repairs are
    two tasks, since the scan stops to let the admin pick."""

    runner = api.state.upgrade_runner
    if runner is None:
        return []
    status = runner.status()
    run = status.get('run')
    if not run:
        return []
    run_state = str(status.get('state') or '')
    title = upgrade_title(run)
    if run_state == 'scanning':
        scan = status.get('scan') or {}
        return [
            Task(
                key=f'upgrade:{run["id"]}:scan',
                kind='upgrade',
                title=f'{title} scan',
                state='running',
                done=int(scan.get('scanned') or 0),
                total=int(scan.get('total') or 0),
                step='Reading the library',
            )
        ]
    counts = status.get('counts') or {}
    scan_task = Task(
        key=f'upgrade:{run["id"]}:scan',
        kind='upgrade',
        title=f'{title} scan',
        state='stopped' if run_state == 'cancelled' else 'done',
        summary=[('To fix', f'{int(counts.get("total") or 0):,}')],
    )
    if run_state == 'ready':
        return [scan_task]
    state = {
        'running': 'running',
        'paused': 'running',
        'done': 'done',
        'cancelled': 'stopped',
    }.get(run_state, 'done')
    summary = [
        ('Updated', f'{int(counts.get("completed") or 0):,}'),
        ('Skipped', f'{int(counts.get("skipped") or 0):,}'),
        ('Failed', f'{int(counts.get("failed") or 0):,}'),
    ]
    lyrics = status.get('lyrics') or {}
    if 'lyrics' in (run.get('categories') or []):
        summary.append(('Lyrics added', f'{int(lyrics.get("added") or 0):,}'))
    return [
        scan_task,
        Task(
            key=f'upgrade:{run["id"]}:run',
            kind='upgrade',
            title=title,
            state=state,
            done=int(counts.get('finished') or 0),
            total=int(counts.get('total') or 0),
            step='Paused' if run_state == 'paused' else '',
            summary=summary,
        ),
    ]


SOURCES = {
    'doctor': doctor_tasks,
    'ratings': ratings_tasks,
    'wanted': wanted_tasks,
    'upgrade': upgrade_tasks,
}


# ---------------------------------------------------------------------------
# Discord commands
# ---------------------------------------------------------------------------

HELP_LINES = [
    ('/status', 'everything Downtify is doing now'),
    ('/progress task', 'one task: Doctor, Library upgrade, ratings…'),
    ('/queue', 'the download queue'),
    ('/doctor', 'the Doctor’s running or last job'),
    ('/upgrade', 'the Library upgrade (cover art, lyrics, tags)'),
    ('/lyrics', 'what the lyrics part of the upgrade found'),
    ('/ratings', 'the Navidrome star ratings'),
    ('/wanted', 'the Wanted catch-up of the artist watches'),
]


def _task_answer(tasks: list[Task], nothing: str) -> Message:
    if not tasks:
        return Message(title=nothing)
    task = next((t for t in tasks if t.state == 'running'), tasks[-1])
    phase = (
        'progress'
        if task.state == 'running'
        else ('fail' if task.state == 'failed' else 'finish')
    )
    return notifications.task_message(task, phase)


def queue_answer() -> Message:
    jobs = list(api.state.download_jobs.values())
    counts: dict[str, int] = {}
    for job in jobs:
        status = str(job.get('status') or '')
        counts[status] = counts.get(status, 0) + 1
    paused = api._global_queue_status().get('paused')
    lines = []
    for job in jobs:
        if job.get('status') == 'downloading':
            pct = int(float(job.get('progress') or 0))
            lines.append(f'⬇ {api.song_label(job.get("song") or {})} {pct}%')
        if len(lines) >= 10:
            break
    return Message(
        title='Download queue' + (' (paused)' if paused else ''),
        text='\n'.join(lines) or 'Nothing is downloading.',
        fields=[
            ('Downloading', f'{counts.get("downloading", 0):,}'),
            ('Waiting', f'{counts.get("queued", 0):,}'),
            ('Done', f'{counts.get("done", 0):,}'),
            ('Failed', f'{counts.get("error", 0):,}'),
        ],
        event='queue',
    )


def lyrics_answer() -> Message:
    runner = api.state.upgrade_runner
    status = runner.status() if runner is not None else {}
    run = status.get('run') or {}
    if 'lyrics' not in (run.get('categories') or []):
        return Message(
            title='Lyrics',
            text='The last Library upgrade did not look for lyrics.',
        )
    found = status.get('lyrics') or {}
    return Message(
        title=f'Lyrics: {upgrade_title(run)}',
        text=f'State: {status.get("state")}',
        fields=[
            ('Added', f'{int(found.get("added") or 0):,}'),
            ('None found', f'{int(found.get("not_found") or 0):,}'),
            ('Failed', f'{int(found.get("failed") or 0):,}'),
            ('Still to go', f'{int(found.get("pending") or 0):,}'),
        ],
        event='upgrade',
    )


def ratings_answer() -> Message:
    msg = _task_answer(ratings_tasks(), 'No star ratings run yet.')
    state = navidrome_ratings_routes._read_state()
    due = None
    try:
        if navidrome_ratings_routes._navidrome_ready() is not None:
            due = navidrome_ratings_routes.next_run_at(
                navidrome_ratings_routes._saved_options(),
                state.get('last_rating_run'),
            )
    except Exception:
        due = None
    if due is not None:
        msg.fields.append(('Next run', due.strftime('%Y-%m-%d %H:%M UTC')))
    return msg


def status_answer() -> Message:
    running = [t for t in dispatcher.read_tasks() if t.state == 'running']
    lines = [
        f'**{t.title}** {progress_bar(t.done, t.total)}'
        + (f' - {t.step}' if t.step else '')
        for t in running
    ]
    queue = queue_answer()
    return Message(
        title='Downtify status',
        text='\n'.join(lines) or 'No long task is running.',
        fields=queue.fields,
        event='status',
    )


def answer(name: str, options: dict[str, Any]) -> Message:
    """The reply to Discord command */name* (runs in a thread)."""

    if name == 'progress':
        name = str(options.get('task') or '')
        if name not in {'doctor', 'upgrade', 'ratings', 'wanted', 'queue'}:
            return Message(title='Pick a task: doctor, upgrade, ratings…')
    if name == 'status':
        return status_answer()
    if name == 'queue':
        return queue_answer()
    if name == 'doctor':
        return _task_answer(doctor_tasks(), 'The Doctor has not run yet.')
    if name == 'upgrade':
        return _task_answer(upgrade_tasks(), 'No Library upgrade yet.')
    if name == 'lyrics':
        return lyrics_answer()
    if name == 'ratings':
        return ratings_answer()
    if name == 'wanted':
        return _task_answer(wanted_tasks(), 'No Wanted job yet.')
    return Message(
        title='Downtify commands',
        text='\n'.join(f'`{cmd}` {what}' for cmd, what in HELP_LINES),
    )


bot = DiscordBot(answer)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


def setup() -> None:
    """Load the saved settings and hook up the sources and the bot."""

    for name, source in SOURCES.items():
        dispatcher.register_source(name, source)
    if bot.apply not in dispatcher.on_config:
        dispatcher.on_config.append(bot.apply)
    dispatcher.configure(notifications.load(_path()))


async def run() -> None:
    """The dispatcher loop (started with the server)."""

    setup()
    try:
        await dispatcher.run()
    finally:
        await bot.stop()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


class SaveRequest(BaseModel):
    settings: dict[str, Any]
    clear: list[str] = []


class TestRequest(BaseModel):
    channel: dict[str, Any] = {}


def _view() -> dict[str, Any]:
    return {
        'settings': notifications.public(dispatcher.cfg),
        'errors': dispatcher.errors(),
        'bot': bot.status(),
        'tasks': list(notifications.TASKS),
        'phases': list(notifications.PHASES),
        'events': list(notifications.EVENTS),
        'progress_choices': list(notifications.PROGRESS_CHOICES),
    }


@router.get('')
async def notifications_status() -> dict[str, Any]:
    return _view()


@router.put('')
async def notifications_save(body: SaveRequest) -> dict[str, Any]:
    cfg = notifications.merge_update(
        dispatcher.cfg, body.settings, clear=tuple(body.clear)
    )
    try:
        notifications.save(_path(), cfg)
    except OSError as exc:
        raise HTTPException(
            500, detail={'code': 'save_failed', 'message': str(exc)}
        ) from None
    dispatcher.configure(cfg)
    return _view()


@router.post('/test/{channel}')
async def notifications_test(
    channel: str, body: TestRequest
) -> dict[str, Any]:
    if channel not in notifications.CHANNELS:
        raise HTTPException(404, detail={'code': 'unknown_channel'})
    cfg = notifications.merge_update(
        dispatcher.cfg, {'channels': {channel: body.channel}}
    )
    try:
        await dispatcher.test(channel, cfg['channels'][channel])
    except notifications.SendError as exc:
        raise HTTPException(
            400, detail={'code': 'send_failed', 'message': str(exc)}
        ) from None
    return {'ok': True}
