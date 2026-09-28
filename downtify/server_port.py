"""Which port the server listens on, and changing it from Settings.

The port comes from, in order: ``--port`` on the command line, the
``DOWNTIFY_PORT`` (or ``PORT``) environment variable, the port saved in
Settings > Server (``port`` in ``<data>/server.json``), and ``8000``. The
first two can't be changed from Settings - the page says which one set it.

A new port applies when the server starts. Settings can also restart it
right away (:func:`request_restart`): ``main.py`` stops the server
gracefully and starts itself again in the same process, so Docker (tini)
and systemd see the same process carry on.

In Docker's default *bridge* network the container's port has to match
the ``ports:`` mapping: changing it from Settings without changing the
mapping (and recreating the container) makes Downtify unreachable. Setting
``DOWNTIFY_PORT`` puts things back, since it wins over Settings.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import Any, Callable, Optional

DEFAULT_PORT = 8000
#: Ports Settings accepts. Below 1024 needs root, which the image drops.
MIN_PORT = 1024
MAX_PORT = 65535
#: Where the port the server listens on is written, for healthcheck.sh.
RUNTIME_FILE = Path('/tmp/downtify.port')

_ENV_VARS = ('DOWNTIFY_PORT', 'PORT')


class PortError(ValueError):
    """A port Settings can't use; the message says why."""


def clean_port(value: Any) -> int:
    """*value* as a port Settings accepts, or :class:`PortError`."""

    try:
        port = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise PortError('The port must be a number') from exc
    if not MIN_PORT <= port <= MAX_PORT:
        raise PortError(f'Use a port from {MIN_PORT} to {MAX_PORT}')
    return port


def _env_port(environ: Any) -> tuple[Optional[int], str]:
    for name in _ENV_VARS:
        raw = str(environ.get(name, '') or '').strip()
        if raw:
            try:
                return int(raw), name
            except ValueError:
                continue
    return None, ''


def resolve_port(
    cli_port: Optional[int],
    saved_port: Optional[int],
    environ: Any = None,
) -> tuple[int, str]:
    """``(port, source)``: the port to listen on and what chose it -
    ``--port``, ``DOWNTIFY_PORT``/``PORT``, ``settings`` or ``default``."""

    if cli_port:
        return int(cli_port), '--port'
    env_port, env_name = _env_port(os.environ if environ is None else environ)
    if env_port:
        return env_port, env_name
    if saved_port:
        return int(saved_port), 'settings'
    return DEFAULT_PORT, 'default'


def locked_by(source: str) -> str:
    """What stops Settings from choosing the port (``''`` when nothing)."""

    return '' if source in {'settings', 'default'} else source


def port_available(host: str, port: int) -> bool:
    """Whether *port* can be listened on at *host* right now."""

    family = socket.AF_INET6 if ':' in (host or '') else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host or '0.0.0.0', port))
        except OSError:
            return False
    return True


def in_docker() -> bool:
    return Path('/.dockerenv').exists()


def write_runtime_port(port: int, path: Path = RUNTIME_FILE) -> None:
    """Note the port the server listens on, for healthcheck.sh."""

    try:
        path.write_text(str(port), encoding='utf-8')
    except OSError:
        pass


# ── Restarting ──────────────────────────────────────────────────────────

_restart: dict[str, Any] = {'handler': None, 'wanted': False}


def set_restart_handler(handler: Optional[Callable[[], None]]) -> None:
    """What stops the running server so ``main.py`` can start it again."""

    _restart['handler'] = handler


def can_restart() -> bool:
    return _restart['handler'] is not None


def request_restart() -> bool:
    """Ask for a restart; whether one will happen."""

    handler = _restart['handler']
    if handler is None:
        return False
    _restart['wanted'] = True
    handler()
    return True


def restart_wanted() -> bool:
    return bool(_restart['wanted'])
