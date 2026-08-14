"""Clerk session verification for FastAPI."""

from __future__ import annotations

import httpx
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from fastapi import HTTPException, Request

from app.config import CLERK_SECRET_KEY


def _clerk_client() -> Clerk | None:
    if not CLERK_SECRET_KEY:
        return None
    return Clerk(bearer_auth=CLERK_SECRET_KEY)


async def require_clerk_user(request: Request):
    """Verify Clerk session; skip if Clerk is not configured (local dev fallback)."""
    client = _clerk_client()
    if client is None:
        return None

    headers = [(k.lower(), v) for k, v in request.headers.items()]
    httpx_request = httpx.Request(
        method=request.method,
        url=str(request.url),
        headers=headers,
        cookies=request.cookies,
    )

    state = client.authenticate_request(
        httpx_request,
        AuthenticateRequestOptions(),
    )

    if not state.is_signed_in:
        raise HTTPException(status_code=401, detail="Sign in required")

    return state
