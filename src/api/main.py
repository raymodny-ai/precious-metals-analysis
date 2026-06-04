"""
FastAPI Main Application
FastAPI主应用
"""

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime, timedelta
import asyncio

from ..utils.config import get_settings
from ..utils.logger import setup_logging
from ..utils.schemas import (
    APIResponse, PriceDataResponse, PriceDataBatch,
    NewsArticleResponse, NewsWithSentiment,
    ETFFlowResponse, ETFFlowSummary,
    SentimentDashboard, TradingSignalResponse,
    PricePrediction
)

logger = setup_logging("api")
settings = get_settings()


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    logger.info("Starting Precious Metals Analysis API...")
    # Startup tasks
    yield
    # Shutdown tasks
    logger.info("Shutting down API...")


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Precious Metals Analysis API",
        version="2.0.0",
        description="""
# 贵金属市场情绪分析与预测系统 API

## 功能模块

### 📈 Price Data
- 历史价格数据
- 实时价格查询
- 技术指标计算

### 💰 ETF Flows
- 资金流向监控
- 异常检测告警
- 持仓人追踪

### 📰 News & Sentiment
- 新闻抓取与分析
- FinBERT/DeepSeek 情绪分析
- 情绪仪表盘

### 🤖 Predictions
- LSTM + Attention 预测
- 集成模型预测
- 置信度估计

### 🔐 Authentication
- JWT Token认证
- 角色权限控制
- 用户管理

## 认证方式
使用 Bearer Token 认证:
```
Authorization: Bearer <your_jwt_token>
```
        """,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Create FastAPI app
app = FastAPI(
    title="Precious Metals Analysis API",
    description="贵金属市场情绪分析与预测系统 API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.openapi = custom_openapi

# Include auth router
from .auth_router import router as auth_router
app.include_router(auth_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """API root endpoint"""
    return {
        "name": "Precious Metals Analysis API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "api": "ok",
            "database": "ok",  # TODO: actual check
            "models": "ok"    # TODO: actual check
        }
    }


# ============================================================================
# Price Data Endpoints
# ============================================================================

@app.get("/api/v1/prices/{symbol}", response_model=PriceDataBatch, tags=["Prices"])
async def get_price_data(
    symbol: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    interval: str = Query("1d", description="Data interval (1d, 1h, 1w)")
):
    """
    Get historical price data for a symbol
    
    Supported symbols: GLD, IAU, GLDM, SGOL, SLV, SIVR, AGQ
    """
    try:
        from ..data_collection.price_fetcher import PriceFetcher
        
        fetcher = PriceFetcher()
        df = fetcher.fetch_price_data(symbol, start_date, end_date, interval)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        data = df.to_dict(orient="records")
        
        return PriceDataBatch(
            symbol=symbol,
            data=[PriceDataResponse(**row) for row in data],
            count=len(data)
        )
    
    except Exception as e:
        logger.error(f"Error fetching price data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/prices/latest", tags=["Prices"])
async def get_latest_prices(
    symbols: Optional[str] = Query(None, description="Comma-separated symbols")
):
    """Get latest prices for symbols"""
    try:
        from ..data_collection.price_fetcher import PriceFetcher
        
        fetcher = PriceFetcher()
        
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(",")]
        else:
            symbol_list = fetcher.GOLD_ETFS + fetcher.SILVER_ETFS
        
        latest = fetcher.fetch_latest_prices(symbol_list)
        
        return APIResponse(
            success=True,
            message="Latest prices retrieved",
            data=latest
        )
    
    except Exception as e:
        logger.error(f"Error fetching latest prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ETF Flow Endpoints
# ============================================================================

@app.get("/api/v1/etf/flows/{symbol}", tags=["ETF Flows"])
async def get_etf_flows(
    symbol: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Get ETF fund flow data"""
    try:
        from ..data_collection.etf_flow_fetcher import ETFFlowFetcher
        
        fetcher = ETFFlowFetcher()
        df = fetcher.estimate_fund_flows(symbol, start_date, end_date)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No flow data for {symbol}")
        
        data = df.to_dict(orient="records")
        
        return APIResponse(
            success=True,
            message=f"ETF flows for {symbol}",
            data=data
        )
    
    except Exception as e:
        logger.error(f"Error fetching ETF flows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/etf/summary", tags=["ETF Flows"])
async def get_etf_summary():
    """Get summary of all ETF flows"""
    try:
        from ..data_collection.etf_flow_fetcher import ETFFlowFetcher
        
        fetcher = ETFFlowFetcher()
        summary = fetcher.get_flow_summary()
        
        return APIResponse(
            success=True,
            message="ETF flow summary",
            data=summary
        )
    
    except Exception as e:
        logger.error(f"Error fetching ETF summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# News & Sentiment Endpoints
# ============================================================================

@app.get("/api/v1/news", tags=["News"])
async def get_news(
    symbol: Optional[str] = Query(None, description="Filter by symbol (GLD, SLV)"),
    limit: int = Query(50, ge=1, le=200),
    include_sentiment: bool = Query(True)
):
    """Get latest news articles with sentiment"""
    try:
        from ..data_collection.news_fetcher import NewsFetcher
        
        fetcher = NewsFetcher()
        
        if symbol:
            if symbol.upper() in ["GLD", "IAU", "GLDM", "SGOL"]:
                df = fetcher.fetch_gold_news(limit=limit)
            else:
                df = fetcher.fetch_silver_news(limit=limit)
        else:
            df = fetcher.fetch_precious_metals_news(limit=limit)
        
        if include_sentiment and not df.empty:
            try:
                from ..nlp.finbert_analyzer import FinBERTAnalyzer
                analyzer = FinBERTAnalyzer()
                df = analyzer.analyze_dataframe(df)
            except Exception as e:
                logger.warning(f"Sentiment analysis failed: {e}")
        
        data = df.to_dict(orient="records")
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(data)} news articles",
            data=data
        )
    
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentiment/dashboard/{symbol}", tags=["Sentiment"])
async def get_sentiment_dashboard(symbol: str):
    """Get sentiment dashboard for a symbol"""
    try:
        from ..data_collection.news_fetcher import NewsFetcher
        from ..nlp.finbert_analyzer import FinBERTAnalyzer
        from ..nlp.sentiment_metrics import SentimentMetricsEngine
        
        # Fetch recent news
        fetcher = NewsFetcher()
        df = fetcher.fetch_precious_metals_news(limit=50)
        
        if df.empty:
            return APIResponse(
                success=True,
                message="No recent news available",
                data={
                    "symbol": symbol,
                    "current_sentiment": 0,
                    "sentiment_label": "neutral",
                    "trend": "stable",
                    "news_volume_24h": 0,
                    "bullish_ratio": 0.5,
                    "bearish_ratio": 0.5,
                    "heat_index": 0
                }
            )
        
        # Analyze sentiment
        try:
            analyzer = FinBERTAnalyzer()
            df = analyzer.analyze_dataframe(df)
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
        
        # Calculate dashboard metrics
        engine = SentimentMetricsEngine()
        dashboard = engine.get_realtime_dashboard(df, symbol)
        
        return APIResponse(
            success=True,
            message=f"Sentiment dashboard for {symbol}",
            data={
                "symbol": dashboard.symbol,
                "current_sentiment": dashboard.current_sentiment,
                "sentiment_label": dashboard.sentiment_label,
                "trend": dashboard.trend,
                "news_volume_24h": dashboard.news_volume_24h,
                "bullish_ratio": dashboard.bullish_ratio,
                "bearish_ratio": dashboard.bearish_ratio,
                "heat_index": dashboard.heat_index,
                "last_updated": dashboard.last_updated.isoformat()
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting sentiment dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Prediction Endpoints
# ============================================================================

@app.get("/api/v1/predictions/{symbol}", tags=["Predictions"])
async def get_predictions(
    symbol: str,
    horizon: int = Query(1, ge=1, le=30, description="Prediction horizon in days")
):
    """Get price predictions for a symbol"""
    try:
        from ..data_collection.price_fetcher import PriceFetcher
        from ..ml.feature_engineering import FeatureEngineer
        from ..ml.lstm_predictor import LSTMPredictor
        
        # Fetch recent data
        fetcher = PriceFetcher()
        df = fetcher.fetch_price_data(symbol, interval="1d")
        
        if df.empty or len(df) < 50:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient data for {symbol}"
            )
        
        current_price = df["close"].iloc[-1]
        
        # Note: In production, you'd load a pre-trained model
        # This is a simplified example
        
        return APIResponse(
            success=True,
            message=f"Predictions for {symbol}",
            data={
                "symbol": symbol,
                "current_price": current_price,
                "predictions": {
                    f"T+{horizon}": current_price * 1.005,  # Placeholder
                },
                "confidence": 0.6,
                "direction": "up",
                "model": "lstm_v1",
                "generated_at": datetime.now().isoformat()
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Macro Data Endpoints
# ============================================================================

@app.get("/api/v1/macro/indicators", tags=["Macro"])
async def get_macro_indicators(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Get macroeconomic indicators"""
    try:
        from ..data_collection.macro_fetcher import MacroFetcher
        
        fetcher = MacroFetcher()
        
        if not fetcher.api_key:
            return APIResponse(
                success=False,
                message="FRED API key not configured",
                data=None
            )
        
        df = fetcher.fetch_key_indicators(start_date, end_date)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="No macro data available")
        
        data = df.to_dict(orient="records")
        
        return APIResponse(
            success=True,
            message="Macro indicators retrieved",
            data=data
        )
    
    except Exception as e:
        logger.error(f"Error fetching macro data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Run server
# ============================================================================

def run_server():
    """Run the API server"""
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )


if __name__ == "__main__":
    run_server()
