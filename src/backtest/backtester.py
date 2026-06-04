"""
Backtesting Framework
回测框架
Based on Backtesting_Framework_Architecture.md
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

from ..utils.logger import setup_logging

logger = setup_logging("backtest")


# ============================================================================
# Data Types and Enums
# ============================================================================

class OrderSide(Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"


class PositionType(Enum):
    """Position type"""
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass
class Order:
    """Trade order"""
    order_id: str
    timestamp: datetime
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    order_type: str = "market"
    filled: bool = False
    fill_price: Optional[float] = None
    fill_timestamp: Optional[datetime] = None
    commission: float = 0.0


@dataclass
class Position:
    """Current position"""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    position_type: PositionType = PositionType.FLAT
    
    def update_price(self, price: float):
        """Update current price and PnL"""
        self.current_price = price
        self.unrealized_pnl = (price - self.avg_price) * self.quantity


@dataclass
class Trade:
    """Completed trade"""
    trade_id: str
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    return_pct: float
    holding_period: int  # bars
    commission: float = 0.0


@dataclass
class Portfolio:
    """Portfolio state"""
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    equity: float = 0.0
    
    def update_equity(self):
        """Update total equity"""
        position_value = sum(
            pos.quantity * pos.current_price 
            for pos in self.positions.values()
        )
        self.equity = self.cash + position_value


@dataclass 
class Signal:
    """Trading signal"""
    timestamp: datetime
    symbol: str
    direction: int  # 1 = long, -1 = short, 0 = flat
    strength: float  # 0 to 1
    confidence: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Data Handler
# ============================================================================

class DataHandler:
    """
    Data handler for backtesting
    
    Responsibilities:
    - Load price and feature data
    - Align multiple data sources
    - Provide data iteration interface
    """
    
    def __init__(
        self,
        price_data: pd.DataFrame,
        feature_data: Optional[pd.DataFrame] = None,
        sentiment_data: Optional[pd.DataFrame] = None,
        etf_flow_data: Optional[pd.DataFrame] = None
    ):
        self.price_data = price_data.copy()
        self.feature_data = feature_data.copy() if feature_data is not None else None
        self.sentiment_data = sentiment_data.copy() if sentiment_data is not None else None
        self.etf_flow_data = etf_flow_data.copy() if etf_flow_data is not None else None
        
        # Ensure time index
        self._prepare_data()
        
        # Current position
        self.current_idx = 0
        self.dates = self.price_data.index.tolist()
    
    def _prepare_data(self):
        """Prepare and align data"""
        # Ensure datetime index
        if "time" in self.price_data.columns:
            self.price_data["time"] = pd.to_datetime(self.price_data["time"])
            self.price_data = self.price_data.set_index("time")
        
        self.price_data = self.price_data.sort_index()
        
        # Align other data sources
        for data in [self.feature_data, self.sentiment_data, self.etf_flow_data]:
            if data is not None and "time" in data.columns:
                data["time"] = pd.to_datetime(data["time"])
                data = data.set_index("time").sort_index()
    
    def reset(self):
        """Reset to beginning"""
        self.current_idx = 0
    
    def has_next(self) -> bool:
        """Check if more data available"""
        return self.current_idx < len(self.dates)
    
    def get_current_bar(self) -> Dict:
        """Get current price bar"""
        if not self.has_next():
            return None
        
        date = self.dates[self.current_idx]
        row = self.price_data.loc[date]
        
        return {
            "time": date,
            "open": row.get("open", row.get("close")),
            "high": row.get("high", row.get("close")),
            "low": row.get("low", row.get("close")),
            "close": row["close"],
            "volume": row.get("volume", 0)
        }
    
    def get_historical_bars(self, lookback: int) -> pd.DataFrame:
        """Get historical bars up to current position"""
        start_idx = max(0, self.current_idx - lookback)
        dates = self.dates[start_idx:self.current_idx + 1]
        return self.price_data.loc[dates]
    
    def get_current_features(self) -> Optional[Dict]:
        """Get features for current bar"""
        if self.feature_data is None:
            return None
        
        date = self.dates[self.current_idx]
        if date in self.feature_data.index:
            return self.feature_data.loc[date].to_dict()
        return None
    
    def get_current_sentiment(self) -> Optional[Dict]:
        """Get sentiment for current bar"""
        if self.sentiment_data is None:
            return None
        
        date = self.dates[self.current_idx]
        if date in self.sentiment_data.index:
            return self.sentiment_data.loc[date].to_dict()
        return None
    
    def advance(self):
        """Move to next bar"""
        self.current_idx += 1


# ============================================================================
# Signal Generator
# ============================================================================

class SignalGenerator(ABC):
    """Abstract base class for signal generators"""
    
    @abstractmethod
    def generate_signal(
        self,
        data_handler: DataHandler,
        portfolio: Portfolio
    ) -> Optional[Signal]:
        """Generate trading signal based on current data"""
        pass


class MLSignalGenerator(SignalGenerator):
    """
    ML-based signal generator
    
    Uses trained models to generate trading signals
    """
    
    def __init__(
        self,
        model,
        feature_engineer,
        threshold_long: float = 0.6,
        threshold_short: float = 0.4
    ):
        self.model = model
        self.feature_engineer = feature_engineer
        self.threshold_long = threshold_long
        self.threshold_short = threshold_short
    
    def generate_signal(
        self,
        data_handler: DataHandler,
        portfolio: Portfolio
    ) -> Optional[Signal]:
        """Generate signal from model prediction"""
        
        # Get historical data for features
        hist = data_handler.get_historical_bars(50)
        if len(hist) < 30:
            return None
        
        # Generate features
        features = self.feature_engineer.engineer_all_features(hist.reset_index())
        
        if features.empty:
            return None
        
        # Get last row features
        X = features.drop(columns=["time", "symbol", "date"], errors="ignore")
        X = X.iloc[-1:].values
        
        # Predict
        try:
            prediction = self.model.predict(X)[0]
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return None
        
        bar = data_handler.get_current_bar()
        
        # Generate signal based on prediction
        if prediction > self.threshold_long:
            direction = 1
            strength = min(1.0, prediction)
        elif prediction < self.threshold_short:
            direction = -1
            strength = min(1.0, 1 - prediction)
        else:
            direction = 0
            strength = 0.5
        
        return Signal(
            timestamp=bar["time"],
            symbol=hist.iloc[0].get("symbol", "UNKNOWN"),
            direction=direction,
            strength=strength,
            confidence=abs(prediction - 0.5) * 2,
            source="ml_model"
        )


class SentimentSignalGenerator(SignalGenerator):
    """Sentiment-based signal generator"""
    
    def __init__(
        self,
        bullish_threshold: float = 0.3,
        bearish_threshold: float = -0.3
    ):
        self.bullish_threshold = bullish_threshold
        self.bearish_threshold = bearish_threshold
    
    def generate_signal(
        self,
        data_handler: DataHandler,
        portfolio: Portfolio
    ) -> Optional[Signal]:
        """Generate signal from sentiment data"""
        
        sentiment = data_handler.get_current_sentiment()
        if sentiment is None:
            return None
        
        bar = data_handler.get_current_bar()
        score = sentiment.get("sentiment_score", 0)
        
        if score > self.bullish_threshold:
            direction = 1
        elif score < self.bearish_threshold:
            direction = -1
        else:
            direction = 0
        
        return Signal(
            timestamp=bar["time"],
            symbol=sentiment.get("symbol", "UNKNOWN"),
            direction=direction,
            strength=abs(score),
            confidence=sentiment.get("confidence", 0.5),
            source="sentiment"
        )


# ============================================================================
# Execution Engine
# ============================================================================

class ExecutionEngine:
    """
    Order execution engine
    
    Handles:
    - Order placement
    - Fill simulation (with slippage)
    - Position tracking
    - Commission calculation
    """
    
    def __init__(
        self,
        slippage_pct: float = 0.001,
        commission_pct: float = 0.001,
        max_position_pct: float = 0.2
    ):
        self.slippage_pct = slippage_pct
        self.commission_pct = commission_pct
        self.max_position_pct = max_position_pct
        
        self.order_counter = 0
        self.trade_counter = 0
        
        self.pending_orders: List[Order] = []
        self.filled_orders: List[Order] = []
        self.trades: List[Trade] = []
        self.entry_prices: Dict[str, Tuple[datetime, float]] = {}  # symbol -> (time, price)
    
    def _generate_order_id(self) -> str:
        self.order_counter += 1
        return f"ORD_{self.order_counter:06d}"
    
    def _generate_trade_id(self) -> str:
        self.trade_counter += 1
        return f"TRD_{self.trade_counter:06d}"
    
    def place_order(
        self,
        portfolio: Portfolio,
        bar: Dict,
        signal: Signal
    ) -> Optional[Order]:
        """Place order based on signal"""
        
        symbol = signal.symbol
        direction = signal.direction
        
        current_position = portfolio.positions.get(symbol)
        current_qty = current_position.quantity if current_position else 0
        
        # Calculate target position
        max_position_value = portfolio.equity * self.max_position_pct
        max_qty = max_position_value / bar["close"]
        
        if direction == 1:  # Long
            if current_qty >= 0:
                # Open or add to long
                target_qty = max_qty * signal.strength
                order_qty = min(target_qty - current_qty, target_qty)
                if order_qty <= 0:
                    return None
                side = OrderSide.BUY
            else:
                # Close short
                order_qty = abs(current_qty)
                side = OrderSide.BUY
                
        elif direction == -1:  # Short
            if current_qty <= 0:
                # Open or add to short
                target_qty = max_qty * signal.strength
                order_qty = min(target_qty + current_qty, target_qty)
                if order_qty <= 0:
                    return None
                side = OrderSide.SELL
            else:
                # Close long
                order_qty = current_qty
                side = OrderSide.SELL
                
        else:  # Flat - close any position
            if current_qty == 0:
                return None
            order_qty = abs(current_qty)
            side = OrderSide.SELL if current_qty > 0 else OrderSide.BUY
        
        order = Order(
            order_id=self._generate_order_id(),
            timestamp=bar["time"],
            symbol=symbol,
            side=side,
            quantity=order_qty,
            price=bar["close"]
        )
        
        self.pending_orders.append(order)
        return order
    
    def execute_orders(
        self,
        portfolio: Portfolio,
        bar: Dict
    ):
        """Execute pending orders"""
        
        for order in self.pending_orders:
            if order.filled:
                continue
            
            # Calculate fill price with slippage
            slippage = order.price * self.slippage_pct
            if order.side == OrderSide.BUY:
                fill_price = order.price + slippage
            else:
                fill_price = order.price - slippage
            
            # Calculate commission
            commission = order.quantity * fill_price * self.commission_pct
            
            # Check if we can afford it
            cost = order.quantity * fill_price + commission
            if order.side == OrderSide.BUY and cost > portfolio.cash:
                logger.warning(f"Insufficient cash for order {order.order_id}")
                continue
            
            # Execute
            order.filled = True
            order.fill_price = fill_price
            order.fill_timestamp = bar["time"]
            order.commission = commission
            
            # Update portfolio
            self._update_portfolio(portfolio, order, bar)
            
            self.filled_orders.append(order)
        
        # Clear pending
        self.pending_orders = [o for o in self.pending_orders if not o.filled]
    
    def _update_portfolio(
        self,
        portfolio: Portfolio,
        order: Order,
        bar: Dict
    ):
        """Update portfolio after order fill"""
        
        symbol = order.symbol
        
        if order.side == OrderSide.BUY:
            cost = order.quantity * order.fill_price + order.commission
            portfolio.cash -= cost
            
            if symbol in portfolio.positions:
                pos = portfolio.positions[symbol]
                # Update average price
                total_qty = pos.quantity + order.quantity
                pos.avg_price = (pos.avg_price * pos.quantity + order.fill_price * order.quantity) / total_qty
                pos.quantity = total_qty
            else:
                portfolio.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=order.quantity,
                    avg_price=order.fill_price,
                    current_price=bar["close"],
                    position_type=PositionType.LONG
                )
                self.entry_prices[symbol] = (bar["time"], order.fill_price)
                
        else:  # SELL
            if symbol in portfolio.positions:
                pos = portfolio.positions[symbol]
                sell_qty = min(order.quantity, pos.quantity)
                
                # Calculate PnL
                pnl = (order.fill_price - pos.avg_price) * sell_qty - order.commission
                portfolio.cash += sell_qty * order.fill_price - order.commission
                
                # Record trade
                if symbol in self.entry_prices:
                    entry_time, entry_price = self.entry_prices[symbol]
                    holding_bars = (bar["time"] - entry_time).days
                    
                    trade = Trade(
                        trade_id=self._generate_trade_id(),
                        entry_time=entry_time,
                        exit_time=bar["time"],
                        symbol=symbol,
                        side="long",
                        entry_price=entry_price,
                        exit_price=order.fill_price,
                        quantity=sell_qty,
                        pnl=pnl,
                        return_pct=(order.fill_price / entry_price - 1) * 100,
                        holding_period=holding_bars,
                        commission=order.commission
                    )
                    self.trades.append(trade)
                
                # Update position
                pos.quantity -= sell_qty
                if pos.quantity <= 0:
                    del portfolio.positions[symbol]
                    if symbol in self.entry_prices:
                        del self.entry_prices[symbol]


# ============================================================================
# Performance Evaluator
# ============================================================================

@dataclass
class PerformanceMetrics:
    """Performance metrics"""
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    avg_trade_pnl: float
    total_trades: int
    avg_holding_period: float
    volatility: float
    calmar_ratio: float
    sortino_ratio: float


class PerformanceEvaluator:
    """
    Calculate performance metrics
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
    
    def calculate_metrics(
        self,
        equity_curve: pd.Series,
        trades: List[Trade],
        initial_capital: float
    ) -> PerformanceMetrics:
        """Calculate all performance metrics"""
        
        # Returns
        returns = equity_curve.pct_change().dropna()
        
        # Total return
        total_return = (equity_curve.iloc[-1] / initial_capital - 1) * 100
        
        # Annualized return
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        annual_return = (1 + total_return / 100) ** (365 / max(days, 1)) - 1
        annual_return *= 100
        
        # Volatility
        volatility = returns.std() * np.sqrt(252) * 100
        
        # Sharpe ratio
        excess_returns = returns - self.risk_free_rate / 252
        sharpe_ratio = np.sqrt(252) * excess_returns.mean() / (returns.std() + 1e-10)
        
        # Max drawdown
        cummax = equity_curve.cummax()
        drawdown = (equity_curve - cummax) / cummax
        max_drawdown = abs(drawdown.min()) * 100
        
        # Trade statistics
        if trades:
            winning_trades = [t for t in trades if t.pnl > 0]
            losing_trades = [t for t in trades if t.pnl <= 0]
            
            win_rate = len(winning_trades) / len(trades) * 100
            
            total_profit = sum(t.pnl for t in winning_trades)
            total_loss = abs(sum(t.pnl for t in losing_trades))
            profit_factor = total_profit / (total_loss + 1e-10)
            
            avg_trade_pnl = np.mean([t.pnl for t in trades])
            avg_holding_period = np.mean([t.holding_period for t in trades])
        else:
            win_rate = 0
            profit_factor = 0
            avg_trade_pnl = 0
            avg_holding_period = 0
        
        # Calmar ratio
        calmar_ratio = annual_return / (max_drawdown + 1e-10)
        
        # Sortino ratio
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino_ratio = (annual_return / 100 - self.risk_free_rate) / (downside_std + 1e-10)
        
        return PerformanceMetrics(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_trade_pnl=avg_trade_pnl,
            total_trades=len(trades),
            avg_holding_period=avg_holding_period,
            volatility=volatility,
            calmar_ratio=calmar_ratio,
            sortino_ratio=sortino_ratio
        )
    
    def generate_report(
        self,
        metrics: PerformanceMetrics,
        equity_curve: pd.Series,
        trades: List[Trade]
    ) -> Dict:
        """Generate comprehensive performance report"""
        
        report = {
            "summary": {
                "total_return": f"{metrics.total_return:.2f}%",
                "annual_return": f"{metrics.annual_return:.2f}%",
                "sharpe_ratio": f"{metrics.sharpe_ratio:.2f}",
                "max_drawdown": f"{metrics.max_drawdown:.2f}%",
                "win_rate": f"{metrics.win_rate:.1f}%",
                "total_trades": metrics.total_trades
            },
            "risk_metrics": {
                "volatility": f"{metrics.volatility:.2f}%",
                "calmar_ratio": f"{metrics.calmar_ratio:.2f}",
                "sortino_ratio": f"{metrics.sortino_ratio:.2f}",
                "profit_factor": f"{metrics.profit_factor:.2f}"
            },
            "trade_stats": {
                "avg_pnl": f"${metrics.avg_trade_pnl:.2f}",
                "avg_holding_period": f"{metrics.avg_holding_period:.1f} days"
            },
            "equity_curve": {
                "start": equity_curve.iloc[0],
                "end": equity_curve.iloc[-1],
                "peak": equity_curve.max(),
                "trough": equity_curve.min()
            }
        }
        
        return report


# ============================================================================
# Main Backtester
# ============================================================================

class Backtester:
    """
    Main backtesting engine
    
    Orchestrates:
    - Data handling
    - Signal generation
    - Order execution
    - Performance evaluation
    """
    
    def __init__(
        self,
        data_handler: DataHandler,
        signal_generator: SignalGenerator,
        initial_capital: float = 100000,
        slippage_pct: float = 0.001,
        commission_pct: float = 0.001
    ):
        self.data_handler = data_handler
        self.signal_generator = signal_generator
        
        self.portfolio = Portfolio(cash=initial_capital, equity=initial_capital)
        self.initial_capital = initial_capital
        
        self.execution = ExecutionEngine(slippage_pct, commission_pct)
        self.evaluator = PerformanceEvaluator()
        
        # Results
        self.equity_history = []
        self.signals_history = []
    
    def run(self, progress_callback: Optional[Callable] = None) -> Dict:
        """Run backtest"""
        
        logger.info("Starting backtest...")
        
        self.data_handler.reset()
        total_bars = len(self.data_handler.dates)
        
        while self.data_handler.has_next():
            bar = self.data_handler.get_current_bar()
            
            # Update positions with current prices
            for pos in self.portfolio.positions.values():
                pos.update_price(bar["close"])
            
            self.portfolio.update_equity()
            
            # Record equity
            self.equity_history.append({
                "time": bar["time"],
                "equity": self.portfolio.equity,
                "cash": self.portfolio.cash
            })
            
            # Execute pending orders
            self.execution.execute_orders(self.portfolio, bar)
            
            # Generate signals
            signal = self.signal_generator.generate_signal(
                self.data_handler,
                self.portfolio
            )
            
            if signal:
                self.signals_history.append(signal)
                
                # Place order
                order = self.execution.place_order(self.portfolio, bar, signal)
                if order:
                    logger.debug(f"Order placed: {order.side.value} {order.quantity:.2f} @ {order.price:.2f}")
            
            # Progress callback
            if progress_callback:
                progress = self.data_handler.current_idx / total_bars
                progress_callback(progress)
            
            self.data_handler.advance()
        
        # Final results
        return self._generate_results()
    
    def _generate_results(self) -> Dict:
        """Generate backtest results"""
        
        equity_df = pd.DataFrame(self.equity_history)
        equity_df = equity_df.set_index("time")
        
        equity_curve = equity_df["equity"]
        
        # Calculate metrics
        metrics = self.evaluator.calculate_metrics(
            equity_curve,
            self.execution.trades,
            self.initial_capital
        )
        
        # Generate report
        report = self.evaluator.generate_report(
            metrics,
            equity_curve,
            self.execution.trades
        )
        
        logger.info(f"Backtest complete. Total return: {metrics.total_return:.2f}%")
        
        return {
            "metrics": metrics,
            "report": report,
            "equity_curve": equity_df,
            "trades": self.execution.trades,
            "signals": self.signals_history
        }


if __name__ == "__main__":
    # Test backtest framework
    import yfinance as yf
    
    # Get sample data
    ticker = yf.Ticker("GLD")
    df = ticker.history(period="2y")
    df = df.reset_index()
    df.columns = df.columns.str.lower()
    df = df.rename(columns={"date": "time"})
    
    # Create data handler
    data_handler = DataHandler(df)
    
    # Simple signal generator
    class SimpleMASignal(SignalGenerator):
        def generate_signal(self, dh, portfolio):
            hist = dh.get_historical_bars(50)
            if len(hist) < 50:
                return None
            
            ma20 = hist["close"].tail(20).mean()
            ma50 = hist["close"].mean()
            current = hist["close"].iloc[-1]
            
            bar = dh.get_current_bar()
            
            if ma20 > ma50:
                direction = 1
            elif ma20 < ma50:
                direction = -1
            else:
                direction = 0
            
            return Signal(
                timestamp=bar["time"],
                symbol="GLD",
                direction=direction,
                strength=0.5,
                confidence=0.6,
                source="ma_crossover"
            )
    
    # Run backtest
    signal_gen = SimpleMASignal()
    backtester = Backtester(data_handler, signal_gen, initial_capital=100000)
    
    results = backtester.run()
    
    print("\nBacktest Results:")
    print(f"  Total Return: {results['metrics'].total_return:.2f}%")
    print(f"  Sharpe Ratio: {results['metrics'].sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {results['metrics'].max_drawdown:.2f}%")
    print(f"  Win Rate: {results['metrics'].win_rate:.1f}%")
    print(f"  Total Trades: {results['metrics'].total_trades}")
