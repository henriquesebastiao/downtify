"""Compare a Spotify playlist with Downtify and Navidrome records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from .library_paths import locate_library_file
from .monitor import KIND_PLAYLIST, SOURCE_SPOTIFY
from .navidrome import _effective_navidrome_settings
from .track_index import normalize_spotify_track_id


@dataclass(slots=True)
class PlaylistDiagnosticsContext:
    catalog: Any
    spotify_cache: Any
    track_index: Any
    navidrome_index: Any
    monitor_db: Any
    hidden: Any
    settings: dict[str, Any]
    download_dir: Path
    slskd_dir: Optional[Path]
    is_admin: bool
    user_id: int
    navidrome_client: Any


@dataclass(slots=True)
class _PlaylistSnapshot:
    tracks: dict[str, dict[str, str]]
    catalog_tracks: list[dict[str, Any]]
    orphan_files: list[dict[str, str]]
    catalog_files: dict[str, str]
    index_files: dict[str, str]
    physical_files: dict[str, str]
    allowed_files: set[str]
    monitor_ids: Optional[set[str]]
    nav_matched: Optional[set[str]]
    nav_count: Optional[int]
    nav_issues: list[dict[str, str]]


def build_playlist_diagnostics(
    name: str,
    files: list[str],
    context: PlaylistDiagnosticsContext,
) -> dict[str, Any]:
    snapshot = _playlist_snapshot(name, files, context)
    if snapshot is None:
        return {'available': False, 'reason': 'spotify_tracks_unavailable'}
    return {'available': True, 'items': _diagnostic_items(snapshot)}


def _playlist_snapshot(
    name: str,
    files: list[str],
    context: PlaylistDiagnosticsContext,
) -> Optional[_PlaylistSnapshot]:
    catalog = context.catalog
    spotify_id = catalog.spotify_id_for_playlist(name) if catalog else None
    cached = (
        context.spotify_cache.get(spotify_id)
        if context.spotify_cache is not None and spotify_id
        else None
    )
    if not cached:
        return None

    tracks = _source_tracks(cached[1])
    catalog_tracks = catalog.list_tracks(name) if catalog else []
    _filter_hidden_tracks(name, tracks, catalog_tracks, context)
    if not tracks:
        return None

    allowed_files = {
        _normalize_path(path) for path in files if _normalize_path(path)
    }
    catalog_files = _catalog_files(name, spotify_id, catalog, allowed_files)
    index_files, source_files, physical_files = _library_files(
        tracks, catalog_files, allowed_files, context
    )
    nav_count, nav_issues = _navidrome_rows(
        name, tracks, source_files, context
    )
    orphan_files = [
        {
            'track_id': str(row.get('track_spotify_id') or ''),
            'label': str(row.get('filename') or ''),
        }
        for row in catalog_tracks
        if str(row.get('track_spotify_id') or '') not in tracks
        and _normalize_path(row.get('filename')) in allowed_files
        and locate_library_file(
            _normalize_path(row.get('filename')),
            context.download_dir,
            context.slskd_dir,
        )
        is not None
    ]
    return _PlaylistSnapshot(
        tracks=tracks,
        catalog_tracks=catalog_tracks,
        orphan_files=orphan_files,
        catalog_files=catalog_files,
        index_files=index_files,
        physical_files=physical_files,
        allowed_files=allowed_files,
        monitor_ids=_monitor_track_ids(spotify_id, context),
        nav_matched=_navidrome_matched_ids(tracks, source_files, context),
        nav_count=nav_count,
        nav_issues=nav_issues,
    )


def _library_files(
    tracks: dict[str, dict[str, str]],
    catalog_files: dict[str, str],
    allowed_files: set[str],
    context: PlaylistDiagnosticsContext,
) -> tuple[dict[str, str], dict[str, Optional[str]], dict[str, str]]:
    index_files = (
        context.track_index.filenames_by_spotify_id()
        if context.track_index is not None
        else {}
    )
    source_files = {
        track_id: catalog_files.get(track_id) or index_files.get(track_id)
        for track_id in tracks
    }
    physical_files = {
        track_id: filename
        for track_id, filename in source_files.items()
        if filename in allowed_files
        and locate_library_file(
            filename, context.download_dir, context.slskd_dir
        )
        is not None
    }
    return index_files, source_files, physical_files


def _diagnostic_items(snapshot: _PlaylistSnapshot) -> list[dict[str, Any]]:
    tracks = snapshot.tracks
    catalog_files = snapshot.catalog_files
    index_files = snapshot.index_files
    physical_files = snapshot.physical_files
    monitor_ids = snapshot.monitor_ids
    nav_matched = snapshot.nav_matched
    missing_downloads = set(tracks) - set(catalog_files)
    missing_files = set(tracks) - set(physical_files)
    missing_index = set(tracks) - set(index_files)
    orphans = snapshot.orphan_files
    return [
        {'key': 'spotify_tracks', 'count': len(tracks), 'issues': []},
        {
            'key': 'downloaded',
            'count': len(tracks) - len(missing_downloads),
            'issues': _affected(tracks, missing_downloads),
        },
        {
            'key': 'physical_files',
            'count': len(physical_files),
            'issues': _affected(tracks, missing_files),
        },
        {
            'key': 'track_index',
            'count': len(set(tracks) - missing_index),
            'issues': _affected(tracks, missing_index),
        },
        {
            'key': 'monitor_history',
            'count': len(set(tracks) & monitor_ids)
            if monitor_ids is not None
            else None,
            'issues': _affected(tracks, set(tracks) - monitor_ids)
            if monitor_ids is not None
            else [],
        },
        {
            'key': 'navidrome_matched',
            'count': len(nav_matched) if nav_matched is not None else None,
            'issues': _affected(tracks, set(tracks) - nav_matched)
            if nav_matched is not None
            else [],
        },
        {
            'key': 'navidrome_rows',
            'count': snapshot.nav_count,
            'issues': snapshot.nav_issues,
        },
        {
            'key': 'missing_files',
            'count': len(missing_files),
            'issues': _affected(tracks, missing_files),
        },
        {'key': 'orphan_files', 'count': len(orphans), 'issues': orphans},
    ]


def _normalize_path(value: Any) -> str:
    return str(value or '').strip().replace('\\', '/')


def _source_tracks(rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    tracks: dict[str, dict[str, str]] = {}
    for song in rows:
        track_id = normalize_spotify_track_id(song)
        if not track_id or track_id in tracks:
            continue
        artists = song.get('artists') or (
            [song['artist']] if song.get('artist') else []
        )
        label = ' - '.join(
            part
            for part in (
                ', '.join(str(artist) for artist in artists),
                str(song.get('name') or ''),
            )
            if part
        )
        tracks[track_id] = {'track_id': track_id, 'label': label or track_id}
    return tracks


def _filter_hidden_tracks(
    name: str,
    tracks: dict[str, dict[str, str]],
    catalog_tracks: list[dict[str, Any]],
    context: PlaylistDiagnosticsContext,
) -> None:
    if context.is_admin or context.hidden is None:
        return
    hidden = context.hidden.songs(name)
    hidden_ids = set(hidden.track_ids)
    for row in catalog_tracks:
        if hidden.hides_file(
            row.get('filename'), str(row.get('content_key') or '')
        ):
            hidden_ids.add(str(row.get('track_spotify_id') or ''))
    for track_id in hidden_ids:
        tracks.pop(track_id, None)


def _catalog_files(
    name: str,
    spotify_id: Optional[str],
    catalog: Any,
    allowed_files: set[str],
) -> dict[str, str]:
    if catalog is None:
        return {}
    names = {name}
    if spotify_id:
        names.update(
            row['name']
            for row in catalog.list_playlists_with_spotify_id()
            if row['spotify_id'] == spotify_id
        )
    result: dict[str, str] = {}
    for playlist_name in names:
        for row in catalog.list_tracks(playlist_name):
            track_id = str(row.get('track_spotify_id') or '').strip()
            filename = _normalize_path(row.get('filename'))
            if track_id and filename in allowed_files:
                result.setdefault(track_id, filename)
    return result


def _affected(
    tracks: dict[str, dict[str, str]], track_ids: set[str]
) -> list[dict[str, str]]:
    return [tracks[track_id] for track_id in tracks if track_id in track_ids]


def _monitor_track_ids(
    spotify_id: Optional[str], context: PlaylistDiagnosticsContext
) -> Optional[set[str]]:
    db = context.monitor_db
    if db is None:
        return None
    watch = db.get_by_spotify_id(
        str(spotify_id), None if context.is_admin else context.user_id
    )
    if (
        watch is None
        or watch.kind != KIND_PLAYLIST
        or watch.source != SOURCE_SPOTIFY
    ):
        return None
    return set(db.get_track_filenames(watch.id))


def _navidrome_matched_ids(
    tracks: dict[str, dict[str, str]],
    source_files: dict[str, Optional[str]],
    context: PlaylistDiagnosticsContext,
) -> Optional[set[str]]:
    cfg = _effective_navidrome_settings(context.settings)
    index = context.navidrome_index
    if (
        not context.settings.get('sync_navidrome', True)
        or not cfg.get('enabled')
        or index is None
    ):
        return None
    return {
        track_id
        for track_id in tracks
        if index.lookup_spotify(track_id)
        or (
            source_files.get(track_id)
            and index.lookup_filename(source_files[track_id])
        )
    }


def _navidrome_rows(
    name: str,
    tracks: dict[str, dict[str, str]],
    source_files: dict[str, Optional[str]],
    context: PlaylistDiagnosticsContext,
) -> tuple[Optional[int], list[dict[str, str]]]:
    cfg = _effective_navidrome_settings(context.settings)
    if not context.settings.get('sync_navidrome', True) or not cfg.get(
        'enabled'
    ):
        return None, []
    try:
        client = context.navidrome_client(cfg)
        if not client.configured():
            return None, []
        playlist_ids = client.find_playlist_ids_by_name(name)
        songs = (
            client.get_playlist_songs(playlist_ids[0]) if playlist_ids else []
        )
    except Exception as exc:
        logger.info(
            'playlist diagnostics: Navidrome lookup failed name={!r} err={}',
            name,
            exc,
        )
        return None, []

    index = context.navidrome_index
    if index is None:
        return len(songs), []
    actual_ids = {str(song.get('id') or '') for song in songs}
    expected_ids: set[str] = set()
    missing_ids: set[str] = set()
    for track_id in tracks:
        song_id = index.lookup_spotify(track_id)
        filename = source_files.get(track_id)
        if not song_id and filename:
            song_id = index.lookup_filename(filename)
        if song_id:
            expected_ids.add(song_id)
        if not song_id or song_id not in actual_ids:
            missing_ids.add(track_id)
    issues = _affected(tracks, missing_ids)
    for position, song in enumerate(songs):
        song_id = str(song.get('id') or '')
        if not song_id or song_id in expected_ids:
            continue
        title = str(song.get('title') or song.get('name') or '')
        artist = str(song.get('artist') or '')
        issues.append({
            'track_id': song_id,
            'label': f'{artist} - {title}'
            if artist and title
            else title or artist or f'Navidrome row {position + 1}',
        })
    return len(songs), issues
