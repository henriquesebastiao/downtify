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
    # An oddity, not an answer: refused, and nothing is remembered.
    with pytest.raises(artist_photo_proxy.PhotoUnavailable):
        artist_photo_proxy.fetch_proxied_photo('Paramore')
    assert artist_photo_proxy._url_cache == {}


@pytest.mark.parametrize(
    'headers',
    [{'content-type': 'text/html'}, {}],
)
def test_non_image_response_is_refused(monkeypatch, headers):
    monkeypatch.setattr(deezer, 'exact_artist_picture', lambda n: CDN)
    monkeypatch.setattr(
        artist_photo_proxy.httpx,
        'get',
        lambda *a, **k: _resp(content=b'<html>', headers=headers),
    )
    # A missing content-type defaults to jpeg; only an explicit non-image
    # type is refused - as a failure, not as "no photo".
    if headers:
        with pytest.raises(artist_photo_proxy.PhotoUnavailable):
            artist_photo_proxy.fetch_proxied_photo('Paramore')
    else:
        assert artist_photo_proxy.fetch_proxied_photo('Paramore')


def test_oversized_image_is_refused(monkeypatch):
    monkeypatch.setattr(deezer, 'exact_artist_picture', lambda n: CDN)
    big = b'x' * (artist_photo_proxy._MAX_BYTES + 1)
    monkeypatch.setattr(
        artist_photo_proxy.httpx,
        'get',
        lambda *a, **k: _resp(
            content=big, headers={'content-type': 'image/jpeg'}
        ),
    )
    with pytest.raises(artist_photo_proxy.PhotoUnavailable):
        artist_photo_proxy.fetch_proxied_photo('Paramore')


def test_a_failed_download_is_a_failure_not_a_miss(monkeypatch):
    monkeypatch.setattr(deezer, 'exact_artist_picture', lambda n: CDN)

    def timeout(*a, **k):
        raise httpx.ReadTimeout('slow CDN')

    monkeypatch.setattr(artist_photo_proxy.httpx, 'get', timeout)
    with pytest.raises(artist_photo_proxy.PhotoUnavailable):
        artist_photo_proxy.fetch_proxied_photo('Paramore')


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


def test_a_failed_lookup_is_not_remembered_as_no_photo(monkeypatch):
    calls = []

    def flaky(name):
        calls.append(name)
        if len(calls) == 1:
            raise ValueError('Could not reach Deezer')
        return CDN

    monkeypatch.setattr(deezer, 'exact_artist_picture', flaky)
    monkeypatch.setattr(
        artist_photo_proxy.httpx,
        'get',
        lambda *a, **k: _resp(
            content=b'jpegbytes', headers={'content-type': 'image/jpeg'}
        ),
    )
    with pytest.raises(artist_photo_proxy.PhotoUnavailable):
        artist_photo_proxy.fetch_proxied_photo('Paramore')
    assert 'paramore' not in artist_photo_proxy._url_cache
    # The outage is over: the very next request gets the photo.
    assert artist_photo_proxy.fetch_proxied_photo('Paramore') == (
        b'jpegbytes',
        'image/jpeg',
    )
    assert calls == ['Paramore', 'Paramore']


def test_an_in_flight_marker_never_outlives_a_failed_lookup(monkeypatch):
    def down(name):
        raise ValueError('Could not reach Deezer')

    monkeypatch.setattr(deezer, 'exact_artist_picture', down)
    with pytest.raises(artist_photo_proxy.PhotoUnavailable):
        artist_photo_proxy.fetch_proxied_photo('Paramore')
    assert artist_photo_proxy._inflight == {}


def test_deezers_request_limit_is_not_remembered_as_no_photo(monkeypatch):
    # Over 50 requests per 5 seconds Deezer answers HTTP 200 with an
    # ``error`` object and no ``data`` - end to end through the real lookup.
    quota = _resp(
        payload={
            'error': {
                'type': 'Exception',
                'message': 'Quota limit exceeded',
                'code': 4,
            }
        }
    )
    answers = [
        quota,
        _search([{'name': 'Foo Fighters', 'picture_medium': CDN}]),
    ]
    monkeypatch.setattr(
        artist_photo_proxy.httpx,
        'get',
        lambda url, *a, **k: (
            answers.pop(0)
            if 'api.deezer.com' in str(url)
            else _resp(
                content=b'jpegbytes', headers={'content-type': 'image/jpeg'}
            )
        ),
    )
    with pytest.raises(artist_photo_proxy.PhotoUnavailable):
        artist_photo_proxy.fetch_proxied_photo('Foo Fighters')
    assert artist_photo_proxy._url_cache == {}
    # A moment later the limit is gone, and the next request just works.
    assert artist_photo_proxy.fetch_proxied_photo('Foo Fighters') == (
        b'jpegbytes',
        'image/jpeg',
    )


def test_only_deezers_own_no_photo_answer_is_remembered(monkeypatch):
    rows = [{'name': 'Someone Else', 'picture_medium': CDN}]
    monkeypatch.setattr(deezer.httpx, 'get', lambda *a, **k: _search(rows))
    assert artist_photo_proxy.fetch_proxied_photo('Nobody') is None
    assert artist_photo_proxy._cached_url('nobody') == (True, None)
