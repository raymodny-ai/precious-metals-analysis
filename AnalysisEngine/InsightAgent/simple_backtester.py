# AnalysisEngine/InsightAgent/simple_backtester.py

"""
简化回测引擎

提供基本的回测功能,支持:
- 策略回测
- 性能指标计算
- 可视化分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Callable
from datetime import datetime

class SimpleBacktester:
    """简化回测引擎"""
    
    def __init__(
        self,
        initial_capital: float = 100000,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        
        self.reset()
    
    def reset(self):
        """重置回测状态"""
        self.cash = self.initial_capital
        self.positions = {}  # {symbol: quantity}
        self.equity_curve = []
        self.trades = []
        self.current_date = None
    
    def run_backtest(
        self,
        data: pd.DataFrame,
        signal_generator: Callable,
        rebalance_frequency: str = 'daily'
    ) -> Dict:
        """
        运行回测
        
        Args:
            data: 价格数据 (MultiIndex: date, symbol 或 DatetimeIndex)
            signal_generator: 信号生成函数 (data -> signal)
            rebalance_frequency: 再平衡频率 ('daily', 'weekly', 'monthly')
        
        Returns:
            回测结果字典
        """
        self.reset()
        
        # 确定日期列表
        if isinstance(data.index, pd.MultiIndex):
            dates = data.index.get_level_values(0).unique()
        else:
            dates = data.index.unique()
        
        for date in dates:
            self.current_date = date
            
            # 获取当日数据
            if isinstance(data.index, pd.MultiIndex):
                day_data = data.loc[date]
            else:
                day_data = data.loc[[date]]
            
            # 生成信号
            try:
                signal = signal_generator(day_data)
                
                # 执行交易
                if hasattr(signal, 'signal_type'):
                    self._execute_signal(signal, day_data)
                elif isinstance(signal, dict):
                    for sym, sig in signal.items():
                        self._execute_signal(sig, day_data)
            except Exception as e:
                print(f"Error on {date}: {e}")
                continue
            
            # 记录权益
            self._record_equity(day_data)
        
        return self._generate_report()
    
    def _execute_signal(self, signal, data):
        """执行交易信号"""
        symbol = signal.symbol
        signal_type = signal.signal_type.value if hasattr(signal.signal_type, 'value') else signal.signal_type
        
        # 获取当前价格
        if 'close' in data.columns:
            if symbol in data.index:
                price = data.loc[symbol, 'close']
            else:
                price = data['close'].iloc[-1]
        else:
            price = data.iloc[-1]['close'] if len(data) == 1 else data['close'].mean()
        
        # 应用滑点
        if 'buy' in signal_type:
            execution_price = price * (1 + self.slippage_rate)
        else:
            execution_price = price * (1 - self.slippage_rate)
        
        current_position = self.positions.get(symbol, 0)
        
        # 买入信号
        if 'buy' in signal_type and current_position == 0:
            # 使用50%现金买入
            position_value = self.cash * 0.5
            quantity = int(position_value / execution_price)
            
            if quantity > 0:
                cost = quantity * execution_price
                commission = cost * self.commission_rate
                total_cost = cost + commission
                
                if total_cost <= self.cash:
                    self.cash -= total_cost
                    self.positions[symbol] = quantity
                    
                    self.trades.append({
                        'date': self.current_date,
                        'symbol': symbol,
                        'action': 'BUY',
                        'quantity': quantity,
                        'price': execution_price,
                        'cost': total_cost
                    })
        
        # 卖出信号
        elif 'sell' in signal_type and current_position > 0:
            proceeds = current_position * execution_price
            commission = proceeds * self.commission_rate
            net_proceeds = proceeds - commission
            
            self.cash += net_proceeds
            self.positions[symbol] = 0
            
            self.trades.append({
                'date': self.current_date,
                'symbol': symbol,
                'action': 'SELL',
                'quantity': current_position,
                'price': execution_price,
                'proceeds': net_proceeds
            })
    
    def _record_equity(self, data):
        """记录权益曲线"""
        # 计算持仓市值
        holdings_value = 0
        for symbol, quantity in self.positions.items():
            if quantity > 0:
                if symbol in data.index and 'close' in data.columns:
                    price = data.loc[symbol, 'close']
                elif 'close' in data.columns:
                    price = data['close'].iloc[-1]
                else:
                    price = 0
                holdings_value += quantity * price
        
        total_equity = self.cash + holdings_value
        
        self.equity_curve.append({
            'date': self.current_date,
            'cash': self.cash,
            'holdings': holdings_value,
            'total': total_equity
        })
    
    def _generate_report(self) -> Dict:
        """生成回测报告"""
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df = equity_df.set_index('date')
        
        # 计算收益率
        equity_df['returns'] = equity_df['total'].pct_change()
        
        # 统计指标
        total_return = (equity_df['total'].iloc[-1] / self.initial_capital) - 1
        n_days = len(equity_df)
        annual_return = (1 + total_return) ** (252 / n_days) - 1 if n_days > 0 else 0
        
        # Sharpe比率
        returns_std = equity_df['returns'].std()
        sharpe_ratio = equity_df['returns'].mean() / returns_std * np.sqrt(252) if returns_std > 0 else 0
        
        # 最大回撤
        cumulative = equity_df['total']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 交易统计
        win_trades = 0
        total_trades_count = 0
        
        buy_trades = [t for t in self.trades if t['action'] == 'BUY']
        sell_trades = [t for t in self.trades if t['action'] == 'SELL']
        
        for buy, sell in zip(buy_trades, sell_trades):
            if sell['proceeds'] > buy['cost']:
                win_trades += 1
            total_trades_count += 1
        
        win_rate = win_trades / total_trades_count if total_trades_count > 0 else 0
        
        return {
            'summary': {
                'initial_capital': self.initial_capital,
                'final_equity': equity_df['total'].iloc[-1],
                'total_return': total_return,
                'annual_return': annual_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'total_trades': total_trades_count,
                'win_rate': win_rate
            },
            'equity_curve': equity_df,
            'trades': self.trades
        }
    
    def get_performance_metrics(self) -> pd.Series:
        """获取性能指标摘要"""
        report = self._generate_report()
        return pd.Series(report['summary'])
