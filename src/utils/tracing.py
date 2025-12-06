"""
OpenTelemetry Distributed Tracing
分布式追踪 - 优化项 #15
"""

import os
import asyncio
from typing import Optional
from contextlib import contextmanager

from .settings import settings
from .logger import setup_logging

logger = setup_logging("tracing")


# Check if OpenTelemetry is available
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.info("OpenTelemetry not installed, tracing disabled")


def setup_tracing(
    service_name: str = "precious-metals-api",
    otlp_endpoint: Optional[str] = None,
    console_export: bool = False
):
    """
    Setup OpenTelemetry tracing
    """
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available")
        return
    
    # Create resource
    resource = Resource.create({
        "service.name": service_name,
        "service.version": settings.app_version,
        "deployment.environment": settings.environment
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Add console exporter if enabled
    if console_export:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    
    # Set as global provider
    trace.set_tracer_provider(provider)
    
    logger.info(f"Tracing initialized for {service_name}")


def get_tracer(name: str):
    """Get a tracer instance"""
    if OTEL_AVAILABLE:
        return trace.get_tracer(name)
    return NoOpTracer()


class NoOpTracer:
    """No-op tracer when OpenTelemetry is not available"""
    
    @contextmanager
    def start_as_current_span(self, name: str, **kwargs):
        yield NoOpSpan()
    
    def start_span(self, name: str, **kwargs):
        return NoOpSpan()


class NoOpSpan:
    """No-op span"""
    
    def set_attribute(self, key: str, value):
        pass
    
    def set_status(self, status):
        pass
    
    def add_event(self, name: str, attributes=None):
        pass
    
    def record_exception(self, exception):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


def instrument_fastapi(app):
    """Instrument FastAPI application"""
    if not OTEL_AVAILABLE:
        return
    
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented with OpenTelemetry")
    except ImportError:
        logger.warning("FastAPI instrumentor not available")


def traced(name: Optional[str] = None):
    """Decorator to trace a function"""
    def decorator(func):
        span_name = name or func.__name__
        tracer = get_tracer(func.__module__)
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        raise
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        raise
            return sync_wrapper
    
    return decorator


if __name__ == "__main__":
    print("Testing Tracing...")
    setup_tracing(console_export=True)
    tracer = get_tracer("test")
    
    with tracer.start_as_current_span("test_operation") as span:
        span.set_attribute("test.key", "value")
        print("Inside traced span")
    
    print("Tracing test complete!")
