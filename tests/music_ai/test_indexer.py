from types import SimpleNamespace

from ai_test_support import opted_in_store

from downtify.music_ai import indexer


def test_priorities_do_not_starve_and_disk_checks_are_bounded(
    tmp_path, monkeypatch
):
    from downtify import (
        api,
        library_catalog,
        library_paths_cache,
        mobile_routes,
    )

    database = opted_in_store(tmp_path / 'derived.db')
    rows = []
    for i in range(500):
        file = f'{i:03}.wav'
        (tmp_path / file).write_bytes(b'synthetic')
        rows.append({
            'id': f'{i:03}',
            'file': file,
            'added': i,
            'fingerprint': str(i),
        })
    database.observe(rows)
    database.listen(1, 'play', '499', 90, 'complete')
    database.set_metadata('model', {'id': 'm', 'ready': True})
    monkeypatch.setattr(indexer, 'store', lambda: database)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'upgrade_runner', None)
    monkeypatch.setattr(
        api.state, 'likes', SimpleNamespace(paths=lambda: ['300.wav'])
    )
    contexts = []
    monkeypatch.setattr(api, 'library_context', lambda: contexts.append(1))
    monkeypatch.setattr(
        library_paths_cache, 'peek_cached_track_entries', lambda _: rows
    )

    def forbidden():
        raise AssertionError('AI must never trigger a NAS listing')

    monkeypatch.setattr(mobile_routes, '_refresh', forbidden)
    refreshed = []
    monkeypatch.setattr(
        mobile_routes,
        '_sync',
        lambda: SimpleNamespace(
            refresh=lambda items: refreshed.append(len(items)),
            changes=lambda *args: {'tracks': [dict(row) for row in rows]},
        ),
    )
    visits = []

    def resolve(file, _):
        visits.append(file)
        return tmp_path / file

    monkeypatch.setattr(library_catalog, 'resolve_library_file', resolve)
    indexer.index_pass()
    assert len(contexts) == 1
    assert refreshed == [500]
    assert len(visits) == 200
    assert len(set(visits)) == 200
    assert visits[:2] == ['499.wav', '300.wav']
    assert database.claim(kind='analysis')['payload']['track'] == '499'
    assert database.claim(kind='analysis')['payload']['track'] == '300'
    visits.clear()
    indexer.index_pass()
    assert len(visits) == 200
    assert {'100.wav', '199.wav'} <= set(visits)


def test_native_activity_prevents_catalog_scan(tmp_path, monkeypatch):
    from downtify import api, mobile_routes

    database = opted_in_store(tmp_path / 'derived.db')
    database.set_metadata('model', {'id': 'm'})
    monkeypatch.setattr(indexer, 'store', lambda: database)
    monkeypatch.setattr(
        api.state, 'download_jobs', {'synthetic': {'status': 'downloading'}}
    )
    monkeypatch.setattr(api.state, 'upgrade_runner', None)

    def forbidden():
        raise AssertionError(
            'No catalog work while native downloads are active'
        )

    monkeypatch.setattr(mobile_routes, '_refresh', forbidden)
    indexer.index_pass()
    assert database.metadata('native_busy') is True


def test_dj_alone_does_not_start_recommendation_analysis(
    tmp_path, monkeypatch
):
    from downtify import api

    database = opted_in_store(tmp_path / 'derived.db')
    database.set_metadata('model', {'id': 'm'})
    database.set_preferences(
        -1,
        {
            'personalization': False,
            'similarity': False,
            'daily': False,
            'weekly': False,
            'dj_prepared': True,
        },
    )
    monkeypatch.setattr(indexer, 'store', lambda: database)

    def forbidden():
        raise AssertionError('DJ has an independent work queue')

    monkeypatch.setattr(api, 'library_context', forbidden)
    indexer.index_pass()
    assert database.claim(kind='analysis') is None
