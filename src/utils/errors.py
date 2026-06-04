"""
Error Handling and Custom Exceptions
错误处理和自定义异常
"""

from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logger import setup_logging

logger = setup_logging("errors")


# ============================================================================
# Custom Exceptions
# ============================================================================

class BaseAPIException(Exception):
    """Base exception for API errors"""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or f"ERR_{status_code}"
        self.details = details or {}
        super().__init__(message)


class ValidationError(BaseAPIException):
    """Data validation error"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details={"field": field} if field else {}
        )


class NotFoundError(BaseAPIException):
    """Resource not found error"""
    
    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier}
        )


class AuthenticationError(BaseAPIException):
    """Authentication error"""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_ERROR"
        )


class AuthorizationError(BaseAPIException):
    """Authorization/permission error"""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN"
        )


class RateLimitError(BaseAPIException):
    """Rate limit exceeded error"""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT",
            details={"retry_after": retry_after}
        )


class DataFetchError(BaseAPIException):
    """Error fetching external data"""
    
    def __init__(self, source: str, message: str):
        super().__init__(
            message=f"Failed to fetch data from {source}: {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="DATA_FETCH_ERROR",
            details={"source": source}
        )


class ModelError(BaseAPIException):
    """ML model error"""
    
    def __init__(self, model: str, message: str):
        super().__init__(
            message=f"Model error ({model}): {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="MODEL_ERROR",
            details={"model": model}
        )


class DatabaseError(BaseAPIException):
    """Database operation error"""
    
    def __init__(self, operation: str, message: str):
        super().__init__(
            message=f"Database error during {operation}: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DB_ERROR",
            details={"operation": operation}
        )


class ExternalServiceError(BaseAPIException):
    """External service error"""
    
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service error ({service}): {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="EXTERNAL_ERROR",
            details={"service": service}
        )


# ============================================================================
# Error Response
# ============================================================================

def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[Dict] = None,
    request_id: Optional[str] = None
) -> Dict:
    """Create standardized error response"""
    return {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }
    }


# ============================================================================
# Exception Handlers
# ============================================================================

async def base_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """Handle custom API exceptions"""
    request_id = request.headers.get("X-Request-ID")
    
    logger.error(
        f"{exc.error_code}: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "request_id": request_id,
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=request_id
        )
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    request_id = request.headers.get("X-Request-ID")
    
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={"path": request.url.path, "request_id": request_id}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            status_code=exc.status_code,
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            request_id=request_id
        )
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors"""
    request_id = request.headers.get("X-Request-ID")
    
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Validation error: {len(errors)} errors",
        extra={"path": request.url.path, "errors": errors}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            status_code=422,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": errors},
            request_id=request_id
        )
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    request_id = request.headers.get("X-Request-ID")
    
    logger.exception(
        f"Unexpected error: {exc}",
        extra={"path": request.url.path, "request_id": request_id}
    )
    
    # Don't expose internal error details in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            request_id=request_id
        )
    )


def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app"""
    app.add_exception_handler(BaseAPIException, base_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Exception handlers registered")


# ============================================================================
# Error Utilities
# ============================================================================

def safe_execute(func, *args, default=None, log_error=True, **kwargs):
    """
    Safely execute a function, returning default on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"Error in {func.__name__}: {e}")
        return default


async def safe_execute_async(coro, default=None, log_error=True):
    """
    Safely execute async coroutine
    """
    try:
        return await coro
    except Exception as e:
        if log_error:
            logger.error(f"Async error: {e}")
        return default


class ErrorTracker:
    """
    Track errors for monitoring
    """
    
    def __init__(self, max_errors: int = 1000):
        self.max_errors = max_errors
        self.errors: list = []
    
    def record(self, error: Exception, context: Optional[Dict] = None):
        """Record an error"""
        entry = {
            "type": type(error).__name__,
            "message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        }
        
        self.errors.append(entry)
        
        # Trim if too many
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
    
    def get_recent(self, n: int = 10) -> list:
        """Get recent errors"""
        return self.errors[-n:]
    
    def get_stats(self) -> Dict:
        """Get error statistics"""
        from collections import Counter
        
        type_counts = Counter(e["type"] for e in self.errors)
        
        return {
            "total": len(self.errors),
            "by_type": dict(type_counts.most_common(10))
        }


# Global error tracker
error_tracker = ErrorTracker()


if __name__ == "__main__":
    print("Testing Error Handling...")
    
    # Test exceptions
    try:
        raise NotFoundError("User", "123")
    except BaseAPIException as e:
        print(f"Exception: {e.error_code} - {e.message}")
    
    # Test error tracker
    error_tracker.record(ValueError("Test error"), {"context": "test"})
    print(f"Error stats: {error_tracker.get_stats()}")
    
    print("\nError handling test complete!")
