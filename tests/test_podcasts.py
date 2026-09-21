"""Podcast subscriptions: feed parsing, retention, tagging and the API."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

from downtify import api, monitor
from downtify.downloader import Downloader
from downtify.library_catalog import (
    PODCASTS_DIRNAME,
    LibraryContext,
    library_context_from_state,
    list_library_paths,
)
from downtify.library_delete import _delete_audio_under_dir
from downtify.library_reconcile import build_disk_content_index
from downtify.monitor import (
    KIND_PODCAST,
    PlaylistMonitorDB,
)
from downtify.podcasts import (
    EpisodeInfo,
    PodcastFeedNotFoundError,
    PodcastStore,
    embed_podcast_tags,
    episode_filename,
    episode_plan,
    match_episode,
    parse_feed_bytes,
    strip_html,
)

# ── a realistic-but-small feed, entirely offline ────────────────────────
SAMPLE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
  <title>The Sample Hour</title>
  <itunes:author>Sample Studios</itunes:author>
  <itunes:image href="https://example.com/art.jpg"/>
  <itunes:subtitle>A made-up show for tests, on a curiosity bender.</itunes:subtitle>
  <item>
    <title>Episode Three: The Reckoning</title>
    <guid>guid-three</guid>
    <description>&lt;p&gt;What happens &lt;b&gt;next&lt;/b&gt;?&lt;/p&gt;</description>
    <pubDate>Fri, 18 Sep 2026 14:00:00 +0000</pubDate>
    <itunes:duration>1:02:03</itunes:duration>
    <itunes:season>2</itunes:season>
    <itunes:episode>3</itunes:episode>
    <enclosure url="https://example.com/ep3.mp3" type="audio/mpeg" length="1000"/>
  </item>
  <item>
    <title>Episode Two</title>
    <guid>guid-two</guid>
    <description>Plain text, no season number here.</description>
    <pubDate>Fri, 11 Sep 2026 14:00:00 +0000</pubDate>
    <itunes:duration>45:30</itunes:duration>
    <itunes:episode>2</itunes:episode>
    <enclosure url="https://example.com/ep2.mp3" type="audio/mpeg" length="900"/>
  </item>
  <item>
    <title>Episode One: The Beginning</title>
    <guid>guid-one</guid>
    <description>Duration given as plain seconds.</description>
    <pubDate>Fri, 04 Sep 2026 14:00:00 +0000</pubDate>
    <itunes:duration>754</itunes:duration>
    <enclosure url="https://example.com/ep1.mp3" type="audio/mpeg" length="800"/>
  </item>
  <item>
    <title>No Guid Here</title>
    <description>Sloppy feeds sometimes omit the guid entirely.</description>
    <pubDate>Fri, 28 Aug 2026 14:00:00 +0000</pubDate>
    <enclosure url="https://example.com/no-guid.mp3" type="audio/mpeg" length="700"/>
  </item>
  <item>
    <title>A Video Extra</title>
    <guid>guid-video</guid>
    <description>Not a podcast episode Downtify can play.</description>
    <pubDate>Fri, 21 Aug 2026 14:00:00 +0000</pubDate>
    <enclosure url="https://example.com/extra.mp4" type="video/mp4" length="5000"/>
  </item>
  <item>
    <title>No Audio At All</title>
    <guid>guid-no-enclosure</guid>
    <description>A text-only post in the feed, with no enclosure.</description>
    <pubDate>Fri, 14 Aug 2026 14:00:00 +0000</pubDate>
  </item>
</channel>
</rss>
"""


# ── strip_html ───────────────────────────────────────────────────────
def test_strip_html_drops_tags_and_keeps_paragraph_breaks():
    assert strip_html('<p>Hello <b>world</b></p><p>Second</p>') == (
        'Hello world\n\nSecond'
    )


def test_strip_html_unescapes_entities_without_any_tags():
    assert strip_html('Rock &amp; Roll') == 'Rock & Roll'


def test_strip_html_of_empty_text_is_empty():
    assert not strip_html('')


def test_strip_html_survives_malformed_markup():
    # An unclosed tag shouldn't raise; a plain fallback is fine.
    assert 'broken' in strip_html('<p>broken<b>markup')


# ── parse_feed_bytes ─────────────────────────────────────────────────
def test_parse_feed_reads_show_metadata():
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    assert feed.name == 'The Sample Hour'
    assert feed.author == 'Sample Studios'
    assert feed.artwork_url == 'https://example.com/art.jpg'
    assert (
        feed.description == 'A made-up show for tests, on a curiosity bender.'
    )
    assert feed.feed_url == 'https://example.com/feed.xml'


def test_parse_feed_drops_video_and_enclosure_less_entries():
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    titles = [e.title for e in feed.episodes]
    assert 'A Video Extra' not in titles
    assert 'No Audio At All' not in titles
    assert len(feed.episodes) == 4  # 6 items minus those two


def test_parse_feed_falls_back_to_enclosure_url_when_guid_is_missing():
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    no_guid = next(e for e in feed.episodes if e.title == 'No Guid Here')
    assert no_guid.guid == 'https://example.com/no-guid.mp3'


def test_parse_feed_reads_html_description_as_plain_text():
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    ep3 = next(e for e in feed.episodes if e.guid == 'guid-three')
    assert ep3.description == 'What happens next?'


@pytest.mark.parametrize(
    ('guid', 'expected_seconds'),
    [
        ('guid-three', 3723.0),  # 1:02:03
        ('guid-two', 2730.0),  # 45:30
        ('guid-one', 754.0),  # plain seconds
    ],
)
def test_parse_feed_reads_itunes_duration_in_every_format(
    guid, expected_seconds
):
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    ep = next(e for e in feed.episodes if e.guid == guid)
    assert ep.duration_seconds == expected_seconds


def test_parse_feed_reads_season_and_episode_numbers_when_present():
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    ep3 = next(e for e in feed.episodes if e.guid == 'guid-three')
    assert (ep3.season_number, ep3.episode_number) == (2, 3)
    # Episode One never set <itunes:episode> — must not be guessed.
    ep1 = next(e for e in feed.episodes if e.guid == 'guid-one')
    assert (ep1.season_number, ep1.episode_number) == (None, None)


def test_parse_feed_publish_dates_are_iso_utc_and_in_order():
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    dates = [e.published_at for e in feed.episodes]
    assert dates == sorted(dates, reverse=True)
    assert feed.episodes[0].published_at.startswith('2026-09-18')


def test_parse_feed_survives_garbage_bytes_without_raising():
    feed = parse_feed_bytes(b'not xml at all <<<', 'https://example.com/x')
    assert feed.episodes == []


# ── match_episode ────────────────────────────────────────────────────
def test_match_episode_finds_an_exact_title():
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    found = match_episode(feed.episodes, 'Episode Two')
    assert found is not None
    assert found.guid == 'guid-two'


def test_match_episode_tolerates_punctuation_and_case_differences():
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    found = match_episode(feed.episodes, 'episode three the reckoning!')
    assert found is not None
    assert found.guid == 'guid-three'


def test_match_episode_returns_none_for_no_match():
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    assert match_episode(feed.episodes, 'Completely Unrelated Title') is None


# ── PodcastStore ─────────────────────────────────────────────────────
def _store(tmp_path: Path) -> PodcastStore:
    return PodcastStore(tmp_path / 'lib.db')


def test_add_show_and_get_by_feed_url_round_trip(tmp_path):
    store = _store(tmp_path)
    show = store.add_show('https://example.com/feed.xml', 'The Sample Hour')
    assert store.get_show_by_feed_url('https://example.com/feed.xml') == show
    assert store.get_show(show['id']) == show
    assert show['folder_name'] == 'The Sample Hour'


def test_two_shows_with_the_same_name_get_distinct_folders(tmp_path):
    store = _store(tmp_path)
    a = store.add_show('https://a.example/feed.xml', 'Duplicate Name')
    b = store.add_show('https://b.example/feed.xml', 'Duplicate Name')
    assert a['folder_name'] != b['folder_name']
    assert b['folder_name'] == 'Duplicate Name (2)'


def test_upsert_episodes_is_idempotent(tmp_path):
    store = _store(tmp_path)
    show = store.add_show('https://example.com/feed.xml', 'The Sample Hour')
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')

    first = store.upsert_episodes(show['id'], feed.episodes)
    assert len(first) == 4

    second = store.upsert_episodes(show['id'], feed.episodes)
    assert second == []  # every guid already known
    assert len(store.list_episodes(show['id'])) == 4


def test_dismissed_episode_is_never_resurrected_by_a_later_fetch(tmp_path):
    store = _store(tmp_path)
    show = store.add_show('https://example.com/feed.xml', 'The Sample Hour')
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    inserted = store.upsert_episodes(show['id'], feed.episodes)
    ep = inserted[0]
    store.mark_downloaded(ep['id'], f'{PODCASTS_DIRNAME}/x/ep.mp3')
    store.prune_download(ep['id'], dismissed=True)

    # A later sync sees the exact same feed again.
    store.upsert_episodes(show['id'], feed.episodes)
    row = store.get_episode(ep['id'])
    assert row['dismissed'] is True
    assert row['filename'] is None


def test_retention_pruned_episode_is_eligible_again_if_raised(tmp_path):
    store = _store(tmp_path)
    show = store.add_show(
        'https://example.com/feed.xml', 'The Sample Hour', retention=1
    )
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    store.upsert_episodes(show['id'], feed.episodes)

    to_download, to_prune = episode_plan(store, show, feed.episodes)
    assert [e['guid'] for e in to_download] == ['guid-three']
    for e in to_download:
        store.mark_downloaded(e['id'], f'{PODCASTS_DIRNAME}/x/{e["guid"]}.mp3')

    # A newer episode appears; retention=1 should prune the old one.
    newest = EpisodeInfo(
        guid='guid-four',
        title='Episode Four',
        description='',
        published_at='2026-09-25T00:00:00+00:00',
        duration_seconds=100,
        season_number=None,
        episode_number=4,
        enclosure_url='https://example.com/ep4.mp3',
        enclosure_type='audio/mpeg',
    )
    fresh = store.upsert_episodes(show['id'], [newest])
    to_download2, to_prune2 = episode_plan(store, show, fresh)
    assert [e['guid'] for e in to_download2] == ['guid-four']
    assert [e['guid'] for e in to_prune2] == ['guid-three']

    # Raising retention makes the pruned episode downloadable again — a
    # deliberate delete (dismissed) never would.
    for e in to_prune2:
        store.prune_download(e['id'], dismissed=False)
    raised = store.update_show(show['id'], retention=3)
    to_download3, _ = episode_plan(store, raised, [])
    assert 'guid-three' in [e['guid'] for e in to_download3]


def test_retention_zero_first_sync_downloads_only_the_newest(tmp_path):
    store = _store(tmp_path)
    show = store.add_show('https://example.com/feed.xml', 'The Sample Hour')
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    inserted = store.upsert_episodes(show['id'], feed.episodes)

    to_download, to_prune = episode_plan(store, show, inserted)
    assert [e['guid'] for e in to_download] == ['guid-three']
    assert to_prune == []


def test_retention_zero_steady_state_downloads_whatever_is_new(tmp_path):
    store = _store(tmp_path)
    show = store.add_show('https://example.com/feed.xml', 'The Sample Hour')
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    older = [e for e in feed.episodes if e.guid != 'guid-three']
    inserted = store.upsert_episodes(show['id'], older)
    to_download, _ = episode_plan(store, show, inserted)
    store.mark_downloaded(to_download[0]['id'], 'x.mp3')

    fresh = store.upsert_episodes(show['id'], feed.episodes)
    to_download2, to_prune2 = episode_plan(store, show, fresh)
    assert [e['guid'] for e in to_download2] == ['guid-three']
    assert to_prune2 == []


def test_set_playback_merges_position_and_played_independently(tmp_path):
    store = _store(tmp_path)
    show = store.add_show('https://example.com/feed.xml', 'The Sample Hour')
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    ep = store.upsert_episodes(show['id'], feed.episodes)[0]

    store.set_playback(ep['id'], position_seconds=42.5)
    assert store.get_episode(ep['id'])['position_seconds'] == 42.5
    assert store.get_episode(ep['id'])['played'] is False

    store.set_playback(ep['id'], played=True)
    row = store.get_episode(ep['id'])
    assert row['played'] is True
    assert row['position_seconds'] == 42.5  # untouched by the played-only call


def test_downloaded_episodes_excludes_dismissed_and_not_yet_downloaded(
    tmp_path,
):
    store = _store(tmp_path)
    show = store.add_show('https://example.com/feed.xml', 'The Sample Hour')
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    eps = store.upsert_episodes(show['id'], feed.episodes)
    store.mark_downloaded(eps[0]['id'], 'a.mp3')
    store.mark_downloaded(eps[1]['id'], 'b.mp3')
    store.prune_download(eps[1]['id'], dismissed=True)

    downloaded = store.downloaded_episodes(show['id'])
    assert [e['id'] for e in downloaded] == [eps[0]['id']]


def test_delete_show_removes_its_episodes_too(tmp_path):
    store = _store(tmp_path)
    show = store.add_show('https://example.com/feed.xml', 'The Sample Hour')
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    store.upsert_episodes(show['id'], feed.episodes)

    deleted = store.delete_show(show['id'])
    assert deleted is not None
    assert store.get_show(show['id']) is None
    assert store.list_episodes(show['id']) == []


# ── filenames ────────────────────────────────────────────────────────
def test_episode_filename_uses_the_published_date_and_title():
    ep = EpisodeInfo(
        guid='g',
        title='A "Weird" Title: Part 1',
        description='',
        published_at='2026-09-18T14:00:00+00:00',
        duration_seconds=1,
        season_number=None,
        episode_number=None,
        enclosure_url='https://example.com/x',
        enclosure_type='audio/mpeg',
    )
    name = episode_filename(ep)
    assert name.startswith('2026-09-18 - ')
    assert name.endswith('.mp3')
    assert '"' not in name


def test_episode_filename_extension_follows_enclosure_type():
    ep = EpisodeInfo(
        guid='g',
        title='X',
        description='',
        published_at='',
        duration_seconds=1,
        season_number=None,
        episode_number=None,
        enclosure_url='https://example.com/x',
        enclosure_type='audio/mp4',
    )
    assert episode_filename(ep).endswith('.m4a')


# ── tagging: real files, no network ──────────────────────────────────
# Same convention as test_downloader_extended.py: these need a real
# ffmpeg to synthesize a decodable source file, which a bare CI runner
# (unlike the Docker image, which bundles it for the app itself) may
# not have — skip rather than fail where it's missing.
_HAS_FFMPEG = bool(shutil.which('ffmpeg'))


def _synth_audio(path: Path, codec: str) -> None:
    subprocess.run(
        [
            'ffmpeg',
            '-loglevel',
            'error',
            '-y',
            '-f',
            'lavfi',
            '-i',
            'anullsrc=r=22050:cl=mono',
            '-t',
            '1',
            '-c:a',
            codec,
            str(path),
        ],
        check=True,
    )


@pytest.mark.skipif(not _HAS_FFMPEG, reason='ffmpeg not installed')
@pytest.mark.parametrize(
    ('filename', 'codec'),
    [('ep.mp3', 'libmp3lame'), ('ep.m4a', 'aac')],
)
def test_embed_podcast_tags_writes_episode_and_show_and_cover(
    tmp_path, filename, codec
):
    path = tmp_path / filename
    _synth_audio(path, codec)
    cover = b'\xff\xd8\xff' + b'0' * 32

    embed_podcast_tags(
        path,
        title='Episode Three: The Reckoning',
        show_name='The Sample Hour',
        author='Sample Studios',
        published_at='2026-09-18T14:00:00+00:00',
        description='What happens next?',
        episode_number=3,
        season_number=2,
        cover_bytes=cover,
    )

    if filename.endswith('.mp3'):
        audio = MP3(str(path))
        assert str(audio.tags['TIT2']) == 'Episode Three: The Reckoning'
        assert str(audio.tags['TALB']) == 'The Sample Hour'
        assert str(audio.tags['TPE1']) == 'Sample Studios'
        assert str(audio.tags['TRCK']) == '3'
        assert str(audio.tags['TPOS']) == '2'
        assert str(audio.tags['TDRC']) == '2026'
        apic = [v for k, v in audio.tags.items() if k.startswith('APIC')]
        assert apic
        assert apic[0].data == cover
    else:
        audio = MP4(str(path))
        assert audio['\xa9nam'] == ['Episode Three: The Reckoning']
        assert audio['\xa9alb'] == ['The Sample Hour']
        assert audio['trkn'][0][0] == 3
        assert audio['disk'][0][0] == 2
        assert audio['covr'][0] == cover


@pytest.mark.skipif(not _HAS_FFMPEG, reason='ffmpeg not installed')
def test_embed_podcast_tags_on_an_unsupported_container_does_not_raise(
    tmp_path,
):
    path = tmp_path / 'episode.wav'
    _synth_audio(path, 'pcm_s16le')
    embed_podcast_tags(
        path,
        title='X',
        show_name='Y',
        author='Z',
        published_at='',
        description='',
        episode_number=None,
        season_number=None,
        cover_bytes=None,
    )
    assert path.exists()  # untagged, but not destroyed


# ── excluded from the music library ───────────────────────────────
def test_podcast_episodes_never_appear_in_the_library_scan(tmp_path):
    download_dir = tmp_path / 'downloads'
    show_dir = download_dir / PODCASTS_DIRNAME / 'A Show'
    show_dir.mkdir(parents=True)
    (show_dir / 'ep.mp3').write_bytes(b'audio')
    (download_dir / 'Regular Song.mp3').write_bytes(b'audio')

    ctx = library_context_from_state(download_dir, {})
    paths = list_library_paths(ctx)
    assert paths == ['Regular Song.mp3']


def test_podcast_episodes_are_skipped_when_reconciling_content_keys(tmp_path):
    download_dir = tmp_path / 'downloads'
    show_dir = download_dir / PODCASTS_DIRNAME / 'A Show'
    show_dir.mkdir(parents=True)
    (show_dir / 'ep.mp3').write_bytes(b'audio-bytes')
    (download_dir / 'Regular Song.mp3').write_bytes(b'more-audio-bytes')

    ctx = library_context_from_state(download_dir, {})
    index = build_disk_content_index(ctx)
    assert list(index.values()) == ['Regular Song.mp3']


# ── the Podcasts root can never be swept by a playlist delete ──────
def test_deleting_a_playlist_named_podcasts_never_touches_episodes(tmp_path):
    download_dir = tmp_path / 'downloads'
    podcasts_dir = download_dir / PODCASTS_DIRNAME / 'A Show'
    podcasts_dir.mkdir(parents=True)
    episode = podcasts_dir / 'ep.mp3'
    episode.write_bytes(b'audio')

    ctx = LibraryContext(download_dir=download_dir)
    result = _delete_audio_under_dir(
        download_dir / PODCASTS_DIRNAME,
        ctx,
        state=type(
            'S',
            (),
            {
                'cover_cache': None,
                'metadata_cache': None,
                'playlist_catalog': None,
            },
        )(),
        skip_paths=set(),
    )
    assert result['deleted'] == []
    assert episode.exists()  # the guard fired before any file was touched


# ── the API endpoints ────────────────────────────────────────────────
class _Body:
    def __init__(self, payload: Any = None):
        self._payload = payload

    async def json(self) -> Any:
        return self._payload


@pytest.fixture
def podcast_state(monkeypatch, tmp_path):
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    monkeypatch.setattr(
        api.state,
        'downloader',
        Downloader(download_dir=downloads, audio_format='mp3'),
    )
    monkeypatch.setattr(
        api.state, 'podcasts', PodcastStore(tmp_path / 'lib.db')
    )
    monkeypatch.setattr(
        api.state, 'monitor_db', PlaylistMonitorDB(tmp_path / 'monitor.db')
    )
    monkeypatch.setattr(api.state, 'loop', None)
    monkeypatch.setattr(api.state.connections, 'broadcast', _noop_broadcast)
    return downloads


async def _noop_broadcast(_message: dict[str, Any]) -> None:
    return None


def test_resolve_reads_a_direct_feed_url(monkeypatch, podcast_state):
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    monkeypatch.setattr(api, 'fetch_feed', lambda url: feed)

    result = asyncio.run(
        api.resolve_podcast(_Body({'url': 'https://example.com/feed.xml'}))
    )
    assert result['show']['name'] == 'The Sample Hour'
    assert len(result['episodes']) == 4
    assert result['already_subscribed'] is False


def test_resolve_reports_a_spotify_exclusive_show_plainly(
    monkeypatch, podcast_state
):
    def _raise(_url):
        raise PodcastFeedNotFoundError('Some Exclusive Show')

    monkeypatch.setattr(api, 'resolve_spotify_podcast', _raise)
    monkeypatch.setattr(
        api.spotify, 'parse_spotify_url', lambda u: ('show', 'abc123')
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            api.resolve_podcast(
                _Body({'url': 'https://open.spotify.com/show/abc123'})
            )
        )
    assert exc.value.status_code == 404
    assert 'Some Exclusive Show' in exc.value.detail


def test_resolve_rejects_a_link_that_is_not_a_feed(monkeypatch, podcast_state):
    def _raise(_url):
        raise ValueError('boom')

    monkeypatch.setattr(api, 'fetch_feed', _raise)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            api.resolve_podcast(_Body({'url': 'https://example.com/nope'}))
        )
    assert exc.value.status_code == 400


def test_subscribe_then_list_then_get_episodes(monkeypatch, podcast_state):
    result = asyncio.run(
        api.subscribe_podcast(
            _Body({
                'feed_url': 'https://example.com/feed.xml',
                'name': 'The Sample Hour',
                'author': 'Sample Studios',
                'retention': 2,
                'interval_minutes': 60,
            })
        )
    )
    assert result['name'] == 'The Sample Hour'
    assert result['interval_minutes'] == 60

    shows = asyncio.run(api.list_podcast_shows())
    assert len(shows) == 1
    assert shows[0]['feed_url'] == 'https://example.com/feed.xml'

    payload = asyncio.run(api.list_podcast_episodes(shows[0]['id']))
    assert payload['show']['id'] == shows[0]['id']
    assert payload['episodes'] == []  # nothing downloaded yet in this test


def test_subscribing_twice_to_the_same_feed_is_rejected(
    monkeypatch, podcast_state
):
    body = {
        'feed_url': 'https://example.com/feed.xml',
        'name': 'The Sample Hour',
    }
    asyncio.run(api.subscribe_podcast(_Body(dict(body))))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.subscribe_podcast(_Body(dict(body))))
    assert exc.value.status_code == 409


def test_update_show_retention_and_watch_interval(monkeypatch, podcast_state):
    show = asyncio.run(
        api.subscribe_podcast(
            _Body({
                'feed_url': 'https://example.com/feed.xml',
                'name': 'The Sample Hour',
            })
        )
    )
    updated = asyncio.run(
        api.update_podcast_show(
            show['id'], _Body({'retention': 5, 'interval_minutes': 120})
        )
    )
    assert updated['retention'] == 5
    assert updated['interval_minutes'] == 120


def test_delete_show_removes_downloaded_files_by_default(
    monkeypatch, podcast_state
):
    show = asyncio.run(
        api.subscribe_podcast(
            _Body({
                'feed_url': 'https://example.com/feed.xml',
                'name': 'The Sample Hour',
            })
        )
    )
    show_dir = podcast_state / PODCASTS_DIRNAME / show['folder_name']
    show_dir.mkdir(parents=True)
    (show_dir / 'ep.mp3').write_bytes(b'audio')

    result = asyncio.run(api.delete_podcast_show(show['id']))
    assert result['files_deleted'] is True
    assert not show_dir.exists()
    assert api.state.podcasts.get_show(show['id']) is None
    assert (
        api.state.monitor_db.get_by_spotify_id('https://example.com/feed.xml')
        is None
    )


def test_delete_show_keeps_files_when_asked(monkeypatch, podcast_state):
    show = asyncio.run(
        api.subscribe_podcast(
            _Body({
                'feed_url': 'https://example.com/feed.xml',
                'name': 'The Sample Hour',
            })
        )
    )
    show_dir = podcast_state / PODCASTS_DIRNAME / show['folder_name']
    show_dir.mkdir(parents=True)
    (show_dir / 'ep.mp3').write_bytes(b'audio')

    result = asyncio.run(api.delete_podcast_show(show['id'], keep_files=True))
    assert result['files_deleted'] is False
    assert (show_dir / 'ep.mp3').exists()


def test_delete_episode_dismisses_it_so_it_never_comes_back(
    monkeypatch, podcast_state
):
    show = asyncio.run(
        api.subscribe_podcast(
            _Body({
                'feed_url': 'https://example.com/feed.xml',
                'name': 'The Sample Hour',
            })
        )
    )
    store = api.state.podcasts
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    inserted = store.upsert_episodes(show['id'], feed.episodes)
    ep = inserted[0]
    full = podcast_state / PODCASTS_DIRNAME / show['folder_name']
    full.mkdir(parents=True)
    file_path = full / 'ep.mp3'
    file_path.write_bytes(b'audio')
    store.mark_downloaded(
        ep['id'], f'{PODCASTS_DIRNAME}/{show["folder_name"]}/ep.mp3'
    )

    result = asyncio.run(api.delete_podcast_episode(ep['id']))
    assert result == {'ok': True}
    assert not file_path.exists()
    row = store.get_episode(ep['id'])
    assert row['dismissed'] is True
    assert row['filename'] is None


def test_set_playback_endpoint_saves_position(monkeypatch, podcast_state):
    show = asyncio.run(
        api.subscribe_podcast(
            _Body({
                'feed_url': 'https://example.com/feed.xml',
                'name': 'The Sample Hour',
            })
        )
    )
    store = api.state.podcasts
    feed = parse_feed_bytes(SAMPLE_FEED, 'https://example.com/feed.xml')
    ep = store.upsert_episodes(show['id'], feed.episodes)[0]

    result = asyncio.run(
        api.set_podcast_playback(ep['id'], _Body({'position_seconds': 12.5}))
    )
    assert result['position_seconds'] == 12.5

    result2 = asyncio.run(
        api.set_podcast_playback(ep['id'], _Body({'played': True}))
    )
    assert result2['played'] is True
    assert result2['position_seconds'] == 12.5


def test_search_endpoint_returns_itunes_results(monkeypatch, podcast_state):
    monkeypatch.setattr(
        api,
        'search_shows',
        lambda q, limit=10: [
            {'name': 'Found Show', 'feed_url': 'https://x/feed'}
        ],
    )
    result = asyncio.run(api.search_podcasts_endpoint(q='anything'))
    assert result['results'][0]['name'] == 'Found Show'


# ── monitor.py dispatch ──────────────────────────────────────────────
def test_monitor_dispatches_a_podcast_watch_to_sync_show(
    monkeypatch, tmp_path
):
    calls = []

    def _fake_sync_show(store, show, download_dir, progress=None):
        calls.append((show['feed_url'], download_dir))
        return 2

    monkeypatch.setattr(monitor, 'sync_show', _fake_sync_show)

    store = PodcastStore(tmp_path / 'lib.db')
    show = store.add_show('https://example.com/feed.xml', 'The Sample Hour')
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist(
        show['feed_url'], show['name'], show['feed_url'], 60, KIND_PODCAST
    )

    async def _broadcast(_msg):
        return None

    async def _run():
        return await monitor.check_watch(
            watch,
            db,
            downloader=Downloader(download_dir=tmp_path, audio_format='mp3'),
            broadcast=_broadcast,
            loop=asyncio.get_running_loop(),
            podcasts=store,
        )

    count = asyncio.run(_run())
    assert count == 2
    assert calls[0][0] == 'https://example.com/feed.xml'
    updated = db.get_playlist(watch.id)
    assert updated.last_checked is not None


def test_monitor_podcast_watch_without_a_matching_show_is_a_harmless_noop(
    monkeypatch, tmp_path
):
    store = PodcastStore(tmp_path / 'lib.db')  # no show added
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist(
        'https://example.com/orphan.xml',
        'Orphan',
        'https://example.com/orphan.xml',
        60,
        KIND_PODCAST,
    )

    async def _broadcast(_msg):
        return None

    async def _run():
        return await monitor.check_watch(
            watch,
            db,
            downloader=Downloader(download_dir=tmp_path, audio_format='mp3'),
            broadcast=_broadcast,
            loop=asyncio.get_running_loop(),
            podcasts=store,
        )

    count = asyncio.run(_run())
    assert count == 0
