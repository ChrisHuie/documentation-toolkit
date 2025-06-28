"""
Centralized logging configuration for the documentation toolkit.

Provides structured logging with OpenTelemetry integration and consistent
formatting across all components.
"""

import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from .telemetry import get_telemetry_manager


class LoggingManager:
    """Manages centralized logging configuration across the toolkit."""

    def __init__(self, service_name: str = "documentation-toolkit"):
        """
        Initialize logging manager.

        Args:
            service_name: Name of the service for logging identification
        """
        self.service_name = service_name
        self.telemetry_manager = get_telemetry_manager()
        self._configured = False

    def configure_logging(
        self,
        level: str = "INFO",
        enable_file_logging: bool = True,
        log_file_path: Path | None = None,
        structured_format: bool = True,
    ) -> None:
        """
        Configure structured logging for the entire application.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
            enable_file_logging: Whether to enable file logging
            log_file_path: Path for log file (auto-generated if None)
            structured_format: Whether to use structured JSON format
        """
        if self._configured:
            return

        # Remove default loguru handler
        logger.remove()

        # Configure console logging
        console_format = self._get_console_format(structured_format)
        logger.add(
            sys.stderr,
            format=console_format,
            level=level,
            colorize=True,
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )

        # Configure file logging if enabled
        if enable_file_logging:
            if log_file_path is None:
                log_file_path = Path.cwd() / "logs" / f"{self.service_name}.log"

            log_file_path.parent.mkdir(parents=True, exist_ok=True)

            file_format = self._get_file_format(structured_format)
            logger.add(
                str(log_file_path),
                format=file_format,
                level=level,
                rotation="10 MB",
                retention="30 days",
                compression="gz",
                backtrace=True,
                diagnose=True,
                enqueue=True,
                serialize=structured_format,  # JSON format for structured logs
            )

        # Add correlation IDs and service information
        logger.configure(
            extra={
                "service_name": self.service_name,
                "version": "1.0.0",
            }
        )

        self._configured = True
        logger.info(
            "Logging configured",
            service=self.service_name,
            level=level,
            file_logging=enable_file_logging,
            structured=structured_format,
        )

    def _get_console_format(self, structured: bool) -> str:
        """Get console logging format."""
        if structured:
            return (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level> | "
                "{extra}"
            )
        else:
            return (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            )

    def _get_file_format(self, structured: bool) -> str:
        """Get file logging format."""
        if structured:
            # JSON format handled by serialize=True
            return "{time} | {level} | {name}:{function}:{line} | {message} | {extra}"
        else:
            return (
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
                "{name}:{function}:{line} | {message}"
            )

    def get_logger(self, name: str) -> Any:
        """
        Get a logger instance with the given name.

        Args:
            name: Logger name (usually __name__)

        Returns:
            Configured logger instance
        """
        return logger.bind(component=name)

    def log_operation_start(self, operation: str, **kwargs) -> None:
        """Log the start of an operation with context."""
        logger.info("Operation started", operation=operation, **kwargs)

    def log_operation_complete(self, operation: str, duration: float, **kwargs) -> None:
        """Log the completion of an operation with metrics."""
        logger.info(
            "Operation completed",
            operation=operation,
            duration_seconds=duration,
            **kwargs,
        )

    def log_operation_error(self, operation: str, error: Exception, **kwargs) -> None:
        """Log an operation error with context."""
        logger.error(
            "Operation failed",
            operation=operation,
            error_type=type(error).__name__,
            error_message=str(error),
            **kwargs,
        )

    def log_rate_limit_status(self, status: dict[str, Any]) -> None:
        """Log rate limit status information."""
        logger.debug("Rate limit status", **status)

    def log_api_request(
        self, method: str, url: str, status_code: int, duration: float
    ) -> None:
        """Log API request information."""
        level = "WARNING" if status_code >= 400 else "DEBUG"
        logger.log(
            level,
            "API request",
            method=method,
            url=url,
            status_code=status_code,
            duration_seconds=duration,
        )

    def log_cache_operation(
        self, operation: str, key: str, hit: bool | None = None, **kwargs
    ) -> None:
        """Log cache operations."""
        logger.debug(
            "Cache operation", operation=operation, key=key, cache_hit=hit, **kwargs
        )

    def log_validation_result(
        self, category: str, passed: bool, details: str | None = None
    ) -> None:
        """Log validation results."""
        level = "INFO" if passed else "WARNING"
        logger.log(
            level,
            "Validation result",
            category=category,
            passed=passed,
            details=details,
        )


# Global logging manager instance
_logging_manager: LoggingManager | None = None


def get_logging_manager() -> LoggingManager:
    """Get or create the global logging manager instance."""
    global _logging_manager
    if _logging_manager is None:
        _logging_manager = LoggingManager()
    return _logging_manager


def configure_logging(
    level: str | None = None,
    structured: bool = True,
    enable_file_logging: bool | None = None,
) -> None:
    """
    Configure application logging with sensible defaults.

    Args:
        level: Logging level from environment or default to INFO
        structured: Enable structured JSON logging
        enable_file_logging: Enable file logging (default: True in production)
    """
    # Get configuration from environment
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()

    if enable_file_logging is None:
        enable_file_logging = os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true"

    # Configure the global logging manager
    manager = get_logging_manager()
    manager.configure_logging(
        level=level,
        structured_format=structured,
        enable_file_logging=enable_file_logging,
    )


def get_logger(name: str) -> Any:
    """
    Get a logger instance for the given component.

    Args:
        name: Component name (usually __name__)

    Returns:
        Configured logger instance
    """
    manager = get_logging_manager()
    return manager.get_logger(name)


# Auto-configure logging on import with environment-based settings
try:
    # Only auto-configure if we're in the main application context
    if "pytest" not in sys.modules and Path.cwd().name == "documentation-toolkit":
        configure_logging()
except Exception:
    # Ignore configuration errors during import
    pass
