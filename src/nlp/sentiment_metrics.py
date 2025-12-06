"""
Sentiment Metrics Aggregation
情绪指标计算模块
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..utils.logger import setup_logging

logger = setup_logging("sentiment_metrics")


@dataclass
class SentimentDashboard:
    """Dashboard data for sentiment display"""
    symbol: str
    current_sentiment: float
    sentiment_label: str
    trend: str  # 'improving', 'stable', 'declining'
    news_volume_24h: int
    bullish_ratio: float
    bearish_ratio: float
    heat_index: float
    last_updated: datetime


class SentimentMetricsEngine:
    """
    Engine for calculating comprehensive sentiment metrics
    
    Features:
    - Real-time sentiment aggregation
    - Historical trend analysis
    - Sentiment momentum indicators
    - Anomaly detection
    """
    
    # Trend thresholds
    IMPROVING_THRESHOLD = 0.05
    DECLINING_THRESHOLD = -0.05
    
    def __init__(self):
        pass
    
    def calculate_composite_index(
        self,
        avg_sentiment: float,
        bullish_ratio: float,
        news_volume: int,
        reference_volume: int = 10
    ) -> float:
        """
        Calculate composite sentiment index (0-100)
        
        Formula:
        - Base: normalized average sentiment (0-100)
        - Weighted by bullish ratio
        - Adjusted by volume (higher volume = more confidence)
        """
        # Normalize sentiment from [-1, 1] to [0, 100]
        base_score = (avg_sentiment + 1) * 50
        
        # Bullish weight
        bullish_weight = bullish_ratio * 100
        
        # Volume confidence factor (0.5 to 1.5)
        volume_factor = min(1.5, max(0.5, news_volume / reference_volume))
        
        # Composite calculation
        composite = (base_score * 0.6 + bullish_weight * 0.4) * volume_factor
        
        # Clamp to 0-100
        return max(0, min(100, composite))
    
    def calculate_sentiment_momentum(
        self,
        sentiment_series: pd.Series,
        short_window: int = 5,
        long_window: int = 20
    ) -> pd.DataFrame:
        """
        Calculate sentiment momentum indicators
        
        Returns:
        - Short-term moving average
        - Long-term moving average
        - Momentum (short MA - long MA)
        - Rate of change
        """
        df = pd.DataFrame({"sentiment": sentiment_series})
        
        # Moving averages
        df["ma_short"] = df["sentiment"].rolling(short_window).mean()
        df["ma_long"] = df["sentiment"].rolling(long_window).mean()
        
        # Momentum
        df["momentum"] = df["ma_short"] - df["ma_long"]
        
        # Rate of change
        df["roc"] = df["sentiment"].pct_change(periods=short_window)
        
        # Acceleration (second derivative)
        df["acceleration"] = df["momentum"].diff()
        
        return df
    
    def detect_sentiment_anomalies(
        self,
        sentiment_series: pd.Series,
        volume_series: Optional[pd.Series] = None,
        z_threshold: float = 2.0
    ) -> pd.DataFrame:
        """
        Detect anomalous sentiment readings
        
        Anomalies:
        - Sentiment > 2 std from mean
        - Sudden large changes
        - High volume + extreme sentiment
        """
        df = pd.DataFrame({"sentiment": sentiment_series})
        
        # Z-score anomaly
        mean = df["sentiment"].mean()
        std = df["sentiment"].std()
        df["z_score"] = (df["sentiment"] - mean) / (std + 1e-6)
        df["is_anomaly_zscore"] = np.abs(df["z_score"]) > z_threshold
        
        # Change anomaly
        df["change"] = df["sentiment"].diff().abs()
        change_threshold = df["change"].mean() + 2 * df["change"].std()
        df["is_anomaly_change"] = df["change"] > change_threshold
        
        # Volume-weighted anomaly (if volume provided)
        if volume_series is not None:
            df["volume"] = volume_series
            df["volume_zscore"] = (df["volume"] - df["volume"].mean()) / (df["volume"].std() + 1e-6)
            df["is_anomaly_volume"] = (np.abs(df["z_score"]) > 1.5) & (df["volume_zscore"] > 1.5)
        else:
            df["is_anomaly_volume"] = False
        
        # Combined anomaly flag
        df["is_anomaly"] = df["is_anomaly_zscore"] | df["is_anomaly_change"] | df["is_anomaly_volume"]
        
        return df
    
    def calculate_sentiment_divergence(
        self,
        sentiment_series: pd.Series,
        price_series: pd.Series,
        window: int = 10
    ) -> pd.DataFrame:
        """
        Calculate divergence between sentiment and price
        
        Divergence signals:
        - Bullish divergence: Price down, sentiment up
        - Bearish divergence: Price up, sentiment down
        """
        df = pd.DataFrame({
            "sentiment": sentiment_series,
            "price": price_series
        })
        
        # Calculate trends
        df["sentiment_ma"] = df["sentiment"].rolling(window).mean()
        df["price_ma"] = df["price"].rolling(window).mean()
        
        df["sentiment_trend"] = df["sentiment_ma"].diff()
        df["price_trend"] = df["price_ma"].diff()
        
        # Detect divergence
        df["bullish_divergence"] = (df["price_trend"] < 0) & (df["sentiment_trend"] > 0)
        df["bearish_divergence"] = (df["price_trend"] > 0) & (df["sentiment_trend"] < 0)
        
        # Divergence strength
        df["divergence_strength"] = np.abs(
            df["sentiment_trend"].fillna(0) - df["price_trend"].fillna(0) * 0.01
        )
        
        return df
    
    def get_realtime_dashboard(
        self,
        df: pd.DataFrame,
        symbol: str
    ) -> SentimentDashboard:
        """
        Generate real-time sentiment dashboard data
        
        Args:
            df: DataFrame with recent sentiment data
            symbol: Asset symbol
        
        Returns:
            SentimentDashboard object
        """
        if df.empty:
            return SentimentDashboard(
                symbol=symbol,
                current_sentiment=0.0,
                sentiment_label="neutral",
                trend="stable",
                news_volume_24h=0,
                bullish_ratio=0.5,
                bearish_ratio=0.5,
                heat_index=0.0,
                last_updated=datetime.now()
            )
        
        # Get recent data (last 24 hours)
        now = datetime.now()
        cutoff = now - timedelta(hours=24)
        
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
            recent = df[df["time"] >= cutoff]
        else:
            recent = df.tail(50)  # Fallback to last 50 entries
        
        if recent.empty:
            recent = df.tail(10)
        
        # Calculate metrics
        current_sentiment = recent["sentiment_score"].mean() if "sentiment_score" in recent.columns else 0.0
        
        # Determine label
        if current_sentiment > 0.2:
            sentiment_label = "positive"
        elif current_sentiment < -0.2:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"
        
        # Determine trend
        if len(df) >= 5:
            recent_mean = df.tail(5)["sentiment_score"].mean() if "sentiment_score" in df.columns else 0
            prev_mean = df.tail(10).head(5)["sentiment_score"].mean() if "sentiment_score" in df.columns else 0
            
            change = recent_mean - prev_mean
            
            if change > self.IMPROVING_THRESHOLD:
                trend = "improving"
            elif change < self.DECLINING_THRESHOLD:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        # News volume
        news_volume_24h = len(recent)
        
        # Ratios
        if "sentiment_label" in recent.columns:
            bullish_ratio = (recent["sentiment_label"] == "positive").mean()
            bearish_ratio = (recent["sentiment_label"] == "negative").mean()
        else:
            bullish_ratio = 0.5
            bearish_ratio = 0.5
        
        # Heat index
        heat_index = self.calculate_composite_index(
            current_sentiment,
            bullish_ratio,
            news_volume_24h
        )
        
        return SentimentDashboard(
            symbol=symbol,
            current_sentiment=current_sentiment,
            sentiment_label=sentiment_label,
            trend=trend,
            news_volume_24h=news_volume_24h,
            bullish_ratio=bullish_ratio,
            bearish_ratio=bearish_ratio,
            heat_index=heat_index,
            last_updated=now
        )
    
    def aggregate_by_interval(
        self,
        df: pd.DataFrame,
        interval: str = "1D",
        symbol: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Aggregate sentiment data by time interval
        
        Args:
            df: DataFrame with sentiment data
            interval: Pandas frequency string ('1H', '1D', '1W')
            symbol: Optional symbol to filter
        
        Returns:
            Aggregated DataFrame
        """
        if df.empty:
            return pd.DataFrame()
        
        df = df.copy()
        
        # Ensure time column
        if "time" not in df.columns:
            return pd.DataFrame()
        
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")
        
        # Filter by symbol if provided
        if symbol and "symbol" in df.columns:
            df = df[df["symbol"] == symbol]
        
        # Aggregate
        agg_funcs = {
            "sentiment_score": ["mean", "std", "min", "max", "count"],
        }
        
        if "sentiment_positive" in df.columns:
            agg_funcs["sentiment_positive"] = "mean"
        if "sentiment_negative" in df.columns:
            agg_funcs["sentiment_negative"] = "mean"
        if "sentiment_label" in df.columns:
            agg_funcs["sentiment_label"] = lambda x: (x == "positive").sum()
        
        result = df.resample(interval).agg(agg_funcs)
        
        # Flatten column names
        result.columns = ["_".join(col).strip("_") if isinstance(col, tuple) else col 
                         for col in result.columns]
        
        result = result.reset_index()
        
        # Add derived metrics
        if "sentiment_score_mean" in result.columns and "sentiment_score_count" in result.columns:
            result["sentiment_index"] = (result["sentiment_score_mean"] + 1) * 50
            result["interval_type"] = "daily" if interval == "1D" else "hourly"
            
            if symbol:
                result["symbol"] = symbol
        
        return result


# Convenience functions
def calculate_sentiment_index(
    sentiment_scores: List[float],
    volumes: Optional[List[int]] = None
) -> float:
    """Calculate overall sentiment index from list of scores"""
    
    if not sentiment_scores:
        return 50.0  # Neutral
    
    avg = np.mean(sentiment_scores)
    
    # Volume weighting if provided
    if volumes and len(volumes) == len(sentiment_scores):
        weighted_avg = np.average(sentiment_scores, weights=volumes)
        avg = (avg + weighted_avg) / 2
    
    # Convert to 0-100 scale
    return (avg + 1) * 50


if __name__ == "__main__":
    # Test the metrics engine
    engine = SentimentMetricsEngine()
    
    # Create sample data
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    sentiment_scores = np.random.uniform(-0.5, 0.5, 30)
    
    df = pd.DataFrame({
        "time": dates,
        "sentiment_score": sentiment_scores,
        "sentiment_label": ["positive" if s > 0.2 else "negative" if s < -0.2 else "neutral" 
                           for s in sentiment_scores]
    })
    
    # Test momentum
    momentum = engine.calculate_sentiment_momentum(df["sentiment_score"])
    print("Momentum indicators:")
    print(momentum.tail())
    
    # Test anomaly detection
    anomalies = engine.detect_sentiment_anomalies(df["sentiment_score"])
    print(f"\nAnomalies detected: {anomalies['is_anomaly'].sum()}")
    
    # Test dashboard
    dashboard = engine.get_realtime_dashboard(df, "GLD")
    print(f"\nDashboard: {dashboard}")
