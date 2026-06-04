"""
HTTP Connection Pool Management
HTTP连接池管理 - 优化项 #6
"""

import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import aiohttp

from .logger import setup_logging
from .settings import settings

logger = setup_logging("http_pool")


class HTTPConnectionPool:
    """
    Managed HTTP connection pool for external API calls
    
    Features:
    - Connection reuse
    - Connection limits
    - Timeout management
    - Automatic cleanup
    """
    
    def __init__(
        self,
        max_connections: int = 100,
        max_connections_per_host: int = 20,
        timeout_total: int = 30,
        timeout_connect: int = 10
    ):
        self.max_connections = max_connections
        self.max_per_host = max_connections_per_host
        self.timeout = aiohttp.ClientTimeout(
            total=timeout_total,
            connect=timeout_connect
        )
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=self.max_connections,
                        limit_per_host=self.max_per_host,
                        ttl_dns_cache=300,
                        enable_cleanup_closed=True
                    )
                    
                    self._session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=self.timeout,
                        headers={
                            "User-Agent": f"PreciousMetalsAPI/{settings.app_version}"
                        }
                    )
                    
                    logger.info("HTTP connection pool initialized")
        
        return self._session
    
    async def close(self):
        """Close the connection pool"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("HTTP connection pool closed")
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """HTTP GET request"""
        session = await self.get_session()
        return await session.get(url, headers=headers, params=params, **kwargs)
    
    async def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """HTTP POST request"""
        session = await self.get_session()
        return await session.post(url, data=data, json=json, headers=headers, **kwargs)
    
    async def get_json(self, url: str, **kwargs) -> Dict:
        """GET request and return JSON"""
        async with await self.get(url, **kwargs) as response:
            response.raise_for_status()
            return await response.json()
    
    async def post_json(self, url: str, data: Dict, **kwargs) -> Dict:
        """POST request and return JSON"""
        async with await self.post(url, json=data, **kwargs) as response:
            response.raise_for_status()
            return await response.json()


# Global HTTP pool
http_pool = HTTPConnectionPool()


# ============================================================================
# Redis Connection Pool
# ============================================================================

class RedisConnectionPool:
    """
    Redis connection pool manager
    """
    
    _pool = None
    
    @classmethod
    async def get_pool(cls):
        """Get Redis connection pool"""
        if cls._pool is None:
            import redis.asyncio as aioredis
            
            cls._pool = aioredis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                decode_responses=False
            )
            logger.info("Redis connection pool initialized")
        
        return cls._pool
    
    @classmethod
    async def get_client(cls):
        """Get Redis client with connection pool"""
        import redis.asyncio as aioredis
        
        pool = await cls.get_pool()
        return aioredis.Redis(connection_pool=pool)
    
    @classmethod
    async def close(cls):
        """Close Redis pool"""
        if cls._pool:
            await cls._pool.disconnect()
            cls._pool = None
            logger.info("Redis connection pool closed")


# ============================================================================
# Lifecycle Management
# ============================================================================

async def startup_pools():
    """Initialize all connection pools on startup"""
    await http_pool.get_session()
    await RedisConnectionPool.get_pool()
    logger.info("All connection pools initialized")


async def shutdown_pools():
    """Close all connection pools on shutdown"""
    await http_pool.close()
    await RedisConnectionPool.close()
    logger.info("All connection pools closed")


@asynccontextmanager
async def lifespan_pools(app):
    """FastAPI lifespan context manager"""
    await startup_pools()
    yield
    await shutdown_pools()


if __name__ == "__main__":
    async def test():
        print("Testing HTTP Connection Pool...")
        
        # Test HTTP
        data = await http_pool.get_json(
            "https://query1.finance.yahoo.com/v8/finance/chart/GLD",
            params={"interval": "1d", "range": "5d"}
        )
        print(f"Got data: {list(data.keys())}")
        
        await http_pool.close()
        print("HTTP pool test complete!")
    
    asyncio.run(test())
