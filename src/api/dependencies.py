"""
FastAPI Dependency Injection
API依赖注入模块
"""

import asyncio
from typing import AsyncGenerator, Optional
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils.db_pool import db_manager
from ..utils.cache import cache, RedisCache
from ..utils.config import get_settings
from ..utils.logger import setup_logging

logger = setup_logging("dependencies")
settings = get_settings()


# ============================================================================
# Database Dependencies
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for async database session
    
    Usage:
        @app.get("/api/v1/data")
        async def get_data(db: AsyncSession = Depends(get_db)):
            result = await db.execute(...)
    """
    async with db_manager.get_async_session() as session:
        yield session


def get_sync_db():
    """FastAPI dependency for sync database session"""
    with db_manager.get_session() as session:
        yield session


# ============================================================================
# Cache Dependencies
# ============================================================================

def get_cache() -> RedisCache:
    """Get Redis cache instance"""
    return cache


# ============================================================================
# Async Wrappers for Sync Fetchers
# ============================================================================

class AsyncExecutor:
    """Thread pool executor for running sync code"""
    
    _executor: Optional[ThreadPoolExecutor] = None
    
    @classmethod
    def get_executor(cls) -> ThreadPoolExecutor:
        if cls._executor is None:
            cls._executor = ThreadPoolExecutor(max_workers=8)
        return cls._executor
    
    @classmethod
    async def run_sync(cls, func, *args, **kwargs):
        """Run synchronous function in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            cls.get_executor(),
            lambda: func(*args, **kwargs)
        )


# ============================================================================
# Price Fetcher Dependency
# ============================================================================

class AsyncPriceFetcher:
    """Async wrapper for PriceFetcher"""
    
    def __init__(self):
        from ..data_collection.price_fetcher import PriceFetcher
        self._fetcher = PriceFetcher()
    
    async def fetch_price_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ):
        """Async fetch price data"""
        return await AsyncExecutor.run_sync(
            self._fetcher.fetch_price_data,
            symbol, start_date, end_date, interval
        )
    
    async def fetch_latest_prices(self, symbols: list):
        """Async fetch latest prices"""
        return await AsyncExecutor.run_sync(
            self._fetcher.fetch_latest_prices,
            symbols
        )


@lru_cache()
def get_price_fetcher() -> AsyncPriceFetcher:
    """Get cached async price fetcher instance"""
    return AsyncPriceFetcher()


def price_fetcher_dependency() -> AsyncPriceFetcher:
    """FastAPI dependency for price fetcher"""
    return get_price_fetcher()


# ============================================================================
# News Fetcher Dependency
# ============================================================================

class AsyncNewsFetcher:
    """Async wrapper for NewsFetcher"""
    
    def __init__(self):
        from ..data_collection.news_fetcher import NewsFetcher
        self._fetcher = NewsFetcher()
    
    async def fetch_gold_news(self, limit: int = 50):
        return await AsyncExecutor.run_sync(
            self._fetcher.fetch_gold_news, limit
        )
    
    async def fetch_silver_news(self, limit: int = 50):
        return await AsyncExecutor.run_sync(
            self._fetcher.fetch_silver_news, limit
        )
    
    async def fetch_precious_metals_news(self, limit: int = 50):
        return await AsyncExecutor.run_sync(
            self._fetcher.fetch_precious_metals_news, limit
        )


@lru_cache()
def get_news_fetcher() -> AsyncNewsFetcher:
    """Get cached async news fetcher"""
    return AsyncNewsFetcher()


def news_fetcher_dependency() -> AsyncNewsFetcher:
    """FastAPI dependency for news fetcher"""
    return get_news_fetcher()


# ============================================================================
# ETF Flow Fetcher Dependency
# ============================================================================

class AsyncETFFlowFetcher:
    """Async wrapper for ETFFlowFetcher"""
    
    def __init__(self):
        from ..data_collection.etf_flow_fetcher import ETFFlowFetcher
        self._fetcher = ETFFlowFetcher()
    
    async def estimate_fund_flows(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        return await AsyncExecutor.run_sync(
            self._fetcher.estimate_fund_flows,
            symbol, start_date, end_date
        )
    
    async def get_flow_summary(self):
        return await AsyncExecutor.run_sync(
            self._fetcher.get_flow_summary
        )


@lru_cache()
def get_etf_flow_fetcher() -> AsyncETFFlowFetcher:
    """Get cached async ETF flow fetcher"""
    return AsyncETFFlowFetcher()


def etf_flow_fetcher_dependency() -> AsyncETFFlowFetcher:
    """FastAPI dependency for ETF flow fetcher"""
    return get_etf_flow_fetcher()


# ============================================================================
# Sentiment Analyzer Dependency
# ============================================================================

class AsyncSentimentAnalyzer:
    """Async wrapper for sentiment analyzer"""
    
    def __init__(self):
        self._analyzer = None
    
    def _get_analyzer(self):
        if self._analyzer is None:
            try:
                from ..nlp.finbert_analyzer import FinBERTAnalyzer
                self._analyzer = FinBERTAnalyzer()
            except Exception as e:
                logger.warning(f"FinBERT not available: {e}")
                self._analyzer = None
        return self._analyzer
    
    async def analyze(self, text: str):
        analyzer = self._get_analyzer()
        if analyzer is None:
            return {"score": 0, "label": "neutral", "error": "analyzer not available"}
        
        return await AsyncExecutor.run_sync(
            analyzer.analyze, text
        )
    
    async def analyze_batch(self, texts: list):
        analyzer = self._get_analyzer()
        if analyzer is None:
            return [{"score": 0, "label": "neutral"} for _ in texts]
        
        return await AsyncExecutor.run_sync(
            analyzer.analyze_batch, texts
        )


@lru_cache()
def get_sentiment_analyzer() -> AsyncSentimentAnalyzer:
    """Get cached async sentiment analyzer"""
    return AsyncSentimentAnalyzer()


def sentiment_analyzer_dependency() -> AsyncSentimentAnalyzer:
    """FastAPI dependency for sentiment analyzer"""
    return get_sentiment_analyzer()


# ============================================================================
# Request Context Dependencies
# ============================================================================

async def get_request_id(request: Request) -> str:
    """Get or generate request ID"""
    return request.headers.get("X-Request-ID", str(id(request)))


async def get_current_user_optional(request: Request):
    """Get current user if authenticated (optional)"""
    from .auth import auth_service
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    return auth_service.verify_token(token)


# ============================================================================
# Composite Dependencies
# ============================================================================

class ServiceContainer:
    """Container for all services"""
    
    def __init__(
        self,
        db: AsyncSession,
        cache: RedisCache,
        price_fetcher: AsyncPriceFetcher,
        news_fetcher: AsyncNewsFetcher,
        etf_fetcher: AsyncETFFlowFetcher,
        sentiment: AsyncSentimentAnalyzer
    ):
        self.db = db
        self.cache = cache
        self.price_fetcher = price_fetcher
        self.news_fetcher = news_fetcher
        self.etf_fetcher = etf_fetcher
        self.sentiment = sentiment


async def get_services(
    db: AsyncSession = Depends(get_db),
    redis: RedisCache = Depends(get_cache),
    prices: AsyncPriceFetcher = Depends(price_fetcher_dependency),
    news: AsyncNewsFetcher = Depends(news_fetcher_dependency),
    etf: AsyncETFFlowFetcher = Depends(etf_flow_fetcher_dependency),
    sentiment: AsyncSentimentAnalyzer = Depends(sentiment_analyzer_dependency)
) -> ServiceContainer:
    """Get all services in one dependency"""
    return ServiceContainer(
        db=db,
        cache=redis,
        price_fetcher=prices,
        news_fetcher=news,
        etf_fetcher=etf,
        sentiment=sentiment
    )


if __name__ == "__main__":
    print("Testing Dependencies...")
    
    # Test async executor
    async def test():
        fetcher = get_price_fetcher()
        data = await fetcher.fetch_latest_prices(["GLD"])
        print(f"Latest prices: {data}")
    
    asyncio.run(test())
    print("Dependencies test complete!")
