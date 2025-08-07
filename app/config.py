import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    def load_dotenv(*args, **kwargs):
        pass

load_dotenv()

class Settings:
    def __init__(self):
        self.PROJECT_NAME = "Privacy App"
        self.PROJECT_VERSION = "1.0.0"

        # Database
        self.POSTGRES_USER = os.getenv("POSTGRES_USER")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
        self.POSTGRES_DB = os.getenv("POSTGRES_DB")
        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST")
        self.POSTGRES_PORT = os.getenv("POSTGRES_PORT")

        self.DATABASE_URL = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

        # JWT
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
        self.JWT_ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

        # Email
        self.EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@privacyapp.com")

        # Fireblocks
        self.FIREBLOCKS_API_BASE_URL = os.getenv(
            "FIREBLOCKS_API_BASE_URL", "https://sandbox-api.fireblocks.io"
        )
        self.FIREBLOCKS_API_KEY = os.getenv("FIREBLOCKS_API_KEY")
        self.FIREBLOCKS_API_SECRET = self._load_secret(
            os.getenv("FIREBLOCKS_API_SECRET")
        )

    @staticmethod
    def _load_secret(value: str | None) -> str | None:
        """Return the contents of *value* if it is a path to a file.

        The FIREBLOCKS_API_SECRET environment variable may contain either the
        raw secret or a path to a file containing the secret.  This helper reads
        the file when a path is provided and returns the stripped contents,
        allowing existing behaviour (direct secret in the environment) to
        continue to work.
        """
        if value and os.path.isfile(value):
            try:
                with open(value, "r", encoding="utf-8") as fh:
                    return fh.read().strip()
            except OSError:
                pass
        return value

settings = Settings()
