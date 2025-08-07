from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Vault(Base):
    __tablename__ = "vaults"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    vault_id = Column(String, unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="vaults")
    wallets = relationship("Wallet", back_populates="vault")

