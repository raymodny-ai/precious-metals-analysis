"""
Feature Engineering Module
特征工程模块
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta

from ..utils.logger import setup_logging

logger = setup_logging("feature_engineering")


class FeatureEngineer:
    """
    Feature engineering for precious metals prediction
    
    Feature categories:
    1. Price features (lags, returns, moving averages)
    2. Technical indicators (RSI, MACD, Bollinger Bands)
    3. Volatility features
    4. Sentiment features
    5. ETF flow features
    6. Macro features
    7. Calendar features
    """
    
    def __init__(self):
        self.feature_names = []
    
    def engineer_all_features(
        self,
        price_df: pd.DataFrame,
        sentiment_df: Optional[pd.DataFrame] = None,
        etf_flow_df: Optional[pd.DataFrame] = None,
        macro_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Generate all features from available data
        
        Args:
            price_df: Price data with OHLCV columns
            sentiment_df: Sentiment metrics (optional)
            etf_flow_df: ETF flow data (optional)
            macro_df: Macro economic data (optional)
        
        Returns:
            DataFrame with all engineered features
        """
        logger.info("Starting feature engineering...")
        
        df = price_df.copy()
        
        # Ensure time index
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
            df = df.sort_values("time")
        
        # 1. Price features
        logger.info("Engineering price features...")
        df = self.add_price_features(df)
        
        # 2. Technical indicators
        logger.info("Engineering technical indicators...")
        df = self.add_technical_indicators(df)
        
        # 3. Volatility features
        logger.info("Engineering volatility features...")
        df = self.add_volatility_features(df)
        
        # 4. Calendar features
        logger.info("Engineering calendar features...")
        df = self.add_calendar_features(df)
        
        # 5. Merge sentiment features
        if sentiment_df is not None and not sentiment_df.empty:
            logger.info("Merging sentiment features...")
            df = self.merge_sentiment_features(df, sentiment_df)
        
        # 6. Merge ETF flow features
        if etf_flow_df is not None and not etf_flow_df.empty:
            logger.info("Merging ETF flow features...")
            df = self.merge_etf_features(df, etf_flow_df)
        
        # 7. Merge macro features
        if macro_df is not None and not macro_df.empty:
            logger.info("Merging macro features...")
            df = self.merge_macro_features(df, macro_df)
        
        # Store feature names
        self.feature_names = [c for c in df.columns if c not in ["time", "symbol", "date"]]
        
        logger.info(f"Feature engineering complete. Total features: {len(self.feature_names)}")
        
        return df
    
    def add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price-based features"""
        df = df.copy()
        
        # Ensure close column exists
        if "close" not in df.columns:
            return df
        
        # Lag features
        for lag in [1, 2, 3, 5, 10, 20]:
            df[f"close_lag_{lag}"] = df["close"].shift(lag)
        
        # Returns
        df["returns_1d"] = df["close"].pct_change()
        df["returns_5d"] = df["close"].pct_change(5)
        df["returns_20d"] = df["close"].pct_change(20)
        
        # Log returns
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
        
        # Moving averages
        for window in [5, 10, 20, 50]:
            df[f"ma_{window}"] = df["close"].rolling(window).mean()
            df[f"ma_{window}_ratio"] = df["close"] / df[f"ma_{window}"]
        
        # Exponential moving averages
        for span in [12, 26]:
            df[f"ema_{span}"] = df["close"].ewm(span=span).mean()
        
        # Price momentum
        df["momentum_5d"] = df["close"] - df["close"].shift(5)
        df["momentum_20d"] = df["close"] - df["close"].shift(20)
        
        # Price range
        if "high" in df.columns and "low" in df.columns:
            df["daily_range"] = df["high"] - df["low"]
            df["daily_range_pct"] = df["daily_range"] / df["close"]
        
        return df
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators"""
        df = df.copy()
        
        close = df["close"]
        
        # RSI (Relative Strength Index)
        for period in [7, 14, 21]:
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / (loss + 1e-10)
            df[f"rsi_{period}"] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        df["macd"] = ema_12 - ema_26
        df["macd_signal"] = df["macd"].ewm(span=9).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]
        
        # Bollinger Bands
        for window in [20]:
            ma = close.rolling(window).mean()
            std = close.rolling(window).std()
            df[f"bb_upper_{window}"] = ma + 2 * std
            df[f"bb_lower_{window}"] = ma - 2 * std
            df[f"bb_width_{window}"] = (df[f"bb_upper_{window}"] - df[f"bb_lower_{window}"]) / ma
            df[f"bb_position_{window}"] = (close - df[f"bb_lower_{window}"]) / (
                df[f"bb_upper_{window}"] - df[f"bb_lower_{window}"] + 1e-10
            )
        
        # Average True Range (ATR)
        if "high" in df.columns and "low" in df.columns:
            high_low = df["high"] - df["low"]
            high_close = np.abs(df["high"] - close.shift())
            low_close = np.abs(df["low"] - close.shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df["atr_14"] = tr.rolling(14).mean()
            df["atr_ratio"] = df["atr_14"] / close
        
        # Stochastic Oscillator
        if "high" in df.columns and "low" in df.columns:
            low_14 = df["low"].rolling(14).min()
            high_14 = df["high"].rolling(14).max()
            df["stoch_k"] = 100 * (close - low_14) / (high_14 - low_14 + 1e-10)
            df["stoch_d"] = df["stoch_k"].rolling(3).mean()
        
        # Rate of Change (ROC)
        for period in [5, 10, 20]:
            df[f"roc_{period}"] = ((close - close.shift(period)) / close.shift(period)) * 100
        
        return df
    
    def add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility features"""
        df = df.copy()
        
        returns = df["close"].pct_change()
        
        # Historical volatility
        for window in [5, 10, 20, 60]:
            df[f"volatility_{window}d"] = returns.rolling(window).std() * np.sqrt(252)
        
        # Volatility ratio
        df["volatility_ratio_5_20"] = df["volatility_5d"] / (df["volatility_20d"] + 1e-10)
        
        # Parkinson volatility (if high/low available)
        if "high" in df.columns and "low" in df.columns:
            log_hl = np.log(df["high"] / df["low"])
            df["parkinson_vol"] = np.sqrt((1 / (4 * np.log(2))) * (log_hl ** 2).rolling(20).mean()) * np.sqrt(252)
        
        # GARCH-like features
        df["squared_returns"] = returns ** 2
        df["ewm_variance"] = df["squared_returns"].ewm(span=20).mean()
        
        # Volatility regime
        vol_median = df["volatility_20d"].expanding().median()
        df["high_volatility_regime"] = (df["volatility_20d"] > vol_median).astype(int)
        
        return df
    
    def add_calendar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add calendar/time features"""
        df = df.copy()
        
        if "time" not in df.columns:
            return df
        
        time_col = pd.to_datetime(df["time"])
        
        # Day features
        df["day_of_week"] = time_col.dt.dayofweek
        df["day_of_month"] = time_col.dt.day
        df["week_of_year"] = time_col.dt.isocalendar().week.astype(int)
        df["month"] = time_col.dt.month
        df["quarter"] = time_col.dt.quarter
        
        # Binary features
        df["is_monday"] = (time_col.dt.dayofweek == 0).astype(int)
        df["is_friday"] = (time_col.dt.dayofweek == 4).astype(int)
        df["is_month_start"] = time_col.dt.is_month_start.astype(int)
        df["is_month_end"] = time_col.dt.is_month_end.astype(int)
        df["is_quarter_end"] = time_col.dt.is_quarter_end.astype(int)
        
        # Cyclical encoding for day of week
        df["day_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
        df["day_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
        
        # Cyclical encoding for month
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
        
        return df
    
    def merge_sentiment_features(
        self,
        df: pd.DataFrame,
        sentiment_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge sentiment features"""
        df = df.copy()
        
        # Prepare sentiment data
        sent = sentiment_df.copy()
        
        if "time" in sent.columns:
            sent["date"] = pd.to_datetime(sent["time"]).dt.date
        elif "date" in sent.columns:
            sent["date"] = pd.to_datetime(sent["date"]).dt.date
        else:
            return df
        
        # Prepare price data
        if "time" in df.columns:
            df["date"] = pd.to_datetime(df["time"]).dt.date
        
        # Select sentiment columns to merge
        sentiment_cols = [c for c in sent.columns if "sentiment" in c.lower() or c in [
            "bullish_ratio", "bearish_ratio", "heat_index", "news_volume"
        ]]
        
        if not sentiment_cols:
            return df
        
        # Aggregate sentiment by date if needed
        sent_agg = sent.groupby("date")[sentiment_cols].mean().reset_index()
        
        # Merge
        df = df.merge(sent_agg, on="date", how="left", suffixes=("", "_sent"))
        
        # Fill missing with neutral values
        for col in sentiment_cols:
            if col in df.columns:
                if "ratio" in col:
                    df[col] = df[col].fillna(0.5)
                elif "score" in col or "sentiment" in col:
                    df[col] = df[col].fillna(0)
                else:
                    df[col] = df[col].fillna(0)
        
        return df
    
    def merge_etf_features(
        self,
        df: pd.DataFrame,
        etf_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge ETF flow features"""
        df = df.copy()
        
        etf = etf_df.copy()
        
        # Prepare dates
        if "time" in etf.columns:
            etf["date"] = pd.to_datetime(etf["time"]).dt.date
        
        if "time" in df.columns:
            df["date"] = pd.to_datetime(df["time"]).dt.date
        
        # Select ETF flow columns
        flow_cols = [c for c in etf.columns if "flow" in c.lower() or c in [
            "net_flow", "aum", "shares_outstanding"
        ]]
        
        if not flow_cols:
            return df
        
        # Aggregate by date
        etf_agg = etf.groupby("date")[flow_cols].mean().reset_index()
        
        # Merge
        df = df.merge(etf_agg, on="date", how="left", suffixes=("", "_etf"))
        
        # Fill missing
        for col in flow_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        return df
    
    def merge_macro_features(
        self,
        df: pd.DataFrame,
        macro_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge macroeconomic features"""
        df = df.copy()
        
        macro = macro_df.copy()
        
        # Prepare dates
        if "time" in macro.columns:
            macro["date"] = pd.to_datetime(macro["time"]).dt.date
        
        if "time" in df.columns:
            df["date"] = pd.to_datetime(df["time"]).dt.date
        
        # Select macro columns
        macro_cols = [c for c in macro.columns if c not in ["time", "date"]]
        
        if not macro_cols:
            return df
        
        # Forward fill missing values (macro data updates less frequently)
        macro = macro.sort_values("date")
        macro[macro_cols] = macro[macro_cols].ffill()
        
        # Merge
        df = df.merge(macro[["date"] + macro_cols], on="date", how="left", suffixes=("", "_macro"))
        
        # Forward fill after merge
        for col in macro_cols:
            if col in df.columns:
                df[col] = df[col].ffill()
        
        return df
    
    def prepare_for_training(
        self,
        df: pd.DataFrame,
        target_col: str = "close",
        horizon: int = 1,
        drop_na: bool = True
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare data for ML training
        
        Args:
            df: Feature DataFrame
            target_col: Column to predict
            horizon: Prediction horizon (days ahead)
            drop_na: Whether to drop rows with NaN
        
        Returns:
            (features_df, target_series)
        """
        df = df.copy()
        
        # Create target variable (future return)
        df["target"] = df[target_col].shift(-horizon).pct_change(horizon)
        
        # Alternative: next day's price
        df["target_price"] = df[target_col].shift(-horizon)
        
        # Direction
        df["target_direction"] = (df["target"] > 0).astype(int)
        
        # Drop non-feature columns
        exclude_cols = ["time", "date", "symbol", "target", "target_price", "target_direction"]
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        
        # Drop NaN if requested
        if drop_na:
            df = df.dropna(subset=feature_cols + ["target"])
        
        X = df[feature_cols]
        y = df["target"]
        
        return X, y
    
    def get_feature_importance_groups(self) -> Dict[str, List[str]]:
        """Get feature groups for analysis"""
        groups = {
            "price": [f for f in self.feature_names if any(x in f for x in ["close", "return", "momentum", "ma_", "ema_"])],
            "technical": [f for f in self.feature_names if any(x in f for x in ["rsi", "macd", "bb_", "stoch", "roc", "atr"])],
            "volatility": [f for f in self.feature_names if "volatil" in f.lower() or "variance" in f],
            "sentiment": [f for f in self.feature_names if "sentiment" in f.lower() or "bullish" in f or "bearish" in f],
            "etf_flow": [f for f in self.feature_names if "flow" in f.lower() or "aum" in f],
            "macro": [f for f in self.feature_names if any(x in f for x in ["treasury", "vix", "dxy", "cpi"])],
            "calendar": [f for f in self.feature_names if any(x in f for x in ["day", "month", "week", "quarter", "is_"])]
        }
        return groups


if __name__ == "__main__":
    # Test feature engineering
    import yfinance as yf
    
    # Get sample data
    ticker = yf.Ticker("GLD")
    df = ticker.history(period="2y")
    df = df.reset_index()
    df.columns = df.columns.str.lower()
    df = df.rename(columns={"date": "time"})
    
    # Engineer features
    fe = FeatureEngineer()
    df_features = fe.engineer_all_features(df)
    
    print(f"Original columns: {len(df.columns)}")
    print(f"After feature engineering: {len(df_features.columns)}")
    print(f"\nFeature groups:")
    for group, features in fe.get_feature_importance_groups().items():
        print(f"  {group}: {len(features)} features")
    
    # Prepare for training
    X, y = fe.prepare_for_training(df_features)
    print(f"\nTraining data shape: X={X.shape}, y={y.shape}")
