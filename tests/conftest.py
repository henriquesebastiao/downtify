from __future__ import annotations

import os
import uuid

import psycopg
import pytest
import requests

from downtify import cookie_refresh, slskd_provider
from downtify import downloader as downloader_mod
from downtify.db.core import Database
from downtify.db.migrations.runner import run_migrations


@pytest.fixture(autouse=True)
def _offline_metadata_lookups(monkeypatch):
    """Keep tests off the network: ``Downloader.download()`` starts the
    iTunes genre, cover-art and ISRC lookups alongside yt-dlp, so even a
    test whose fake YoutubeDL aborts the download would otherwise fire
    real HTTP requests (and ``embed_metadata`` fetches the cover too).
    Tests that exercise these lookups override them with their own
    fakes."""

    monkeypatch.setattr(downloader_mod, '_fetch_itunes_genre', lambda s: '')
    monkeypatch.setattr(downloader_mod, '_download_cover', lambda url: None)
    monkeypatch.setattr(downloader_mod.isrc_mod, 'lookup', lambda song: None)
    # Every download below the cover size goal asks the cover sources for
    # a larger cover (downloader.cover_goal).
    monkeypatch.setattr(
        downloader_mod.cover_sources, '_source_url', lambda *a, **k: ''
    )


@pytest.fixture(autouse=True)
def _no_remembered_slskd_failures():
    """slskd candidates that failed are remembered process-wide
    (``slskd_provider.remember_failure``): each test starts with none."""

    slskd_provider.forget_failures()
    yield
    slskd_provider.forget_failures()


@pytest.fixture(autouse=True)
def _offline_cookie_keepalive(monkeypatch):
    """An uploaded cookies.txt starts a keep-alive pass in the background
    (``downtify/cookie_refresh.py``); without this it would call YouTube.
    Tests of the keep-alive install their own fake session."""

    def _refuse(*_args, **_kwargs):
        raise requests.ConnectionError('tests run offline')

    def _offline_session() -> requests.Session:
        session = requests.Session()
        session.request = _refuse
        return session

    monkeypatch.setattr(cookie_refresh, '_new_session', _offline_session)


@pytest.fixture(scope='session')
def pg_url():
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        pytest.skip('TEST_DATABASE_URL not set')
    return url


@pytest.fixture
def pg_db(pg_url):
    """A migrated PostgreSQL ``Database`` in a schema unique to this test.

    The schema is dropped afterwards, with CASCADE, so no test sees another
    test's rows.
    """
    schema = f'sc_{uuid.uuid4().hex[:8]}'
    with psycopg.connect(pg_url, autocommit=True) as admin:
        admin.execute(f'create schema {schema}')
    database = Database.postgres(pg_url, search_path=schema, max_size=4)
    try:
        run_migrations(database)
        yield database
    finally:
        database.close()
        with psycopg.connect(pg_url, autocommit=True) as admin:
            admin.execute(f'drop schema if exists {schema} cascade')


@pytest.fixture
def sqlite_db(tmp_path):
    """A SQLite ``Database`` in a temporary file. Stores create their own
    tables on SQLite, so no migrations run here."""
    database = Database.sqlite(tmp_path / 'test.db')
    try:
        yield database
    finally:
        database.close()


@pytest.fixture(params=['sqlite', 'postgres'])
def backend_db(request):
    """Run a test once per backend. The postgres case skips unless
    ``TEST_DATABASE_URL`` is set."""
    fixture_name = {'sqlite': 'sqlite_db', 'postgres': 'pg_db'}[request.param]
    return request.getfixturevalue(fixture_name)
