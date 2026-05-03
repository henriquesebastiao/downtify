"""Tests for version.sh — checks the script exists, validates its flags
and verifies it updates all three version files correctly."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / 'version.sh'


def test_script_exists():
    assert SCRIPT.exists(), 'version.sh is missing from repo root'


def test_script_is_executable():
    assert SCRIPT.stat().st_mode & 0o111, 'version.sh is not executable'


def test_current_flag_returns_valid_semver():
    result = subprocess.run(
        [str(SCRIPT), '--current'],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    version = result.stdout.strip()
    parts = version.split('.')
    assert len(parts) == 3, f'Not semver: {version!r}'
    assert all(p.isdigit() for p in parts), f'Non-numeric parts in {version!r}'


def test_invalid_semver_rejected():
    result = subprocess.run(
        [str(SCRIPT), 'not-semver'],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0


def test_missing_argument_shows_usage():
    result = subprocess.run(
        [str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0


def _setup_fake_repo(base: Path) -> None:
    """Create minimal stubs of every file that version.sh updates."""
    (base / 'downtify').mkdir()
    (base / 'downtify' / '__init__.py').write_text(
        "__version__ = '1.0.0'\n", encoding='utf-8'
    )
    (base / 'pyproject.toml').write_text(
        '[project]\nversion = "1.0.0"\n', encoding='utf-8'
    )
    (base / 'frontend').mkdir()
    (base / 'frontend' / 'package.json').write_text(
        '{\n  "version": "1.0.0"\n}\n', encoding='utf-8'
    )
    (base / 'Makefile').write_text(
        'DOWNTIFY_VERSION := 1.0.0\n', encoding='utf-8'
    )
    (base / 'Dockerfile').write_text(
        'LABEL version="1.0.0"\n'
        '      org.opencontainers.image.version="1.0.0" \\\n',
        encoding='utf-8',
    )
    components = base / 'frontend' / 'src' / 'components'
    components.mkdir(parents=True)
    (components / 'Hero.vue').write_text(
        "const version = ref(localStorage.getItem('version') || '1.0.0')\n",
        encoding='utf-8',
    )


def test_bump_updates_all_three_files(tmp_path):
    _setup_fake_repo(tmp_path)
    script_copy = tmp_path / 'version.sh'
    shutil.copy(SCRIPT, script_copy)

    result = subprocess.run(
        ['bash', str(script_copy), '2.3.4'],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    assert (
        "__version__ = '2.3.4'"
        in (tmp_path / 'downtify' / '__init__.py').read_text()
    )
    assert 'version = "2.3.4"' in (tmp_path / 'pyproject.toml').read_text()
    assert (
        '"version": "2.3.4"'
        in (tmp_path / 'frontend' / 'package.json').read_text()
    )
    assert 'DOWNTIFY_VERSION := 2.3.4' in (tmp_path / 'Makefile').read_text()
    dockerfile = (tmp_path / 'Dockerfile').read_text()
    assert 'LABEL version="2.3.4"' in dockerfile
    assert 'org.opencontainers.image.version="2.3.4"' in dockerfile
    assert (
        "|| '2.3.4'"
        in (
            tmp_path / 'frontend' / 'src' / 'components' / 'Hero.vue'
        ).read_text()
    )


def test_bump_noop_when_already_at_target(tmp_path):
    _setup_fake_repo(tmp_path)
    script_copy = tmp_path / 'version.sh'
    shutil.copy(SCRIPT, script_copy)

    result = subprocess.run(
        ['bash', str(script_copy), '1.0.0'],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert result.returncode == 0
    assert 'nothing to do' in result.stdout.lower()


def test_current_flag_in_fake_repo(tmp_path):
    _setup_fake_repo(tmp_path)
    script_copy = tmp_path / 'version.sh'
    shutil.copy(SCRIPT, script_copy)

    result = subprocess.run(
        ['bash', str(script_copy), '--current'],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == '1.0.0'
