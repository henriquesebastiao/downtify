"""Playlist monitoring system for Downtify."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from spotdl.types.playlist import Playlist

logger = logging.getLogger(__name__)


class PlaylistMonitor:
    """Monitor Spotify playlists for changes and trigger downloads."""

    def __init__(self, storage_path: Path, check_interval: int = 3600):
        """
        Initialize the playlist monitor.

        Args:
            storage_path: Path to store monitored playlists data
            check_interval: Interval in seconds between checks (1 hour)
        """
        self.storage_path = storage_path
        self.check_interval = check_interval
        self.monitored_playlists: dict[str, dict[str, Any]] = {}
        self._task: asyncio.Task | None = None
        self._load_monitored_playlists()

    def _load_monitored_playlists(self):
        """Load monitored playlists from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, encoding='utf-8') as f:
                    self.monitored_playlists = json.load(f)
                num_playlists = len(self.monitored_playlists)
                logger.info(f'Loaded {num_playlists} monitored playlists')
            except Exception as e:
                logger.error(f'Error loading monitored playlists: {e}')
                self.monitored_playlists = {}
        else:
            self.monitored_playlists = {}

    def _save_monitored_playlists(self):
        """Save monitored playlists to storage."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.monitored_playlists, f, indent=2)
            logger.info('Saved monitored playlists')
        except Exception as e:
            logger.error(f'Error saving monitored playlists: {e}')

    def add_playlist(self, playlist_url: str) -> dict[str, Any]:
        """
        Add a playlist to monitoring.

        Args:
            playlist_url: Spotify playlist URL

        Returns:
            Dictionary with status and playlist info
        """
        try:
            playlist = Playlist.from_url(playlist_url)
            playlist_id = playlist.url

            if playlist_id in self.monitored_playlists:
                return {
                    'success': False,
                    'message': 'Playlist already monitored',
                    'playlist_id': playlist_id,
                }

            # Get initial track list
            track_urls = playlist.urls
            self.monitored_playlists[playlist_id] = {
                'name': playlist.name,
                'url': playlist_url,
                'track_urls': track_urls,
                'added_at': datetime.now().isoformat(),
                'last_checked': None,
                'total_tracks': len(track_urls),
            }
            self._save_monitored_playlists()

            logger.info(
                f'Added playlist to monitoring: {playlist.name} '
                f'({len(track_urls)} tracks)'
            )
            return {
                'success': True,
                'message': 'Playlist added to monitoring',
                'playlist_id': playlist_id,
                'playlist_name': playlist.name,
                'total_tracks': len(track_urls),
            }
        except Exception as e:
            logger.error(f'Error adding playlist to monitoring: {e}')
            return {
                'success': False,
                'message': 'Failed to add playlist to monitoring',
            }

    def remove_playlist(self, playlist_url: str) -> dict[str, Any]:
        """
        Remove a playlist from monitoring.

        Args:
            playlist_url: Spotify playlist URL or ID

        Returns:
            Dictionary with status
        """
        # Try to match by URL or ID
        playlist_id = None
        for pid, data in self.monitored_playlists.items():
            if pid == playlist_url or data['url'] == playlist_url:
                playlist_id = pid
                break

        if playlist_id:
            playlist_name = self.monitored_playlists[playlist_id]['name']
            del self.monitored_playlists[playlist_id]
            self._save_monitored_playlists()
            logger.info(f'Removed playlist from monitoring: {playlist_name}')
            return {
                'success': True,
                'message': f'Removed playlist: {playlist_name}',
            }

        return {
            'success': False,
            'message': 'Playlist not found in monitored list',
        }

    def list_playlists(self) -> list[dict[str, Any]]:
        """
        List all monitored playlists.

        Returns:
            List of monitored playlists info
        """
        return [
            {
                'playlist_id': pid,
                'name': data['name'],
                'url': data['url'],
                'total_tracks': data['total_tracks'],
                'added_at': data['added_at'],
                'last_checked': data['last_checked'],
            }
            for pid, data in self.monitored_playlists.items()
        ]

    def check_playlist_changes(self, playlist_id: str) -> dict[str, list[str]]:
        """
        Check a playlist for changes.

        Args:
            playlist_id: Playlist ID to check

        Returns:
            Dictionary with 'new_tracks' and 'removed_tracks' lists
        """
        if playlist_id not in self.monitored_playlists:
            return {'new_tracks': [], 'removed_tracks': []}

        try:
            playlist_data = self.monitored_playlists[playlist_id]
            playlist_url = playlist_data['url']
            old_track_urls = set(playlist_data['track_urls'])

            # Fetch current playlist
            playlist = Playlist.from_url(playlist_url)
            current_track_urls = set(playlist.urls)

            # Find changes
            new_tracks = list(current_track_urls - old_track_urls)
            removed_tracks = list(old_track_urls - current_track_urls)

            # Update stored data
            self.monitored_playlists[playlist_id]['track_urls'] = list(
                current_track_urls
            )
            self.monitored_playlists[playlist_id]['total_tracks'] = len(
                current_track_urls
            )
            self.monitored_playlists[playlist_id]['last_checked'] = (
                datetime.now().isoformat()
            )
            self._save_monitored_playlists()

            if new_tracks or removed_tracks:
                logger.info(
                    f'Changes detected in {playlist_data["name"]}: '
                    f'{len(new_tracks)} new, {len(removed_tracks)} removed'
                )

            return {'new_tracks': new_tracks, 'removed_tracks': removed_tracks}
        except Exception as e:
            logger.error(f'Error checking playlist {playlist_id}: {e}')
            return {'new_tracks': [], 'removed_tracks': []}

    async def check_all_playlists(self) -> dict[str, Any]:
        """
        Check all monitored playlists for changes.

        Returns:
            Dictionary with summary of changes
        """
        logger.info('Checking all monitored playlists...')
        results = {}
        total_new = 0
        total_removed = 0

        for playlist_id in list(self.monitored_playlists.keys()):
            changes = self.check_playlist_changes(playlist_id)
            if changes['new_tracks'] or changes['removed_tracks']:
                results[playlist_id] = changes
                total_new += len(changes['new_tracks'])
                total_removed += len(changes['removed_tracks'])

        logger.info(
            f'Check complete: {total_new} new tracks, '
            f'{total_removed} removed tracks across '
            f'{len(results)} playlists'
        )
        return {
            'checked_at': datetime.now().isoformat(),
            'playlists_changed': len(results),
            'total_new_tracks': total_new,
            'total_removed_tracks': total_removed,
            'changes': results,
        }

    async def _monitoring_loop(self, download_callback=None):
        """
        Background task that periodically checks playlists.

        Args:
            download_callback: Optional async function to call for new tracks
        """
        logger.info(
            f'Starting playlist monitoring loop '
            f'(interval: {self.check_interval}s)'
        )
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                results = await self.check_all_playlists()

                # Trigger downloads for new tracks if callback provided
                if download_callback and results['total_new_tracks'] > 0:
                    await self._process_new_tracks(
                        results['changes'], download_callback
                    )
            except asyncio.CancelledError:
                logger.info('Monitoring loop cancelled')
                break
            except Exception as e:
                logger.error(f'Error in monitoring loop: {e}')

    @staticmethod
    async def _process_new_tracks(changes, download_callback):
        """Process new tracks and trigger downloads."""
        for playlist_id, change_data in changes.items():
            for track_url in change_data['new_tracks']:
                try:
                    await download_callback(track_url)
                except Exception as e:
                    logger.error(f'Error downloading track {track_url}: {e}')

    def start_monitoring(self, download_callback=None):
        """
        Start the background monitoring task.

        Args:
            download_callback: Optional async function to call for new tracks
        """
        if self._task is None or self._task.done():
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(
                self._monitoring_loop(download_callback)
            )
            logger.info('Playlist monitoring started')
        else:
            logger.warning('Monitoring task already running')

    def stop_monitoring(self):
        """Stop the background monitoring task."""
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info('Playlist monitoring stopped')
        else:
            logger.warning('No monitoring task to stop')
