# AnalysisEngine/InsightAgent/risk/stress_tester.py

"""
压力测试框架

支持:
- 预定义压力场景 (金融危机、地缘冲突等)
- 场景分析
- 历史危机回测
- 反向压力测试
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class StressScenario:
    """压力测试场景"""
    name: str
    description: str
    shock_parameters: Dict[str, float]
    probability: float = 0.01

class StressTester:
    """压力测试引擎"""
    
    def __init__(self):
        self.scenarios = self._define_scenarios()
    
    def _define_scenarios(self) -> List[StressScenario]:
        """定义压力测试场景"""
        return [
            StressScenario(
                name="2008_financial_crisis",
                description="类似2008年金融危机",
                shock_parameters={
                    'gold_return': 0.05,      # 金价+5%
                    'stocks_return': -0.40,   # 股市-40%
                    'vix_change': 3.0,        # VIX暴涨3倍
                    'credit_spread': 0.06     # 信用利差+600bp
                },
                probability=0.01
            ),
            StressScenario(
                name="fed_hawkish_shock",
                description="美联储意外大幅加息",
                shock_parameters={
                    'gold_return': -0.15,     # 金价-15%
                    'stocks_return': -0.20,   # 股市-20%
                    'dxy_return': 0.10,       # 美元+10%
                    'bond_yield_change': 0.02 # 收益率+200bp
                },
                probability=0.05
            ),
            StressScenario(
                name="geopolitical_crisis",
                description="重大地缘冲突爆发",
                shock_parameters={
                    'gold_return': 0.20,      # 金价+20%
                    'stocks_return': -0.25,   # 股市-25%
                    'oil_return': 0.50,       # 油价+50%
                    'vix_change': 2.5
                },
                probability=0.03
            ),
            StressScenario(
                name="inflation_surge",
                description="通胀失控",
                shock_parameters={
                    'gold_return': 0.15,      # 金价+15%
                    'stocks_return': -0.15,   # 股市-15%
                    'inflation_change': 0.05, # 通胀+5%
                    'bond_yield_change': 0.03
                },
                probability=0.04
            ),
            StressScenario(
                name="liquidity_crisis",
                description="流动性枯竭",
                shock_parameters={
                    'gold_return': -0.10,     # 金价-10% (被迫抛售)
                    'stocks_return': -0.35,   # 股市-35%
                    'credit_spread': 0.08,    # 信用利差+800bp
                    'volume_shock': -0.70     # 成交量-70%
                },
                probability=0.02
            ),
            StressScenario(
                name="china_slowdown",
                description="中国经济硬着陆",
                shock_parameters={
                    'gold_return': -0.08,     # 金价-8% (需求下降)
                    'copper_return': -0.30,   # 铜价-30%
                    'mining_stocks': -0.40,   # 矿业股-40%
                    'emfx_return': -0.20      # 新兴市场货币-20%
                },
                probability=0.03
            )
        ]
    
    def run_scenario_analysis(
        self,
        portfolio: Dict[str, float],
        current_prices: Dict[str, float],
        scenario: StressScenario
    ) -> Dict:
        """
        运行单个场景分析
        
        Args:
            portfolio: 组合持仓 {asset: quantity}
            current_prices: 当前价格 {asset: price}
            scenario: 压力场景
        
        Returns:
            场景分析结果
        """
        # 计算当前组合价值
        current_value = sum(
            portfolio.get(asset, 0) * current_prices.get(asset, 0)
            for asset in portfolio.keys()
        )
        
        # 应用冲击
        shocked_prices = {}
        for asset in portfolio.keys():
            current_price = current_prices.get(asset, 0)
            
            # 根据资产类型应用冲击
            if 'gold' in asset.lower() or asset.upper() in ['GLD', 'XAUUSD']:
                shock = scenario.shock_parameters.get('gold_return', 0)
            elif asset.upper() in ['SPY', 'QQQ', 'DIA']:  # 股票ETF
                shock = scenario.shock_parameters.get('stocks_return', 0)
            elif 'mining' in asset.lower() or asset.upper() in ['GDX', 'GDXJ']:
                shock = scenario.shock_parameters.get('mining_stocks', 
                        scenario.shock_parameters.get('stocks_return', 0) * 1.5)
            else:
                shock = scenario.shock_parameters.get('stocks_return', 0) * 0.8
            
            shocked_prices[asset] = current_price * (1 + shock)
        
        # 计算冲击后组合价值
        shocked_value = sum(
            portfolio.get(asset, 0) * shocked_prices.get(asset, 0)
            for asset in portfolio.keys()
        )
        
        # 计算损失
        loss = shocked_value - current_value
        loss_pct = loss / current_value if current_value > 0 else 0
        
        return {
            'scenario_name': scenario.name,
            'description': scenario.description,
            'current_value': current_value,
            'shocked_value': shocked_value,
            'loss': loss,
            'loss_pct': loss_pct,
            'probability': scenario.probability,
            'expected_loss': loss * scenario.probability,
            'shocked_prices': shocked_prices
        }
    
    def run_all_scenarios(
        self,
        portfolio: Dict[str, float],
        current_prices: Dict[str, float]
    ) -> pd.DataFrame:
        """
        运行所有压力场景
        
        Returns:
            场景分析汇总表
        """
        results = []
        
        for scenario in self.scenarios:
            result = self.run_scenario_analysis(portfolio, current_prices, scenario)
            results.append(result)
        
        df = pd.DataFrame(results)
        df = df.sort_values('loss_pct')
        
        return df
    
    @staticmethod
    def _calculate_max_drawdown(returns: pd.Series) -> float:
        """计算最大回撤"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def monte_carlo_stress_test(
        self,
        portfolio_returns: pd.Series,
        n_simulations: int = 10000,
        confidence_level: float = 0.99
    ) -> Dict:
        """
        蒙特卡洛压力测试
        
        模拟极端尾部事件
        
        Args:
            portfolio_returns: 历史收益率
            n_simulations: 模拟次数
            confidence_level: 置信水平
        
        Returns:
            蒙特卡洛压力测试结果
        """
        mu = portfolio_returns.mean()
        sigma = portfolio_returns.std()
        
        # 生成模拟收益率 (使用t分布,厚尾)
        np.random.seed(42)
        df = 5  # 自由度
        simulated_returns = stats.t.rvs(df, loc=mu, scale=sigma, size=n_simulations)
        
        # 极端损失分析
        worst_percentile = np.percentile(simulated_returns, (1 - confidence_level) * 100)
        extreme_losses = simulated_returns[simulated_returns <= worst_percentile]
        
        return {
            'worst_case': np.min(simulated_returns),
            f'{confidence_level*100:.0f}%_worst': worst_percentile,
            'expected_shortfall': np.mean(extreme_losses),
            'extreme_loss_probability': len(extreme_losses) / n_simulations,
            '99th_percentile_loss': worst_percentile
        }
    
    def get_worst_scenario(
        self,
        portfolio: Dict[str, float],
        current_prices: Dict[str, float]
    ) -> Dict:
        """
        找出对组合最不利的场景
        
        Returns:
            最坏场景及其影响
        """
        all_results = self.run_all_scenarios(portfolio, current_prices)
        worst = all_results.loc[all_results['loss_pct'].idxmin()]
        
        return {
            'worst_scenario': worst['scenario_name'],
            'description': worst['description'],
            'expected_loss': worst['loss'],
            'expected_loss_pct': worst['loss_pct'],
            'probability': worst['probability'],
            'risk_weighted_loss': worst['expected_loss']
        }
