"""Cover art at the sizes a client shows it: small in lists, full size in
Now Playing.

The cover is read out of the audio file's tags once (the same reader
``/cover`` uses, :func:`downtify.cover_art.extract_cover_art`) and every
size is kept on disk under ``<data>/cover_thumbs``, keyed by the file's
content key and modification time - so a re-tagged file gets new
pictures, and nothing is re-extracted or re-scaled on later requests.
Scaling uses the ffmpeg already in the image; without it (or if it
fails) the full-size picture is served for every size.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from loguru import logger

from .cover_art import extract_cover_art

#: The sizes (px, longest side) a client may ask for; ``0`` is full size.
SIZES = (150, 300, 600)


def normalize_size(value: object) -> int:
    """The smallest allowed size at or above *value*; ``0`` (full size)
    for ``full``, nothing, or anything larger than the biggest size."""

    try:
        wanted = int(str(value))
    except (TypeError, ValueError):
        return 0
    for size in SIZES:
        if wanted <= size:
            return size
    return 0


class CoverThumbs:
    """Covers by size, cached on disk."""

    def __init__(self, cache_dir: Path, ffmpeg: Optional[str] = None) -> None:
        self._dir = Path(cache_dir)
        self._ffmpeg = ffmpeg if ffmpeg is not None else shutil.which('ffmpeg')

    @staticmethod
    def _key(source: Path) -> str:
        st = source.stat()
        raw = f'{source.name}\n{st.st_size}\n{st.st_mtime_ns}'
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(
        self, source: Path, size: int = 0
    ) -> Optional[tuple[bytes, str, str]]:
        """``(image, media type, etag)`` for *source*'s cover at *size*,
        or ``None`` when the file has no cover."""

        key = self._key(source)
        full = self._full(source, key)
        if full is None:
            return None
        data, mime = full
        if not size:
            return data, mime, f'"{key[:16]}-full"'
        thumb = self._dir / f'{key}-{size}.jpg'
        if thumb.is_file():
            return thumb.read_bytes(), 'image/jpeg', f'"{key[:16]}-{size}"'
        scaled = self._scale(data, size)
        if scaled is None:
            return data, mime, f'"{key[:16]}-full"'
        self._dir.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            thumb.write_bytes(scaled)
        return scaled, 'image/jpeg', f'"{key[:16]}-{size}"'

    def _full(self, source: Path, key: str) -> Optional[tuple[bytes, str]]:
        data_path = self._dir / f'{key}-full.bin'
        meta_path = self._dir / f'{key}-full.json'
        if data_path.is_file() and meta_path.is_file():
            with contextlib.suppress(OSError, ValueError):
                mime = json.loads(meta_path.read_text())['mime']
                return data_path.read_bytes(), mime
        data, mime = extract_cover_art(source)
        if not data:
            return None
        mime = mime or 'image/jpeg'
        self._dir.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            data_path.write_bytes(data)
            meta_path.write_text(json.dumps({'mime': mime}))
        return data, mime

    def _scale(self, data: bytes, size: int) -> Optional[bytes]:
        if not self._ffmpeg:
            return None
        try:
            result = subprocess.run(
                [
                    self._ffmpeg,
                    '-nostdin',
                    '-hide_banner',
                    '-loglevel',
                    'error',
                    '-i',
                    'pipe:0',
                    '-vf',
                    f'scale={size}:{size}:force_original_aspect_ratio=decrease',
                    '-frames:v',
                    '1',
                    '-q:v',
                    '4',
                    '-f',
                    'image2',
                    '-c:v',
                    'mjpeg',
                    'pipe:1',
                ],
                input=data,
                capture_output=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            logger.opt(exception=True).debug('Cover scaling failed')
            return None
        if result.returncode != 0 or not result.stdout:
            return None
        return result.stdout
