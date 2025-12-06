"""
Structured Logging with structlog
结构化日志
"""

import sys
import logging
from typing import Optional
from datetime import datetime

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

from .config import get_settings

settings = get_settings()


def configure_structlog():
    """Configure structlog for structured logging"""
    if not STRUCTLOG_AVAILABLE:
        return
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # JSON output for production, console for development
    if getattr(settings, 'environment', 'development') == 'production':
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_struct_logger(name: str):
    """Get structured logger instance"""
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        # Fallback to standard logging
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        return logger


class RequestLogger:
    """
    Request logging utilities
    """
    
    def __init__(self, name: str = "api"):
        self.logger = get_struct_logger(name)
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **extra
    ):
        """Log API request"""
        self.logger.info(
            "api_request",
            method=method,
            path=path,
            status_code=status_code,
            latency_ms=round(latency_ms, 2),
            user_id=user_id,
            request_id=request_id,
            **extra
        )
    
    def log_error(
        self,
        error_type: str,
        message: str,
        request_id: Optional[str] = None,
        **extra
    ):
        """Log error"""
        self.logger.error(
            "api_error",
            error_type=error_type,
            message=message,
            request_id=request_id,
            **extra
        )
    
    def log_data_fetch(
        self,
        source: str,
        symbol: str,
        status: str,
        latency_ms: float,
        record_count: int = 0
    ):
        """Log data fetch operation"""
        self.logger.info(
            "data_fetch",
            source=source,
            symbol=symbol,
            status=status,
            latency_ms=round(latency_ms, 2),
            record_count=record_count
        )
    
    def log_prediction(
        self,
        model: str,
        symbol: str,
        prediction: float,
        confidence: float,
        latency_ms: float
    ):
        """Log model prediction"""
        self.logger.info(
            "model_prediction",
            model=model,
            symbol=symbol,
            prediction=prediction,
            confidence=confidence,
            latency_ms=round(latency_ms, 2)
        )
    
    def log_alert(
        self,
        alert_type: str,
        severity: str,
        symbol: str,
        message: str
    ):
        """Log alert triggered"""
        self.logger.warning(
            "alert_triggered",
            alert_type=alert_type,
            severity=severity,
            symbol=symbol,
            message=message
        )


# Global request logger
request_logger = RequestLogger()


# ============================================================================
# Logging Middleware
# ============================================================================

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request logging
    """
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
        self.logger = RequestLogger()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip logging for excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)
        
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", str(id(request)))
        
        # Add to context
        if STRUCTLOG_AVAILABLE:
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(request_id=request_id)
        
        try:
            response = await call_next(request)
            latency_ms = (time.time() - start_time) * 1000
            
            self.logger.log_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=latency_ms,
                request_id=request_id,
                client_ip=request.client.host if request.client else None
            )
            
            # Add request ID to response
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            self.logger.log_error(
                error_type=type(e).__name__,
                message=str(e),
                request_id=request_id,
                path=request.url.path,
                latency_ms=latency_ms
            )
            raise


# Initialize structlog on import
configure_structlog()


if __name__ == "__main__":
    print("Testing Structured Logging...")
    
    logger = get_struct_logger("test")
    logger.info("test_event", key="value", number=42)
    
    req_logger = RequestLogger()
    req_logger.log_request(
        method="GET",
        path="/api/v1/prices/GLD",
        status_code=200,
        latency_ms=45.5,
        user_id="user123"
    )
    
    print("Structured logging test complete!")
