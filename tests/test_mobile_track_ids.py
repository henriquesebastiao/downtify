import asyncio
import json

import pytest
from fastapi import HTTPException

from downtify.library_sync import LibrarySync
from downtify.manual_playlists import MAX_TRACKS_PER_EDIT
from downtify.mobile_track_ids import resolve_mobile_track_ids
from downtify.sqlite_utils import connect_sqlite


class FakeSync:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def rows_for(self, ids):
        self.calls.append(list(ids))
        return {key: self.rows[key] for key in ids if key in self.rows}


def test_resolves_in_one_batch_and_preserves_order_duplicates():
    sync = FakeSync({'a': {'file': 'A'}, 'b': {'file': 'B'}})
    visible_calls = []

    def visible(paths, _request):
        visible_calls.append(paths)
        return paths

    result = asyncio.run(
        resolve_mobile_track_ids(
            sync,
            [' b ', 'a', 'b'],
            object(),
            refresh=lambda: None,
            filter_paths=visible,
        )
    )

    assert result == ['B', 'A', 'B']
    assert sync.calls == [['b', 'a']]
    assert visible_calls == [['B', 'A']]


def test_resolves_limit_of_duplicate_ids_only_once():
    sync = FakeSync({'a': {'file': 'A'}})
    seen = []
    result = asyncio.run(
        resolve_mobile_track_ids(
            sync,
            ['a'] * MAX_TRACKS_PER_EDIT,
            object(),
            refresh=lambda: None,
            filter_paths=lambda paths, _request: seen.append(paths) or paths,
        )
    )
    assert result == ['A'] * MAX_TRACKS_PER_EDIT
    assert sync.calls == [['a']]
    assert seen == [['A']]


def test_refreshes_once_for_unknown_id_then_returns_404():
    sync = FakeSync({'a': {'file': 'A'}})
    refreshed = []

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            resolve_mobile_track_ids(
                sync,
                ['missing'],
                object(),
                refresh=lambda: refreshed.append(True),
                filter_paths=lambda paths, _request: paths,
            )
        )

    assert exc.value.status_code == 404
    assert refreshed == [True]
    assert len(sync.calls) == 2


def test_hidden_path_is_indistinguishable_from_unknown_id():
    sync = FakeSync({'a': {'file': 'A'}})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            resolve_mobile_track_ids(
                sync,
                ['a'],
                object(),
                refresh=lambda: None,
                filter_paths=lambda _paths, _request: [],
            )
        )
    assert exc.value.status_code == 404


def test_validates_entire_input_and_limit_before_lookup():
    sync = FakeSync({})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            resolve_mobile_track_ids(
                sync,
                ['valid', None],
                object(),
                refresh=lambda: None,
                filter_paths=lambda paths, _request: paths,
            )
        )
    assert exc.value.status_code == 400
    assert sync.calls == []

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            resolve_mobile_track_ids(
                sync,
                ['a', 'b'],
                object(),
                refresh=lambda: None,
                filter_paths=lambda paths, _request: paths,
                max_items=1,
            )
        )
    assert exc.value.status_code == 400
    assert sync.calls == []


def test_rows_for_keeps_replacement_alias_precedence(tmp_path):
    db_path = tmp_path / 'library.db'
    sync = LibrarySync(db_path)
    sync.refresh([{'file': 'A.mp3', 'title': 'Current'}])
    with connect_sqlite(str(db_path)) as db:
        live_id = db.execute(
            'SELECT track_id FROM sync_tracks WHERE path=?', ('A.mp3',)
        ).fetchone()[0]
        db.execute("""CREATE TABLE library_audio_sync_aliases (
            track_id TEXT, old_file TEXT)""")
        db.execute("""CREATE TABLE library_audio_replacements (
            old_file TEXT, new_metadata TEXT, state TEXT)""")
        db.execute(
            'INSERT INTO library_audio_sync_aliases VALUES (?, ?)',
            (live_id, 'old.mp3'),
        )
        db.execute(
            'INSERT INTO library_audio_replacements VALUES (?, ?, ?)',
            (
                'old.mp3',
                json.dumps({'file': 'B.mp3', 'title': 'Replacement'}),
                'linked',
            ),
        )

    assert sync.rows_for([live_id])[live_id]['file'] == 'B.mp3'
    assert sync.rows_for([live_id])[live_id]['title'] == 'Replacement'


def test_rows_for_replacements_use_current_metadata(tmp_path):
    db_path = tmp_path / 'library.db'
    sync = LibrarySync(db_path)
    sync.refresh([
        {'file': 'A.mp3', 'title': 'Original'},
        {'file': 'B.mp3', 'title': 'Updated'},
    ])
    with connect_sqlite(str(db_path)) as db:
        live_id = db.execute(
            'SELECT track_id FROM sync_tracks WHERE path=?', ('A.mp3',)
        ).fetchone()[0]
        db.execute(
            'CREATE TABLE library_audio_sync_aliases (track_id TEXT, old_file TEXT)'
        )
        db.execute(
            'CREATE TABLE library_audio_replacements (old_file TEXT, new_metadata TEXT, state TEXT)'
        )
        db.execute(
            'INSERT INTO library_audio_sync_aliases VALUES (?, ?)',
            (live_id, 'old.mp3'),
        )
        db.execute(
            'INSERT INTO library_audio_replacements VALUES (?, ?, ?)',
            (
                'old.mp3',
                json.dumps({'file': 'B.mp3', 'title': 'Stale'}),
                'linked',
            ),
        )
    assert sync.rows_for([live_id])[live_id] == sync.row_for(live_id)
