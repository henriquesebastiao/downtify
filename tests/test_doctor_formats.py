"""The Doctor's "Formats to convert": a FLAC in the library becomes an MP3
that takes over everything pointing at it (playlists, the track index,
watches), and the FLAC is removed - as a duplicate merge does.

Real stores on temporary databases and a real FLAC made by ffmpeg.
"""

from __future__ import annotations

import asyncio
import shutil

import pytest
from fastapi import HTTPException
from mutagen.mp3 import MP3

from downtify import doctor_routes, format_convert, m3u
from tests.test_duplicate_merge import ONE_DANCE, lib  # noqa: F401  # fixture
from tests.test_format_convert import _flac

pytestmark = pytest.mark.skipif(
    shutil.which('ffmpeg') is None, reason='needs ffmpeg'
)

FLAC_NAME = 'Drake/Drake - One Dance.flac'
MP3_NAME = 'Drake/Drake - One Dance.mp3'


@pytest.fixture
def doctor(monkeypatch, lib):  # noqa: F811  # the fixture above
    async def nothing(*_args, **_kwargs):
        return None

    state = doctor_routes.api.state
    monkeypatch.setattr(doctor_routes, '_ctx', lambda: lib.ctx)
    monkeypatch.setattr(doctor_routes, '_merge_stores', lambda ctx: lib.merge)
    monkeypatch.setattr(doctor_routes, '_publish_library', lambda ctx: None)
    monkeypatch.setattr(state, 'library_trash', None)
    monkeypatch.setattr(state, 'track_index', lib.track_index)
    monkeypatch.setattr(state, 'playlist_catalog', lib.catalog)
    monkeypatch.setattr(state, 'cover_cache', None)
    monkeypatch.setattr(state, 'metadata_cache', None)
    monkeypatch.setattr(state, 'navidrome_index', None)
    monkeypatch.setattr(state, 'settings', {'bitrate': '320'})
    monkeypatch.setattr(
        doctor_routes.api, 'announce_playlists_changed', nothing
    )
    monkeypatch.setattr(
        doctor_routes.api, '_schedule_playlist_refresh_after_delete', nothing
    )
    monkeypatch.setattr(doctor_routes, '_state', {})
    monkeypatch.setattr(doctor_routes, '_stale', set())
    return lib


def _convert(files):
    return asyncio.run(doctor_routes._convert_files({}, files, 1))


def test_a_flac_is_replaced_by_an_mp3_that_keeps_its_references(doctor):
    stores = doctor
    flac = _flac(stores.root / FLAC_NAME)
    stores.track_index.register(ONE_DANCE, FLAC_NAME, full_path=flac)
    (stores.root / 'Chill Mix.m3u').write_text(
        f'#EXTM3U\n#EXTINF:3,One Dance\n{FLAC_NAME}\n', encoding='utf-8'
    )
    (stores.root / 'Mine.m3u').write_text(
        f'#EXTM3U\n{m3u.MANUAL_M3U_MARKER}\n{FLAC_NAME}\n', encoding='utf-8'
    )
    watch = stores.monitor.add_playlist('37i9dQZF1E4chill', 'Chill Mix', 'url')
    stores.monitor.mark_track_downloaded(watch.id, ONE_DANCE, FLAC_NAME)
    size_before = flac.stat().st_size

    result = _convert([FLAC_NAME])

    assert result['failed'] == []
    [done] = result['converted']
    assert (done['file'], done['new_file']) == (FLAC_NAME, MP3_NAME)
    assert done['size_before'] == size_before
    assert not flac.exists()
    mp3 = stores.root / MP3_NAME
    assert round(MP3(str(mp3)).info.bitrate / 1000) == 320
    assert stores.track_index.lookup(ONE_DANCE) == MP3_NAME
    assert stores.monitor.get_track_filenames(watch.id)[ONE_DANCE] == MP3_NAME
    for playlist in ('Chill Mix.m3u', 'Mine.m3u'):
        text = (stores.root / playlist).read_text(encoding='utf-8')
        assert MP3_NAME in text
        assert FLAC_NAME not in text


def test_a_file_that_cannot_be_converted_is_left_alone(doctor):
    stores = doctor
    broken = stores.root / 'Drake' / 'Broken.flac'
    broken.write_bytes(b'not audio')

    result = _convert(['Drake/Broken.flac'])

    assert result['converted'] == []
    assert result['failed'] == [
        {'file': 'Drake/Broken.flac', 'error': 'convert_failed'}
    ]
    assert broken.read_bytes() == b'not audio'
    assert not (stores.root / 'Drake' / 'Broken.mp3').exists()


def test_when_the_swap_is_refused_the_new_mp3_is_removed(doctor, monkeypatch):
    stores = doctor
    flac = _flac(stores.root / FLAC_NAME)

    def refuse(*_args):
        raise doctor_routes.MergeError('dedupe_replacement_pending', FLAC_NAME)

    monkeypatch.setattr(doctor_routes, 'plan_merge', refuse)

    result = _convert([FLAC_NAME])

    assert result['failed'][0]['error'] == 'dedupe_replacement_pending'
    assert flac.exists()
    assert not (stores.root / MP3_NAME).exists()


def test_a_stop_ends_the_run_between_files(doctor):
    stores = doctor
    _flac(stores.root / FLAC_NAME)
    job = {'cancel': True}

    result = asyncio.run(doctor_routes._convert_files(job, [FLAC_NAME], 1))

    assert result['converted'] == []
    assert result['cancelled']
    assert result['left'] == 1


def test_only_files_the_last_scan_listed_can_be_converted(doctor, monkeypatch):
    monkeypatch.setattr(format_convert, 'ffmpeg', lambda: 'ffmpeg')

    with pytest.raises(HTTPException) as err:
        asyncio.run(
            doctor_routes.formats_convert(
                doctor_routes.FormatConvert(files=[FLAC_NAME]), _Admin()
            )
        )

    assert err.value.status_code == 409
    assert err.value.detail['code'] == 'rescan_first'


def test_the_scan_lists_the_chosen_formats(doctor, monkeypatch):
    rows = [
        {'file': FLAC_NAME, 'size': 30_000_000, 'duration': 174},
        {'file': 'Drake/Other.mp3', 'size': 7_000_000, 'duration': 174},
    ]
    monkeypatch.setattr(
        doctor_routes.api,
        '_usage_library_inputs',
        lambda ctx: {
            'entries': rows,
            'sources': {},
            'slskd_in_place': False,
        },
    )
    monkeypatch.setattr(doctor_routes, '_m3u_infos', lambda ctx: [])
    monkeypatch.setattr(doctor_routes, '_referenced', lambda *a: set())

    found = doctor_routes._formats_found({}, ['flac'])

    assert [f['file'] for f in found['files']] == [FLAC_NAME]
    assert found['count'] == 1
    assert found['estimated'] == 174 * 320 * 1000 // 8
    assert doctor_routes._state['formats'] == {FLAC_NAME}


class _Admin:
    scope: dict = {'state': {}}
