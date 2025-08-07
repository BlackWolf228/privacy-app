from sqlalchemy import Column, String, Boolean, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    has_vault = Column(Boolean, default=False, nullable=False)
    privacy_id = Column(String(10), unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Optional fields you asked for — for future use
    device_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    app_version = Column(String, nullable=True)
    country_code = Column(String, nullable=True)
    referral_code = Column(String, nullable=True)
    email_verified = Column(Boolean, default=False)
    phone_number = Column(String, nullable=True)
    kyc_status = Column(String, default="not_started")
    email_codes = relationship("EmailCode", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "username IS NULL OR privacy_id <> username",
            name="ck_privacy_id_username_diff",
        ),
    )

    def __repr__(self):
        return f"<User id={self.id} email={self.email} active={self.is_active} kyc={self.kyc_status}>"
