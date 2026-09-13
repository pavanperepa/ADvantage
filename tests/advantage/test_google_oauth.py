from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
import requests

from advantage.integrations.google_oauth import (
    GOOGLE_DRIVE_READONLY_SCOPE,
    GoogleOAuthConfig,
    GoogleOAuthError,
    build_google_drive_authorization_request,
    exchange_google_authorization_code,
    refresh_google_drive_access_token,
    resolve_google_drive_access_token,
)


class StubResponse:
    def __init__(self, status_code: int, body: dict | None = None) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> dict:
        if self._body is None:
            raise ValueError("not json")
        return self._body


class StubSession:
    def __init__(self, response: StubResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict, int]] = []

    def post(self, url: str, *, data: dict, timeout: int):
        self.calls.append((url, data, timeout))
        return self.response


def oauth_config() -> GoogleOAuthConfig:
    return GoogleOAuthConfig(
        client_id="test-client.apps.googleusercontent.com",
        client_secret="test-client-secret",
        redirect_uri="http://localhost:8765/oauth2/callback",
    )


def test_authorization_request_uses_readonly_scope_and_state():
    request = build_google_drive_authorization_request(oauth_config())
    query = parse_qs(urlparse(request.url).query)

    assert query["scope"] == [GOOGLE_DRIVE_READONLY_SCOPE]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert query["state"] == [request.state]
    assert "test-client-secret" not in request.url


def test_exchange_code_returns_secret_wrapped_tokens():
    session = StubSession(
        StubResponse(
            200,
            {
                "access_token": "access-secret",
                "refresh_token": "refresh-secret",
                "expires_in": 3600,
                "scope": GOOGLE_DRIVE_READONLY_SCOPE,
                "token_type": "Bearer",
            },
        )
    )

    tokens = exchange_google_authorization_code(
        oauth_config(), "authorization-code", session=session
    )

    assert tokens.access_token.get_secret_value() == "access-secret"
    assert tokens.refresh_token is not None
    assert tokens.refresh_token.get_secret_value() == "refresh-secret"
    assert "access-secret" not in repr(tokens)
    assert "refresh-secret" not in repr(tokens)


def test_exchange_code_rejects_missing_drive_permission():
    session = StubSession(
        StubResponse(
            200,
            {
                "access_token": "access-secret",
                "refresh_token": "refresh-secret",
                "scope": "openid email",
            },
        )
    )

    with pytest.raises(GoogleOAuthError, match="permission was not granted"):
        exchange_google_authorization_code(
            oauth_config(), "authorization-code", session=session
        )


def test_refresh_access_token_posts_credentials_without_exposing_result():
    session = StubSession(StubResponse(200, {"access_token": "new-access", "expires_in": 3600}))

    access_token = refresh_google_drive_access_token(
        oauth_config(), "refresh-secret", session=session
    )

    assert access_token == "new-access"
    _, data, _ = session.calls[0]
    assert data["grant_type"] == "refresh_token"
    assert data["client_secret"] == "test-client-secret"
    assert data["refresh_token"] == "refresh-secret"


def test_resolver_prefers_refresh_token_and_keeps_access_token_as_fallback():
    environment = {
        "GOOGLE_DRIVE_OAUTH_CLIENT_ID": "client-id",
        "GOOGLE_DRIVE_OAUTH_CLIENT_SECRET": "client-secret",
        "GOOGLE_DRIVE_OAUTH_REDIRECT_URI": "http://localhost:8765/oauth2/callback",
        "GOOGLE_DRIVE_REFRESH_TOKEN": "refresh-secret",
        "GOOGLE_DRIVE_ACCESS_TOKEN": "stale-access",
    }
    session = StubSession(StubResponse(200, {"access_token": "fresh-access"}))

    assert resolve_google_drive_access_token(environment, session=session) == "fresh-access"

    assert (
        resolve_google_drive_access_token({"GOOGLE_DRIVE_ACCESS_TOKEN": "access-only"})
        == "access-only"
    )


def test_token_exchange_errors_are_sanitized():
    session = StubSession(
        StubResponse(
            400,
            {
                "error": "invalid_grant",
                "error_description": "authorization-code refresh-secret client-secret",
            },
        )
    )

    with pytest.raises(GoogleOAuthError) as exc_info:
        refresh_google_drive_access_token(
            oauth_config(), "refresh-secret", session=session
        )

    message = str(exc_info.value)
    assert "authorization-code" not in message
    assert "refresh-secret" not in message
    assert "client-secret" not in message


def test_token_endpoint_network_failure_is_sanitized():
    class FailingSession:
        def post(self, url: str, *, data: dict, timeout: int):
            raise requests.Timeout("payload contained client-secret")

    with pytest.raises(GoogleOAuthError) as exc_info:
        refresh_google_drive_access_token(
            oauth_config(), "refresh-secret", session=FailingSession()
        )

    assert "client-secret" not in str(exc_info.value)
    assert "refresh-secret" not in str(exc_info.value)
