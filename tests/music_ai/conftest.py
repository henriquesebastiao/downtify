import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_api import client  # noqa: E402
from test_dj_store import database  # noqa: E402

__all__ = ['client', 'database']
