"""Optional shared-token auth. No token configured -> open (LAN use)."""

from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException, status

from . import config


def require_auth(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None),
) -> None:
    if not config.AUTH_TOKEN:
        return
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    token = token or x_auth_token
    if token != config.AUTH_TOKEN:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or missing auth token")
