"""Reading an image's pixel size from its header bytes."""

from __future__ import annotations

import struct

from downtify.image_size import image_dimensions, image_short_side


def _png(width: int, height: int) -> bytes:
    return (
        b'\x89PNG\r\n\x1a\n'
        + struct.pack('>I', 13)
        + b'IHDR'
        + struct.pack('>II', width, height)
        + b'\x08\x06\x00\x00\x00'
    )


def _jpeg(width: int, height: int) -> bytes:
    app0 = b'\xff\xe0' + struct.pack('>H', 16) + b'JFIF\x00' + b'\x00' * 9
    sof0 = (
        b'\xff\xc0'
        + struct.pack('>H', 17)
        + b'\x08'
        + struct.pack('>HH', height, width)
        + b'\x03' * 10
    )
    return b'\xff\xd8' + app0 + sof0 + b'\xff\xda' + b'\x00' * 32


def _gif(width: int, height: int) -> bytes:
    return b'GIF89a' + struct.pack('<HH', width, height) + b'\x00' * 8


def _webp_vp8x(width: int, height: int) -> bytes:
    body = (
        b'VP8X'
        + struct.pack('<I', 10)
        + b'\x00\x00\x00\x00'
        + (width - 1).to_bytes(3, 'little')
        + (height - 1).to_bytes(3, 'little')
    )
    return b'RIFF' + struct.pack('<I', len(body) + 4) + b'WEBP' + body


def test_png_dimensions() -> None:
    assert image_dimensions(_png(1200, 1200)) == (1200, 1200)


def test_jpeg_dimensions_from_start_of_frame() -> None:
    assert image_dimensions(_jpeg(640, 640)) == (640, 640)


def test_jpeg_skips_application_segments() -> None:
    # The size lives behind a JFIF segment, so a parser that reads a
    # fixed offset instead of walking the chain gets this wrong.
    assert image_dimensions(_jpeg(300, 200)) == (300, 200)


def test_gif_dimensions_are_little_endian() -> None:
    assert image_dimensions(_gif(500, 400)) == (500, 400)


def test_webp_extended_dimensions_are_stored_minus_one() -> None:
    assert image_dimensions(_webp_vp8x(1400, 1400)) == (1400, 1400)


def test_unknown_and_truncated_data_has_no_size() -> None:
    assert image_dimensions(b'') is None
    assert image_dimensions(None) is None
    assert image_dimensions(b'not an image at all') is None
    assert image_dimensions(_png(800, 800)[:20]) is None


def test_jpeg_without_a_frame_header_has_no_size() -> None:
    # Only a scan marker: nothing declares the size.
    assert image_dimensions(b'\xff\xd8\xff\xda' + b'\x00' * 40) is None


def test_short_side_is_the_smaller_dimension() -> None:
    assert image_short_side(_png(1200, 600)) == 600
    assert image_short_side(_png(300, 300)) == 300
    assert image_short_side(b'junk') == 0
