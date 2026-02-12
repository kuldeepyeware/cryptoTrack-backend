"""Centralized application settings."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/cryptotrack",
    )
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000"
    ).split(",")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Clerk
    CLERK_ISSUER: str = os.getenv(
        "CLERK_ISSUER", "https://noted-leopard-40.clerk.accounts.dev"
    )
    CLERK_JWKS_URL: str = f"{CLERK_ISSUER}/.well-known/jwks.json"
    JWKS_CACHE_TTL: int = 3600  # 1 hour


settings = Settings()
