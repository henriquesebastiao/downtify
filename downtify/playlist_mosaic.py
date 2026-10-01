"""Spotify-style collage for a user-created playlist's sidecar JPEG.

Imported playlists keep the artwork downloaded with the M3U. Manual
ones have no remote cover, so the first 1–4 distinct track covers are
composed into ``<playlist>.jpg`` beside the M3U (Navidrome, file
browsers). The SPA also mosaics from track covers in the UI.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from loguru import logger

from .cover_art import extract_cover_art
from .library_catalog import LibraryContext, resolve_library_file

MOSAIC_SIZE = 600
MAX_TILES = 4


def _ffmpeg() -> Optional[str]:
    return shutil.which('ffmpeg')


def _filter_complex(count: int) -> str:
    """ffmpeg graph: 1 cover fills the square; 2 split down the middle;
    3 is left-full + two stacked on the right; 4 is a 2×2 grid."""

    size = MOSAIC_SIZE
    half = size // 2
    crop = 'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}'
    if count <= 1:
        return f'[0:v]{crop.format(w=size, h=size)}[out]'
    if count == 2:
        cell = crop.format(w=half, h=size)
        return f'[0:v]{cell}[l];[1:v]{cell}[r];[l][r]hstack=inputs=2[out]'
    if count == 3:
        left = crop.format(w=half, h=size)
        sq = crop.format(w=half, h=half)
        return (
            f'[0:v]{left}[l];[1:v]{sq}[tr];[2:v]{sq}[br];'
            '[tr][br]vstack=inputs=2[r];[l][r]hstack=inputs=2[out]'
        )
    cell = crop.format(w=half, h=half)
    return (
        f'[0:v]{cell}[a];[1:v]{cell}[b];'
        f'[2:v]{cell}[c];[3:v]{cell}[d];'
        '[a][b]hstack=inputs=2[top];'
        '[c][d]hstack=inputs=2[bot];'
        '[top][bot]vstack=inputs=2[out]'
    )


def unique_cover_images(
    ctx: LibraryContext, files: list[str], *, limit: int = MAX_TILES
) -> list[bytes]:
    """Embedded/folder art for *files*, first distinct images in order."""

    images: list[bytes] = []
    seen: set[str] = set()
    for stored in files:
        path = resolve_library_file(stored, ctx)
        if path is None:
            continue
        data, _mime = extract_cover_art(path)
        if not data:
            continue
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        images.append(data)
        if len(images) >= limit:
            break
    return images


def _compose(images: list[bytes], dest: Path) -> bool:
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        if len(images) == 1:
            dest.write_bytes(images[0])
            return True
        return False
    with tempfile.TemporaryDirectory(prefix='downtify-mosaic-') as raw:
        tmp = Path(raw)
        inputs: list[str] = []
        for index, data in enumerate(images):
            tile = tmp / f'{index}.bin'
            tile.write_bytes(data)
            inputs.extend(['-i', str(tile)])
        out = tmp / 'out.jpg'
        cmd = [
            ffmpeg,
            '-nostdin',
            '-hide_banner',
            '-loglevel',
            'error',
            *inputs,
            '-filter_complex',
            _filter_complex(len(images)),
            '-map',
            '[out]',
            '-frames:v',
            '1',
            '-q:v',
            '4',
            '-y',
            str(out),
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=30, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            logger.opt(exception=True).debug(
                'Playlist mosaic ffmpeg failed for {}', dest
            )
            if len(images) == 1:
                dest.write_bytes(images[0])
                return True
            return False
        if (
            result.returncode != 0
            or not out.is_file()
            or not out.stat().st_size
        ):
            logger.debug(
                'Playlist mosaic ffmpeg error for {}: {}',
                dest,
                (result.stderr or b'').decode('utf-8', errors='replace')[:400],
            )
            if len(images) == 1:
                dest.write_bytes(images[0])
                return True
            return False
        dest.write_bytes(out.read_bytes())
        return True


def refresh_manual_playlist_cover(
    ctx: LibraryContext, m3u_path: Path, files: list[str]
) -> Optional[Path]:
    """Write or remove ``m3u_path``'s ``.jpg`` from the playlist's tracks."""

    dest = m3u_path.with_suffix('.jpg')
    images = unique_cover_images(ctx, files)
    if not images:
        dest.unlink(missing_ok=True)
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    if _compose(images, dest):
        return dest
    dest.unlink(missing_ok=True)
    return None
