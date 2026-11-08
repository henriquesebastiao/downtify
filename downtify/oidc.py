"""OpenID Connect authorization-code login with PKCE."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from urllib.parse import urlencode

import httpx
from joserfc import jwt
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry


class OIDCError(ValueError):
    """An OIDC response or identity could not be trusted."""


@dataclass(frozen=True)
class OIDCConfig:
    issuer: str
    client_id: str
    client_secret: str
    scopes: str = 'openid profile email'
    redirect_uri: str = ''
    username_claim: str = 'preferred_username'
    groups_claim: str = 'groups'
    allowed_groups: tuple[str, ...] = ()
    admin_groups: tuple[str, ...] = ()

    @classmethod
    def from_env(
        cls, environ: Optional[Mapping[str, str]] = None
    ) -> Optional[OIDCConfig]:
        values = os.environ if environ is None else environ
        issuer = values.get('DOWNTIFY_OIDC_ISSUER', '').strip()
        client_id = values.get('DOWNTIFY_OIDC_CLIENT_ID', '').strip()
        client_secret = values.get('DOWNTIFY_OIDC_CLIENT_SECRET', '').strip()
        if not any((issuer, client_id, client_secret)):
            return None
        if not all((issuer, client_id, client_secret)):
            raise ValueError(
                'DOWNTIFY_OIDC_ISSUER, DOWNTIFY_OIDC_CLIENT_ID and '
                'DOWNTIFY_OIDC_CLIENT_SECRET must all be set'
            )
        if not issuer.startswith(('https://', 'http://')):
            raise ValueError('DOWNTIFY_OIDC_ISSUER must be an HTTP(S) URL')

        def values_for(name: str) -> tuple[str, ...]:
            return tuple(
                item.strip()
                for item in values.get(name, '').split(',')
                if item.strip()
            )

        return cls(
            issuer=issuer,
            client_id=client_id,
            client_secret=client_secret,
            scopes=values.get(
                'DOWNTIFY_OIDC_SCOPES', 'openid profile email'
            ).strip(),
            redirect_uri=values.get('DOWNTIFY_OIDC_REDIRECT_URI', '').strip(),
            username_claim=values.get(
                'DOWNTIFY_OIDC_USERNAME_CLAIM', 'preferred_username'
            ).strip(),
            groups_claim=values.get(
                'DOWNTIFY_OIDC_GROUPS_CLAIM', 'groups'
            ).strip(),
            allowed_groups=values_for('DOWNTIFY_OIDC_ALLOWED_GROUPS'),
            admin_groups=values_for('DOWNTIFY_OIDC_ADMIN_GROUPS'),
        )


class OIDCTransactions:
    """Short-lived, single-use OIDC transactions held in process memory."""

    def __init__(self, ttl_seconds: int = 600) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._pending: dict[str, tuple[float, str, str]] = {}

    def create(self) -> tuple[str, str, str]:
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        with self._lock:
            now = time.monotonic()
            self._pending = {
                key: value
                for key, value in self._pending.items()
                if value[0] >= now
            }
            self._pending[state] = (now + self._ttl, nonce, verifier)
        return state, nonce, verifier

    def consume(self, state: str) -> Optional[tuple[str, str]]:
        with self._lock:
            entry = self._pending.pop(state, None)
        if entry is None or entry[0] < time.monotonic():
            return None
        return entry[1], entry[2]


def create_authorization_url(
    config: OIDCConfig,
    metadata: Mapping[str, Any],
    callback_uri: str,
    transactions: OIDCTransactions,
) -> tuple[str, str]:
    endpoint = metadata.get('authorization_endpoint')
    if not isinstance(endpoint, str) or not endpoint.startswith((
        'https://',
        'http://',
    )):
        raise OIDCError('The provider has no valid authorization endpoint')
    state, nonce, verifier = transactions.create()
    challenge = (
        base64
        .urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b'=')
        .decode()
    )
    query = urlencode({
        'client_id': config.client_id,
        'redirect_uri': callback_uri,
        'response_type': 'code',
        'scope': config.scopes,
        'state': state,
        'nonce': nonce,
        'code_challenge': challenge,
        'code_challenge_method': 'S256',
    })
    separator = '&' if '?' in endpoint else '?'
    return f'{endpoint}{separator}{query}', state


_ALLOWED_ALGORITHMS = (
    'RS256',
    'RS384',
    'RS512',
    'PS256',
    'PS384',
    'PS512',
    'ES256',
    'ES384',
    'ES512',
    'EdDSA',
)


def verify_id_token(
    encoded: str,
    jwks: Mapping[str, Any],
    config: OIDCConfig,
    expected_nonce: str,
) -> dict[str, Any]:
    """Verify the ID token signature, standard claims, audience and nonce."""

    try:
        token = jwt.decode(
            encoded,
            KeySet.import_key_set(jwks),
            algorithms=_ALLOWED_ALGORITHMS,
        )
        claims = dict(token.claims)
        JWTClaimsRegistry(
            leeway=60,
            iss={'essential': True, 'value': config.issuer},
            sub={'essential': True},
            exp={'essential': True},
            iat={'essential': True},
        ).validate(claims)
    except Exception as exc:
        raise OIDCError('The provider returned an invalid ID token') from exc

    audience = claims.get('aud')
    audiences = [audience] if isinstance(audience, str) else audience
    if not isinstance(audiences, list) or config.client_id not in audiences:
        raise OIDCError('The ID token was issued for a different client')
    authorized_party = claims.get('azp')
    if len(audiences) > 1 and authorized_party != config.client_id:
        raise OIDCError('The ID token has an invalid authorized party')
    if authorized_party is not None and authorized_party != config.client_id:
        raise OIDCError('The ID token has an invalid authorized party')
    nonce = claims.get('nonce')
    if not isinstance(nonce, str) or not hmac.compare_digest(
        nonce, expected_nonce
    ):
        raise OIDCError('The ID token nonce does not match')
    return claims


def claim_value(claims: Mapping[str, Any], path: str) -> Any:
    value: Any = claims
    for part in path.split('.'):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def authorize_claims(
    claims: Mapping[str, Any], config: OIDCConfig
) -> tuple[str, str]:
    """Return the provider username and mapped Downtify role."""

    group_value = claim_value(claims, config.groups_claim)
    if isinstance(group_value, str):
        groups = {group_value}
    elif isinstance(group_value, list):
        groups = {value for value in group_value if isinstance(value, str)}
    else:
        groups = set()

    if config.allowed_groups and not groups.intersection(
        config.allowed_groups
    ):
        raise OIDCError('Your identity is not in an allowed group')

    role = 'admin' if groups.intersection(config.admin_groups) else 'user'
    username = claim_value(claims, config.username_claim)
    if not isinstance(username, str) or not username.strip():
        username = claims.get('email')
    if not isinstance(username, str) or not username.strip():
        username = claims.get('sub')
    if not isinstance(username, str) or not username.strip():
        raise OIDCError('The provider did not return a usable identity')
    return username.strip(), role


def clean_oidc_username(value: str, issuer: str, subject: str) -> str:
    name = re.sub(r'[^A-Za-z0-9._-]+', '_', value).strip('._-')[:32]
    if len(name) < 3:
        suffix = hashlib.sha256(f'{issuer}\0{subject}'.encode()).hexdigest()
        name = f'oidc_{suffix[:12]}'
    return name


def local_login_enabled_from_env(
    environ: Optional[Mapping[str, str]] = None,
) -> bool:
    values = os.environ if environ is None else environ
    return values.get(
        'DOWNTIFY_DISABLE_LOCAL_LOGIN', ''
    ).strip().lower() not in {
        '1',
        'true',
        'yes',
        'on',
    }


class OIDCProvider:
    """Discover an OIDC provider and complete its authorization flow."""

    def __init__(
        self,
        config: OIDCConfig,
        transactions: Optional[OIDCTransactions] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.config = config
        self.transactions = transactions or OIDCTransactions()
        self._transport = transport
        self._metadata: Optional[dict[str, Any]] = None
        self._jwks: Optional[dict[str, Any]] = None

    async def _get_json(self, url: str) -> dict[str, Any]:
        async with httpx.AsyncClient(
            timeout=10, transport=self._transport
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            value = response.json()
        if not isinstance(value, dict):
            raise OIDCError('The provider returned invalid JSON')
        return value

    async def metadata(self) -> dict[str, Any]:
        if self._metadata is None:
            discovery_url = (
                self.config.issuer.rstrip('/')
                + '/.well-known/openid-configuration'
            )
            metadata = await self._get_json(discovery_url)
            if metadata.get('issuer') != self.config.issuer:
                raise OIDCError('The provider issuer does not match')
            for name in (
                'authorization_endpoint',
                'token_endpoint',
                'jwks_uri',
            ):
                endpoint = metadata.get(name)
                if not isinstance(endpoint, str) or not endpoint.startswith((
                    'https://',
                    'http://',
                )):
                    raise OIDCError(f'The provider is missing {name}')
            self._metadata = metadata
        return self._metadata

    async def begin(self, callback_uri: str) -> tuple[str, str]:
        metadata = await self.metadata()
        return create_authorization_url(
            self.config, metadata, callback_uri, self.transactions
        )

    async def authenticate(
        self,
        *,
        code: str,
        state: str,
        cookie_state: str,
        callback_uri: str,
    ) -> tuple[dict[str, Any], str, str]:
        if (
            not state
            or not cookie_state
            or not hmac.compare_digest(state, cookie_state)
        ):
            raise OIDCError('The sign-in state does not match')
        transaction = self.transactions.consume(state)
        if transaction is None:
            raise OIDCError(
                'The sign-in state has expired or was already used'
            )
        nonce, verifier = transaction
        metadata = await self.metadata()
        async with httpx.AsyncClient(
            timeout=10, transport=self._transport
        ) as client:
            response = await client.post(
                metadata['token_endpoint'],
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': callback_uri,
                    'code_verifier': verifier,
                },
                auth=httpx.BasicAuth(
                    self.config.client_id, self.config.client_secret
                ),
                headers={'Accept': 'application/json'},
            )
            response.raise_for_status()
            token_response = response.json()
        if not isinstance(token_response, dict) or not isinstance(
            token_response.get('id_token'), str
        ):
            raise OIDCError('The provider did not return an ID token')
        if self._jwks is None:
            self._jwks = await self._get_json(metadata['jwks_uri'])
        claims = verify_id_token(
            token_response['id_token'], self._jwks, self.config, nonce
        )
        username, role = authorize_claims(claims, self.config)
        return claims, username, role
