import resend
import os

resend.api_key = os.getenv("RESEND_API_KEY")  # pune în .env

async def send_verification_email(to_email: str, code: str):
    resend.Emails.send({
        "from": "no-reply@payinprivacy.com",
        "to": to_email,
        "subject": "Your 2FA Verification Code",
        "html": f"<p>Your verification code is: <strong>{code}</strong></p>"
    })
