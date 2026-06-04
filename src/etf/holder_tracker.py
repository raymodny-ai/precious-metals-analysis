"""
ETF Holder Tracking Module
持仓人变动追踪模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

from ..utils.logger import setup_logging
from ..utils.config import get_settings

logger = setup_logging("holder_tracker")
settings = get_settings()


@dataclass
class HolderChange:
    """Record of holder change"""
    holder_name: str
    symbol: str
    change_date: datetime
    prev_shares: float
    new_shares: float
    change_shares: float
    change_pct: float
    prev_value: float
    new_value: float
    holder_type: str  # 'institution', 'hedge_fund', 'etf', 'mutual_fund'
    significance: str  # 'major', 'moderate', 'minor'


@dataclass
class HolderSnapshot:
    """Snapshot of all holders at a point in time"""
    symbol: str
    date: datetime
    total_institutional_shares: float
    total_institutional_pct: float
    num_holders: int
    top_holders: List[Dict[str, Any]]
    concentration: float  # Top 10 holders percentage


class HolderTracker:
    """
    Track changes in ETF institutional holdings
    
    Features:
    - 13F filing analysis
    - Holder change detection
    - Concentration tracking
    - Smart money flow analysis
    """
    
    # Notable institutional holders to track
    NOTABLE_HOLDERS = [
        "BlackRock",
        "Vanguard",
        "State Street",
        "Fidelity",
        "JPMorgan",
        "Goldman Sachs",
        "Morgan Stanley",
        "Bank of America",
        "Bridgewater",
        "Ray Dalio",
        "Citadel",
        "Renaissance",
        "Two Sigma",
        "AQR",
        "D.E. Shaw",
        "Soros Fund",
        "Berkshire Hathaway"
    ]
    
    def __init__(self):
        self.holder_history: Dict[str, List[HolderSnapshot]] = {}
        self.changes: List[HolderChange] = []
    
    def add_snapshot(
        self,
        symbol: str,
        holders_data: List[Dict],
        date: Optional[datetime] = None
    ):
        """
        Add a holder snapshot
        
        Args:
            symbol: ETF symbol
            holders_data: List of holder dictionaries with keys:
                - name, shares, value, pct_held, holder_type
            date: Snapshot date (default: now)
        """
        if date is None:
            date = datetime.now()
        
        if symbol not in self.holder_history:
            self.holder_history[symbol] = []
        
        # Sort by shares
        holders_data = sorted(holders_data, key=lambda x: x.get("shares", 0), reverse=True)
        
        # Calculate totals
        total_shares = sum(h.get("shares", 0) for h in holders_data)
        total_institutional_pct = sum(h.get("pct_held", 0) for h in holders_data)
        
        # Top 10 concentration
        top_10_shares = sum(h.get("shares", 0) for h in holders_data[:10])
        concentration = top_10_shares / (total_shares + 1e-10) * 100
        
        # Create snapshot
        snapshot = HolderSnapshot(
            symbol=symbol,
            date=date,
            total_institutional_shares=total_shares,
            total_institutional_pct=total_institutional_pct,
            num_holders=len(holders_data),
            top_holders=holders_data[:20],
            concentration=concentration
        )
        
        # Detect changes from previous snapshot
        if self.holder_history[symbol]:
            prev_snapshot = self.holder_history[symbol][-1]
            self._detect_changes(prev_snapshot, snapshot, holders_data)
        
        self.holder_history[symbol].append(snapshot)
        
        logger.info(f"Added holder snapshot for {symbol}: {len(holders_data)} holders")
    
    def _detect_changes(
        self,
        prev: HolderSnapshot,
        curr: HolderSnapshot,
        holders_data: List[Dict]
    ):
        """Detect significant holder changes"""
        
        # Build lookup of previous holders
        prev_holders = {h["name"]: h for h in prev.top_holders}
        
        for holder in holders_data:
            name = holder.get("name", "")
            shares = holder.get("shares", 0)
            value = holder.get("value", 0)
            holder_type = holder.get("holder_type", "institution")
            
            if name in prev_holders:
                prev_shares = prev_holders[name].get("shares", 0)
                prev_value = prev_holders[name].get("value", 0)
                
                if prev_shares > 0:
                    change_shares = shares - prev_shares
                    change_pct = (shares / prev_shares - 1) * 100
                    
                    # Determine significance
                    if abs(change_pct) > 50:
                        significance = "major"
                    elif abs(change_pct) > 20:
                        significance = "moderate"
                    elif abs(change_pct) > 5:
                        significance = "minor"
                    else:
                        continue  # Skip small changes
                    
                    change = HolderChange(
                        holder_name=name,
                        symbol=curr.symbol,
                        change_date=curr.date,
                        prev_shares=prev_shares,
                        new_shares=shares,
                        change_shares=change_shares,
                        change_pct=change_pct,
                        prev_value=prev_value,
                        new_value=value,
                        holder_type=holder_type,
                        significance=significance
                    )
                    
                    self.changes.append(change)
                    
                    if significance in ["major", "moderate"]:
                        action = "increased" if change_shares > 0 else "decreased"
                        logger.info(f"{name} {action} {curr.symbol} by {abs(change_pct):.1f}%")
            else:
                # New holder
                if shares > 0 and self._is_notable_holder(name):
                    change = HolderChange(
                        holder_name=name,
                        symbol=curr.symbol,
                        change_date=curr.date,
                        prev_shares=0,
                        new_shares=shares,
                        change_shares=shares,
                        change_pct=100,
                        prev_value=0,
                        new_value=value,
                        holder_type=holder_type,
                        significance="major"
                    )
                    self.changes.append(change)
                    logger.info(f"New notable holder: {name} initiated position in {curr.symbol}")
    
    def _is_notable_holder(self, name: str) -> bool:
        """Check if holder is notable"""
        name_lower = name.lower()
        return any(notable.lower() in name_lower for notable in self.NOTABLE_HOLDERS)
    
    def get_recent_changes(
        self,
        symbol: Optional[str] = None,
        days: int = 90,
        significance: Optional[str] = None
    ) -> List[HolderChange]:
        """Get recent holder changes"""
        
        cutoff = datetime.now() - timedelta(days=days)
        
        changes = [c for c in self.changes if c.change_date >= cutoff]
        
        if symbol:
            changes = [c for c in changes if c.symbol == symbol]
        
        if significance:
            changes = [c for c in changes if c.significance == significance]
        
        return sorted(changes, key=lambda x: x.change_date, reverse=True)
    
    def get_smart_money_flow(
        self,
        symbol: str,
        hedge_funds_only: bool = False
    ) -> Dict:
        """
        Analyze smart money flow direction
        
        Returns:
        - Overall direction (increasing/decreasing/stable)
        - Notable movers
        - Concentration trends
        """
        if symbol not in self.holder_history or len(self.holder_history[symbol]) < 2:
            return {"direction": "unknown", "message": "Insufficient data"}
        
        snapshots = self.holder_history[symbol]
        recent = snapshots[-1]
        prev = snapshots[-2] if len(snapshots) >= 2 else None
        
        # Filter changes
        changes = [c for c in self.changes 
                  if c.symbol == symbol and 
                  (not hedge_funds_only or c.holder_type == "hedge_fund")]
        
        # Calculate net direction
        net_change = sum(c.change_shares for c in changes)
        
        if net_change > 0:
            direction = "increasing"
        elif net_change < 0:
            direction = "decreasing"
        else:
            direction = "stable"
        
        # Notable movers
        notable_increases = [c for c in changes 
                           if c.significance in ["major", "moderate"] and c.change_shares > 0]
        notable_decreases = [c for c in changes 
                           if c.significance in ["major", "moderate"] and c.change_shares < 0]
        
        return {
            "symbol": symbol,
            "direction": direction,
            "net_change_shares": net_change,
            "current_concentration": recent.concentration,
            "num_holders": recent.num_holders,
            "notable_increases": [
                {"name": c.holder_name, "change_pct": c.change_pct}
                for c in notable_increases[:5]
            ],
            "notable_decreases": [
                {"name": c.holder_name, "change_pct": c.change_pct}
                for c in notable_decreases[:5]
            ]
        }
    
    def get_holder_comparison(
        self,
        symbols: List[str]
    ) -> pd.DataFrame:
        """Compare holder metrics across multiple ETFs"""
        
        data = []
        
        for symbol in symbols:
            if symbol in self.holder_history and self.holder_history[symbol]:
                recent = self.holder_history[symbol][-1]
                data.append({
                    "symbol": symbol,
                    "num_holders": recent.num_holders,
                    "total_institutional_pct": recent.total_institutional_pct,
                    "concentration_top10": recent.concentration,
                    "snapshot_date": recent.date
                })
        
        return pd.DataFrame(data)
    
    def to_dict(self) -> Dict:
        """Export tracker state to dict"""
        return {
            "holder_history": {
                symbol: [
                    {
                        "date": s.date.isoformat(),
                        "num_holders": s.num_holders,
                        "concentration": s.concentration,
                        "top_holders": s.top_holders[:10]
                    }
                    for s in snapshots
                ]
                for symbol, snapshots in self.holder_history.items()
            },
            "recent_changes": [
                {
                    "holder_name": c.holder_name,
                    "symbol": c.symbol,
                    "change_pct": c.change_pct,
                    "significance": c.significance,
                    "date": c.change_date.isoformat()
                }
                for c in self.changes[-20:]
            ]
        }


if __name__ == "__main__":
    # Test holder tracker
    tracker = HolderTracker()
    
    # Sample data
    holders_q1 = [
        {"name": "BlackRock Inc", "shares": 50000000, "value": 9250000000, "pct_held": 20.0, "holder_type": "institution"},
        {"name": "Vanguard Group", "shares": 35000000, "value": 6475000000, "pct_held": 14.0, "holder_type": "institution"},
        {"name": "State Street Corp", "shares": 25000000, "value": 4625000000, "pct_held": 10.0, "holder_type": "institution"},
        {"name": "Citadel Advisors", "shares": 5000000, "value": 925000000, "pct_held": 2.0, "holder_type": "hedge_fund"},
    ]
    
    holders_q2 = [
        {"name": "BlackRock Inc", "shares": 55000000, "value": 10175000000, "pct_held": 22.0, "holder_type": "institution"},
        {"name": "Vanguard Group", "shares": 38000000, "value": 7030000000, "pct_held": 15.2, "holder_type": "institution"},
        {"name": "State Street Corp", "shares": 22000000, "value": 4070000000, "pct_held": 8.8, "holder_type": "institution"},
        {"name": "Citadel Advisors", "shares": 8000000, "value": 1480000000, "pct_held": 3.2, "holder_type": "hedge_fund"},
        {"name": "Bridgewater Associates", "shares": 3000000, "value": 555000000, "pct_held": 1.2, "holder_type": "hedge_fund"},
    ]
    
    tracker.add_snapshot("GLD", holders_q1, datetime(2024, 3, 31))
    tracker.add_snapshot("GLD", holders_q2, datetime(2024, 6, 30))
    
    # Get changes
    changes = tracker.get_recent_changes("GLD")
    print(f"\nDetected {len(changes)} changes:")
    for c in changes:
        print(f"  {c.holder_name}: {c.change_pct:+.1f}% ({c.significance})")
    
    # Smart money flow
    flow = tracker.get_smart_money_flow("GLD")
    print(f"\nSmart Money Flow: {flow['direction']}")
