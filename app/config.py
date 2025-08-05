import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.PROJECT_NAME = "Privacy App"
        self.PROJECT_VERSION = "1.0.0"

        # Database
        self.POSTGRES_USER = os.getenv("POSTGRES_USER")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
        self.POSTGRES_DB = os.getenv("POSTGRES_DB")
        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

        self.DATABASE_URL = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

        # JWT
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key")
        self.JWT_ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

        # Email
        self.EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@privacyapp.com")

settings = Settings()
