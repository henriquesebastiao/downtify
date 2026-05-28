"""slskd provider integration for track search and download handoff."""

from __future__ import annotations

import re
import shutil
import threading
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable, Optional

ProgressCallback = Callable[[float, str], None]
from urllib.parse import quote

import requests
from loguru import logger

_SLSKD_SEM: Optional[threading.Semaphore] = None
_SLSKD_SEM_LIMIT = 0


def _slskd_parallel_limit(settings: dict[str, Any]) -> int:
    return _int_setting(
        settings,
        'max_parallel_downloads',
        3,
        minimum=1,
        maximum=8,
    )


def _slskd_semaphore(settings: dict[str, Any]) -> threading.Semaphore:
    """Match Downtify parallel download setting; do not serialize all slskd work."""
    global _SLSKD_SEM, _SLSKD_SEM_LIMIT
    limit = _slskd_parallel_limit(settings)
    if _SLSKD_SEM is None or _SLSKD_SEM_LIMIT != limit:
        _SLSKD_SEM = threading.Semaphore(limit)
        _SLSKD_SEM_LIMIT = limit
    return _SLSKD_SEM

_DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 600
_DEFAULT_QUEUED_TIMEOUT_SECONDS = 180


def _int_setting(
    settings: dict[str, Any],
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(settings.get(key) or default)
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


def _slskd_deadline(settings: dict[str, Any]) -> float:
    seconds = _int_setting(
        settings,
        'download_timeout_seconds',
        _DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
        minimum=30,
        maximum=3600,
    )
    return time.monotonic() + seconds


def _past_deadline(deadline: float) -> bool:
    return time.monotonic() >= deadline

_AUDIO_EXTENSIONS = frozenset({'mp3', 'flac', 'm4a', 'ogg', 'opus'})
_FILTER_KEYWORDS = (
    'live',
    'remix',
    'instrumental',
    'extended',
    'clean',
    'acapella',
    'karaoke',
)


class SlskdClient:
    def __init__(self, settings: dict[str, Any]):
        self.base_url = str(settings.get('base_url') or '').strip().rstrip('/')
        self.api_key = str(settings.get('api_key') or '').strip()
        self.timeout = int(settings.get('timeout_seconds') or 20)
        self.search_retries = int(settings.get('search_retries') or 5)
        self.search_poll_seconds = int(settings.get('search_poll_seconds') or 15)
        self.download_attempts = int(settings.get('download_attempts') or 3)
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({'X-API-Key': self.api_key})

    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def can_connect(self) -> bool:
        for ep in (
            '/api/v0/application',
            '/api/v0/options',
            '/api/v0/transfers/downloads',
        ):
            try:
                self._request('GET', ep)
                return True
            except Exception:
                continue
        return False

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Any] = None,
    ) -> Any:
        url = f'{self.base_url}{path}'
        kwargs: dict[str, Any] = {'timeout': self.timeout}
        if json_body is not None:
            kwargs['json'] = json_body
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        if not resp.content:
            return {}
        return resp.json()

    def start_search(self, query: str) -> Optional[str]:
        body = {
            'searchText': query,
            'filterResponses': True,
            'minimumResponseFileCount': 1,
            'minimumPeerUploadSpeed': 1,
        }
        try:
            data = self._request('POST', '/api/v0/searches', json_body=body)
        except Exception as exc:
            logger.info('slskd: search POST failed q={!r} err={}', query[:120], exc)
            return None
        if isinstance(data, dict):
            for key in ('id', 'searchId'):
                raw = data.get(key)
                if isinstance(raw, (int, str)) and str(raw).strip():
                    return str(raw).strip()
        return None

    def wait_search_complete(
        self,
        search_id: str,
        label: str,
        *,
        on_poll: Optional[Callable[[float], None]] = None,
        deadline: Optional[float] = None,
    ) -> bool:
        max_attempts = max(1, self.search_retries)
        for attempt in range(max_attempts):
            if deadline is not None and _past_deadline(deadline):
                return False
            if on_poll is not None:
                try:
                    on_poll(5.0 + (attempt / max_attempts) * 30.0)
                except Exception:
                    logger.opt(exception=True).debug(
                        'slskd search progress callback error'
                    )
            try:
                status = self._request('GET', f'/api/v0/searches/{search_id}')
            except Exception as exc:
                logger.info(
                    'slskd: search status failed id={} err={}', search_id, exc
                )
                return False
            if not isinstance(status, dict):
                return False
            file_count = int(status.get('fileCount') or 0)
            locked = int(status.get('lockedFileCount') or 0)
            if status.get('isComplete'):
                if file_count > 0 and file_count != locked:
                    return True
                logger.info(
                    'slskd: search complete but no free files label={!r} '
                    'fileCount={} locked={}',
                    label[:120],
                    file_count,
                    locked,
                )
                return False
            if attempt + 1 < self.search_retries:
                time.sleep(max(1, self.search_poll_seconds))
        logger.info(
            'slskd: search timed out label={!r} retries={}',
            label[:120],
            self.search_retries,
        )
        return False

    def search_responses(self, search_id: str) -> list[dict[str, Any]]:
        try:
            data = self._request('GET', f'/api/v0/searches/{search_id}/responses')
        except Exception:
            return []
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        return []

    def delete_search(self, search_id: str) -> None:
        try:
            self._request('DELETE', f'/api/v0/searches/{search_id}')
        except Exception:
            pass

    def enqueue_download(self, row: dict[str, Any]) -> bool:
        username = str(
            row.get('username') or row.get('userName') or row.get('user') or ''
        ).strip()
        filename = str(
            row.get('filename')
            or row.get('fileName')
            or row.get('path')
            or row.get('fullPath')
            or ''
        ).strip()
        if not username or not filename:
            return False
        try:
            size = int(row.get('size') or 0)
        except (TypeError, ValueError):
            size = 0
        endpoint = f'/api/v0/transfers/downloads/{quote(username)}'
        body = [{'filename': filename, 'size': max(0, size)}]
        try:
            self._request('POST', endpoint, json_body=body)
            return True
        except Exception as exc:
            logger.info(
                'slskd: enqueue failed user={!r} file={!r} err={}',
                username,
                filename[:120],
                exc,
            )
            return False

    def list_download_transfers(self) -> list[dict[str, Any]]:
        try:
            data = self._request('GET', '/api/v0/transfers/downloads')
        except Exception:
            return []
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        return []

    def find_transfer(
        self, username: str, filename: str
    ) -> Optional[dict[str, Any]]:
        for peer_filter in (username, ''):
            for peer in self.list_download_transfers():
                if peer_filter and str(peer.get('username') or '') != peer_filter:
                    continue
                for directory in peer.get('directories') or []:
                    if not isinstance(directory, dict):
                        continue
                    for file_row in directory.get('files') or []:
                        if not isinstance(file_row, dict):
                            continue
                        name = str(
                            file_row.get('filename')
                            or file_row.get('fileName')
                            or ''
                        )
                        if _paths_match(name, filename):
                            return file_row
        return None

    def remote_download_directories(self) -> list[str]:
        """Best-effort read of slskd's configured download/incomplete dirs."""
        for endpoint in ('/api/v0/options', '/api/v0/application'):
            try:
                data = self._request('GET', endpoint)
            except Exception:
                continue
            paths = _extract_directory_paths(data)
            if paths:
                return paths
        return []


def _flatten_slskd_responses(data: Any) -> list[dict[str, Any]]:
    responses = data if isinstance(data, list) else []
    rows: list[dict[str, Any]] = []
    for resp in responses:
        if not isinstance(resp, dict):
            continue
        username = str(
            resp.get('username') or resp.get('userName') or resp.get('user') or ''
        ).strip()
        for file_row in resp.get('files') or []:
            if not isinstance(file_row, dict):
                continue
            filename = str(
                file_row.get('filename')
                or file_row.get('fileName')
                or file_row.get('path')
                or ''
            ).strip()
            if not filename:
                continue
            rows.append({**file_row, 'username': username})
    return rows


def _normalize_search_text(text: str) -> str:
    folded = unicodedata.normalize('NFKC', text)
    folded = re.sub(r"[''`\u2019]", '', folded)
    return re.sub(r'\s+', ' ', folded).strip()


def _alnum_only(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', _normalize_search_text(text).casefold())


def _primary_title(title: str) -> str:
    text = str(title or '').strip()
    if ' - ' in text:
        return text.split(' - ', 1)[0].strip()
    return text


def _slskd_search_queries(song: dict[str, Any]) -> list[str]:
    artists = [
        str(a).strip() for a in (song.get('artists') or [])[:2] if str(a).strip()
    ]
    artist = artists[0] if artists else ''
    title = str(song.get('name') or '').strip()
    short_title = _primary_title(title)
    queries: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        normalized = _normalize_search_text(q)
        if normalized and normalized not in seen:
            seen.add(normalized)
            queries.append(normalized)

    # Explo uses "title - artist"
    if short_title and artist:
        add(f'{short_title} - {artist}')
    if title and artist and title != short_title:
        add(f'{title} - {artist}')
    if short_title:
        add(short_title)
    if artist and title:
        add(f'{artist} {title}')
    return queries


def _file_extension(filename: str) -> str:
    ext = Path(filename.replace('\\', '/')).suffix.lower().lstrip('.')
    return re.sub(r'[^a-z0-9]+', '', ext)


def _contains_keyword(song: dict[str, Any], filename: str) -> bool:
    title = str(song.get('name') or '').casefold()
    artist = ' '.join(str(a) for a in (song.get('artists') or [])).casefold()
    content = filename.casefold()
    for keyword in _FILTER_KEYWORDS:
        if keyword in title or keyword in artist:
            continue
        if keyword in content:
            return True
    return False


def _parse_duration_seconds(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value or '').strip()
    if not text:
        return 0
    if text.isdigit():
        return int(text)
    parts = text.split(':')
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return 0
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return 0


def _response_has_free_slot(resp: dict[str, Any]) -> bool:
    return resp.get('hasFreeUploadSlot') is True


def _file_is_locked(file_row: dict[str, Any]) -> bool:
    if file_row.get('isLocked') is True:
        return True
    if file_row.get('IsLocked') is True:
        return True
    return False


def _locked_filenames(resp: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for file_row in resp.get('lockedFiles') or []:
        if not isinstance(file_row, dict):
            continue
        filename = str(
            file_row.get('filename')
            or file_row.get('fileName')
            or file_row.get('path')
            or ''
        ).strip()
        if filename:
            names.add(filename.casefold())
    return names


def _filter_slskd_responses(
    responses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Drop peers without a free upload slot (slskd UI: hide no free slots)."""
    return [r for r in responses if _response_has_free_slot(r)]


def _collect_matching_files(
    song: dict[str, Any], responses: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    artist = _alnum_only(
        ' '.join(str(a) for a in (song.get('artists') or [])[:1])
    )
    album = _alnum_only(str(song.get('album_name') or ''))
    title = _alnum_only(_primary_title(str(song.get('name') or '')))
    target_duration = int(song.get('duration') or 0)
    if target_duration > 1000:
        target_duration = target_duration // 1000
    matches: list[dict[str, Any]] = []

    for resp in _filter_slskd_responses(responses):
        if int(resp.get('fileCount') or 0) <= 0:
            continue
        username = str(resp.get('username') or '').strip()
        locked_names = _locked_filenames(resp)
        for file_row in resp.get('files') or []:
            if not isinstance(file_row, dict):
                continue
            if _file_is_locked(file_row):
                continue
            filename = str(
                file_row.get('filename')
                or file_row.get('fileName')
                or file_row.get('path')
                or ''
            ).strip()
            if not filename:
                continue
            if filename.casefold() in locked_names:
                continue
            ext = _file_extension(filename)
            if ext and ext not in _AUDIO_EXTENSIONS:
                continue
            if _contains_keyword(song, filename):
                continue
            length = _parse_duration_seconds(
                file_row.get('length') or file_row.get('duration')
            )
            if target_duration and length and abs(target_duration - length) > 10:
                continue
            sanitized_name = _alnum_only(filename)
            if not (
                (artist and artist in sanitized_name)
                or (album and album in sanitized_name)
            ):
                continue
            if title and title not in sanitized_name:
                continue
            matches.append({**file_row, 'username': username, 'filename': filename})
    return matches


def _filter_by_quality(
    files: list[dict[str, Any]], settings: dict[str, Any]
) -> list[dict[str, Any]]:
    raw_ext = settings.get('extensions') or ['mp3', 'flac']
    extensions = [
        str(e).strip().lower().lstrip('.')
        for e in raw_ext
        if str(e).strip()
    ] or ['mp3', 'flac']
    min_bitrate = int(settings.get('min_bitrate') or 0)
    max_files = int(settings.get('download_attempts') or 3)
    filtered: list[dict[str, Any]] = []
    for ext in extensions:
        for file_row in files:
            if _file_extension(str(file_row.get('filename') or '')) != ext:
                continue
            try:
                bitrate = int(file_row.get('bitRate') or file_row.get('bitrate') or 0)
            except (TypeError, ValueError):
                bitrate = 0
            if min_bitrate and bitrate and bitrate < min_bitrate:
                continue
            filtered.append(file_row)
            if len(filtered) >= max_files:
                return filtered
    return filtered


def _file_basename(filename: str) -> str:
    return Path(str(filename or '').replace('\\', '/')).name


def _paths_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    return _file_basename(left).casefold() == _file_basename(right).casefold()


def _extract_directory_paths(data: Any) -> list[str]:
    paths: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            directories = node.get('directories')
            if isinstance(directories, dict):
                for key in ('downloads', 'incomplete', 'download'):
                    raw = directories.get(key)
                    if isinstance(raw, str) and raw.strip():
                        paths.append(raw.strip())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    out: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        if raw not in seen:
            seen.add(raw)
            out.append(raw)
    return out


def _search_roots(
    settings: dict[str, Any], client: SlskdClient
) -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()
    for raw in (
        settings.get('source_dir'),
        settings.get('output_dir'),
        settings.get('download_dir'),
        *client.remote_download_directories(),
    ):
        text = str(raw or '').strip()
        if not text or text in seen:
            continue
        seen.add(text)
        roots.append(Path(text))
    return roots


def _parse_soulseek_path(filename: str) -> tuple[str, str]:
    normalized = filename.replace('\\', '/')
    parent = Path(normalized).parent
    parent_name = '' if str(parent) in ('.', '/') else parent.name
    return Path(normalized).name, parent_name


def _transfer_failed(status: dict[str, Any]) -> bool:
    state = str(status.get('state') or '')
    return 'Errored' in state or 'Cancelled' in state or 'Aborted' in state


def _transfer_succeeded(status: dict[str, Any]) -> bool:
    state = str(status.get('state') or '')
    remaining = int(status.get('bytesRemaining') or 0)
    percent = float(status.get('percentComplete') or 0)
    return (
        remaining == 0
        or percent >= 100
        or 'Succeeded' in state
        or 'Completed' in state
    )


def _slskd_transfer_progress_pct(
    *,
    transfer: Optional[dict[str, Any]] = None,
    on_disk_bytes: int = 0,
    expected_size: int = 0,
    poll_attempt: int = 0,
) -> tuple[float, str]:
    """Map an active slskd transfer to overall job progress (40–92%)."""

    lo, hi = 40.0, 92.0
    span = hi - lo
    if transfer:
        try:
            pct_complete = float(transfer.get('percentComplete') or 0)
        except (TypeError, ValueError):
            pct_complete = 0.0
        if 0 < pct_complete <= 100:
            return lo + span * (pct_complete / 100.0), 'Downloading'
        try:
            transferred = int(transfer.get('bytesTransferred') or 0)
            size = int(transfer.get('size') or 0) or int(expected_size or 0)
        except (TypeError, ValueError):
            transferred = 0
            size = 0
        if size > 0 and transferred >= 0:
            ratio = min(1.0, transferred / size)
            return lo + span * ratio, 'Downloading'
    if expected_size > 0 and on_disk_bytes > 0:
        ratio = min(1.0, on_disk_bytes / expected_size)
        return lo + span * ratio, 'Downloading'
    fallback = lo + min(span * 0.12, max(0, poll_attempt) * 0.4)
    return min(hi - 4.0, fallback), 'Waiting for slskd'


def _normalize_token(text: str) -> str:
    folded = unicodedata.normalize('NFKD', text)
    stripped = ''.join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', stripped).casefold().strip()


def _disk_complete(path: Path, expected_size: int) -> bool:
    try:
        size = path.stat().st_size
    except OSError:
        return False
    if expected_size > 0:
        return size >= int(expected_size * 0.95)
    return size > 50_000


def _find_on_disk(
    roots: list[Path],
    soulseek_filename: str,
    *,
    username: str = '',
    min_size: int = 1,
) -> Optional[Path]:
    basename, parent = _parse_soulseek_path(soulseek_filename)
    if not basename:
        return None
    relative_candidates: list[Path] = [Path(basename)]
    if parent:
        relative_candidates.append(Path(parent) / basename)
    if username:
        relative_candidates.append(Path(username) / basename)
        if parent:
            relative_candidates.append(Path(username) / parent / basename)

    for root in roots:
        if not root.exists():
            continue
        for rel in relative_candidates:
            candidate = root / rel
            if candidate.is_file() and candidate.stat().st_size >= min_size:
                return candidate

    best: Optional[Path] = None
    best_mtime = 0.0
    for root in roots:
        if not root.exists():
            continue
        try:
            matches = list(root.rglob(basename))
        except OSError:
            continue
        for candidate in matches:
            if not candidate.is_file():
                continue
            try:
                size = candidate.stat().st_size
                mtime = candidate.stat().st_mtime
            except OSError:
                continue
            if size < min_size:
                continue
            if mtime >= best_mtime:
                best = candidate
                best_mtime = mtime
    return best


def _find_on_disk_for_song(
    roots: list[Path],
    song: dict[str, Any],
    soulseek_filename: str,
    *,
    username: str = '',
    expected_size: int = 0,
    extensions: Optional[frozenset[str]] = None,
) -> Optional[Path]:
    min_size = max(1, int(expected_size * 0.95) if expected_size else 1)
    found = _find_on_disk(
        roots,
        soulseek_filename,
        username=username,
        min_size=min_size,
    )
    if found is not None:
        return found

    title = _normalize_token(str(song.get('name') or ''))
    if len(title) < 3:
        return None
    exts = extensions or _AUDIO_EXTENSIONS
    best: Optional[Path] = None
    best_mtime = 0.0
    for root in roots:
        if not root.exists():
            continue
        for ext in exts:
            pattern = ext if ext.startswith('.') else f'.{ext}'
            try:
                matches = list(root.rglob(f'*{pattern}'))
            except OSError:
                continue
            for candidate in matches:
                if not candidate.is_file():
                    continue
                if title not in _normalize_token(candidate.name):
                    continue
                try:
                    size = candidate.stat().st_size
                    mtime = candidate.stat().st_mtime
                except OSError:
                    continue
                if size < min_size:
                    continue
                if mtime >= best_mtime:
                    best = candidate
                    best_mtime = mtime
    return best


def _copy_to_output(src: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / src.name
    if dest.resolve() != src.resolve():
        shutil.copy2(src, dest)
    return dest


def _resolve_downloaded_file(
    roots: list[Path],
    output_dir: Path,
    song: dict[str, Any],
    soulseek_filename: str,
    *,
    username: str,
    leave_in_place: bool,
    expected_size: int = 0,
) -> Optional[Path]:
    found = _find_on_disk_for_song(
        roots,
        song,
        soulseek_filename,
        username=username,
        expected_size=expected_size,
    )
    if found is None:
        return None
    if leave_in_place:
        return found
    return _copy_to_output(found, output_dir)


def _finalize_slskd_path(found: Path, output_dir: Path, leave_in_place: bool) -> Path:
    if leave_in_place:
        return found
    return _copy_to_output(found, output_dir)


def _wait_for_slskd_file(
    client: SlskdClient,
    song: dict[str, Any],
    username: str,
    filename: str,
    settings: dict[str, Any],
    roots: list[Path],
    *,
    expected_size: int = 0,
    progress_cb: Optional[ProgressCallback] = None,
    deadline: Optional[float] = None,
) -> Optional[Path]:
    """Wait for slskd to finish, then return the file path on disk (if found)."""
    interval = _int_setting(
        settings, 'poll_interval_seconds', 5, minimum=1, maximum=30
    )
    attempts = _int_setting(
        settings, 'poll_max_attempts', 60, minimum=1, maximum=300
    )
    queued_timeout = _int_setting(
        settings,
        'queued_timeout_seconds',
        _DEFAULT_QUEUED_TIMEOUT_SECONDS,
        minimum=15,
        maximum=3600,
    )
    wait_started = time.monotonic()
    last_bytes = -1
    last_progress = wait_started
    last_reported_pct = -1.0

    for attempt in range(max(1, attempts)):
        if deadline is not None and _past_deadline(deadline):
            logger.info(
                'slskd: download timeout while waiting for file title={!r} '
                'user={!r} file={!r}',
                song.get('name'),
                username,
                _file_basename(filename)[:120],
            )
            return None
        found = _find_on_disk_for_song(
            roots,
            song,
            filename,
            username=username,
            expected_size=expected_size,
        )
        on_disk_bytes = 0
        if found is not None:
            try:
                on_disk_bytes = found.stat().st_size
            except OSError:
                on_disk_bytes = 0
            if _disk_complete(found, expected_size):
                if progress_cb is not None:
                    progress_cb(92.0, 'Downloading')
                return found

        transfer = client.find_transfer(username, filename)
        if transfer:
            try:
                expected_size = max(
                    expected_size, int(transfer.get('size') or 0)
                )
            except (TypeError, ValueError):
                pass
            if _transfer_failed(transfer):
                return None
            transferred = int(transfer.get('bytesTransferred') or 0)
            if transferred > last_bytes:
                last_bytes = transferred
                last_progress = time.monotonic()
            elif time.monotonic() - last_progress > queued_timeout:
                logger.info(
                    'slskd: stalled (no progress) title={!r} user={!r} '
                    'bytes={} state={!r}',
                    song.get('name'),
                    username,
                    transferred,
                    transfer.get('state'),
                )
                return None
        elif time.monotonic() - wait_started > queued_timeout:
            logger.info(
                'slskd: queued timeout (transfer not started) title={!r} '
                'user={!r} file={!r}',
                song.get('name'),
                username,
                _file_basename(filename)[:120],
            )
            return None

        if progress_cb is not None:
            pct, message = _slskd_transfer_progress_pct(
                transfer=transfer,
                on_disk_bytes=on_disk_bytes,
                expected_size=expected_size,
                poll_attempt=attempt,
            )
            if pct > last_reported_pct or attempt == 0:
                last_reported_pct = pct
                progress_cb(pct, message)

        time.sleep(max(1, interval))

    return _find_on_disk_for_song(
        roots,
        song,
        filename,
        username=username,
        expected_size=expected_size,
    )


def download_from_slskd(
    song: dict[str, Any],
    settings: dict[str, Any],
    progress_cb: Optional[ProgressCallback] = None,
) -> Optional[Path]:
    if not bool(settings.get('enabled')):
        return None
    client = SlskdClient(settings)
    if not client.configured():
        logger.info('slskd: missing configuration title={!r}', song.get('name'))
        return None
    if not client.can_connect():
        logger.info('slskd: connectivity check failed base_url={!r}', client.base_url)
        return None

    output_dir = Path(str(settings.get('output_dir') or settings.get('download_dir') or '/downloads'))
    source_dir = Path(
        str(settings.get('source_dir') or settings.get('download_dir') or output_dir)
    )
    leave_in_place = bool(settings.get('leave_in_place', True))
    queries = _slskd_search_queries(song)
    if not queries:
        return None

    label = f"{song.get('name')} - {', '.join(song.get('artists') or [])}"

    def report(pct: float, message: str) -> None:
        if progress_cb is not None:
            try:
                progress_cb(pct, message)
            except Exception:
                logger.opt(exception=True).debug('slskd progress callback error')

    deadline = _slskd_deadline(settings)
    report(2.0, 'Searching slskd')

    search_id = ''
    queued: Optional[dict[str, Any]] = None

    # Search + enqueue only: allow N in parallel; do not hold the slot while
    # waiting minutes for the Soulseek transfer on disk.
    with _slskd_semaphore(settings):
        responses: list[dict[str, Any]] = []
        used_query = ''
        for query in queries:
            if _past_deadline(deadline):
                logger.info(
                    'slskd: download timeout during search title={!r}',
                    song.get('name'),
                )
                return None
            report(8.0, 'Searching slskd')
            search_id = client.start_search(query) or ''
            if not search_id:
                continue
            if not client.wait_search_complete(
                search_id,
                label,
                on_poll=lambda pct: report(pct, 'Searching slskd'),
                deadline=deadline,
            ):
                client.delete_search(search_id)
                search_id = ''
                continue
            raw_responses = client.search_responses(search_id)
            responses = _filter_slskd_responses(raw_responses)
            if responses:
                used_query = query
                break
            client.delete_search(search_id)
            search_id = ''

        if not responses:
            logger.info(
                'slskd: no results title={!r} queries={}',
                song.get('name'),
                queries[:6],
            )
            if search_id:
                client.delete_search(search_id)
            return None

        candidates = _collect_matching_files(song, responses)
        if not candidates:
            logger.info(
                'slskd: no matching audio files title={!r} q={!r} responses={}',
                song.get('name'),
                used_query[:120],
                len(responses),
            )
            client.delete_search(search_id)
            return None

        files = _filter_by_quality(candidates, settings)
        if not files:
            logger.info(
                'slskd: no files passed quality filters title={!r}',
                song.get('name'),
            )
            client.delete_search(search_id)
            return None

        for file_row in files:
            if client.enqueue_download(file_row):
                queued = file_row
                break

        if queued is None:
            logger.info('slskd: failed to enqueue title={!r}', song.get('name'))
            client.delete_search(search_id)
            return None

        if _past_deadline(deadline):
            client.delete_search(search_id)
            logger.info(
                'slskd: download timeout before transfer title={!r}',
                song.get('name'),
            )
            return None

    report(36.0, 'Queued on slskd')
    username = str(queued.get('username') or '')
    filename = str(queued.get('filename') or '')
    try:
        queued_size = int(queued.get('size') or 0)
    except (TypeError, ValueError):
        queued_size = 0
    roots = _search_roots(settings, client)

    def _root_key(path: Path) -> str:
        try:
            return str(path.resolve())
        except OSError:
            return str(path)

    root_keys = {_root_key(r) for r in roots}
    if _root_key(source_dir) not in root_keys:
        roots.insert(0, source_dir)
    if _root_key(output_dir) not in root_keys:
        roots.append(output_dir)

    found = _wait_for_slskd_file(
        client,
        song,
        username,
        filename,
        settings,
        roots,
        expected_size=queued_size,
        progress_cb=progress_cb,
        deadline=deadline,
    )
    if search_id:
        client.delete_search(search_id)

    if found is None:
        found = _resolve_downloaded_file(
            roots,
            output_dir,
            song,
            filename,
            username=username,
            leave_in_place=leave_in_place,
            expected_size=queued_size,
        )
    else:
        found = _finalize_slskd_path(found, output_dir, leave_in_place)

    if found is None:
        remote_dirs = client.remote_download_directories()
        logger.info(
            'slskd: file not found after transfer title={!r} searched={} '
            'slskd_dirs={} file={!r} user={!r}',
            song.get('name'),
            [str(p) for p in roots],
            remote_dirs,
            _file_basename(filename),
            username,
        )
    return found
