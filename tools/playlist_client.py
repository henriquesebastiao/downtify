"""Interactive client for exercising the mobile playlist API.

Run: python tools/playlist_client.py [server-url]
Use a paired device token when prompted. Type help for commands.
"""

import cmd
import json
import shlex
import sys
import urllib.error
import urllib.request
import uuid


class PlaylistClient(cmd.Cmd):
    intro = 'Connected. Type help for commands; quit to exit.'
    prompt = 'playlist> '

    def __init__(self, base, token):
        super().__init__()
        self.base = base.rstrip('/')
        self.token = token

    def request(self, method, path, payload=None):
        headers = {'Authorization': f'Bearer {self.token}'}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(
            self.base + path, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.load(response)
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result
        except urllib.error.HTTPError as exc:
            print(f'HTTP {exc.code}: {exc.read().decode(errors="replace")}')
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f'Connection failed: {exc}')

    def do_info(self, arg):
        "info: show server capabilities."
        self.request('GET', '/api/server/info')

    def do_library(self, arg):
        "library: list track IDs available to your account."
        self.request('GET', '/api/v1/library')

    def do_list(self, arg):
        "list: list accessible playlists and their track IDs."
        self.request('GET', '/api/v1/playlists')

    def do_smoke(self, arg):
        "smoke [TRACK_ID]: create a playlist, add a track and remove it."
        track_id = arg.strip()
        if not track_id:
            library = self.request('GET', '/api/v1/library')
            if library is None:
                return
            tracks = library.get('tracks', [])
            if not tracks:
                print('No accessible tracks found; supply a track ID.')
                return
            track_id = tracks[0]['id']
        name = 'API smoke ' + uuid.uuid4().hex[:12]
        created = self.request('POST', '/api/v1/playlists', {'name': name})
        if created is None:
            return
        name = created['name']
        print(f'Test playlist: {name} (delete it in the web interface)')
        added = self.request(
            'POST',
            '/api/v1/playlists/tracks',
            {
                'name': name,
                'add': [track_id],
            },
        )
        if added is None:
            return
        if track_id not in added.get('track_ids', []):
            print('Add did not return the requested track; stopping.')
            return
        removed = self.request(
            'POST',
            '/api/v1/playlists/tracks',
            {
                'name': name,
                'remove': [track_id],
            },
        )
        if removed is not None and track_id not in removed.get(
            'track_ids', []
        ):
            print('Smoke test passed: track added and removed.')
        elif removed is not None:
            print('Smoke test failed: track remains in the playlist.')

    def do_create(self, arg):
        "create NAME: create a manual playlist (quote names with spaces)."
        self._write(
            'POST', '/api/v1/playlists', arg, 1, lambda a: {'name': a[0]}
        )

    def do_rename(self, arg):
        "rename NAME NEW_NAME: rename a manual playlist."
        self._write(
            'POST',
            '/api/v1/playlists/rename',
            arg,
            2,
            lambda a: {'name': a[0], 'new_name': a[1]},
        )

    def do_add(self, arg):
        "add NAME TRACK_ID [TRACK_ID ...]: append tracks; duplicates allowed."
        self._write(
            'POST',
            '/api/v1/playlists/tracks',
            arg,
            2,
            lambda a: {'name': a[0], 'add': a[1:], 'allow_duplicates': True},
            minimum=True,
        )

    def do_remove(self, arg):
        "remove NAME TRACK_ID [TRACK_ID ...]: remove all copies of tracks."
        self._write(
            'POST',
            '/api/v1/playlists/tracks',
            arg,
            2,
            lambda a: {'name': a[0], 'remove': a[1:]},
            minimum=True,
        )

    def do_remove_entry(self, arg):
        "remove_entry NAME TRACK_ID OCCURRENCE: remove one zero-based copy."
        try:
            args = shlex.split(arg)
            if len(args) != 3 or int(args[2]) < 0:  # noqa: PLR2004
                raise ValueError('expected NAME TRACK_ID OCCURRENCE')
            occurrence = int(args[2])
        except ValueError as exc:
            print(f'Invalid arguments: {exc}')
            return
        self.request(
            'POST',
            '/api/v1/playlists/tracks',
            {
                'name': args[0],
                'remove_entries': [
                    {'track_id': args[1], 'occurrence': occurrence}
                ],
            },
        )

    def do_order(self, arg):
        "order NAME [TRACK_ID ...]: provide the complete desired track order."
        self._write(
            'PUT',
            '/api/v1/playlists/order',
            arg,
            1,
            lambda a: {'name': a[0], 'track_ids': a[1:]},
            minimum=True,
        )

    def _write(self, method, path, arg, count, payload, minimum=False):  # noqa: PLR0913, PLR0917
        try:
            args = shlex.split(arg)
        except ValueError as exc:
            print(f'Invalid arguments: {exc}')
            return
        if len(args) < count or (not minimum and len(args) != count):
            print('Invalid arguments. Type help for command usage.')
            return
        self.request(method, path, payload(args))

    def do_quit(self, arg):  # noqa: PLR6301
        "quit: exit the client."
        return True

    do_EOF = do_quit


def authenticate(server, credential):
    """Exchange a pairing code for a device token when needed."""
    if credential.startswith('dtfy_'):
        return credential
    body = json.dumps({
        'code': credential,
        'device_name': 'Playlist test client',
        'platform': 'other',
    }).encode()
    request = urllib.request.Request(
        server.rstrip('/') + '/api/auth/pair',
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)['token']
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors='replace')
        sys.exit(f'Pairing failed (HTTP {exc.code}): {detail}')
    except (urllib.error.URLError, TimeoutError, KeyError) as exc:
        sys.exit(f'Pairing failed: {exc}')


if __name__ == '__main__':
    server = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000'
    credential = input('Device token or pairing code: ').strip()
    if not credential:
        sys.exit('A device token or pairing code is required.')
    token = authenticate(server, credential)
    PlaylistClient(server, token).cmdloop()
