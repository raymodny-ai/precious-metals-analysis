# AnalysisEngine/InsightAgent/indicators/volatility_indicators.py

import pandas as pd
import numpy as np
from typing import Tuple

class VolatilityIndicators:
    """波动率类技术指标"""
    
    @staticmethod
    def atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        平均真实波幅 (Average True Range)
        
        衡量市场波动性
        """
        # 真实波动幅度
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def keltner_channel(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        ema_period: int = 20,
        atr_period: int = 10,
        multiplier: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        肯特纳通道 (Keltner Channel)
        
        基于ATR的趋势通道
        
        Returns:
            (上轨, 中轨, 下轨)
        """
        # 中轨 (EMA)
        middle_line = close.ewm(span=ema_period, adjust=False).mean()
        
        # ATR
        atr = VolatilityIndicators.atr(high, low, close, atr_period)
        
        # 上下轨
        upper_band = middle_line + (multiplier * atr)
        lower_band = middle_line - (multiplier * atr)
        
        return upper_band, middle_line, lower_band
    
    @staticmethod
    def standard_deviation(data: pd.Series, period: int = 20) -> pd.Series:
        """
        标准差 (Standard Deviation)
        
        波动率的基础度量
        """
        return data.rolling(window=period).std()
    
    @staticmethod
    def historical_volatility(
        close: pd.Series,
        period: int = 30,
        annualize: bool = True
    ) -> pd.Series:
        """
        历史波动率 (Historical Volatility)
        
        对数收益率的标准差
        """
        # 对数收益率
        log_returns = np.log(close / close.shift(1))
        
        # 标准差
        volatility = log_returns.rolling(window=period).std()
        
        # 年化
        if annualize:
            volatility = volatility * np.sqrt(252)  # 假设252个交易日
        
        return volatility
    
    @staticmethod
    def donchian_channel(
        high: pd.Series,
        low: pd.Series,
        period: int = 20
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        唐奇安通道 (Donchian Channel)
        
        基于最高/最低价的通道
        
        Returns:
            (上轨, 中轨, 下轨)
        """
        upper_band = high.rolling(window=period).max()
        lower_band = low.rolling(window=period).min()
        middle_band = (upper_band + lower_band) / 2
        
        return upper_band, middle_band, lower_band
