"""PlaylistShares on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

from downtify.playlist_shares import PRIVATE, PUBLIC, SHARED, PlaylistShares
from tests.db.helpers import query

OWNER = 1
ANA = 2
BO = 3
CY = 4


def test_visibility_share_list_and_editors(backend_db):
    shares = PlaylistShares(backend_db)

    assert shares.visibility('Mix') == PRIVATE
    assert shares.visibility_map() == {}

    shares.set_visibility('Mix', SHARED, [ANA, BO], editors=[ANA, CY])
    assert shares.visibility('mix') == SHARED
    assert shares.visibility_map() == {'mix': SHARED}
    assert shares.shared_users() == {'mix': [ANA, BO]}
    # Only users on the list can be editors.
    assert shares.editors() == {'mix': [ANA]}

    assert shares.view_for(ANA).to_me == {'mix': False}
    shares.mark_seen('Mix', ANA)
    assert shares.view_for(ANA).to_me == {'mix': True}
    assert shares.view_for(BO).to_me == {'mix': False}

    # Existing users keep whether they opened it; dropping BO ends
    # their share, and with editors=None ANA keeps editing.
    shares.set_visibility('Mix', SHARED, [ANA, CY])
    assert shares.shared_users() == {'mix': [ANA, CY]}
    assert shares.editors() == {'mix': [ANA]}
    assert shares.view_for(ANA).to_me == {'mix': True}
    assert shares.view_for(CY).to_me == {'mix': False}
    assert shares.view_for(BO).to_me == {}

    # Leaving SHARED clears the list and the editors.
    shares.set_visibility('Mix', SHARED, [])
    assert shares.shared_users() == {}
    assert shares.editors() == {}

    # Unknown visibility is refused; PRIVATE drops the row.
    try:
        shares.set_visibility('Mix', 'nope')
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError('expected ValueError')
    shares.set_visibility('Mix', PRIVATE)
    assert shares.visibility('Mix') == PRIVATE
    count = query(backend_db, 'SELECT COUNT(*) FROM playlist_shares')
    assert tuple(count[0]) == (0,)


def test_public_follows_and_follow_cleanup(backend_db):
    shares = PlaylistShares(backend_db)
    shares.set_visibility('Mix', PUBLIC)
    assert shares.view_for(ANA).public == frozenset({'mix'})

    shares.follow(ANA, 'Mix')
    shares.follow(ANA, 'Mix')  # a second follow is a no-op
    shares.follow(0, 'Mix')  # no user, nothing happens
    shares.follow(ANA, '')  # no name, nothing happens
    assert shares.view_for(ANA).followed == frozenset({'mix'})

    shares.follow(ANA, 'Mix', False)
    assert shares.view_for(ANA).followed == frozenset()

    # Following is dropped when the playlist stops being public.
    shares.follow(BO, 'Mix')
    shares.set_visibility('Mix', SHARED, [BO])
    assert shares.view_for(BO).followed == frozenset()
    shares.set_visibility('Mix', PUBLIC)
    assert shares.view_for(BO).followed == frozenset()


def test_rename_carries_sharing_and_collisions_are_replaced(backend_db):
    shares = PlaylistShares(backend_db)
    shares.set_visibility('Mix', SHARED, [ANA], editors=[ANA])
    shares.set_favorite(ANA, 'Mix', True)
    shares.rename('Mix', 'Renamed')
    assert shares.visibility_map() == {'renamed': SHARED}
    assert shares.shared_users() == {'renamed': [ANA]}
    assert shares.editors() == {'renamed': [ANA]}
    assert shares.favorites(ANA) == frozenset({'renamed'})

    # Renaming onto an existing name replaces that name's rows.
    shares.set_visibility('A', SHARED, [ANA])
    shares.set_visibility('B', SHARED, [ANA, BO])
    shares.rename('A', 'B')
    assert shares.shared_users() == {'b': [ANA, BO], 'renamed': [ANA]}
    assert shares.visibility('a') == PRIVATE
    assert shares.visibility('b') == SHARED

    # A no-op rename changes nothing.
    shares.rename('b', 'B')
    assert shares.shared_users() == {'b': [ANA, BO], 'renamed': [ANA]}


def test_forget_and_remove_user(backend_db):
    shares = PlaylistShares(backend_db)
    shares.set_visibility('Mix', SHARED, [ANA, BO], editors=[ANA])
    shares.set_favorite(ANA, 'Mix', True)
    shares.set_visibility('Other', PUBLIC)
    shares.follow(ANA, 'Other')

    shares.remove_user(ANA)
    assert shares.shared_users() == {'mix': [BO]}
    assert shares.editors() == {}
    assert shares.favorites(ANA) == frozenset()
    assert shares.view_for(ANA).followed == frozenset()

    shares.forget('Mix')
    assert shares.visibility('Mix') == PRIVATE
    assert shares.shared_users() == {}
    assert shares.visibility('Other') == PUBLIC


def test_favorites_are_personal_and_validated(backend_db):
    shares = PlaylistShares(backend_db)
    shares.set_favorite(ANA, 'Mix', True)
    shares.set_favorite(ANA, 'Mix', True)
    shares.set_favorite(BO, 'Mix', True)
    assert shares.favorites(ANA) == frozenset({'mix'})
    assert shares.favorites(BO) == frozenset({'mix'})

    shares.set_favorite(ANA, 'Mix', False)
    assert shares.favorites(ANA) == frozenset()
    assert shares.favorites(BO) == frozenset({'mix'})

    for user, name in ((0, 'Mix'), (ANA, '  ')):
        try:
            shares.set_favorite(user, name, True)
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError('expected ValueError')


def test_display_names_set_update_and_clear(backend_db):
    shares = PlaylistShares(backend_db)
    assert shares.display_names() == {}

    shares.set_display_name('spotify:1', 'First')
    shares.set_display_name('spotify:1', 'Second')
    shares.set_display_name('spotify:2', 'Other')
    assert shares.display_names() == {
        'spotify:1': 'Second',
        'spotify:2': 'Other',
    }

    shares.set_display_name('spotify:2', '')
    assert shares.display_names() == {'spotify:1': 'Second'}


def test_snapshot_and_restore_roll_back_a_failed_create(backend_db):
    shares = PlaylistShares(backend_db)
    shares.set_visibility('Mix', SHARED, [ANA, BO], editors=[ANA])
    shares.set_favorite(ANA, 'Mix', True)
    shares.follow(BO, 'Mix')  # a follow row, restored along with the rest

    before = shares.snapshot('Mix')
    shares.forget('Mix')
    assert shares.visibility('Mix') == PRIVATE
    assert shares.favorites(ANA) == frozenset()

    shares.restore('Mix', before)
    assert shares.visibility('Mix') == SHARED
    assert shares.shared_users() == {'mix': [ANA, BO]}
    assert shares.editors() == {'mix': [ANA]}
    assert shares.favorites(ANA) == frozenset({'mix'})

    # Restoring over rows that changed since puts the snapshot back.
    shares.mark_seen('Mix', ANA)
    assert shares.view_for(ANA).to_me == {'mix': True}
    shares.restore('Mix', before)
    assert shares.view_for(ANA).to_me == {'mix': False}

    # An empty snapshot changes nothing.
    shares.restore('Mix', {})
    assert shares.shared_users() == {'mix': [ANA, BO]}
