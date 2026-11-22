from __future__ import annotations

from downtify.duplicate_merge import KeptApart


def test_keep_counts_only_new_pairs(backend_db) -> None:
    kept = KeptApart(backend_db)
    assert kept.keep(['a.mp3', 'b.mp3']) == 1
    # Same pair again: nothing new is inserted.
    assert kept.keep(['b.mp3', 'a.mp3']) == 0
    # A third file adds two new pairs (a-c, b-c).
    assert kept.keep(['a.mp3', 'b.mp3', 'c.mp3']) == 2
    assert kept.keep(['only.mp3']) == 0
    assert kept.keep([]) == 0


def test_pairs_are_sorted_and_normalised(backend_db) -> None:
    kept = KeptApart(backend_db)
    kept.keep(['Drake\\One.mp3', ' Drake/Two.mp3 ', ''])
    assert kept.pairs() == {('Drake/One.mp3', 'Drake/Two.mp3')}


def test_settled_needs_every_pair(backend_db) -> None:
    kept = KeptApart(backend_db)
    kept.keep(['a.mp3', 'b.mp3'])
    assert kept.settled(['b.mp3', 'a.mp3'])
    assert not kept.settled(['a.mp3', 'b.mp3', 'c.mp3'])
    assert not kept.settled(['a.mp3'])
    assert not kept.settled([])
    assert kept.settled(['a.mp3', 'b.mp3'], kept.pairs())


def test_forget_files_drops_pairs_touching_them(backend_db) -> None:
    kept = KeptApart(backend_db)
    kept.keep(['a.mp3', 'b.mp3', 'c.mp3'])
    kept.forget_files(['b.mp3'])
    assert kept.pairs() == {('a.mp3', 'c.mp3')}
    kept.forget_files([])
    assert kept.pairs() == {('a.mp3', 'c.mp3')}


def test_forget_clears_everything(backend_db) -> None:
    kept = KeptApart(backend_db)
    kept.keep(['a.mp3', 'b.mp3', 'c.mp3'])
    assert kept.forget() == 3
    assert kept.pairs() == set()
    assert kept.forget() == 0


def test_a_second_store_on_the_same_database_sees_the_pairs(
    backend_db,
) -> None:
    KeptApart(backend_db).keep(['a.mp3', 'b.mp3'])
    assert KeptApart(backend_db).pairs() == {('a.mp3', 'b.mp3')}
