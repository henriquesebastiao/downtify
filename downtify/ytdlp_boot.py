"""Load the yt-dlp that Settings > YouTube installed, before anything
imports yt-dlp.

``main.py`` imports this module first (``import downtify.ytdlp_boot``),
ahead of every module that does ``import yt_dlp``. When "Update yt-dlp
by itself" is on and a tested version is saved under
``<data>/yt-dlp/<version>/``, that folder goes to the front of
``sys.path``, so the saved copy wins over the one in the image.

If the saved copy can't be imported, or reports a different version
than its folder name, it is taken off ``sys.path`` again, the half
imported modules are dropped, and the image's yt-dlp is used. The
reason is kept in :data:`BOOT` so Settings can show it and the updater
can go back to the previous version.

Only the standard library is used here: anything heavier might pull in
yt-dlp itself before the path is set.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

#: The settings and state file, next to settings.json.
STATE_FILE = 'ytdlp.json'
#: Folder holding one sub-folder per installed version.
VERSIONS_DIR = 'yt-dlp'

_VERSION_RE = re.compile(r'^\d{4}\.\d{1,2}\.\d{1,2}(?:\.\d+)?$')

#: What happened at start: ``source`` is ``image`` or ``saved``;
#: ``version`` the yt-dlp in use; ``error`` why a saved copy wasn't used.
BOOT: dict[str, Any] = {
    'source': 'image',
    'version': None,
    'path': None,
    'error': None,
    'wanted': None,
}


def data_dir() -> Path:
    return Path(os.getenv('DATABASE_DIR') or '/data')


def valid_version(value: Any) -> bool:
    return isinstance(value, str) and bool(_VERSION_RE.match(value))


def version_dir(base: Path, version: str) -> Path:
    return Path(base) / VERSIONS_DIR / version


def read_state(base: Path) -> dict[str, Any]:
    try:
        raw = json.loads((Path(base) / STATE_FILE).read_text('utf-8'))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _forget_modules() -> None:
    for name in list(sys.modules):
        if name == 'yt_dlp' or name.startswith('yt_dlp.'):
            del sys.modules[name]


def _import_version() -> Optional[str]:
    import yt_dlp.version  # noqa: PLC0415

    return str(yt_dlp.version.__version__)


def activate(base: Optional[Path] = None) -> dict[str, Any]:
    """Put the saved yt-dlp first on ``sys.path`` when it is switched on
    and loads; otherwise leave the image's. Returns :data:`BOOT`."""

    base = Path(base) if base is not None else data_dir()
    state = read_state(base)
    wanted = state.get('active')
    BOOT.update(source='image', path=None, error=None, wanted=None)
    if state.get('enabled') is True and valid_version(wanted):
        BOOT['wanted'] = wanted
        folder = version_dir(base, wanted)
        if (folder / 'yt_dlp' / '__init__.py').is_file():
            sys.path.insert(0, str(folder))
            _forget_modules()
            try:
                loaded = _import_version()
            except Exception as exc:  # a broken copy must never stop start
                loaded = None
                BOOT['error'] = f'{type(exc).__name__}: {exc}'[:300]
            if loaded == wanted:
                BOOT.update(source='saved', version=loaded, path=str(folder))
                return BOOT
            if loaded is not None:
                BOOT['error'] = f'the folder holds yt-dlp {loaded}'
            try:
                sys.path.remove(str(folder))
            except ValueError:
                pass
            _forget_modules()
        else:
            BOOT['error'] = 'the saved copy is missing'
    try:
        BOOT['version'] = _import_version()
    except Exception:
        BOOT['version'] = None
    return BOOT


def _load_dotenv() -> None:
    """``DATABASE_DIR`` may come from a ``.env`` file (non-Docker runs);
    ``main.py`` loads it later too, which is harmless."""

    try:
        from load_dotenv import load_dotenv  # noqa: PLC0415

        load_dotenv()
    except Exception:
        pass


# Only before anything imported yt-dlp: later, swapping it would leave
# modules holding the old one (and nothing would gain from it).
if (
    os.getenv('DOWNTIFY_YTDLP_BOOT', '1') != '0'
    and 'yt_dlp' not in sys.modules
):
    _load_dotenv()
    activate()
