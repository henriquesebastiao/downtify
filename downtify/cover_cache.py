"""Optional on-disk cache for embedded cover art (``/cover`` endpoint)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .cover_art import extract_cover_art
from .library_cache_keys import file_content_key
from .library_paths import locate_library_file


def _norm_filename(filename: str) -> str:
    return str(filename or '').strip().replace('\\', '/')


class CoverArtCache:
    """Stores cover bytes under *cache_dir* when enabled in settings."""

    def __init__(self, cache_dir: Path) -> None:
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _paths(self, key: str) -> tuple[Path, Path]:
        return self._dir / f'{key}.meta', self._dir / f'{key}.bin'

    def lookup(
        self, stored_path: str, full_path: Path
    ) -> Optional[tuple[bytes, str]]:
        name = _norm_filename(stored_path)
        if not name or not full_path.is_file():
            return None
        try:
            mtime_ns, size = self._file_stat(full_path)
        except OSError:
            return None

        ck = file_content_key(full_path)
        if not ck:
            return None
        meta_path, data_path = self._paths(ck)
        if not meta_path.is_file() or not data_path.is_file():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return None
        if (
            int(meta.get('file_mtime_ns') or 0) != mtime_ns
            or int(meta.get('file_size') or 0) != size
        ):
            return None
        try:
            data = data_path.read_bytes()
        except OSError:
            return None
        if not data:
            return None
        mime = str(meta.get('mime') or 'image/jpeg')
        return data, mime

    def store(
        self,
        stored_path: str,
        full_path: Path,
        data: bytes,
        mime: str,
    ) -> None:
        name = _norm_filename(stored_path)
        if not name or not data:
            return
        try:
            mtime_ns, size = self._file_stat(full_path)
        except OSError:
            return
        ck = file_content_key(full_path)
        if not ck:
            return
        meta_path, data_path = self._paths(ck)
        meta: dict[str, Any] = {
            'filename': name,
            'content_key': ck,
            'file_mtime_ns': mtime_ns,
            'file_size': size,
            'mime': mime or 'image/jpeg',
        }
        try:
            data_path.write_bytes(data)
            meta_path.write_text(
                json.dumps(meta, separators=(',', ':')),
                encoding='utf-8',
            )
        except OSError:
            return

    def refresh(self, stored_path: str, full_path: Path) -> None:
        data, mime = extract_cover_art(full_path)
        if data:
            self.store(stored_path, full_path, data, mime or 'image/jpeg')
        else:
            self.forget(stored_path, full_path=full_path)

    def refresh_stored_path(
        self,
        stored_path: str,
        *,
        download_dir: Path,
        slskd_dir: Optional[Path] = None,
    ) -> None:
        full = locate_library_file(stored_path, download_dir, slskd_dir)
        if full is not None:
            self.refresh(stored_path, full)
        else:
            self.forget_by_stored_path(stored_path)

    def forget_by_stored_path(self, stored_path: str) -> None:
        name = _norm_filename(stored_path)
        if not name:
            return
        for meta_file in self._dir.glob('*.meta'):
            try:
                meta = json.loads(meta_file.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                continue
            if str(meta.get('filename') or '') != name:
                continue
            ck = str(meta.get('content_key') or '')
            if not ck:
                continue
            meta_path, data_path = self._paths(ck)
            for path in (meta_path, data_path):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

    def forget(
        self,
        filename: str,
        *,
        full_path: Optional[Path] = None,
    ) -> None:
        if full_path is None:
            return
        ck = file_content_key(full_path)
        if not ck:
            return
        meta_path, data_path = self._paths(ck)
        for path in (meta_path, data_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _file_stat(full_path: Path) -> tuple[int, int]:
        st = full_path.stat()
        return int(st.st_mtime_ns), int(st.st_size)
