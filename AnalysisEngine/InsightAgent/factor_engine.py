# AnalysisEngine/InsightAgent/factor_engine.py

import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class FactorConfig:
    """因子配置"""
    name: str
    weight: float
    normalize_method: str = 'z_score'  # 'z_score', 'min_max', 'rank'
    direction: int = 1  # 1: 正向 (越大越好), -1: 反向 (越小越好)

class FactorEngine:
    """多因子计算引擎"""
    
    def __init__(self):
        self.factor_library = self._initialize_factor_library()
    
    def _initialize_factor_library(self) -> Dict:
        """初始化因子库"""
        return {
            # 价值因子
            'pe_ratio': FactorConfig('pe_ratio', 0.10, direction=-1),
            'pb_ratio': FactorConfig('pb_ratio', 0.08, direction=-1),
            'ps_ratio': FactorConfig('ps_ratio', 0.07, direction=-1),
            'dividend_yield': FactorConfig('dividend_yield', 0.10, direction=1),
            'ev_ebitda': FactorConfig('ev_ebitda', 0.08, direction=-1),
            
            # 成长因子
            'revenue_growth_yoy': FactorConfig('revenue_growth_yoy', 0.12, direction=1),
            'earnings_growth_yoy': FactorConfig('earnings_growth_yoy', 0.12, direction=1),
            'roe': FactorConfig('roe', 0.10, direction=1),
            'roa': FactorConfig('roa', 0.08, direction=1),
            
            # 质量因子
            'profit_margin': FactorConfig('profit_margin', 0.08, direction=1),
            'debt_to_equity': FactorConfig('debt_to_equity', 0.06, direction=-1),
            'current_ratio': FactorConfig('current_ratio', 0.06, direction=1),
            'interest_coverage': FactorConfig('interest_coverage', 0.06, direction=1),
            
            # 动量因子
            'return_1m': FactorConfig('return_1m', 0.12, direction=1),
            'return_3m': FactorConfig('return_3m', 0.10, direction=1),
            'return_6m': FactorConfig('return_6m', 0.08, direction=1),
            'return_12m': FactorConfig('return_12m', 0.06, direction=1),
            
            # 技术因子
            'rsi': FactorConfig('rsi', 0.08, direction=-1),  # 偏好超卖
            'macd_signal': FactorConfig('macd_signal', 0.08, direction=1),
            'bb_position': FactorConfig('bb_position', 0.06, direction=1),
            'volume_surge': FactorConfig('volume_surge', 0.08, direction=1),
            
            # 波动率因子
            'volatility_20d': FactorConfig('volatility_20d', 0.06, direction=-1),
            'beta': FactorConfig('beta', 0.05, direction=-1),
            
            # 贵金属相关因子
            'gold_correlation': FactorConfig('gold_correlation', 0.15, direction=1),
            'gold_beta': FactorConfig('gold_beta', 0.12, direction=1),
            'correlation_stability': FactorConfig('correlation_stability', 0.08, direction=1),
        }
    
    def calculate_all_factors(
        self,
        price_data: pd.DataFrame,
        fundamental_data: pd.DataFrame = None,
        market_data: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        计算所有因子
        
        Args:
            price_data: 价格数据 (OHLCV)
            fundamental_data: 基本面数据
            market_data: 市场数据 (指数, 金价等)
        
        Returns:
            因子矩阵 (行: 股票, 列: 因子)
        """
        factor_df = pd.DataFrame(index=price_data.index)
        
        # 1. 价值因子 (如果有基本面数据)
        if fundamental_data is not None:
            if 'pe_ratio' in fundamental_data.columns:
                factor_df['pe_ratio'] = fundamental_data['pe_ratio']
            if 'pb_ratio' in fundamental_data.columns:
                factor_df['pb_ratio'] = fundamental_data['pb_ratio']
            if 'dividend_yield' in fundamental_data.columns:
                factor_df['dividend_yield'] = fundamental_data['dividend_yield']
        
        # 2. 成长因子
        if fundamental_data is not None:
            if 'revenue' in fundamental_data.columns:
                factor_df['revenue_growth_yoy'] = fundamental_data['revenue'].pct_change(4)  # 季度数据
            if 'earnings' in fundamental_data.columns:
                factor_df['earnings_growth_yoy'] = fundamental_data['earnings'].pct_change(4)
            if 'roe' in fundamental_data.columns:
                factor_df['roe'] = fundamental_data['roe']
        
        # 3. 动量因子
        close_price = price_data['close'] if 'close' in price_data.columns else price_data
        factor_df['return_1m'] = close_price.pct_change(21)  # 21个交易日
        factor_df['return_3m'] = close_price.pct_change(63)
        factor_df['return_6m'] = close_price.pct_change(126)
        factor_df['return_12m'] = close_price.pct_change(252)
        
        # 4. 技术因子
        try:
            from .indicators.momentum_indicators import MomentumIndicators
            from .indicators.trend_indicators import TrendIndicators
            
            factor_df['rsi'] = MomentumIndicators.rsi(close_price, 14)
            
            macd, signal, _ = TrendIndicators.macd(close_price)
            factor_df['macd_signal'] = macd - signal
            
            upper_bb, middle_bb, lower_bb = TrendIndicators.bollinger_bands(close_price)
            factor_df['bb_position'] = (close_price - lower_bb) / (upper_bb - lower_bb)
        except ImportError:
            pass
        
        # 5. 成交量因子
        if 'volume' in price_data.columns:
            volume = price_data['volume']
            avg_volume = volume.rolling(window=20).mean()
            factor_df['volume_surge'] = volume / avg_volume
        
        # 6. 波动率因子
        returns = close_price.pct_change()
        factor_df['volatility_20d'] = returns.rolling(window=20).std() * np.sqrt(252)
        
        # 7. 贵金属相关因子
        if market_data is not None and 'gold_price' in market_data.columns:
            gold_returns = market_data['gold_price'].pct_change()
            
            # 滚动相关性
            factor_df['gold_correlation'] = returns.rolling(window=60).corr(gold_returns)
            
            # Beta (对金价)
            covariance = returns.rolling(window=60).cov(gold_returns)
            gold_variance = gold_returns.rolling(window=60).var()
            factor_df['gold_beta'] = covariance / gold_variance
            
            # 相关性稳定性 (标准差越小越稳定)
            rolling_corr = returns.rolling(window=60).corr(gold_returns)
            factor_df['correlation_stability'] = -rolling_corr.rolling(window=60).std()
        
        return factor_df
    
    def normalize_factors(
        self,
        factor_df: pd.DataFrame,
        method: str = 'z_score'
    ) -> pd.DataFrame:
        """
        因子标准化
        
        Args:
            factor_df: 原始因子矩阵
            method: 'z_score', 'min_max', 'rank'
        
        Returns:
            标准化后的因子矩阵
        """
        normalized = factor_df.copy()
        
        if method == 'z_score':
            # Z-score标准化
            mean = factor_df.mean()
            std = factor_df.std()
            normalized = (factor_df - mean) / std
        
        elif method == 'min_max':
            # 最小-最大标准化到[0, 1]
            min_val = factor_df.min()
            max_val = factor_df.max()
            normalized = (factor_df - min_val) / (max_val - min_val)
        
        elif method == 'rank':
            # 排名标准化
            normalized = factor_df.rank(pct=True)
        
        # 处理异常值 (Winsorize)
        normalized = normalized.clip(lower=-3, upper=3)
        
        return normalized
    
    def calculate_composite_score(
        self,
        factor_df: pd.DataFrame,
        factor_weights: Dict[str, float] = None
    ) -> pd.Series:
        """
        计算综合因子得分
        
        Args:
            factor_df: 标准化后的因子矩阵
            factor_weights: 因子权重字典
        
        Returns:
            综合得分 (Series)
        """
        if factor_weights is None:
            factor_weights = {
                config.name: config.weight
                for config in self.factor_library.values()
            }
        
        # 应用方向调整
        adjusted_factors = factor_df.copy()
        for factor_name, config in self.factor_library.items():
            if factor_name in adjusted_factors.columns:
                adjusted_factors[factor_name] *= config.direction
        
        # 加权求和
        composite_score = pd.Series(0.0, index=factor_df.index)
        
        for factor_name, weight in factor_weights.items():
            if factor_name in adjusted_factors.columns:
                composite_score += adjusted_factors[factor_name] * weight
        
        return composite_score
    
    def factor_ic_analysis(
        self,
        factor_values: pd.DataFrame,
        forward_returns: pd.Series,
        periods: List[int] = [5, 10, 20]
    ) -> pd.DataFrame:
        """
        因子IC分析 (Information Coefficient)
        
        衡量因子预测能力
        
        Args:
            factor_values: 因子值 (T时刻)
            forward_returns: 未来收益率 (T+N时刻)
            periods: 预测期限列表
        
        Returns:
            IC统计表
        """
        ic_results = []
        
        for period in periods:
            # 计算未来N期收益率
            future_returns = forward_returns.shift(-period)
            
            # 计算IC (Spearman相关系数)
            ic = factor_values.corrwith(future_returns, method='spearman')
            
            ic_results.append({
                'period': period,
                'ic_mean': ic.mean(),
                'ic_std': ic.std(),
                'ic_ir': ic.mean() / ic.std() if ic.std() != 0 else 0,  # Information Ratio
                'ic_positive_ratio': (ic > 0).sum() / len(ic)
            })
        
        return pd.DataFrame(ic_results)
