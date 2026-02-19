import asyncio
import logging
import os
import sys
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from load_dotenv import load_dotenv
from spotdl.types.options import DownloaderOptions, WebOptions
from spotdl.utils.arguments import parse_arguments
from spotdl.utils.config import create_settings
from spotdl.utils.logging import NAME_TO_LEVEL
from spotdl.utils.spotify import SpotifyClient
from spotdl.utils.web import (
    ALLOWED_ORIGINS,
    SPAStaticFiles,
    app_state,
    fix_mime_types,
    get_current_state,
    router,
)
from uvicorn import Config, Server

load_dotenv()

__version__ = '1.1.4'
logger = logging.getLogger(__name__)
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', '/downloads'))
WEB_GUI_LOCATION = os.getenv('WEB_GUI_LOCATION', '/downtify/frontend/dist')


def web(web_settings: WebOptions, downloader_settings: DownloaderOptions):
    """
    Run the web server.

    ### Arguments
    - web_settings: Web server settings.
    - downloader_settings: Downloader settings.
    """

    # Apply the fix for mime types
    fix_mime_types()

    # Set up the app loggers
    uvicorn_logger = logging.getLogger('uvicorn')
    uvicorn_logger.propagate = False

    spotipy_logger = logging.getLogger('spotipy')
    spotipy_logger.setLevel(logging.NOTSET)

    # Initialize the web server settings
    app_state.web_settings = web_settings
    app_state.logger = uvicorn_logger

    # Create the event loop
    app_state.loop = (
        asyncio.new_event_loop()
        if sys.platform != 'win32'
        else asyncio.ProactorEventLoop()  # type: ignore
    )

    downloader_settings['simple_tui'] = True
    web_settings['web_gui_location'] = WEB_GUI_LOCATION

    # Download web app from GitHub if not already downloaded or force flag set
    web_app_dir = WEB_GUI_LOCATION

    app_state.api = FastAPI(
        title='Downtify',
        description='Download your Spotify playlists and songs along with album art and metadata in a self-hosted way via Docker.',
        version=__version__,
        dependencies=[Depends(get_current_state)],
    )

    app_state.api.include_router(router)

    @app_state.api.get('/list')
    def list_downloads():
        downloads_dir = str(DOWNLOAD_DIR)
        audio_exts = {'.mp3', '.m4a', '.flac', '.ogg', '.wav', '.aac', '.opus'}
        try:
            entries = os.listdir(downloads_dir)
        except FileNotFoundError:
            return []

        files: list[str] = []
        for entry in entries:
            full_path = os.path.join(downloads_dir, entry)
            if os.path.isfile(full_path):
                _, ext = os.path.splitext(entry)
                if ext.lower() in audio_exts:
                    files.append(entry)

        files.sort()
        return files

    @app_state.api.delete('/delete')
    def delete_download(file: str):
        downloads_dir = str(DOWNLOAD_DIR)
        full_path = os.path.join(downloads_dir, file)
        if not os.path.isfile(full_path):
            return {'deleted': False, 'error': 'File not found'}
        try:
            os.remove(full_path)
        except Exception as e:
            return {'deleted': False, 'error': str(e)}
        return {'deleted': True}

    # Add the CORS middleware
    app_state.api.add_middleware(
        CORSMiddleware,
        allow_origins=(
            ALLOWED_ORIGINS + web_settings['allowed_origins']
            if web_settings['allowed_origins']
            else ALLOWED_ORIGINS
        ),
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    # Expose downloads as static files for direct links
    app_state.api.mount(
        '/downloads',
        StaticFiles(directory=str(DOWNLOAD_DIR)),
        name='downloads',
    )

    # Add the static files for the SPA (must be mounted after /downloads)
    app_state.api.mount(
        '/',
        SPAStaticFiles(directory=web_app_dir, html=True),
        name='static',
    )
    config = Config(
        app=app_state.api,
        host=web_settings['host'],
        port=web_settings['port'],
        workers=1,
        log_level=NAME_TO_LEVEL[downloader_settings['log_level']],
        loop=app_state.loop,  # type: ignore
    )
    if web_settings['enable_tls']:
        logger.info('Enabling TLS')
        config.ssl_certfile = web_settings['cert_file']
        config.ssl_keyfile = web_settings['key_file']
        config.ssl_ca_certs = web_settings['ca_file']

    app_state.server = Server(config)

    app_state.downloader_settings = downloader_settings

    if not web_settings['web_use_output_dir']:
        logger.info(
            'Files are stored in temporary directory '
            'and will be deleted after the program exits '
            'to save them to current directory permanently '
            'enable the `web_use_output_dir` option '
        )
    else:
        logger.info(
            'Files are stored in current directory '
            'to save them to temporary directory '
            'disable the `web_use_output_dir` option '
        )

    logger.info('Starting web server \n')

    # Start the web server
    app_state.loop.run_until_complete(app_state.server.serve())


if __name__ == '__main__':
    _KEY = b'\x4f\x2a\x91\x3c'

    _ID_ENC = b'}\x1c\xa2\r\x7f\x13\xf4_z\x1a\xa5Z{N\xf5\x0fvL\xf4ZyN\xa8Y|N\xa3^|\x18\xa7]'  # Client ID
    _SEC_ENC = b'}\x1a\xf0\x0e}\x1b\xf5_)\x1f\xa4^{\x13\xf0^-L\xf2Zw\x1e\xa7Y}N\xf7\x0f}\x1a\xa3\n'  # Client Secret

    def _decode(data: bytes, key: bytes) -> str:
        return bytes(
            b ^ key[i % len(key)] for i, b in enumerate(data)
        ).decode()

    # Parse the arguments
    arguments = parse_arguments()

    # Create settings dicts
    spotify_settings, downloader_settings, web_settings = create_settings(
        arguments
    )

    web_settings['web_use_output_dir'] = True
    downloader_settings['output'] = str(
        DOWNLOAD_DIR / '{artists} - {title}.{output-ext}'
    )
    spotify_settings['client_id'] = os.getenv(
        'CLIENT_ID', _decode(_ID_ENC, _KEY)
    )
    spotify_settings['client_secret'] = os.getenv(
        'CLIENT_SECRET', _decode(_SEC_ENC, _KEY)
    )

    # Initialize spotify client
    SpotifyClient.init(**spotify_settings)
    spotify_client = SpotifyClient()

    # Start web ui
    web(web_settings, downloader_settings)
