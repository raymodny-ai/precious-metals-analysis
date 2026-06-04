# AnalysisEngine/InsightAgent/indicators/trend_indicators.py

import pandas as pd
import numpy as np
from typing import Tuple, Optional

class TrendIndicators:
    """趋势类技术指标"""
    
    @staticmethod
    def moving_average(data: pd.Series, period: int, ma_type: str = 'SMA') -> pd.Series:
        """
        移动平均线
        
        Args:
            data: 价格序列
            period: 周期
            ma_type: 'SMA'简单/'EMA'指数/'WMA'加权/'DEMA'双指数
        
        Returns:
            移动平均序列
        """
        if ma_type == 'SMA':
            return data.rolling(window=period).mean()
        
        elif ma_type == 'EMA':
            return data.ewm(span=period, adjust=False).mean()
        
        elif ma_type == 'WMA':
            weights = np.arange(1, period + 1)
            return data.rolling(window=period).apply(
                lambda x: np.dot(x, weights) / weights.sum(), raw=True
            )
        
        elif ma_type == 'DEMA':
            # 双指数移动平均
            ema1 = data.ewm(span=period, adjust=False).mean()
            ema2 = ema1.ewm(span=period, adjust=False).mean()
            return 2 * ema1 - ema2
        
        else:
            raise ValueError(f"Unknown MA type: {ma_type}")
    
    @staticmethod
    def macd(
        data: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD指标 (Moving Average Convergence Divergence)
        
        Returns:
            (MACD线, 信号线, MACD柱)
        """
        # 快速EMA
        ema_fast = data.ewm(span=fast_period, adjust=False).mean()
        
        # 慢速EMA
        ema_slow = data.ewm(span=slow_period, adjust=False).mean()
        
        # MACD线
        macd_line = ema_fast - ema_slow
        
        # 信号线
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # MACD柱
        macd_histogram = macd_line - signal_line
        
        return macd_line, signal_line, macd_histogram
    
    @staticmethod
    def bollinger_bands(
        data: pd.Series,
        period: int = 20,
        std_multiplier: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        布林带
        
        Returns:
            (上轨, 中轨, 下轨)
        """
        # 中轨 (SMA)
        middle_band = data.rolling(window=period).mean()
        
        # 标准差
        std = data.rolling(window=period).std()
        
        # 上轨和下轨
        upper_band = middle_band + (std * std_multiplier)
        lower_band = middle_band - (std * std_multiplier)
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def parabolic_sar(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        acceleration: float = 0.02,
        maximum: float = 0.2
    ) -> pd.Series:
        """
        抛物线转向指标 (Parabolic SAR)
        
        用于确定趋势反转点
        """
        sar = close.copy()
        af = acceleration
        uptrend = True
        ep = high.iloc[0]  # 极值点
        
        for i in range(1, len(close)):
            if uptrend:
                sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
                
                if low.iloc[i] < sar.iloc[i]:
                    uptrend = False
                    sar.iloc[i] = ep
                    ep = low.iloc[i]
                    af = acceleration
                else:
                    if high.iloc[i] > ep:
                        ep = high.iloc[i]
                        af = min(af + acceleration, maximum)
            else:
                sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
                
                if high.iloc[i] > sar.iloc[i]:
                    uptrend = True
                    sar.iloc[i] = ep
                    ep = high.iloc[i]
                    af = acceleration
                else:
                    if low.iloc[i] < ep:
                        ep = low.iloc[i]
                        af = min(af + acceleration, maximum)
        
        return sar
    
    @staticmethod
    def adx(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        平均趋向指数 (Average Directional Index)
        
        衡量趋势强度 (>25表示强趋势)
        
        Returns:
            (ADX, +DI, -DI)
        """
        # 真实波动幅度
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 方向移动
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # 平滑处理
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean() / atr
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx, plus_di, minus_di
    
    @staticmethod
    def ichimoku_cloud(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        conversion_period: int = 9,
        base_period: int = 26,
        span_b_period: int = 52,
        displacement: int = 26
    ) -> dict:
        """
        一目均衡表 (Ichimoku Cloud)
        
        返回云图各组成部分
        """
        # 转换线 (Tenkan-sen)
        conversion_line = (
            high.rolling(window=conversion_period).max() +
            low.rolling(window=conversion_period).min()
        ) / 2
        
        # 基准线 (Kijun-sen)
        base_line = (
            high.rolling(window=base_period).max() +
            low.rolling(window=base_period).min()
        ) / 2
        
        # 先行跨度A (Senkou Span A)
        span_a = ((conversion_line + base_line) / 2).shift(displacement)
        
        # 先行跨度B (Senkou Span B)
        span_b = (
            (high.rolling(window=span_b_period).max() +
             low.rolling(window=span_b_period).min()) / 2
        ).shift(displacement)
        
        # 延迟线 (Chikou Span)
        lagging_span = close.shift(-displacement)
        
        return {
            'conversion_line': conversion_line,
            'base_line': base_line,
            'span_a': span_a,
            'span_b': span_b,
            'lagging_span': lagging_span
        }
