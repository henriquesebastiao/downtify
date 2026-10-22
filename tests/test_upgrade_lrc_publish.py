"""Publishing lyrics must work across bind mounts and retain failed copies."""

from __future__ import annotations

import errno
import os
import tempfile
from pathlib import Path

import pytest

from downtify import library_upgrade


def test_publish_never_renames_between_source_and_destination(
    tmp_path, monkeypatch
):
    source = tmp_path / 'audio' / 'track.downtify-upgrade.lrc'
    destination = tmp_path / 'data' / 'lyrics' / 'track.lrc'
    source.parent.mkdir()
    source.write_bytes('[00:01.00] une ligne é'.encode())
    source.chmod(0o640)
    expected = source.read_bytes()
    replace = os.replace

    def same_directory_only(src: str, dst: str) -> None:
        if Path(src).parent != Path(dst).parent:
            raise OSError(errno.EXDEV, 'Cross-device link')
        replace(src, dst)

    monkeypatch.setattr(library_upgrade.os, 'replace', same_directory_only)
    library_upgrade._publish_staged_lrc(source, destination)
    assert destination.read_bytes() == expected
    assert destination.stat().st_mode & 0o777 == 0o640
    assert not source.exists()
    assert list(destination.parent.iterdir()) == [destination]


@pytest.mark.parametrize('failure', ['copy', 'verify', 'replace'])
def test_failed_publication_preserves_source_and_existing_destination(
    tmp_path, monkeypatch, failure
):
    source = tmp_path / 'source.lrc'
    destination = tmp_path / 'dest' / 'track.lrc'
    source.write_bytes(b'new lyrics')
    destination.parent.mkdir()
    destination.write_bytes(b'existing lyrics')

    def fail(*_args, **_kwargs):
        raise OSError('synthetic write failure')

    if failure == 'copy':
        monkeypatch.setattr(library_upgrade.shutil, 'copyfileobj', fail)
    elif failure == 'replace':
        monkeypatch.setattr(library_upgrade.os, 'replace', fail)
    else:
        monkeypatch.setattr(
            library_upgrade.shutil,
            'copyfileobj',
            lambda _src, out: out.write(b'wrong bytes'),
        )
    with pytest.raises(
        OSError, match='synthetic write failure|failed verification'
    ):
        library_upgrade._publish_staged_lrc(source, destination)
    assert source.read_bytes() == b'new lyrics'
    assert destination.read_bytes() == b'existing lyrics'
    assert list(destination.parent.iterdir()) == [destination]


def test_publish_between_real_linux_filesystems(tmp_path):
    shared = Path('/dev/shm')
    if not shared.is_dir() or shared.stat().st_dev == tmp_path.stat().st_dev:
        pytest.skip('requires two distinct writable Linux filesystems')

    with tempfile.TemporaryDirectory(
        prefix='downtify-lrc-test-', dir=shared
    ) as target:
        source = tmp_path / 'source.lrc'
        source.write_bytes(b'[00:01.00] checked copy')
        destination = Path(target) / 'lyrics' / 'track.lrc'
        destination.parent.mkdir()
        with pytest.raises(OSError) as error:
            os.replace(source, destination)
        assert error.value.errno == errno.EXDEV
        library_upgrade._publish_staged_lrc(source, destination)
        assert destination.read_bytes() == b'[00:01.00] checked copy'
        assert not source.exists()
