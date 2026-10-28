from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from downtify import admin_access


@pytest.mark.parametrize(
    ('kind', 'role'),
    [('signed', 'admin'), ('device', 'user'), ('session', 'user')],
)
def test_sensitive_mutation_revalidates_admin(monkeypatch, kind, role):
    principal = SimpleNamespace(kind=kind, is_admin=True, user_id=1)
    monkeypatch.setattr(
        admin_access.api, 'principal_of', lambda _request: principal
    )
    auth = SimpleNamespace(
        users=SimpleNamespace(get=Mock(return_value={'role': role}))
    )
    monkeypatch.setattr(admin_access.api.state, 'auth', auth)
    with pytest.raises(HTTPException) as error:
        admin_access.admin_user(Mock())
    assert error.value.status_code == 403


@pytest.mark.parametrize('kind', ['session', 'device'])
def test_valid_administrators_can_mutate(monkeypatch, kind):
    principal = SimpleNamespace(kind=kind, is_admin=True, user_id=1)
    monkeypatch.setattr(
        admin_access.api, 'principal_of', lambda _request: principal
    )
    auth = SimpleNamespace(
        users=SimpleNamespace(get=Mock(return_value={'role': 'admin'}))
    )
    monkeypatch.setattr(admin_access.api.state, 'auth', auth)
    assert admin_access.admin_user(Mock()) == 1
