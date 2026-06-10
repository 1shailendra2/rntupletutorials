import time

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from services.supabase_client import supabase_auth, supabase_admin

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Request / Response models ──────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    store_name: str
    supplier_email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    user_id: str
    email: str


# ── Routes ─────────────────────────────────────────────────────────────

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest):
    """Register a new user via Supabase Auth and create their profile row."""

    # 1. Create the user through Supabase GoTrue
    auth_resp = await supabase_auth("signup", {
        "email": body.email,
        "password": body.password,
    })

    if auth_resp.status_code >= 400:
        detail = auth_resp.json().get("msg") or auth_resp.json().get("error_description") or auth_resp.text
        raise HTTPException(status_code=auth_resp.status_code, detail=str(detail))

    data = auth_resp.json()
    user = data.get("user", data)
    user_id = user["id"]
    access_token = data.get("access_token", "")

    # 2. Insert into profiles using the admin (service-role) client to bypass RLS
    # Retry loop: auth.users row may not be committed yet when FK check runs
    for attempt in range(3):
        try:
            supabase_admin.table("profiles").insert({
                "id": user_id,
                "store_name": body.store_name,
                "supplier_email": body.supplier_email,
            }).execute()
            break
        except Exception as e:
            if attempt == 2:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"User created but profile insert failed: {str(e)}",
                )
            time.sleep(0.5)

    return AuthResponse(access_token=access_token, user_id=user_id, email=body.email)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    """Authenticate an existing user and return a JWT."""

    auth_resp = await supabase_auth("token?grant_type=password", {
        "email": body.email,
        "password": body.password,
    })

    if auth_resp.status_code >= 400:
        err = auth_resp.json()
        detail = err.get("msg") or err.get("error_description") or err.get("message") or auth_resp.text
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(detail))

    data = auth_resp.json()
    user = data.get("user", {})

    return AuthResponse(
        access_token=data["access_token"],
        user_id=user.get("id", ""),
        email=user.get("email", body.email),
    )
