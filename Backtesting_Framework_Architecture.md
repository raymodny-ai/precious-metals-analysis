# 第二部分：回测框架完整架构设计文档

## 第一章：回测系统整体架构

### 1.1 系统设计原则

```
回测系统 5 大原则：

1️⃣ 真实性（Authenticity）
   ├─ 完整复现交易过程
   ├─ 包括滑点、佣金、税费
   └─ 处理流动性约束

2️⃣ 可靠性（Robustness）
   ├─ Walk-Forward Analysis 避免过拟合
   ├─ 蒙特卡洛模拟
   └─ Bootstrap 验证

3️⃣ 可重复性（Reproducibility）
   ├─ 种子固定
   ├─ 数据版本控制
   └─ 参数完整记录

4️⃣ 可扩展性（Scalability）
   ├─ 模块化设计
   ├─ 支持多资产
   └─ 易于添加新策略

5️⃣ 性能（Performance）
   ├─ 向量化计算
   ├─ 缓存优化
   └─ 并行处理
```

### 1.2 系统架构图

```
┌─────────────────────────────────────────────────────┐
│              回测系统完整架构                        │
└─────────────────────────────────────────────────────┘
        │
        ├─ 数据层
        │  ├─ DataLoader：加载历史数据
        │  ├─ FeatureEngineer：特征工程
        │  └─ DataValidator：数据质量检查
        │
        ├─ 模型层
        │  ├─ ModelPredictor：价格预测
        │  ├─ UncertaintyEstimator：不确定性量化
        │  └─ FeatureImportance：特征解释
        │
        ├─ 信号层
        │  ├─ SignalGenerator：交易信号生成
        │  ├─ RiskCalculator：风险计算
        │  └─ PositionSizer：头寸管理
        │
        ├─ 执行层
        │  ├─ OrderExecutor：订单执行
        │  ├─ SlippageSimulator：滑点模拟
        │  └─ CostCalculator：成本计算
        │
        ├─ 评估层
        │  ├─ MetricsCalculator：指标计算
        │  ├─ PerformanceAnalyzer：性能分析
        │  └─ DrawdownAnalyzer：回撤分析
        │
        └─ 验证层
           ├─ WalkForwardValidator：前向验证
           ├─ MonteCarloValidator：蒙特卡洛
           └─ BootstrapValidator：自助验证
```

---

## 第二章：详细模块实现

### 2.1 数据层

```python
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

class DataLoader:
    """历史数据加载和管理"""
    
    def __init__(self, data_source='local', cache_dir='./data_cache'):
        self.data_source = data_source
        self.cache_dir = cache_dir
        self.data = {}
    
    def load_gold_data(self, symbol='GLD', start_date='2020-01-01', end_date=None):
        """
        加载黄金价格数据
        
        返回格式：
        | date       | close | high | low | volume |
        |------------|-------|------|-----|--------|
        | 2020-01-01 | 160.0 | 161  | 159 | 2.5M   |
        """
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 从 yfinance/poly.io 加载
        import yfinance as yf
        df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        # 数据清洗
        df = df.dropna()
        df = df.drop_duplicates()
        df = df.sort_index()
        
        # 添加基础特征
        df['returns'] = df['Close'].pct_change()
        df['volume_ma'] = df['Volume'].rolling(20).mean()
        
        self.data[symbol] = df
        return df
    
    def validate_data(self, df, min_observations=100):
        """数据质量检查"""
        
        issues = []
        
        # 检查数据量
        if len(df) < min_observations:
            issues.append(f"数据量不足：{len(df)} < {min_observations}")
        
        # 检查缺失值
        missing_pct = df.isnull().sum() / len(df) * 100
        if (missing_pct > 0.1).any():
            issues.append(f"存在缺失值：{missing_pct}")
        
        # 检查异常值（价格变动 > 20%）
        returns = df['Close'].pct_change()
        extreme_returns = (returns.abs() > 0.2).sum()
        if extreme_returns > 0:
            issues.append(f"存在极端价格变动：{extreme_returns} 天")
        
        return len(issues) == 0, issues


class FeatureEngineer:
    """特征工程：生成所有需要的特征"""
    
    def __init__(self, df):
        self.df = df.copy()
    
    def engineer_features(self):
        """生成完整特征集"""
        
        # 1️⃣ 价格特征
        self.df['close_lag1'] = self.df['Close'].shift(1)
        self.df['close_lag5'] = self.df['Close'].shift(5)
        self.df['close_lag20'] = self.df['Close'].shift(20)
        
        # 2️⃣ 波动率特征
        self.df['volatility_5d'] = self.df['Close'].pct_change().rolling(5).std()
        self.df['volatility_20d'] = self.df['Close'].pct_change().rolling(20).std()
        
        # 3️⃣ 技术指标
        self.df['rsi_14'] = self._calculate_rsi(self.df['Close'], 14)
        self.df['macd'] = self._calculate_macd(self.df['Close'])
        self.df['bollinger_width'] = self._calculate_bollinger_width(self.df['Close'])
        
        # 4️⃣ 移动平均
        self.df['ma_5'] = self.df['Close'].rolling(5).mean()
        self.df['ma_20'] = self.df['Close'].rolling(20).mean()
        self.df['price_to_ma_ratio'] = self.df['Close'] / self.df['ma_20']
        
        # 5️⃣ 日期特征
        self.df['day_of_week'] = self.df.index.dayofweek
        self.df['month'] = self.df.index.month
        self.df['is_month_end'] = (self.df.index.day >= 25).astype(int)
        
        # 删除 NaN
        self.df = self.df.dropna()
        
        return self.df
    
    def _calculate_rsi(self, prices, period=14):
        """RSI 指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices):
        """MACD 指标"""
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        return ema_12 - ema_26
    
    def _calculate_bollinger_width(self, prices, period=20):
        """布林带宽度"""
        ma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = ma + 2 * std
        lower = ma - 2 * std
        return upper - lower
```

### 2.2 信号层

```python
class SignalGenerator:
    """生成交易信号"""
    
    def __init__(self, predictions, confidence, thresholds=None):
        """
        predictions：模型预测的价格
        confidence：预测置信度
        thresholds：信号阈值
        """
        self.predictions = predictions
        self.confidence = confidence
        self.thresholds = thresholds or {
            'buy_strength': 0.02,     # 预期上升 > 2%
            'sell_strength': -0.02,   # 预期下降 > 2%
            'buy_confidence': 0.7,    # 置信度 > 70%
            'sell_confidence': 0.7
        }
    
    def generate_signals(self, current_prices):
        """生成 BUY / SELL / HOLD 信号"""
        
        signals = []
        
        for i, (pred, conf, curr) in enumerate(zip(
            self.predictions, self.confidence, current_prices
        )):
            
            price_change = (pred - curr) / curr
            
            if price_change > self.thresholds['buy_strength'] and \
               conf > self.thresholds['buy_confidence']:
                signal = 'BUY'
                strength = 'STRONG' if conf > 0.8 else 'MODERATE'
            
            elif price_change < self.thresholds['sell_strength'] and \
                 conf > self.thresholds['sell_confidence']:
                signal = 'SELL'
                strength = 'STRONG' if conf > 0.8 else 'MODERATE'
            
            else:
                signal = 'HOLD'
                strength = None
            
            signals.append({
                'date': i,
                'signal': signal,
                'strength': strength,
                'predicted_price': pred,
                'confidence': conf,
                'expected_return': price_change
            })
        
        return pd.DataFrame(signals)


class PositionSizer:
    """头寸管理和风险控制"""
    
    def __init__(self, initial_capital=100000, max_risk_per_trade=0.02):
        """
        initial_capital：初始资本
        max_risk_per_trade：每笔交易最大风险 (2%)
        """
        self.initial_capital = initial_capital
        self.max_risk_per_trade = max_risk_per_trade
        self.current_capital = initial_capital
    
    def calculate_position_size(self, current_price, stop_loss_price, signal_strength):
        """
        计算头寸大小
        
        公式：头寸 = (资本 × 风险比例) / (入场价 - 止损价)
        """
        
        risk_amount = self.current_capital * self.max_risk_per_trade
        price_difference = abs(current_price - stop_loss_price)
        
        if price_difference == 0:
            position_size = 0
        else:
            position_size = risk_amount / price_distance
        
        # 根据信号强度调整
        if signal_strength == 'STRONG':
            position_multiplier = 1.0
        elif signal_strength == 'MODERATE':
            position_multiplier = 0.7
        else:
            position_multiplier = 0.0
        
        position_size *= position_multiplier
        
        return position_size
```

---

### 2.3 执行层

```python
class OrderExecutor:
    """订单执行和成本计算"""
    
    def __init__(self, slippage_bps=1.0, commission_bps=0.5):
        """
        slippage_bps：滑点 (0.01%)
        commission_bps：佣金 (0.005%)
        """
        self.slippage_bps = slippage_bps / 10000
        self.commission_bps = commission_bps / 10000
        self.execution_log = []
    
    def execute_order(self, order_type, quantity, price, date):
        """
        执行订单
        
        order_type: 'BUY' 或 'SELL'
        """
        
        # 计算滑点
        if order_type == 'BUY':
            execution_price = price * (1 + self.slippage_bps)
        else:  # SELL
            execution_price = price * (1 - self.slippage_bps)
        
        # 计算成本
        notional = quantity * execution_price
        commission = notional * self.commission_bps
        total_cost = notional + commission
        
        trade = {
            'date': date,
            'type': order_type,
            'quantity': quantity,
            'order_price': price,
            'execution_price': execution_price,
            'commission': commission,
            'total_cost': total_cost,
            'slippage': (execution_price - price) * quantity
        }
        
        self.execution_log.append(trade)
        return trade


class PortfolioManager:
    """投资组合管理"""
    
    def __init__(self, initial_capital=100000):
        self.cash = initial_capital
        self.positions = {}  # {symbol: quantity}
        self.trades = []
        self.equity_curve = [initial_capital]
    
    def add_position(self, symbol, quantity, entry_price):
        """添加头寸"""
        if symbol not in self.positions:
            self.positions[symbol] = 0
        
        self.positions[symbol] += quantity
        cost = quantity * entry_price
        self.cash -= cost
        
        self.trades.append({
            'type': 'BUY',
            'symbol': symbol,
            'quantity': quantity,
            'price': entry_price,
            'cost': cost
        })
    
    def close_position(self, symbol, quantity, exit_price):
        """平仓"""
        if symbol not in self.positions:
            return None
        
        actual_quantity = min(quantity, self.positions[symbol])
        proceeds = actual_quantity * exit_price
        self.cash += proceeds
        self.positions[symbol] -= actual_quantity
        
        if self.positions[symbol] == 0:
            del self.positions[symbol]
        
        self.trades.append({
            'type': 'SELL',
            'symbol': symbol,
            'quantity': actual_quantity,
            'price': exit_price,
            'proceeds': proceeds
        })
        
        return proceeds
    
    def get_total_equity(self, current_prices):
        """计算总权益"""
        position_value = sum(
            self.positions.get(symbol, 0) * current_prices.get(symbol, 0)
            for symbol in self.positions
        )
        return self.cash + position_value
```

---

### 2.4 评估层

```python
import scipy.stats as stats

class PerformanceMetrics:
    """计算交易性能指标"""
    
    def __init__(self, trades, equity_curve, returns, risk_free_rate=0.02):
        """
        trades：交易列表
        equity_curve：权益曲线
        returns：日度收益率
        """
        self.trades = trades
        self.equity_curve = np.array(equity_curve)
        self.returns = np.array(returns)
        self.risk_free_rate = risk_free_rate
    
    def calculate_all_metrics(self):
        """计算所有指标"""
        
        metrics = {}
        
        # 1️⃣ 收益指标
        metrics['total_return'] = (self.equity_curve[-1] - self.equity_curve[0]) / self.equity_curve[0]
        metrics['annual_return'] = (1 + metrics['total_return']) ** (252 / len(self.returns)) - 1
        
        # 2️⃣ 风险指标
        metrics['volatility'] = np.std(self.returns) * np.sqrt(252)
        metrics['sharpe_ratio'] = (metrics['annual_return'] - self.risk_free_rate) / metrics['volatility'] if metrics['volatility'] > 0 else 0
        
        # 3️⃣ 回撤指标
        cumulative = np.cumprod(1 + self.returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        
        metrics['max_drawdown'] = np.min(drawdown)
        metrics['avg_drawdown'] = np.mean(drawdown[drawdown < 0])
        
        # 4️⃣ 交易指标
        metrics['num_trades'] = len(self.trades)
        metrics['win_rate'] = self._calculate_win_rate()
        metrics['profit_factor'] = self._calculate_profit_factor()
        metrics['expectancy'] = self._calculate_expectancy()
        
        # 5️⃣ 调整后风险指标
        metrics['sortino_ratio'] = self._calculate_sortino_ratio()
        metrics['calmar_ratio'] = metrics['annual_return'] / abs(metrics['max_drawdown']) if metrics['max_drawdown'] != 0 else 0
        
        return metrics
    
    def _calculate_win_rate(self):
        """胜率"""
        if len(self.trades) == 0:
            return 0
        
        winning_trades = sum(1 for trade in self.trades if trade.get('pnl', 0) > 0)
        return winning_trades / len(self.trades)
    
    def _calculate_profit_factor(self):
        """利润因子（总收益 / 总亏损）"""
        
        gains = sum(max(0, trade.get('pnl', 0)) for trade in self.trades)
        losses = sum(max(0, -trade.get('pnl', 0)) for trade in self.trades)
        
        if losses == 0:
            return float('inf') if gains > 0 else 0
        return gains / losses
    
    def _calculate_expectancy(self):
        """期望收益"""
        if len(self.trades) == 0:
            return 0
        
        total_pnl = sum(trade.get('pnl', 0) for trade in self.trades)
        return total_pnl / len(self.trades)
    
    def _calculate_sortino_ratio(self):
        """Sortino 比率（仅考虑下行波动）"""
        
        downside_returns = self.returns[self.returns < 0]
        downside_volatility = np.std(downside_returns) * np.sqrt(252)
        
        if downside_volatility == 0:
            return 0
        
        annual_return = (1 + np.mean(self.returns)) ** 252 - 1
        return (annual_return - self.risk_free_rate) / downside_volatility


class DrawdownAnalyzer:
    """回撤分析"""
    
    def __init__(self, equity_curve):
        self.equity_curve = np.array(equity_curve)
    
    def calculate_drawdowns(self):
        """计算每个回撤期间"""
        
        cumulative = self.equity_curve / self.equity_curve[0]
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        
        # 识别回撤期间
        drawdown_periods = []
        in_drawdown = False
        start_idx = 0
        
        for i, dd in enumerate(drawdown):
            if dd < 0 and not in_drawdown:
                in_drawdown = True
                start_idx = i
            elif dd == 0 and in_drawdown:
                in_drawdown = False
                drawdown_periods.append({
                    'start': start_idx,
                    'end': i,
                    'duration': i - start_idx,
                    'max_dd': np.min(drawdown[start_idx:i+1])
                })
        
        return {
            'drawdown_curve': drawdown,
            'periods': drawdown_periods,
            'max_drawdown': np.min(drawdown),
            'avg_drawdown': np.mean(drawdown[drawdown < 0]),
            'num_drawdowns': len(drawdown_periods)
        }
```

---

## 第三章：Walk-Forward 验证框架

### 3.1 Walk-Forward 实现

```python
class WalkForwardValidator:
    """
    前向验证框架
    
    解决问题：防止过拟合
    方法：在时间窗口上滚动优化和测试
    """
    
    def __init__(self, data, train_size=252, test_size=63, step_size=63):
        """
        data：完整数据
        train_size：训练窗口（252 天 ≈ 1 年）
        test_size：测试窗口（63 天 ≈ 3 月）
        step_size：滚动步长（63 天 ≈ 3 月）
        """
        
        self.data = data
        self.train_size = train_size
        self.test_size = test_size
        self.step_size = step_size
        self.wfo_results = []
    
    def run_wfo(self, strategy_func, param_space):
        """
        运行 Walk-Forward 分析
        
        strategy_func：策略函数
        param_space：参数空间
        """
        
        total_length = len(self.data)
        test_index = 0
        wfo_cycle = 0
        
        print("🔄 开始 Walk-Forward Analysis...")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        while test_index + self.test_size <= total_length:
            
            train_start = max(0, test_index - self.train_size)
            train_end = test_index
            test_end = test_index + self.test_size
            
            train_data = self.data.iloc[train_start:train_end]
            test_data = self.data.iloc[test_index:test_end]
            
            print(f"\n📊 周期 {wfo_cycle + 1}:")
            print(f"   训练期：{train_data.index[0].date()} → {train_data.index[-1].date()}")
            print(f"   测试期：{test_data.index[0].date()} → {test_data.index[-1].date()}")
            
            # 步骤 1：在训练集上优化
            best_params = self._optimize_parameters(
                train_data, strategy_func, param_space
            )
            print(f"   最优参数：{best_params}")
            
            # 步骤 2：在测试集上评估（离样本）
            out_of_sample_results = strategy_func(
                test_data, best_params
            )
            print(f"   测试期收益：{out_of_sample_results['return']:.2%}")
            print(f"   测试期夏普比：{out_of_sample_results['sharpe']:.2f}")
            
            self.wfo_results.append({
                'cycle': wfo_cycle,
                'train_period': (train_data.index[0], train_data.index[-1]),
                'test_period': (test_data.index[0], test_data.index[-1]),
                'best_params': best_params,
                'out_of_sample': out_of_sample_results
            })
            
            test_index += self.step_size
            wfo_cycle += 1
        
        print(f"\n✅ 完成 {wfo_cycle} 个 Walk-Forward 周期")
        return self._aggregate_results()
    
    def _optimize_parameters(self, train_data, strategy_func, param_space):
        """在训练集上优化参数"""
        
        best_sharpe = float('-inf')
        best_params = None
        
        # 使用 Optuna 优化
        from optuna import create_study
        
        def objective(trial):
            params = {
                key: trial.suggest_int(key, *space) if isinstance(space, tuple)
                else trial.suggest_float(key, *space)
                for key, space in param_space.items()
            }
            
            result = strategy_func(train_data, params)
            return -result['sharpe']  # 最大化夏普比
        
        study = create_study(direction='minimize')
        study.optimize(objective, n_trials=50, show_progress_bar=False)
        
        return study.best_params
    
    def _aggregate_results(self):
        """聚合所有周期的结果"""
        
        all_returns = []
        all_sharpes = []
        all_drawdowns = []
        
        for result in self.wfo_results:
            oos = result['out_of_sample']
            all_returns.append(oos['return'])
            all_sharpes.append(oos['sharpe'])
            all_drawdowns.append(oos['max_drawdown'])
        
        return {
            'avg_return': np.mean(all_returns),
            'std_return': np.std(all_returns),
            'avg_sharpe': np.mean(all_sharpes),
            'avg_max_dd': np.mean(all_drawdowns),
            'cycle_results': self.wfo_results
        }
```

### 3.2 蒙特卡洛模拟

```python
class MonteCarloValidator:
    """蒙特卡洛模拟验证策略稳健性"""
    
    def __init__(self, returns, num_simulations=1000):
        self.returns = np.array(returns)
        self.num_simulations = num_simulations
    
    def run_simulation(self):
        """运行蒙特卡洛模拟"""
        
        n_days = len(self.returns)
        simulated_returns = np.zeros((self.num_simulations, n_days))
        simulated_equity = np.zeros((self.num_simulations, n_days))
        
        print(f"🎲 运行 {self.num_simulations} 次蒙特卡洛模拟...")
        
        for sim in range(self.num_simulations):
            # 随机重采样收益
            sampled_indices = np.random.choice(
                len(self.returns), size=n_days, replace=True
            )
            simulated_returns[sim] = self.returns[sampled_indices]
            
            # 计算权益曲线
            simulated_equity[sim] = np.cumprod(1 + simulated_returns[sim])
        
        return {
            'simulated_equity': simulated_equity,
            'final_equity_distribution': simulated_equity[:, -1],
            'percentile_5': np.percentile(simulated_equity[:, -1], 5),
            'percentile_50': np.percentile(simulated_equity[:, -1], 50),
            'percentile_95': np.percentile(simulated_equity[:, -1], 95),
            'var_95': np.percentile(simulated_returns.sum(axis=1), 5),
            'cvar_95': np.mean(simulated_returns.sum(axis=1)[
                simulated_returns.sum(axis=1) <= np.percentile(simulated_returns.sum(axis=1), 5)
            ])
        }
```

### 3.3 Bootstrap 验证

```python
class BootstrapValidator:
    """Bootstrap 验证统计显著性"""
    
    def __init__(self, returns, num_bootstrap=1000):
        self.returns = np.array(returns)
        self.num_bootstrap = num_bootstrap
    
    def run_bootstrap(self):
        """运行 Bootstrap"""
        
        bootstrap_means = []
        bootstrap_medians = []
        
        for _ in range(self.num_bootstrap):
            sample = np.random.choice(
                self.returns, size=len(self.returns), replace=True
            )
            bootstrap_means.append(np.mean(sample))
            bootstrap_medians.append(np.median(sample))
        
        # 计算置信区间
        ci_5 = np.percentile(bootstrap_means, 5)
        ci_95 = np.percentile(bootstrap_means, 95)
        
        # Wilcoxon 检验（是否显著不同于 0）
        from scipy.stats import wilcoxon
        statistic, pvalue = wilcoxon(self.returns)
        
        return {
            'bootstrap_means': bootstrap_means,
            'mean_ci_5': ci_5,
            'mean_ci_95': ci_95,
            'mean': np.mean(bootstrap_means),
            'wilcoxon_pvalue': pvalue,
            'is_significant': pvalue < 0.05
        }
```

---

## 第四章：完整回测脚本

```python
class FullBacktestingSystem:
    """完整回测系统集成"""
    
    def __init__(self, symbol='GLD', initial_capital=100000):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.data = None
        self.model = None
        self.results = {}
    
    def run_full_backtest(self, start_date='2020-01-01', end_date=None):
        """运行完整回测"""
        
        print("═" * 50)
        print("🚀 启动完整回测系统")
        print("═" * 50)
        
        # 步骤 1：加载数据
        print("\n[1/6] 加载历史数据...")
        loader = DataLoader()
        self.data = loader.load_gold_data(self.symbol, start_date, end_date)
        
        # 步骤 2：特征工程
        print("[2/6] 特征工程...")
        engineer = FeatureEngineer(self.data)
        self.data = engineer.engineer_features()
        
        # 步骤 3：模型训练（使用最优参数）
        print("[3/6] 训练预测模型...")
        # 这里使用前面优化的参数
        ensemble = EnsembleGoldPredictor()
        predictions, uncertainty = ensemble.predict_with_explanation(
            self.data.drop('Close', axis=1).values
        )
        
        # 步骤 4：生成信号
        print("[4/6] 生成交易信号...")
        signals = SignalGenerator(predictions, uncertainty).generate_signals(
            self.data['Close'].values
        )
        
        # 步骤 5：执行回测
        print("[5/6] 执行回测...")
        self.results = self._execute_trades(signals)
        
        # 步骤 6：性能评估
        print("[6/6] 计算性能指标...")
        self._calculate_performance()
        
        print("\n✅ 回测完成！")
        self._print_summary()
        
        return self.results
    
    def _execute_trades(self, signals):
        """执行交易"""
        
        executor = OrderExecutor()
        portfolio = PortfolioManager(self.initial_capital)
        
        trades = []
        equity_curve = [self.initial_capital]
        
        for i, signal in signals.iterrows():
            
            if signal['signal'] == 'BUY':
                # 计算头寸大小
                position_size = int(self.initial_capital / self.data['Close'].iloc[i])
                trade = executor.execute_order('BUY', position_size, 
                                              self.data['Close'].iloc[i], i)
                portfolio.add_position(self.symbol, position_size, 
                                      self.data['Close'].iloc[i])
                trades.append(trade)
            
            elif signal['signal'] == 'SELL':
                # 平仓
                if self.symbol in portfolio.positions:
                    quantity = portfolio.positions[self.symbol]
                    portfolio.close_position(self.symbol, quantity, 
                                            self.data['Close'].iloc[i])
            
            # 记录权益
            equity = portfolio.get_total_equity({self.symbol: self.data['Close'].iloc[i]})
            equity_curve.append(equity)
        
        return {
            'trades': trades,
            'equity_curve': equity_curve,
            'executor_log': executor.execution_log
        }
    
    def _calculate_performance(self):
        """计算性能指标"""
        
        equity = np.array(self.results['equity_curve'])
        returns = np.diff(equity) / equity[:-1]
        
        metrics = PerformanceMetrics(
            self.results['trades'],
            equity,
            returns
        ).calculate_all_metrics()
        
        self.results['metrics'] = metrics
    
    def _print_summary(self):
        """打印回测摘要"""
        
        m = self.results['metrics']
        
        print("\n" + "═" * 50)
        print("📊 回测结果摘要")
        print("═" * 50)
        print(f"总收益率：{m['total_return']:.2%}")
        print(f"年化收益：{m['annual_return']:.2%}")
        print(f"波动率：{m['volatility']:.2%}")
        print(f"夏普比：{m['sharpe_ratio']:.2f}")
        print(f"最大回撤：{m['max_drawdown']:.2%}")
        print(f"Calmar 比：{m['calmar_ratio']:.2f}")
        print(f"交易数：{m['num_trades']}")
        print(f"胜率：{m['win_rate']:.2%}")
        print(f"利润因子：{m['profit_factor']:.2f}")
        print("═" * 50)
```

---

## 参考资源

1. Walk-Forward[234]：https://blog.quantinsti.com/walk-forward-optimization-introduction/
2. 实现[240]：https://www.youtube.com/watch?v=9m987swadQU
3. 蒙特卡洛和 Bootstrap：https://en.wikipedia.org/wiki/Bootstrap_aggregating