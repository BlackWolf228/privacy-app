from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from uuid import UUID
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=8)

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    has_vault: bool
    created_at: datetime
    updated_at: datetime
    referral_code: Optional[str] = None
    email_verified: bool
    phone_number: Optional[str] = None
    kyc_status: Optional[str] = None

    class Config:
        from_attributes = True
