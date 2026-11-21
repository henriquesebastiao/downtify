"""Library upgrade: ISRCs for older files (opt-in, confident or nothing)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from downtify import isrc, library_upgrade
from downtify.library_upgrade import (
    CATEGORY_ARTWORK,
    CATEGORY_ISRC,
    ISRC_LOOKUP_ONLY,
    UpgradeOptions,
    normalize_categories,
)
from tests.test_library_upgrade import (
    _context,
    _runner,
    _wait,
    _write_track,
)

CODE = 'USUG11904206'


def _library(tmp_path: Path):
    ctx = _context(tmp_path)
    old = _write_track(ctx.download_dir / 'old.mp3', cover_px=300)
    tagged = _write_track(ctx.download_dir / 'tagged.mp3', cover_px=300)
    isrc.write(tagged, 'GBUM71029604')
    return ctx, old, tagged


def _lookups(monkeypatch: Any, answer: str) -> list[dict[str, Any]]:
    asked: list[dict[str, Any]] = []

    def lookup(song):
        asked.append(song)
        return answer or None

    monkeypatch.setattr(library_upgrade.isrc_mod, 'lookup', lookup)
    return asked


def _scan(runner, categories) -> None:
    runner.start_scan(UpgradeOptions(categories=categories))
    _wait(runner)


def test_isrc_categories_are_a_run_of_their_own() -> None:
    assert normalize_categories(['isrc', 'artwork']) == (CATEGORY_ISRC,)
    assert normalize_categories(['isrc_lookup']) == (
        CATEGORY_ISRC,
        ISRC_LOOKUP_ONLY,
    )
    # The default never includes them.
    assert CATEGORY_ISRC not in normalize_categories(None)
    assert CATEGORY_ISRC not in normalize_categories(['nonsense'])


def test_a_normal_scan_never_looks_for_isrcs(tmp_path: Path) -> None:
    ctx, _old, _tagged = _library(tmp_path)
    runner = _runner(tmp_path, ctx)
    _scan(runner, library_upgrade.CATEGORIES)
    summary = runner.scan_summary()
    assert CATEGORY_ISRC not in summary['categories']
    assert summary['categories'][CATEGORY_ARTWORK] == 2


def test_an_isrc_scan_queues_only_files_without_one(tmp_path: Path) -> None:
    ctx, _old, _tagged = _library(tmp_path)
    runner = _runner(tmp_path, ctx)
    _scan(runner, (CATEGORY_ISRC,))
    summary = runner.scan_summary()
    # Nothing else is looked for, though both covers are small.
    assert summary['categories'] == {
        'artwork': 0,
        'lyrics': 0,
        'metadata': 0,
        'isrc': 1,
    }
    jobs = runner.db.jobs(runner.db.latest_run()['id'])
    assert [j['file'] for j in jobs] == ['old.mp3']


def test_looking_up_writes_nothing_and_checks_nothing(
    tmp_path: Path, monkeypatch: Any
) -> None:
    ctx, old, _tagged = _library(tmp_path)
    before = old.read_bytes()
    asked = _lookups(monkeypatch, CODE)
    runner = _runner(tmp_path, ctx)
    _scan(runner, (CATEGORY_ISRC, ISRC_LOOKUP_ONLY))
    runner.start((CATEGORY_ISRC, ISRC_LOOKUP_ONLY))
    _wait(runner)

    job = runner.db.jobs(runner.db.latest_run()['id'])[0]
    assert job['status'] == 'done'
    assert job['detail'] == f'Would add ISRC {CODE}'
    assert old.read_bytes() == before
    # The lookup got the song as its tags describe it.
    assert asked[0]['name'] == 'Track'
    assert asked[0]['artists'] == ['Artist']
    # Not marked as checked: the real run still picks it up.
    _scan(runner, (CATEGORY_ISRC,))
    assert runner.status()['counts']['total'] == 1


def test_a_confident_code_is_written_through_a_verified_copy(
    tmp_path: Path, monkeypatch: Any
) -> None:
    ctx, old, tagged = _library(tmp_path)
    _lookups(monkeypatch, CODE)
    rekeyed: list[tuple[str, str, str]] = []
    runner = _runner(tmp_path, ctx)
    runner.deps.rekey_owners = lambda a, b, s: rekeyed.append((a, b, s))
    _scan(runner, (CATEGORY_ISRC,))
    runner.start((CATEGORY_ISRC,))
    _wait(runner)

    job = runner.db.jobs(runner.db.latest_run()['id'])[0]
    assert (job['status'], job['detail']) == ('done', f'ISRC {CODE}')
    assert isrc.read(old) == CODE
    # Only the ISRC changed: the other tags (and the cover) are kept.
    assert library_upgrade.MutagenFile(str(old)).tags['TIT2'].text == ['Track']
    assert 'APIC:Cover' in library_upgrade.MutagenFile(str(old)).tags
    # The file grew, so whatever pointed at it follows the new key.
    assert len(rekeyed) == 1
    assert rekeyed[0][2] == 'old.mp3'
    # The tagged file was never touched.
    assert isrc.read(tagged) == 'GBUM71029604'
    # Done: the next ISRC scan finds nothing left.
    _scan(runner, (CATEGORY_ISRC,))
    assert runner.status()['counts']['total'] == 0


def test_no_sure_code_leaves_the_file_and_waits_before_asking_again(
    tmp_path: Path, monkeypatch: Any
) -> None:
    ctx, old, _tagged = _library(tmp_path)
    before = old.read_bytes()
    asked = _lookups(monkeypatch, '')
    runner = _runner(tmp_path, ctx)
    _scan(runner, (CATEGORY_ISRC,))
    runner.start((CATEGORY_ISRC,))
    _wait(runner)

    job = runner.db.jobs(runner.db.latest_run()['id'])[0]
    assert job['status'] == 'skipped'
    assert job['detail'] == 'No ISRC found for sure; left as it is'
    assert old.read_bytes() == before
    assert len(asked) == 1
    # Checked: the next scan doesn't ask Deezer again for it (until the
    # "don't check again for" days have passed).
    _scan(runner, (CATEGORY_ISRC,))
    assert runner.status()['counts']['total'] == 0


def test_a_file_that_got_an_isrc_meanwhile_is_left_alone(
    tmp_path: Path, monkeypatch: Any
) -> None:
    ctx, old, _tagged = _library(tmp_path)
    asked = _lookups(monkeypatch, CODE)
    runner = _runner(tmp_path, ctx)
    _scan(runner, (CATEGORY_ISRC,))
    isrc.write(old, 'GBAYE0601498')  # tagged between scan and run
    runner.start((CATEGORY_ISRC,))
    _wait(runner)

    job = runner.db.jobs(runner.db.latest_run()['id'])[0]
    assert (job['status'], job['detail']) == ('skipped', 'Already has an ISRC')
    assert asked == []
    assert isrc.read(old) == 'GBAYE0601498'


def test_a_write_that_does_not_verify_keeps_the_original(
    tmp_path: Path, monkeypatch: Any
) -> None:
    ctx, old, _tagged = _library(tmp_path)
    before = old.read_bytes()
    _lookups(monkeypatch, CODE)
    monkeypatch.setattr(library_upgrade, '_commit', lambda stage: False)
    runner = _runner(tmp_path, ctx)
    _scan(runner, (CATEGORY_ISRC,))
    runner.start((CATEGORY_ISRC,))
    _wait(runner)

    job = runner.db.jobs(runner.db.latest_run()['id'])[0]
    assert job['status'] == 'failed'
    assert 'kept the original' in job['detail']
    assert old.read_bytes() == before


def test_a_look_up_scan_started_by_hand_still_writes_nothing(
    tmp_path: Path, monkeypatch: Any
) -> None:
    ctx, old, _tagged = _library(tmp_path)
    before = old.read_bytes()
    _lookups(monkeypatch, CODE)
    runner = _runner(tmp_path, ctx)
    _scan(runner, (CATEGORY_ISRC, ISRC_LOOKUP_ONLY))
    runner.start((CATEGORY_ISRC,))  # the page's switch: just "isrc"
    _wait(runner)

    job = runner.db.jobs(runner.db.latest_run()['id'])[0]
    assert job['detail'] == f'Would add ISRC {CODE}'
    assert old.read_bytes() == before
