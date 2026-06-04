# AnalysisEngine/InsightAgent/risk/var_calculator.py

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class VaRResult:
    """VaR计算结果"""
    var_value: float
    cvar_value: float
    confidence_level: float
    method: str
    worst_scenarios: pd.Series = None

class VaRCalculator:
    """风险价值计算器"""
    
    def __init__(self, confidence_level: float = 0.95):
        """
        Args:
            confidence_level: 置信水平 (默认95%)
        """
        self.confidence_level = confidence_level
    
    def historical_var(
        self,
        returns: pd.Series,
        confidence_level: float = None
    ) -> VaRResult:
        """
        历史模拟法 VaR
        
        优点: 不假设分布, 直接使用历史数据
        缺点: 依赖历史数据, 可能无法捕捉极端事件
        
        Args:
            returns: 历史收益率序列
            confidence_level: 置信水平
        
        Returns:
            VaR结果
        """
        if confidence_level is None:
            confidence_level = self.confidence_level
        
        # 计算VaR (取α分位数)
        var = np.percentile(returns, (1 - confidence_level) * 100)
        
        # 计算CVaR (超过VaR的平均损失)
        worst_returns = returns[returns <= var]
        cvar = worst_returns.mean()
        
        return VaRResult(
            var_value=var,
            cvar_value=cvar,
            confidence_level=confidence_level,
            method='historical',
            worst_scenarios=worst_returns
        )
    
    def parametric_var(
        self,
        returns: pd.Series,
        confidence_level: float = None,
        distribution: str = 'normal'
    ) -> VaRResult:
        """
        参数法 VaR
        
        假设收益率服从某种分布 (通常为正态分布)
        
        Args:
            returns: 历史收益率序列
            confidence_level: 置信水平
            distribution: 'normal' / 't_student' / 'skewed_t'
        
        Returns:
            VaR结果
        """
        if confidence_level is None:
            confidence_level = self.confidence_level
        
        mu = returns.mean()
        sigma = returns.std()
        
        if distribution == 'normal':
            # 正态分布
            z_score = stats.norm.ppf(1 - confidence_level)
            var = mu + z_score * sigma
            
            # CVaR (条件期望)
            cvar = mu - sigma * stats.norm.pdf(z_score) / (1 - confidence_level)
        
        elif distribution == 't_student':
            # t分布 (更厚的尾部, 适合金融数据)
            df = self._estimate_degrees_of_freedom(returns)
            t_value = stats.t.ppf(1 - confidence_level, df)
            var = mu + t_value * sigma * np.sqrt((df - 2) / df)
            
            # t分布CVaR近似
            cvar = var * 1.2  # 简化近似
        
        elif distribution == 'skewed_t':
            # 偏斜t分布 (考虑偏度和峰度)
            skewness = returns.skew()
            kurtosis = returns.kurtosis()
            
            # Cornish-Fisher展开
            z = stats.norm.ppf(1 - confidence_level)
            cf_adjustment = (z**2 - 1) * skewness / 6 + (z**3 - 3*z) * (kurtosis - 3) / 24
            adjusted_z = z + cf_adjustment
            
            var = mu + adjusted_z * sigma
            cvar = var * 1.15  # 简化近似
        
        else:
            raise ValueError(f"Unknown distribution: {distribution}")
        
        return VaRResult(
            var_value=var,
            cvar_value=cvar,
            confidence_level=confidence_level,
            method=f'parametric_{distribution}'
        )
    
    def monte_carlo_var(
        self,
        returns: pd.Series,
        confidence_level: float = None,
        n_simulations: int = 10000,
        forecast_horizon: int = 1
    ) -> VaRResult:
        """
        蒙特卡洛模拟 VaR
        
        通过随机模拟生成未来可能的收益率场景
        
        Args:
            returns: 历史收益率序列
            confidence_level: 置信水平
            n_simulations: 模拟次数
            forecast_horizon: 预测期限 (天数)
        
        Returns:
            VaR结果
        """
        if confidence_level is None:
            confidence_level = self.confidence_level
        
        mu = returns.mean()
        sigma = returns.std()
        
        # 生成模拟收益率
        np.random.seed(42)
        simulated_returns = np.random.normal(
            mu * forecast_horizon,
            sigma * np.sqrt(forecast_horizon),
            n_simulations
        )
        
        # 计算VaR
        var = np.percentile(simulated_returns, (1 - confidence_level) * 100)
        
        # 计算CVaR
        worst_scenarios = simulated_returns[simulated_returns <= var]
        cvar = worst_scenarios.mean()
        
        return VaRResult(
            var_value=var,
            cvar_value=cvar,
            confidence_level=confidence_level,
            method='monte_carlo',
            worst_scenarios=pd.Series(worst_scenarios)
        )
    
    @staticmethod
    def _estimate_degrees_of_freedom(returns: pd.Series) -> float:
        """估计t分布的自由度"""
        kurtosis = returns.kurtosis()
        # 根据峰度估计自由度: df ≈ 6/(峰度-3) + 4
        df = max(6 / max(kurtosis, 0.1) + 4, 5)
        return df
    
    def compare_methods(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> pd.DataFrame:
        """
        比较不同VaR计算方法
        
        Args:
            returns: 历史收益率
            confidence_level: 置信水平
        
        Returns:
            比较结果DataFrame
        """
        methods = [
            ('Historical', lambda: self.historical_var(returns, confidence_level)),
            ('Parametric Normal', lambda: self.parametric_var(returns, confidence_level, 'normal')),
            ('Parametric t-Student', lambda: self.parametric_var(returns, confidence_level, 't_student')),
            ('Monte Carlo', lambda: self.monte_carlo_var(returns, confidence_level)),
        ]
        
        results = []
        for method_name, method_func in methods:
            try:
                result = method_func()
                results.append({
                    'Method': method_name,
                    'VaR': result.var_value,
                    'CVaR': result.cvar_value,
                    'VaR (%)': result.var_value * 100,
                    'CVaR (%)': result.cvar_value * 100
                })
            except Exception as e:
                print(f"Error in {method_name}: {e}")
        
        return pd.DataFrame(results)
