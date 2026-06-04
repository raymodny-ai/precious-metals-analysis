"""
Redis Cache Layer
Redis缓存层
高性能数据缓存
"""

import json
import pickle
import hashlib
from typing import Optional, Any, Union, Callable, TypeVar
from datetime import timedelta
from functools import wraps
import asyncio

from .logger import setup_logging
from .config import get_settings

logger = setup_logging("cache")
settings = get_settings()

T = TypeVar('T')


class CacheConfig:
    """Cache configuration"""
    
    # TTL defaults (in seconds)
    PRICE_TTL = 60          # 1 minute for prices
    NEWS_TTL = 300          # 5 minutes for news
    SENTIMENT_TTL = 600     # 10 minutes for sentiment
    PREDICTION_TTL = 3600   # 1 hour for predictions
    ETF_FLOW_TTL = 1800     # 30 minutes for ETF flows
    USER_TTL = 86400        # 24 hours for user data


class RedisCache:
    """
    Redis-based caching layer
    
    Features:
    - Automatic serialization/deserialization
    - TTL management
    - Cache invalidation
    - Pattern-based operations
    - Async support
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or getattr(settings, 'redis_url', 'redis://localhost:6379/0')
        self._sync_client = None
        self._async_client = None
        self._initialized = False
        
        self._init_client()
    
    def _init_client(self):
        """Initialize Redis client"""
        try:
            import redis
            
            self._sync_client = redis.from_url(
                self.redis_url,
                decode_responses=False,  # We handle encoding ourselves
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Test connection
            self._sync_client.ping()
            self._initialized = True
            logger.info(f"Redis connected: {self.redis_url}")
            
        except ImportError:
            logger.warning("redis-py not installed")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
    
    async def _get_async_client(self):
        """Get async Redis client"""
        if self._async_client is None:
            try:
                import redis.asyncio as aioredis
                self._async_client = await aioredis.from_url(
                    self.redis_url,
                    decode_responses=False
                )
            except Exception as e:
                logger.warning(f"Async Redis failed: {e}")
                return None
        return self._async_client
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Try JSON first for simple types
            return json.dumps(value, default=str).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        if data is None:
            return None
        
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return pickle.loads(data)
    
    def _make_key(self, key: str, prefix: str = "pm") -> str:
        """Create prefixed cache key"""
        return f"{prefix}:{key}"
    
    # ========== Sync Operations ==========
    
    def get(self, key: str, prefix: str = "pm") -> Optional[Any]:
        """Get value from cache"""
        if not self._initialized:
            return None
        
        try:
            full_key = self._make_key(key, prefix)
            data = self._sync_client.get(full_key)
            return self._deserialize(data)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        prefix: str = "pm"
    ) -> bool:
        """Set value in cache with TTL"""
        if not self._initialized:
            return False
        
        try:
            full_key = self._make_key(key, prefix)
            data = self._serialize(value)
            self._sync_client.setex(full_key, ttl, data)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str, prefix: str = "pm") -> bool:
        """Delete key from cache"""
        if not self._initialized:
            return False
        
        try:
            full_key = self._make_key(key, prefix)
            self._sync_client.delete(full_key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str, prefix: str = "pm") -> int:
        """Delete all keys matching pattern"""
        if not self._initialized:
            return 0
        
        try:
            full_pattern = self._make_key(pattern, prefix)
            keys = self._sync_client.keys(full_pattern)
            if keys:
                return self._sync_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0
    
    def exists(self, key: str, prefix: str = "pm") -> bool:
        """Check if key exists"""
        if not self._initialized:
            return False
        
        try:
            full_key = self._make_key(key, prefix)
            return bool(self._sync_client.exists(full_key))
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    def ttl(self, key: str, prefix: str = "pm") -> int:
        """Get TTL for key"""
        if not self._initialized:
            return -1
        
        try:
            full_key = self._make_key(key, prefix)
            return self._sync_client.ttl(full_key)
        except Exception as e:
            logger.error(f"Cache ttl error: {e}")
            return -1
    
    # ========== Async Operations ==========
    
    async def aget(self, key: str, prefix: str = "pm") -> Optional[Any]:
        """Async get value from cache"""
        client = await self._get_async_client()
        if client is None:
            return None
        
        try:
            full_key = self._make_key(key, prefix)
            data = await client.get(full_key)
            return self._deserialize(data)
        except Exception as e:
            logger.error(f"Async cache get error: {e}")
            return None
    
    async def aset(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        prefix: str = "pm"
    ) -> bool:
        """Async set value in cache"""
        client = await self._get_async_client()
        if client is None:
            return False
        
        try:
            full_key = self._make_key(key, prefix)
            data = self._serialize(value)
            await client.setex(full_key, ttl, data)
            return True
        except Exception as e:
            logger.error(f"Async cache set error: {e}")
            return False
    
    # ========== Hash Operations ==========
    
    def hget(self, name: str, key: str, prefix: str = "pm") -> Optional[Any]:
        """Get field from hash"""
        if not self._initialized:
            return None
        
        try:
            full_name = self._make_key(name, prefix)
            data = self._sync_client.hget(full_name, key)
            return self._deserialize(data)
        except Exception as e:
            logger.error(f"Cache hget error: {e}")
            return None
    
    def hset(self, name: str, key: str, value: Any, prefix: str = "pm") -> bool:
        """Set field in hash"""
        if not self._initialized:
            return False
        
        try:
            full_name = self._make_key(name, prefix)
            data = self._serialize(value)
            self._sync_client.hset(full_name, key, data)
            return True
        except Exception as e:
            logger.error(f"Cache hset error: {e}")
            return False
    
    def hgetall(self, name: str, prefix: str = "pm") -> dict:
        """Get all fields from hash"""
        if not self._initialized:
            return {}
        
        try:
            full_name = self._make_key(name, prefix)
            raw = self._sync_client.hgetall(full_name)
            return {
                k.decode(): self._deserialize(v)
                for k, v in raw.items()
            }
        except Exception as e:
            logger.error(f"Cache hgetall error: {e}")
            return {}
    
    # ========== Statistics ==========
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self._initialized:
            return {"status": "disconnected"}
        
        try:
            info = self._sync_client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "keys": self._sync_client.dbsize(),
                "hit_rate": info.get("keyspace_hits", 0) / max(
                    info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1), 1
                )
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"status": "error", "message": str(e)}
    
    def flush(self):
        """Flush all cache"""
        if self._initialized:
            self._sync_client.flushdb()
            logger.info("Cache flushed")


# Global cache instance
cache = RedisCache()


# ============================================================================
# Decorators
# ============================================================================

def cached(
    ttl: int = 3600,
    prefix: str = "pm",
    key_builder: Optional[Callable] = None
):
    """
    Decorator for caching function results
    
    Usage:
        @cached(ttl=300)
        def get_data(symbol: str):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key from function name and args
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try cache
            cached_value = cache.get(cache_key, prefix)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, ttl, prefix)
            logger.debug(f"Cache set: {cache_key}")
            
            return result
        
        return wrapper
    return decorator


def async_cached(
    ttl: int = 3600,
    prefix: str = "pm",
    key_builder: Optional[Callable] = None
):
    """Async version of cached decorator"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try cache
            cached_value = await cache.aget(cache_key, prefix)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.aset(cache_key, result, ttl, prefix)
            
            return result
        
        return wrapper
    return decorator


# ============================================================================
# Specialized Cache Functions
# ============================================================================

def cache_price(symbol: str, data: dict):
    """Cache price data"""
    cache.set(f"price:{symbol}", data, CacheConfig.PRICE_TTL)


def get_cached_price(symbol: str) -> Optional[dict]:
    """Get cached price"""
    return cache.get(f"price:{symbol}")


def cache_sentiment(symbol: str, data: dict):
    """Cache sentiment data"""
    cache.set(f"sentiment:{symbol}", data, CacheConfig.SENTIMENT_TTL)


def get_cached_sentiment(symbol: str) -> Optional[dict]:
    """Get cached sentiment"""
    return cache.get(f"sentiment:{symbol}")


def invalidate_symbol_cache(symbol: str):
    """Invalidate all cache for a symbol"""
    cache.delete_pattern(f"*:{symbol}*")
    logger.info(f"Invalidated cache for {symbol}")


if __name__ == "__main__":
    print("Testing Redis Cache...")
    
    # Test basic operations
    cache.set("test", {"value": 123}, ttl=60)
    result = cache.get("test")
    print(f"Set/Get: {result}")
    
    # Test decorator
    @cached(ttl=60)
    def expensive_function(x: int) -> int:
        print("Computing...")
        return x * 2
    
    print(f"First call: {expensive_function(5)}")
    print(f"Second call (cached): {expensive_function(5)}")
    
    # Stats
    print(f"Stats: {cache.get_stats()}")
