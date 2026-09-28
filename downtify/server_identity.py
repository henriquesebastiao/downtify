"""Who this Downtify server is, for the apps that connect to it.

A client (the Android app) tells servers apart, and recognises one it has
paired with before, by a **server ID**: a random value made once and kept
in ``/data/server.json``, so it survives restarts, upgrades and a changed
address. The file also holds the **server name** people see in the app's
server list and in LAN discovery - editable in Settings > Apps, and the
machine's hostname until someone changes it - and the port chosen in
Settings > Server, if any (see :mod:`downtify.server_port`).

:func:`server_info` is what ``GET /api/server/info`` returns. That route
is public even when sign-in is required (an app must be able to check an
address before it has any credentials), so it says nothing more than an
app needs to decide how to talk to the server.
"""

from __future__ import annotations

import json
import os
import secrets
import socket
import tempfile
import threading
from pathlib import Path
from typing import Any, Optional

#: The version of the ``/api/v1`` surface mobile clients use. Bump it only
#: for a change that would break an app built against the previous one;
#: additions (new fields, new endpoints) keep it.
API_VERSION = 1

#: Longest server name accepted, in characters.
MAX_NAME_LENGTH = 64

_FILE_NAME = 'server.json'


def _default_name() -> str:
    try:
        name = socket.gethostname().strip()
    except OSError:
        name = ''
    return (name or 'Downtify')[:MAX_NAME_LENGTH]


def clean_name(value: Any) -> str:
    """*value* as a server name: trimmed, one line, at most
    :data:`MAX_NAME_LENGTH` characters. ``''`` when nothing is left."""

    text = ' '.join(str(value or '').split())
    return text[:MAX_NAME_LENGTH]


class ServerIdentity:
    """The server's ID and name, persisted in ``<data>/server.json``."""

    def __init__(self, data_dir: Path) -> None:
        self._path = Path(data_dir) / _FILE_NAME
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self._path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        changed = False
        server_id = str(data.get('server_id') or '')
        if len(server_id) < 16:
            server_id = secrets.token_hex(16)
            changed = True
        name = clean_name(data.get('name'))
        if not name:
            name = _default_name()
            changed = True
        result: dict[str, Any] = {'server_id': server_id, 'name': name}
        port = data.get('port')
        if isinstance(port, int) and not isinstance(port, bool) and port > 0:
            result['port'] = port
        if changed:
            self._write(result)
        return result

    def _write(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            dir=self._path.parent, prefix='.server.', suffix='.json'
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump(data, handle)
            os.replace(tmp, self._path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    @property
    def server_id(self) -> str:
        return self._data['server_id']

    @property
    def name(self) -> str:
        return self._data['name']

    @property
    def port(self) -> Optional[int]:
        """The port chosen in Settings > Server, or ``None``."""

        return self._data.get('port')

    def set_port(self, port: int) -> None:
        with self._lock:
            data = {**self._data, 'port': int(port)}
            self._write(data)
            self._data = data

    def set_name(self, value: Any) -> str:
        """Rename the server. Raises :class:`ValueError` for an empty name."""

        name = clean_name(value)
        if not name:
            raise ValueError('The server name cannot be empty')
        with self._lock:
            data = {**self._data, 'name': name}
            self._write(data)
            self._data = data
        return name


def server_info(
    identity: ServerIdentity,
    *,
    version: str,
    require_sign_in: bool,
    transcoding: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """The public description of this server (``GET /api/server/info``).

    *transcoding* is :meth:`downtify.transcode.Transcoder.capability`, or
    ``None`` when ffmpeg isn't available - the app then only offers
    original quality.
    """

    return {
        'server_id': identity.server_id,
        'name': identity.name,
        'product': 'Downtify',
        'version': version,
        'api_version': API_VERSION,
        'require_sign_in': require_sign_in,
        'capabilities': {
            'transcoding': transcoding
            or {'available': False, 'formats': [], 'bitrates': []},
            'signed_urls': True,
            'pairing': True,
            'podcasts': True,
            'discover': True,
            'lyrics': True,
            'library_sync': True,
        },
    }
