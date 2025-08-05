from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

DATABASE_URL = settings.DATABASE_URL

# Creează un engine asincron
engine = create_async_engine(DATABASE_URL, echo=True)

# Creează o sesiune asincronă
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Baza pentru toate modelele
Base = declarative_base()

# Funcție pentru a obține o sesiune DB
async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()
