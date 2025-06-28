"""
Rate limiting manager for API requests.

Simple stub implementation for rate limiting functionality.
"""

import time
from collections.abc import Callable
from typing import Any


class RateLimitManager:
    """Manages rate limiting for API requests."""

    def __init__(self, default_delay: float = 1.0):
        """Initialize rate limit manager."""
        self.default_delay = default_delay
        self.last_request_time = 0.0

    def wait_if_needed(self, delay: float | None = None) -> None:
        """Wait if needed to respect rate limits."""
        current_time = time.time()
        actual_delay = delay or self.default_delay
        time_since_last = current_time - self.last_request_time

        if time_since_last < actual_delay:
            sleep_time = actual_delay - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def rate_limited(self, delay: float | None = None) -> Callable:
        """Decorator for rate-limited functions."""

        def decorator(func: Callable) -> Callable:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                self.wait_if_needed(delay)
                return func(*args, **kwargs)

            return wrapper

        return decorator


# Global instance
global_rate_limit_manager = RateLimitManager()
