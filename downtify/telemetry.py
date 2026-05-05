"""Structured debug/info logging helpers (JSON previews, secret redaction)."""

from __future__ import annotations

import json
import re
from typing import Any

_SENSITIVE_SUBSTRINGS = frozenset({
    'token',
    'secret',
    'password',
    'authorization',
    'cookie',
})

# Spotify embed sentry / correlation blobs — noisy and irrelevant for parsing.
_DROP_KEYS_CASEFOLD = frozenset({
    '_sentrytracedata',
    '_sentrybaggage',
    '_sentrytrace_data',
})


def redact_sensitive_mapping(
    obj: Any, *, depth: int = 0, max_depth: int = 28
) -> Any:
    """Return a nested structure safe to log (tokens and secrets redacted)."""

    if depth > max_depth:
        return '<max depth>'
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            ks = str(k)
            lk = ks.casefold()
            if lk in _DROP_KEYS_CASEFOLD:
                continue
            if any(fragment in lk for fragment in _SENSITIVE_SUBSTRINGS):
                out[ks] = '<redacted>'
            else:
                out[ks] = redact_sensitive_mapping(v, depth=depth + 1)
        return out
    if isinstance(obj, list):
        if len(obj) > 120:
            head = [
                redact_sensitive_mapping(x, depth=depth + 1) for x in obj[:120]
            ]
            return head + [f'<{len(obj) - 120} more list items>']
        return [redact_sensitive_mapping(x, depth=depth + 1) for x in obj]
    return obj


def json_log_blob(obj: Any, *, max_chars: int = 16000) -> str:
    """Serialize for logs; truncate very large responses."""

    try:
        blob = json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        blob = repr(obj)
    blob = _collapse_ws(blob)
    if len(blob) > max_chars:
        return blob[:max_chars] + (
            f'...<truncated {len(blob) - max_chars} chars>'
        )
    return blob


def _collapse_ws(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()
