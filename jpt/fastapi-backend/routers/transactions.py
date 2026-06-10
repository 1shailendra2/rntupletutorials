from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from typing import Optional
from thefuzz import fuzz

import httpx
from services.supabase_client import get_headers, SUPABASE_URL, supabase_admin
from services.whisper_service import transcribe_audio
from services.llm_service import extract_transaction_from_text
from services.email_service import send_reorder_email
from routers._deps import get_current_user

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ── Models ─────────────────────────────────────────────────────────────

class TransactionOut(BaseModel):
    id: str
    user_id: str
    product_id: str
    action: str
    quantity: int
    price: Optional[float] = None
    created_at: Optional[str] = None
    product_name: Optional[str] = None


class VoiceTransactionResponse(BaseModel):
    transcript: str
    extracted: dict
    product: dict
    transaction: dict
    alert_sent: bool


# ── Helpers ────────────────────────────────────────────────────────────

def fuzzy_match_product(product_name: str, products: list[dict]) -> dict | None:
    """Return the best fuzzy-matched product or None."""
    best_match = None
    best_score = 0
    for p in products:
        score = fuzz.token_sort_ratio(product_name.lower(), p["name"].lower())
        if score > best_score:
            best_score = score
            best_match = p
    # Require at least 50% similarity
    return best_match if best_score >= 50 else None


# ── Routes ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[TransactionOut])
async def list_transactions(user: dict = Depends(get_current_user)):
    """Return all transactions for the authenticated user, newest first.

    Uses a PostgREST resource embedding to include the product name.
    """
    user_id = user["sub"]
    token = user["access_token"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/transactions?select=id,user_id,product_id,action,quantity,price,created_at,products(name)&order=created_at.desc",
                headers=get_headers(token)
            )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        rows = response.json()
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    # Flatten the embedded product name
    for row in rows:
        product_info = row.pop("products", None)
        row["product_name"] = product_info["name"] if product_info else None

    return rows


@router.post("/voice", response_model=VoiceTransactionResponse)
async def voice_transaction(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Process a voice audio file into an inventory transaction.

    Pipeline: Audio → Whisper transcript → Gemini extraction → RPC update.
    """
    import traceback
    try:
        user_id = user["sub"]
        token = user["access_token"]

        # 1. Transcribe audio with Whisper
        audio_bytes = await file.read()
        transcript = await transcribe_audio(audio_bytes, file.filename or "audio.webm")

        # 2. Extract structured data with Gemini
        try:
            extracted = await extract_transaction_from_text(transcript)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not extract transaction from transcript: {e}",
            )

        product_name = extracted.get("product_name", "")
        quantity = int(extracted.get("quantity", 0))
        action = extracted.get("action", "sale")

        if action not in ("sale", "restock"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid action '{action}'. Must be 'sale' or 'restock'.",
            )

        # 3. Fetch user's products and fuzzy-match
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{SUPABASE_URL}/rest/v1/products?select=*",
                    headers=get_headers(token)
                )
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            user_products = response.json()
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        matched_product = fuzzy_match_product(product_name, user_products)

        if not matched_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No product matching '{product_name}' found in your inventory.",
            )

        # 4. Call the RPC to update quantity
        quantity_change = quantity if action == "restock" else -quantity
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SUPABASE_URL}/rest/v1/rpc/update_product_quantity",
                    headers=get_headers(token),
                    json={
                        "p_product_id": matched_product["id"],
                        "p_quantity_change": quantity_change,
                        "p_action": action,
                    }
                )
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"RPC update_product_quantity failed: {response.text}",
                )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"RPC update_product_quantity failed: {e}",
            )

        # 5. Fetch the updated product
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{SUPABASE_URL}/rest/v1/products?select=*&id=eq.{matched_product['id']}",
                    headers=get_headers(token)
                )
            updated_product = response.json()[0] if response.status_code == 200 and response.json() else matched_product
        except Exception:
            updated_product = matched_product

        # 6. Fetch latest transaction for this product (the one just created by the RPC)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{SUPABASE_URL}/rest/v1/transactions?select=*&product_id=eq.{matched_product['id']}&order=created_at.desc&limit=1",
                    headers=get_headers(token)
                )
            transaction = response.json()[0] if response.status_code == 200 and response.json() else {}
        except Exception:
            transaction = {}

        # 7. Check if alert is needed
        alert_sent = False
        new_qty = updated_product.get("quantity", 0)
        threshold = updated_product.get("threshold", 0)

        if new_qty < threshold:
            # Fetch the user's profile for store_name and supplier_email (via admin to bypass RLS)
            try:
                profile_result = supabase_admin.table("profiles") \
                    .select("*") \
                    .eq("id", user_id) \
                    .execute()
                profile = profile_result.data[0] if profile_result.data else {}
            except Exception:
                profile = {}

            supplier_email = profile.get("supplier_email", "")
            store_name = profile.get("store_name", "Store")

            if supplier_email:
                alert_sent = send_reorder_email(
                    product_name=updated_product["name"],
                    current_quantity=new_qty,
                    threshold=threshold,
                    supplier_email=supplier_email,
                    store_name=store_name,
                )

        return VoiceTransactionResponse(
            transcript=transcript,
            extracted=extracted,
            product=updated_product,
            transaction=transaction,
            alert_sent=alert_sent,
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unhandled voice transaction error:\n{traceback.format_exc()}"
        )

