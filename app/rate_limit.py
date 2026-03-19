"""
Rate Limiting Module

Prevents API abuse by limiting requests per client.

Uses sliding window algorithm:
- Track request timestamps per client
- Allow max requests per time window
- Clean up old data to prevent memory leaks
"""
import time
from collections import deque
from typing import Dict, Optional
from fastapi import HTTPException, status, Request


class RateLimiter:
    """
    Sliding window rate limiter.

    Example:
        limiter = RateLimiter(requests=100, window=60)
        # Allows 100 requests per 60 seconds per client
    """

    def __init__(self, requests: int = 100, window: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests: Maximum number of requests allowed
            window: Time window in seconds
        """
        self.requests = requests
        self.window = window
        # Store request timestamps per client: {client_key: deque([timestamps])}
        self.clients: Dict[str, deque] = {}

    def _get_client_key(self, request: Request) -> str:
        """
        Get client identifier for rate limiting.

        Uses API key if available, otherwise IP address.

        Args:
            request: FastAPI Request object

        Returns:
            str: Client identifier
        """
        # Try to get API key from headers
        api_key = request.headers.get("x-api-key")
        if api_key:
            return f"apikey:{api_key[:8]}"  # Use first 8 chars

        # Fall back to IP address
        # Handle both direct and proxied requests
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    def is_allowed(self, request: Request) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            request: FastAPI Request object

        Returns:
            bool: True if request is allowed, False otherwise
        """
        client_key = self._get_client_key(request)
        now = time.time()

        # Get or create client's request history
        if client_key not in self.clients:
            self.clients[client_key] = deque()
            return True

        timestamps = self.clients[client_key]

        # Remove timestamps outside the window
        cutoff = now - self.window
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

        # Check if limit exceeded
        if len(timestamps) >= self.requests:
            return False

        # Add current request timestamp
        timestamps.append(now)
        return True

    def get_retry_after(self, request: Request) -> int:
        """
        Get seconds until next request is allowed.

        Args:
            request: FastAPI Request object

        Returns:
            int: Seconds to wait
        """
        client_key = self._get_client_key(request)

        if client_key not in self.clients:
            return 0

        timestamps = self.clients[client_key]
        if not timestamps:
            return 0

        # When oldest timestamp expires
        oldest = timestamps[0]
        now = time.time()
        retry_after = int(oldest + self.window - now)

        return max(0, retry_after)

    def cleanup(self):
        """
        Remove stale client data to prevent memory leaks.

        Should be called periodically (e.g., every hour).
        """
        now = time.time()
        cutoff = now - self.window

        stale_clients = []
        for client_key, timestamps in self.clients.items():
            # Remove old timestamps
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            # Mark empty clients for removal
            if not timestamps:
                stale_clients.append(client_key)

        # Remove stale clients
        for client_key in stale_clients:
            del self.clients[client_key]


class RateLimitChecker:
    """
    FastAPI dependency for rate limiting.

    Usage:
        @app.get("/api/v1/predict")
        async def predict(
            request: Request,
            _rate_limit: None = Depends(rate_limit_checker)
        ):
            return {"result": "ok"}
    """

    def __init__(self, limiter: RateLimiter):
        """
        Initialize rate limit dependency.

        Args:
            limiter: RateLimiter instance
        """
        self.limiter = limiter

    async def __call__(self, request: Request) -> None:
        """
        Check rate limit and raise exception if exceeded.

        Args:
            request: FastAPI Request object

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        if not self.limiter.is_allowed(request):
            retry_after = self.limiter.get_retry_after(request)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Retry after {retry_after} seconds.",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )


# Global rate limiter instances
# Default: 100 requests per minute per client
default_rate_limiter = RateLimiter(requests=100, window=60)

# Stricter for prediction endpoint: 60 requests per minute
prediction_rate_limiter = RateLimiter(requests=60, window=60)

# Create dependency checkers
rate_limit_checker = RateLimitChecker(default_rate_limiter)
prediction_rate_limit_checker = RateLimitChecker(prediction_rate_limiter)
