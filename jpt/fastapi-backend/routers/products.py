from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import httpx
from services.supabase_client import get_headers, SUPABASE_URL
from routers._deps import get_current_user

router = APIRouter(prefix="/products", tags=["Products"])


# ── Models ─────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    quantity: int
    price: float
    threshold: int


class ProductOut(BaseModel):
    id: str
    user_id: str
    name: str
    quantity: int
    price: float
    threshold: int
    status: str
    created_at: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────

def compute_status(quantity: int, threshold: int) -> str:
    if quantity <= 0:
        return "OUT"
    if quantity < threshold:
        return "LOW"
    return "OK"


# ── Routes ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[ProductOut])
async def list_products(user: dict = Depends(get_current_user)):
    """Return all products belonging to the authenticated user."""
    user_id = user["sub"]
    token = user["access_token"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/products?select=*&order=created_at.desc",
                headers=get_headers(token)
            )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(body: ProductCreate, user: dict = Depends(get_current_user)):
    """Create a new product for the authenticated user."""
    user_id = user["sub"]
    token = user["access_token"]
    product_status = compute_status(body.quantity, body.threshold)

    headers = get_headers(token)
    headers["Prefer"] = "return=representation"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/products",
                headers=headers,
                json={
                    "user_id": user_id,
                    "name": body.name,
                    "quantity": body.quantity,
                    "price": body.price,
                    "threshold": body.threshold,
                    "status": product_status,
                }
            )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        products = response.json()
        return products[0] if isinstance(products, list) else products
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

