import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")


def send_reorder_email(
    product_name: str,
    current_quantity: int,
    threshold: int,
    supplier_email: str,
    store_name: str,
) -> bool:
    """Send a low-stock reorder email to the supplier via SMTP."""
    subject = f"Reorder Required: {product_name} - {store_name}"
    body = (
        f"Dear Supplier,\n\n"
        f"{store_name} is running low on {product_name}.\n"
        f"Current quantity: {current_quantity}.\n"
        f"Reorder threshold: {threshold}.\n\n"
        f"Please send a reorder at your earliest convenience.\n\n"
        f"Best regards,\n{store_name}"
    )

    msg = MIMEMultipart()
    msg["From"] = SMTP_EMAIL
    msg["To"] = supplier_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, supplier_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[email_service] Failed to send email: {e}")
        return False
