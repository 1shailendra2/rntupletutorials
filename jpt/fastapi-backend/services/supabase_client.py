from __future__ import annotations

import os
import httpx
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# SDK clients — anon for auth, admin (service-role) to bypass RLS
print(f"[supabase_client] ANON_KEY starts with:         {SUPABASE_ANON_KEY[:20]}...")
print(f"[supabase_client] SERVICE_ROLE_KEY starts with: {SUPABASE_SERVICE_ROLE_KEY[:20]}...")
supabase_anon = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def get_user_client(token: str):
    """Create a Supabase client authenticated with the user's JWT.

    This ensures PostgREST receives the correct auth context so that
    RLS policies can resolve ``auth.uid()`` properly.
    """
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.postgrest.auth(token)
    return client


def get_headers(token: str):
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def get_supabase_headers(access_token: str | None = None, use_service_role: bool = False) -> dict:
    """Build headers for Supabase REST / Auth calls."""
    key = SUPABASE_SERVICE_ROLE_KEY if use_service_role else SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    elif use_service_role:
        headers["Authorization"] = f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"
    return headers


async def supabase_request(
    method: str,
    path: str,
    *,
    access_token: str | None = None,
    use_service_role: bool = False,
    json_body: dict | None = None,
    params: dict | None = None,
    extra_headers: dict | None = None,
) -> httpx.Response:
    """Generic async helper for calling the Supabase REST API."""
    url = f"{SUPABASE_URL}{path}"
    headers = get_supabase_headers(access_token=access_token, use_service_role=use_service_role)
    if extra_headers:
        headers.update(extra_headers)

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            url,
            headers=headers,
            json=json_body,
            params=params,
            timeout=30.0,
        )
    return response


async def supabase_auth(endpoint: str, json_body: dict) -> httpx.Response:
    """Call Supabase GoTrue Auth endpoints (signup / token)."""
    url = f"{SUPABASE_URL}/auth/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=json_body, timeout=30.0)
    return response


async def supabase_rpc(
    function_name: str,
    params: dict,
    access_token: str | None = None,
    use_service_role: bool = False,
) -> httpx.Response:
    """Call a Supabase RPC (database function)."""
    return await supabase_request(
        "POST",
        f"/rest/v1/rpc/{function_name}",
        access_token=access_token,
        use_service_role=use_service_role,
        json_body=params,
    )
