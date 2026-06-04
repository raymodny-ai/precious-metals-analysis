"""
ETF Flow Alert System
ETF资金流预警系统
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from ..utils.logger import setup_logging
from ..utils.config import get_settings

logger = setup_logging("etf_alerts")
settings = get_settings()


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of ETF flow alerts"""
    LARGE_INFLOW = "large_inflow"
    LARGE_OUTFLOW = "large_outflow"
    UNUSUAL_VOLUME = "unusual_volume"
    FLOW_REVERSAL = "flow_reversal"
    HOLDER_CHANGE = "holder_change"
    CORRELATED_FLOW = "correlated_flow"
    TREND_BREAK = "trend_break"


@dataclass
class ETFAlert:
    """ETF flow alert"""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    symbol: str
    title: str
    description: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_read: bool = False


class ETFFlowAlertEngine:
    """
    ETF Fund Flow Alert Engine
    
    Monitors:
    - Large unusual inflows/outflows
    - Volume anomalies
    - Flow reversals
    - Holder changes (13F filings)
    - Correlated flows across ETFs
    - Trend breaks
    """
    
    # Default thresholds (can be customized)
    DEFAULT_THRESHOLDS = {
        "large_flow_zscore": 2.0,          # Z-score for large flow detection
        "volume_zscore": 2.5,               # Z-score for unusual volume
        "reversal_threshold": 0.5,          # Flow reversal threshold
        "correlation_threshold": 0.8,       # Cross-ETF correlation threshold  
        "trend_break_periods": 10,          # Periods for trend calculation
        "trend_break_threshold": 0.3,       # Deviation from trend
    }
    
    def __init__(self, thresholds: Optional[Dict] = None):
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.alerts: List[ETFAlert] = []
        self.alert_counter = 0
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        self.alert_counter += 1
        return f"ALERT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.alert_counter:04d}"
    
    def detect_large_flows(
        self,
        df: pd.DataFrame,
        lookback_days: int = 60
    ) -> List[ETFAlert]:
        """
        Detect unusually large fund flows
        
        Args:
            df: DataFrame with columns [time, symbol, net_flow]
            lookback_days: Historical period for baseline
        
        Returns:
            List of ETFAlert objects
        """
        alerts = []
        
        if df.empty or "net_flow" not in df.columns:
            return alerts
        
        for symbol in df["symbol"].unique():
            symbol_df = df[df["symbol"] == symbol].copy()
            symbol_df = symbol_df.sort_values("time")
            
            if len(symbol_df) < lookback_days:
                continue
            
            # Calculate z-score
            mean_flow = symbol_df["net_flow"].tail(lookback_days).mean()
            std_flow = symbol_df["net_flow"].tail(lookback_days).std()
            
            if std_flow == 0:
                continue
            
            latest_flow = symbol_df["net_flow"].iloc[-1]
            zscore = (latest_flow - mean_flow) / std_flow
            
            # Check for large flows
            if abs(zscore) > self.thresholds["large_flow_zscore"]:
                is_inflow = latest_flow > 0
                alert_type = AlertType.LARGE_INFLOW if is_inflow else AlertType.LARGE_OUTFLOW
                
                # Determine severity
                if abs(zscore) > 4:
                    severity = AlertSeverity.CRITICAL
                elif abs(zscore) > 3:
                    severity = AlertSeverity.HIGH
                else:
                    severity = AlertSeverity.MEDIUM
                
                alert = ETFAlert(
                    alert_id=self._generate_alert_id(),
                    alert_type=alert_type,
                    severity=severity,
                    symbol=symbol,
                    title=f"Large {'Inflow' if is_inflow else 'Outflow'} Detected - {symbol}",
                    description=f"{symbol} experienced a {abs(zscore):.1f}σ {'inflow' if is_inflow else 'outflow'} of ${abs(latest_flow)/1e6:.1f}M",
                    value=latest_flow,
                    threshold=mean_flow + self.thresholds["large_flow_zscore"] * std_flow,
                    metadata={
                        "zscore": zscore,
                        "mean_flow": mean_flow,
                        "std_flow": std_flow
                    }
                )
                alerts.append(alert)
        
        return alerts
    
    def detect_volume_anomaly(
        self,
        df: pd.DataFrame,
        lookback_days: int = 20
    ) -> List[ETFAlert]:
        """
        Detect unusual trading volume
        """
        alerts = []
        
        if df.empty or "volume" not in df.columns:
            return alerts
        
        for symbol in df["symbol"].unique():
            symbol_df = df[df["symbol"] == symbol].copy()
            symbol_df = symbol_df.sort_values("time")
            
            if len(symbol_df) < lookback_days:
                continue
            
            mean_volume = symbol_df["volume"].tail(lookback_days).mean()
            std_volume = symbol_df["volume"].tail(lookback_days).std()
            
            if std_volume == 0:
                continue
            
            latest_volume = symbol_df["volume"].iloc[-1]
            zscore = (latest_volume - mean_volume) / std_volume
            
            if zscore > self.thresholds["volume_zscore"]:
                severity = AlertSeverity.HIGH if zscore > 3.5 else AlertSeverity.MEDIUM
                
                alert = ETFAlert(
                    alert_id=self._generate_alert_id(),
                    alert_type=AlertType.UNUSUAL_VOLUME,
                    severity=severity,
                    symbol=symbol,
                    title=f"Unusual Volume - {symbol}",
                    description=f"{symbol} trading volume is {zscore:.1f}x normal ({latest_volume/1e6:.1f}M shares)",
                    value=latest_volume,
                    threshold=mean_volume + self.thresholds["volume_zscore"] * std_volume,
                    metadata={"zscore": zscore, "volume_ratio": latest_volume / mean_volume}
                )
                alerts.append(alert)
        
        return alerts
    
    def detect_flow_reversals(
        self,
        df: pd.DataFrame,
        lookback_days: int = 5
    ) -> List[ETFAlert]:
        """
        Detect sudden reversals in fund flow direction
        """
        alerts = []
        
        if df.empty or "net_flow" not in df.columns:
            return alerts
        
        for symbol in df["symbol"].unique():
            symbol_df = df[df["symbol"] == symbol].copy()
            symbol_df = symbol_df.sort_values("time")
            
            if len(symbol_df) < lookback_days + 1:
                continue
            
            # Recent flow sum
            recent_flow = symbol_df["net_flow"].tail(lookback_days).sum()
            # Previous period flow sum
            prev_flow = symbol_df["net_flow"].iloc[-(2*lookback_days):-lookback_days].sum()
            
            if abs(prev_flow) < 1e6:  # Ignore small flows
                continue
            
            # Check for reversal
            if prev_flow > 0 and recent_flow < -abs(prev_flow) * self.thresholds["reversal_threshold"]:
                alert = ETFAlert(
                    alert_id=self._generate_alert_id(),
                    alert_type=AlertType.FLOW_REVERSAL,
                    severity=AlertSeverity.HIGH,
                    symbol=symbol,
                    title=f"Flow Reversal - {symbol}",
                    description=f"{symbol} reversed from ${prev_flow/1e6:.1f}M inflows to ${recent_flow/1e6:.1f}M outflows",
                    value=recent_flow,
                    threshold=prev_flow,
                    metadata={"prev_flow": prev_flow, "reversal_ratio": recent_flow / prev_flow}
                )
                alerts.append(alert)
                
            elif prev_flow < 0 and recent_flow > abs(prev_flow) * self.thresholds["reversal_threshold"]:
                alert = ETFAlert(
                    alert_id=self._generate_alert_id(),
                    alert_type=AlertType.FLOW_REVERSAL,
                    severity=AlertSeverity.HIGH,
                    symbol=symbol,
                    title=f"Flow Reversal - {symbol}",
                    description=f"{symbol} reversed from ${abs(prev_flow)/1e6:.1f}M outflows to ${recent_flow/1e6:.1f}M inflows",
                    value=recent_flow,
                    threshold=prev_flow,
                    metadata={"prev_flow": prev_flow, "reversal_ratio": recent_flow / prev_flow}
                )
                alerts.append(alert)
        
        return alerts
    
    def detect_correlated_flows(
        self,
        df: pd.DataFrame,
        lookback_days: int = 20
    ) -> List[ETFAlert]:
        """
        Detect unusual simultaneous flows across multiple ETFs
        """
        alerts = []
        
        if df.empty or "net_flow" not in df.columns:
            return alerts
        
        # Pivot to get flows by symbol
        pivot = df.pivot_table(
            index="time", 
            columns="symbol", 
            values="net_flow", 
            aggfunc="sum"
        ).tail(lookback_days)
        
        if len(pivot.columns) < 2:
            return alerts
        
        # Calculate correlation
        corr_matrix = pivot.corr()
        
        # Check for high correlations
        symbols = list(pivot.columns)
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                corr = corr_matrix.loc[sym1, sym2]
                
                if abs(corr) > self.thresholds["correlation_threshold"]:
                    # Check if both have significant recent flows
                    recent_flow_1 = pivot[sym1].iloc[-5:].sum()
                    recent_flow_2 = pivot[sym2].iloc[-5:].sum()
                    
                    if abs(recent_flow_1) > 10e6 and abs(recent_flow_2) > 10e6:
                        direction = "same direction" if corr > 0 else "opposite direction"
                        
                        alert = ETFAlert(
                            alert_id=self._generate_alert_id(),
                            alert_type=AlertType.CORRELATED_FLOW,
                            severity=AlertSeverity.MEDIUM,
                            symbol=f"{sym1}/{sym2}",
                            title=f"Correlated Flows - {sym1} & {sym2}",
                            description=f"{sym1} and {sym2} showing {corr:.0%} correlation ({direction})",
                            value=corr,
                            threshold=self.thresholds["correlation_threshold"],
                            metadata={
                                "symbol1": sym1,
                                "symbol2": sym2,
                                "correlation": corr,
                                "flow1": recent_flow_1,
                                "flow2": recent_flow_2
                            }
                        )
                        alerts.append(alert)
        
        return alerts
    
    def run_all_detections(
        self,
        flow_df: pd.DataFrame,
        price_df: Optional[pd.DataFrame] = None
    ) -> List[ETFAlert]:
        """
        Run all detection algorithms
        
        Returns:
            Combined list of all detected alerts
        """
        all_alerts = []
        
        # Large flow detection
        all_alerts.extend(self.detect_large_flows(flow_df))
        
        # Volume anomaly (if price data available)
        if price_df is not None and not price_df.empty:
            all_alerts.extend(self.detect_volume_anomaly(price_df))
        
        # Flow reversals
        all_alerts.extend(self.detect_flow_reversals(flow_df))
        
        # Correlated flows
        all_alerts.extend(self.detect_correlated_flows(flow_df))
        
        # Store alerts
        self.alerts.extend(all_alerts)
        
        # Log summary
        logger.info(f"Detected {len(all_alerts)} alerts: "
                   f"{sum(1 for a in all_alerts if a.severity == AlertSeverity.CRITICAL)} critical, "
                   f"{sum(1 for a in all_alerts if a.severity == AlertSeverity.HIGH)} high, "
                   f"{sum(1 for a in all_alerts if a.severity == AlertSeverity.MEDIUM)} medium")
        
        return all_alerts
    
    def get_unread_alerts(self, severity: Optional[AlertSeverity] = None) -> List[ETFAlert]:
        """Get unread alerts, optionally filtered by severity"""
        alerts = [a for a in self.alerts if not a.is_read]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def mark_read(self, alert_id: str):
        """Mark an alert as read"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.is_read = True
                break
    
    def to_dict_list(self, alerts: Optional[List[ETFAlert]] = None) -> List[Dict]:
        """Convert alerts to list of dicts for API response"""
        if alerts is None:
            alerts = self.alerts
        
        return [
            {
                "alert_id": a.alert_id,
                "alert_type": a.alert_type.value,
                "severity": a.severity.value,
                "symbol": a.symbol,
                "title": a.title,
                "description": a.description,
                "value": a.value,
                "threshold": a.threshold,
                "timestamp": a.timestamp.isoformat(),
                "is_read": a.is_read,
                "metadata": a.metadata
            }
            for a in alerts
        ]


if __name__ == "__main__":
    # Test alert engine
    import numpy as np
    
    # Create sample flow data
    dates = pd.date_range(start="2024-01-01", periods=60, freq="D")
    
    data = []
    for symbol in ["GLD", "SLV", "IAU"]:
        base_flow = 10e6 if symbol == "GLD" else 5e6
        flows = np.random.normal(base_flow, 20e6, len(dates))
        
        # Add anomaly on last day
        flows[-1] = flows[-1] * 5
        
        for date, flow in zip(dates, flows):
            data.append({"time": date, "symbol": symbol, "net_flow": flow})
    
    df = pd.DataFrame(data)
    
    # Run detection
    engine = ETFFlowAlertEngine()
    alerts = engine.run_all_detections(df)
    
    print(f"\nDetected {len(alerts)} alerts:")
    for alert in alerts[:5]:
        print(f"  [{alert.severity.value.upper()}] {alert.title}")
        print(f"    {alert.description}")
