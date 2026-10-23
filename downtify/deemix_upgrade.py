"""Opt-in catalog-verified Deemix replacements, with durable receipts."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

from . import lyrics as lyrics_mod
from .deemix_provider import (
    DeemixClient,
    _catalog_track,
    candidate_matches,
    download_from_deemix,
    normalize_settings,
    verified_audio,
)
from .deemix_upgrade_playlists import digest, rewrite_playlists
from .deemix_upgrade_store import AudioReplacementStore
from .library_cache_keys import file_content_key
from .library_catalog import (
    LibraryContext,
    library_entry_for_file,
    resolve_library_file,
)
from .library_paths import library_stored_path
from .library_upgrade import UpgradeOptions, UpgradeOutcome
from .library_upgrade_db import JOB_DONE, JOB_SKIPPED


class DeemixLibraryUpgrade:
    """Prepare individually, then publish references once per batch.

    The Deemix collection is only read. The sole deletable files are
    individually verified originals inside Downtify's download root.
    """

    def __init__(
        self,
        store: AudioReplacementStore,
        context: Callable[[], LibraryContext],
        settings: Callable[[], dict[str, Any]],
        playing: Callable[[], set[str]],
        publish_catalog: Callable[[], None],
        rekey_owners: Callable[[str, str, str], None] | None = None,
        lyrics_cache: Any = None,
    ) -> None:
        self.store = store
        self.context = context
        self.settings = settings
        self.playing = playing
        self.publish_catalog = publish_catalog
        self.rekey_owners = rekey_owners
        self.lyrics_cache = lyrics_cache

    @staticmethod
    def _guard() -> None:
        """Optional host mount markers, checked again before destructive work."""
        markers = json.loads(
            os.environ.get('DOWNTIFY_LIBRARY_READY_MARKERS', '{}')
        )
        for name, expected in markers.items():
            if Path(name).read_text(encoding='utf-8').strip() != expected:
                raise ValueError('A required library mount is unavailable')

    def _source(self, stored: str) -> Path:
        ctx = self.context()
        if stored.startswith(('ext/', 'slskd/')):
            raise ValueError('External originals are never removed')
        full = (ctx.download_dir / stored).resolve(strict=True)
        if (
            not full.is_relative_to(ctx.download_dir.resolve())
            or not full.is_file()
        ):
            raise ValueError('Original is outside the download collection')
        return full

    def _config(self) -> dict[str, Any]:
        self._guard()
        cfg = normalize_settings(self.settings().get('deemix') or {})
        if not cfg['enabled']:
            raise ValueError('Enable and test Deemix before replacing audio')
        source = Path(cfg['source_dir']).resolve(strict=True)
        if source not in [p.resolve() for p in self.context().extra_dirs]:
            raise ValueError('Register the Deemix collection first')
        return cfg

    def prepare(
        self,
        stored: str,
        options: UpgradeOptions,
        run_id: int,
        on_stage: Callable[[str], None],
    ) -> UpgradeOutcome:
        cfg = self._config()
        old = self._source(stored)
        if old.is_relative_to(Path(cfg['source_dir']).resolve()):
            return UpgradeOutcome(
                JOB_SKIPPED, 'Already in the Deemix collection', checked=False
            )
        receipt = self.store.get(stored)
        chosen_id = options.deemix_recordings.get(stored)
        old_sha = digest(old)
        if receipt:
            if chosen_id and str(receipt['catalog'].get('id')) != chosen_id:
                raise ValueError(
                    'A different replacement was already prepared; review that operation first'
                )
            if receipt['old_sha'] != old_sha:
                raise ValueError(
                    'Original changed since preparation; kept for review'
                )
            self._verified_target(receipt)
            self.store.reuse(stored, run_id, options.delete_replaced_audio)
            return UpgradeOutcome(
                JOB_DONE,
                'Verified replacement reused; publication pending',
                checked=False,
            )
        entry = library_entry_for_file(stored, old)
        required = (
            ('title', 'artist') if chosen_id else ('title', 'artist', 'album')
        )
        if not all(entry.get(key) for key in required):
            return UpgradeOutcome(
                JOB_SKIPPED,
                'Artist, title and album are required for safe matching',
                checked=False,
            )
        if (
            entry.get('codec') in {'flac', 'alac', 'wav'}
            and cfg['bitrate'] != '9'
        ):
            return UpgradeOutcome(
                JOB_SKIPPED,
                'Kept lossless original; select FLAC in Deemix first',
                checked=False,
            )
        if cfg['bitrate'] == '1' and int(entry.get('bitrate') or 0) > 150000:
            return UpgradeOutcome(
                JOB_SKIPPED, 'Kept higher-bitrate original', checked=False
            )
        song = {
            'name': entry['title'],
            'artist': entry['artist'],
            'album_name': entry['album'],
        }
        if entry.get('explicit'):
            song['explicit'] = True
        on_stage('matching')
        client = DeemixClient(cfg)
        try:
            client.connect()
            row = _catalog_track(
                client,
                {'song_id': 'deezer-' + chosen_id} if chosen_id else song,
            )
        finally:
            client.close()
        if chosen_id and row is not None:
            # An explicitly reviewed catalog link can correct an old
            # album label. It must still be the same artist/title/version.
            if str(row.get('id')) != chosen_id or not candidate_matches(
                {**song, 'album_name': ''}, row
            ):
                return UpgradeOutcome(
                    JOB_SKIPPED,
                    'Selected recording does not match the artist and title; original retained',
                    checked=False,
                )
            song = {
                **song,
                'album_name': (row.get('album') or {}).get('title'),
            }
        if row is None or not candidate_matches(song, row):
            return UpgradeOutcome(
                JOB_SKIPPED,
                'No unambiguous matching album recording; original retained',
                checked=False,
            )
        on_stage('downloading')
        target = download_from_deemix({'song_id': f'deezer-{row["id"]}'}, cfg)
        if target is None:
            raise ValueError('Deemix did not return a verified recording')
        target = target.resolve(strict=True)
        if target == old or not target.is_relative_to(
            Path(cfg['source_dir']).resolve()
        ):
            raise ValueError(
                'Replacement must remain inside the separate Deemix collection'
            )
        target_sha = digest(target)
        if not verified_audio(target, row, cfg['bitrate']):
            raise ValueError('Replacement metadata or duration did not verify')
        on_stage('verifying')
        subprocess.run(
            [
                'ffmpeg',
                '-nostdin',
                '-v',
                'error',
                '-xerror',
                '-i',
                str(target),
                '-f',
                'null',
                '-',
            ],
            check=True,
            capture_output=True,
            timeout=180,
        )
        if digest(old) != old_sha:
            raise ValueError(
                'Original changed during download; kept for review'
            )
        ctx = self.context()
        new_file = library_stored_path(
            target, ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
        )
        metadata = library_entry_for_file(new_file, target)
        if not candidate_matches(
            song,
            {
                'title': metadata.get('title'),
                'artist': {'name': metadata.get('artist')},
                'album': {'title': metadata.get('album')},
                'explicit_lyrics': bool(metadata.get('explicit')),
            },
        ):
            raise ValueError(
                'Downloaded album tags do not match the requested release'
            )
        if entry.get('has_cover') and not metadata.get('has_cover'):
            raise ValueError('Replacement is missing the original artwork')
        if (
            ctx.metadata_cache is not None
            and ctx.metadata_cache.refresh(new_file, target) is None
        ):
            raise ValueError('Replacement could not be registered')
        self._missing_lyrics(target, row)
        if digest(target) != target_sha:
            raise ValueError(
                'Replacement changed during verification; original retained'
            )
        self.store.save_prepared({
            'old_file': stored,
            'run_id': run_id,
            'new_file': new_file,
            'old_key': file_content_key(old),
            'new_key': file_content_key(target),
            'old_sha': old_sha,
            'new_sha': target_sha,
            'new_metadata': metadata,
            'catalog': row,
            'delete_original': int(options.delete_replaced_audio),
        })
        return UpgradeOutcome(
            JOB_DONE,
            'Deemix recording verified; publication pending',
            changed=['audio'],
            checked=False,
        )

    def _missing_lyrics(self, target: Path, row: dict[str, Any]) -> None:
        """Supplement absent lyrics only; never retag or overwrite Deemix."""
        existing = lyrics_mod.read_track_lyrics(target)
        if existing.get('synced') or existing.get('plain'):
            return
        providers = self.settings().get('lyrics_providers') or []
        if not providers:
            return
        song = {
            'name': row.get('title'),
            'artists': [row.get('artist') or {}],
            'album_name': (row.get('album') or {}).get('title'),
            'duration': row.get('duration'),
        }
        found = lyrics_mod.fetch(song, providers, self.lyrics_cache)
        if found is None or not found.has_any():
            return
        dest = lyrics_mod.lrc_path_for(target)
        if (
            dest.resolve().is_relative_to(
                Path(self._config()['source_dir']).resolve()
            )
            or dest.exists()
        ):
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        staged = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=dest.parent, prefix='.deemix-lyrics-', delete=False
            ) as output:
                staged = Path(output.name)
                output.write(
                    (found.synced or found.plain or '').encode('utf-8')
                )
                output.flush()
                os.fsync(output.fileno())
            try:
                os.link(staged, dest)
            except FileExistsError:
                pass
        finally:
            if staged:
                staged.unlink(missing_ok=True)

    def _verified_target(self, receipt: dict[str, Any]) -> Path:
        ctx = self.context()
        cfg = self._config()
        target = resolve_library_file(receipt['new_file'], ctx)
        if target is None or not target.resolve().is_relative_to(
            Path(cfg['source_dir']).resolve()
        ):
            raise ValueError('Replacement collection is unavailable')
        if digest(target) != receipt['new_sha']:
            raise ValueError('Replacement changed; original retained')
        return target

    def finalize(
        self, run_id: int, stopped: Callable[[], bool]
    ) -> list[dict[str, Any]]:
        receipts = self.store.for_run(run_id)
        ctx = self.context()
        mapping: dict[Path, tuple[Path, float]] = {}
        eligible = []
        playing = self.playing()
        for receipt in receipts:
            if stopped():
                raise InterruptedError('Replacement paused')
            if receipt['old_file'] in playing:
                raise ValueError(
                    'An original is playing; pause playback and resume this run'
                )
            target = self._verified_target(receipt)
            old = (ctx.download_dir / receipt['old_file']).resolve()
            if not old.exists() and receipt['state'] in {'linked', 'removed'}:
                self.store.mark(
                    receipt['old_file'],
                    'removed',
                    'Cleanup already completed',
                    deleted=True,
                )
                continue
            old = self._source(receipt['old_file'])
            if digest(old) != receipt['old_sha']:
                raise ValueError(
                    'Original changed before publication; retained'
                )
            alias = os.environ.get('DOWNTIFY_DEEMIX_M3U_ROOT', '')
            playlist_target = target
            if alias:
                root = Path(self._config()['source_dir']).resolve()
                if Path(alias).resolve() != root:
                    raise ValueError(
                        'M3U alias does not resolve to the Deemix collection'
                    )
                playlist_target = Path(alias) / target.relative_to(root)
            mapping[old] = (
                playlist_target,
                receipt['new_metadata']['duration'],
            )
            eligible.append(receipt)
        roots = [ctx.download_dir, *ctx.extra_dirs]
        if ctx.slskd_dir:
            roots.append(ctx.slskd_dir)
        rewrite_playlists(roots, ctx.download_dir, mapping, stopped=stopped)
        if stopped():
            raise InterruptedError(
                'Replacement paused before reference publication'
            )
        self.store.relink(eligible)
        self.store.assert_relinked(eligible)
        if self.rekey_owners:
            for receipt in eligible:
                self.rekey_owners(
                    receipt['old_key'], receipt['new_key'], receipt['new_file']
                )
        self.publish_catalog()

        for receipt in eligible:
            if stopped():
                raise InterruptedError('Replacement paused before cleanup')
            old_file = receipt['old_file']
            if not receipt['delete_original']:
                self.store.mark(
                    old_file, 'retained', 'Original kept by request'
                )
                continue
            if old_file in self.playing():
                raise ValueError('Original is playing; cleanup deferred')
            old = self._source(old_file)
            self._verified_target(receipt)
            if digest(old) != receipt['old_sha']:
                raise ValueError('Original changed before cleanup; retained')
            self._guard()
            # The database transaction and M3U publication have succeeded;
            # remove only this verified original, never folders or sidecars.
            old.unlink()
            self.store.mark(
                old_file,
                'removed',
                'Original removed after verified import',
                deleted=True,
            )
            if ctx.metadata_cache is not None:
                ctx.metadata_cache.forget(old_file)
        self.publish_catalog()
        return self.store.for_run(run_id)


def alias_file(
    stored: str, store: AudioReplacementStore, ctx: LibraryContext
) -> Path | None:
    """Read-only compatibility for old player URLs; not used by mutations."""
    alias = store.path_alias(stored)
    return resolve_library_file(alias, ctx) if alias else None
