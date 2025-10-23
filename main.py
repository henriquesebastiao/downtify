import asyncio
import logging
import os
import sys
from pathlib import Path

import requests
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

from playlist_monitor import PlaylistMonitor

load_dotenv()

__version__ = '1.1.0'
logger = logging.getLogger(__name__)
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', '/downloads'))
WEB_GUI_LOCATION = os.getenv('WEB_GUI_LOCATION', '/downtify/frontend/dist')
MONITOR_INTERVAL = int(os.getenv('MONITOR_INTERVAL', '3600'))  # 1 hour
MONITOR_STORAGE = Path(
    os.getenv('MONITOR_STORAGE', '/downloads/.monitored_playlists.json')
)


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

    @app_state.api.post('/monitor/add')
    async def add_monitored_playlist(playlist_url: str):
        """Add a playlist to monitoring and trigger immediate check."""
        monitor = getattr(app_state, 'playlist_monitor', None)
        if monitor is None:
            return {
                'success': False,
                'message': 'Playlist monitoring not initialized',
            }

        result = monitor.add_playlist(playlist_url)

        # If successfully added, trigger an immediate check to start downloading
        if result.get('success'):
            try:
                # Run check in background without waiting
                asyncio.create_task(monitor.check_all_playlists())
                logger.info('Triggered check for newly added playlist')
            except Exception as e:
                logger.error(f'Error triggering immediate check: {e}')

        return result

    @app_state.api.delete('/monitor/remove')
    def remove_monitored_playlist(playlist_url: str):
        """Remove a playlist from monitoring."""
        monitor = getattr(app_state, 'playlist_monitor', None)
        if monitor is None:
            return {
                'success': False,
                'message': 'Playlist monitoring not initialized',
            }
        return monitor.remove_playlist(playlist_url)

    @app_state.api.get('/monitor/list')
    def list_monitored_playlists():
        """List all monitored playlists."""
        monitor = getattr(app_state, 'playlist_monitor', None)
        if monitor is None:
            return []
        return monitor.list_playlists()

    @app_state.api.post('/monitor/check')
    async def check_monitored_playlists():
        """Manually trigger a check of all monitored playlists."""
        monitor = getattr(app_state, 'playlist_monitor', None)
        if monitor is None:
            return {
                'success': False,
                'message': 'Playlist monitoring not initialized',
            }
        results = await monitor.check_all_playlists()
        return {'success': True, 'results': results}

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

    # Initialize playlist monitor
    app_state.playlist_monitor = PlaylistMonitor(
        MONITOR_STORAGE, MONITOR_INTERVAL
    )

    # Define download callback for new tracks
    async def download_new_track(track_url: str, playlist_id: str = None):
        """Download a new track detected by the monitor."""
        try:
            logger.info(
                f'Downloading new track from monitored playlist: {track_url}'
            )

            # Use the /api/download/url endpoint via HTTP request
            # This ensures proper client session management
            port = web_settings.get('port', 8000)
            host = web_settings.get('host', '127.0.0.1')
            base_url = f'http://{host}:{port}'

            # Make HTTP request in executor to avoid blocking
            def make_request():
                try:
                    response = requests.post(
                        f'{base_url}/api/download/url',
                        params={
                            'url': track_url,
                            'client_id': 'playlist_monitor',
                        },
                        timeout=10,
                    )
                    return response.status_code, response.text
                except Exception as e:
                    return None, str(e)

            status_code, response_text = await app_state.loop.run_in_executor(
                None, make_request
            )

            HTTP_OK = 200
            if status_code == HTTP_OK:
                logger.info(f'Successfully queued download for: {track_url}')
                # Mark the track as downloaded in the monitor
                if playlist_id:
                    app_state.playlist_monitor.mark_track_downloaded(
                        playlist_id, track_url
                    )
            else:
                logger.warning(
                    f'Failed to download {track_url}: '
                    f'{status_code} - {response_text}'
                )

        except Exception as e:
            logger.error(f'Error downloading new track {track_url}: {e}')

    # Start monitoring in background
    app_state.playlist_monitor.start_monitoring(
        download_callback=download_new_track
    )

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
        'CLIENT_ID', '5f573c9620494bae87890c0f08a60293'
    )
    spotify_settings['client_secret'] = os.getenv(
        'CLIENT_SECRET', '212476d9b0f3472eaa762d90b19b0ba8'
    )

    # Initialize spotify client
    SpotifyClient.init(**spotify_settings)
    spotify_client = SpotifyClient()

    # Start web ui
    web(web_settings, downloader_settings)
