"""
Rate Limiting Module Tests

Tests for RateLimiter and RateLimitChecker classes.
"""
import pytest
import time
import asyncio
from unittest.mock import MagicMock, Mock
from fastapi import HTTPException, status

from app.rate_limit import RateLimiter, RateLimitChecker


def create_mock_request(api_key=None, ip="127.0.0.1", x_forwarded_for=None):
    """Create a properly mocked Request object."""
    request = Mock()
    request.headers = Mock()
    # Create a simple dict-based get that doesn't use side_effect with lambda
    headers_dict = {
        "x-api-key": api_key,
        "x-forwarded-for": x_forwarded_for
    }
    request.headers.get = lambda key, default=None: headers_dict.get(key.lower() if isinstance(key, str) else key, default)
    request.client = Mock()
    request.client.host = ip
    return request


@pytest.mark.unit
class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_rate_limiter_init(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(requests=10, window=30)
        assert limiter.requests == 10
        assert limiter.window == 30
        assert isinstance(limiter.clients, dict)

    def test_is_allowed_first_request(self):
        """Test that first request is always allowed."""
        limiter = RateLimiter(requests=5, window=60)
        request = create_mock_request(api_key="test-key-12345")

        assert limiter.is_allowed(request) is True

    def test_is_allowed_up_to_limit(self):
        """Test that requests up to limit are allowed."""
        limiter = RateLimiter(requests=2, window=60)
        # Create the request ONCE and reuse it - same request object
        request = create_mock_request(ip="192.168.1.1", api_key=None)

        # First request creates client (not tracked against limit)
        assert limiter.is_allowed(request) is True
        # Next 2 requests are allowed (limit is 2)
        assert limiter.is_allowed(request) is True
        assert limiter.is_allowed(request) is True
        # 4th should be blocked (limit exceeded)
        assert limiter.is_allowed(request) is False

    def test_is_allowed_with_api_key(self):
        """Test client identification via API key."""
        limiter = RateLimiter(requests=2, window=60)
        # Create the request ONCE and reuse it
        request = create_mock_request(api_key="dev-key-12345")

        # First request creates client
        assert limiter.is_allowed(request) is True
        # Next 2 requests are allowed
        assert limiter.is_allowed(request) is True
        assert limiter.is_allowed(request) is True
        # 4th should be blocked
        assert limiter.is_allowed(request) is False

    def test_is_allowed_with_x_forwarded_for(self):
        """Test client identification via X-Forwarded-For header."""
        limiter = RateLimiter(requests=1, window=60)
        request = create_mock_request(x_forwarded_for="10.0.0.1, 10.0.0.2", api_key=None)

        assert limiter.is_allowed(request) is True

    def test_get_retry_after_returns_zero_for_new_client(self):
        """Test that retry_after is 0 for new clients."""
        limiter = RateLimiter(requests=5, window=60)
        request = create_mock_request(api_key="new-key")

        retry_after = limiter.get_retry_after(request)
        assert retry_after == 0

    def test_get_retry_after_for_limited_client(self):
        """Test retry_after calculation for rate-limited client."""
        limiter = RateLimiter(requests=1, window=10)
        request = create_mock_request(api_key="limited-key", ip="10.0.0.1")

        # Use up the limit
        limiter.is_allowed(request)
        # Try again (should be blocked)
        limiter.is_allowed(request)

        retry_after = limiter.get_retry_after(request)
        assert 0 <= retry_after <= 10

    def test_cleanup_with_no_clients(self):
        """Test cleanup when no clients exist."""
        limiter = RateLimiter(requests=5, window=60)
        # Should not raise
        limiter.cleanup()
        assert limiter.clients == {}

    def test_different_clients_separate_limits(self):
        """Test that different clients have separate rate limits."""
        limiter = RateLimiter(requests=2, window=60)

        request1 = create_mock_request(api_key="client-1")
        request2 = create_mock_request(api_key="client-2")

        # Client 1: first request creates client
        assert limiter.is_allowed(request1) is True
        # Client 1: next 2 requests are allowed
        assert limiter.is_allowed(request1) is True
        assert limiter.is_allowed(request1) is True
        # Client 1: 4th request blocked
        assert limiter.is_allowed(request1) is False

        # Client 2: first request creates client (separate limit)
        assert limiter.is_allowed(request2) is True
        # Client 2: still has full limit available
        assert limiter.is_allowed(request2) is True
        assert limiter.is_allowed(request2) is True
        assert limiter.is_allowed(request2) is False


@pytest.mark.unit
class TestRateLimitChecker:
    """Tests for RateLimitChecker dependency."""

    def test_rate_limit_checker_init(self):
        """Test RateLimitChecker initialization."""
        limiter = RateLimiter(requests=10, window=60)
        checker = RateLimitChecker(limiter)
        assert checker.limiter == limiter

    def test_rate_limit_checker_allows_request(self):
        """Test that checker allows requests under limit."""
        limiter = RateLimiter(requests=5, window=60)
        checker = RateLimitChecker(limiter)
        request = create_mock_request(api_key="allowed-key")

        # Should not raise
        asyncio.run(checker(request))

    def test_rate_limit_checker_raises_429(self):
        """Test that checker raises HTTPException when limit exceeded."""
        limiter = RateLimiter(requests=1, window=60)
        checker = RateLimitChecker(limiter)
        request = create_mock_request(api_key="blocked-key")

        # First request creates client (not counted against limit)
        asyncio.run(checker(request))
        # Second request counted
        asyncio.run(checker(request))
        # Third request should raise 429 (limit exceeded)
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(checker(request))

        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
