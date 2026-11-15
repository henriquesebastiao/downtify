from ai_test_support import opted_in_store

from downtify.music_ai.catalog import ensure_analysis_queue, unanalysed


def prepare(tmp_path):
    database = opted_in_store(tmp_path / 'derived.db')
    database.observe([
        {
            'id': track,
            'file': track + '.wav',
            'size': 1,
            'modified': 0,
            'added': 0,
            'duration': 1,
            'fingerprint': 'f-' + track,
        }
        for track in ('a', 'b', 'c')
    ])
    database.set_metadata('native_catalog_initialized', True)
    database.set_metadata('model', {'id': 'm', 'ready': True})
    with database.connect() as db:
        db.executemany(
            'INSERT OR IGNORE INTO catalog_live VALUES (?)',
            [(track,) for track in ('a', 'b', 'c')],
        )
    return database


def test_orphan_track_returns_to_the_queue_despite_an_unchanged_marker(
    tmp_path,
):
    database = prepare(tmp_path)
    ensure_analysis_queue(database, 'm')
    with database.connect() as db:
        db.execute('DELETE FROM catalog_pending')
    # The marker says the queue is already scheduled; the track has no analysis.
    assert unanalysed(database, 'm') == ['a', 'b', 'c']
    assert unanalysed(database, 'm', limit=2) == ['a', 'b']
    ensure_analysis_queue(database, 'm')
    with database.connect() as db:
        db.execute('DELETE FROM catalog_pending')
    with database.connect() as db:
        assert (
            db.execute('SELECT COUNT(*) FROM catalog_pending').fetchone()[0]
            == 0
        )


def test_analysed_pending_and_exhausted_tracks_are_skipped(tmp_path):
    database = prepare(tmp_path)
    with database.connect() as db:
        db.execute("INSERT INTO analyses VALUES ('a','f-a','m',x'00000000',0)")
        db.execute("INSERT INTO catalog_pending(id,priority) VALUES ('b',0)")
    database.enqueue(
        'job-c',
        'analysis',
        {'track': 'c', 'model': 'm'},
        priority=0,
    )
    with database.connect() as db:
        db.execute(
            "UPDATE jobs SET state='failed', attempts=3 WHERE id='job-c'"
        )
    assert unanalysed(database, 'm') == []
    # A stale fingerprint is not a valid analysis: the track comes back.
    with database.connect() as db:
        db.execute("INSERT INTO analyses VALUES ('b','old','m',x'00000000',0)")
        db.execute('DELETE FROM catalog_pending')
    assert unanalysed(database, 'm') == ['b']
    # An exhausted first row never hides the next one behind the limit.
    with database.connect() as db:
        db.execute("DELETE FROM analyses WHERE id='a'")
        db.execute("DELETE FROM analyses WHERE id='b'")
        db.execute(
            "UPDATE jobs SET state='failed', attempts=3 WHERE id='job-c'"
        )
        db.execute(
            "INSERT INTO jobs VALUES ('job-a','analysis',?, 'failed', 0, '', '', 3, 0, 0)",
            ('{"track": "a"}',),
        )
    assert unanalysed(database, 'm', limit=1) == ['b']
