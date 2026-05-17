"""Authentication, cookie, CORS, and origin helpers for the Web UI server."""

from __future__ import annotations

import ipaddress
import secrets
from http.cookies import SimpleCookie
from urllib.parse import urlparse


def is_loopback_host(host: str | None) -> bool:
    """Return whether *host* resolves to the local machine."""
    if not host:
        return False
    normalized = host.strip().strip("[]").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def origin_is_allowed(origin: str, *, host_header: str | None, token: str | None) -> bool:
    """Return whether a browser Origin is allowed for this request."""
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False

    host_name = urlparse(f"http://{host_header}").hostname if host_header else None
    if is_loopback_host(parsed.hostname):
        return True

    return bool(token and host_name and parsed.hostname.lower() == host_name.lower())


def request_origin_allowed(origin: str | None, *, host_header: str | None, token: str | None) -> bool:
    """Return whether a request with the given Origin should be accepted."""
    return not origin or origin_is_allowed(origin, host_header=host_header, token=token)


def cors_origin(
    *,
    origin: str | None,
    host_header: str | None,
    client_host: str,
    client_port: int,
    token: str | None,
) -> str:
    """Return the Access-Control-Allow-Origin value for a response."""
    if origin and origin_is_allowed(origin, host_header=host_header, token=token):
        return origin
    if host_header:
        return f"http://{host_header}"
    return f"http://{client_host}:{client_port}"


def check_auth(token: str | None, *, authorization: str, cookie_header: str) -> bool:
    """Validate bearer-token or cookie authentication for protected Web UI routes."""
    if not token:
        return True
    if secrets.compare_digest(authorization, f"Bearer {token}"):
        return True

    cookie = SimpleCookie()
    cookie.load(cookie_header)
    token_cookie = cookie.get("cc_branch_token")
    if token_cookie is None:
        return False
    return secrets.compare_digest(token_cookie.value, token)


def query_token_is_valid(token: str | None, query: dict[str, list[str]]) -> bool:
    """Return whether a URL query token can establish the auth cookie."""
    if not token:
        return False
    tokens = query.get("token", [])
    return bool(tokens) and secrets.compare_digest(tokens[0], token)


def auth_cookie_header(token: str | None) -> str:
    """Build a safe Set-Cookie header for browser-originated Web UI actions."""
    cookie = SimpleCookie()
    cookie["cc_branch_token"] = token or ""
    cookie["cc_branch_token"]["path"] = "/"
    cookie["cc_branch_token"]["httponly"] = True
    cookie["cc_branch_token"]["samesite"] = "Strict"
    return cookie.output(header="").strip()
