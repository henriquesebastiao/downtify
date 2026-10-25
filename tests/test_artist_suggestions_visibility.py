"""History suggestions obey the same artist visibility as the library."""

from types import SimpleNamespace

import pytest

from downtify import api
from tests.test_artist_suggestions import listen, request


@pytest.mark.parametrize('admin', [False, True])
def test_hidden_artists_do_not_leak_from_personal_history(monkeypatch, admin):
    monkeypatch.setattr(
        api,
        '_require_discover',
        lambda: SimpleNamespace(
            listens=lambda uid: [listen('Hidden', 10), listen('Visible', 3)]
        ),
    )
    monkeypatch.setattr(
        api,
        '_require_monitor_db',
        lambda: SimpleNamespace(list_playlists=lambda uid: []),
    )
    monkeypatch.setattr(api, 'library_context', lambda: None)
    monkeypatch.setattr(api, 'allowed_entry_keys', lambda req: None)
    monkeypatch.setattr(api, 'admin_hidden_rules', lambda req: None)
    monkeypatch.setattr(api, 'library_artist_index', lambda *a, **kw: [])
    monkeypatch.setattr(
        api,
        'hidden_rules',
        lambda: SimpleNamespace(artist_hidden=lambda name: name == 'Hidden'),
    )
    out = api.monitor_artist_suggestions(request(admin=admin), 0, 0, 20)
    assert [row['name'] for row in out['listening']['items']] == (
        ['Hidden', 'Visible'] if admin else ['Visible']
    )
