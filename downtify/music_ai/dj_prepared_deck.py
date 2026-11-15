"""Isolated preparation tasks; only the caller adopts their returned files."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .dj_audio import FRAME_BYTES, AudioError, AudioIO


@dataclass(frozen=True)
class PreparedAnalysis:
    track: str
    result: dict
    source: dict
    created_snapshot: bool


@dataclass(frozen=True)
class DecodedDeck:
    key: Any
    path: Path
    frames: int
    buffer: Any = None


def _clone(owner_io):
    clone = AudioIO(
        owner_io.cache,
        owner_io.roots,
        budget=owner_io.budget,
        min_free=owner_io.min_free,
        max_track_seconds=owner_io.max_track_seconds,
        workspace=(
            owner_io.workspace.name
            if owner_io.workspace != owner_io.cache
            else None
        ),
    )
    if hasattr(owner_io, 'reclaim'):
        clone.reclaim = owner_io.reclaim
    return clone


def _private_path(value, owner_io, pattern):
    path = Path(value)
    if (
        owner_io.workspace.is_symlink()
        or path.is_symlink()
        or path.parent.resolve() != owner_io.workspace.resolve()
        or re.fullmatch(pattern, path.name) is None
        or (path.exists() and not path.is_file())
    ):
        raise AudioError('unsafe_prepared_deck_path')
    return path


def discard_analysis(prepared, owner_io):
    if prepared.created_snapshot:
        path = _private_path(
            prepared.source['snapshot']['path'],
            owner_io,
            r'source-[0-9]+\.audio',
        )
        path.unlink(missing_ok=True)


def discard_decoded(decoded, owner_io):
    if decoded.buffer is not None:
        decoded.buffer.close()
    path = _private_path(decoded.path, owner_io, r'decoded-[0-9]+\.pcm')
    path.unlink(missing_ok=True)


def prepare_analysis(worker, owner_io, track, source, slot, checkpoint):
    source = deepcopy(source)
    borrowed = 'snapshot' in source
    io = _clone(owner_io)
    try:
        result = worker.prepare_deck(
            track,
            io,
            source=source,
            slot=slot,
            checkpoint=checkpoint,
            report=False,
        )
        checkpoint()
        return PreparedAnalysis(
            track, deepcopy(result), deepcopy(source), not borrowed
        )
    except BaseException:
        if not borrowed and 'snapshot' in source:
            discard_analysis(
                PreparedAnalysis(track, {}, source, True), owner_io
            )
        raise


def decode_deck(
    owner_io,
    row,
    result,
    source,
    key,
    target,
    checkpoint,
    *,
    progressive=False,
):
    row, result, source = deepcopy((row, result, source))
    target = _private_path(target, owner_io, r'decoded-[0-9]+\.pcm')
    if target.exists():
        raise AudioError('unsafe_cache_destination')
    io = _clone(owner_io)
    audio = source.get('snapshot', source)
    if 'snapshot' in source:
        io.allow_snapshot(audio['path'], audio['source_version'])
    complete = {
        'cue': row['cue'],
        'speed': row['speed'],
        'source_end': result['profile']['duration'],
    }
    try:
        checkpoint()
        if progressive:
            buffer = io.stream(
                audio['path'],
                complete,
                result['loudness'],
                checkpoint,
                expected=audio['source_version'],
            )
            try:
                checkpoint()
                return DecodedDeck(key, target, len(buffer), buffer)
            except BaseException:
                buffer.close()
                raise
        path = io.decode(
            audio['path'],
            complete,
            result['loudness'],
            target,
            checkpoint,
            expected=audio['source_version'],
        )
        path = _private_path(path, owner_io, r'decoded-[0-9]+\.pcm')
        if path != target or path.stat().st_size % FRAME_BYTES:
            raise AudioError('decoded_length_mismatch')
        checkpoint()
        io.check_space(FRAME_BYTES)
        # A new absolute start can increase the rounded span by one frame.
        with path.open('ab') as output:
            output.write(bytes(FRAME_BYTES))
        checkpoint()
        return DecodedDeck(key, path, path.stat().st_size // FRAME_BYTES)
    except BaseException:
        discard_decoded(DecodedDeck(key, target, 0), owner_io)
        raise
