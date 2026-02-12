"""Clerk JWT authentication dependency for FastAPI."""
import logging
import time
from typing import Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

# ── JWKS cache ────────────────────────────────────────────────
_jwks_cache: dict = {}
_jwks_cache_time: float = 0


async def _get_jwks() -> dict:
    """Fetch and cache Clerk's JWKS public keys."""
    global _jwks_cache, _jwks_cache_time

    if _jwks_cache and (time.time() - _jwks_cache_time) < settings.JWKS_CACHE_TTL:
        return _jwks_cache

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(settings.CLERK_JWKS_URL)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_time = time.time()
        logger.info("Refreshed Clerk JWKS keys")
        return _jwks_cache


def _get_signing_key(jwks: dict, token: str) -> jwt.algorithms.RSAAlgorithm:
    """Find the correct public key for the given token."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to find matching signing key",
    )


async def verify_clerk_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    FastAPI dependency — verifies a Clerk JWT and returns the user ID.

    Usage:
        @router.get("/")
        async def my_route(user_id: str = Depends(verify_clerk_token)):
            ...
    """
    token = credentials.credentials

    try:
        jwks = await _get_jwks()
        public_key = _get_signing_key(jwks, token)

        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=settings.CLERK_ISSUER,
            options={
                "verify_aud": False,
                "verify_exp": True,
                "verify_iss": True,
            },
        )

        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user ID (sub claim)",
            )

        return user_id

    except jwt.ExpiredSignatureError:
        logger.warning("Rejected expired Clerk token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidIssuerError:
        logger.warning("Rejected token with invalid issuer")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer",
        )
    except jwt.PyJWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )
