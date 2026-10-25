"""A known recording ID is not proof of a complete, readable album."""

from mutagen.id3 import ID3, TALB, TIT2, TPE1, TRCK

from downtify import monitor
from downtify.release_files import matches_release
from tests.test_artist_watch import (
    _add_artist,
    _album,
    _db,
    _FakeDownloader,
    _patch_provider,
    _run_check,
    _track,
)


def test_same_id_single_then_album_does_not_omit_the_album_track(
    monkeypatch, tmp_path
):
    db = _db(tmp_path)
    watch = _add_artist(db)
    dl = _FakeDownloader(tmp_path)
    _patch_provider(
        monkeypatch,
        [_album('single', 'Single')],
        {'single': [_track('same', 'One', 'Single', 1)]},
    )
    _run_check(watch, db, dl)
    _patch_provider(
        monkeypatch,
        [_album('album', 'Album'), _album('single', 'Single')],
        {
            'single': [_track('same', 'One', 'Single', 1)],
            'album': [
                _track('same', 'One', 'Album', 1),
                _track('two', 'Two', 'Album', 2),
            ],
        },
    )
    dl.calls.clear()
    assert _run_check(watch, db, dl) == 2
    assert dl.calls == ['same', 'two']
    assert set(db.releases.tracks(watch.id, 'album')) == {
        (1, 'same'),
        (2, 'two'),
    }
    assert (tmp_path / 'Single/same.mp3').is_file()


def test_removed_file_is_not_silently_skipped(monkeypatch, tmp_path):
    db = _db(tmp_path)
    watch = _add_artist(db)
    dl = _FakeDownloader(tmp_path)
    _patch_provider(
        monkeypatch,
        [_album('album', 'Album')],
        {'album': [_track('one', 'One', 'Album', 1)]},
    )
    _run_check(watch, db, dl)
    (tmp_path / 'Album/one.mp3').unlink()
    dl.calls.clear()
    assert _run_check(watch, db, dl) == 1
    assert dl.calls == ['one']


def test_empty_or_truncated_tracklist_never_marks_album_complete(
    monkeypatch, tmp_path
):
    db = _db(tmp_path)
    watch = _add_artist(db)
    dl = _FakeDownloader(tmp_path)
    _patch_provider(monkeypatch, [_album('album', 'Album')], {'album': []})
    _run_check(watch, db, dl)
    assert not db.get_seen_album_ids(watch.id)
    song = {**_track('one', 'One', 'Album', 1), 'album_track_total': 2}
    _patch_provider(monkeypatch, [_album('album', 'Album')], {'album': [song]})
    _run_check(watch, db, dl)
    assert not db.get_seen_album_ids(watch.id)


def test_downloader_returning_another_release_is_not_a_success(
    monkeypatch, tmp_path
):
    db = _db(tmp_path)
    watch = _add_artist(db)
    dl = _FakeDownloader(tmp_path)
    old = dl.download(_track('one', 'One', 'Single', 1))
    monkeypatch.setattr(dl, 'download', lambda *a: old)
    _patch_provider(
        monkeypatch,
        [_album('album', 'Album')],
        {'album': [_track('one', 'One', 'Album', 1)]},
    )
    assert _run_check(watch, db, dl) == 0
    assert not db.get_seen_album_ids(watch.id)
    assert not db.releases.tracks(watch.id, 'album')


def test_rechecks_only_one_historical_release_and_skips_new_only_baseline(
    monkeypatch, tmp_path
):
    db = _db(tmp_path)
    watch = _add_artist(db)
    for n in range(10):
        db.mark_album_seen(watch.id, str(n), str(n))
    db.mark_albums_skipped(watch.id, [_album('baseline', 'Baseline')])
    with db._connect() as conn:
        conn.execute('UPDATE seen_albums SET last_attempt=NULL')
    requested = []
    monkeypatch.setattr(
        monitor.providers,
        'artist_albums_from_channel_id',
        lambda _: (
            [_album(str(n), str(n)) for n in range(10)]
            + [_album('baseline', 'Baseline')]
        ),
    )
    monkeypatch.setattr(
        monitor.providers,
        'album_tracks_from_browse_id',
        lambda album: requested.append(album) or [],
    )
    _run_check(watch, db, _FakeDownloader(tmp_path))
    _run_check(watch, db, _FakeDownloader(tmp_path))
    assert requested == ['0', '1']


def test_release_tracking_survives_reopen_and_cascades_with_watch(tmp_path):
    db = _db(tmp_path)
    watch = _add_artist(db)
    db.releases.record(watch.id, 'album', 1, 'one', 'Album/one.mp3')
    reopened = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    assert (
        reopened.releases.tracks(watch.id, 'album')[(1, 'one')]
        == 'Album/one.mp3'
    )
    reopened.delete_playlist(watch.id)
    assert not reopened.releases.tracks(watch.id, 'album')


def test_release_validation_is_read_only_and_requires_album_tags(tmp_path):
    dl = _FakeDownloader(tmp_path)
    single = _track('one', 'One', 'Single', 1)
    filename = dl.download(single)
    path = tmp_path / filename
    before = path.read_bytes()
    assert matches_release(path, single)
    assert not matches_release(path, {**single, 'album_name': 'Album'})
    assert path.read_bytes() == before


def test_tag_only_file_is_not_validated_as_audio(tmp_path):
    path = tmp_path / 'broken.mp3'
    tags = ID3()
    tags.add(TIT2(encoding=3, text=['One']))
    tags.add(TALB(encoding=3, text=['Album']))
    tags.add(TPE1(encoding=3, text=['Test Artist']))
    tags.add(TRCK(encoding=3, text=['1']))
    tags.save(path)
    assert not matches_release(path, _track('one', 'One', 'Album', 1))
