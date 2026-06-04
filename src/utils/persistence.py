"""
Data Persistence Layer
数据持久化层 - 解决问题3
实现: 定时任务抓取 → 存入PostgreSQL → Redis缓存 → API查询
"""

import asyncio
from typing import Optional, List, Dict, Any, TypeVar, Generic
from datetime import datetime, timedelta
from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from ..models.base import PriceData, ETFFlow, NewsArticle, SentimentScore, Prediction
from ..utils.cache import cache, cached, CacheConfig
from ..utils.db_pool import db_manager
from ..utils.logger import setup_logging

logger = setup_logging("persistence")

T = TypeVar('T')


# ============================================================================
# Base Repository
# ============================================================================

class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model: T):
        self.model = model
    
    async def get_by_id(self, session: AsyncSession, id: int) -> Optional[T]:
        result = await session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[T]:
        result = await session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
    
    async def create(self, session: AsyncSession, **data) -> T:
        instance = self.model(**data)
        session.add(instance)
        await session.flush()
        return instance
    
    async def bulk_create(self, session: AsyncSession, items: List[Dict]) -> int:
        """Bulk insert items"""
        if not items:
            return 0
        
        stmt = insert(self.model).values(items)
        stmt = stmt.on_conflict_do_nothing()  # Skip duplicates
        result = await session.execute(stmt)
        return result.rowcount


# ============================================================================
# Price Data Repository
# ============================================================================

class PriceRepository(BaseRepository[PriceData]):
    """Repository for price data with caching"""
    
    def __init__(self):
        super().__init__(PriceData)
    
    async def get_by_symbol(
        self,
        session: AsyncSession,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[PriceData]:
        """Get price data for symbol with optional date range"""
        
        # Try cache first
        cache_key = f"prices:{symbol}:{start_date}:{end_date}:{limit}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit: {cache_key}")
            return cached_data
        
        # Build query
        query = select(self.model).where(self.model.symbol == symbol)
        
        if start_date:
            query = query.where(self.model.timestamp >= start_date)
        if end_date:
            query = query.where(self.model.timestamp <= end_date)
        
        query = query.order_by(desc(self.model.timestamp)).limit(limit)
        
        result = await session.execute(query)
        data = list(result.scalars().all())
        
        # Cache result
        cache.set(cache_key, data, ttl=CacheConfig.PRICE_TTL)
        
        return data
    
    async def get_latest(
        self,
        session: AsyncSession,
        symbol: str
    ) -> Optional[PriceData]:
        """Get latest price for symbol"""
        
        cache_key = f"latest_price:{symbol}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        result = await session.execute(
            select(self.model)
            .where(self.model.symbol == symbol)
            .order_by(desc(self.model.timestamp))
            .limit(1)
        )
        price = result.scalar_one_or_none()
        
        if price:
            cache.set(cache_key, price, ttl=60)  # 1 minute cache
        
        return price
    
    async def get_latest_all(
        self,
        session: AsyncSession,
        symbols: List[str]
    ) -> Dict[str, PriceData]:
        """Get latest prices for multiple symbols"""
        
        # Check cache
        results = {}
        missing = []
        
        for symbol in symbols:
            cached = cache.get(f"latest_price:{symbol}")
            if cached:
                results[symbol] = cached
            else:
                missing.append(symbol)
        
        if missing:
            # Query missing symbols
            for symbol in missing:
                price = await self.get_latest(session, symbol)
                if price:
                    results[symbol] = price
        
        return results
    
    async def upsert_prices(
        self,
        session: AsyncSession,
        prices: List[Dict]
    ) -> int:
        """Upsert price data (insert or update on conflict)"""
        
        if not prices:
            return 0
        
        stmt = insert(self.model).values(prices)
        stmt = stmt.on_conflict_do_update(
            index_elements=['symbol', 'timestamp'],
            set_={
                'close': stmt.excluded.close,
                'open': stmt.excluded.open,
                'high': stmt.excluded.high,
                'low': stmt.excluded.low,
                'volume': stmt.excluded.volume,
            }
        )
        result = await session.execute(stmt)
        
        # Invalidate cache for affected symbols
        symbols = set(p['symbol'] for p in prices)
        for symbol in symbols:
            cache.delete_pattern(f"*:{symbol}*")
        
        return result.rowcount


# ============================================================================
# ETF Flow Repository
# ============================================================================

class ETFFlowRepository(BaseRepository[ETFFlow]):
    """Repository for ETF flow data"""
    
    def __init__(self):
        super().__init__(ETFFlow)
    
    async def get_by_symbol(
        self,
        session: AsyncSession,
        symbol: str,
        days: int = 30
    ) -> List[ETFFlow]:
        """Get ETF flows for symbol"""
        
        cache_key = f"etf_flows:{symbol}:{days}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        result = await session.execute(
            select(self.model)
            .where(and_(
                self.model.symbol == symbol,
                self.model.flow_date >= start_date
            ))
            .order_by(desc(self.model.flow_date))
        )
        data = list(result.scalars().all())
        
        cache.set(cache_key, data, ttl=CacheConfig.ETF_FLOW_TTL)
        
        return data
    
    async def get_flow_summary(
        self,
        session: AsyncSession,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, Dict]:
        """Get flow summary for symbols"""
        
        default_symbols = ['GLD', 'IAU', 'SLV', 'SIVR']
        symbols = symbols or default_symbols
        
        summary = {}
        for symbol in symbols:
            flows = await self.get_by_symbol(session, symbol, days=30)
            
            if flows:
                total_flow = sum(float(f.net_flow or 0) for f in flows)
                avg_flow = total_flow / len(flows) if flows else 0
                
                summary[symbol] = {
                    'total_flow_30d': total_flow,
                    'avg_daily_flow': avg_flow,
                    'flow_count': len(flows),
                    'last_flow': flows[0].net_flow if flows else None
                }
        
        return summary


# ============================================================================
# News Repository
# ============================================================================

class NewsRepository(BaseRepository[NewsArticle]):
    """Repository for news articles"""
    
    def __init__(self):
        super().__init__(NewsArticle)
    
    async def get_recent(
        self,
        session: AsyncSession,
        limit: int = 50,
        symbol: Optional[str] = None,
        include_sentiment: bool = True
    ) -> List[NewsArticle]:
        """Get recent news articles"""
        
        cache_key = f"news:recent:{symbol}:{limit}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        query = select(self.model).order_by(desc(self.model.published_at))
        
        if symbol:
            query = query.where(self.model.symbols.contains([symbol]))
        
        if include_sentiment:
            query = query.where(self.model.is_processed == True)
        
        query = query.limit(limit)
        
        result = await session.execute(query)
        data = list(result.scalars().all())
        
        cache.set(cache_key, data, ttl=CacheConfig.NEWS_TTL)
        
        return data
    
    async def save_articles(
        self,
        session: AsyncSession,
        articles: List[Dict]
    ) -> int:
        """Save news articles (skip duplicates by URL)"""
        
        if not articles:
            return 0
        
        # Check existing URLs
        urls = [a.get('url') for a in articles if a.get('url')]
        
        existing = await session.execute(
            select(self.model.url).where(self.model.url.in_(urls))
        )
        existing_urls = set(row[0] for row in existing.fetchall())
        
        # Filter new articles
        new_articles = [a for a in articles if a.get('url') not in existing_urls]
        
        if new_articles:
            return await self.bulk_create(session, new_articles)
        
        return 0


# ============================================================================
# Sentiment Repository
# ============================================================================

class SentimentRepository(BaseRepository[SentimentScore]):
    """Repository for sentiment scores"""
    
    def __init__(self):
        super().__init__(SentimentScore)
    
    async def get_by_symbol(
        self,
        session: AsyncSession,
        symbol: str,
        days: int = 7
    ) -> List[SentimentScore]:
        """Get sentiment scores for symbol"""
        
        cache_key = f"sentiment:{symbol}:{days}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        result = await session.execute(
            select(self.model)
            .where(and_(
                self.model.symbol == symbol,
                self.model.timestamp >= start_date
            ))
            .order_by(desc(self.model.timestamp))
        )
        data = list(result.scalars().all())
        
        cache.set(cache_key, data, ttl=CacheConfig.SENTIMENT_TTL)
        
        return data
    
    async def get_dashboard(
        self,
        session: AsyncSession,
        symbol: str
    ) -> Dict:
        """Get sentiment dashboard data for symbol"""
        
        cache_key = f"sentiment_dashboard:{symbol}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Get recent scores
        scores = await self.get_by_symbol(session, symbol, days=30)
        
        if not scores:
            return {
                'symbol': symbol,
                'current_sentiment': 0,
                'avg_7d': 0,
                'trend': 'neutral',
                'news_count': 0
            }
        
        current = scores[0].avg_sentiment if scores else 0
        recent_7d = scores[:7]
        avg_7d = sum(s.avg_sentiment for s in recent_7d) / len(recent_7d) if recent_7d else 0
        
        # Determine trend
        if current > avg_7d + 0.1:
            trend = 'improving'
        elif current < avg_7d - 0.1:
            trend = 'declining'
        else:
            trend = 'stable'
        
        dashboard = {
            'symbol': symbol,
            'current_sentiment': current,
            'avg_7d': avg_7d,
            'trend': trend,
            'news_count': sum(s.news_count or 0 for s in recent_7d),
            'positive_ratio': scores[0].positive_ratio if scores else 0,
            'negative_ratio': scores[0].negative_ratio if scores else 0
        }
        
        cache.set(cache_key, dashboard, ttl=CacheConfig.SENTIMENT_TTL)
        
        return dashboard


# ============================================================================
# Data Sync Service
# ============================================================================

class DataSyncService:
    """
    Service to sync data from external sources to database
    
    Usage:
        sync = DataSyncService()
        await sync.sync_prices(['GLD', 'SLV'])
        await sync.sync_etf_flows(['GLD'])
    """
    
    def __init__(self):
        self.price_repo = PriceRepository()
        self.etf_repo = ETFFlowRepository()
        self.news_repo = NewsRepository()
    
    async def sync_prices(
        self,
        symbols: List[str],
        days: int = 30
    ) -> Dict[str, int]:
        """Sync price data from yfinance to database"""
        
        from ..data_collection.price_fetcher import PriceFetcher
        
        fetcher = PriceFetcher()
        results = {}
        
        async with db_manager.get_async_session() as session:
            for symbol in symbols:
                try:
                    # Fetch from yfinance
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                    
                    df = fetcher.fetch_price_data(symbol, start_date, end_date)
                    
                    if df is not None and not df.empty:
                        # Convert to records
                        prices = []
                        for idx, row in df.iterrows():
                            prices.append({
                                'symbol': symbol,
                                'timestamp': idx.to_pydatetime(),
                                'open': row['Open'],
                                'high': row['High'],
                                'low': row['Low'],
                                'close': row['Close'],
                                'volume': int(row['Volume']),
                            })
                        
                        count = await self.price_repo.upsert_prices(session, prices)
                        results[symbol] = count
                        logger.info(f"Synced {count} prices for {symbol}")
                    else:
                        results[symbol] = 0
                        
                except Exception as e:
                    logger.error(f"Failed to sync prices for {symbol}: {e}")
                    results[symbol] = -1
            
            await session.commit()
        
        return results
    
    async def sync_news(self, limit: int = 50) -> int:
        """Sync news from external sources to database"""
        
        from ..data_collection.news_fetcher import NewsFetcher
        
        fetcher = NewsFetcher()
        
        try:
            articles = fetcher.fetch_precious_metals_news(limit=limit)
            
            async with db_manager.get_async_session() as session:
                count = await self.news_repo.save_articles(session, articles)
                await session.commit()
                
            logger.info(f"Synced {count} news articles")
            return count
            
        except Exception as e:
            logger.error(f"Failed to sync news: {e}")
            return 0


# ============================================================================
# Cache Warming
# ============================================================================

class CacheWarmer:
    """
    Pre-warm cache with frequently accessed data
    
    Run on application startup or via scheduled task
    """
    
    def __init__(self):
        self.price_repo = PriceRepository()
        self.etf_repo = ETFFlowRepository()
        self.sentiment_repo = SentimentRepository()
    
    async def warm_all(self, symbols: List[str] = None):
        """Warm all caches"""
        symbols = symbols or ['GLD', 'IAU', 'SLV', 'SIVR', 'PSLV']
        
        logger.info("Starting cache warming...")
        
        async with db_manager.get_async_session() as session:
            # Warm price cache
            for symbol in symbols:
                await self.price_repo.get_latest(session, symbol)
                await self.price_repo.get_by_symbol(session, symbol, limit=100)
            
            # Warm ETF flow cache
            await self.etf_repo.get_flow_summary(session, symbols)
            
            # Warm sentiment cache
            for symbol in symbols:
                await self.sentiment_repo.get_dashboard(session, symbol)
        
        logger.info("Cache warming complete")


# Global instances
price_repository = PriceRepository()
etf_flow_repository = ETFFlowRepository()
news_repository = NewsRepository()
sentiment_repository = SentimentRepository()
data_sync_service = DataSyncService()
cache_warmer = CacheWarmer()


if __name__ == "__main__":
    print("Testing Data Persistence Layer...")
    
    async def test():
        # Test sync service
        sync = DataSyncService()
        results = await sync.sync_prices(['GLD'], days=7)
        print(f"Sync results: {results}")
        
        # Test cache warmer
        warmer = CacheWarmer()
        await warmer.warm_all(['GLD'])
        
        print("Data persistence test complete!")
    
    asyncio.run(test())
