from types import SimpleNamespace
from unittest.mock import Mock

from downtify.music_ai.dj_worker import DjWorker


def test_snapshot_slots_are_reused_beyond_the_original_40_tracks(tmp_path):
    worker = DjWorker.__new__(DjWorker)
    worker.job = {
        'sources': {
            str(i): {'path': 'fixture', 'source_version': [1]}
            for i in range(100)
        }
    }
    worker.database = SimpleNamespace(metadata=lambda *args: 0)
    worker.publish = Mock()
    worker.checkpoint = Mock()
    worker.analyze = Mock(return_value={'profile': {}})
    snapshots = {}
    slots = []

    def freeze(path, version, slot, checkpoint):
        slots.append(slot)
        target = tmp_path / f'source-{slot}.audio'
        assert not target.exists()
        target.write_bytes(b'synthetic')
        snapshots[str(target)] = [1]
        return {'path': str(target), 'source_version': [1]}

    io = SimpleNamespace(
        snapshots=snapshots, workspace=tmp_path, freeze=freeze
    )
    for i in range(100):
        keep = {str(j) for j in range(max(0, i - 3), i)}
        worker.release_decks(io, keep)
        worker.prepare_deck(str(i), io)
        assert len(snapshots) <= 4
    assert max(slots) <= 3
    worker.release_decks(io, set())
    assert not snapshots
    assert not list(tmp_path.glob('*.audio'))
