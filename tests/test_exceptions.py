"""
Exception Handling Tests

Tests for custom exceptions and exception handlers.
"""
import pytest
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from unittest.mock import Mock

from app.exceptions import (
    APIException,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    RateLimitError,
    ModelError,
    api_exception_handler,
    http_exception_handler
)


def create_mock_request(path="/api/v1/predict"):
    """Create a properly mocked Request object."""
    request = Mock()
    request.url = Mock()
    request.url.path = path
    return request


@pytest.mark.unit
class TestAPIException:
    """Tests for APIException base class."""

    def test_api_exception_init(self):
        """Test APIException initialization."""
        exc = APIException(
            status_code=422,
            title="Test Error",
            detail="This is a test error"
        )
        assert exc.status_code == 422
        assert exc.title == "Test Error"
        assert exc.detail == "This is a test error"
        assert exc.errors == []

    def test_api_exception_with_errors(self):
        """Test APIException with validation errors."""
        errors = [{"field": "amount", "message": "Must be positive"}]
        exc = APIException(
            status_code=422,
            title="Validation Error",
            detail="Invalid input",
            errors=errors
        )
        assert exc.errors == errors

    def test_api_exception_custom_error_type(self):
        """Test APIException with custom error type."""
        exc = APIException(
            status_code=500,
            title="Server Error",
            detail="Something went wrong",
            error_type="https://api.example.com/errors/custom"
        )
        assert exc.error_type == "https://api.example.com/errors/custom"

    def test_api_exception_default_error_type(self):
        """Test APIException generates default error type."""
        exc = APIException(
            status_code=500,
            title="Custom Error",
            detail="Test"
        )
        assert "custom-error" in exc.error_type

    def test_api_exception_to_dict(self):
        """Test APIException to_dict method."""
        exc = APIException(
            status_code=422,
            title="Test",
            detail="Test detail"
        )
        result = exc.to_dict()
        assert result["status"] == 422
        assert result["title"] == "Test"
        assert result["detail"] == "Test detail"
        assert "type" in result
        assert "errors" in result


@pytest.mark.unit
class TestSpecificExceptions:
    """Tests for specific exception classes."""

    def test_validation_error_defaults(self):
        """Test ValidationError has correct defaults."""
        exc = ValidationError("Invalid input")
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc.title == "Validation Error"
        assert exc.detail == "Invalid input"

    def test_not_found_error_defaults(self):
        """Test NotFoundError has correct defaults."""
        exc = NotFoundError()
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.title == "Not Found"

    def test_not_found_error_custom_detail(self):
        """Test NotFoundError with custom detail."""
        exc = NotFoundError("Transaction not found")
        assert exc.detail == "Transaction not found"

    def test_authentication_error_defaults(self):
        """Test AuthenticationError has correct defaults."""
        exc = AuthenticationError()
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.title == "Authentication Error"

    def test_rate_limit_error_with_retry_after(self):
        """Test RateLimitError stores retry_after."""
        exc = RateLimitError(retry_after=30)
        assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exc.retry_after == 30
        assert "30 seconds" in exc.detail

    def test_model_error_defaults(self):
        """Test ModelError has correct defaults."""
        exc = ModelError()
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc.title == "Model Error"


@pytest.mark.unit
class TestExceptionHandlers:
    """Tests for exception handler functions."""

    @pytest.mark.asyncio
    async def test_api_exception_handler(self):
        """Test api_exception_handler returns JSONResponse."""
        exc = APIException(
            status_code=422,
            title="Test Error",
            detail="Test detail"
        )
        request = create_mock_request("/api/v1/predict")

        response = await api_exception_handler(request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_api_exception_handler_includes_instance(self):
        """Test api_exception_handler includes request path."""
        exc = APIException(500, "Error", "Detail")
        request = create_mock_request("/test/path")

        response = await api_exception_handler(request, exc)
        import json
        body = json.loads(response.body.decode())

        assert body["instance"] == "/test/path"

    @pytest.mark.asyncio
    async def test_http_exception_handler(self):
        """Test http_exception_handler handles standard HTTPException."""
        exc = HTTPException(status_code=404, detail="Not found")
        request = create_mock_request("/api/v1/missing")

        response = await http_exception_handler(request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_http_exception_handler_content(self):
        """Test http_exception_handler returns correct content."""
        exc = HTTPException(status_code=401, detail="Unauthorized")
        request = create_mock_request("/api/v1/predict")

        response = await http_exception_handler(request, exc)
        import json
        body = json.loads(response.body.decode())

        assert body["status"] == 401
        assert body["detail"] == "Unauthorized"
        assert body["instance"] == "/api/v1/predict"
        assert "type" in body
