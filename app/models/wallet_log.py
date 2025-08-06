from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.database import Base

class WalletLog(Base):
    __tablename__ = "wallet_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    wallet_id = Column(String, nullable=False)
    network = Column(String, nullable=False)
    address = Column(String, nullable=False)
    balance = Column(String, nullable=True)
    status = Column(String, nullable=True)
    action = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
