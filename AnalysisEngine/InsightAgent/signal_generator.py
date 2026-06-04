# AnalysisEngine/InsightAgent/signal_generator.py

"""
多策略交易信号生成系统

支持:
- 趋势跟踪策略 (Trend Following)
- 均值回归策略 (Mean Reversion)
- 突破策略 (Breakout)
- 多策略融合
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class SignalType(Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"

@dataclass
class TradingSignal:
    """交易信号"""
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    strength: float  # 0-1之间
    price: float
    strategy_name: str
    reasoning: str
    metadata: Dict = None

class TrendFollowingStrategy:
    """趋势跟踪策略 - 双均线+ATR止损"""
    
    def __init__(self, fast_period: int = 10, slow_period: int = 30, atr_period: int = 14):
        self.name = "Trend Following"
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.atr_period = atr_period
        self.weight = 1.0
    
    def generate_signal(self, data: pd.DataFrame, current_position: float = 0) -> TradingSignal:
        """基于双均线+ATR止损的趋势跟踪"""
        close = data['close']
        high = data['high']
        low = data['low']
        
        # 计算双均线
        ma_fast = close.rolling(self.fast_period).mean()
        ma_slow = close.rolling(self.slow_period).mean()
        
        # 计算ATR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()
        
        # 最新值
        current_price = close.iloc[-1]
        current_ma_fast = ma_fast.iloc[-1]
        current_ma_slow = ma_slow.iloc[-1]
        current_atr = atr.iloc[-1]
        
        # 信号生成
        if current_ma_fast > current_ma_slow and current_position <= 0:
            signal_type = SignalType.BUY
            strength = min((current_ma_fast - current_ma_slow) / current_ma_slow * 10, 1.0)
            reasoning = f"Golden cross: Fast MA ({current_ma_fast:.2f}) > Slow MA ({current_ma_slow:.2f})"
        elif current_ma_fast < current_ma_slow and current_position >= 0:
            signal_type = SignalType.SELL
            strength = min((current_ma_slow - current_ma_fast) / current_ma_slow * 10, 1.0)
            reasoning = f"Death cross: Fast MA ({current_ma_fast:.2f}) < Slow MA ({current_ma_slow:.2f})"
        else:
            signal_type = SignalType.HOLD
            strength = 0.0
            reasoning = "No clear trend signal"
        
        return TradingSignal(
            timestamp=data.index[-1],
            symbol=data.get('symbol', ['Unknown'])[0] if 'symbol' in data.columns else 'Unknown',
            signal_type=signal_type,
            strength=strength,
            price=current_price,
            strategy_name=self.name,
            reasoning=reasoning,
            metadata={
                'ma_fast': current_ma_fast,
                'ma_slow': current_ma_slow,
                'atr': current_atr,
                'stop_loss': current_price - 2 * current_atr,
                'take_profit': current_price + 4 * current_atr
            }
        )

class MeanReversionStrategy:
    """均值回归策略 - 布林带+RSI"""
    
    def __init__(self, bb_period: int = 20, bb_std: float = 2.0, rsi_period: int = 14):
        self.name = "Mean Reversion"
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.weight = 1.0
    
    def generate_signal(self, data: pd.DataFrame, current_position: float = 0) -> TradingSignal:
        """基于布林带+RSI的均值回归"""
        close = data['close']
        
        # 布林带
        bb_middle = close.rolling(self.bb_period).mean()
        bb_std_val = close.rolling(self.bb_period).std()
        bb_upper = bb_middle + (bb_std_val * self.bb_std)
        bb_lower = bb_middle - (bb_std_val * self.bb_std)
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(self.rsi_period).mean()
        loss = -delta.where(delta < 0, 0).rolling(self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 最新值
        current_price = close.iloc[-1]
        current_bb_upper = bb_upper.iloc[-1]
        current_bb_lower = bb_lower.iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # 信号生成
        if current_price < current_bb_lower and current_rsi < 30:
            signal_type = SignalType.BUY
            strength = min((current_bb_lower - current_price) / current_bb_lower * 5 + (30 - current_rsi) / 30, 1.0)
            reasoning = f"Oversold: Price below lower BB, RSI={current_rsi:.1f}"
        elif current_price > current_bb_upper and current_rsi > 70:
            signal_type = SignalType.SELL
            strength = min((current_price - current_bb_upper) / current_bb_upper * 5 + (current_rsi - 70) / 30, 1.0)
            reasoning = f"Overbought: Price above upper BB, RSI={current_rsi:.1f}"
        else:
            signal_type = SignalType.HOLD
            strength = 0.0
            reasoning = "Price within normal range"
        
        return TradingSignal(
            timestamp=data.index[-1],
            symbol=data.get('symbol', ['Unknown'])[0] if 'symbol' in data.columns else 'Unknown',
            signal_type=signal_type,
            strength=strength,
            price=current_price,
            strategy_name=self.name,
            reasoning=reasoning,
            metadata={'bb_upper': current_bb_upper, 'bb_lower': current_bb_lower, 'rsi': current_rsi}
        )

class MultiStrategySignalGenerator:
    """多策略信号融合器"""
    
    def __init__(self, strategies: List):
        self.strategies = strategies
        self.signal_history = []
    
    def generate_consensus_signal(
        self,
        data: pd.DataFrame,
        current_position: float = 0
    ) -> Tuple[TradingSignal, List[TradingSignal]]:
        """生成共识信号"""
        # 收集所有策略信号
        all_signals = []
        for strategy in self.strategies:
            signal = strategy.generate_signal(data, current_position)
            all_signals.append(signal)
        
        # 加权投票
        score_map = {
            SignalType.STRONG_SELL: -2,
            SignalType.SELL: -1,
            SignalType.HOLD: 0,
            SignalType.BUY: 1,
            SignalType.STRONG_BUY: 2
        }
        
        total_score = sum(signal.strength * score_map[signal.signal_type] * strategy.weight 
                         for signal, strategy in zip(all_signals, self.strategies))
        total_weight = sum(strategy.weight for strategy in self.strategies)
        consensus_score = total_score / total_weight if total_weight > 0 else 0
        
        # 确定共识信号类型
        if consensus_score >= 1.5:
            consensus_type = SignalType.STRONG_BUY
        elif consensus_score >= 0.5:
            consensus_type = SignalType.BUY
        elif consensus_score <= -1.5:
            consensus_type = SignalType.STRONG_SELL
        elif consensus_score <= -0.5:
            consensus_type = SignalType.SELL
        else:
            consensus_type = SignalType.HOLD
        
        consensus_strength = min(abs(consensus_score) / 2, 1.0)
        
        # 生成理由
        active_signals = [s for s in all_signals if s.signal_type != SignalType.HOLD]
        if active_signals:
            reasoning = f"Consensus from {len(active_signals)} strategies: " + \
                       "; ".join([f"{s.strategy_name} ({s.signal_type.value})" for s in active_signals])
        else:
            reasoning = "No clear signals from any strategy"
        
        consensus_signal = TradingSignal(
            timestamp=data.index[-1],
            symbol=data.get('symbol', ['Unknown'])[0] if 'symbol' in data.columns else 'Unknown',
            signal_type=consensus_type,
            strength=consensus_strength,
            price=data['close'].iloc[-1],
            strategy_name="Consensus",
            reasoning=reasoning,
            metadata={
                'consensus_score': consensus_score,
                'individual_signals': [
                    {'strategy': s.strategy_name, 'type': s.signal_type.value, 'strength': s.strength}
                    for s in all_signals
                ]
            }
        )
        
        self.signal_history.append({
            'timestamp': consensus_signal.timestamp,
            'consensus_signal': consensus_signal,
            'individual_signals': all_signals
        })
        
        return consensus_signal, all_signals
