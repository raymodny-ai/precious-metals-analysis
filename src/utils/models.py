"""
Database Models (SQLAlchemy ORM)
数据库模型
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, Text, DateTime, Date, ARRAY, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from .database import Base


class Asset(Base):
    """资产维度表"""
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    asset_type = Column(String(20), nullable=False)  # 'gold_etf', 'silver_etf', 'futures', 'index'
    exchange = Column(String(20))
    currency = Column(String(10), default="USD")
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PriceData(Base):
    """价格数据超表"""
    __tablename__ = "price_data"
    
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol = Column(String(20), primary_key=True, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float, nullable=False)
    volume = Column(Float)
    adj_close = Column(Float)
    source = Column(String(20), default="yfinance")


class NewsArticle(Base):
    """新闻文章超表"""
    __tablename__ = "news_articles"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False, index=True)
    symbol = Column(String(20), index=True)
    title = Column(Text, nullable=False)
    content = Column(Text)
    source = Column(String(100))
    url = Column(Text)
    author = Column(String(100))
    # 情绪分析结果
    sentiment_positive = Column(Float)
    sentiment_negative = Column(Float)
    sentiment_neutral = Column(Float)
    sentiment_score = Column(Float)  # -1 to +1
    sentiment_label = Column(String(20))  # 'positive', 'negative', 'neutral'
    # 元数据
    keywords = Column(ARRAY(Text))
    language = Column(String(10), default="en")
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ETFFlow(Base):
    """ETF资金流超表"""
    __tablename__ = "etf_flows"
    
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol = Column(String(20), primary_key=True, nullable=False, index=True)
    net_flow = Column(Float)  # 净流入(正)/流出(负)
    shares_outstanding = Column(Float)
    aum = Column(Float)
    flow_change_1d = Column(Float)
    flow_change_5d = Column(Float)
    flow_change_20d = Column(Float)
    source = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ETFHolder(Base):
    """ETF持有者表"""
    __tablename__ = "etf_holders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    holder_name = Column(String(200), nullable=False)
    shares = Column(Float)
    value_usd = Column(Float)
    percent_of_fund = Column(Float)
    report_date = Column(Date)
    holder_type = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SentimentMetric(Base):
    """情绪指标超表"""
    __tablename__ = "sentiment_metrics"
    
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol = Column(String(20), primary_key=True, nullable=False, index=True)
    interval_type = Column(String(10), primary_key=True, nullable=False)  # 'hourly', 'daily'
    sentiment_index = Column(Float)  # 0-100
    bullish_ratio = Column(Float)
    bearish_ratio = Column(Float)
    news_volume = Column(Integer)
    avg_sentiment = Column(Float)
    sentiment_std = Column(Float)
    sentiment_change_1d = Column(Float)
    sentiment_change_5d = Column(Float)
    heat_index = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CorrelationAnalysis(Base):
    """相关性分析表"""
    __tablename__ = "correlation_analysis"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_date = Column(Date, nullable=False, index=True)
    symbol1 = Column(String(20), nullable=False)
    symbol2 = Column(String(20), nullable=False)
    correlation_type = Column(String(50), nullable=False)
    lookback_days = Column(Integer, nullable=False)
    correlation_value = Column(Float, nullable=False)
    p_value = Column(Float)
    is_significant = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TradingSignal(Base):
    """交易信号表"""
    __tablename__ = "trading_signals"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)  # 'BUY', 'SELL', 'HOLD'
    signal_strength = Column(String(20))  # 'STRONG', 'MODERATE', 'WEAK'
    confidence = Column(Float)
    predicted_price = Column(Float)
    predicted_return = Column(Float)
    prediction_horizon = Column(Integer)
    model_name = Column(String(50))
    model_version = Column(String(20))
    feature_importance = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
