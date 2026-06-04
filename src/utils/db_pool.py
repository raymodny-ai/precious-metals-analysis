"""
Database Connection Pool and Optimization
数据库连接池和查询优化
"""

from typing import Optional, Dict, Any, AsyncGenerator
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass
import time

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool

from .logger import setup_logging
from .config import get_settings

logger = setup_logging("db_pool")
settings = get_settings()


@dataclass
class PoolConfig:
    """Connection pool configuration"""
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800  # 30 minutes
    pool_pre_ping: bool = True


class DatabaseManager:
    """
    Database connection manager with pooling
    
    Features:
    - Connection pooling
    - Query profiling
    - Auto-reconnection
    - Health checking
    """
    
    def __init__(
        self,
        database_url: Optional[str] = None,
        pool_config: Optional[PoolConfig] = None
    ):
        self.database_url = database_url or getattr(
            settings, 'database_url', 
            'postgresql://postgres:postgres@localhost:5432/precious_metals'
        )
        self.pool_config = pool_config or PoolConfig()
        
        self._sync_engine = None
        self._async_engine = None
        self._sync_session_factory = None
        self._async_session_factory = None
        
        self._query_count = 0
        self._slow_queries: list = []
    
    def _create_sync_engine(self):
        """Create synchronous engine with pooling"""
        if self._sync_engine is None:
            self._sync_engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=self.pool_config.pool_size,
                max_overflow=self.pool_config.max_overflow,
                pool_timeout=self.pool_config.pool_timeout,
                pool_recycle=self.pool_config.pool_recycle,
                pool_pre_ping=self.pool_config.pool_pre_ping,
                echo=False
            )
            
            # Add query profiling
            @event.listens_for(self._sync_engine, "before_cursor_execute")
            def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                conn.info.setdefault("query_start_time", []).append(time.time())
            
            @event.listens_for(self._sync_engine, "after_cursor_execute")
            def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                total = time.time() - conn.info["query_start_time"].pop()
                self._query_count += 1
                
                # Log slow queries
                if total > 1.0:  # More than 1 second
                    self._slow_queries.append({
                        "query": statement[:200],
                        "time": total,
                        "timestamp": time.time()
                    })
                    logger.warning(f"Slow query ({total:.2f}s): {statement[:100]}...")
            
            self._sync_session_factory = sessionmaker(
                bind=self._sync_engine,
                expire_on_commit=False
            )
            
            logger.info("Sync database engine created")
        
        return self._sync_engine
    
    def _create_async_engine(self):
        """Create async engine with pooling"""
        if self._async_engine is None:
            # Convert sync URL to async
            async_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            ).replace(
                "postgres://", "postgresql+asyncpg://"
            )
            
            self._async_engine = create_async_engine(
                async_url,
                pool_size=self.pool_config.pool_size,
                max_overflow=self.pool_config.max_overflow,
                pool_recycle=self.pool_config.pool_recycle,
                pool_pre_ping=self.pool_config.pool_pre_ping,
                echo=False
            )
            
            self._async_session_factory = async_sessionmaker(
                bind=self._async_engine,
                expire_on_commit=False,
                class_=AsyncSession
            )
            
            logger.info("Async database engine created")
        
        return self._async_engine
    
    @contextmanager
    def get_session(self) -> Session:
        """Get sync database session"""
        self._create_sync_engine()
        session = self._sync_session_factory()
        
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session"""
        self._create_async_engine()
        session = self._async_session_factory()
        
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database error: {e}")
            raise
        finally:
            await session.close()
    
    def health_check(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            self._create_sync_engine()
            
            with self._sync_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            pool = self._sync_engine.pool
            
            return {
                "status": "healthy",
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "query_count": self._query_count
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def get_slow_queries(self, n: int = 10) -> list:
        """Get recent slow queries"""
        return self._slow_queries[-n:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        health = self.health_check()
        
        return {
            **health,
            "slow_queries_count": len(self._slow_queries),
            "recent_slow_queries": self.get_slow_queries(5)
        }
    
    async def close(self):
        """Close all connections"""
        if self._sync_engine:
            self._sync_engine.dispose()
            logger.info("Sync engine disposed")
        
        if self._async_engine:
            await self._async_engine.dispose()
            logger.info("Async engine disposed")


# Global database manager
db_manager = DatabaseManager()


# FastAPI dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session"""
    async with db_manager.get_async_session() as session:
        yield session


def get_sync_db():
    """Dependency for sync database session"""
    with db_manager.get_session() as session:
        yield session


# ============================================================================
# Query Optimization Utilities
# ============================================================================

class QueryOptimizer:
    """Query optimization utilities"""
    
    @staticmethod
    def build_date_filter(column, start_date=None, end_date=None):
        """Build date range filter"""
        filters = []
        if start_date:
            filters.append(column >= start_date)
        if end_date:
            filters.append(column <= end_date)
        return filters
    
    @staticmethod
    def paginate(query, page: int = 1, per_page: int = 20):
        """Add pagination to query"""
        offset = (page - 1) * per_page
        return query.offset(offset).limit(per_page)
    
    @staticmethod
    def batch_insert(session: Session, model, data: list, batch_size: int = 1000):
        """Batch insert for large datasets"""
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            session.bulk_insert_mappings(model, batch)
            session.flush()


INDEX_RECOMMENDATIONS = """
CREATE INDEX IF NOT EXISTS idx_prices_symbol_time ON price_data(symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_time ON sentiment_scores(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_etf_symbol_date ON etf_flows(symbol, flow_date DESC);
"""
