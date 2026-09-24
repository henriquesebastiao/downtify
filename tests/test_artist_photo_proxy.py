from __future__ import annotations

import httpx
import pytest

from downtify import artist_photo_proxy, deezer

CDN = 'https://cdn-images.dzcdn.net/images/artist/abc/250x250.jpg'


def _resp(*, payload=None, content=b'', headers=None):
    request = httpx.Request('GET', 'https://example.test/')
    if payload is not None:
        return httpx.Response(200, json=payload, request=request)
    return httpx.Response(
        200, content=content, headers=headers or {}, request=request
    )


@pytest.fixture(autouse=True)
def _clean_cache():
    artist_photo_proxy._url_cache.clear()
    yield
    artist_photo_proxy._url_cache.clear()


def _search(rows):
    return _resp(payload={'data': rows})


def test_exact_artist_picture_matches_name_case_insensitively(monkeypatch):
    rows = [
        {'name': 'Paramore Tribute', 'picture_medium': 'wrong'},
        {'name': 'PARAMORE', 'picture_medium': CDN},
    ]
    monkeypatch.setattr(deezer.httpx, 'get', lambda *a, **k: _search(rows))
    assert deezer.exact_artist_picture(' paramore ') == CDN


def test_exact_artist_picture_rejects_near_matches(monkeypatch):
    rows = [{'name': 'Paramore Tribute', 'picture_medium': CDN}]
    monkeypatch.setattr(deezer.httpx, 'get', lambda *a, **k: _search(rows))
    assert deezer.exact_artist_picture('Paramore') is None


def test_fetch_proxied_photo_returns_bytes_and_type(monkeypatch):
    monkeypatch.setattr(deezer, 'exact_artist_picture', lambda name: CDN)
    monkeypatch.setattr(
        artist_photo_proxy.httpx,
        'get',
        lambda *a, **k: _resp(
            content=b'jpegbytes', headers={'content-type': 'image/jpeg'}
        ),
    )
    assert artist_photo_proxy.fetch_proxied_photo('Paramore') == (
        b'jpegbytes',
        'image/jpeg',
    )


def test_url_lookup_is_cached_including_misses(monkeypatch):
    calls = []

    monkeypatch.setattr(deezer, 'exact_artist_picture', calls.append)
    assert artist_photo_proxy.fetch_proxied_photo('Nobody') is None
    assert artist_photo_proxy.fetch_proxied_photo('nobody') is None
    assert calls == ['Nobody']


def test_url_cache_entries_expire(monkeypatch):
    calls = []
    monkeypatch.setattr(deezer, 'exact_artist_picture', calls.append)
    artist_photo_proxy.fetch_proxied_photo('Nobody')
    key = 'nobody'
    url, stamp = artist_photo_proxy._url_cache[key]
    artist_photo_proxy._url_cache[key] = (
        url,
        stamp - artist_photo_proxy._URL_TTL - 1,
    )
    artist_photo_proxy.fetch_proxied_photo('Nobody')
    assert len(calls) == 2


def test_cache_is_capped(monkeypatch):
    monkeypatch.setattr(artist_photo_proxy, '_MAX_ENTRIES', 3)
    for i in range(5):
        artist_photo_proxy._remember_url(f'a{i}', None)
    assert list(artist_photo_proxy._url_cache) == ['a2', 'a3', 'a4']


def test_non_dzcdn_url_is_never_downloaded(monkeypatch):
    monkeypatch.setattr(
        deezer, 'exact_artist_picture', lambda n: 'https://evil.example/a.jpg'
    )

    def boom(*a, **k):
        raise AssertionError('must not download')

    monkeypatch.setattr(artist_photo_proxy.httpx, 'get', boom)
    assert artist_photo_proxy.fetch_proxied_photo('Paramore') is None


@pytest.mark.parametrize(
    'headers',
    [{'content-type': 'text/html'}, {}],
)
def test_non_image_response_is_dropped(monkeypatch, headers):
    monkeypatch.setattr(deezer, 'exact_artist_picture', lambda n: CDN)
    monkeypatch.setattr(
        artist_photo_proxy.httpx,
        'get',
        lambda *a, **k: _resp(content=b'<html>', headers=headers),
    )
    # A missing content-type defaults to jpeg; only an explicit non-image
    # type is refused.
    result = artist_photo_proxy.fetch_proxied_photo('Paramore')
    assert (result is None) == bool(headers)


def test_oversized_image_is_dropped(monkeypatch):
    monkeypatch.setattr(deezer, 'exact_artist_picture', lambda n: CDN)
    big = b'x' * (artist_photo_proxy._MAX_BYTES + 1)
    monkeypatch.setattr(
        artist_photo_proxy.httpx,
        'get',
        lambda *a, **k: _resp(
            content=big, headers={'content-type': 'image/jpeg'}
        ),
    )
    assert artist_photo_proxy.fetch_proxied_photo('Paramore') is None


def test_blank_name_makes_no_request(monkeypatch):
    def boom(*a, **k):
        raise AssertionError('no request expected')

    monkeypatch.setattr(deezer, 'exact_artist_picture', boom)
    assert artist_photo_proxy.fetch_proxied_photo('   ') is None


def test_nothing_is_written_to_disk(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(deezer, 'exact_artist_picture', lambda n: CDN)
    monkeypatch.setattr(
        artist_photo_proxy.httpx,
        'get',
        lambda *a, **k: _resp(
            content=b'jpegbytes', headers={'content-type': 'image/jpeg'}
        ),
    )
    artist_photo_proxy.fetch_proxied_photo('Paramore')
    assert list(tmp_path.iterdir()) == []


def test_module_has_no_persisting_helpers():
    source = artist_photo_proxy.__file__
    text = open(source, encoding='utf-8').read()
    code = text.split('"""', 2)[2]
    assert 'artist_profile' not in code
    assert 'write_bytes' not in code
    assert 'open(' not in code
