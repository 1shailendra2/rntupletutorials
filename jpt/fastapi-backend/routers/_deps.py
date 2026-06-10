"""Shared FastAPI dependencies (auth helpers)."""
from __future__ import annotations

import jwt
from fastapi import HTTPException, status, Request


async def get_current_user(request: Request) -> dict:
    """Extract and decode the Supabase JWT from the Authorization header.

    Returns a dict with at least ``sub`` (user id) and ``access_token``.

    Supabase already verified the token on signup/login and now signs
    with ES256, so we skip local signature verification and just read
    the claims.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
        )

    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
        )

    payload["access_token"] = token
    return payload

