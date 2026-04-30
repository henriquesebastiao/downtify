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
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from load_dotenv import load_dotenv
from loguru import logger
from mutagen import File as MutagenFile
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from uvicorn import Config, Server

from downtify import __version__, api
from downtify.downloader import Downloader
from downtify.monitor import PlaylistMonitorDB, monitor_loop

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
DATABASE_DIR = Path('/data')
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
    """Return ``(image_bytes, mime)`` for the embedded cover, or ``(None, None)``.

    Reads tags lazily — mutagen format detection handles MP3/FLAC/M4A/OGG/Opus
    without us needing to dispatch on extension.
    """

    try:
        # ID3 (mp3, sometimes wav/aac)
        try:
            tag = ID3(str(path))
            for frame in tag.getall('APIC'):
                if frame.data:
                    return frame.data, frame.mime or 'image/jpeg'
        except Exception:
            pass

        # FLAC
        if path.suffix.lower() == '.flac':
            try:
                f = FLAC(str(path))
                if f.pictures:
                    pic = f.pictures[0]
                    return pic.data, pic.mime or 'image/jpeg'
            except Exception:
                pass

        # MP4 / M4A
        if path.suffix.lower() in {'.m4a', '.mp4', '.aac'}:
            try:
                m = MP4(str(path))
                covr = m.tags.get('covr') if m.tags else None
                if covr:
                    pic = covr[0]
                    fmt = getattr(pic, 'imageformat', None)
                    mime = (
                        'image/png'
                        if fmt == 14  # MP4Cover.FORMAT_PNG
                        else 'image/jpeg'
                    )
                    return bytes(pic), mime
            except Exception:
                pass

        # Ogg Vorbis / Opus — METADATA_BLOCK_PICTURE base64
        if path.suffix.lower() in {'.ogg', '.opus'}:
            try:
                ogg = (
                    OggOpus(str(path))
                    if path.suffix.lower() == '.opus'
                    else OggVorbis(str(path))
                )
                blocks = ogg.get('metadata_block_picture') or []
                for raw in blocks:
                    try:
                        pic = Picture(base64.b64decode(raw))
                        if pic.data:
                            return pic.data, pic.mime or 'image/jpeg'
                    except Exception:
                        continue
            except Exception:
                pass

        # Generic fallback — let mutagen pick the right parser
        try:
            f = MutagenFile(str(path))
            if f is not None and getattr(f, 'pictures', None):
                pic = f.pictures[0]
                return pic.data, pic.mime or 'image/jpeg'
        except Exception:
            pass
    except Exception:
        return None, None
    return None, None


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
        lyrics_providers=api.state.settings.get('lyrics_providers') or [],
    )
    app.include_router(api.router)

    @app.on_event('startup')
    async def _startup() -> None:
        loop = asyncio.get_running_loop()
        api.state.loop = loop
        db_path = DATABASE_DIR / 'downtify_monitor.db'
        api.state.monitor_db = PlaylistMonitorDB(db_path)
        asyncio.create_task(
            monitor_loop(
                db=api.state.monitor_db,
                get_downloader=lambda: api.state.downloader,
                broadcast=api.state.connections.broadcast,
                loop=loop,
                settings=api.state.settings,
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

    @app.get('/cover')
    def get_cover(file: str):
        # Resolve and confine to DOWNLOAD_DIR to prevent path traversal.
        base = DOWNLOAD_DIR.resolve()
        try:
            full = (base / file).resolve()
            full.relative_to(base)
        except (ValueError, RuntimeError):
            raise HTTPException(status_code=400, detail='Invalid path')
        if not full.is_file():
            raise HTTPException(status_code=404, detail='File not found')

        data, mime = _extract_cover(full)
        if data is None:
            raise HTTPException(status_code=404, detail='No embedded cover')
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
    loop.run_until_complete(server.serve())


if __name__ == '__main__':
    main()
