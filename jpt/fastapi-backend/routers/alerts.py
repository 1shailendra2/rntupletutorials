from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from services.email_service import send_reorder_email

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class EmailAlertRequest(BaseModel):
    product_name: str
    current_quantity: int
    threshold: int
    supplier_email: EmailStr
    store_name: str


class EmailAlertResponse(BaseModel):
    sent: bool


@router.post("/email", response_model=EmailAlertResponse)
async def send_alert_email(body: EmailAlertRequest):
    """Send a low-stock reorder email to the supplier."""
    success = send_reorder_email(
        product_name=body.product_name,
        current_quantity=body.current_quantity,
        threshold=body.threshold,
        supplier_email=body.supplier_email,
        store_name=body.store_name,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send alert email. Check SMTP configuration.",
        )

    return EmailAlertResponse(sent=True)
