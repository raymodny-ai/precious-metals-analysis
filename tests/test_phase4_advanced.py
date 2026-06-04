# tests/test_phase4_advanced.py

"""
Phase 4 高级模块单元测试

测试因子引擎、VaR计算器、信号生成器和回测引擎
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import sys
sys.path.insert(0, 'f:/Financial Project/TrendRadar  BettaFish/PreciousInsight')

from AnalysisEngine.InsightAgent.factor_engine import FactorEngine
from AnalysisEngine.InsightAgent.risk.var_calculator import VaRCalculator, VaRResult
from AnalysisEngine.InsightAgent.signal_generator import (
    TrendFollowingStrategy,
    MeanReversionStrategy,
    MultiStrategySignalGenerator,
    SignalType
)
from AnalysisEngine.InsightAgent.simple_backtester import SimpleBacktester


class TestFactorEngine:
    """测试因子引擎"""
    
    @pytest.fixture
    def price_data(self):
        """生成价格数据"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=300, freq='D')
        close = 100 + np.cumsum(np.random.randn(300) * 2)
        high = close + np.random.rand(300) * 2
        low = close - np.random.rand(300) * 2
        volume = np.random.randint(1000000, 5000000, 300)
        
        return pd.DataFrame({
            'close': close,
            'high': high,
            'low': low,
            'volume': volume
        }, index=dates)
    
    def test_factor_engine_init(self):
        """测试因子引擎初始化"""
        engine = FactorEngine()
        assert engine.factor_library is not None
        assert len(engine.factor_library) > 20  # 应该有25+因子
    
    def test_calculate_factors(self, price_data):
        """测试因子计算"""
        engine = FactorEngine()
        
        factors = engine.calculate_all_factors(price_data)
        
        assert factors is not None
        assert len(factors) > 0
        # 应该包含动量因子
        assert 'return_1m' in factors.columns
        assert 'volatility_20d' in factors.columns
    
    def test_normalize_factors(self, price_data):
        """测试因子标准化"""
        engine = FactorEngine()
        
        factors = engine.calculate_all_factors(price_data)
        normalized = engine.normalize_factors(factors, method='z_score')
        
        # Z-score标准化后,均值应接近0,标准差接近1
        for col in normalized.columns:
            if normalized[col].notna().sum() > 10:  # 至少有10个有效值
                mean = normalized[col].mean()
                std = normalized[col].std()
                assert abs(mean) < 0.5  # 均值接近0
                assert abs(std - 1.0) < 0.5  # 标准差接近1
    
    def test_composite_score(self, price_data):
        """测试综合评分"""
        engine = FactorEngine()
        
        factors = engine.calculate_all_factors(price_data)
        normalized = engine.normalize_factors(factors)
        scores = engine.calculate_composite_score(normalized)
        
        assert scores is not None
        assert len(scores) == len(normalized)


class TestVaRCalculator:
    """测试VaR计算器"""
    
    @pytest.fixture
    def returns_data(self):
        """生成收益率数据"""
        np.random.seed(42)
        # 模拟正态分布收益率,均值0.05%,标准差1.5%
        returns = np.random.normal(0.0005, 0.015, 250)
        return pd.Series(returns)
    
    def test_var_calculator_init(self):
        """测试初始化"""
        calc = VaRCalculator(confidence_level=0.95)
        assert calc.confidence_level == 0.95
    
    def test_historical_var(self, returns_data):
        """测试历史模拟法VaR"""
        calc = VaRCalculator(confidence_level=0.95)
        result = calc.historical_var(returns_data)
        
        assert isinstance(result, VaRResult)
        assert result.var_value < 0  # VaR应该是负值(损失)
        assert result.cvar_value < result.var_value  # CVaR应该更负
        assert result.method == 'historical'
    
    def test_parametric_var(self, returns_data):
        """测试参数法VaR"""
        calc = VaRCalculator(confidence_level=0.95)
        result = calc.parametric_var(returns_data, distribution='normal')
        
        assert isinstance(result, VaRResult)
        assert result.var_value < 0
        assert result.method == 'parametric_normal'
    
    def test_monte_carlo_var(self, returns_data):
        """测试蒙特卡洛VaR"""
        calc = VaRCalculator(confidence_level=0.95)
        result = calc.monte_carlo_var(returns_data, n_simulations=1000)
        
        assert isinstance(result, VaRResult)
        assert result.var_value < 0
        assert result.method == 'monte_carlo'
    
    def test_compare_methods(self, returns_data):
        """测试方法对比"""
        calc = VaRCalculator(confidence_level=0.95)
        comparison = calc.compare_methods(returns_data)
        
        assert isinstance(comparison, pd.DataFrame)
        assert len(comparison) >= 3  # 至少3种方法
        assert 'VaR' in comparison.columns
        assert 'CVaR' in comparison.columns


class TestSignalGenerator:
    """测试信号生成器"""
    
    @pytest.fixture
    def market_data(self):
        """生成市场数据"""
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
    
    def test_trend_following_strategy(self, market_data):
        """测试趋势跟踪策略"""
        strategy = TrendFollowingStrategy(fast_period=5, slow_period=20)
        signal = strategy.generate_signal(market_data)
        
        assert signal is not None
        assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        assert 0 <= signal.strength <= 1
        assert signal.metadata is not None
        assert 'stop_loss' in signal.metadata
    
    def test_mean_reversion_strategy(self, market_data):
        """测试均值回归策略"""
        strategy = MeanReversionStrategy(bb_period=20, rsi_period=14)
        signal = strategy.generate_signal(market_data)
        
        assert signal is not None
        assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        assert 'rsi' in signal.metadata
    
    def test_multi_strategy_generator(self, market_data):
        """测试多策略融合"""
        trend_strategy = TrendFollowingStrategy()
        mean_rev_strategy = MeanReversionStrategy()
        
        multi_gen = MultiStrategySignalGenerator([trend_strategy, mean_rev_strategy])
        consensus, individual = multi_gen.generate_consensus_signal(market_data)
        
        assert consensus is not None
        assert len(individual) == 2
        assert consensus.strategy_name == "Consensus"
        assert 'consensus_score' in consensus.metadata


class TestSimpleBacktester:
    """测试回测引擎"""
    
    @pytest.fixture
    def price_data(self):
        """生成价格数据"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        close = 100 + np.cumsum(np.random.randn(100) * 0.5)  # 小幅波动
        high = close + np.random.rand(100) * 1
        low = close - np.random.rand(100) * 1
        volume = np.random.randint(1000000, 5000000, 100)
        
        df = pd.DataFrame({
            'close': close,
            'high': high,
            'low': low,
            'volume': volume
        }, index=dates)
        df['symbol'] = 'TEST'
        return df
    
    def test_backtester_init(self):
        """测试初始化"""
        bt = SimpleBacktester(initial_capital=100000)
        assert bt.initial_capital == 100000
        assert bt.cash == 100000
    
    def test_run_backtest(self, price_data):
        """测试运行回测"""
        bt = SimpleBacktester(initial_capital=100000)
        
        # 简单策略:价格上涨买入,下跌卖出
        def simple_signal(data):
            from AnalysisEngine.InsightAgent.signal_generator import TradingSignal, SignalType
            close = data['close'] if 'close' in data else data.iloc[0]['close']
            
            if isinstance(close, pd.Series):
                current_price = close.iloc[-1]
            else:
                current_price = close
            
            # 简单规则
            if len(data) >= 2:
                prev_price = data['close'].iloc[-2] if 'close' in data else data.iloc[-2]['close']
                if current_price > prev_price:
                    signal_type = SignalType.BUY
                else:
                    signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD
            
            return TradingSignal(
                timestamp=data.index[-1],
                symbol='TEST',
                signal_type=signal_type,
                strength=0.5,
                price=current_price,
                strategy_name='Simple',
                reasoning='Test'
            )
        
        results = bt.run_backtest(price_data, simple_signal)
        
        assert 'summary' in results
        assert 'equity_curve' in results
        assert 'trades' in results
        
        summary = results['summary']
        assert 'total_return' in summary
        assert 'sharpe_ratio' in summary
        assert 'max_drawdown' in summary


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
