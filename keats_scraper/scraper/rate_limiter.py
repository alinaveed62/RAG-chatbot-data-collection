"""Rate limiting for respectful web scraping."""

import time
import random
from typing import Optional
from functools import wraps

from ..config import RateLimitConfig
from ..utils.logging_config import get_logger

logger = get_logger()


class RateLimiter:
    """Implements rate limiting with random delays and exponential backoff."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self._last_request_time: float = 0
        self._request_count: int = 0

    def wait(self) -> None:
        """Wait appropriate time before next request."""
        now = time.time()
        elapsed = now - self._last_request_time

        # Calculate minimum delay
        min_interval = 60.0 / self.config.requests_per_minute

        # Add random jitter
        delay = random.uniform(
            max(min_interval, self.config.min_delay_seconds),
            self.config.max_delay_seconds,
        )

        # Wait if needed
        if elapsed < delay:
            sleep_time = delay - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self._last_request_time = time.time()
        self._request_count += 1

    def backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.config.min_delay_seconds * (
            self.config.backoff_factor ** attempt
        )
        # Add jitter
        delay *= random.uniform(0.5, 1.5)
        return min(delay, 60.0)  # Cap at 60 seconds

    def reset(self) -> None:
        """Reset rate limiter state."""
        self._last_request_time = 0
        self._request_count = 0

    @property
    def request_count(self) -> int:
        """Get total request count."""
        return self._request_count


def rate_limited(limiter: RateLimiter):
    """Decorator to apply rate limiting to a function."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter.wait()
            return func(*args, **kwargs)

        return wrapper

    return decorator
