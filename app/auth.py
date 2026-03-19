"""
API Key Authentication Module

FastAPI Dependency Injection allows us to reuse authentication logic across endpoints.

Usage:
    @app.get("/protected")
    async def protected_endpoint(api_key: str = Depends(verify_api_key)):
        return {"message": "Authorized"}
"""
from fastapi import Header, HTTPException, status
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


# In production, load from environment variable or database
VALID_API_KEYS = {
    "dev-key-12345": "development",
    "test-key-67890": "testing",
    # In production: fetch from database or secrets manager
}

# Also allow key from environment
env_key = os.getenv("API_KEY")
if env_key:
    VALID_API_KEYS[env_key] = "production"


async def verify_api_key(x_api_key: str = Header(..., description="API Key for authentication")) -> str:
    """
    Verify API key from X-API-Key header.

    FastAPI Dependency Injection:
    - Automatically extracts X-API-Key header
    - Returns 401 if missing or invalid
    - Can be used in any endpoint: api_key: str = Depends(verify_api_key)

    Args:
        x_api_key: API key from request header

    Returns:
        str: The validated API key

    Raises:
        HTTPException: 401 if key is invalid
    """
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Invalid API key",
                "message": "Please provide a valid X-API-Key header"
            },
            headers={"WWW-Authenticate": "ApiKey"}
        )
    return x_api_key


async def verify_api_key_optional(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """
    Optional API key verification for public endpoints.

    Returns None if key is not provided, validates if provided.
    Useful for endpoints that work without auth but have enhanced features with auth.

    Args:
        x_api_key: API key from request header (optional)

    Returns:
        Optional[str]: The validated API key or None
    """
    if x_api_key is None:
        return None
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key


def get_client_info(api_key: str) -> dict:
    """
    Get client information from API key.

    In production, this would query a database.
    """
    client_type = VALID_API_KEYS.get(api_key, "unknown")
    return {
        "client_type": client_type,
        "api_key_prefix": api_key[:8] + "..." if len(api_key) > 8 else api_key
    }
