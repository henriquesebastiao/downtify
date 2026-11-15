from downtify import api, cover_sources, downloader

SIZES = {b'small': 300, b'medium': 640, b'large': 1200}
SONG = {'name': 'Song', 'artists': ['Band'], 'cover_url': 'https://x/cover'}


def _patch(monkeypatch, *, fetched, better=None):
    asked = []
    monkeypatch.setattr(downloader, '_download_cover', lambda url: fetched)
    monkeypatch.setattr(
        downloader, 'image_short_side', lambda data: SIZES.get(data, 0)
    )

    def best(song, *, current, preference='highest'):
        asked.append(current.width if current else 0)
        return better

    monkeypatch.setattr(cover_sources, 'best_cover', best)
    return asked


def test_minimum_off_keeps_the_source_cover(monkeypatch):
    asked = _patch(monkeypatch, fetched=b'small')

    assert downloader._download_cover_meeting(SONG, 0) == b'small'
    assert not asked


def test_cover_that_meets_the_minimum_is_kept(monkeypatch):
    asked = _patch(monkeypatch, fetched=b'medium')

    assert downloader._download_cover_meeting(SONG, 600) == b'medium'
    assert not asked


def test_small_cover_is_replaced_by_a_larger_one(monkeypatch):
    larger = cover_sources.CoverCandidate('itunes', b'large', 1200)
    asked = _patch(monkeypatch, fetched=b'medium', better=larger)

    assert downloader._download_cover_meeting(SONG, 1000) == b'large'
    assert asked == [640]


def test_without_a_larger_cover_the_best_found_is_still_used(monkeypatch):
    larger = cover_sources.CoverCandidate('youtube-music', b'medium', 640)
    _patch(monkeypatch, fetched=b'small', better=larger)

    assert downloader._download_cover_meeting(SONG, 1000) == b'medium'


def test_no_source_cover_still_looks_for_one(monkeypatch):
    found = cover_sources.CoverCandidate('spotify', b'large', 1200)
    asked = _patch(monkeypatch, fetched=None, better=found)

    assert downloader._download_cover_meeting(SONG, 600) == b'large'
    assert asked == [0]


def test_cover_min_resolution_is_clamped():
    assert api._clamp_cover_min_resolution('abc') == 0
    assert api._clamp_cover_min_resolution(-5) == 0
    assert api._clamp_cover_min_resolution(1000) == 1000
    assert api._clamp_cover_min_resolution(99999) == (
        api.MAX_COVER_MIN_RESOLUTION
    )
    assert api.DEFAULT_SETTINGS['cover_min_resolution'] == 0
