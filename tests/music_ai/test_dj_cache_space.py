from pathlib import Path

import pytest

from downtify.music_ai.dj_audio import AudioError, AudioIO


def test_cache_rotation_between_type_check_and_size_is_safe(
    tmp_path, monkeypatch
):
    music = tmp_path / 'music'
    music.mkdir()
    io = AudioIO(tmp_path / 'dj', [music], min_free=0)
    rotating = io.cache / 'segment-00000001.ts.tmp'
    rotating.write_bytes(b'encoded')
    original = Path.is_file
    calls = 0

    def is_file(path, *args, **kwargs):
        nonlocal calls
        result = original(path, *args, **kwargs)
        if path == rotating and result:
            calls += 1
            rotating.unlink()
        return result

    monkeypatch.setattr(Path, 'is_file', is_file)
    io.check_space(0)
    assert calls == 1


def test_cache_budget_is_still_enforced(tmp_path):
    music = tmp_path / 'music'
    music.mkdir()
    io = AudioIO(tmp_path / 'dj', [music], min_free=0)
    with pytest.raises(AudioError, match='dj_cache_full'):
        io.check_space(io.budget + 1)
