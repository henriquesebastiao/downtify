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
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from load_dotenv import load_dotenv
from uvicorn import Config, Server

from downtify import __version__, api
from downtify.downloader import Downloader
from downtify.monitor import PlaylistMonitorDB, monitor_loop

load_dotenv()

logger = logging.getLogger(__name__)
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', '/downloads'))
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


def build_app() -> FastAPI:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
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

    api.state.version = __version__
    api.state.downloader = Downloader(
        DOWNLOAD_DIR,
        audio_format=api.state.settings['format'],
        audio_bitrate=api.state.settings.get('bitrate', '320'),
        output_template=api.state.settings['output'].replace(
            '.{output-ext}', ''
        ),
    )
    app.include_router(api.router)

    @app.on_event('startup')
    async def _startup() -> None:
        loop = asyncio.get_running_loop()
        api.state.loop = loop
        db_path = DOWNLOAD_DIR / 'downtify_monitor.db'
        api.state.monitor_db = PlaylistMonitorDB(db_path)
        asyncio.create_task(
            monitor_loop(
                db=api.state.monitor_db,
                get_downloader=lambda: api.state.downloader,
                broadcast=api.state.connections.broadcast,
                loop=loop,
            )
        )

    @app.get('/list')
    def list_downloads() -> list[str]:
        audio_exts = {'.mp3', '.m4a', '.flac', '.ogg', '.wav', '.aac', '.opus'}
        try:
            entries = os.listdir(str(DOWNLOAD_DIR))
        except FileNotFoundError:
            return []
        files: list[str] = []
        for entry in entries:
            full = os.path.join(str(DOWNLOAD_DIR), entry)
            if (
                os.path.isfile(full)
                and os.path.splitext(entry)[1].lower() in audio_exts
            ):
                files.append(entry)
        files.sort()
        return files

    @app.delete('/delete')
    def delete_download(file: str) -> dict:
        full = os.path.join(str(DOWNLOAD_DIR), file)
        if not os.path.isfile(full):
            return {'deleted': False, 'error': 'File not found'}
        try:
            os.remove(full)
        except Exception as exc:
            return {'deleted': False, 'error': str(exc)}
        return {'deleted': True}

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
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

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
        workers=1,
    )
    server = Server(config)

    logger.info(
        'Starting Downtify %s on http://%s:%s',
        __version__,
        args.host,
        args.port,
    )
    loop.run_until_complete(server.serve())


if __name__ == '__main__':
    main()
