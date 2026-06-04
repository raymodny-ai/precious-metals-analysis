# AnalysisEngine/InsightAgent/indicators/momentum_indicators.py

import pandas as pd
import numpy as np
from typing import Tuple

class MomentumIndicators:
    """动量类技术指标"""
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        相对强弱指数 (Relative Strength Index)
        
        范围: 0-100
        超买: >70, 超卖: <30
        """
        # 计算价格变化
        delta = data.diff()
        
        # 分离涨跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 平均涨跌
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # RS和RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def stochastic_oscillator(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """
        随机震荡指标 (Stochastic Oscillator)
        
        Returns:
            (%K线, %D线)
        """
        # %K线
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k_line = 100 * (close - lowest_low) / (highest_high - lowest_low)
        
        # %D线 (K的移动平均)
        d_line = k_line.rolling(window=d_period).mean()
        
        return k_line, d_line
    
    @staticmethod
    def cci(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 20
    ) -> pd.Series:
        """
        商品通道指数 (Commodity Channel Index)
        
        范围: -100到+100之间为正常
        >+100超买, <-100超卖
        """
        # 典型价格
        tp = (high + low + close) / 3
        
        # 移动平均
        sma = tp.rolling(window=period).mean()
        
        # 平均绝对偏差
        mad = tp.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - x.mean()))
        )
        
        # CCI
        cci = (tp - sma) / (0.015 * mad)
        
        return cci
    
    @staticmethod
    def williams_r(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        威廉指标 (Williams %R)
        
        范围: -100到0
        超买: >-20, 超卖: <-80
        """
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        
        williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)
        
        return williams_r
    
    @staticmethod
    def roc(data: pd.Series, period: int = 12) -> pd.Series:
        """
        变动率指标 (Rate of Change)
        
        衡量价格变化速度
        """
        roc = 100 * (data - data.shift(period)) / data.shift(period)
        return roc
    
    @staticmethod
    def momentum(data: pd.Series, period: int = 10) -> pd.Series:
        """
        动量指标 (Momentum)
        
        当前价格与N期前价格的差值
        """
        return data - data.shift(period)
