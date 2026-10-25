import pytest

from downtify.artist_suggestions import artist_candidates


@pytest.mark.parametrize(
    ('url', 'allowed'),
    [
        ('https://yt3.googleusercontent.com/artist-photo', True),
        ('https://yt3.ggpht.com/artist-photo', True),
        ('https://i.scdn.co/image/artist-photo', True),
        ('https://image-cdn-ak.spotifycdn.com/image/artist-photo', True),
        ('http://yt3.ggpht.com/artist-photo', False),
        ('https://untrusted.invalid/artist-photo', False),
        ('https://user:password@i.scdn.co/image/photo', False),
        ('javascript:alert(1)', False),
    ],
)
def test_profile_photos_use_the_matching_first_party_search_result(
    url, allowed
):
    result = artist_candidates(
        'Artist',
        [{'name': 'Artist', 'artist_id': 'UC' + 'a' * 22, 'cover_url': url}],
    )
    candidate = result['candidates'][0]
    assert candidate['image_url'] == (url if allowed else '')
    assert candidate['source'] == 'youtube_music'


def test_spotify_photo_stays_attached_to_its_artist_id():
    rows = [
        {
            'name': 'Same',
            'artist_id': n * 22,
            'image_url': 'https://i.scdn.co/image/' + n,
        }
        for n in ('a', 'b')
    ]
    result = artist_candidates('Same', rows, source='spotify')
    assert result['url'] is None
    for candidate in result['candidates']:
        assert candidate['image_url'].endswith(candidate['artist_id'][0])
        assert candidate['source'] == 'spotify'
