"""Routes of the Doctor's AI helper (:mod:`downtify.doctor_ai`).

``/api/doctor/ai/...`` is the page's side, admin-only: start and stop
the helper, the "may apply from the chat" switch, and the suggestions
with Apply / Dismiss. ``/api/doctor/ai/mcp`` is the assistant's side:
the MCP endpoint, outside the sign-in rules (an assistant has no
Downtify account) and guarded by the helper's own key instead.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from . import doctor_ai, doctor_ai_sections  # noqa: F401  # registers tools
from .admin_access import admin_user
from .doctor_ai import ToolError, helper

router = APIRouter(prefix='/api/doctor/ai', dependencies=[Depends(admin_user)])
mcp_router = APIRouter()

#: Where assistants connect, relative to the server's address.
MCP_PATH = '/api/doctor/ai/mcp'


def _status() -> dict[str, Any]:
    doctor_ai.refresh_states()
    return {**helper.status(), 'mcp_path': MCP_PATH}


@router.get('')
def ai_status() -> dict[str, Any]:
    """Whether the helper runs, its key and its suggestions."""

    return _status()


@router.post('/start')
def ai_start(user_id: int = Depends(admin_user)) -> dict[str, Any]:
    """Start the helper with a new key (a running one gets a new key)."""

    helper.start(user_id)
    return _status()


@router.post('/stop')
def ai_stop() -> dict[str, Any]:
    helper.stop()
    return _status()


class AiSettings(BaseModel):
    can_apply: bool


@router.put('/settings')
def ai_settings(payload: AiSettings) -> dict[str, Any]:
    """The "may apply what you agreed to in the chat" switch."""

    if not helper.running:
        raise HTTPException(409, detail={'code': 'ai_not_running'})
    helper.can_apply = payload.can_apply
    return _status()


class SuggestionIds(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=500)


@router.post('/apply')
async def ai_apply(
    payload: SuggestionIds, user_id: int = Depends(admin_user)
) -> dict[str, Any]:
    """Apply waiting suggestions as one Doctor job."""

    try:
        result = await doctor_ai.apply(payload.ids, by='page', user_id=user_id)
    except ToolError as exc:
        raise HTTPException(
            409, detail={'code': 'ai_apply_failed', 'message': str(exc)}
        ) from None
    return {**_status(), 'applied': result}


@router.post('/dismiss')
def ai_dismiss(payload: SuggestionIds) -> dict[str, Any]:
    helper.remove(payload.ids)
    return _status()


@router.post('/clear')
def ai_clear() -> dict[str, Any]:
    """Forget applied and failed suggestions."""

    helper.clear_finished()
    return _status()


# ---------------------------------------------------------------------------
# MCP endpoint
# ---------------------------------------------------------------------------


def _plain(status: int, message: str, **headers: str) -> Response:
    return Response(
        json.dumps({'error': message}),
        status_code=status,
        media_type='application/json',
        headers=headers,
    )


def _guard(request: Request) -> Response | None:
    if not helper.running:
        return _plain(
            503,
            'The Downtify AI helper is off. Start it in Settings > '
            'Doctor > AI helper.',
        )
    if not helper.check(request.headers.get('authorization', '')):
        return _plain(
            401,
            'Wrong or old key: copy the current one from Settings > '
            'Doctor > AI helper.',
            **{'WWW-Authenticate': 'Bearer'},
        )
    return None


@mcp_router.post(MCP_PATH)
async def mcp_post(request: Request) -> Response:
    refused = _guard(request)
    if refused is not None:
        return refused
    body = await request.body()
    try:
        message = doctor_ai.parse(body)
    except ValueError:
        return Response(
            json.dumps(
                doctor_ai._error(None, doctor_ai.PARSE_ERROR, 'Parse error')
            ),
            status_code=400,
            media_type='application/json',
        )
    if isinstance(message, list):
        answers = [
            a for a in [await doctor_ai.handle(m) for m in message] if a
        ]
        if not answers:
            return Response(status_code=202)
        return Response(
            json.dumps(answers, ensure_ascii=False),
            media_type='application/json',
        )
    answer = await doctor_ai.handle(message)
    if answer is None:
        return Response(status_code=202)
    return Response(
        json.dumps(answer, ensure_ascii=False),
        media_type='application/json',
    )


@mcp_router.get(MCP_PATH)
@mcp_router.delete(MCP_PATH)
async def mcp_other(request: Request) -> Response:
    """No event stream and no sessions: every answer comes with its POST."""

    refused = _guard(request)
    if refused is not None:
        return refused
    return Response(status_code=405, headers={'Allow': 'POST'})
