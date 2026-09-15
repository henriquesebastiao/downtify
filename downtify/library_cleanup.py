"""Leftovers to clean up after a library track is deleted.

Shared by ``DELETE /delete`` / ``/delete/batch`` (``main.py``) and the
library catalog deletes (``downtify/library_delete.py``: playlist delete,
tag-mismatch cleanup), so every way of removing a track leaves the same
state behind.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

_AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.flac', '.ogg', '.wav', '.aac', '.opus'}

#: Filename written by Downloader._save_album_cover next to every track
#: of an album folder (organize-by-album layout only).
ALBUM_COVER_FILENAME = 'cover.jpg'


def delete_lrc_sidecar(audio_path: Path) -> None:
    """Best-effort removal of the .lrc sidecar next to a deleted track.

    Mirrors the naming ``downtify/downloader.py:embed_lyrics`` writes the
    sidecar with — same basename as the audio file, ``.lrc`` extension.
    A missing or unremovable sidecar must not fail the audio file's own
    deletion, which has already succeeded by the time this runs.
    """
    lrc = audio_path.with_suffix('.lrc')
    try:
        lrc.unlink(missing_ok=True)
    except OSError:
        logger.opt(exception=True).warning(
            'Could not remove LRC sidecar {}', lrc
        )


def delete_album_cover_if_orphaned(audio_path: Path) -> None:
    """Best-effort removal of a now-unused ``cover.jpg``.

    ``cover.jpg`` (written by ``Downloader._save_album_cover`` under the
    *Organize by album* layout) sits once per album folder, shared by
    every track in it — so it's only safe to delete once no other track
    in that same folder still needs it. Checked *after* the audio file
    itself is gone, so the deleted track doesn't count as a remaining
    dependent.
    """
    folder = audio_path.parent
    cover = folder / ALBUM_COVER_FILENAME
    if not cover.is_file():
        return
    still_used = any(
        p.is_file() and p.suffix.lower() in _AUDIO_EXTENSIONS
        for p in folder.iterdir()
    )
    if still_used:
        return
    try:
        cover.unlink(missing_ok=True)
    except OSError:
        logger.opt(exception=True).warning(
            'Could not remove orphaned album cover {}', cover
        )


def prune_empty_parent_dirs(start_dir: Path, root: Path) -> None:
    """Remove ``start_dir`` and its empty ancestors, stopping at ``root``.

    Run after a track and its sidecars are deleted, so a per-playlist or
    per-artist/album folder left with nothing in it doesn't linger
    forever. Climbs one directory at a time and stops at the first one
    that still has something in it — ``root`` (the downloads directory)
    is never removed itself, even if it ends up empty.
    """
    try:
        root = root.resolve()
        current = start_dir.resolve()
    except OSError:
        return
    # Safety: only ever climb within root's own tree, never above it.
    if current != root and root not in current.parents:
        return
    while current != root:
        try:
            if any(current.iterdir()):
                return
            current.rmdir()
        except OSError:
            return
        current = current.parent


def remove_track_leftovers(audio_path: Path, root: Path) -> None:
    """Run every cleanup step for an already-deleted track under ``root``."""

    delete_lrc_sidecar(audio_path)
    delete_album_cover_if_orphaned(audio_path)
    prune_empty_parent_dirs(audio_path.parent, root)
