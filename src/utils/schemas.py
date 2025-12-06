"""
Data Schemas (Pydantic)
数据模式定义
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Asset Schemas
# ============================================================================
class AssetBase(BaseModel):
    symbol: str
    name: str
    asset_type: str
    exchange: Optional[str] = None
    currency: str = "USD"
    description: Optional[str] = None


class AssetCreate(AssetBase):
    pass


class AssetResponse(AssetBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Price Data Schemas
# ============================================================================
class PriceDataBase(BaseModel):
    symbol: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[float] = None
    adj_close: Optional[float] = None


class PriceDataCreate(PriceDataBase):
    time: datetime
    source: str = "yfinance"


class PriceDataResponse(PriceDataBase):
    time: datetime
    source: str
    
    class Config:
        from_attributes = True


class PriceDataBatch(BaseModel):
    """Batch price data response"""
    symbol: str
    data: List[PriceDataResponse]
    count: int


# ============================================================================
# News Schemas
# ============================================================================
class NewsArticleBase(BaseModel):
    title: str
    content: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    author: Optional[str] = None
    symbol: Optional[str] = None


class NewsArticleCreate(NewsArticleBase):
    time: datetime
    keywords: Optional[List[str]] = None


class SentimentResult(BaseModel):
    """Sentiment analysis result"""
    positive: float = Field(ge=0, le=1)
    negative: float = Field(ge=0, le=1)
    neutral: float = Field(ge=0, le=1)
    score: float = Field(ge=-1, le=1)  # Composite score
    label: str  # 'positive', 'negative', 'neutral'


class NewsArticleResponse(NewsArticleBase):
    id: int
    time: datetime
    sentiment_positive: Optional[float] = None
    sentiment_negative: Optional[float] = None
    sentiment_neutral: Optional[float] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    keywords: Optional[List[str]] = None
    processed: bool
    
    class Config:
        from_attributes = True


class NewsWithSentiment(NewsArticleResponse):
    """News article with full sentiment details"""
    sentiment: Optional[SentimentResult] = None


# ============================================================================
# ETF Flow Schemas
# ============================================================================
class ETFFlowBase(BaseModel):
    symbol: str
    net_flow: Optional[float] = None
    shares_outstanding: Optional[float] = None
    aum: Optional[float] = None


class ETFFlowCreate(ETFFlowBase):
    time: datetime
    source: Optional[str] = None


class ETFFlowResponse(ETFFlowBase):
    time: datetime
    flow_change_1d: Optional[float] = None
    flow_change_5d: Optional[float] = None
    flow_change_20d: Optional[float] = None
    source: Optional[str] = None
    
    class Config:
        from_attributes = True


class ETFFlowSummary(BaseModel):
    """ETF flow summary"""
    symbol: str
    latest_flow: Optional[float] = None
    total_flow_7d: Optional[float] = None
    total_flow_30d: Optional[float] = None
    aum: Optional[float] = None
    aum_change_pct: Optional[float] = None


# ============================================================================
# Sentiment Metrics Schemas
# ============================================================================
class SentimentMetricBase(BaseModel):
    symbol: str
    interval_type: str  # 'hourly', 'daily'
    sentiment_index: Optional[float] = None
    bullish_ratio: Optional[float] = None
    bearish_ratio: Optional[float] = None
    news_volume: Optional[int] = None
    avg_sentiment: Optional[float] = None


class SentimentMetricResponse(SentimentMetricBase):
    time: datetime
    sentiment_std: Optional[float] = None
    sentiment_change_1d: Optional[float] = None
    sentiment_change_5d: Optional[float] = None
    heat_index: Optional[float] = None
    
    class Config:
        from_attributes = True


class SentimentDashboard(BaseModel):
    """Sentiment dashboard data"""
    symbol: str
    current_sentiment: float
    sentiment_label: str
    trend: str  # 'improving', 'stable', 'declining'
    news_volume_24h: int
    bullish_ratio: float
    bearish_ratio: float
    heat_index: float


# ============================================================================
# Trading Signal Schemas
# ============================================================================
class TradingSignalBase(BaseModel):
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    signal_strength: Optional[str] = None
    confidence: Optional[float] = None
    predicted_price: Optional[float] = None
    predicted_return: Optional[float] = None
    prediction_horizon: Optional[int] = None


class TradingSignalCreate(TradingSignalBase):
    time: datetime
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    feature_importance: Optional[Dict[str, float]] = None


class TradingSignalResponse(TradingSignalBase):
    id: int
    time: datetime
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    feature_importance: Optional[Dict[str, float]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Prediction Schemas
# ============================================================================
class PricePrediction(BaseModel):
    """Price prediction result"""
    symbol: str
    current_price: float
    predictions: Dict[str, float]  # {'T+1': price, 'T+5': price, 'T+30': price}
    confidence: Dict[str, float]  # Confidence per horizon
    direction: str  # 'up', 'down', 'neutral'
    generated_at: datetime


class ModelPerformance(BaseModel):
    """Model performance metrics"""
    model_name: str
    accuracy: float
    mae: float
    rmse: float
    sharpe_ratio: Optional[float] = None
    last_updated: datetime


# ============================================================================
# API Response Schemas
# ============================================================================
class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool = True
    message: str = "Success"
    data: Optional[Any] = None


class PaginatedResponse(BaseModel):
    """Paginated response"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int
