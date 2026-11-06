from downtify.music_ai import compute_budget
from downtify.music_ai.store import Store


def test_dj_waits_for_analysis_to_yield_without_overlapping_or_expanding_cpu(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(compute_budget, 'pressure_high', lambda: False)
    database = Store(tmp_path / 'derived.db')
    now = [100.0]

    def clock():
        return now[0]

    analysis = compute_budget.acquire(database, 'analysis', clock=clock)
    assert analysis is not None
    assert compute_budget.acquire(database, 'dj', clock=clock) is None
    assert not analysis.renew()
    analysis.release()
    dj = compute_budget.acquire(database, 'dj', clock=clock)
    assert dj is not None
    assert compute_budget.acquire(database, 'analysis', clock=clock) is None
    dj.release()
    now[0] += 11
    assert (
        compute_budget.acquire(database, 'analysis', clock=clock) is not None
    )


def test_expired_owner_cannot_renew_or_release_a_successor(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(compute_budget, 'pressure_high', lambda: False)
    database = Store(tmp_path / 'derived.db')
    now = [100.0]
    first = compute_budget.acquire(database, 'analysis', clock=lambda: now[0])
    now[0] += 46
    second = compute_budget.acquire(database, 'dj', clock=lambda: now[0])
    assert second is not None
    assert not first.renew()
    first.release()
    assert second.renew()


def test_pressure_defers_only_our_background_analysis(tmp_path, monkeypatch):
    monkeypatch.setattr(compute_budget, 'pressure_high', lambda: True)
    database = Store(tmp_path / 'derived.db')
    assert compute_budget.acquire(database, 'analysis') is None
    assert compute_budget.acquire(database, 'dj') is not None
