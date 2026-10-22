from __future__ import annotations

from copy import deepcopy

from downtify.catalog_worker import fold_library_entries
from downtify.external_library import (
    effective_external_library,
    finish_library_entries,
)
from downtify.library_catalog import LibraryContext, library_context_from_state
from downtify.library_paths import extra_dir_id
from downtify.library_paths_cache import _cache_key


def row(file, **kwargs):
    return {
        'file': file,
        'title': 'Song',
        'artist': 'Artist',
        'album': 'Album',
        'duration': 173,
        **kwargs,
    }


def test_preferred_recording_can_replace_clip_in_listing_without_mutation():
    owned = row('Artist/Song.mp3', duration=190, playlists=['Favorites'])
    external = row('ext/preferred/Artist/Song.flac', playlists=['Imported'])
    entries = [owned, external]
    before = deepcopy(entries)
    result = finish_library_entries(entries, 'preferred')
    assert [e['file'] for e in result] == [external['file']]
    assert result[0]['playlists'] == ['Imported', 'Favorites']
    assert entries == before


def test_distinct_single_album_and_version_are_not_folded():
    entries = [
        row('old.mp3'),
        row('ext/preferred/single.mp3', album='Single'),
        row('ext/preferred/live.mp3', title='Song (Live)'),
        row('ext/preferred/studio.mp3'),
    ]
    result = finish_library_entries(entries, 'preferred')
    assert {e['file'] for e in result} == {e['file'] for e in entries[1:]}


def test_unknown_album_does_not_hide_another_file():
    entries = [row('owned.mp3', album=''), row('ext/preferred/preferred.mp3')]
    assert len(finish_library_entries(entries, 'preferred')) == 2


def test_default_behavior_stays_owned_first():
    entries = [row('owned.mp3'), row('ext/preferred/preferred.mp3')]
    assert finish_library_entries(entries) == entries[:1]


def test_absent_preferred_folder_falls_back():
    entries = [row('owned.mp3'), row('ext/other/other.mp3')]
    assert finish_library_entries(
        entries, 'missing'
    ) == finish_library_entries(entries)


def test_primary_setting_only_accepts_registered_folder(tmp_path):
    folder = str(tmp_path)
    assert (
        effective_external_library({
            'external_library': {
                'folders': [folder],
                'primary_folder': folder,
            }
        })['primary_folder']
        == folder
    )
    assert 'primary_folder' not in effective_external_library({
        'external_library': {
            'folders': [],
            'primary_folder': folder,
        }
    })


def test_context_and_cache_key_include_primary_but_default_cache_is_stable(
    tmp_path,
):
    folder = tmp_path / 'extra'
    base = tmp_path / 'owned'
    settings = {
        'external_library': {
            'folders': [str(folder)],
            'primary_folder': str(folder),
        }
    }
    ctx = library_context_from_state(base, settings)
    assert ctx.primary_extra_id == extra_dir_id(folder)
    default = LibraryContext(base, extra_dirs=(folder,))
    assert _cache_key(ctx) != _cache_key(default)
    assert '|primary=' not in _cache_key(default)


def test_inline_worker_accepts_the_preference():
    entries = [row('owned.mp3'), row('ext/preferred/preferred.mp3')]
    assert fold_library_entries(entries, 'preferred')[0]['file'].startswith(
        'ext/preferred/'
    )
