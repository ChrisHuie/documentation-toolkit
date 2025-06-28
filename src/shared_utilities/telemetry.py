"""
OpenTelemetry instrumentation utilities for monitoring and observability
"""

import functools
import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

try:
    from opentelemetry import trace as otel_trace  # type: ignore
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore
    from opentelemetry.sdk.trace.export import (  # type: ignore
        BatchSpanProcessor,
    )

    # Optional OTLP exporter - only import if available
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore
            OTLPSpanExporter,
        )

        OTLP_AVAILABLE = True
    except ImportError:
        OTLP_AVAILABLE = False
    from opentelemetry.sdk.resources import Resource  # type: ignore

    # Optional instrumentation - only import if available
    try:
        from opentelemetry.instrumentation.requests import (
            RequestsInstrumentor,  # type: ignore
        )
        from opentelemetry.instrumentation.urllib3 import (
            URLLib3Instrumentor,  # type: ignore
        )

        INSTRUMENTATION_AVAILABLE = True
    except ImportError:
        INSTRUMENTATION_AVAILABLE = False
    from opentelemetry.trace import Status, StatusCode  # type: ignore

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    OTLP_AVAILABLE = False
    INSTRUMENTATION_AVAILABLE = False


class TelemetryManager:
    """Manages OpenTelemetry setup and instrumentation"""

    def __init__(self, service_name: str = "documentation-toolkit"):
        """
        Initialize telemetry manager.

        Args:
            service_name: Name of the service for telemetry identification
        """
        self.service_name = service_name
        self.tracer = None
        self.enabled = OTEL_AVAILABLE

        if self.enabled:
            self._setup_telemetry()

    def _setup_telemetry(self) -> None:
        """Set up OpenTelemetry tracing"""
        # Create resource with service information
        resource = Resource.create(
            {
                "service.name": self.service_name,
                "service.version": "1.0.0",
            }
        )

        # Set up tracer provider
        otel_trace.set_tracer_provider(TracerProvider(resource=resource))

        # Set up span processors
        tracer_provider = otel_trace.get_tracer_provider()

        # Console exporter disabled for now to avoid test issues
        # In production, you can uncomment this section if needed:
        # console_exporter = ConsoleSpanExporter()
        # console_processor = BatchSpanProcessor(console_exporter)
        # tracer_provider.add_span_processor(console_processor)

        # OTLP exporter for production (if endpoint is configured and OTLP is available)
        if OTLP_AVAILABLE:
            otlp_endpoint = self._get_otlp_endpoint()
            if otlp_endpoint:
                otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                otlp_processor = BatchSpanProcessor(otlp_exporter)
                tracer_provider.add_span_processor(otlp_processor)  # type: ignore

        # Get tracer
        self.tracer = otel_trace.get_tracer(__name__)  # type: ignore

        # Instrument common libraries (if instrumentation is available)
        if INSTRUMENTATION_AVAILABLE:
            RequestsInstrumentor().instrument()
            URLLib3Instrumentor().instrument()

    def _get_otlp_endpoint(self) -> str | None:
        """Get OTLP endpoint from environment variables"""
        import os

        return os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    @contextmanager
    def trace_operation(
        self, operation_name: str, attributes: dict[str, Any] | None = None
    ):
        """
        Context manager for tracing operations.

        Args:
            operation_name: Name of the operation being traced
            attributes: Additional attributes to add to the span

        Yields:
            The current span
        """
        if not self.enabled or not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(operation_name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))

            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def trace_function(
        self,
        operation_name: str | None = None,
        include_args: bool = False,
        include_result: bool = False,
    ):
        """
        Decorator for tracing function calls.

        Args:
            operation_name: Custom operation name (defaults to function name)
            include_args: Whether to include function arguments as attributes
            include_result: Whether to include return value as attribute

        Returns:
            Decorated function
        """

        def decorator(func: Callable) -> Callable:
            if not self.enabled:
                return func

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                name = operation_name or f"{func.__module__}.{func.__name__}"

                with self.trace_operation(name) as span:
                    if span and include_args:
                        # Add function arguments as attributes
                        for i, arg in enumerate(args):
                            span.set_attribute(
                                f"arg.{i}", str(arg)[:100]
                            )  # Limit length

                        for key, value in kwargs.items():
                            span.set_attribute(
                                f"kwarg.{key}", str(value)[:100]
                            )  # Limit length

                    start_time = time.time()
                    try:
                        result = func(*args, **kwargs)

                        if span:
                            duration = time.time() - start_time
                            span.set_attribute("duration_seconds", duration)

                            if include_result and result is not None:
                                span.set_attribute(
                                    "result", str(result)[:100]
                                )  # Limit length

                        return result

                    except Exception as e:
                        if span:
                            span.set_status(Status(StatusCode.ERROR, str(e)))
                            span.record_exception(e)
                        raise

            return wrapper

        return decorator

    def add_event(
        self, span, event_name: str, attributes: dict[str, Any] | None = None
    ):
        """
        Add an event to the current span.

        Args:
            span: The span to add the event to
            event_name: Name of the event
            attributes: Additional attributes for the event
        """
        if span and self.enabled:
            span.add_event(event_name, attributes or {})

    def set_attribute(self, span, key: str, value: Any):
        """
        Set an attribute on the current span.

        Args:
            span: The span to set the attribute on
            key: Attribute key
            value: Attribute value
        """
        if span and self.enabled:
            span.set_attribute(key, str(value))

    def record_metrics(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        additional_tags: dict[str, str] | None = None,
    ):
        """
        Record custom metrics for operations.

        Args:
            operation: Name of the operation
            duration: Duration in seconds
            success: Whether the operation was successful
            additional_tags: Additional tags for the metric
        """
        # This is a placeholder for custom metrics
        # In a full implementation, you would use OpenTelemetry metrics
        pass


# Global telemetry manager instance
_telemetry_manager: TelemetryManager | None = None


def get_telemetry_manager() -> TelemetryManager:
    """Get or create the global telemetry manager instance"""
    global _telemetry_manager
    if _telemetry_manager is None:
        _telemetry_manager = TelemetryManager()
    return _telemetry_manager


def trace_operation(operation_name: str, attributes: dict[str, Any] | None = None):
    """
    Convenience function for tracing operations.

    Args:
        operation_name: Name of the operation
        attributes: Additional attributes
    """
    return get_telemetry_manager().trace_operation(operation_name, attributes)


def trace_function(
    operation_name: str | None = None,
    include_args: bool = False,
    include_result: bool = False,
):
    """
    Convenience decorator for tracing functions.

    Args:
        operation_name: Custom operation name
        include_args: Whether to include function arguments
        include_result: Whether to include return value
    """
    return get_telemetry_manager().trace_function(
        operation_name, include_args, include_result
    )


def is_telemetry_enabled() -> bool:
    """Check if telemetry is available and enabled"""
    return OTEL_AVAILABLE and get_telemetry_manager().enabled


# Backwards compatibility aliases
trace = trace_operation
instrument = trace_function
