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
import base64
import logging
import mimetypes
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from load_dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel, Field
from uvicorn import Config, Server

from downtify import __version__, api
from downtify.cover_art import extract_cover_art
from downtify.cover_cache import CoverArtCache
from downtify.download_pool import limiter_from_settings
from downtify.downloader import Downloader
from downtify.library_catalog import (
    LibraryContext,
    library_context_from_state,
    list_library_entries,
    resolve_library_file,
)
from downtify.library_delete import delete_library_file
from downtify.library_metadata_cache import LibraryMetadataCache
from downtify.library_paths_cache import invalidate_library_paths_cache
from downtify.library_reconcile import refresh_playlists_after_moves
from downtify.monitor import PlaylistMonitorDB, monitor_loop
from downtify.navidrome_index import NavidromeIndex
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex

load_dotenv()

def _uvicorn_access_log_enabled() -> bool:
    """HTTP request lines are off by default; set DOWNTIFY_ACCESS_LOG=full to enable."""
    raw = str(os.getenv('DOWNTIFY_ACCESS_LOG', '') or '').strip().lower()
    return raw in {'1', 'true', 'full', 'all', 'on'}


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
    intercept = _InterceptHandler()
    for _name in ('uvicorn', 'uvicorn.error', 'uvicorn.access', 'fastapi'):
        _log = logging.getLogger(_name)
        _log.handlers = [intercept]
        _log.propagate = False


DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', '/downloads'))
DATABASE_DIR = Path('/data')
WEB_GUI_LOCATION = os.getenv('WEB_GUI_LOCATION', '/downtify/frontend/dist')
DEFAULT_HOST = os.getenv('HOST', '0.0.0.0')
DEFAULT_PORT = int(os.getenv('DOWNTIFY_PORT', os.getenv('PORT', '8000')))
_TRANSPARENT_GIF = base64.b64decode(
    'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
)


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


class LibraryListEntry(BaseModel):
    """One row from ``GET /list``."""

    file: str
    title: str = ''
    artist: str = ''
    album: str = ''
    has_cover: bool = False
    playlists: list[str] = Field(default_factory=list)


async def _application_startup() -> None:
    loop = asyncio.get_running_loop()
    api.state.loop = loop
    api.state.download_limiter = limiter_from_settings(api.state.settings)
    db_path = DATABASE_DIR / 'downtify_monitor.db'
    api.state.monitor_db = PlaylistMonitorDB(db_path)
    library_db = DATABASE_DIR / 'downtify_library.db'
    api.state.track_index = TrackIndex(library_db)
    api.state.navidrome_index = NavidromeIndex(library_db)
    api.state.metadata_cache = LibraryMetadataCache(library_db)
    api.state.cover_cache = CoverArtCache(DATABASE_DIR / 'cover_cache')
    api.state.playlist_catalog = PlaylistCatalog(library_db)
    lib_ctx = library_context_from_state(
        DOWNLOAD_DIR, api.state.settings, api.state.track_index
    )
    try:
        imported = api.state.track_index.backfill_from_monitor_db(db_path)
        if imported:
            logger.info(
                'Track library index: imported {} path(s) from monitor history',
                imported,
            )
    except Exception:
        logger.exception('Track library backfill from monitor db failed')
    try:
        imported_pl = api.state.playlist_catalog.backfill_from_monitor_db(
            db_path,
            download_dir=lib_ctx.download_dir,
            slskd_dir=lib_ctx.slskd_dir,
        )
        if imported_pl:
            logger.info(
                'Playlist catalog: linked {} track(s) from monitor history',
                imported_pl,
            )
    except Exception:
        logger.exception('Playlist catalog backfill from monitor db failed')
    asyncio.create_task(
        monitor_loop(
            db=api.state.monitor_db,
            get_downloader=lambda: api.state.downloader,
            get_track_index=lambda: api.state.track_index,
            get_navidrome_index=lambda: api.state.navidrome_index,
            get_metadata_cache=lambda: api.state.metadata_cache,
            get_cover_cache=lambda: api.state.cover_cache,
            get_playlist_catalog=lambda: api.state.playlist_catalog,
            broadcast=api.state.connections.broadcast,
            loop=loop,
            settings=api.state.settings,
        )
    )


@asynccontextmanager
async def _application_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await _application_startup()
    yield


def build_app() -> FastAPI:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title='Downtify',
        description=(
            'Download your Spotify playlists and songs along with album '
            'art and metadata in a self-hosted way via Docker.'
        ),
        version=__version__,
        lifespan=_application_lifespan,
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

    api.state.version = __version__
    api.state.downloader = Downloader(
        DOWNLOAD_DIR,
        audio_format=api.state.settings['format'],
        audio_bitrate=api.state.settings.get('bitrate', '320'),
        output_template=api.state.settings['output'].replace(
            '.{output-ext}', ''
        ),
        audio_providers=api._effective_audio_providers(api.state.settings),
        slskd_settings=api._effective_slskd_settings(api.state.settings),
        youtube_settings=api._effective_youtube_settings(api.state.settings),
        lyrics_providers=api._effective_lyrics_providers(api.state.settings),
        organize_by_artist=bool(
            api.state.settings.get('organize_by_artist', False)
        ),
    )
    app.include_router(api.router)

    def _library_ctx() -> LibraryContext:
        return library_context_from_state(
            DOWNLOAD_DIR,
            api.state.settings,
            api.state.track_index,
            metadata_cache=api.state.metadata_cache,
            playlist_catalog=api.state.playlist_catalog,
        )

    @app.get('/list', response_model=list[LibraryListEntry])
    def list_downloads(refresh: bool = False) -> list[LibraryListEntry]:
        if refresh:
            invalidate_library_paths_cache()
        rows = list_library_entries(_library_ctx())
        return [LibraryListEntry.model_validate(row) for row in rows]

    @app.get('/media/{file_path:path}')
    def serve_media(file_path: str) -> FileResponse:
        full = resolve_library_file(file_path, _library_ctx())
        if full is None:
            raise HTTPException(status_code=404, detail='File not found')
        return FileResponse(
            full,
            media_type=mimetypes.guess_type(str(full))[0]
            or 'application/octet-stream',
        )

    async def _refresh_playlists_after_delete(
        playlist_names: set[str],
    ) -> None:
        """M3U / Navidrome refresh can take minutes; run off the request path."""

        if not playlist_names or api.state.downloader is None:
            return
        if api.state.playlist_catalog is None:
            return
        try:
            await asyncio.to_thread(
                refresh_playlists_after_moves,
                playlist_names,
                settings=api.state.settings,
                downloader=api.state.downloader,
                playlist_catalog=api.state.playlist_catalog,
                track_index=api.state.track_index,
                monitor_db=api.state.monitor_db,
                navidrome_index=api.state.navidrome_index,
            )
        except Exception:
            logger.exception(
                'delete: background playlist refresh failed for {}',
                ', '.join(sorted(playlist_names)[:5]),
            )

    @app.delete('/delete')
    async def delete_download(file: str) -> dict:
        result = delete_library_file(
            file,
            _library_ctx(),
            cover_cache=api.state.cover_cache,
            metadata_cache=api.state.metadata_cache,
            playlist_catalog=api.state.playlist_catalog,
            track_index=api.state.track_index,
            navidrome_index=api.state.navidrome_index,
        )
        if not result.get('deleted'):
            return {
                'deleted': False,
                'error': result.get('error') or 'File not found',
            }
        affected = set(result.get('playlists_affected') or [])
        if affected:
            asyncio.create_task(_refresh_playlists_after_delete(affected))
        return {
            'deleted': True,
            'playlists_affected': result.get('playlists_affected') or [],
            'playlists_refresh_scheduled': bool(affected),
        }

    @app.get('/cover')
    def get_cover(file: str):
        full = resolve_library_file(file, _library_ctx())
        if full is None:
            raise HTTPException(status_code=404, detail='File not found')

        data: bytes | None = None
        mime: str | None = None
        if api.state.settings.get('cache_cover_art'):
            cache = api.state.cover_cache
            if cache is not None:
                hit = cache.lookup(file, full)
                if hit is not None:
                    data, mime = hit
        if data is None:
            data, mime = extract_cover_art(full)
            if data is None:
                return Response(
                    content=_TRANSPARENT_GIF,
                    media_type='image/gif',
                    headers={'Cache-Control': 'public, max-age=3600'},
                )
            if api.state.settings.get('cache_cover_art'):
                cache = api.state.cover_cache
                if cache is not None:
                    cache.store(file, full, data, mime or 'image/jpeg')
        return Response(
            content=data,
            media_type=mime or 'image/jpeg',
            headers={
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
        access_log=_uvicorn_access_log_enabled(),
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
