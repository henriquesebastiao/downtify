"""yt-dlp updating itself (downtify/ytdlp_update.py, ytdlp_boot.py)."""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from downtify import ytdlp_boot, ytdlp_update
from downtify.ytdlp_update import UpdateError, YtdlpUpdater

ROOT = Path(__file__).resolve().parents[1]
NEW = '2099.1.2'
OLD = '2099.1.1'


def _wheel(version: str = NEW, extra: dict[str, str] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as archive:
        archive.writestr('yt_dlp/__init__.py', 'from . import version\n')
        archive.writestr('yt_dlp/version.py', f'__version__ = {version!r}\n')
        archive.writestr(
            f'yt_dlp-{version}.dist-info/METADATA', 'Name: yt-dlp'
        )
        for name, text in (extra or {}).items():
            archive.writestr(name, text)
    return buf.getvalue()


def _release(version: str, data: bytes) -> dict:
    return {
        'info': {'version': version},
        'urls': [
            {
                'packagetype': 'sdist',
                'filename': f'yt_dlp-{version}.tar.gz',
                'url': 'https://files.example/sdist',
                'digests': {'sha256': 'a' * 64},
            },
            {
                'packagetype': 'bdist_wheel',
                'filename': f'yt_dlp-{version}-py3-none-any.whl',
                'url': 'https://files.example/wheel',
                'digests': {'sha256': hashlib.sha256(data).hexdigest()},
                'size': len(data),
            },
        ],
    }


class _Resp:
    def __init__(self, *, payload=None, content=b''):
        self._payload = payload
        self.content = content

    @staticmethod
    def raise_for_status():
        return None

    def json(self):
        return self._payload


class _Fake:
    """PyPI, the test process and the notifications of one updater."""

    def __init__(self, version=NEW, data=None):
        self.data = _wheel(version) if data is None else data
        self.release = _release(version, self.data)
        self.results: list[dict] = []
        self.tested: list[str] = []
        self.sent: list[tuple[str, str, str]] = []
        self.restarts = 0
        self.idle = True

    def get(self, url, **_kw):
        if url == ytdlp_update.PYPI_URL:
            return _Resp(payload=self.release)
        return _Resp(content=self.data)

    def run(self, args, **_kw):
        self.tested.append(args[4])
        result = self.results.pop(0) if self.results else {'ok': True}
        return SimpleNamespace(
            stdout='noise\nYTDLP_TEST ' + json.dumps(result) + '\n',
            stderr='',
        )

    def emit(self, event, title, text):
        self.sent.append((event, title, text))

    def restart(self):
        self.restarts += 1
        return True


@pytest.fixture
def running(monkeypatch):
    version = {'value': OLD}
    monkeypatch.setattr(
        ytdlp_update, 'running_version', lambda: version['value']
    )
    return version


def _updater(tmp_path, fake, boot=None):
    return YtdlpUpdater(
        tmp_path,
        http_get=fake.get,
        run=fake.run,
        emit=fake.emit,
        restart=fake.restart,
        is_idle=lambda: fake.idle,
        boot=boot if boot is not None else {'source': 'image'},
    )


# -- PyPI and the wheel ---------------------------------------------------


def test_pick_wheel_takes_the_pure_python_wheel():
    data = _wheel()
    picked = ytdlp_update.pick_wheel(_release(NEW, data))

    assert picked['version'] == NEW
    assert picked['url'] == 'https://files.example/wheel'
    assert picked['sha256'] == hashlib.sha256(data).hexdigest()


def test_pick_wheel_refuses_odd_versions_and_yanked_files():
    with pytest.raises(UpdateError):
        ytdlp_update.pick_wheel({'info': {'version': '../evil'}, 'urls': []})
    release = _release(NEW, _wheel())
    release['urls'][1]['yanked'] = True
    with pytest.raises(UpdateError):
        ytdlp_update.pick_wheel(release)


def test_unpack_keeps_only_the_package(tmp_path):
    wheel = tmp_path / 'w.whl'
    wheel.write_bytes(
        _wheel(
            extra={
                '../escape.py': 'x',
                'other_pkg/__init__.py': 'x',
                'yt_dlp/../../up.py': 'x',
            }
        )
    )
    target = tmp_path / 'out'
    ytdlp_update.unpack_wheel(wheel, target, NEW)

    found = sorted(
        p.relative_to(target).as_posix()
        for p in target.rglob('*')
        if p.is_file()
    )
    assert found == [
        f'yt_dlp-{NEW}.dist-info/METADATA',
        'yt_dlp/__init__.py',
        'yt_dlp/version.py',
    ]
    assert not (tmp_path / 'escape.py').exists()


def test_unpack_needs_the_yt_dlp_package(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as archive:
        archive.writestr('something/__init__.py', '')
    wheel = tmp_path / 'w.whl'
    wheel.write_bytes(buf.getvalue())
    with pytest.raises(UpdateError):
        ytdlp_update.unpack_wheel(wheel, tmp_path / 'out', NEW)


# -- checking -------------------------------------------------------------


def test_switched_on_a_tested_newer_version_is_kept(tmp_path, running):
    fake = _Fake()
    fake.results = [{'ok': True, 'version': NEW}]
    up = _updater(tmp_path, fake)
    up.configure(enabled=True)

    status = up.check_now()

    assert status['active'] == NEW
    assert status['restart_pending'] is True
    assert status['error'] is None
    saved = tmp_path / 'yt-dlp' / NEW / 'yt_dlp' / '__init__.py'
    assert saved.is_file()
    assert [title for _e, title, _t in fake.sent] == [f'Updated to {NEW}']
    # No work folder is left behind.
    assert [p.name for p in (tmp_path / 'yt-dlp').iterdir()] == [NEW]


def test_up_to_date_does_nothing(tmp_path, running):
    running['value'] = NEW
    fake = _Fake()
    up = _updater(tmp_path, fake)
    up.configure(enabled=True)

    status = up.check_now()

    assert status['active'] is None
    assert status['latest'] == NEW
    assert fake.tested == []
    assert fake.sent == []


def test_checksum_mismatch_installs_nothing(tmp_path, running):
    fake = _Fake()
    fake.release['urls'][1]['digests']['sha256'] = 'b' * 64
    up = _updater(tmp_path, fake)
    up.configure(enabled=True)

    status = up.check_now()

    assert status['active'] is None
    assert 'checksum' in status['error']
    assert fake.tested == []


def test_a_version_failing_while_the_current_works_is_never_used(
    tmp_path, running
):
    fake = _Fake()
    fake.results = [
        {'ok': False, 'version': NEW, 'error': 'ExtractorError: boom'},
        {'ok': True, 'version': OLD},
    ]
    up = _updater(tmp_path, fake)
    up.configure(enabled=True)

    status = up.check_now()

    assert status['active'] is None
    assert up.load()['rejected'] == {NEW: 'ExtractorError: boom'}
    assert fake.sent[0][1] == f'{NEW} failed the test'
    # The baseline test ran on the image's yt-dlp (no folder).
    assert not fake.tested[1]
    # Not tried again.
    up.check_now()
    assert len(fake.tested) == 2


def test_both_failing_changes_nothing_and_tries_again(tmp_path, running):
    fake = _Fake()
    fake.results = [
        {'ok': False, 'error': 'no network'},
        {'ok': False, 'error': 'no network'},
    ]
    up = _updater(tmp_path, fake)
    up.configure(enabled=True)

    status = up.check_now()

    assert status['active'] is None
    assert up.load()['rejected'] == {}
    assert 'Could not test' in status['error']
    assert fake.sent == []


def test_switched_off_it_only_says_an_update_is_out_once(tmp_path, running):
    fake = _Fake()
    up = _updater(tmp_path, fake)

    up.check_now()
    up.check_now()

    assert fake.tested == []
    assert len(fake.sent) == 1
    event, title, text = fake.sent[0]
    assert (event, title) == ('ytdlp', f'Update available: {NEW}')
    assert 'Update yt-dlp by itself' in text


def test_switched_off_pypi_is_only_asked_when_downloads_fail(tmp_path):
    up = _updater(tmp_path, _Fake())

    assert up.check_due(now=10**6) is False
    up.ask_soon()
    assert up.check_due(now=10**6) is True


def test_switched_on_the_check_is_daily_or_sooner_when_failing(tmp_path):
    up = _updater(tmp_path, _Fake())
    up.configure(enabled=True)
    up._last_check = 1000.0

    assert up.check_due(now=1000.0 + 3 * 3600) is False
    up.ask_soon()
    assert up.check_due(now=1000.0 + 3 * 3600) is True


# -- going back and starting ----------------------------------------------


def _install(tmp_path, version):
    folder = ytdlp_boot.version_dir(tmp_path, version) / 'yt_dlp'
    folder.mkdir(parents=True)
    (folder / '__init__.py').write_text('')


def test_going_back_to_the_previous_version_keeps_the_newer_away(
    tmp_path, running
):
    _install(tmp_path, OLD)
    _install(tmp_path, NEW)
    up = _updater(tmp_path, _Fake())
    up.configure(enabled=True)
    up._update(active=NEW, previous=OLD)

    status = up.use('previous')

    assert status['active'] == OLD
    assert NEW in up.load()['rejected']


def test_going_back_to_the_image_switches_updates_off(tmp_path, running):
    up = _updater(tmp_path, _Fake())
    up.configure(enabled=True)
    up._update(active=NEW)

    status = up.use('image')

    assert status['active'] is None
    assert status['enabled'] is False


def test_no_previous_version_is_an_error(tmp_path):
    up = _updater(tmp_path, _Fake())
    with pytest.raises(UpdateError):
        up.use('previous')


def test_a_copy_that_would_not_load_is_dropped_for_the_previous(
    tmp_path, running
):
    _install(tmp_path, OLD)
    fake = _Fake()
    boot = {'source': 'image', 'wanted': NEW, 'error': 'SyntaxError: x'}
    up = _updater(tmp_path, fake, boot=boot)
    up.configure(enabled=True)
    up._update(active=NEW, previous=OLD)

    up.after_boot()

    state = up.load()
    assert state['active'] == OLD
    assert state['rejected'] == {NEW: 'SyntaxError: x'}
    assert fake.sent[0][1] == f'{NEW} would not load'


def test_a_new_version_in_use_is_announced_once(tmp_path, running):
    running['value'] = NEW
    fake = _Fake()
    up = _updater(tmp_path, fake, boot={'source': 'saved', 'wanted': NEW})
    up.configure(enabled=True)
    up._update(active=NEW)

    up.after_boot()
    up.after_boot()

    assert [t for _e, t, _x in fake.sent] == [f'Now using {NEW}']


def test_restart_waits_until_nothing_runs(tmp_path, running):
    fake = _Fake()
    up = _updater(tmp_path, fake)
    up.configure(enabled=True)
    up._update(active=NEW)

    fake.idle = False
    assert up.maybe_restart() is False
    fake.idle = True
    assert up.maybe_restart() is True
    assert fake.restarts == 1
    # Once is enough.
    assert up.maybe_restart() is False


def test_no_restart_without_auto_restart_or_when_in_use(tmp_path, running):
    fake = _Fake()
    up = _updater(tmp_path, fake)
    up.configure(enabled=True, auto_restart=False)
    up._update(active=NEW)
    assert up.maybe_restart() is False

    up.configure(auto_restart=True)
    running['value'] = NEW
    assert up.maybe_restart() is False
    assert fake.restarts == 0


def test_status_says_an_update_is_out(tmp_path, running):
    up = _updater(tmp_path, _Fake())
    up._update(latest=NEW)

    assert up.status()['update_available'] is True
    running['value'] = NEW
    assert up.status()['update_available'] is False


# -- the real test script and boot, in their own process ------------------


def _python(
    code: str, env_extra: dict[str, str]
) -> subprocess.CompletedProcess:
    env = {**os.environ, 'DOWNTIFY_YTDLP_BOOT': '0', **env_extra}
    return subprocess.run(
        [sys.executable, '-c', textwrap.dedent(code)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        timeout=120,
        check=False,
    )


def _saved_copy(base: Path, version: str, init: str = '') -> None:
    pkg = ytdlp_boot.version_dir(base, version) / 'yt_dlp'
    pkg.mkdir(parents=True)
    (pkg / '__init__.py').write_text(init or 'from . import version\n')
    (pkg / 'version.py').write_text(f'__version__ = {version!r}\n')


_BOOT = """
    import json, sys
    from pathlib import Path
    from downtify import ytdlp_boot
    boot = ytdlp_boot.activate(Path(sys.argv[1] if len(sys.argv) > 1 else {base!r}))
    import yt_dlp.version
    print(json.dumps({{**boot, 'loaded': yt_dlp.version.__version__}}))
"""


def _boot(base: Path) -> dict:
    proc = _python(_BOOT.format(base=str(base)), {})
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_boot_loads_the_saved_copy_when_switched_on(tmp_path):
    _saved_copy(tmp_path, NEW)
    (tmp_path / 'ytdlp.json').write_text(
        json.dumps({'enabled': True, 'active': NEW})
    )

    boot = _boot(tmp_path)

    assert boot['source'] == 'saved'
    assert boot['loaded'] == NEW


def test_boot_ignores_the_saved_copy_when_switched_off(tmp_path):
    _saved_copy(tmp_path, NEW)
    (tmp_path / 'ytdlp.json').write_text(
        json.dumps({'enabled': False, 'active': NEW})
    )

    boot = _boot(tmp_path)

    assert boot['source'] == 'image'
    assert boot['loaded'] != NEW


def test_boot_falls_back_when_the_saved_copy_is_broken(tmp_path):
    _saved_copy(tmp_path, NEW, init='raise RuntimeError("broken copy")\n')
    (tmp_path / 'ytdlp.json').write_text(
        json.dumps({'enabled': True, 'active': NEW})
    )

    boot = _boot(tmp_path)

    assert boot['source'] == 'image'
    assert 'broken copy' in boot['error']
    assert boot['loaded'] != NEW


def test_boot_falls_back_when_the_copy_is_another_version(tmp_path):
    _saved_copy(tmp_path, NEW)
    (
        ytdlp_boot.version_dir(tmp_path, NEW) / 'yt_dlp' / 'version.py'
    ).write_text("__version__ = '2000.1.1'\n")
    (tmp_path / 'ytdlp.json').write_text(
        json.dumps({'enabled': True, 'active': NEW})
    )

    boot = _boot(tmp_path)

    assert boot['source'] == 'image'
    assert '2000.1.1' in boot['error']


def test_the_test_script_reports_a_broken_copy(tmp_path):
    _saved_copy(tmp_path, NEW, init='raise RuntimeError("nope")\n')
    up = YtdlpUpdater(tmp_path, boot={'source': 'image'})

    result = up.test(ytdlp_boot.version_dir(tmp_path, NEW))

    assert result['ok'] is False
    assert 'nope' in result['error']
