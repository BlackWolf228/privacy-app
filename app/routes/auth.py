from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from jose import jwt
import os
import logging

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserOut
from app.utils.security import hash_password, verify_password
from app.config import settings
from app.utils.identifiers import generate_unique_privacy_id

from app.utils.whitelist import is_email_whitelisted

logger = logging.getLogger(__name__)
router = APIRouter()

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + expires_delta})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/auth/register", response_model=UserOut)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    email = user.email.lower()

    # 1. Verificam daca emailul este in whitelist
    if not is_email_whitelisted(email):
        raise HTTPException(status_code=403, detail="This email is not whitelisted")

    # 2. Check if email already exists
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 3. Create new user
    privacy_id = await generate_unique_privacy_id(db)
    new_user = User(
        email=email,
        password_hash=hash_password(user.password),
        privacy_id=privacy_id,
    )
    db.add(new_user)

    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError as e:
        await db.rollback()
        # fallback in case of race condition
        if 'duplicate key value violates unique constraint' in str(e.orig).lower():
            raise HTTPException(status_code=400, detail="Email already registered")
        logger.error(f"Integrity error: {e}")
        raise HTTPException(status_code=500, detail="Database integrity error")
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error during registration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return new_user

@router.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    email = form_data.username.lower()
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
    except DataError:
        raise HTTPException(status_code=400, detail="Invalid login request")
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}