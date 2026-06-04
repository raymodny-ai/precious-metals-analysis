"""
Slowapi Rate Limiter Integration
slowapi速率限制 - 优化项 #7
"""

from typing import Optional
from fastapi import FastAPI, Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .settings import settings
from .logger import setup_logging

logger = setup_logging("slowapi")


def get_limiter_key(request: Request) -> str:
    """
    Get rate limit key from request
    
    Priority:
    1. API key from header
    2. User ID from JWT
    3. Client IP address
    """
    # Check for API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key[:16]}"
    
    # Check for authenticated user
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        # Use token hash as key (don't expose full token)
        import hashlib
        token_hash = hashlib.md5(auth_header.encode()).hexdigest()[:16]
        return f"user:{token_hash}"
    
    # Fall back to IP address
    return get_remote_address(request)


# Create limiter with custom key function
limiter = Limiter(
    key_func=get_limiter_key,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
    storage_uri=settings.redis_url if settings.redis_url else None,
    strategy="fixed-window"
)


def setup_rate_limiting(app: FastAPI):
    """
    Setup rate limiting for FastAPI app
    
    Usage:
        from src.utils.slowapi_limiter import setup_rate_limiting
        
        app = FastAPI()
        setup_rate_limiting(app)
    """
    if not settings.rate_limit_enabled:
        logger.info("Rate limiting disabled")
        return
    
    # Add limiter to app state
    app.state.limiter = limiter
    
    # Add exception handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add middleware
    app.add_middleware(SlowAPIMiddleware)
    
    logger.info(f"Rate limiting enabled: {settings.rate_limit_per_minute}/minute")


# ============================================================================
# Preset rate limits for different endpoint types
# ============================================================================

# Standard limits
LIMIT_STANDARD = f"{settings.rate_limit_per_minute}/minute"  # 100/min
LIMIT_STRICT = "30/minute"   # For expensive operations
LIMIT_RELAXED = "200/minute"  # For simple reads

# Burst limits
LIMIT_BURST_1 = "10/second"
LIMIT_BURST_5 = "5/second"

# Auth limits (prevent brute force)
LIMIT_AUTH = "10/minute"

# Data-intensive endpoints
LIMIT_DATA = "20/minute"

# Prediction endpoints (expensive)
LIMIT_PREDICTION = "10/minute"


# ============================================================================
# Usage Examples
# ============================================================================
"""
from fastapi import FastAPI, Request
from src.utils.slowapi_limiter import limiter, LIMIT_STANDARD, LIMIT_STRICT

app = FastAPI()

@app.get("/api/v1/prices/{symbol}")
@limiter.limit(LIMIT_STANDARD)
async def get_prices(request: Request, symbol: str):
    pass

@app.post("/api/v1/predictions")
@limiter.limit(LIMIT_STRICT)
async def create_prediction(request: Request):
    pass

@app.post("/api/v1/auth/login")
@limiter.limit(LIMIT_AUTH)
async def login(request: Request):
    pass
"""
