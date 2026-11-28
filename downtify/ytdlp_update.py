"""Keep yt-dlp up to date without waiting for a Downtify release.

YouTube changes its pages every few weeks and an older yt-dlp then fails
every download until someone updates it. With "Update yt-dlp by itself"
on (Settings > Sources > YouTube, off by default) this module, once a day:

1. asks PyPI for the newest yt-dlp release;
2. downloads its wheel and checks it against the SHA-256 PyPI lists;
3. unpacks only the ``yt_dlp`` package into ``<data>/yt-dlp/<version>/``
   (a wheel is a zip: nothing is installed and no setup code runs);
4. tests it in a separate Python process: it must read the formats of a
   known YouTube video, the same way a download starts;
5. when the test passes, saves it as the version to use. Downtify loads
   it at its next start (:mod:`downtify.ytdlp_boot`) and, with "Restart
   when it's quiet" on, restarts itself as soon as nothing is downloading
   or running.

A version that fails the test while the one in use passes is never used
(``rejected``). When both fail, YouTube itself may be unreachable, so
nothing changes and the next check tries again. The previous version is
kept, so Settings can go back to it - or to the image's own yt-dlp. A
saved copy that won't load at start is dropped the same way.

Every step that matters goes out as the ``ytdlp`` notification.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
from loguru import logger

from . import notifications, ytdlp_boot

PYPI_URL = 'https://pypi.org/pypi/yt-dlp/json'
#: "Me at the zoo", YouTube's first upload: never taken down.
TEST_VIDEO = 'jNQXAC9IVRw'
#: Seconds between two checks of PyPI.
CHECK_SECONDS = 24 * 3600
#: A check asked for because downloads keep failing waits this long
#: after the previous one.
URGENT_GAP_SECONDS = 2 * 3600
#: Seconds between two looks at whether a restart can happen.
TICK_SECONDS = 60
#: The first check waits this long after start, so boot isn't slowed.
STARTUP_DELAY_SECONDS = 120
TEST_TIMEOUT_SECONDS = 180
REQUEST_TIMEOUT = 30
#: Largest wheel accepted (yt-dlp's is about 3 MB).
MAX_WHEEL_BYTES = 40 * 1024 * 1024

DEFAULTS: dict[str, Any] = {
    'enabled': False,
    'auto_restart': True,
    'active': None,
    'previous': None,
    'latest': None,
    'checked_at': None,
    'error': None,
    'rejected': {},
    'notified_available': None,
    'announced': None,
}

_TEST_SCRIPT = r"""
import json, sys
folder, video, cookies, ipv4 = sys.argv[1:5]
if folder:
    sys.path.insert(0, folder)
out = {'ok': False}
try:
    import yt_dlp
    out['version'] = yt_dlp.version.__version__
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': True,
        'remote_components': ['ejs:github'],
    }
    if cookies:
        opts['cookiefile'] = cookies
    if ipv4:
        opts['source_address'] = '0.0.0.0'
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(
            'https://music.youtube.com/watch?v=' + video, download=False
        )
        audio = [
            f for f in (info or {}).get('formats') or []
            if f.get('acodec') not in (None, 'none')
            and f.get('vcodec') in (None, 'none')
            and f.get('url')
            and str(f.get('protocol') or '').startswith('http')
            and 'm3u8' not in str(f.get('protocol') or '')
        ]
        if not audio:
            raise RuntimeError('no audio formats found')
        # The start of the audio itself: reading the formats can work
        # while YouTube refuses the stream (HTTP 403).
        best = max(audio, key=lambda f: f.get('abr') or 0)
        from yt_dlp.networking import Request
        headers = dict(best.get('http_headers') or {})
        headers['Range'] = 'bytes=0-65535'
        resp = ydl.urlopen(Request(best['url'], headers=headers))
        data = resp.read(65536)
        out['bytes'] = len(data)
        if not data:
            raise RuntimeError('the audio stream sent nothing')
        out['ok'] = True
except BaseException as exc:
    out['error'] = (type(exc).__name__ + ': ' + str(exc))[:400]
print('YTDLP_TEST ' + json.dumps(out))
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def version_key(value: Optional[str]) -> tuple[int, ...]:
    """``'2026.11.23'`` -> ``(2026, 11, 23)``; ``()`` for anything else."""

    if not ytdlp_boot.valid_version(value):
        return ()
    return tuple(int(part) for part in str(value).split('.'))


def image_version() -> Optional[str]:
    """The yt-dlp that came with the image (not a saved copy, whose
    folder is first on ``sys.path`` with its own metadata)."""

    try:
        from importlib.metadata import distributions  # noqa: PLC0415

        saved = ytdlp_boot.BOOT.get('path')
        paths = [p for p in sys.path if p != saved]
        for dist in distributions(name='yt-dlp', path=paths):
            return dist.version
    except Exception:
        pass
    return None


def running_version() -> Optional[str]:
    """The yt-dlp loaded in this process."""

    try:
        import yt_dlp.version  # noqa: PLC0415

        return str(yt_dlp.version.__version__)
    except Exception:
        return ytdlp_boot.BOOT.get('version')


class UpdateError(RuntimeError):
    """A step of an update failed; the message says which, in words."""


def _safe_member(name: str, version: str) -> bool:
    parts = name.replace('\\', '/').split('/')
    if not parts or name.startswith('/') or '..' in parts:
        return False
    return parts[0] == 'yt_dlp' or parts[0] == f'yt_dlp-{version}.dist-info'


def unpack_wheel(wheel: Path, target: Path, version: str) -> None:
    """Unpack the ``yt_dlp`` package of *wheel* into *target*."""

    with zipfile.ZipFile(wheel) as archive:
        members = [
            m
            for m in archive.infolist()
            if not m.is_dir() and _safe_member(m.filename, version)
        ]
        if not any(m.filename == 'yt_dlp/__init__.py' for m in members):
            raise UpdateError('the download has no yt_dlp package')
        for member in members:
            dest = target / member.filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as src, dest.open('wb') as out:
                shutil.copyfileobj(src, out)


def pick_wheel(release: dict[str, Any]) -> dict[str, Any]:
    """PyPI's entry for the pure-Python wheel of the newest release."""

    version = str((release.get('info') or {}).get('version') or '')
    if not ytdlp_boot.valid_version(version):
        raise UpdateError(f'PyPI named an unexpected version {version!r}')
    for entry in release.get('urls') or []:
        name = str(entry.get('filename') or '')
        sha = (entry.get('digests') or {}).get('sha256')
        if (
            entry.get('packagetype') == 'bdist_wheel'
            and name.endswith('-py3-none-any.whl')
            and not entry.get('yanked')
            and isinstance(sha, str)
            and len(sha) == 64
        ):
            return {
                'version': version,
                'url': entry.get('url'),
                'sha256': sha.lower(),
                'size': int(entry.get('size') or 0),
            }
    raise UpdateError(f'PyPI has no wheel for yt-dlp {version}')


class YtdlpUpdater:
    """The saved settings and the work of one Downtify process."""

    def __init__(
        self,
        base: Path,
        *,
        cookies_file: Callable[[], Optional[str]] = lambda: None,
        is_idle: Callable[[], bool] = lambda: True,
        restart: Callable[[], bool] = lambda: False,
        http_get: Callable[..., Any] = httpx.get,
        run: Callable[..., Any] = subprocess.run,
        emit: Callable[[str, str, str], None] = notifications.emit,
        boot: Optional[dict[str, Any]] = None,
    ) -> None:
        self.base = Path(base)
        self.cookies_file = cookies_file
        self.is_idle = is_idle
        self.restart = restart
        self.http_get = http_get
        self.run = run
        self.emit = emit
        self.boot = boot if boot is not None else ytdlp_boot.BOOT
        self._lock = threading.Lock()
        self._busy = False
        self._last_check = 0.0
        self._urgent = False
        self._restarting = False
        self.phase: Optional[str] = None

    # -- saved state ----------------------------------------------------

    @property
    def path(self) -> Path:
        return self.base / ytdlp_boot.STATE_FILE

    def load(self) -> dict[str, Any]:
        raw = ytdlp_boot.read_state(self.base)
        state = {**DEFAULTS, **{k: v for k, v in raw.items() if k in DEFAULTS}}
        state['enabled'] = state['enabled'] is True
        state['auto_restart'] = state['auto_restart'] is not False
        for key in ('active', 'previous', 'latest'):
            if not ytdlp_boot.valid_version(state[key]):
                state[key] = None
        if not isinstance(state['rejected'], dict):
            state['rejected'] = {}
        return state

    def save(self, state: dict[str, Any]) -> None:
        self.base.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, indent=2), 'utf-8')
        tmp.replace(self.path)

    def _update(self, **changes: Any) -> dict[str, Any]:
        with self._lock:
            state = self.load()
            state.update(changes)
            self.save(state)
            return state

    # -- what Settings shows ---------------------------------------------

    def restart_pending(self, state: Optional[dict[str, Any]] = None) -> bool:
        """Whether the yt-dlp to use differs from the one loaded."""

        state = state or self.load()
        if not state['enabled'] or not state['active']:
            return self.boot.get('source') == 'saved'
        return state['active'] != running_version()

    def status(self) -> dict[str, Any]:
        state = self.load()
        return {
            'enabled': state['enabled'],
            'auto_restart': state['auto_restart'],
            'running': running_version(),
            'running_source': self.boot.get('source') or 'image',
            'image': image_version(),
            'active': state['active'],
            'previous': state['previous'],
            'latest': state['latest'],
            'checked_at': state['checked_at'],
            'error': state['error'],
            'boot_error': self.boot.get('error'),
            'restart_pending': self.restart_pending(state),
            'busy': self._busy,
            'phase': self.phase,
            'update_available': bool(
                state['latest']
                and version_key(state['latest'])
                > version_key(running_version())
            ),
        }

    def configure(
        self,
        *,
        enabled: Optional[bool] = None,
        auto_restart: Optional[bool] = None,
    ) -> dict[str, Any]:
        changes: dict[str, Any] = {}
        if enabled is not None:
            changes['enabled'] = bool(enabled)
        if auto_restart is not None:
            changes['auto_restart'] = bool(auto_restart)
        if changes:
            self._update(**changes)
        if enabled:
            self._last_check = 0.0
        return self.status()

    def use(self, which: str) -> dict[str, Any]:
        """Go back to the ``previous`` saved version or to the ``image``'s
        own yt-dlp; it applies at the next restart."""

        state = self.load()
        if which == 'image':
            # Off as well: otherwise the next check installs it again.
            self._update(
                enabled=False,
                active=None,
                previous=state['active'] or state['previous'],
            )
        elif which == 'previous':
            prev = state['previous']
            if not prev or not self._installed(prev):
                raise UpdateError('There is no previous version to go back to')
            rejected = dict(state['rejected'])
            if state['active']:
                # The next check must not bring it straight back.
                rejected[state['active']] = 'You went back from this version'
            self._update(
                active=prev, previous=state['active'], rejected=rejected
            )
        else:
            raise UpdateError(f'Unknown choice {which!r}')
        return self.status()

    # -- start ------------------------------------------------------------

    def after_boot(self) -> None:
        """Note what happened at start: a saved copy that wouldn't load
        is dropped; a newly used version is announced once."""

        state = self.load()
        wanted = self.boot.get('wanted')
        if wanted and self.boot.get('source') != 'saved':
            reason = self.boot.get('error') or 'it would not load'
            rejected = {**state['rejected'], wanted: reason}
            back = state['previous'] if state['previous'] != wanted else None
            if back and not self._installed(back):
                back = None
            self._update(active=back, previous=None, rejected=rejected)
            logger.warning(
                'yt-dlp {} did not load ({}); using {}',
                wanted,
                reason,
                back or 'the built-in yt-dlp',
            )
            self.emit(
                'ytdlp',
                f'{wanted} would not load',
                f'{reason}. Downtify uses '
                f'{back or "its built-in yt-dlp"} instead.',
            )
            return
        version = running_version()
        if (
            self.boot.get('source') == 'saved'
            and version
            and state['announced'] != version
        ):
            self._update(announced=version)
            self.emit(
                'ytdlp',
                f'Now using {version}',
                'Downtify restarted with the updated yt-dlp.',
            )

    # -- checking ---------------------------------------------------------

    def _installed(self, version: str) -> bool:
        folder = ytdlp_boot.version_dir(self.base, version)
        return (folder / 'yt_dlp' / '__init__.py').is_file()

    def ask_soon(self) -> None:
        """YouTube downloads keep failing: check before the day is over."""

        self._urgent = True

    def check_due(self, now: Optional[float] = None) -> bool:
        """Daily while switched on. While off, PyPI is only asked when
        YouTube downloads keep failing, to say an update is out."""

        now = time.monotonic() if now is None else now
        if not self._urgent and not self.load()['enabled']:
            return False
        gap = URGENT_GAP_SECONDS if self._urgent else CHECK_SECONDS
        return not self._last_check or now - self._last_check >= gap

    def latest_release(self) -> dict[str, Any]:
        resp = self.http_get(
            PYPI_URL,
            timeout=REQUEST_TIMEOUT,
            headers={'Accept': 'application/json'},
            follow_redirects=True,
        )
        resp.raise_for_status()
        return pick_wheel(resp.json())

    def check_now(self) -> dict[str, Any]:
        """One full check (blocking: run it in a thread). Never raises:
        the outcome is in :meth:`status`."""

        with self._lock:
            if self._busy:
                return self.status()
            self._busy = True
        self._last_check = time.monotonic()
        urgent, self._urgent = self._urgent, False
        try:
            self._check(urgent)
        except UpdateError as exc:
            self._update(error=str(exc), checked_at=_now())
            logger.warning('yt-dlp update: {}', exc)
        except Exception as exc:
            self._update(
                error=f'{type(exc).__name__}: {exc}', checked_at=_now()
            )
            logger.opt(exception=True).warning('yt-dlp update check failed')
        finally:
            self._busy = False
            self.phase = None
        return self.status()

    def _check(self, urgent: bool) -> None:
        self.phase = 'checking'
        try:
            wheel = self.latest_release()
        except UpdateError:
            raise
        except Exception as exc:
            raise UpdateError(f'Could not ask PyPI: {exc}') from exc
        latest = wheel['version']
        state = self._update(latest=latest, checked_at=_now(), error=None)
        current = running_version()
        newest_have = max(version_key(current), version_key(state['active']))
        if version_key(latest) <= newest_have:
            return
        if not state['enabled']:
            if state['notified_available'] != latest:
                self._update(notified_available=latest)
                self.emit(
                    'ytdlp',
                    f'Update available: {latest}',
                    f'Downtify uses yt-dlp {current}. Turn on "Update '
                    'yt-dlp by itself" in Settings > Sources, or update '
                    'Downtify when a release has it.',
                )
            return
        if latest in state['rejected']:
            return
        self._install(wheel, current, urgent=urgent)

    def _download(self, wheel: dict[str, Any], dest: Path) -> None:
        self.phase = 'downloading'
        resp = self.http_get(
            wheel['url'], timeout=REQUEST_TIMEOUT * 4, follow_redirects=True
        )
        resp.raise_for_status()
        data = resp.content
        if len(data) > MAX_WHEEL_BYTES:
            raise UpdateError('The download is far larger than expected')
        digest = hashlib.sha256(data).hexdigest()
        if digest != wheel['sha256']:
            raise UpdateError(
                'The download did not match the checksum PyPI lists'
            )
        dest.write_bytes(data)

    def test(self, folder: Optional[Path]) -> dict[str, Any]:
        """Run the test video through the yt-dlp in *folder* (``None``:
        the one in the image), in a separate Python process."""

        cookies_copy = None
        source = self.cookies_file()
        try:
            if source and Path(source).is_file():
                handle, name = tempfile.mkstemp(suffix='.txt')
                os.close(handle)
                shutil.copyfile(source, name)
                cookies_copy = name
            ipv4 = os.getenv('DOWNTIFY_FORCE_IPV4', '').strip().lower()
            args = [
                sys.executable,
                '-I',
                '-c',
                _TEST_SCRIPT,
                str(folder) if folder else '',
                TEST_VIDEO,
                cookies_copy or '',
                '1' if ipv4 in {'1', 'true', 'yes'} else '',
            ]
            try:
                proc = self.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=TEST_TIMEOUT_SECONDS,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return {'ok': False, 'error': 'the test took too long'}
            for line in (proc.stdout or '').splitlines():
                if line.startswith('YTDLP_TEST '):
                    try:
                        return json.loads(line[len('YTDLP_TEST ') :])
                    except ValueError:
                        break
            tail = (proc.stderr or '').strip().splitlines()[-1:] or ['']
            return {'ok': False, 'error': tail[0][:400] or 'no answer'}
        finally:
            if cookies_copy:
                try:
                    os.unlink(cookies_copy)
                except OSError:
                    pass

    def _current_folder(self) -> Optional[Path]:
        path = self.boot.get('path')
        return (
            Path(path) if path and self.boot.get('source') == 'saved' else None
        )

    def _install(
        self, wheel: dict[str, Any], current: Optional[str], *, urgent: bool
    ) -> None:
        version = wheel['version']
        root = self.base / ytdlp_boot.VERSIONS_DIR
        root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f'.new-{version}-', dir=root))
        try:
            wheel_file = staging / 'yt_dlp.whl'
            self._download(wheel, wheel_file)
            folder = staging / 'pkg'
            unpack_wheel(wheel_file, folder, version)
            wheel_file.unlink()
            self.phase = 'testing'
            result = self.test(folder)
            if result.get('ok') and result.get('version') == version:
                self._keep(folder, version)
                return
            reason = result.get('error') or (
                f'it reported version {result.get("version")}'
            )
            baseline = self.test(self._current_folder())
            if baseline.get('ok'):
                state = self.load()
                self._update(rejected={**state['rejected'], version: reason})
                logger.warning(
                    'yt-dlp {} failed the test ({}); staying on {}',
                    version,
                    reason,
                    current,
                )
                self.emit(
                    'ytdlp',
                    f'{version} failed the test',
                    f'{reason}. Downtify stays on {current}, which works.',
                )
                return
            raise UpdateError(
                f'Could not test yt-dlp {version}: {reason}. The version '
                f'in use fails the same test, so YouTube may be '
                'unreachable or need fresh cookies. Trying again later.'
            )
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def _keep(self, folder: Path, version: str) -> None:
        final = ytdlp_boot.version_dir(self.base, version)
        if final.exists():
            shutil.rmtree(final)
        folder.replace(final)
        state = self.load()
        previous = state['active'] if state['active'] != version else None
        state = self._update(active=version, previous=previous, error=None)
        self._prune(state)
        logger.info('yt-dlp {} passed the test and is ready', version)
        how = (
            'Downtify restarts to use it once nothing is downloading.'
            if state['auto_restart']
            else 'Restart Downtify to use it (Settings > Sources).'
        )
        self.emit(
            'ytdlp', f'Updated to {version}', f'It passed the test. {how}'
        )

    def _prune(self, state: dict[str, Any]) -> None:
        keep = {state['active'], state['previous'], running_version()}
        root = self.base / ytdlp_boot.VERSIONS_DIR
        for child in root.iterdir() if root.is_dir() else []:
            if not child.is_dir() or child.name in keep:
                continue
            # Old versions, and work folders left by a crash mid-update.
            if ytdlp_boot.valid_version(child.name) or child.name.startswith(
                '.new-'
            ):
                shutil.rmtree(child, ignore_errors=True)

    # -- restarting -------------------------------------------------------

    def maybe_restart(self) -> bool:
        """Restart when a different yt-dlp is waiting and nothing runs."""

        if self._restarting or self._busy:
            return False
        state = self.load()
        if not state['enabled'] or not state['auto_restart']:
            return False
        if not self.restart_pending(state):
            return False
        try:
            idle = self.is_idle()
        except Exception:
            logger.opt(exception=True).debug('yt-dlp update: idle check')
            idle = False
        if not idle:
            return False
        self._restarting = True
        logger.info(
            'Restarting Downtify to use yt-dlp {}',
            state['active'] or 'from the image',
        )
        if not self.restart():
            self._restarting = False
            return False
        return True

    def restart_now(self) -> bool:
        self._restarting = True
        if not self.restart():
            self._restarting = False
            return False
        return True


async def ytdlp_update_loop(updater: YtdlpUpdater) -> None:
    """Background task: check PyPI daily (sooner while YouTube downloads
    keep failing) and restart onto a tested version when it's quiet."""

    try:
        await asyncio.to_thread(updater.after_boot)
    except Exception:
        logger.exception('yt-dlp update: start-up note failed')
    await asyncio.sleep(STARTUP_DELAY_SECONDS)
    while True:
        try:
            if updater.check_due():
                await asyncio.to_thread(updater.check_now)
            updater.maybe_restart()
        except Exception:
            logger.exception('Unexpected error in yt-dlp update loop')
        await asyncio.sleep(TICK_SECONDS)
