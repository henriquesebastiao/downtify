from datetime import datetime, timezone

import pytest

from downtify.music_ai.dj_navigation import navigation


@pytest.fixture
def stream(tmp_path):
    identity = 'a' * 32
    folder = tmp_path / identity
    folder.mkdir()
    origin = 1_700_000_000
    stamp = datetime.fromtimestamp(origin + 174, timezone.utc).isoformat()
    (folder / 'index.m3u8').write_text(
        f'#EXTM3U\n#EXT-X-PROGRAM-DATE-TIME:{stamp}\n'
        '#EXTINF:6,\nsegment-00000029.ts\n'
        '#EXTINF:6,\nsegment-00000030.ts\n'
        '#EXTINF:6,\nsegment-00000031.ts\n'
    )
    for sequence in range(29, 32):
        (folder / f'segment-{sequence:08d}.ts').write_bytes(b'audio')
    return tmp_path, {
        'id': identity,
        'mode': 'interactive',
        'state': 'ready',
        'media_origin': origin,
        'timeline': [
            {'id': 'one', 'start': 0, 'end': 180},
            {'id': 'two', 'start': 180, 'end': 360},
        ],
    }


def test_completed_interactive_render_navigates_its_published_audio(stream):
    cache, session = stream
    result = navigation(session, 'next', {'position': '175'}, cache)
    assert result == {
        'accepted': True,
        'seek_to_seconds': 180,
        'effective_after_seconds': 0.0,
    }
    assert (
        navigation(session, 'previous', {'position': '185'}, cache) == result
    )


def test_previous_outside_retained_window_does_not_leave_mix(stream):
    cache, session = stream
    result = navigation(session, 'previous', {'position': '181'}, cache)
    assert result['accepted'] is False
    assert 'fenêtre' in result['reason']


def test_last_marker_is_an_explicit_refusal_for_a_completed_render(stream):
    cache, session = stream
    assert (
        navigation(session, 'next', {'position': '185'}, cache)['accepted']
        is False
    )
    assert (
        navigation(
            {**session, 'state': 'playing'}, 'next', {'position': '185'}, cache
        )
        is None
    )


@pytest.mark.parametrize('position', ['nan', 'inf', '-1', '1000001', 'bad'])
def test_navigation_rejects_invalid_playheads(stream, position):
    cache, session = stream
    with pytest.raises(ValueError):
        navigation(session, 'next', {'position': position}, cache)


def test_removed_or_symlinked_segments_cannot_be_selected(stream):
    cache, session = stream
    segment = cache / session['id'] / 'segment-00000030.ts'
    segment.unlink()
    assert (
        navigation(session, 'next', {'position': '175'}, cache)['accepted']
        is False
    )
    segment.symlink_to(cache / session['id'] / 'segment-00000029.ts')
    assert (
        navigation(session, 'next', {'position': '175'}, cache)['accepted']
        is False
    )
