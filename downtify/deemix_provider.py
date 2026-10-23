"""Optional Deemix server audio source; credentials stay in its session."""

from __future__ import annotations

import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlsplit

import httpx
import mutagen
from loguru import logger

from .deezer import _get_json

DEFAULT_SETTINGS = {
    'enabled': False,
    'base_url': '',
    'remote_dir': '/downloads',
    'source_dir': '/deemix',
    'bitrate': '3',
    'download_timeout_seconds': 600,
}
_AUDIO = {'.mp3', '.flac', '.m4a', '.opus', '.ogg'}


class DeemixError(RuntimeError):
    """A stable, credential-free reason an integration cannot proceed."""


def normalize_settings(raw: Any) -> dict[str, Any]:
    """Normalize only known settings. Never accept a stored ARL."""
    raw = raw if isinstance(raw, dict) else {}
    cfg = {
        **DEFAULT_SETTINGS,
        **{k: v for k, v in raw.items() if k in DEFAULT_SETTINGS},
    }
    cfg['enabled'] = bool(cfg['enabled'])
    for key in ('base_url', 'remote_dir', 'source_dir'):
        cfg[key] = str(cfg[key] or '').strip().rstrip('/')
    cfg['bitrate'] = str(cfg['bitrate'])
    if cfg['bitrate'] not in {'1', '3', '9'}:
        cfg['bitrate'] = '3'
    try:
        cfg['download_timeout_seconds'] = min(
            3600, max(30, int(cfg['download_timeout_seconds']))
        )
    except (TypeError, ValueError):
        cfg['download_timeout_seconds'] = 600
    return cfg


def validate_settings(cfg: dict[str, Any]) -> None:
    """Reject embedded credentials and ambiguous path mappings."""
    try:
        url = urlsplit(cfg['base_url'])
    except ValueError:
        raise DeemixError('connection_bad_url') from None
    if (
        url.scheme not in {'http', 'https'}
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise DeemixError('connection_bad_url')
    if not all(
        Path(cfg[k]).is_absolute() for k in ('remote_dir', 'source_dir')
    ):
        raise DeemixError('folder_missing')


class DeemixClient:
    """One short-lived cookie session; no global queue mutation."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        validate_settings(cfg)
        self.cfg = cfg
        self.http = httpx.Client(
            base_url=cfg['base_url'] + '/',
            timeout=15,
            follow_redirects=False,
        )

    def close(self) -> None:
        self.http.close()

    def request(self, method: str, route: str, **kwargs: Any) -> Any:
        try:
            res = self.http.request(method, 'api/' + route, **kwargs)
            res.raise_for_status()
            return res.json()
        except (httpx.HTTPError, ValueError):
            raise DeemixError('connection_unreachable') from None

    def connect(self) -> dict[str, Any]:
        info = self.request('GET', 'connect')
        if not isinstance(info, dict) or 'autologin' not in info:
            raise DeemixError('connection_not_deemix')
        if info.get('autologin'):
            filename = os.environ.get('DOWNTIFY_DEEMIX_ARL_FILE', '')
            try:
                arl = (
                    Path(filename).read_text(encoding='utf-8').strip()
                    if filename
                    else ''
                )
            except OSError:
                raise DeemixError('auth_bad_credentials') from None
            if not arl:
                raise DeemixError('auth_bad_credentials')
            # Only read the private credential when opening a session.
            # Never expose it through settings, queue data or error messages.
            self.request('POST', 'loginArl', json={'arl': arl})
            info = self.request('GET', 'connect')
        if info.get('autologin'):
            raise DeemixError('auth_bad_credentials')
        user = info.get('currentUser') or {}
        needed = {'3': 'can_stream_hq', '9': 'can_stream_lossless'}.get(
            self.cfg['bitrate']
        )
        if needed and not user.get(needed):
            raise DeemixError('quality_unavailable')
        return info

    def local_file(self, remote: str) -> Optional[Path]:
        """Confine a queue path to the explicitly mapped shared folder."""
        remote_path = Path(remote)
        try:
            rel = remote_path.relative_to(Path(self.cfg['remote_dir']))
            root = Path(self.cfg['source_dir']).resolve(strict=True)
            path = (root / rel).resolve(strict=True)
            path.relative_to(root)
            if path.is_file() and path.suffix.lower() in _AUDIO:
                return path
        except (OSError, ValueError):
            pass
        return None


def _key(value: Any) -> str:
    text = unicodedata.normalize('NFKD', str(value or '').casefold())
    return re.sub(
        r'[^\w]+',
        '',
        ''.join(c for c in text if not unicodedata.combining(c)),
    )


def _artists(song: dict[str, Any]) -> str:
    artists = song.get('artists') or []
    if isinstance(artists, str):
        return artists.split(',')[0]
    if artists:
        first = artists[0]
        return str(first.get('name', '') if isinstance(first, dict) else first)
    return str(song.get('artist') or '')


def candidate_matches(song: dict[str, Any], row: dict[str, Any]) -> bool:
    """Exact recording metadata only; never a fuzzy title-only match."""
    if not _key(song.get('name')) or not _key(_artists(song)):
        return False
    if _key(song['name']) != _key(row.get('title')) or _key(
        _artists(song)
    ) != _key((row.get('artist') or {}).get('name')):
        return False
    album = song.get('album_name')
    if album and _key(album) != _key((row.get('album') or {}).get('title')):
        return False
    if isinstance(song.get('explicit'), bool) and (
        song['explicit'] != bool(row.get('explicit_lyrics'))
    ):
        return False
    # For catalog downloads duration is the requested recording's length.
    # A later library replacement must supply catalog metadata, not the
    # duration of an existing YouTube clip.
    duration = song.get('duration')
    return (
        not duration
        or abs(float(duration) - float(row.get('duration') or 0)) <= 3
    )


def _catalog_track(
    client: DeemixClient, song: dict[str, Any]
) -> Optional[dict]:
    ident = str(song.get('song_id') or '')
    url = str(song.get('url') or '')
    match = re.fullmatch(r'deezer-(\d+)', ident) or re.search(
        r'https://(?:www\.)?deezer\.com/(?:[a-z]{2}/)?track/(\d+)(?:$|[?/#])',
        url,
    )
    if match:
        # Existing catalog adapter avoids putting a Deemix session cookie
        # on a request to a different origin.
        row = _get_json('https://api.deezer.com/track/' + match[1])
        return row if isinstance(row, dict) and row.get('id') else None
    result = client.request(
        'GET',
        'search',
        params={
            'term': f'{_artists(song)} {song.get("name", "")}',
            'type': 'track',
            'start': 0,
            'nb': 25,
        },
    )
    rows = result.get('data', []) if isinstance(result, dict) else []
    if isinstance(rows, dict):
        rows = rows.get('data', [])
    matches = [
        row
        for row in rows
        if isinstance(row, dict) and candidate_matches(song, row)
    ]
    ids = {str(row.get('id')) for row in matches if row.get('id')}
    return matches[0] if len(ids) == 1 else None


def verified_audio(path: Path, row: dict[str, Any], bitrate: str) -> bool:
    """A queue completion alone does not prove a readable full recording."""
    try:
        audio = mutagen.File(path, easy=True)
        if audio is None or not audio.info or path.stat().st_size == 0:
            return False
        tags = audio.tags or {}
        if _key((tags.get('title') or [''])[0]) != _key(
            row.get('title')
        ) or _key((tags.get('artist') or [''])[0]) != _key(
            (row.get('artist') or {}).get('name')
        ):
            return False
        album = _key((row.get('album') or {}).get('title'))
        if album and _key((tags.get('album') or [''])[0]) != album:
            return False
        expected = float(row.get('duration') or 0)
        if expected <= 0 or abs(audio.info.length - expected) > 3:
            return False
        lossless = 'audio/flac' in (getattr(audio, 'mime', None) or [])
        if bitrate == '9':
            return lossless
        if lossless:
            return True
        minimum = 300000 if bitrate == '3' else 115000
        return getattr(audio.info, 'bitrate', 0) >= minimum
    except (OSError, ValueError, mutagen.MutagenError):
        return False


def _completed_file(
    client: DeemixClient,
    job: dict[str, Any],
    row: dict[str, Any],
    bitrate: str,
) -> Path:
    for entry in job.get('files') or []:
        remote = str(entry.get('path') or '')
        path = client.local_file(remote)
        if path is None and remote and entry.get('filename'):
            path = client.local_file(
                str(Path(remote) / str(entry['filename']))
            )
        if path and verified_audio(path, row, bitrate):
            return path
    raise DeemixError('download_file_unverified')


def download_from_deemix(
    song: dict[str, Any],
    cfg: dict[str, Any],
    progress_cb: Optional[Callable[..., None]] = None,
) -> Optional[Path]:
    """Download one matched recording; keep all Deemix files in place."""
    client: Optional[DeemixClient] = None
    try:
        client = DeemixClient(cfg)
        client.connect()
        row = _catalog_track(client, song)
        if row is None:
            return None
        ident = str(row['id'])
        uuid = f'track_{ident}_{cfg["bitrate"]}'
        result = client.request(
            'POST',
            'addToQueue',
            json={
                'url': 'https://www.deezer.com/track/' + ident,
                'bitrate': cfg['bitrate'],
            },
        )
        obj = (result.get('data') or {}).get('obj')
        if isinstance(obj, list):
            obj = obj[0] if len(obj) == 1 else None
        if isinstance(obj, dict):
            uuid = str(obj.get('uuid') or uuid)
        deadline = time.monotonic() + cfg['download_timeout_seconds']
        while time.monotonic() < deadline:
            queue = client.request('GET', 'getQueue')
            job = (queue.get('queue') or {}).get(uuid)
            if job:
                if str(job.get('id')) != ident:
                    raise DeemixError('download_identity_mismatch')
                if job.get('status') in {'completed', 'withErrors'}:
                    return _completed_file(client, job, row, cfg['bitrate'])
                if job.get('status') in {'failed', 'cancelled'}:
                    raise DeemixError('download_failed')
                if progress_cb:
                    progress_cb(
                        min(99.0, float(job.get('progress') or 0)),
                        'Downloading',
                        'deemix',
                    )
            time.sleep(2)
        raise DeemixError('download_timeout')
    except DeemixError as exc:
        logger.warning('Deemix source unavailable: {}', str(exc))
        return None
    finally:
        if client:
            client.close()


def check_deemix(cfg: dict[str, Any]) -> dict[str, Any]:
    """Test a session and read-only shared folder, without queue changes."""
    client: Optional[DeemixClient] = None
    try:
        client = DeemixClient(cfg)
        client.connect()
        if not Path(cfg['source_dir']).is_dir():
            raise DeemixError('folder_missing')
        return {
            'ok': True,
            'server': 'Deemix',
            'checks': [
                {
                    'id': 'connection',
                    'status': 'ok',
                    'code': 'ok',
                    'detail': '',
                },
                {
                    'id': 'folder',
                    'status': 'ok',
                    'code': 'ok',
                    'detail': cfg['source_dir'],
                },
            ],
        }
    except DeemixError as exc:
        ident, _, code = str(exc).partition('_')
        return {
            'ok': False,
            'server': '',
            'checks': [
                {'id': ident, 'status': 'fail', 'code': code, 'detail': ''},
            ],
        }
    finally:
        if client:
            client.close()
