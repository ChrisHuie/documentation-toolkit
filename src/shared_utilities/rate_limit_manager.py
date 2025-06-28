"""
Centralized rate limit management for GitHub API requests.
Provides intelligent rate limiting based on GitHub's X-RateLimit headers.
Used across all tools in the documentation-toolkit project.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass

import requests
from loguru import logger


@dataclass
class RateLimitStatus:
    """Current rate limit status from GitHub API."""

    limit: int  # Total requests allowed per hour
    remaining: int  # Requests remaining in current window
    reset_time: int  # Unix timestamp when limit resets
    used: int  # Requests used in current window

    @property
    def usage_percentage(self) -> float:
        """Percentage of rate limit used (0.0 to 1.0)."""
        if self.limit == 0:
            return 0.0
        return (self.limit - self.remaining) / self.limit

    @property
    def minutes_until_reset(self) -> float:
        """Minutes until rate limit resets."""
        return max(0, (self.reset_time - time.time()) / 60)

    @property
    def requests_per_minute_remaining(self) -> float:
        """Safe requests per minute based on remaining quota."""
        if self.minutes_until_reset <= 0:
            return float(self.remaining)  # Reset imminent, use all remaining
        return self.remaining / self.minutes_until_reset


class RateLimitManager:
    """
    Manages GitHub API rate limiting with intelligent throttling.

    Designed to be shared across all tools in the documentation-toolkit project
    to provide consistent rate limiting behavior and cross-tool awareness.
    """

    def __init__(self, safety_buffer: int = 10, min_requests_threshold: int = 50):
        """
        Initialize rate limit manager.

        Args:
            safety_buffer: Number of requests to keep in reserve
            min_requests_threshold: Minimum requests before aggressive throttling
        """
        self.safety_buffer = safety_buffer
        self.min_requests_threshold = min_requests_threshold
        self.last_status: RateLimitStatus | None = None
        self.last_request_time = 0.0

    def extract_rate_limit_status(
        self, response: requests.Response
    ) -> RateLimitStatus | None:
        """
        Extract rate limit information from GitHub API response headers.

        Args:
            response: requests.Response object from GitHub API

        Returns:
            RateLimitStatus object or None if headers not present
        """
        try:
            headers = response.headers

            # GitHub provides these headers for rate limit info
            limit = int(headers.get("X-RateLimit-Limit", 0))
            remaining = int(headers.get("X-RateLimit-Remaining", 0))
            reset_time = int(headers.get("X-RateLimit-Reset", 0))
            used = int(headers.get("X-RateLimit-Used", limit - remaining))

            status = RateLimitStatus(
                limit=limit, remaining=remaining, reset_time=reset_time, used=used
            )

            # Update last known status
            self.last_status = status

            return status

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse rate limit headers: {e}")
            return None

    def log_rate_limit_status(
        self, response: requests.Response, tool_name: str = "unknown"
    ) -> None:
        """
        Log current rate limit status from API response.

        Args:
            response: GitHub API response
            tool_name: Name of tool making the request for better logging
        """
        status = self.extract_rate_limit_status(response)
        if status:
            logger.info(
                f"[{tool_name}] Rate limit: {status.remaining}/{status.limit} remaining "
                f"({status.usage_percentage:.1%} used, resets in {status.minutes_until_reset:.1f}m)"
            )

    def calculate_delay(self, status: RateLimitStatus | None = None) -> float:
        """
        Calculate appropriate delay before next request.

        Args:
            status: Current rate limit status, uses last known if None

        Returns:
            Delay in seconds before next request
        """
        if status is None:
            status = self.last_status

        if status is None:
            # No rate limit info available, use conservative default
            return 1.0

        # Check if we're approaching rate limit exhaustion
        if status.remaining <= self.safety_buffer:
            # Very aggressive throttling when near exhaustion
            if status.minutes_until_reset > 0:
                # Spread remaining requests over remaining time
                delay = (status.minutes_until_reset * 60) / max(1, status.remaining)
                return min(delay, 300)  # Cap at 5 minutes
            else:
                # Reset is imminent, short delay
                return 5.0

        # Check if we're below minimum threshold
        if status.remaining < self.min_requests_threshold:
            # Moderate throttling when getting low
            safe_rate = status.requests_per_minute_remaining * 0.8  # 80% of safe rate
            if safe_rate > 0:
                delay = 60 / safe_rate  # Convert to seconds between requests
                return min(delay, 60)  # Cap at 1 minute
            return 30.0

        # Normal operation - light throttling based on usage
        usage_pct = status.usage_percentage

        if usage_pct < 0.5:
            # Under 50% usage - minimal delay
            return 0.5
        elif usage_pct < 0.8:
            # 50-80% usage - moderate delay
            return 1.0 + (usage_pct - 0.5) * 4  # Scale from 1-2.2 seconds
        else:
            # Over 80% usage - more aggressive delay
            return 2.0 + (usage_pct - 0.8) * 10  # Scale from 2-4 seconds

    def wait_if_needed(
        self, response: requests.Response | None = None, tool_name: str = "unknown"
    ) -> None:
        """
        Wait appropriate amount of time before next request.

        Args:
            response: Optional response to extract rate limit info from
            tool_name: Name of tool making the request for better logging
        """
        current_time = time.time()

        # Extract rate limit status if response provided
        status = None
        if response:
            status = self.extract_rate_limit_status(response)

        # Calculate delay
        delay = self.calculate_delay(status)

        # Account for time already elapsed since last request
        time_elapsed = current_time - self.last_request_time
        adjusted_delay = max(0, delay - time_elapsed)

        if adjusted_delay > 0:
            logger.debug(f"[{tool_name}] Rate limiting: waiting {adjusted_delay:.1f}s")
            time.sleep(adjusted_delay)

        # Update last request time
        self.last_request_time = time.time()

    def check_rate_limit_safety(self, required_requests: int = 1) -> tuple[bool, str]:
        """
        Check if it's safe to make a certain number of requests.

        Args:
            required_requests: Number of requests planned

        Returns:
            Tuple of (is_safe, reason)
        """
        if self.last_status is None:
            return True, "No rate limit information available"

        status = self.last_status

        # Check if we have enough requests remaining
        safe_remaining = status.remaining - self.safety_buffer
        if required_requests > safe_remaining:
            return False, (
                f"Not enough requests remaining: need {required_requests}, "
                f"have {safe_remaining} (keeping {self.safety_buffer} in reserve)"
            )

        # Check if reset is very soon and we need to be conservative
        if (
            status.minutes_until_reset < 1
            and required_requests > status.remaining * 0.5
        ):
            return False, (
                f"Rate limit resets in {status.minutes_until_reset:.1f}m, "
                "conserving requests until reset"
            )

        return True, "Safe to proceed"

    def get_recommended_batch_size(self, default_batch_size: int) -> int:
        """
        Get recommended batch size based on current rate limit status.

        Args:
            default_batch_size: Preferred batch size under normal conditions

        Returns:
            Recommended batch size (may be smaller than default)
        """
        if self.last_status is None:
            return default_batch_size

        status = self.last_status

        # If we're running low on requests, reduce batch size
        if status.remaining < self.min_requests_threshold:
            # Very conservative batching
            return min(default_batch_size, max(1, status.remaining // 4))
        elif status.remaining < self.min_requests_threshold * 2:
            # Moderate reduction
            return min(default_batch_size, max(5, status.remaining // 3))
        else:
            # Normal batching
            return default_batch_size

    def format_status_summary(self) -> str:
        """Get a formatted summary of current rate limit status."""
        if self.last_status is None:
            return "Rate limit status: Unknown"

        status = self.last_status
        return (
            f"Rate limit: {status.remaining}/{status.limit} remaining "
            f"({status.usage_percentage:.1%} used), "
            f"resets in {status.minutes_until_reset:.1f} minutes"
        )

    def should_pause_operations(self) -> tuple[bool, float]:
        """
        Check if operations should be paused due to rate limit exhaustion.

        Returns:
            Tuple of (should_pause, recommended_wait_time_seconds)
        """
        if self.last_status is None:
            return False, 0

        status = self.last_status

        # Pause if we're at or below safety buffer
        if status.remaining <= self.safety_buffer:
            wait_time = status.minutes_until_reset * 60
            return True, min(wait_time, 3600)  # Cap at 1 hour

        return False, 0

    def make_rate_limited_request(
        self, request_func: Callable, tool_name: str = "unknown", *args, **kwargs
    ) -> requests.Response:
        """
        Make a rate-limited GitHub API request with automatic throttling.

        Args:
            request_func: Function that makes the HTTP request (e.g., requests.get)
            tool_name: Name of tool making the request for logging
            *args, **kwargs: Arguments passed to request_func

        Returns:
            requests.Response object

        Raises:
            Exception: If rate limit is exhausted and should pause operations
        """
        # Check if we should pause operations
        should_pause, wait_time = self.should_pause_operations()
        if should_pause:
            from requests.exceptions import HTTPError

            error_msg = (
                f"Rate limit exhausted. Please wait {wait_time / 60:.1f} minutes before continuing. "
                f"Current status: {self.format_status_summary()}"
            )
            # Raise an HTTPError with 403 status to match GitHub's rate limit response
            raise HTTPError(f"403 Client Error: rate limit exceeded - {error_msg}")

        # Wait based on current rate limit status
        self.wait_if_needed(tool_name=tool_name)

        # Make the request
        response = request_func(*args, **kwargs)

        # Log rate limit status from response
        self.log_rate_limit_status(response, tool_name)

        return response


# Global rate limit manager instance for project-wide use
# All tools should use this same instance to share rate limit awareness
global_rate_limit_manager = RateLimitManager()
