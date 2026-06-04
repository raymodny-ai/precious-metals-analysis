# API参考文档

PreciousInsight API完整参考

---

## 目录

1. [技术指标API](#技术指标api)
2. [因子引擎API](#因子引擎api)
3. [风险管理API](#风险管理api)
4. [信号生成API](#信号生成api)
5. [ML预测API](#ml预测api)
6. [回测引擎API](#回测引擎api)
7. [LLM服务API](#llm服务api)

---

## 技术指标API

### 趋势指标

#### `TrendIndicators.moving_average()`

计算移动平均线

**参数**:
- `data` (pd.Series): 价格序列
- `period` (int): 周期,默认20
- `ma_type` (str): 类型 'SMA'/'EMA'/'WMA'/'DEMA'

**返回**: pd.Series

**示例**:
```python
sma = TrendIndicators.moving_average(close, 20, 'SMA')
ema = TrendIndicators.moving_average(close, 20, 'EMA')
```

#### `TrendIndicators.macd()`

计算MACD指标

**参数**:
- `data` (pd.Series): 价格序列
- `fast_period` (int): 快线周期,默认12
- `slow_period` (int): 慢线周期,默认26
- `signal_period` (int): 信号线周期,默认9

**返回**: Tuple[pd.Series, pd.Series, pd.Series]
- macd_line: MACD线
- signal_line: 信号线
- histogram: MACD柱

**示例**:
```python
macd, signal, hist = TrendIndicators.macd(close)
```

---

## 因子引擎API

### FactorEngine

多因子计算引擎

#### `__init__()`

初始化因子引擎,加载25+预定义因子

#### `calculate_all_factors()`

计算所有因子

**参数**:
- `price_data` (pd.DataFrame): OHLCV数据
- `fundamental_data` (pd.DataFrame, optional): 基本面数据
- `market_data` (pd.DataFrame, optional): 市场数据(含金价)

**返回**: pd.DataFrame (行=时间,列=因子)

**示例**:
```python
engine = FactorEngine()
factors = engine.calculate_all_factors(
    price_data=ohlcv_df,
    market_data=market_df
)
```

#### `normalize_factors()`

因子标准化

**参数**:
- `factor_df` (pd.DataFrame): 原始因子矩阵
- `method` (str): 'z_score'/'min_max'/'rank'

**返回**: pd.DataFrame

#### `calculate_composite_score()`

计算综合评分

**参数**:
- `factor_df` (pd.DataFrame): 标准化后因子
- `factor_weights` (Dict, optional): 因子权重

**返回**: pd.Series

---

## 风险管理API

### VaRCalculator

风险价值计算器

#### `__init__(confidence_level=0.95)`

**参数**:
- `confidence_level` (float): 置信水平,默认0.95

#### `historical_var()`

历史模拟法VaR

**参数**:
- `returns` (pd.Series): 收益率序列
- `confidence_level` (float, optional): 置信水平

**返回**: VaRResult
- `var_value` (float): VaR值
- `cvar_value` (float): CVaR值
- `confidence_level` (float): 置信水平
- `method` (str): 方法名

**示例**:
```python
var_calc = VaRCalculator(confidence_level=0.95)
result = var_calc.historical_var(returns)
print(f"VaR: {result.var_value:.2%}")
print(f"CVaR: {result.cvar_value:.2%}")
```

---

## 信号生成API

### TrendFollowingStrategy

趋势跟踪策略

#### `__init__(fast_period=10, slow_period=30)`

**参数**:
- `fast_period` (int): 快线周期
- `slow_period` (int): 慢线周期

#### `generate_signal()`

生成交易信号

**参数**:
- `data` (pd.DataFrame): OHLCV数据
- `current_position` (float): 当前仓位 (-1到1)

**返回**: TradingSignal
- `signal_type` (SignalType): BUY/SELL/HOLD
- `strength` (float): 信号强度 0-1
- `price` (float): 当前价格
- `reasoning` (str): 信号理由
- `metadata` (dict): 元数据(止损/止盈等)

**示例**:
```python
strategy = TrendFollowingStrategy(fast_period=10, slow_period=30)
signal = strategy.generate_signal(data)
print(f"{signal.signal_type.value}: {signal.reasoning}")
```

---

## ML预测API

### XGBoostPredictor

XGBoost方向预测模型

#### `__init__(n_estimators=100, max_depth=5)`

**参数**:
- `n_estimators` (int): 树的数量
- `max_depth` (int): 树的最大深度
- `learning_rate` (float): 学习率

#### `train()`

训练模型

**参数**:
- `data` (pd.DataFrame): OHLCV数据
- `test_size` (float): 测试集比例,默认0.2
- `forecast_horizon` (int): 预测期限(天),默认1

**返回**: Dict
- `train_accuracy` (float): 训练集准确率
- `test_accuracy` (float): 测试集准确率
- `feature_importance` (pd.Series): 特征重要性

**示例**:
```python
predictor = XGBoostPredictor(n_estimators=100)
results = predictor.train(data, test_size=0.2)
print(f"准确率: {results['test_accuracy']:.1%}")
```

#### `predict()`

预测方向

**返回**: int (1=上涨, 0=下跌)

#### `predict_proba()`

预测概率

**返回**: float (上涨概率 0-1)

---

## 回测引擎API

### SimpleBacktester

简化回测引擎

#### `__init__(initial_capital=100000)`

**参数**:
- `initial_capital` (float): 初始资金
- `commission_rate` (float): 手续费率
- `slippage_rate` (float): 滑点率

#### `run_backtest()`

运行回测

**参数**:
- `data` (pd.DataFrame): 价格数据
- `signal_generator` (Callable): 信号生成函数

**返回**: Dict
```python
{
    'summary': {
        'total_return': float,
        'annual_return': float,
        'sharpe_ratio': float,
        'max_drawdown': float,
        'total_trades': int,
        'win_rate': float
    },
    'equity_curve': pd.DataFrame,
    'trades': List[dict]
}
```

**示例**:
```python
backtester = SimpleBacktester(initial_capital=100000)

def signal_func(data):
    strategy = TrendFollowingStrategy()
    return strategy.generate_signal(data, 0)

results = backtester.run_backtest(data, signal_func)
print(f"总收益: {results['summary']['total_return']:.1%}")
print(f"Sharpe: {results['summary']['sharpe_ratio']:.2f}")
```

---

## LLM服务API

### LLMService

统一LLM服务接口

#### `complete()`

LLM补全

**参数**:
- `request` (LLMRequest):
  - `task_type` (TaskType): 任务类型
  - `prompt` (str): 提示词
  - `system_prompt` (str, optional): 系统提示
  - `max_tokens` (int): 最大token数

**返回**: LLMResponse
- `content` (str): 生成内容
- `model` (str): 使用的模型
- `tokens_used` (int): 消耗token
- `cost` (float): 成本
- `latency` (float): 延迟(秒)

**示例**:
```python
from AnalysisEngine.LLMService.llm_service import get_llm_service
from AnalysisEngine.LLMService.base import LLMRequest, TaskType

llm = get_llm_service()
request = LLMRequest(
    task_type=TaskType.ANALYSIS,
    prompt="分析当前黄金市场走势"
)
response = llm.complete(request)
print(response.content)
```

---

## 错误处理

所有API在出错时抛出相应异常:

```python
try:
    result = var_calc.historical_var(returns)
except ValueError as e:
    print(f"参数错误: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

---

## 数据格式

### OHLCV DataFrame

```python
pd.DataFrame({
    'open': float,
    'high': float,
    'low': float,
    'close': float,
    'volume': int
}, index=pd.DatetimeIndex)
```

### 因子DataFrame

```python
pd.DataFrame({
    'return_1m': float,
    'return_3m': float,
    'rsi': float,
    # ... 其他因子
}, index=pd.DatetimeIndex)
```

---

更多API详情请查看源代码文档字符串。
