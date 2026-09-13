from __future__ import annotations

import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
from pydantic import BaseModel, ConfigDict, Field, SecretStr


GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
DEFAULT_GOOGLE_DRIVE_REDIRECT_URI = "http://localhost:8765/oauth2/callback"


class GoogleOAuthError(RuntimeError):
    """A sanitized Google OAuth configuration or token-exchange failure."""


class GoogleOAuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(min_length=1)
    client_secret: SecretStr = Field(repr=False)
    redirect_uri: str = Field(default=DEFAULT_GOOGLE_DRIVE_REDIRECT_URI, min_length=1)

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> GoogleOAuthConfig:
        client_id = environment.get("GOOGLE_DRIVE_OAUTH_CLIENT_ID", "").strip()
        client_secret = environment.get("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET", "").strip()
        redirect_uri = environment.get(
            "GOOGLE_DRIVE_OAUTH_REDIRECT_URI", DEFAULT_GOOGLE_DRIVE_REDIRECT_URI
        ).strip()
        missing = [
            name
            for name, value in (
                ("GOOGLE_DRIVE_OAUTH_CLIENT_ID", client_id),
                ("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET", client_secret),
                ("GOOGLE_DRIVE_OAUTH_REDIRECT_URI", redirect_uri),
            )
            if not value
        ]
        if missing:
            raise GoogleOAuthError(
                "Missing Google OAuth configuration: " + ", ".join(missing) + "."
            )
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )


class GoogleOAuthTokens(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: SecretStr = Field(repr=False)
    refresh_token: SecretStr | None = Field(default=None, repr=False)
    expires_in: int | None = Field(default=None, ge=0)
    scope: str | None = None
    token_type: str | None = None


@dataclass(frozen=True, repr=False)
class GoogleAuthorizationRequest:
    url: str
    state: str


def build_google_drive_authorization_request(
    config: GoogleOAuthConfig,
) -> GoogleAuthorizationRequest:
    state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_DRIVE_READONLY_SCOPE,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
    )
    return GoogleAuthorizationRequest(
        url=f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}",
        state=state,
    )


def exchange_google_authorization_code(
    config: GoogleOAuthConfig,
    code: str,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> GoogleOAuthTokens:
    if not code.strip():
        raise GoogleOAuthError("Google OAuth returned an incomplete authorization response.")
    payload = {
        "client_id": config.client_id,
        "client_secret": config.client_secret.get_secret_value(),
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": config.redirect_uri,
    }
    tokens = _request_tokens(payload, session=session, timeout=timeout)
    if tokens.scope and GOOGLE_DRIVE_READONLY_SCOPE not in tokens.scope.split():
        raise GoogleOAuthError(
            "Google Drive read-only permission was not granted. Reconnect Drive and approve it."
        )
    return tokens


def refresh_google_drive_access_token(
    config: GoogleOAuthConfig,
    refresh_token: str,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> str:
    if not refresh_token.strip():
        raise GoogleOAuthError("The Google Drive refresh token is missing.")
    payload = {
        "client_id": config.client_id,
        "client_secret": config.client_secret.get_secret_value(),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    tokens = _request_tokens(payload, session=session, timeout=timeout)
    return tokens.access_token.get_secret_value()


def resolve_google_drive_access_token(
    environment: Mapping[str, str],
    *,
    session: requests.Session | None = None,
) -> str:
    refresh_token = environment.get("GOOGLE_DRIVE_REFRESH_TOKEN", "").strip()
    if refresh_token:
        config = GoogleOAuthConfig.from_environment(environment)
        return refresh_google_drive_access_token(config, refresh_token, session=session)

    access_token = environment.get("GOOGLE_DRIVE_ACCESS_TOKEN", "").strip()
    if access_token:
        return access_token

    raise GoogleOAuthError(
        "Google Drive is not authorized. Run scripts/intake/google_drive_authorize.py "
        "after configuring the OAuth client in the ignored .env file."
    )


def _request_tokens(
    payload: dict[str, str],
    *,
    session: requests.Session | None,
    timeout: int,
) -> GoogleOAuthTokens:
    requester = session or requests.Session()
    try:
        response = requester.post(GOOGLE_TOKEN_ENDPOINT, data=payload, timeout=timeout)
    except (requests.ConnectionError, requests.Timeout):
        raise GoogleOAuthError("The Google OAuth token endpoint could not be reached.") from None

    try:
        body: Any = response.json()
    except ValueError:
        body = None
    if response.status_code >= 400:
        error_code = body.get("error") if isinstance(body, dict) else None
        if error_code == "invalid_grant":
            raise GoogleOAuthError(
                "Google rejected the authorization grant. Reconnect Drive and try again."
            )
        raise GoogleOAuthError(
            f"Google OAuth token exchange failed (HTTP {response.status_code})."
        )
    if not isinstance(body, dict) or not str(body.get("access_token", "")).strip():
        raise GoogleOAuthError("Google OAuth returned an invalid token response.")
    return GoogleOAuthTokens(
        access_token=str(body["access_token"]),
        refresh_token=(
            str(body["refresh_token"]) if body.get("refresh_token") else None
        ),
        expires_in=(int(body["expires_in"]) if body.get("expires_in") is not None else None),
        scope=(str(body["scope"]) if body.get("scope") else None),
        token_type=(str(body["token_type"]) if body.get("token_type") else None),
    )
