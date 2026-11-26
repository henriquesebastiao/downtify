"""The low-bitrate report (downtify/low_bitrate.py and its routes): which
files are listed, which Soulseek copies are offered and in what order,
and how a chosen copy is placed - beside the old file, with its tags,
never over it - before the old file is merged into it and trashed.

Audio files are made with ffmpeg (skipped without it); slskd is faked.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3

from downtify import low_bitrate as lb
from downtify import low_bitrate_routes as routes
from downtify.library_metadata import read_audio_metadata

FFMPEG = shutil.which('ffmpeg')
needs_ffmpeg = pytest.mark.skipif(FFMPEG is None, reason='needs ffmpeg')


def _entry(file: str, kbps: int, codec: str = 'mp3', **extra) -> dict:
    return {
        'file': file,
        'title': extra.pop('title', Path(file).stem),
        'artist': extra.pop('artist', 'Artist'),
        'album': 'Album',
        'duration': 200.0,
        'bitrate': kbps * 1000,
        'codec': codec,
        'size': 1000,
        **extra,
    }


# ── The report ──────────────────────────────────────────────────────────


def test_report_lists_lossy_files_under_the_threshold_lowest_first():
    entries = [
        _entry('a.mp3', 320),
        _entry('b.mp3', 128),
        _entry('c.m4a', 160, codec='aac'),
        _entry('d.flac', 200, codec='flac'),  # lossless never listed
        _entry('e.mp3', 0),  # unknown bitrate: nobody knows it is low
        _entry('f.mp3', 256),  # at the threshold is fine
        _entry('g.ogg', 96, codec='vorbis'),
    ]
    rows = lb.report_rows(entries, 256, {'b.mp3': 'youtube'})
    assert [row['file'] for row in rows] == ['g.ogg', 'b.mp3', 'c.m4a']
    assert rows[1]['bitrate'] == 128
    assert rows[1]['format'] == 'mp3'
    assert rows[1]['source'] == 'youtube'
    assert not rows[0]['source']


def test_threshold_is_clamped():
    assert lb.clamp_threshold('abc') == lb.DEFAULT_THRESHOLD_KBPS
    assert lb.clamp_threshold(10) == lb.MIN_THRESHOLD_KBPS
    assert lb.clamp_threshold(9999) == lb.MAX_THRESHOLD_KBPS
    assert lb.clamp_threshold(192) == 192


def test_song_for_entry_splits_the_artists():
    song = lb.song_for_entry(_entry('x.mp3', 128, artist='A;B'))
    assert song['artists'] == ['A', 'B']
    assert song['duration'] == 200


# ── Candidates ──────────────────────────────────────────────────────────


def _row(name: str, kbps: int = 0, score: int = 10, user='u', **extra):
    return {
        'username': user,
        'filename': f'Music\\Album\\{name}',
        'bitRate': kbps,
        'match_score': score,
        'size': 5_000_000,
        'length': 200,
        **extra,
    }


def test_mp3_320_comes_first_then_256_then_unlisted_bitrates():
    ranked = [
        _row('unknown.mp3', 0, score=30, user='a'),
        _row('ogg.ogg', 320, score=30, user='b'),
        _row('mp3-256.mp3', 256, score=30, user='c'),
        _row('mp3-320.mp3', 320, score=12, user='d'),
    ]
    picked = lb.pick_candidates(ranked, 128)
    assert [r['filename'].split('\\')[-1] for r in picked] == [
        'mp3-320.mp3',
        'mp3-256.mp3',
        'ogg.ogg',
        'unknown.mp3',
    ]


def test_worse_or_too_low_copies_are_never_offered():
    ranked = [
        _row('same.mp3', 128),
        _row('low.mp3', 192),
        _row('wav.wav', 1411),
        _row('ok.mp3', 256),
    ]
    picked = lb.pick_candidates(ranked, 128)
    assert [r['filename'].split('\\')[-1] for r in picked] == ['ok.mp3']
    # Better than a 256 file means more than 256.
    assert lb.pick_candidates([_row('ok.mp3', 256)], 256) == []


def test_lossless_only_when_asked_for():
    ranked = [_row('song.flac', 900), _row('song.mp3', 320, user='b')]
    assert len(lb.pick_candidates(ranked, 128)) == 1
    picked = lb.pick_candidates(ranked, 128, include_lossless=True)
    assert [r['filename'][-4:] for r in picked] == ['.mp3', 'flac']


def test_formats_to_avoid_are_never_offered():
    ranked = [_row('song.flac', 900), _row('song.ogg', 320, user='b')]
    picked = lb.pick_candidates(
        ranked, 128, include_lossless=True, avoid={'flac', 'ogg'}
    )
    assert picked == []


def test_vbr_v0_counts_as_best():
    v0 = _row('v0.mp3', 245, isVariableBitRate=True)
    picked = lb.pick_candidates([v0, _row('cbr.mp3', 256, user='x')], 128)
    assert picked[0] is v0
    assert lb.public_candidate(v0, 200)['best'] is True


def test_weak_matches_and_repeats_are_dropped():
    ranked = [
        _row('a.mp3', 320, score=2),
        _row('b.mp3', 320, user='p'),
        {**_row('b.mp3', 320, user='p'), 'filename': 'Other\\b.mp3'},
    ]
    picked = lb.pick_candidates(ranked, 128, min_score=5)
    assert len(picked) == 1


def test_public_candidate_shows_what_the_page_needs():
    row = _row('Song.mp3', 320, hasFreeUploadSlot=False, queueLength=4)
    shown = lb.public_candidate(row, 197.0)
    assert shown['name'] == 'Song.mp3'
    assert shown['folder'] == 'Album'
    assert shown['bitrate'] == 320
    assert shown['duration_diff'] == 3
    assert shown['free_slot'] is False
    assert shown['queue'] == 4
    assert shown['id'] == lb.candidate_id(row)
    assert 'filename' not in shown


class FakeClient:
    def __init__(self, files):
        self.files = files
        self.deleted = []
        self.enqueued = []

    @staticmethod
    def configured():
        return True

    @staticmethod
    def can_connect():
        return True

    @staticmethod
    def start_search(query):
        return 'search-1'

    @staticmethod
    def wait_search_complete(*args, **kwargs):
        return True

    def search_responses(self, search_id):
        return [
            {
                'username': 'peer',
                'fileCount': len(self.files),
                'hasFreeUploadSlot': True,
                'queueLength': 0,
                'files': self.files,
            }
        ]

    def delete_search(self, search_id):
        self.deleted.append(search_id)

    def enqueue_download(self, row):
        self.enqueued.append(row)
        return True

    @staticmethod
    def remote_download_directories():
        return []


def test_search_uses_slskd_matching_and_writes_nothing():
    song = {'name': 'Halo', 'artists': ['Beyonce'], 'duration': 261}
    client = FakeClient([
        {
            'filename': 'Beyonce\\I Am\\03 - Beyonce - Halo.mp3',
            'size': 9_000_000,
            'bitRate': 320,
            'length': 261,
        },
        {
            'filename': 'Beyonce\\I Am\\03 - Beyonce - Halo (Live).mp3',
            'size': 9_000_000,
            'bitRate': 320,
            'length': 261,
        },
        {
            'filename': 'Other\\Somebody - Something Else.mp3',
            'size': 9_000_000,
            'bitRate': 320,
            'length': 100,
        },
    ])
    settings = {'enabled': True, 'base_url': 'x', 'api_key': 'y'}
    found = lb.search_candidates(song, settings, 128, client=client)
    names = [row['filename'] for row in found]
    assert names == ['Beyonce\\I Am\\03 - Beyonce - Halo.mp3']
    assert client.deleted  # the search is cleaned up
    assert client.enqueued == []


def test_search_refuses_without_slskd():
    with pytest.raises(lb.UpgradeError) as caught:
        lb.search_candidates({'name': 'x'}, {'enabled': False}, 128)
    assert caught.value.code == 'slskd_off'


# ── Placing the new copy ────────────────────────────────────────────────


def test_the_new_copy_never_takes_the_old_path(tmp_path):
    old = tmp_path / 'Song.mp3'
    old.write_bytes(b'x')
    assert lb.target_path(old, '.mp3').name == 'Song (HQ).mp3'
    (tmp_path / 'Song (HQ).mp3').write_bytes(b'x')
    assert lb.target_path(old, '.mp3').name == 'Song (HQ) 2.mp3'
    assert lb.target_path(old, '.m4a').name == 'Song.m4a'
    (tmp_path / 'Song.m4a').write_bytes(b'x')
    assert lb.target_path(old, '.m4a').name == 'Song (HQ).m4a'


def _make(path: Path, kbps: int, seconds: float = 6.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    codec = {'.mp3': 'libmp3lame', '.m4a': 'aac', '.ogg': 'libvorbis'}[
        path.suffix
    ]
    args = [FFMPEG, '-nostdin', '-v', 'error', '-y', '-f', 'lavfi']
    args += ['-i', f'sine=frequency=440:duration={seconds}']
    args += ['-ac', '2', '-c:a', codec, '-b:a', f'{kbps}k', str(path)]
    subprocess.run(args, check=True, capture_output=True)
    return path


def _tag(path: Path) -> None:
    tags = EasyID3()
    tags.update({
        'title': 'Halo',
        'artist': 'Beyonce',
        'album': 'I Am... Sasha Fierce',
        'tracknumber': '3',
    })
    tags.save(str(path))
    id3 = ID3(str(path))
    id3.add(APIC(mime='image/png', type=3, data=b'\x89PNG cover'))
    id3.save(str(path))


@needs_ffmpeg
def test_a_better_copy_lands_beside_the_old_file_with_its_tags(tmp_path):
    old = _make(tmp_path / 'lib' / 'Halo.mp3', 128)
    _tag(old)
    (tmp_path / 'lib' / 'Halo.lrc').write_text('[00:01.00]la', 'utf-8')
    os.utime(old, (1_600_000_000, 1_600_000_000))
    before = old.read_bytes()
    download = _make(tmp_path / 'slskd' / 'Beyonce - Halo.mp3', 320)

    new, figures = lb.place_upgrade(old, download)

    assert new.name == 'Halo (HQ).mp3'
    assert old.read_bytes() == before  # the old file is untouched
    assert download.is_file()  # slskd's copy is cleaned up later
    meta = read_audio_metadata(new)
    assert meta['title'] == 'Halo'
    assert meta['album'] == 'I Am... Sasha Fierce'
    assert ID3(str(new)).getall('APIC')[0].data == b'\x89PNG cover'
    assert (tmp_path / 'lib' / 'Halo (HQ).lrc').read_text('utf-8') == (
        '[00:01.00]la'
    )
    assert int(new.stat().st_mtime) == 1_600_000_000
    assert figures['bitrate_before'] == 128
    assert figures['bitrate_after'] == 320
    assert not list((tmp_path / 'lib').glob('*downtify-upgrade*'))


@needs_ffmpeg
def test_a_copy_that_is_not_better_is_refused_and_leaves_nothing(tmp_path):
    old = _make(tmp_path / 'lib' / 'Halo.mp3', 192)
    worse = _make(tmp_path / 'slskd' / 'Halo.mp3', 128)
    with pytest.raises(lb.UpgradeError) as caught:
        lb.place_upgrade(old, worse)
    assert caught.value.code == 'not_better'
    assert sorted(p.name for p in (tmp_path / 'lib').iterdir()) == ['Halo.mp3']


@needs_ffmpeg
def test_a_copy_of_another_length_is_refused(tmp_path):
    old = _make(tmp_path / 'lib' / 'Halo.mp3', 128, seconds=6)
    longer = _make(tmp_path / 'slskd' / 'Halo.mp3', 320, seconds=20)
    with pytest.raises(lb.UpgradeError) as caught:
        lb.place_upgrade(old, longer)
    assert caught.value.code == 'length_mismatch'


@needs_ffmpeg
def test_tags_follow_a_copy_in_another_format(tmp_path):
    old = _make(tmp_path / 'lib' / 'Halo.mp3', 128)
    _tag(old)
    download = _make(tmp_path / 'slskd' / 'Halo.m4a', 256)
    new, _figures = lb.place_upgrade(old, download)
    assert new.name == 'Halo.m4a'
    meta = read_audio_metadata(new)
    assert meta['title'] == 'Halo'
    assert meta['artist'] == 'Beyonce'
    assert meta['track_number'] == 3


# ── The routes ──────────────────────────────────────────────────────────


@pytest.fixture
def state(monkeypatch):
    routes._searches.clear()
    routes._replacements.clear()
    fake = SimpleNamespace(
        downloader=SimpleNamespace(
            slskd_settings={'enabled': True, 'base_url': 'x', 'api_key': 'y'}
        ),
        file_providers=None,
        hand_replaced=None,
        library_trash=object(),
        metadata_cache=None,
    )
    monkeypatch.setattr(routes.api, 'state', fake)
    monkeypatch.setattr(
        routes,
        '_entries',
        lambda: {
            'b.mp3': _entry('b.mp3', 128),
            'good.mp3': _entry('good.mp3', 320),
        },
    )
    yield fake
    routes._searches.clear()
    routes._replacements.clear()


def test_the_report_only_reads(state):
    report = asyncio.run(routes.low_bitrate_report(threshold=256))
    assert [row['file'] for row in report['tracks']] == ['b.mp3']
    assert report['slskd'] is True
    assert report['trash'] is True
    assert report['tracks'][0]['search'] is None


def test_only_a_candidate_this_server_found_can_be_chosen(state):
    with pytest.raises(lb.UpgradeError) as caught:
        routes._chosen_row('b.mp3', 'made-up')
    assert caught.value.code == 'search_again'
    row = _row('b.mp3', 320)
    routes._searches['b.mp3'] = {
        'state': 'done',
        'rows': {lb.candidate_id(row): row},
        'searched_at': __import__('time').time(),
    }
    assert routes._chosen_row('b.mp3', lb.candidate_id(row)) is row
    assert routes._search_view('b.mp3').keys() == {'state', 'searched_at'}


def test_replacing_needs_the_music_trash(state):
    state.library_trash = None
    with pytest.raises(lb.UpgradeError) as caught:
        routes._trash_preview('b.mp3', 1)
    assert caught.value.code == 'trash_off'


def test_a_refused_merge_takes_the_new_copy_back_out(
    state, monkeypatch, tmp_path
):
    new = tmp_path / 'b (HQ).mp3'
    new.write_bytes(b'new')
    ctx = SimpleNamespace(download_dir=tmp_path, slskd_dir=None, extra_dirs=[])
    monkeypatch.setattr(routes.api, 'library_context', lambda: ctx)
    monkeypatch.setattr(routes, 'merge_library_listing_file', lambda *a: None)
    monkeypatch.setattr(routes, '_trash_preview', lambda *a: 'batch')
    monkeypatch.setattr(routes.doctor_routes, '_merge_stores', lambda c: None)

    def refuse(*_args):
        raise routes.MergeError('dedupe_replacement_pending', 'b.mp3')

    monkeypatch.setattr(routes, 'plan_merge', refuse)
    with pytest.raises(lb.UpgradeError) as caught:
        asyncio.run(routes._publish('b.mp3', new, tmp_path / 'dl.mp3', 1))
    assert caught.value.code == 'dedupe_replacement_pending'
    assert not new.exists()


def test_publishing_merges_the_old_file_into_the_new_one_then_trashes_it(
    state, monkeypatch, tmp_path
):
    new = tmp_path / 'b (HQ).mp3'
    new.write_bytes(b'new')
    ctx = SimpleNamespace(download_dir=tmp_path, slskd_dir=None, extra_dirs=[])
    calls = []
    plan = SimpleNamespace(
        keep='b (HQ).mp3',
        extras=[('b.mp3', tmp_path / 'b.mp3')],
        playlists={'Mix'},
    )

    async def remove(plan_, ctx_, user_id, batch):
        calls.append(('trash', batch, user_id))
        return ['b.mp3'], []

    async def nothing(*_a, **_k):
        calls.append(('announce',))

    monkeypatch.setattr(routes.api, 'library_context', lambda: ctx)
    monkeypatch.setattr(
        routes,
        'merge_library_listing_file',
        lambda c, f: calls.append(('list', f)),
    )
    monkeypatch.setattr(routes, '_trash_preview', lambda f, u: 'batch-1')
    monkeypatch.setattr(
        routes.doctor_routes, '_merge_stores', lambda c: 'stores'
    )

    def planned(keep, extras, ctx_):
        calls.append(('plan', keep, extras))
        return plan

    monkeypatch.setattr(routes, 'plan_merge', planned)
    monkeypatch.setattr(
        routes, 'relink_duplicates', lambda p, s: calls.append(('relink',))
    )
    monkeypatch.setattr(routes.doctor_routes, '_remove_copies', remove)
    monkeypatch.setattr(
        routes, 'finish_merge', lambda p, s, r: calls.append(('finish', r))
    )
    monkeypatch.setattr(
        routes.doctor_routes, '_publish_library', lambda c: None
    )
    monkeypatch.setattr(routes, 'leftover_references', lambda p, s: [])
    monkeypatch.setattr(
        routes.api, '_schedule_playlist_refresh_after_delete', nothing
    )
    monkeypatch.setattr(routes.api, 'announce_playlists_changed', nothing)

    result = asyncio.run(routes._publish('b.mp3', new, tmp_path / 'dl', 7))

    assert [c[0] for c in calls[:5]] == [
        'list',
        'plan',
        'relink',
        'trash',
        'finish',
    ]
    assert calls[1] == ('plan', 'b (HQ).mp3', ['b.mp3'])
    assert calls[3] == ('trash', 'batch-1', 7)
    assert result['new_file'] == 'b (HQ).mp3'
    assert result['trashed'] is True
    assert result['playlists'] == ['Mix']
    assert new.exists()


def test_a_refused_copy_is_deleted_from_slskds_folder_only(tmp_path):
    slskd = tmp_path / 'slskd'
    inside = slskd / 'Album' / 'Halo.mp3'
    inside.parent.mkdir(parents=True)
    inside.write_bytes(b'x')
    outside = tmp_path / 'music' / 'Halo.mp3'
    outside.parent.mkdir()
    outside.write_bytes(b'x')
    settings = {'source_dir': str(slskd)}
    assert lb.discard_transfer(outside, settings) is False
    assert outside.exists()
    assert lb.discard_transfer(inside, {'source_dir': ''}) is False
    assert lb.discard_transfer(inside, settings) is True
    assert not inside.exists()
