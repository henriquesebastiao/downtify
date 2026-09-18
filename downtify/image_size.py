"""Read an image's pixel size from its header bytes.

The library upgrade needs to know how big a cover already is before it
decides to replace it, and it asks that question once per track across a
whole library — so it reads the few header bytes that carry the size
instead of decoding the image. JPEG, PNG, WebP and GIF cover every cover
Downtify writes or finds.
"""

from __future__ import annotations

import struct
from typing import Optional

#: Start-of-frame markers that carry the size. SOF4/SOF8/SOF12 (0xC4,
#: 0xC8, 0xCC) are Huffman/arithmetic tables, not frames.
_JPEG_SOF = frozenset({
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
})

Size = tuple[int, int]


def _png_size(data: bytes) -> Optional[Size]:
    if len(data) < 24 or data[12:16] != b'IHDR':
        return None
    width, height = struct.unpack('>II', data[16:24])
    return (width, height)


def _gif_size(data: bytes) -> Optional[Size]:
    if len(data) < 10:
        return None
    width, height = struct.unpack('<HH', data[6:10])
    return (width, height)


def _jpeg_size(data: bytes) -> Optional[Size]:
    # Walk the segment chain: 0xFF, marker, 2-byte length, payload.
    pos = 2
    end = len(data)
    while pos + 9 < end:
        if data[pos] != 0xFF:
            # Skip fill bytes; anything else means the chain is broken.
            pos += 1
            continue
        marker = data[pos + 1]
        pos += 2
        if marker in {0xD8, 0x01} or 0xD0 <= marker <= 0xD7:
            continue
        if marker == 0xDA:  # start of scan: no size past this point
            return None
        (length,) = struct.unpack('>H', data[pos : pos + 2])
        if length < 2:
            return None
        if marker in _JPEG_SOF:
            height, width = struct.unpack('>HH', data[pos + 3 : pos + 7])
            return (width, height)
        pos += length
    return None


def _webp_size(data: bytes) -> Optional[Size]:
    if len(data) < 30:
        return None
    chunk = data[12:16]
    if chunk == b'VP8 ':
        if data[23:26] != b'\x9d\x01\x2a':
            return None
        width, height = struct.unpack('<HH', data[26:30])
        return (width & 0x3FFF, height & 0x3FFF)
    if chunk == b'VP8L':
        if data[20] != 0x2F:
            return None
        (bits,) = struct.unpack('<I', data[21:25])
        return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    if chunk == b'VP8X':
        # 24-bit little-endian, stored as size - 1.
        width = int.from_bytes(data[24:27], 'little') + 1
        height = int.from_bytes(data[27:30], 'little') + 1
        return (width, height)
    return None


def image_dimensions(data: Optional[bytes]) -> Optional[Size]:
    """Return ``(width, height)`` for *data*, or ``None`` if unreadable."""

    if not data or len(data) < 10:
        return None
    try:
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            size = _png_size(data)
        elif data[:3] == b'\xff\xd8\xff':
            size = _jpeg_size(data)
        elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            size = _webp_size(data)
        elif data[:6] in {b'GIF87a', b'GIF89a'}:
            size = _gif_size(data)
        else:
            return None
    except (struct.error, IndexError):
        return None
    if size is None or size[0] <= 0 or size[1] <= 0:
        return None
    return size


def image_short_side(data: Optional[bytes]) -> int:
    """The smaller of the two sides, or ``0`` when the size is unknown.

    Covers are square in practice; using the short side keeps a wide
    banner from counting as high-resolution art.
    """

    size = image_dimensions(data)
    return min(size) if size else 0
