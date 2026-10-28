"""Revalidate administrator privileges for sensitive mutations."""

from fastapi import HTTPException, Request

from . import api


def admin_user(request: Request) -> int:
    principal = api.principal_of(request)
    if (
        principal is None
        or principal.kind not in {'session', 'device'}
        or not principal.is_admin
        or not principal.user_id
    ):
        raise HTTPException(403, detail={'code': 'admin_required'})
    auth = api.state.auth
    user = auth.users.get(principal.user_id) if auth else None
    if user is None or user.get('role') != 'admin':
        raise HTTPException(403, detail={'code': 'admin_required'})
    return principal.user_id
