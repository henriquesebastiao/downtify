"""Navidrome integration via the Subsonic API (playlist sync)."""

from __future__ import annotations

import hashlib
import re
import secrets
import time
import unicodedata
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlencode

import requests
from loguru import logger

# Subsonic createPlaylist via GET appends every songId to the query string; large
# playlists hit HTTP 414. POST form bodies avoid that; we still batch adds.
_PLAYLIST_SONG_ID_BATCH = 80


def _song_id_batches(
    song_ids: list[str], batch_size: int = _PLAYLIST_SONG_ID_BATCH
) -> list[list[str]]:
    batches: list[list[str]] = []
    for index in range(0, len(song_ids), batch_size):
        batches.append(song_ids[index : index + batch_size])
    return batches


def _parse_subsonic_http_response(resp: requests.Response) -> dict[str, Any]:
    resp.raise_for_status()
    data = resp.json()
    body = data.get('subsonic-response') if isinstance(data, dict) else None
    if not isinstance(body, dict):
        raise ValueError('Invalid Subsonic response')
    if body.get('status') == 'failed':
        err = body.get('error') or {}
        message = err.get('message') if isinstance(err, dict) else str(err)
        raise ValueError(str(message or 'Subsonic request failed'))
    return body


def _playlist_id_from_body(
    body: dict[str, Any], fallback: Optional[str] = None
) -> str:
    playlist = body.get('playlist')
    if isinstance(playlist, dict):
        pid = str(playlist.get('id') or '').strip()
        if pid:
            return pid
    if fallback:
        return fallback
    raise ValueError('createPlaylist returned no playlist id')


@dataclass
class PlaylistSyncResult:
    playlist_id: str
    playlist_name: str
    matched: int
    total: int
    scanned: bool
    scan_complete: bool = False


def _search_title(title: str) -> str:
    """Title used for Navidrome search (strip feat. suffixes, keep remix names)."""

    text = str(title or '').strip()
    lowered = text.casefold()
    for marker in (' - feat.', ' (feat.', ' - ft.', ' (ft.', ' - featuring '):
        idx = lowered.find(marker)
        if idx > 0:
            return text[:idx].strip()
    return text


def _normalize_path_text(path: str) -> str:
    return unicodedata.normalize('NFC', str(path or '').replace('\\', '/'))


def _path_match_keys(filename: str) -> list[str]:
    """Path fragments for matching Navidrome ``path`` (any library root prefix)."""

    text = _normalize_path_text(filename).casefold().strip()
    if not text:
        return []
    keys: list[str] = [text]
    parts = [part for part in text.split('/') if part]
    if len(parts) >= 2:
        tail = '/'.join(parts[-2:])
        if tail not in keys:
            keys.append(tail)
    base = text.rsplit('/', 1)[-1]
    if base and base not in keys:
        keys.append(base)
    if text.startswith('slskd/'):
        without_slskd = text[len('slskd/') :]
        if without_slskd not in keys:
            keys.append(without_slskd)
    return keys


def _navidrome_path_basename(path: str) -> str:
    return str(path or '').replace('\\', '/').casefold().rsplit('/', 1)[-1]


def _normalize_filename_key(name: str) -> str:
    text = str(name or '').casefold().replace('&', ' and ')
    text = re.sub(r'[^\w\s.-]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def _loosen_search_query(text: str) -> str:
    """Strip punctuation so Navidrome full-text search finds filename-like rows."""

    lowered = _normalize_path_text(text).casefold().replace('&', ' and ')
    cleaned = re.sub(r'[^\w\s-]', ' ', lowered)
    return re.sub(r'\s+', ' ', cleaned).strip()


def _queries_from_filename_stem(stem: str) -> list[str]:
    text = str(stem or '').strip()
    if not text:
        return []
    out: list[str] = []
    if ' - ' in text:
        artists_part, title_part = text.rsplit(' - ', 1)
        artists_part = artists_part.strip()
        title_part = title_part.strip()
        if title_part:
            out.append(title_part)
        if artists_part:
            out.append(artists_part)
            lead = artists_part.split(',')[0].strip()
            if lead and title_part:
                out.append(f'{title_part} {lead}')
                out.append(f'{lead} {title_part}')
    loosened = _loosen_search_query(text)
    if loosened and loosened not in out:
        out.append(loosened)
    return out


def _basename_aligned(stored: str, indexed: str) -> bool:
    if stored == indexed:
        return True
    left = _normalize_filename_key(stored)
    right = _normalize_filename_key(indexed)
    if not left or not right:
        return False
    if left == right:
        return True
    if (
        len(left) >= 12
        and len(right) >= 12
        and (left in right or right in left)
    ):
        return True
    return False


def _path_matches(path_keys: list[str], navidrome_path: str) -> bool:
    """True when Downtify's stored path lines up with Navidrome's indexed path."""

    c_path = _normalize_path_text(navidrome_path).casefold()
    if not path_keys or not c_path:
        return False
    c_base = _navidrome_path_basename(c_path)
    for key in path_keys:
        if not key:
            continue
        if c_path == key or c_path.endswith(f'/{key}'):
            return True
        if key in c_path:
            return True
        key_base = key.rsplit('/', 1)[-1]
        if key_base and _basename_aligned(key_base, c_base):
            return True
    return False


def _search_queries_for_song(
    song: dict[str, Any], path_keys: list[str]
) -> list[str]:
    """Build search queries; filename-first so indexed paths are found."""

    title = _search_title(str(song.get('name') or ''))
    artists = [str(a) for a in (song.get('artists') or []) if str(a).strip()]
    artist = artists[0] if artists else ''
    queries: list[str] = []

    def add(query: str) -> None:
        text = str(query or '').strip()
        if text and text not in queries:
            queries.append(text)

    if path_keys:
        basename = path_keys[0].rsplit('/', 1)[-1]
        stem = basename.rsplit('.', 1)[0] if basename else ''
        for item in _queries_from_filename_stem(stem):
            add(item)
        add(stem)
        add(basename)
        add(path_keys[0])
        for key in path_keys[1:]:
            add(key)
    add(f'{title} {artist}'.strip())
    if len(artists) > 1:
        add(f'{title} {", ".join(artists[:3])}'.strip())
    return queries


def _pick_song_id_from_candidates(
    songs: list[dict[str, Any]],
    song: dict[str, Any],
    path_keys: list[str],
    target_duration: int,
) -> Optional[str]:
    title = _search_title(str(song.get('name') or ''))
    artists = [str(a) for a in (song.get('artists') or []) if str(a).strip()]
    artist = artists[0] if artists else ''
    require_artist = bool(path_keys)

    for candidate in songs:
        if not isinstance(candidate, dict):
            continue
        cid = str(candidate.get('id') or '').strip()
        if not cid:
            continue
        c_path = str(candidate.get('path') or '')
        if path_keys and _path_matches(path_keys, c_path):
            return cid

    for candidate in songs:
        if not isinstance(candidate, dict):
            continue
        cid = str(candidate.get('id') or '').strip()
        if not cid:
            continue
        c_artist = str(candidate.get('artist') or '')
        c_title = str(candidate.get('title') or '')
        c_duration = int(candidate.get('duration') or 0)

        artist_match = artist and artist.casefold() in c_artist.casefold()
        title_match = (
            title.casefold() == c_title.casefold()
            or str(song.get('name') or '').casefold() == c_title.casefold()
        )
        duration_match = (
            not target_duration
            or not c_duration
            or abs(target_duration - c_duration) < 10
        )

        if artist_match and title_match and duration_match:
            return cid
        if not require_artist and title_match and duration_match:
            return cid
    return None


def _effective_navidrome_settings(settings: dict[str, Any]) -> dict[str, Any]:
    raw = settings.get('navidrome')
    if not isinstance(raw, dict):
        raw = {}
    url = str(raw.get('url') or '').strip().rstrip('/')
    username = str(raw.get('username') or '').strip()
    password = str(raw.get('password') or '')
    admin_username = str(raw.get('admin_username') or '').strip()
    admin_password = str(raw.get('admin_password') or '')
    try:
        scan_wait_seconds = int(raw.get('scan_wait_seconds') or 120)
    except (TypeError, ValueError):
        scan_wait_seconds = 120
    scan_wait_seconds = min(600, max(10, scan_wait_seconds))
    try:
        scan_poll_seconds = int(raw.get('scan_poll_seconds') or 5)
    except (TypeError, ValueError):
        scan_poll_seconds = 5
    scan_poll_seconds = min(120, max(2, scan_poll_seconds))
    try:
        scan_retry_seconds = int(raw.get('scan_retry_seconds') or 15)
    except (TypeError, ValueError):
        scan_retry_seconds = 15
    scan_retry_seconds = min(120, max(0, scan_retry_seconds))
    return {
        'enabled': bool(raw.get('enabled', False)),
        'url': url,
        'username': username,
        'password': password,
        'admin_username': admin_username,
        'admin_password': admin_password,
        'public_playlist': bool(raw.get('public_playlist', False)),
        'scan_after_download': bool(raw.get('scan_after_download', True)),
        'scan_full': bool(raw.get('scan_full', False)),
        'scan_wait_seconds': scan_wait_seconds,
        'scan_poll_seconds': scan_poll_seconds,
        'scan_retry_seconds': scan_retry_seconds,
        'client_name': str(raw.get('client_name') or 'Downtify').strip()
        or 'Downtify',
        'api_version': str(raw.get('api_version') or '1.16.1').strip()
        or '1.16.1',
    }


class NavidromeClient:
    """Minimal Subsonic client for Navidrome playlist and library operations."""

    def __init__(self, cfg: dict[str, Any]):
        self.base_url = str(cfg.get('url') or '').rstrip('/')
        self.username = str(cfg.get('username') or '')
        self.password = str(cfg.get('password') or '')
        self.admin_username = str(cfg.get('admin_username') or '')
        self.admin_password = str(cfg.get('admin_password') or '')
        self.client_name = str(cfg.get('client_name') or 'Downtify')
        self.api_version = str(cfg.get('api_version') or '1.16.1')
        self.scan_poll_seconds = int(cfg.get('scan_poll_seconds') or 5)
        self.timeout = 30
        self._token = ''
        self._salt = ''

    def configured(self) -> bool:
        return bool(self.base_url and self.username and self.password)

    def _refresh_auth(self) -> None:
        salt = secrets.token_urlsafe(8)[:12]
        token = hashlib.md5(f'{self.password}{salt}'.encode()).hexdigest()
        self._salt = salt
        self._token = token

    def _auth_query(
        self,
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> dict[str, str]:
        user = username if username is not None else self.username
        pwd = password if password is not None else self.password
        salt = secrets.token_urlsafe(8)[:12]
        token = hashlib.md5(f'{pwd}{salt}'.encode()).hexdigest()
        return {
            'u': user,
            't': token,
            's': salt,
            'v': self.api_version,
            'c': self.client_name,
            'f': 'json',
        }

    def _request(
        self,
        endpoint: str,
        extra: Optional[dict[str, Any]] = None,
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> dict[str, Any]:
        params = self._auth_query(username=username, password=password)
        if extra:
            for key, value in extra.items():
                if value is None:
                    continue
                params[key] = str(value)
        url = f'{self.base_url}/rest/{endpoint}?{urlencode(params)}'
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        body = (
            data.get('subsonic-response') if isinstance(data, dict) else None
        )
        if not isinstance(body, dict):
            raise ValueError('Invalid Subsonic response')
        if body.get('status') == 'failed':
            err = body.get('error') or {}
            message = err.get('message') if isinstance(err, dict) else str(err)
            raise ValueError(str(message or 'Subsonic request failed'))
        return body

    def ping(self) -> bool:
        try:
            self._request('ping')
            return True
        except Exception as exc:
            logger.info(
                'navidrome: ping failed url={!r} err={}', self.base_url, exc
            )
            return False

    def _scan_credentials(self) -> tuple[str, str]:
        if self.admin_username and self.admin_password:
            return self.admin_username, self.admin_password
        return self.username, self.password

    def start_scan(self, *, full: bool = False) -> None:
        """Trigger Navidrome ``startScan`` (incremental by default, like Explo/deemix hooks)."""

        extra: dict[str, Any] = {}
        if full:
            extra['fullScan'] = 'true'
        user, pwd = self._scan_credentials()
        self._request('startScan', extra or None, username=user, password=pwd)

    def wait_scan_complete(self, max_wait_seconds: int) -> bool:
        deadline = time.monotonic() + max(10, max_wait_seconds)
        user, pwd = self._scan_credentials()
        while time.monotonic() < deadline:
            try:
                body = self._request(
                    'getScanStatus', username=user, password=pwd
                )
            except Exception as exc:
                logger.info('navidrome: scan status failed err={}', exc)
                return False
            status = body.get('scanStatus') if isinstance(body, dict) else None
            if isinstance(status, dict) and not status.get('scanning'):
                return True
            time.sleep(self.scan_poll_seconds)
        logger.warning(
            'navidrome: library scan still running after {}s; '
            'playlist match may be incomplete',
            max_wait_seconds,
        )
        return False

    def _search3_songs(
        self, query: str, *, song_count: int = 200
    ) -> list[dict]:
        body = self._request(
            'search3',
            {'query': query, 'songCount': song_count},
        )
        results = body.get('searchResult3') if isinstance(body, dict) else None
        songs: list[Any] = []
        if isinstance(results, dict):
            songs = results.get('song') or []
        if isinstance(songs, dict):
            songs = [songs]
        if not isinstance(songs, list):
            return []
        return [s for s in songs if isinstance(s, dict)]

    def search_song_id(self, song: dict[str, Any]) -> Optional[str]:
        path_keys = _path_match_keys(str(song.get('filename') or ''))
        queries = _search_queries_for_song(song, path_keys)
        if not queries:
            return None

        target_duration = int(song.get('duration') or 0)
        if target_duration > 1000:
            target_duration //= 1000

        seen_ids: set[str] = set()
        candidates: list[dict[str, Any]] = []
        for query in queries:
            for candidate in self._search3_songs(query):
                cid = str(candidate.get('id') or '').strip()
                if not cid or cid in seen_ids:
                    continue
                seen_ids.add(cid)
                candidates.append(candidate)
        return _pick_song_id_from_candidates(
            candidates, song, path_keys, target_duration
        )

    def find_playlist_ids_by_name(self, name: str) -> list[str]:
        """Return all playlist IDs with an exact *name* match (newest API order)."""

        body = self._request('getPlaylists')
        playlists = body.get('playlists') if isinstance(body, dict) else None
        items = []
        if isinstance(playlists, dict):
            items = playlists.get('playlist') or []
        if isinstance(items, dict):
            items = [items]
        ids: list[str] = []
        for pl in items:
            if not isinstance(pl, dict):
                continue
            if str(pl.get('name') or '') != name:
                continue
            pid = str(pl.get('id') or '').strip()
            if pid:
                ids.append(pid)
        return ids

    def delete_playlist(self, playlist_id: str) -> None:
        self._request('deletePlaylist', {'id': playlist_id})

    def _rest_post(
        self,
        endpoint: str,
        query: dict[str, str],
        form_pairs: list[tuple[str, str]],
    ) -> dict[str, Any]:
        url = f'{self.base_url}/rest/{endpoint}'
        resp = requests.post(
            url, params=query, data=form_pairs, timeout=self.timeout
        )
        return _parse_subsonic_http_response(resp)

    def _add_songs_to_playlist(
        self, playlist_id: str, song_ids: list[str]
    ) -> None:
        if not song_ids:
            return
        query = self._auth_query()
        query['playlistId'] = playlist_id
        form = [('songIdToAdd', sid) for sid in song_ids]
        self._rest_post('updatePlaylist', query, form)

    def _create_or_replace_playlist(
        self,
        name: str,
        song_ids: list[str],
        *,
        playlist_id: Optional[str] = None,
    ) -> str:
        """Create a playlist or replace tracks on an existing one (Subsonic semantics)."""

        if not song_ids:
            raise ValueError('No songs matched in Navidrome library')
        batches = _song_id_batches(song_ids)
        query = self._auth_query()
        query['name'] = name
        if playlist_id:
            query['playlistId'] = playlist_id
        form = [('songId', sid) for sid in batches[0]]
        logger.info(
            'navidrome: createPlaylist POST batch 1/{} songs={} (uri-safe)',
            len(batches),
            len(form),
        )
        body = self._rest_post('createPlaylist', query, form)
        pid = _playlist_id_from_body(body, playlist_id)
        for index, batch in enumerate(batches[1:], start=2):
            logger.info(
                'navidrome: updatePlaylist POST batch {}/{} songs={}',
                index,
                len(batches),
                len(batch),
            )
            self._add_songs_to_playlist(pid, batch)
        return pid

    def create_playlist(self, name: str, song_ids: list[str]) -> str:
        return self._create_or_replace_playlist(name, song_ids)

    def replace_playlist(
        self, playlist_id: str, name: str, song_ids: list[str]
    ) -> str:
        """Replace all tracks on an existing playlist (same ID, no delete)."""

        return self._create_or_replace_playlist(
            name, song_ids, playlist_id=playlist_id
        )

    def update_playlist_meta(
        self,
        playlist_id: str,
        *,
        comment: str,
        public: bool,
    ) -> None:
        self._request(
            'updatePlaylist',
            {
                'playlistId': playlist_id,
                'comment': comment,
                'public': str(public).lower(),
            },
        )


def _scan_wait_budget(cfg: dict[str, Any], track_count: int) -> int:
    """Seconds to wait for Navidrome scan; scales slightly with playlist size."""

    base = int(cfg['scan_wait_seconds'])
    return min(900, max(base, 30 + track_count * 2))


def _song_label(song: dict[str, Any]) -> str:
    label = str(song.get('name') or 'unknown')
    artists = song.get('artists') or []
    if artists:
        label = f'{", ".join(str(a) for a in artists)} - {label}'
    fn = str(song.get('filename') or '').strip()
    return f'{label} ({fn})' if fn else label


def _match_songs_in_library(
    client: NavidromeClient,
    songs: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    song_ids: list[str] = []
    unmatched: list[dict[str, Any]] = []
    for song in songs:
        sid = client.search_song_id(song)
        if sid:
            song_ids.append(sid)
        else:
            unmatched.append(song)
    return song_ids, unmatched


def _trigger_library_scan(
    client: NavidromeClient,
    cfg: dict[str, Any],
    track_count: int,
) -> bool:
    """Start Navidrome scan and block until idle or timeout. Returns scan finished."""

    wait_seconds = _scan_wait_budget(cfg, track_count)
    mode = 'full' if cfg.get('scan_full') else 'incremental'
    logger.info(
        'navidrome: starting {} library scan before playlist sync '
        '(up to {}s, {} tracks)',
        mode,
        wait_seconds,
        track_count,
    )
    client.start_scan(full=bool(cfg.get('scan_full')))
    if client.wait_scan_complete(wait_seconds):
        logger.info('navidrome: library scan finished')
        return True
    return False


def sync_playlist_to_navidrome(
    playlist_name: str,
    songs: list[dict[str, Any]],
    settings: dict[str, Any],
    *,
    comment: str = 'Synced from Spotify via Downtify',
) -> Optional[PlaylistSyncResult]:
    """Match *songs* in Navidrome and create/replace a server playlist."""
    cfg = _effective_navidrome_settings(settings)
    if not cfg.get('enabled'):
        return None
    client = NavidromeClient(cfg)
    if not client.configured():
        logger.info('navidrome: missing url/username/password')
        return None
    if not client.ping():
        logger.info('navidrome: server unreachable url={!r}', cfg.get('url'))
        return None
    if not songs:
        return None

    scanned = False
    scan_complete = False
    if cfg.get('scan_after_download'):
        try:
            scanned = True
            scan_complete = _trigger_library_scan(client, cfg, len(songs))
        except Exception as exc:
            logger.info('navidrome: library scan failed err={}', exc)

    song_ids, pending = _match_songs_in_library(client, songs)
    retry_seconds = int(cfg.get('scan_retry_seconds') or 0)
    if pending and scanned and retry_seconds > 0:
        logger.info(
            'navidrome: {} track(s) not indexed yet; retrying match in {}s',
            len(pending),
            retry_seconds,
        )
        time.sleep(retry_seconds)
        extra_ids, pending = _match_songs_in_library(client, pending)
        song_ids.extend(extra_ids)

    total = len(songs)
    matched = len(song_ids)
    if pending:
        labels = [_song_label(s) for s in pending]
        logger.info(
            'navidrome: {} track(s) not in library index for playlist={!r}: {}',
            len(pending),
            playlist_name,
            '; '.join(labels[:12]) + ('; ...' if len(labels) > 12 else ''),
        )
    if matched == 0:
        logger.info(
            'navidrome: no tracks matched library for playlist={!r} total={}',
            playlist_name,
            total,
        )
        return PlaylistSyncResult(
            '', playlist_name, 0, total, scanned, scan_complete
        )

    existing_ids = client.find_playlist_ids_by_name(playlist_name)
    try:
        if existing_ids:
            playlist_id = existing_ids[0]
            for duplicate_id in existing_ids[1:]:
                try:
                    client.delete_playlist(duplicate_id)
                    logger.info(
                        'navidrome: removed duplicate playlist id={} name={!r}',
                        duplicate_id,
                        playlist_name,
                    )
                except Exception as exc:
                    logger.info(
                        'navidrome: could not remove duplicate playlist id={} err={}',
                        duplicate_id,
                        exc,
                    )
            playlist_id = client.replace_playlist(
                playlist_id, playlist_name, song_ids
            )
            logger.info(
                'navidrome: updated existing playlist id={} name={!r}',
                playlist_id,
                playlist_name,
            )
        else:
            playlist_id = client.create_playlist(playlist_name, song_ids)
            logger.info(
                'navidrome: created playlist id={} name={!r}',
                playlist_id,
                playlist_name,
            )
        client.update_playlist_meta(
            playlist_id,
            comment=comment,
            public=bool(cfg.get('public_playlist')),
        )
    except Exception as exc:
        logger.info(
            'navidrome: playlist create failed name={!r} matched={}/{} err={}',
            playlist_name,
            matched,
            total,
            exc,
        )
        return PlaylistSyncResult(
            '', playlist_name, matched, total, scanned, scan_complete
        )

    logger.info(
        'navidrome: playlist synced name={!r} id={} matched={}/{} scan_complete={}',
        playlist_name,
        playlist_id,
        matched,
        total,
        scan_complete,
    )
    return PlaylistSyncResult(
        playlist_id, playlist_name, matched, total, scanned, scan_complete
    )
