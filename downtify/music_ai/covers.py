"""Deterministic local playlist covers: same key, same picture, no service."""

from __future__ import annotations

import hashlib

PALETTES = {
    'calme': ('#0f2a3d', '#5b8fa8'),
    'concentration': ('#1b2430', '#6b8cae'),
    'energie': ('#3a1200', '#f97316'),
    'fete': ('#2a0a2e', '#e879f9'),
    'melancolie': ('#101828', '#3b82f6'),
    'detente': ('#0b2b26', '#2dd4bf'),
    'rap': ('#1a1a1a', '#facc15'),
    'pop': ('#350b28', '#f472b6'),
    'rock': ('#2b0d0d', '#ef4444'),
    'electro': ('#0b1030', '#38bdf8'),
}
SIZE = 512


def seed_bytes(key):
    return hashlib.sha256(key.encode()).digest()


def url(cadence, mood, period):
    return (
        f'/api/v1/music-ai/playlists/{cadence}/{mood}'
        f'/cover.svg?period={period}'
    )


def svg(key, mood):
    """A geometric cover derived only from the key; no text and no external asset."""
    palette = PALETTES.get(mood, ('#111827', '#94a3b8'))
    data = seed_bytes(key)
    angle = data[0] * 360 // 256
    rings = 3 + data[1] % 3
    shapes = []
    for index in range(rings):
        offset = 3 + index * 5
        radius = 60 + (data[offset] * (SIZE // 2 - 80)) // 256
        cx = 80 + (data[offset + 1] * (SIZE - 160)) // 256
        cy = 80 + (data[offset + 2] * (SIZE - 160)) // 256
        opacity = 0.18 + (data[offset + 3] % 40) / 200
        width = 2 + data[offset + 4] % 6
        shapes.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" '
            f'stroke="{palette[1]}" stroke-width="{width}" '
            f'stroke-opacity="{opacity:.2f}"/>'
        )
    band = 40 + data[8] % 160
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" '
        f'height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}" role="img">'
        f'<defs><linearGradient id="g" gradientTransform="rotate({angle} .5 .5)">'
        f'<stop offset="0" stop-color="{palette[0]}"/>'
        f'<stop offset="1" stop-color="{palette[1]}" stop-opacity="0.55"/>'
        f'</linearGradient></defs>'
        f'<rect width="{SIZE}" height="{SIZE}" fill="url(#g)"/>'
        + ''.join(shapes)
        + f'<rect y="{SIZE - band}" width="{SIZE}" height="{band}" '
        f'fill="{palette[0]}" fill-opacity="0.35"/>'
        '</svg>'
    )
