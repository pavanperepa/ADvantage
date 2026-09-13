"""Authorize local read-only Google Drive intake through a localhost callback."""

from __future__ import annotations

import argparse
import os
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv, set_key

from advantage.integrations.google_oauth import (
    DEFAULT_GOOGLE_DRIVE_REDIRECT_URI,
    GoogleOAuthConfig,
    GoogleOAuthError,
    build_google_drive_authorization_request,
    exchange_google_authorization_code,
)


ROOT = Path(__file__).resolve().parents[2]


class OAuthCallbackServer(HTTPServer):
    expected_path: str
    expected_state: str
    authorization_code: str | None = None
    oauth_error: str | None = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    server: OAuthCallbackServer

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        if parsed.path != self.server.expected_path:
            self._respond(404, "This is not the configured Google OAuth callback.")
            return
        query = parse_qs(parsed.query)
        returned_state = query.get("state", [""])[0]
        if not returned_state or returned_state != self.server.expected_state:
            self.server.oauth_error = "state_mismatch"
            self._respond(400, "Authorization could not be verified. Return to the terminal.")
            return
        provider_error = query.get("error", [""])[0]
        code = query.get("code", [""])[0]
        if provider_error:
            self.server.oauth_error = provider_error
            self._respond(400, "Google Drive authorization was not granted.")
            return
        if not code:
            self.server.oauth_error = "missing_code"
            self._respond(400, "Google did not return an authorization code.")
            return
        self.server.authorization_code = code
        self._respond(200, "Google Drive is connected. You can close this tab.")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _respond(self, status: int, message: str) -> None:
        body = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>ADvantage Google Drive</title></head>"
            f"<body><h1>{message}</h1></body></html>"
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Seconds to wait for the browser callback",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Print the authorization URL instead of opening the default browser",
    )
    return parser


def validate_local_redirect_uri(value: str) -> tuple[str, int, str]:
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise GoogleOAuthError(
            "Local authorization requires an http://localhost redirect URI."
        )
    if parsed.query or parsed.fragment or not parsed.path:
        raise GoogleOAuthError("The Google OAuth redirect URI must have a fixed path.")
    try:
        port = parsed.port
    except ValueError:
        raise GoogleOAuthError("The Google OAuth redirect URI has an invalid port.") from None
    if port is None:
        raise GoogleOAuthError("The Google OAuth redirect URI must include a port.")
    return parsed.hostname, port, parsed.path


def main() -> None:
    args = build_parser().parse_args()
    env_path = ROOT / ".env"
    load_dotenv(env_path)
    config = GoogleOAuthConfig.from_environment(os.environ)
    host, port, callback_path = validate_local_redirect_uri(config.redirect_uri)
    request = build_google_drive_authorization_request(config)

    server = OAuthCallbackServer((host, port), OAuthCallbackHandler)
    server.expected_path = callback_path
    server.expected_state = request.state
    server.timeout = 1
    try:
        opened = False if args.no_browser else webbrowser.open(request.url, new=1)
        if not opened:
            print("Open this Google authorization URL in your browser:")
            print(request.url)
        print("Waiting for Google Drive consent; no token will be displayed...")
        deadline = time.monotonic() + max(args.timeout, 1)
        while (
            time.monotonic() < deadline
            and server.authorization_code is None
            and server.oauth_error is None
        ):
            server.handle_request()
    finally:
        server.server_close()

    if server.oauth_error:
        raise GoogleOAuthError(
            "Google Drive authorization was denied or could not be verified."
        )
    if not server.authorization_code:
        raise GoogleOAuthError("Timed out waiting for Google Drive authorization.")

    tokens = exchange_google_authorization_code(
        config,
        server.authorization_code,
    )
    refresh_token = tokens.refresh_token
    if refresh_token is None:
        raise GoogleOAuthError(
            "Google did not return a refresh token. Revoke the existing app grant, then reconnect."
        )
    env_path.touch(exist_ok=True)
    set_key(
        str(env_path),
        "GOOGLE_DRIVE_REFRESH_TOKEN",
        refresh_token.get_secret_value(),
        quote_mode="always",
    )
    print("Google Drive authorization was saved to the ignored .env file.")
    print("The refresh token and access token were not displayed.")


if __name__ == "__main__":
    main()
