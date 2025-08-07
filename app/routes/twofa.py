from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
import secrets

from app.database import get_db
from app.models.user import User
from app.models.twofa import EmailCode
from app.models.wallet import Wallet
from app.schemas.twofa import EmailCodeVerify
from app.utils.auth import get_current_user
from app.utils.email import send_verification_email

router = APIRouter(prefix="/auth", tags=["2FA"])

@router.post("/request-code")
async def request_code(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    code = f"{secrets.randbelow(900000) + 100000:06d}"
    expiry = datetime.utcnow() + timedelta(minutes=10)

    email_code = EmailCode(
        user_id=current_user.id,
        code=code,
        expires_at=expiry
    )
    db.add(email_code)
    await db.commit()

    await send_verification_email(current_user.email, code)
    return {"message": "Verification code sent."}

@router.post("/verify-code")
async def verify_code(
    payload: EmailCodeVerify,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify an emailed code for the current user.

    The email supplied in the payload must match the authenticated user's
    email address. Mismatched emails are rejected to prevent cross-account
    verification.
    """

    if payload.email != current_user.email:
        raise HTTPException(status_code=400, detail="Email does not match authenticated user")

    result = await db.execute(
        select(EmailCode).where(
            EmailCode.user_id == current_user.id,
            EmailCode.code == payload.code
        )
    )
    email_code = result.scalar_one_or_none()

    if not email_code or email_code.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    current_user.email_verified = True
    db.add(current_user)

    await db.commit()

    return {"message": "Code verified successfully"}
