"""
Common utilities shared across tools
"""

from .logging_config import configure_logging, get_logger, get_logging_manager
from .telemetry import get_telemetry_manager, trace_function, trace_operation

# Import rate_limit_manager if available (may not be in all versions)
try:
    from .rate_limit_manager import RateLimitManager, global_rate_limit_manager

    _RATE_LIMITING_AVAILABLE = True
except ImportError:
    # Fallback for missing rate_limit_manager
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from .rate_limit_manager import RateLimitManager

    _RATE_LIMITING_AVAILABLE = False
    RateLimitManager = None  # type: ignore
    global_rate_limit_manager = None  # type: ignore

__all__ = [
    "configure_logging",
    "get_logger",
    "get_logging_manager",
    "get_telemetry_manager",
    "trace_function",
    "trace_operation",
]

if _RATE_LIMITING_AVAILABLE:
    __all__.extend(["RateLimitManager", "global_rate_limit_manager"])
