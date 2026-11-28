"""Noticing YouTube downloads that keep failing (downtify/ytdlp_health.py)."""

from __future__ import annotations

from types import SimpleNamespace

from downtify import notifications, ytdlp_health
from downtify.ytdlp_health import BROKEN_AFTER, YoutubeHealth, classify

NSIG = (
    'ERROR: [youtube] abc: nsig extraction failed: Some formats may be missing'
)


def _health():
    sent = []
    broken = []
    health = YoutubeHealth(
        emit=lambda e, t, x: sent.append((e, t, x)),
        version=lambda: '2026.11.23',
        on_broken=lambda: broken.append(True),
        update_hint=lambda: 'Checking for a newer yt-dlp now. ',
    )
    return health, sent, broken


def test_classify():
    assert classify('ERROR: [youtube] x: Video unavailable') == 'song'
    assert classify('Private video. Sign in if you') == 'song'
    assert classify('Sign in to confirm your age') == 'song'
    assert classify('[Errno -3] Temporary failure in name resolution') == (
        'network'
    )
    assert classify("Sign in to confirm you're not a bot") == 'bot'
    assert classify(NSIG) == 'ytdlp'
    assert classify('Requested format is not available') == 'ytdlp'


def test_failures_in_a_row_over_several_songs_send_one_message():
    health, sent, broken = _health()
    for n in range(BROKEN_AFTER + 5):
        health.failure(f'v{n % 4}', NSIG)

    assert len(sent) == 1
    event, title, text = sent[0]
    assert event == 'ytdlp'
    assert title == 'YouTube downloads keep failing'
    assert 'yt-dlp 2026.11.23' in text
    assert 'Checking for a newer yt-dlp now.' in text
    assert 'nsig extraction failed' in text
    assert broken == [True]
    assert health.status()['failing'] is True


def test_one_song_failing_again_and_again_is_not_yt_dlp():
    health, sent, _ = _health()
    for _ in range(BROKEN_AFTER * 2):
        health.failure('same', NSIG)

    assert sent == []


def test_song_and_network_errors_do_not_count():
    health, sent, _ = _health()
    for n in range(BROKEN_AFTER * 2):
        health.failure(f'v{n}', 'Video unavailable')
        health.failure(f'v{n}', 'Connection refused')

    assert sent == []
    assert health.status()['streak'] == 0


def test_a_working_download_resets_and_reports_recovery():
    health, sent, _ = _health()
    for n in range(BROKEN_AFTER - 1):
        health.failure(f'v{n}', NSIG)
    health.success()
    for n in range(BROKEN_AFTER - 1):
        health.failure(f'w{n}', NSIG)
    assert sent == []

    health.failure('last', NSIG)
    health.success()

    assert [t for _e, t, _x in sent] == [
        'YouTube downloads keep failing',
        'YouTube downloads work again',
    ]


def test_bot_checks_point_at_the_cookies():
    health, sent, _ = _health()
    for n in range(BROKEN_AFTER):
        health.failure(f'v{n}', "Sign in to confirm you're not a bot")

    assert sent[0][0] == 'youtube_cookies'
    assert sent[0][1] == 'YouTube wants a sign-in'


def test_new_events_reach_channels_saved_before_them():
    old_channel = {
        'enabled': True,
        'events': ['download_failed'],
        'known_events': [
            'download_failed',
            'download_done',
            'new_releases',
            'watch_done',
            'spotify_companion',
            'slskd_outage',
        ],
    }
    cfg = notifications.effective({'channels': {'discord': old_channel}})

    events = cfg['channels']['discord']['events']
    assert 'ytdlp' in events
    assert 'youtube_cookies' in events
    assert 'slskd_outage' not in events


def test_report_helpers_never_raise(monkeypatch):
    def boom(*_a):
        raise RuntimeError

    monkeypatch.setattr(
        ytdlp_health, 'monitor', SimpleNamespace(success=boom, failure=boom)
    )
    ytdlp_health.report_success()
    ytdlp_health.report_failure('v', 'x')
