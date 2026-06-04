"""
SQLAlchemy ORM Models
数据库ORM模型定义
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, ForeignKey, Index, JSON, Numeric, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


# ============================================================================
# Price Data Models
# ============================================================================

class PriceData(Base):
    """Historical price data for ETFs"""
    __tablename__ = 'price_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    open = Column(Numeric(12, 4))
    high = Column(Numeric(12, 4))
    low = Column(Numeric(12, 4))
    close = Column(Numeric(12, 4), nullable=False)
    volume = Column(Integer)
    adj_close = Column(Numeric(12, 4))
    
    # Technical indicators (pre-computed)
    returns_1d = Column(Float)
    ma_5 = Column(Float)
    ma_20 = Column(Float)
    rsi_14 = Column(Float)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('symbol', 'timestamp', name='uix_price_symbol_time'),
        Index('idx_price_symbol_time_desc', symbol, timestamp.desc()),
        # For TimescaleDB: uncomment below
        # {'timescaledb_hypertable': {'time_column_name': 'timestamp'}}
    )
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'open': float(self.open) if self.open else None,
            'high': float(self.high) if self.high else None,
            'low': float(self.low) if self.low else None,
            'close': float(self.close),
            'volume': self.volume,
        }


# ============================================================================
# ETF Flow Models
# ============================================================================

class ETFFlow(Base):
    """ETF fund flow data"""
    __tablename__ = 'etf_flows'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    flow_date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    net_flow = Column(Numeric(18, 2))  # In USD
    shares_outstanding = Column(Integer)
    nav = Column(Numeric(12, 4))
    premium_discount = Column(Float)
    
    # Calculated metrics
    flow_7d_sum = Column(Numeric(18, 2))
    flow_30d_sum = Column(Numeric(18, 2))
    flow_zscore = Column(Float)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('symbol', 'flow_date', name='uix_etf_symbol_date'),
        Index('idx_etf_flow_date_desc', symbol, flow_date.desc()),
    )


class ETFHolder(Base):
    """ETF institutional holder data from 13F filings"""
    __tablename__ = 'etf_holders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    holder_name = Column(String(255), nullable=False)
    holder_cik = Column(String(20))
    
    filing_date = Column(DateTime(timezone=True), nullable=False)
    report_date = Column(DateTime(timezone=True))
    
    shares_held = Column(Integer)
    market_value = Column(Numeric(18, 2))
    pct_of_portfolio = Column(Float)
    shares_change = Column(Integer)
    shares_change_pct = Column(Float)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_holder_symbol_date', symbol, filing_date.desc()),
    )


# ============================================================================
# News & Sentiment Models
# ============================================================================

class NewsArticle(Base):
    """News articles storage"""
    __tablename__ = 'news_articles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    title = Column(String(500), nullable=False)
    content = Column(Text)
    summary = Column(Text)
    url = Column(String(1000))
    source = Column(String(100))
    author = Column(String(200))
    
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    fetched_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Symbols mentioned
    symbols = Column(JSONB, default=list)  # ['GLD', 'SLV']
    
    # Sentiment analysis results
    sentiment_score = Column(Float)  # -1 to 1
    sentiment_label = Column(String(20))  # positive, negative, neutral
    sentiment_confidence = Column(Float)
    sentiment_model = Column(String(50))  # finbert, deepseek, hybrid
    
    # Metadata
    language = Column(String(10), default='en')
    is_processed = Column(Boolean, default=False)
    
    __table_args__ = (
        Index('idx_news_published', published_at.desc()),
        Index('idx_news_sentiment', sentiment_score),
    )


class SentimentScore(Base):
    """Aggregated sentiment scores by symbol and time"""
    __tablename__ = 'sentiment_scores'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Aggregated scores
    avg_sentiment = Column(Float)
    weighted_sentiment = Column(Float)
    news_count = Column(Integer)
    
    # Distribution
    positive_ratio = Column(Float)
    negative_ratio = Column(Float)
    neutral_ratio = Column(Float)
    
    # Trends
    sentiment_ma_7d = Column(Float)
    sentiment_change_1d = Column(Float)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('symbol', 'timestamp', name='uix_sentiment_symbol_time'),
        Index('idx_sentiment_symbol_time', symbol, timestamp.desc()),
    )


# ============================================================================
# Prediction Models
# ============================================================================

class Prediction(Base):
    """Model predictions storage"""
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    
    prediction_date = Column(DateTime(timezone=True), nullable=False)
    target_date = Column(DateTime(timezone=True), nullable=False)
    horizon_days = Column(Integer, nullable=False)
    
    # Prediction values
    predicted_price = Column(Numeric(12, 4))
    predicted_return = Column(Float)
    predicted_direction = Column(String(10))  # up, down, neutral
    confidence = Column(Float)
    
    # Model info
    model_name = Column(String(100))
    model_version = Column(String(50))
    
    # Actual values (filled later for backtesting)
    actual_price = Column(Numeric(12, 4))
    actual_return = Column(Float)
    prediction_error = Column(Float)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_prediction_symbol_date', symbol, prediction_date.desc()),
    )


# ============================================================================
# Alert Models
# ============================================================================

class Alert(Base):
    """System alerts and notifications"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    alert_type = Column(String(50), nullable=False)  # etf_flow, sentiment, price, model
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    symbol = Column(String(10), index=True)
    
    title = Column(String(200), nullable=False)
    message = Column(Text)
    details = Column(JSONB)
    
    triggered_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        Index('idx_alert_active', is_active, triggered_at.desc()),
    )


# ============================================================================
# User Models
# ============================================================================

class User(Base):
    """User accounts"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    role = Column(String(20), default='user')  # user, admin, analyst
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_login = Column(DateTime(timezone=True))
    
    # Profile
    name = Column(String(100))
    preferences = Column(JSONB, default=dict)


class APIKey(Base):
    """API keys for users"""
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(100))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    
    # Rate limiting
    rate_limit = Column(Integer, default=1000)  # requests per hour
    
    user = relationship('User', backref='api_keys')


# ============================================================================
# Model Registry
# ============================================================================

class ModelRegistry(Base):
    """ML model version registry"""
    __tablename__ = 'model_registry'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    model_type = Column(String(50))  # lstm, xgboost, ensemble
    
    # Model artifacts
    artifact_path = Column(String(500))
    artifact_size = Column(Integer)
    
    # Metrics
    metrics = Column(JSONB)  # {'mae': 0.02, 'rmse': 0.03, 'sharpe': 1.5}
    
    # Status
    stage = Column(String(20), default='development')  # development, staging, production
    is_active = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    deployed_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        UniqueConstraint('name', 'version', name='uix_model_name_version'),
    )


# ============================================================================
# Database Initialization
# ============================================================================

def create_tables(engine):
    """Create all tables"""
    Base.metadata.create_all(engine)


def drop_tables(engine):
    """Drop all tables"""
    Base.metadata.drop_all(engine)


# For Alembic migrations
target_metadata = Base.metadata
