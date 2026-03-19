"""
Enhanced Error Handling Module

Follows RFC 7807 Problem Details for HTTP APIs.

Standard error format:
{
    "type": "https://api.example.com/errors/validation-error",
    "title": "Validation Error",
    "status": 422,
    "detail": "Invalid input data",
    "instance": "/api/v1/predict",
    "errors": [...]  # Additional validation errors
}
"""
from typing import Any, Dict, Optional, List
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse


class APIException(HTTPException):
    """
    Base exception for API errors.

    Provides consistent error format across all endpoints.
    """

    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        error_type: Optional[str] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize API exception.

        Args:
            status_code: HTTP status code
            title: Short error title
            detail: Detailed error message
            error_type: Error type identifier (URL or string)
            errors: Additional error details (e.g., validation errors)
        """
        super().__init__(status_code=status_code, detail=detail)

        self.title = title
        self.error_type = error_type or f"https://api.fraud-detection.com/errors/{title.lower().replace(' ', '-')}"
        self.errors = errors or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "type": self.error_type,
            "title": self.title,
            "status": self.status_code,
            "detail": self.detail,
            "errors": self.errors
        }


class ValidationError(APIException):
    """Raised when request validation fails."""

    def __init__(self, detail: str, errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation Error",
            detail=detail,
            errors=errors
        )


class NotFoundError(APIException):
    """Raised when a resource is not found."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=detail
        )


class AuthenticationError(APIException):
    """Raised when authentication fails."""

    def __init__(self, detail: str = "Invalid API key"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Authentication Error",
            detail=detail
        )


class RateLimitError(APIException):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            title="Rate Limit Exceeded",
            detail=f"Too many requests. Retry after {retry_after} seconds."
        )
        self.retry_after = retry_after


class ModelError(APIException):
    """Raised when model prediction fails."""

    def __init__(self, detail: str = "Prediction service error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Model Error",
            detail=detail
        )


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    Global exception handler for APIException.

    Converts APIException to standardized JSON response.

    Args:
        request: FastAPI Request object
        exc: The exception that was raised

    Returns:
        JSONResponse: Formatted error response
    """
    error_dict = exc.to_dict()
    error_dict["instance"] = str(request.url.path)

    return JSONResponse(
        status_code=exc.status_code,
        content=error_dict
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Global exception handler for standard HTTPException.

    Provides consistent format for all HTTP exceptions.

    Args:
        request: FastAPI Request object
        exc: The HTTPException that was raised

    Returns:
        JSONResponse: Formatted error response
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"https://httpstatuses.com/{exc.status_code}",
            "title": getattr(exc, "title", "HTTP Error"),
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url.path)
        }
    )
