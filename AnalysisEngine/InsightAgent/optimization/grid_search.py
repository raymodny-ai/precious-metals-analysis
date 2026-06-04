# AnalysisEngine/InsightAgent/optimization/grid_search.py

"""
参数优化 - 网格搜索

用于策略参数优化
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Any
from itertools import product
import multiprocessing as mp

class GridSearchOptimizer:
    """网格搜索参数优化器"""
    
    def __init__(self, backtest_func: Callable, metric: str = 'sharpe_ratio'):
        """
        Args:
            backtest_func: 回测函数,签名: func(data, **params) -> results_dict
            metric: 优化目标指标
        """
        self.backtest_func = backtest_func
        self.metric = metric
        self.results = []
    
    def optimize(
        self,
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        n_jobs: int = 1
    ) -> Dict:
        """
        网格搜索优化
        
        Args:
            data: 回测数据
            param_grid: 参数网格 {'param_name': [values]}
            n_jobs: 并行任务数 (1=串行)
        
        Returns:
            优化结果
        """
        # 生成所有参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(product(*param_values))
        
        print(f"Testing {len(param_combinations)} parameter combinations...")
        
        # 顺序执行 (避免并行复杂度)
        results = []
        for i, combination in enumerate(param_combinations):
            params = dict(zip(param_names, combination))
            
            try:
                # 运行回测
                backtest_result = self.backtest_func(data, **params)
                
                # 提取目标指标
                metric_value = backtest_result['summary'][self.metric]
                
                results.append({
                    'params': params,
                    'metric_value': metric_value,
                    'full_result': backtest_result
                })
                
                if (i + 1) % 10 == 0:
                    print(f"Progress: {i + 1}/{len(param_combinations)}")
            
            except Exception as e:
                print(f"Error with params {params}: {e}")
                continue
        
        self.results = results
        
        # 找出最优参数
        if results:
            best = max(results, key=lambda x: x['metric_value'])
            worst = min(results, key=lambda x: x['metric_value'])
            
            return {
                'best_params': best['params'],
                'best_metric': best['metric_value'],
                'worst_params': worst['params'],
                'worst_metric': worst['metric_value'],
                'n_combinations': len(results),
                'all_results': results
            }
        else:
            return {'error': 'No valid results'}
    
    def get_results_dataframe(self) -> pd.DataFrame:
        """
        获取结果DataFrame
        
        Returns:
            结果表格
        """
        if not self.results:
            return pd.DataFrame()
        
        rows = []
        for result in self.results:
            row = result['params'].copy()
            row[self.metric] = result['metric_value']
            
            # 添加其他指标
            summary = result['full_result']['summary']
            row['total_return'] = summary.get('total_return', 0)
            row['max_drawdown'] = summary.get('max_drawdown', 0)
            row['total_trades'] = summary.get('total_trades', 0)
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df = df.sort_values(self.metric, ascending=False)
        return df
    
    def plot_heatmap(self, param1: str, param2: str):
        """
        绘制2D参数热图
        
        Args:
            param1: 第一个参数名
            param2: 第二个参数名
        """
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
        except ImportError:
            print("matplotlib/seaborn not installed")
            return
        
        df = self.get_results_dataframe()
        
        pivot = df.pivot_table(
            index=param1,
            columns=param2,
            values=self.metric
        )
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(pivot, annot=True, fmt='.3f', cmap='RdYlGn')
        plt.title(f'{self.metric} Heatmap')
        plt.tight_layout()
        plt.show()


class SimpleParameterOptimizer:
    """简化版参数优化器"""
    
    @staticmethod
    def optimize_ma_crossover(
        data: pd.DataFrame,
        fast_range: range = range(5, 21, 5),
        slow_range: range = range(20, 61, 10)
    ) -> Dict:
        """
        优化均线交叉参数
        
        Returns:
            最优参数
        """
        from ..simple_backtester import SimpleBacktester
        from ..signal_generator import TrendFollowingStrategy
        
        best_sharpe = -np.inf
        best_params = None
        
        results = []
        
        for fast in fast_range:
            for slow in slow_range:
                if fast >= slow:
                    continue
                
                try:
                    # 创建策略
                    strategy = TrendFollowingStrategy(fast_period=fast, slow_period=slow)
                    
                    # 回测
                    backtester = SimpleBacktester(initial_capital=100000)
                    result = backtester.run_backtest(
                        data,
                        lambda d: strategy.generate_signal(d, 0)
                    )
                    
                    sharpe = result['summary']['sharpe_ratio']
                    
                    results.append({
                        'fast': fast,
                        'slow': slow,
                        'sharpe': sharpe,
                        'return': result['summary']['total_return'],
                        'max_dd': result['summary']['max_drawdown']
                    })
                    
                    if sharpe > best_sharpe:
                        best_sharpe = sharpe
                        best_params = {'fast': fast, 'slow': slow}
                
                except Exception as e:
                    print(f"Error with fast={fast}, slow={slow}: {e}")
                    continue
        
        return {
            'best_params': best_params,
            'best_sharpe': best_sharpe,
            'all_results': pd.DataFrame(results).sort_values('sharpe', ascending=False)
        }
