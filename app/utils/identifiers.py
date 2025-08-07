import secrets
import string
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User


async def generate_unique_privacy_id(db: AsyncSession, length: int = 10) -> str:
    """Generate a unique privacy identifier for a user.

    The identifier is composed of uppercase letters and digits and is
    guaranteed to be unique across all users.
    """
    alphabet = string.ascii_uppercase + string.digits
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        result = await db.execute(select(User).where(User.privacy_id == candidate))
        if result.scalar_one_or_none() is None:
            return candidate
