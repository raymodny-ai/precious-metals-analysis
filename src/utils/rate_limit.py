"""
API Rate Limiting and Request Validation
API速率限制和请求验证
"""

import time
import hashlib
from typing import Optional, Dict, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import asyncio

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .logger import setup_logging
from .config import get_settings

logger = setup_logging("rate_limit")
settings = get_settings()


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10
    window_seconds: int = 60


@dataclass
class RateLimitRecord:
    """Record for tracking rate limits"""
    request_times: list = field(default_factory=list)
    hourly_count: int = 0
    hourly_reset: float = 0
    
    def clean_old_requests(self, window: int):
        """Remove requests outside window"""
        cutoff = time.time() - window
        self.request_times = [t for t in self.request_times if t > cutoff]


class InMemoryRateLimiter:
    """
    In-memory rate limiter
    
    For production, use Redis-based limiter
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.records: Dict[str, RateLimitRecord] = defaultdict(RateLimitRecord)
        self._lock = asyncio.Lock()
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Use IP + User-Agent hash for identification
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        
        # Check for API key or auth token
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # Use token hash for authenticated users
            token_hash = hashlib.md5(auth_header.encode()).hexdigest()[:16]
            return f"token:{token_hash}"
        
        return f"ip:{client_ip}"
    
    async def is_allowed(self, request: Request) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limits
        
        Returns:
            (allowed, headers_dict)
        """
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        async with self._lock:
            record = self.records[client_id]
            
            # Clean old requests
            record.clean_old_requests(self.config.window_seconds)
            
            # Check hourly limit
            if current_time > record.hourly_reset:
                record.hourly_count = 0
                record.hourly_reset = current_time + 3600
            
            # Calculate limits
            minute_count = len(record.request_times)
            remaining = self.config.requests_per_minute - minute_count
            hourly_remaining = self.config.requests_per_hour - record.hourly_count
            
            headers = {
                "X-RateLimit-Limit": str(self.config.requests_per_minute),
                "X-RateLimit-Remaining": str(max(0, remaining)),
                "X-RateLimit-Reset": str(int(current_time + self.config.window_seconds)),
                "X-RateLimit-Hourly-Remaining": str(max(0, hourly_remaining))
            }
            
            # Check if allowed
            if minute_count >= self.config.requests_per_minute:
                headers["Retry-After"] = str(self.config.window_seconds)
                return False, headers
            
            if record.hourly_count >= self.config.requests_per_hour:
                headers["Retry-After"] = str(int(record.hourly_reset - current_time))
                return False, headers
            
            # Record request
            record.request_times.append(current_time)
            record.hourly_count += 1
            
            return True, headers
    
    def reset(self, client_id: Optional[str] = None):
        """Reset rate limit records"""
        if client_id:
            if client_id in self.records:
                del self.records[client_id]
        else:
            self.records.clear()


class RedisRateLimiter:
    """
    Redis-based rate limiter for distributed systems
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._client = None
        
        try:
            import redis
            self._client = redis.from_url(
                getattr(settings, 'redis_url', 'redis://localhost:6379/0')
            )
        except Exception as e:
            logger.warning(f"Redis rate limiter unavailable: {e}")
    
    async def is_allowed(self, request: Request) -> tuple[bool, Dict[str, Any]]:
        """Check if request is allowed"""
        if self._client is None:
            # Fallback: allow all if Redis unavailable
            return True, {}
        
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"
        
        try:
            pipe = self._client.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.config.window_seconds)
            results = pipe.execute()
            
            count = results[0]
            remaining = max(0, self.config.requests_per_minute - count)
            
            headers = {
                "X-RateLimit-Limit": str(self.config.requests_per_minute),
                "X-RateLimit-Remaining": str(remaining),
            }
            
            if count > self.config.requests_per_minute:
                headers["Retry-After"] = str(self.config.window_seconds)
                return False, headers
            
            return True, headers
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True, {}


# Global rate limiter
rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting
    """
    
    def __init__(
        self,
        app,
        limiter: Optional[InMemoryRateLimiter] = None,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.limiter = limiter or rate_limiter
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)
        
        # Check rate limit
        allowed, headers = await self.limiter.is_allowed(request)
        
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too many requests",
                    "message": "Rate limit exceeded. Please try again later."
                },
                headers=headers
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


# ============================================================================
# Request Validation
# ============================================================================

class RequestValidator:
    """
    Request validation utilities
    """
    
    ALLOWED_SYMBOLS = [
        "GLD", "IAU", "GLDM", "SGOL", "PHYS",
        "SLV", "SIVR", "PSLV", "AGQ"
    ]
    
    VALID_INTERVALS = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
    
    @staticmethod
    def validate_symbol(symbol: str) -> str:
        """Validate trading symbol"""
        symbol = symbol.upper().strip()
        
        if not symbol:
            raise HTTPException(
                status_code=400,
                detail="Symbol is required"
            )
        
        if symbol not in RequestValidator.ALLOWED_SYMBOLS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid symbol. Allowed: {', '.join(RequestValidator.ALLOWED_SYMBOLS)}"
            )
        
        return symbol
    
    @staticmethod
    def validate_interval(interval: str) -> str:
        """Validate time interval"""
        interval = interval.lower().strip()
        
        if interval not in RequestValidator.VALID_INTERVALS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Allowed: {', '.join(RequestValidator.VALID_INTERVALS)}"
            )
        
        return interval
    
    @staticmethod
    def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> tuple:
        """Validate date range"""
        from datetime import datetime
        
        if start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid start_date format. Use YYYY-MM-DD"
                )
        else:
            start = None
        
        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid end_date format. Use YYYY-MM-DD"
                )
        else:
            end = None
        
        if start and end and start > end:
            raise HTTPException(
                status_code=400,
                detail="start_date must be before end_date"
            )
        
        return start, end
    
    @staticmethod
    def validate_limit(limit: int, max_limit: int = 1000) -> int:
        """Validate limit parameter"""
        if limit < 1:
            raise HTTPException(
                status_code=400,
                detail="Limit must be at least 1"
            )
        
        if limit > max_limit:
            raise HTTPException(
                status_code=400,
                detail=f"Limit cannot exceed {max_limit}"
            )
        
        return limit


# FastAPI dependency
def validate_symbol(symbol: str) -> str:
    """Dependency for symbol validation"""
    return RequestValidator.validate_symbol(symbol)


def validate_interval(interval: str = "1d") -> str:
    """Dependency for interval validation"""
    return RequestValidator.validate_interval(interval)


if __name__ == "__main__":
    print("Testing Rate Limiter...")
    
    # Simulate requests
    import asyncio
    from unittest.mock import Mock
    
    async def test():
        limiter = InMemoryRateLimiter(RateLimitConfig(requests_per_minute=5))
        
        mock_request = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {}
        
        for i in range(7):
            allowed, headers = await limiter.is_allowed(mock_request)
            print(f"Request {i+1}: {'Allowed' if allowed else 'Blocked'}, Remaining: {headers.get('X-RateLimit-Remaining')}")
    
    asyncio.run(test())
    
    print("\nRate limiter test complete!")
