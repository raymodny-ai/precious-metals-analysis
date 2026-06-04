"""
技术指标库

包含5类技术指标:
- trend_indicators: 趋势指标 (MA, MACD, BB, SAR, ADX, Ichimoku)
- momentum_indicators: 动量指标 (RSI, Stochastic, CCI, Williams %R, ROC)
- volume_indicators: 成交量指标 (OBV, MFI, VWAP, CMF, A/D)
- volatility_indicators: 波动率指标 (ATR, Keltner, Donchian)
- precious_metals_indicators: 贵金属专用指标
"""

from .trend_indicators import TrendIndicators
from .momentum_indicators import MomentumIndicators
from .volume_indicators import VolumeIndicators
from .volatility_indicators import VolatilityIndicators
from .precious_metals_indicators import PreciousMetalsIndicators

__all__ = [
    'TrendIndicators',
    'MomentumIndicators',
    'VolumeIndicators',
    'VolatilityIndicators',
    'PreciousMetalsIndicators'
]
