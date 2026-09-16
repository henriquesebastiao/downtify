"""Downtify entry point.

Boots the FastAPI app that powers the web UI. The previous incarnation
relied on the Spotify Web API (via ``spotdl`` + ``spotipy``); since that
path now requires a Spotify Premium account, this version resolves
metadata directly from the public ``open.spotify.com/embed`` endpoints
and pulls the audio from YouTube via ``yt-dlp``.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import mimetypes
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from load_dotenv import load_dotenv
from loguru import logger
from uvicorn import Config, Server

from downtify import __version__, api, m3u
from downtify.cookies import CookiesStore
from downtify.cover_art import extract_cover_art
from downtify.cover_cache import CoverArtCache
from downtify.downloader import Downloader
from downtify.library_catalog import (
    list_library_entries,
    list_library_paths,
    resolve_library_file,
)
from downtify.library_cleanup import remove_track_leftovers
from downtify.library_metadata_cache import LibraryMetadataCache
from downtify.library_paths import SLSKD_LIBRARY_PREFIX
from downtify.monitor import PlaylistMonitorDB, monitor_loop, reconcile_loop
from downtify.navidrome_index import NavidromeIndex
from downtify.playlist_batches import PlaylistBatchStore, ensure_batch_records
from downtify.playlist_catalog import PlaylistCatalog
from downtify.playlist_spotify_cache import (
    PlaylistSpotifyCache,
    playlist_spotify_cache_loop,
)
from downtify.track_index import TrackIndex
from downtify.update_check import UpdateChecker, update_check_loop

load_dotenv()


class _InterceptHandler(logging.Handler):
    """Redirect all stdlib logging records into loguru."""

    @staticmethod
    def emit(record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def _setup_logging(level: str) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        format=(
            '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | '
            '<level>{level: <8}</level> | '
            '<cyan>{name}</cyan> - '
            '<level>{message}</level>'
        ),
        level=level.upper(),
        colorize=None,
    )
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    # Explicitly override uvicorn's loggers before it starts — uvicorn will
    # still write to these logger names, and we want them flowing through
    # loguru rather than being printed raw by uvicorn's default handler.
    for _name in ('uvicorn', 'uvicorn.error', 'uvicorn.access', 'fastapi'):
        _log = logging.getLogger(_name)
        _log.handlers = [_InterceptHandler()]
        _log.propagate = False


DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', '/downloads'))
DATABASE_DIR = Path(os.getenv('DATABASE_DIR', '/data'))
WEB_GUI_LOCATION = os.getenv('WEB_GUI_LOCATION', '/downtify/frontend/dist')
DEFAULT_HOST = os.getenv('HOST', '0.0.0.0')
DEFAULT_PORT = int(os.getenv('DOWNTIFY_PORT', os.getenv('PORT', '8000')))


class SPAStaticFiles(StaticFiles):
    """Serve ``index.html`` for unknown paths so SPA routing works."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except Exception:
            return await super().get_response('index.html', scope)


def _fix_mime_types() -> None:
    mimetypes.add_type('application/javascript', '.js')
    mimetypes.add_type('application/javascript', '.mjs')
    mimetypes.add_type('text/css', '.css')


def _extract_cover(path: Path) -> tuple[bytes | None, str | None]:
    """Return ``(image_bytes, mime)`` for a track's cover, or ``(None, None)``.

    Embedded art first (ID3 APIC, FLAC Picture, MP4 ``covr``, Vorbis
    METADATA_BLOCK_PICTURE), then a ``cover.jpg``/``folder.jpg`` next to
    the file. The reader lives in ``downtify/cover_art.py`` so the library
    catalog's ``has_cover`` flag and the cover cache use the same logic.
    """

    return extract_cover_art(path)


#: Hard cap on a single batch-delete request, so an accidental
#: "select everything" on a huge library can't tie up a request
#: forever or send a payload that's obviously not a real selection.
MAX_BATCH_DELETE = 2000


def _library_root_for(
    file: str, base: Path, slskd_dir: Optional[Path]
) -> tuple[Path, str]:
    """``(root, path relative to root)`` for a library path.

    ``slskd/...`` paths are slskd downloads left in place under the slskd
    folder; everything else is relative to the downloads folder.
    """
    text = str(file or '').replace('\\', '/')
    if slskd_dir is not None and text.startswith(SLSKD_LIBRARY_PREFIX):
        return slskd_dir.resolve(), text[len(SLSKD_LIBRARY_PREFIX) :]
    return base, text


def _delete_track_file(
    file: str, base: Path, slskd_dir: Optional[Path] = None
) -> dict:
    """Delete one track (``file``, relative to ``base``) plus its
    sidecars, and prune the folder it leaves behind if it's now empty.

    ``slskd/...`` paths are resolved against ``slskd_dir`` instead, with the
    same cleanup, and pruning stops at the slskd folder.

    Returns ``{'deleted': True}`` or ``{'deleted': False, 'error': str}``
    — this is the exact shape ``DELETE /delete`` has always returned;
    ``DELETE /delete/batch`` reuses it per file.
    """
    root, relative = _library_root_for(file, base, slskd_dir)
    # Resolve and confine to its root to prevent path traversal.
    try:
        full = (root / relative).resolve()
        full.relative_to(root)
    except (ValueError, RuntimeError):
        return {'deleted': False, 'error': 'Invalid path'}
    if not full.is_file():
        return {'deleted': False, 'error': 'File not found'}
    try:
        full.unlink()
    except Exception as exc:
        return {'deleted': False, 'error': str(exc)}
    remove_track_leftovers(full, root)
    return {'deleted': True}


def _delete_tracks_batch(
    files: list[str], base: Path, slskd_dir: Optional[Path] = None
) -> dict:
    """Delete every file in ``files`` (each relative to ``base``).

    Each file is handled independently through :func:`_delete_track_file`
    — one bad path or an already-gone file doesn't stop the rest.
    Raises :class:`ValueError` if ``files`` is larger than
    :data:`MAX_BATCH_DELETE`, so an accidental "select everything" on a
    huge library can't tie up a request forever.
    """
    # Dedupe (order-preserving) so a client sending the same path twice
    # can't have the second attempt report a spurious "File not found"
    # for a file the first attempt already removed.
    files = list(dict.fromkeys(files))
    if len(files) > MAX_BATCH_DELETE:
        raise ValueError(
            f'Cannot delete more than {MAX_BATCH_DELETE} files in one request'
        )
    results = {f: _delete_track_file(f, base, slskd_dir) for f in files}
    deleted = sum(1 for r in results.values() if r['deleted'])
    return {
        'deleted_count': deleted,
        'failed_count': len(files) - deleted,
        'results': results,
    }


def _open_library_stores(monitor_db_path: Path) -> None:
    """Open the library catalog/index/cache stores in /data and backfill the
    track index and playlist catalog from Playlist Monitor history."""

    library_db = DATABASE_DIR / 'downtify_library.db'
    api.state.track_index = TrackIndex(library_db)
    api.state.navidrome_index = NavidromeIndex(library_db)
    api.state.metadata_cache = LibraryMetadataCache(library_db)
    api.state.playlist_catalog = PlaylistCatalog(library_db)
    api.state.playlist_batch_store = PlaylistBatchStore(library_db)
    api.state.playlist_spotify_cache = PlaylistSpotifyCache(library_db)
    api.state.cover_cache = CoverArtCache(DATABASE_DIR / 'cover_cache')
    ctx = api.library_context()
    try:
        imported = api.state.track_index.backfill_from_monitor_db(
            monitor_db_path
        )
        if imported:
            logger.info(
                'Track library index: imported {} path(s) from monitor '
                'history',
                imported,
            )
    except Exception:
        logger.exception('Track library backfill from monitor db failed')
    try:
        linked = api.state.playlist_catalog.backfill_from_monitor_db(
            monitor_db_path,
            download_dir=ctx.download_dir,
            slskd_dir=ctx.slskd_dir,
        )
        if linked:
            logger.info(
                'Playlist catalog: linked {} track(s) from monitor history',
                linked,
            )
    except Exception:
        logger.exception('Playlist catalog backfill from monitor db failed')
    try:
        registered = ensure_batch_records(
            api.state.playlist_batch_store,
            api.collect_playlist_batch_sync_rows(),
        )
        if registered:
            logger.info(
                'Playlist batches: registered {} playlist(s) from library',
                registered,
            )
    except Exception:
        logger.exception('Playlist batch sync from library failed')


def build_app() -> FastAPI:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        loop = asyncio.get_running_loop()
        api.state.loop = loop
        api.state.download_semaphore = asyncio.Semaphore(
            api._clamp_parallel_downloads(
                api.state.settings.get('max_parallel_downloads', 3)
            )
        )
        db_path = DATABASE_DIR / 'downtify_monitor.db'
        api.state.monitor_db = PlaylistMonitorDB(db_path)
        _open_library_stores(db_path)
        # Keeps the cached Spotify track lists of known playlists fresh for
        # the playlist batch reports.
        asyncio.create_task(
            playlist_spotify_cache_loop(
                api.state.playlist_spotify_cache,
                api.known_spotify_playlist_ids,
            )
        )
        asyncio.create_task(
            monitor_loop(
                db=api.state.monitor_db,
                get_downloader=lambda: api.state.downloader,
                broadcast=api.state.connections.broadcast,
                loop=loop,
                settings=api.state.settings,
                get_library=api.library_stores,
            )
        )
        # Separate hourly sweep that forgets a downloaded-track record once
        # its file is gone from the downloads directory — see
        # downtify/monitor.py:reconcile_loop for why this is a distinct,
        # slower cadence from the per-watch monitor_loop above.
        asyncio.create_task(
            reconcile_loop(
                db=api.state.monitor_db,
                get_downloader=lambda: api.state.downloader,
            )
        )
        # Hourly check against GitHub Releases (see
        # downtify/update_check.py) so the footer can tell the user a
        # newer Downtify is out. GET /api/check_update only ever reads
        # this loop's cached result — the request to GitHub never blocks
        # a page load.
        api.state.update_checker = UpdateChecker()
        asyncio.create_task(update_check_loop(api.state.update_checker))

        yield

    app = FastAPI(
        lifespan=lifespan,
        title='Downtify',
        description=(
            'Download your Spotify playlists and songs along with album '
            'art and metadata in a self-hosted way via Docker.'
        ),
        version=__version__,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    settings_path = DATABASE_DIR / 'settings.json'
    api.state.settings_path = settings_path
    api.state.settings = api._load_settings(settings_path)

    # Lives alongside settings.json in the /data volume so an uploaded
    # cookies.txt survives container updates.
    cookies_store = CookiesStore(DATABASE_DIR / 'cookies.txt')
    api.state.cookies_store = cookies_store

    api.state.version = __version__
    api.state.downloader = Downloader(
        DOWNLOAD_DIR,
        cookies_store=cookies_store,
        audio_format=api.state.settings['format'],
        audio_bitrate=api.state.settings.get('bitrate', '320'),
        output_template=api.state.settings['output'].replace(
            '.{output-ext}', ''
        ),
        lyrics_providers=api._effective_lyrics_providers(api.state.settings),
        organize_by_artist=bool(
            api.state.settings.get('organize_by_artist', False)
        ),
        organize_by_album=bool(
            api.state.settings.get('organize_by_album', False)
        ),
        download_cover_art=bool(
            api.state.settings.get('download_cover_art', True)
        ),
        overwrite_existing_files=bool(
            api.state.settings.get('overwrite_existing_files', True)
        ),
        audio_providers=api._effective_audio_providers(api.state.settings),
        slskd_settings=api._effective_slskd_settings(api.state.settings),
    )
    api.providers.set_cover_resolution(
        api._clamp_cover_resolution(
            api.state.settings.get(
                'cover_resolution', api.providers.DEFAULT_COVER_RESOLUTION
            )
        )
    )
    app.include_router(api.router)

    @app.get('/list')
    def list_downloads(refresh: bool = False) -> list[str]:
        """Every playable library file: the downloads folder (recursively,
        so per-playlist folders show up), slskd downloads left in place
        (``slskd/...``) and files known to the track index.

        The directory scan is cached briefly; ``?refresh=true`` forces a
        rescan.
        """
        if refresh:
            api.invalidate_library_paths_cache()
        return list_library_paths(api.library_context())

    @app.get('/playlists')
    def list_playlists() -> list[dict]:
        """List downloaded playlists, derived from the ``.m3u`` files
        Downtify already writes for playlist/album downloads and
        Playlist Monitor sweeps (see ``downtify/m3u.py``).

        Each M3U file on disk is one playlist, regardless of whether
        *Organize by artist/album* put its tracks in a per-playlist
        folder or scattered them into artist/album folders — the M3U is
        the one place that still records "these tracks belong together,
        in this order" either way. Single tracks and albums downloaded
        without an M3U (e.g. via the YouTube Music album endpoint)
        aren't playlists and don't show up here.
        """
        base = DOWNLOAD_DIR.resolve()
        if not base.exists():
            return []
        slskd_dir = api.library_context().slskd_dir
        playlists: list[dict] = []
        for m3u_path in sorted(base.rglob('*.m3u')):
            tracks = m3u.read_m3u_tracks(m3u_path, base, slskd_dir)
            if not tracks:
                continue
            playlists.append({
                'name': m3u_path.stem,
                'files': tracks,
                'count': len(tracks),
            })
        playlists.sort(key=lambda p: p['name'].casefold())
        return playlists

    @app.get('/tracks')
    def list_tracks() -> list[dict]:
        """List library tracks with metadata read from embedded tags.

        Powers the player's and Library's "only this artist" / "only
        this album" filters — ``/list`` only has filenames, and album in
        particular isn't reliably derivable from the filename or folder
        layout unless *Organize by artist/album* is on.

        Each row has ``file``, ``artist`` and ``album``, plus ``title``,
        ``has_cover`` and, when the file belongs to a downloaded
        playlist, ``playlists``. Tags are cached in /data per file and
        re-read only when the file's modification time or size changes.
        """
        tracks = list_library_entries(api.library_context())
        tracks.sort(key=lambda t: t['file'])
        return tracks

    @app.get('/media/{file_path:path}')
    def serve_media(file_path: str) -> FileResponse:
        """Serve a library file by its library path.

        Covers what the ``/downloads`` static mount can't: slskd downloads
        left in place under the slskd folder (``slskd/...``).
        """
        full = resolve_library_file(file_path, api.library_context())
        if full is None:
            raise HTTPException(status_code=404, detail='File not found')
        return FileResponse(
            full,
            media_type=mimetypes.guess_type(str(full))[0]
            or 'application/octet-stream',
        )

    @app.delete('/delete')
    async def delete_download(file: str) -> dict:
        result = await asyncio.to_thread(
            _delete_track_file,
            file,
            DOWNLOAD_DIR.resolve(),
            api.library_context().slskd_dir,
        )
        return await api.after_library_delete({file: result}, result)

    @app.delete('/delete/batch')
    async def delete_downloads_batch(
        files: list[str] = Body(..., embed=True),
    ) -> dict:
        """Delete several tracks in one request.

        Powers the Library page's multi-select — selecting every track
        matching the active playlist/artist/album filter (including
        ones on other pages) and deleting them all is impractical one
        file at a time. Each file is deleted independently: one bad
        path or a file that's already gone doesn't stop the rest.
        """
        try:
            result = await asyncio.to_thread(
                _delete_tracks_batch,
                files,
                DOWNLOAD_DIR.resolve(),
                api.library_context().slskd_dir,
            )
        except ValueError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        return await api.after_library_delete(result['results'], result)

    @app.get('/cover')
    def get_cover(file: str):
        # Resolved and confined to the downloads or slskd folder, which
        # prevents path traversal.
        full = resolve_library_file(file, api.library_context())
        if full is None:
            raise HTTPException(status_code=404, detail='File not found')

        data: bytes | None = None
        mime: str | None = None
        cache = (
            api.state.cover_cache
            if api.state.settings.get('cache_cover_art')
            else None
        )
        if cache is not None:
            hit = cache.lookup(file, full)
            if hit is not None:
                data, mime = hit
        if data is None:
            data, mime = _extract_cover(full)
            if data is None:
                raise HTTPException(
                    status_code=404, detail='No embedded cover'
                )
            if cache is not None:
                cache.store(file, full, data, mime or 'image/jpeg')
        return Response(
            content=data,
            media_type=mime or 'image/jpeg',
            headers={
                # Cache by mtime — clients fetch once per file revision.
                'Cache-Control': 'public, max-age=86400',
                'ETag': f'"{int(full.stat().st_mtime)}"',
            },
        )

    app.mount(
        '/downloads',
        StaticFiles(directory=str(DOWNLOAD_DIR)),
        name='downloads',
    )
    app.mount(
        '/',
        SPAStaticFiles(directory=WEB_GUI_LOCATION, html=True),
        name='static',
    )
    return app


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog='downtify')
    # The legacy entrypoint passed ``web`` as the subcommand plus a few
    # spotdl-only flags. We accept and ignore the unsupported ones so
    # existing Docker images keep starting cleanly.
    parser.add_argument('mode', nargs='?', default='web')
    parser.add_argument('--host', default=DEFAULT_HOST)
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--log-level', default='info')
    parser.add_argument('--keep-alive', action='store_true')
    parser.add_argument('--keep-sessions', action='store_true')
    parser.add_argument('--web-use-output-dir', action='store_true')
    args, _ = parser.parse_known_args()
    return args


def main() -> None:
    args = _parse_args()
    _setup_logging(args.log_level)

    _fix_mime_types()
    app = build_app()

    loop = (
        asyncio.new_event_loop()
        if sys.platform != 'win32'
        else asyncio.ProactorEventLoop()  # type: ignore[attr-defined]
    )
    config = Config(
        app=app,
        host=args.host,
        port=args.port,
        loop=loop,  # type: ignore[arg-type]
        log_level=args.log_level.lower(),
        log_config=None,
        workers=1,
    )
    server = Server(config)

    logger.info(
        'Starting Downtify {} on http://{}:{}',
        __version__,
        args.host,
        args.port,
    )
    logger.info('Application log level (Loguru): {}', args.log_level.upper())
    loop.run_until_complete(server.serve())


if __name__ == '__main__':
    main()
