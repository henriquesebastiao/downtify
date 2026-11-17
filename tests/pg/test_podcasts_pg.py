"""PodcastStore on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

from downtify.podcasts import EpisodeInfo, PodcastStore
from tests.db.helpers import query

FEED = 'https://example.com/feed.xml'


def _ep(guid: str, published: str) -> EpisodeInfo:
    return EpisodeInfo(
        guid=guid,
        title=f'Title {guid}',
        description=f'About {guid}',
        published_at=published,
        duration_seconds=60.5,
        season_number=None,
        episode_number=None,
        enclosure_url=f'https://example.com/{guid}.mp3',
        enclosure_type='audio/mpeg',
    )


def _count(db, sql: str, *params) -> int:
    return int(query(db, sql, *params)[0][0])


def test_add_show_round_trip_and_lookups(backend_db) -> None:
    store = PodcastStore(backend_db)
    show = store.add_show(
        FEED,
        'Alpha Show',
        author='Ann',
        description='Desc',
        artwork_url='https://example.com/a.png',
        source_url='https://open.spotify.com/show/1',
        retention=3,
        user_id=5,
    )
    assert show['name'] == 'Alpha Show'
    assert show['author'] == 'Ann'
    assert show['retention'] == 3
    assert show['user_id'] == 5
    assert show['folder_name']

    assert store.get_show(show['id']) == show
    assert store.get_show(999_999) is None
    assert store.get_show_by_feed_url(FEED, 5) == show
    assert store.get_show_by_feed_url(FEED, 6) is None
    assert store.get_show_by_feed_url(FEED)['id'] == show['id']
    assert store.get_show_by_feed_url('https://nope.example') is None


def test_adding_the_same_feed_twice_for_one_user_returns_the_original(
    backend_db,
) -> None:
    store = PodcastStore(backend_db)
    first = store.add_show(FEED, 'One', user_id=1)
    again = store.add_show(FEED, 'Renamed', user_id=1)
    assert again == first
    assert [s['name'] for s in store.list_shows(1)] == ['One']

    # The same feed for another user is a separate subscription, and the
    # connection stays usable after the duplicate was ignored.
    other = store.add_show(FEED, 'Two', user_id=2)
    assert other['id'] != first['id']
    assert other['user_id'] == 2


def test_same_name_shows_get_distinct_folders(backend_db) -> None:
    store = PodcastStore(backend_db)
    a = store.add_show('https://a.example/feed', 'Radiolab')
    b = store.add_show('https://b.example/feed', 'Radiolab')
    c = store.add_show('https://c.example/feed', 'Radiolab')
    assert b['folder_name'] == f'{a["folder_name"]} (2)'
    assert c['folder_name'] == f'{a["folder_name"]} (3)'


def test_list_shows_sorts_case_insensitively_and_filters_by_user(
    backend_db,
) -> None:
    store = PodcastStore(backend_db)
    store.add_show('https://1.example/f', 'beta', user_id=1)
    store.add_show('https://2.example/f', 'Alpha', user_id=1)
    store.add_show('https://3.example/f', 'gamma', user_id=2)

    assert [s['name'] for s in store.list_shows()] == [
        'Alpha',
        'beta',
        'gamma',
    ]
    assert [s['name'] for s in store.list_shows(1)] == ['Alpha', 'beta']
    assert store.list_shows(3) == []


def test_update_show_changes_only_the_allowed_fields(backend_db) -> None:
    store = PodcastStore(backend_db)
    show = store.add_show(FEED, 'Old', user_id=1)

    updated = store.update_show(
        show['id'],
        name='New',
        retention=2,
        feed_url='https://hijack.example',
        bogus=1,
    )
    assert updated['name'] == 'New'
    assert updated['retention'] == 2
    assert updated['feed_url'] == FEED

    assert store.update_show(show['id']) == updated
    assert store.update_show(999_999, name='x') is None


def test_reassign_legacy_then_remove_user_cascades(backend_db) -> None:
    store = PodcastStore(backend_db)
    show = store.add_show(FEED, 'Legacy', user_id=0)
    ep = store.upsert_episodes(show['id'], [_ep('g1', '2026-01-01')])[0]
    store.set_playback(ep['id'], position_seconds=12.0)  # user 0

    assert store.reassign_legacy(0) == 0
    assert store.reassign_legacy(9) == 2  # one show, one playback row
    assert store.get_show(show['id'])['user_id'] == 9
    listed = store.list_episodes(show['id'], user_id=9)
    assert listed[0]['position_seconds'] == 12.0

    store.remove_user(9)
    assert store.get_show(show['id']) is None
    assert store.list_shows(9) == []
    assert _count(backend_db, 'SELECT COUNT(*) FROM podcast_episodes') == 0
    assert _count(backend_db, 'SELECT COUNT(*) FROM podcast_playback') == 0


def test_upsert_episodes_inserts_only_new_guids(backend_db) -> None:
    store = PodcastStore(backend_db)
    show = store.add_show(FEED, 'Show')
    batch = [
        _ep('g1', '2026-01-01T00:00:00+00:00'),
        _ep('g2', '2026-02-01T00:00:00+00:00'),
        _ep('g1', '2026-01-01T00:00:00+00:00'),  # repeated in the batch
    ]
    inserted = store.upsert_episodes(show['id'], batch)
    assert [e['guid'] for e in inserted] == ['g1', 'g2']
    first = inserted[0]
    assert first['show_id'] == show['id']
    assert first['title'] == 'Title g1'
    assert first['duration_seconds'] == 60.5
    assert first['season_number'] is None
    assert first['dismissed'] is False
    assert first['played'] is False
    assert first['position_seconds'] == 0
    assert first['filename'] is None

    assert store.upsert_episodes(show['id'], batch) == []
    assert len(store.list_episodes(show['id'])) == 2


def test_list_episodes_newest_first_with_per_user_playback(
    backend_db,
) -> None:
    store = PodcastStore(backend_db)
    show = store.add_show(FEED, 'Show')
    eps = store.upsert_episodes(
        show['id'],
        [
            _ep('a', '2026-01-01T00:00:00+00:00'),
            _ep('b', '2026-03-01T00:00:00+00:00'),
            _ep('c', '2026-02-01T00:00:00+00:00'),
        ],
    )
    a, b, c = (e['id'] for e in sorted(eps, key=lambda e: e['guid']))
    store.set_playback(a, position_seconds=30, played=True, user_id=1)
    store.prune_download(c, dismissed=True)

    everything = store.list_episodes(show['id'], user_id=1)
    assert [e['guid'] for e in everything] == ['b', 'c', 'a']
    played = everything[-1]
    assert played['position_seconds'] == 30
    assert played['played'] is True

    other_user = store.list_episodes(show['id'])
    assert other_user[-1]['played'] is False
    assert other_user[-1]['position_seconds'] == 0

    visible = store.list_episodes(show['id'], include_dismissed=False)
    assert [e['guid'] for e in visible] == ['b', 'a']


def test_get_episode_with_and_without_playback(backend_db) -> None:
    store = PodcastStore(backend_db)
    show = store.add_show(FEED, 'Show')
    ep = store.upsert_episodes(show['id'], [_ep('g1', '2026-01-01')])[0]
    store.set_playback(ep['id'], played=True, user_id=4)

    row = store.get_episode(ep['id'], user_id=4)
    assert row['played'] is True
    assert row['guid'] == 'g1'
    assert store.get_episode(ep['id'])['played'] is False
    assert store.get_episode(999_999) is None


def test_downloads_are_recorded_pruned_and_never_resurrected(
    backend_db,
) -> None:
    store = PodcastStore(backend_db)
    show = store.add_show(FEED, 'Show')
    eps = store.upsert_episodes(
        show['id'],
        [_ep('a', '2026-01-01'), _ep('b', '2026-02-01')],
    )
    a, b = eps[0]['id'], eps[1]['id']

    store.mark_downloaded(a, 'podcasts/Show/a.mp3')
    store.mark_downloaded(b, 'podcasts/Show/b.mp3')
    row = store.get_episode(a)
    assert row['filename'] == 'podcasts/Show/a.mp3'
    assert row['downloaded_at']
    assert [e['id'] for e in store.downloaded_episodes(show['id'])] == [
        b,
        a,
    ]

    # A retention prune makes the episode eligible again ...
    store.prune_download(a, dismissed=False)
    row = store.get_episode(a)
    assert row['filename'] is None
    assert row['downloaded_at'] is None
    assert row['dismissed'] is False

    # ... while a deliberate delete is never fetched again by a sync.
    store.prune_download(b, dismissed=True)
    assert store.get_episode(b)['dismissed'] is True
    assert store.upsert_episodes(show['id'], [_ep('b', '2026-02-01')]) == []
    assert store.get_episode(b)['dismissed'] is True
    assert [e['id'] for e in store.downloaded_episodes(show['id'])] == []

    # Downloading it explicitly clears the dismissal again.
    store.mark_downloaded(b, 'podcasts/Show/b.mp3')
    assert store.get_episode(b)['dismissed'] is False


def test_set_playback_clamps_and_keeps_users_and_fields_apart(
    backend_db,
) -> None:
    store = PodcastStore(backend_db)
    show = store.add_show(FEED, 'Show')
    ep = store.upsert_episodes(show['id'], [_ep('g1', '2026-01-01')])[0]
    eid = ep['id']

    store.set_playback(eid, position_seconds=-5)
    assert store.get_episode(eid)['position_seconds'] == 0.0

    store.set_playback(eid, position_seconds=42.5, user_id=1)
    assert store.get_episode(eid, user_id=1)['position_seconds'] == 42.5
    assert store.get_episode(eid)['position_seconds'] == 0.0

    store.set_playback(eid, played=True)
    assert store.get_episode(eid)['played'] is True
    assert store.get_episode(eid, user_id=1)['played'] is False

    store.set_playback(eid, played=False)
    assert store.get_episode(eid)['played'] is False
    assert store.get_episode(eid)['position_seconds'] == 0.0
    assert (
        _count(backend_db, 'SELECT COUNT(*) FROM podcast_playback') == 2
    )  # one row per user, never duplicated


def test_delete_show_cascades_to_episodes_and_playback(backend_db) -> None:
    store = PodcastStore(backend_db)
    doomed = store.add_show(FEED, 'Doomed')
    keeper = store.add_show('https://keep.example/feed', 'Keeper')
    d_eps = store.upsert_episodes(
        doomed['id'],
        [_ep('d1', '2026-01-01'), _ep('d2', '2026-02-01')],
    )
    k_ep = store.upsert_episodes(keeper['id'], [_ep('k1', '2026-01-01')])[0]
    store.set_playback(d_eps[0]['id'], position_seconds=5, user_id=0)
    store.set_playback(d_eps[0]['id'], position_seconds=6, user_id=1)
    store.set_playback(k_ep['id'], position_seconds=7)

    deleted = store.delete_show(doomed['id'])
    assert deleted is not None
    assert deleted['id'] == doomed['id']
    assert store.get_show(doomed['id']) is None
    assert store.list_episodes(doomed['id']) == []
    assert store.delete_show(doomed['id']) is None

    assert (
        _count(
            backend_db,
            'SELECT COUNT(*) FROM podcast_episodes WHERE show_id = ?',
            doomed['id'],
        )
        == 0
    )
    assert (
        _count(
            backend_db,
            'SELECT COUNT(*) FROM podcast_playback WHERE episode_id = ?',
            d_eps[0]['id'],
        )
        == 0
    )

    # The other show is untouched.
    assert store.get_show(keeper['id']) is not None
    assert store.get_episode(k_ep['id'])['position_seconds'] == 7
