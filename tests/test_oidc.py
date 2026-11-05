from __future__ import annotations

import base64
import hashlib
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from joserfc import jwt
from joserfc.jwk import RSAKey

from downtify.oidc import (
    OIDCConfig,
    OIDCError,
    OIDCTransactions,
    authorize_claims,
    create_authorization_url,
    verify_id_token,
)


def _config(**kwargs) -> OIDCConfig:
    return OIDCConfig(
        issuer='https://id.example.test',
        client_id='downtify',
        client_secret='client-secret',
        **kwargs,
    )


def _signed_token(key, **overrides) -> str:
    now = int(time.time())
    claims = {
        'iss': 'https://id.example.test',
        'sub': 'subject-123',
        'aud': 'downtify',
        'exp': now + 300,
        'iat': now,
        'nonce': 'expected-nonce',
        'preferred_username': 'maria',
        'groups': ['downtify-users'],
        **overrides,
    }
    return jwt.encode({'alg': 'RS256'}, claims, key)


def test_oidc_config_is_optional_and_requires_complete_credentials():
    assert OIDCConfig.from_env({}) is None
    with pytest.raises(ValueError, match='must all be set'):
        OIDCConfig.from_env({'DOWNTIFY_OIDC_ISSUER': 'https://id.example'})


def test_config_reads_claim_and_group_settings():
    config = OIDCConfig.from_env({
        'DOWNTIFY_OIDC_ISSUER': 'https://id.example',
        'DOWNTIFY_OIDC_CLIENT_ID': 'downtify',
        'DOWNTIFY_OIDC_CLIENT_SECRET': 'secret',
        'DOWNTIFY_OIDC_GROUPS_CLAIM': 'realm_access.roles',
        'DOWNTIFY_OIDC_ALLOWED_GROUPS': 'users, admins',
        'DOWNTIFY_OIDC_ADMIN_GROUPS': 'admins',
    })

    assert config is not None
    assert config.groups_claim == 'realm_access.roles'
    assert config.allowed_groups == ('users', 'admins')
    assert config.admin_groups == ('admins',)


def test_authorization_url_uses_pkce_s256_and_nonce():
    config = _config()
    transactions = OIDCTransactions()
    url, state = create_authorization_url(
        config,
        {'authorization_endpoint': 'https://id.example/authorize'},
        'https://music.example/api/auth/oidc/callback',
        transactions,
    )
    query = parse_qs(urlsplit(url).query)
    transaction = transactions.consume(state)

    assert transaction is not None
    nonce, verifier = transaction
    challenge = hashlib.sha256(verifier.encode()).digest()
    assert query['code_challenge_method'] == ['S256']
    assert query['code_challenge'] == [
        base64.urlsafe_b64encode(challenge).rstrip(b'=').decode()
    ]
    assert query['nonce'] == [nonce]
    assert query['redirect_uri'] == [
        'https://music.example/api/auth/oidc/callback'
    ]


def test_oidc_transaction_is_single_use():
    transactions = OIDCTransactions()
    state, nonce, verifier = transactions.create()

    assert transactions.consume(state) == (nonce, verifier)
    assert transactions.consume(state) is None


def test_valid_signed_id_token_is_accepted():
    private_key = RSAKey.generate_key(2048)
    jwks = {'keys': [private_key.as_dict(private=False)]}

    claims = verify_id_token(
        _signed_token(private_key), jwks, _config(), 'expected-nonce'
    )

    assert claims['sub'] == 'subject-123'
    assert claims['preferred_username'] == 'maria'


@pytest.mark.parametrize(
    ('overrides', 'nonce', 'message'),
    [
        ({'aud': 'another-client'}, 'expected-nonce', 'different client'),
        ({}, 'wrong-nonce', 'nonce does not match'),
        (
            {'iss': 'https://other.example'},
            'expected-nonce',
            'invalid ID token',
        ),
        ({'exp': 1}, 'expected-nonce', 'invalid ID token'),
    ],
)
def test_invalid_id_token_claims_are_rejected(overrides, nonce, message):
    private_key = RSAKey.generate_key(2048)
    jwks = {'keys': [private_key.as_dict(private=False)]}

    with pytest.raises(OIDCError, match=message):
        verify_id_token(
            _signed_token(private_key, **overrides), jwks, _config(), nonce
        )


def test_invalid_signature_is_rejected():
    signing_key = RSAKey.generate_key(2048)
    other_key = RSAKey.generate_key(2048)

    with pytest.raises(OIDCError, match='invalid ID token'):
        verify_id_token(
            _signed_token(signing_key),
            {'keys': [other_key.as_dict(private=False)]},
            _config(),
            'expected-nonce',
        )


def test_group_claim_maps_role_and_enforces_allowlist():
    config = _config(
        groups_claim='realm_access.roles',
        allowed_groups=('downtify-users',),
        admin_groups=('downtify-admins',),
    )

    assert authorize_claims(
        {
            'sub': 'subject-123',
            'preferred_username': 'maria',
            'realm_access': {'roles': ['downtify-users', 'downtify-admins']},
        },
        config,
    ) == ('maria', 'admin')

    with pytest.raises(OIDCError, match='not in an allowed group'):
        authorize_claims(
            {
                'sub': 'subject-456',
                'preferred_username': 'other',
                'realm_access': {'roles': ['other']},
            },
            config,
        )
