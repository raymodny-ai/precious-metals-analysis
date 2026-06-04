# tests/test_phase4_indicators.py

"""
Phase 4 技术指标模块单元测试

测试所有5类指标的正确性
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 导入指标模块
import sys
sys.path.insert(0, 'f:/Financial Project/TrendRadar  BettaFish/PreciousInsight')

from AnalysisEngine.InsightAgent.indicators.trend_indicators import TrendIndicators
from AnalysisEngine.InsightAgent.indicators.momentum_indicators import MomentumIndicators
from AnalysisEngine.InsightAgent.indicators.volume_indicators import VolumeIndicators
from AnalysisEngine.InsightAgent.indicators.volatility_indicators import VolatilityIndicators
from AnalysisEngine.InsightAgent.indicators.precious_metals_indicators import PreciousMetalsIndicators


class TestTrendIndicators:
    """测试趋势指标"""
    
    @pytest.fixture
    def sample_prices(self):
        """生成测试数据"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        return pd.Series(prices, index=dates)
    
    @pytest.fixture
    def ohlc_data(self):
        """生成OHLC数据"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        close = 100 + np.cumsum(np.random.randn(100) * 2)
        high = close + np.random.rand(100) * 2
        low = close - np.random.rand(100) * 2
        
        return pd.DataFrame({
            'close': close,
            'high': high,
            'low': low
        }, index=dates)
    
    def test_sma(self, sample_prices):
        """测试简单移动平均"""
        sma = TrendIndicators.moving_average(sample_prices, period=10, ma_type='SMA')
        
        assert len(sma) == len(sample_prices)
        assert not sma.iloc[-1] != sma.iloc[-1]  # 检查不是NaN
        
        # 手动验证最后一个值
        expected = sample_prices.iloc[-10:].mean()
        assert abs(sma.iloc[-1] - expected) < 0.01
    
    def test_ema(self, sample_prices):
        """测试指数移动平均"""
        ema = TrendIndicators.moving_average(sample_prices, period=10, ma_type='EMA')
        
        assert len(ema) == len(sample_prices)
        assert not pd.isna(ema.iloc[-1])
        
        # EMA应该对最新价格反应更快
        sma = TrendIndicators.moving_average(sample_prices, period=10, ma_type='SMA')
        assert ema.iloc[-1] != sma.iloc[-1]  # 两者应该不同
    
    def test_macd(self, sample_prices):
        """测试MACD"""
        macd_line, signal_line, histogram = TrendIndicators.macd(sample_prices)
        
        assert len(macd_line) == len(sample_prices)
        assert len(signal_line) == len(sample_prices)
        assert len(histogram) == len(sample_prices)
        
        # MACD柱 = MACD线 - 信号线
        assert abs(histogram.iloc[-1] - (macd_line.iloc[-1] - signal_line.iloc[-1])) < 0.01
    
    def test_bollinger_bands(self, sample_prices):
        """测试布林带"""
        upper, middle, lower = TrendIndicators.bollinger_bands(sample_prices, period=20, std_multiplier=2.0)
        
        # 上轨应该 > 中轨 > 下轨
        assert upper.iloc[-1] > middle.iloc[-1] > lower.iloc[-1]
        
        # 中轨应该等于SMA
        sma = sample_prices.rolling(20).mean()
        assert abs(middle.iloc[-1] - sma.iloc[-1]) < 0.01
    
    def test_adx(self, ohlc_data):
        """测试ADX"""
        adx, plus_di, minus_di = TrendIndicators.adx(
            ohlc_data['high'], 
            ohlc_data['low'], 
            ohlc_data['close']
        )
        
        assert len(adx) == len(ohlc_data)
        # ADX应该在0-100之间
        assert 0 <= adx.iloc[-1] <= 100


class TestMomentumIndicators:
    """测试动量指标"""
    
    @pytest.fixture
    def sample_prices(self):
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        return pd.Series(prices, index=dates)
    
    def test_rsi(self, sample_prices):
        """测试RSI"""
        rsi = MomentumIndicators.rsi(sample_prices, period=14)
        
        assert len(rsi) == len(sample_prices)
        # RSI应该在0-100之间
        valid_rsi = rsi.dropna()
        assert all(0 <= val <= 100 for val in valid_rsi)
    
    def test_roc(self, sample_prices):
        """测试ROC"""
        roc = MomentumIndicators.roc(sample_prices, period=12)
        
        assert len(roc) == len(sample_prices)
        # 手动验证
        expected = 100 * (sample_prices.iloc[-1] - sample_prices.iloc[-13]) / sample_prices.iloc[-13]
        assert abs(roc.iloc[-1] - expected) < 0.01


class TestVolumeIndicators:
    """测试成交量指标"""
    
    @pytest.fixture
    def ohlcv_data(self):
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        close = 100 + np.cumsum(np.random.randn(100) * 2)
        high = close + np.random.rand(100) * 2
        low = close - np.random.rand(100) * 2
        volume = np.random.randint(1000000, 5000000, 100)
        
        return pd.DataFrame({
            'close': close,
            'high': high,
            'low': low,
            'volume': volume
        }, index=dates)
    
    def test_obv(self, ohlcv_data):
        """测试OBV"""
        obv = VolumeIndicators.obv(ohlcv_data['close'], ohlcv_data['volume'])
        
        assert len(obv) == len(ohlcv_data)
        assert obv.iloc[0] == ohlcv_data['volume'].iloc[0]
    
    def test_vwap(self, ohlcv_data):
        """测试VWAP"""
        vwap = VolumeIndicators.vwap(
            ohlcv_data['high'],
            ohlcv_data['low'],
            ohlcv_data['close'],
            ohlcv_data['volume']
        )
        
        assert len(vwap) == len(ohlcv_data)
        # VWAP应该在合理范围内
        assert ohlcv_data['low'].min() <= vwap.iloc[-1] <= ohlcv_data['high'].max()


class TestVolatilityIndicators:
    """测试波动率指标"""
    
    @pytest.fixture
    def ohlc_data(self):
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        close = 100 + np.cumsum(np.random.randn(100) * 2)
        high = close + np.random.rand(100) * 2
        low = close - np.random.rand(100) * 2
        
        return pd.DataFrame({
            'close': close,
            'high': high,
            'low': low
        }, index=dates)
    
    def test_atr(self, ohlc_data):
        """测试ATR"""
        atr = VolatilityIndicators.atr(
            ohlc_data['high'],
            ohlc_data['low'],
            ohlc_data['close'],
            period=14
        )
        
        assert len(atr) == len(ohlc_data)
        # ATR应该 > 0
        assert atr.iloc[-1] > 0
    
    def test_historical_volatility(self, ohlc_data):
        """测试历史波动率"""
        hv = VolatilityIndicators.historical_volatility(
            ohlc_data['close'],
            period=30,
            annualize=True
        )
        
        assert len(hv) == len(ohlc_data)
        # 年化波动率应该 > 0
        valid_hv = hv.dropna()
        assert all(val > 0 for val in valid_hv)


class TestPreciousMetalsIndicators:
    """测试贵金属专用指标"""
    
    def test_gold_silver_ratio(self):
        """测试金银比"""
        gold = pd.Series([1800, 1850, 1900])
        silver = pd.Series([24, 25, 26])
        
        ratio = PreciousMetalsIndicators.gold_silver_ratio(gold, silver)
        
        assert len(ratio) == 3
        # 金银比应该在合理范围 (50-90)
        assert all(50 <= val <= 90 for val in ratio)
    
    def test_real_interest_rate(self):
        """测试实际利率"""
        nominal = pd.Series([5.0, 5.5, 6.0])
        inflation = pd.Series([3.0, 3.5, 4.0])
        
        real_rate = PreciousMetalsIndicators.real_interest_rate_spread(nominal, inflation)
        
        assert len(real_rate) == 3
        assert abs(real_rate.iloc[0] - 2.0) < 0.01


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v', '--tb=short'])
