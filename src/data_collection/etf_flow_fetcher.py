"""
ETF Flow Data Fetcher
ETF资金流数据采集模块
Supports: FMP API, Yahoo Finance (fallback)
"""

import pandas as pd
import numpy as np
import requests
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from ..utils.logger import setup_logging
from ..utils.config import get_settings

logger = setup_logging("etf_flow_fetcher")
settings = get_settings()


class ETFFlowFetcher:
    """
    ETF Fund Flow Data Fetcher
    
    Tracks:
    - Gold ETFs: GLD, IAU, GLDM, SGOL
    - Silver ETFs: SLV, SIVR, AGQ
    
    Data includes:
    - Net fund flows (inflows/outflows)
    - Shares outstanding changes
    - AUM (Assets Under Management)
    - Top holders (13F data)
    """
    
    # ETF metadata
    ETF_INFO = {
        "GLD": {"name": "SPDR Gold Shares", "type": "gold", "expense_ratio": 0.40},
        "IAU": {"name": "iShares Gold Trust", "type": "gold", "expense_ratio": 0.25},
        "GLDM": {"name": "SPDR Gold MiniShares", "type": "gold", "expense_ratio": 0.10},
        "SGOL": {"name": "Aberdeen Physical Gold", "type": "gold", "expense_ratio": 0.17},
        "SLV": {"name": "iShares Silver Trust", "type": "silver", "expense_ratio": 0.50},
        "SIVR": {"name": "Aberdeen Physical Silver", "type": "silver", "expense_ratio": 0.30},
        "AGQ": {"name": "ProShares Ultra Silver", "type": "silver", "expense_ratio": 0.95},
    }
    
    FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(self, fmp_api_key: Optional[str] = None):
        self.fmp_api_key = fmp_api_key or settings.fmp_api_key
        
        if not self.fmp_api_key:
            logger.warning("FMP API key not configured. Using limited functionality.")
    
    def _fmp_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make request to FMP API"""
        if not self.fmp_api_key:
            return None
        
        params = params or {}
        params["apikey"] = self.fmp_api_key
        
        url = f"{self.FMP_BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"FMP API request failed: {e}")
            return None
    
    def get_etf_profile(self, symbol: str) -> Optional[Dict]:
        """Get ETF profile information"""
        data = self._fmp_request(f"etf/info/{symbol}")
        
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        
        # Fallback to yfinance
        return self._get_etf_profile_yfinance(symbol)
    
    def _get_etf_profile_yfinance(self, symbol: str) -> Optional[Dict]:
        """Get ETF profile from yfinance as fallback"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                "symbol": symbol,
                "name": info.get("longName", self.ETF_INFO.get(symbol, {}).get("name")),
                "aum": info.get("totalAssets"),
                "expense_ratio": info.get("annualReportExpenseRatio"),
                "nav": info.get("navPrice"),
                "shares_outstanding": info.get("sharesOutstanding"),
                "avg_volume": info.get("averageVolume"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
            }
        except Exception as e:
            logger.error(f"Error getting ETF profile for {symbol}: {e}")
            return None
    
    def get_shares_outstanding_history(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get historical shares outstanding data
        This can be used to estimate fund flows
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get historical data
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                return pd.DataFrame()
            
            # Reset index and clean
            df = df.reset_index()
            df.columns = df.columns.str.lower()
            
            # Rename date column
            if "date" in df.columns:
                df = df.rename(columns={"date": "time"})
            
            # Add symbol
            df["symbol"] = symbol
            
            # Get current shares outstanding as baseline
            info = ticker.info
            shares_outstanding = info.get("sharesOutstanding", np.nan)
            
            # Estimate shares based on volume patterns (simplified)
            df["volume_ratio"] = df["volume"] / df["volume"].mean()
            
            # Basic estimation (this is simplified - real data would come from SEC filings)
            if not np.isnan(shares_outstanding):
                df["shares_outstanding"] = shares_outstanding
            else:
                df["shares_outstanding"] = np.nan
            
            return df[["time", "symbol", "close", "volume", "shares_outstanding"]]
            
        except Exception as e:
            logger.error(f"Error getting shares outstanding for {symbol}: {e}")
            return pd.DataFrame()
    
    def estimate_fund_flows(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Estimate daily fund flows based on price and volume data
        
        Flow estimation method:
        - Use volume and price to estimate dollar flows
        - Compare with historical averages to detect unusual flows
        """
        try:
            ticker = yf.Ticker(symbol)
            
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                return pd.DataFrame()
            
            df = df.reset_index()
            df.columns = df.columns.str.lower()
            
            if "date" in df.columns:
                df = df.rename(columns={"date": "time"})
            
            df["symbol"] = symbol
            
            # Calculate metrics
            df["dollar_volume"] = df["close"] * df["volume"]
            df["avg_volume_20d"] = df["volume"].rolling(20).mean()
            df["volume_ratio"] = df["volume"] / df["avg_volume_20d"]
            
            # Estimate net flow direction based on price change and volume
            df["returns"] = df["close"].pct_change()
            df["flow_direction"] = np.sign(df["returns"])
            
            # Estimate flow magnitude (simplified model)
            # Positive returns + high volume = inflow
            # Negative returns + high volume = outflow
            df["estimated_flow"] = df["dollar_volume"] * df["flow_direction"] * (df["volume_ratio"] - 1)
            df["estimated_flow"] = df["estimated_flow"].fillna(0)
            
            # Rolling flows
            df["flow_5d"] = df["estimated_flow"].rolling(5).sum()
            df["flow_20d"] = df["estimated_flow"].rolling(20).sum()
            
            # Anomaly detection (>2 std from mean)
            flow_std = df["estimated_flow"].std()
            flow_mean = df["estimated_flow"].mean()
            df["is_anomaly"] = np.abs(df["estimated_flow"] - flow_mean) > 2 * flow_std
            
            # Format output
            result = df[[
                "time", "symbol", "close", "volume", "dollar_volume",
                "estimated_flow", "flow_5d", "flow_20d", "is_anomaly"
            ]].copy()
            
            # Rename for schema compatibility
            result = result.rename(columns={
                "estimated_flow": "net_flow",
                "flow_5d": "flow_change_5d",
                "flow_20d": "flow_change_20d"
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error estimating fund flows for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_top_holders(self, symbol: str) -> pd.DataFrame:
        """
        Get top institutional holders (from 13F filings)
        """
        data = self._fmp_request(f"institutional-holder/{symbol}")
        
        if not data:
            # Fallback to yfinance
            return self._get_holders_yfinance(symbol)
        
        holders = []
        for holder in data:
            holders.append({
                "symbol": symbol,
                "holder_name": holder.get("holder", ""),
                "shares": holder.get("shares", 0),
                "value_usd": holder.get("value", 0),
                "percent_of_fund": holder.get("weightedAvgOwned", 0) * 100,
                "report_date": holder.get("dateReported"),
                "holder_type": "institutional"
            })
        
        return pd.DataFrame(holders)
    
    def _get_holders_yfinance(self, symbol: str) -> pd.DataFrame:
        """Get holders from yfinance as fallback"""
        try:
            ticker = yf.Ticker(symbol)
            holders = ticker.institutional_holders
            
            if holders is None or holders.empty:
                return pd.DataFrame()
            
            holders = holders.reset_index(drop=True)
            holders["symbol"] = symbol
            holders["holder_type"] = "institutional"
            
            # Rename columns
            column_map = {
                "Holder": "holder_name",
                "Shares": "shares",
                "Value": "value_usd",
                "% Out": "percent_of_fund",
                "Date Reported": "report_date"
            }
            holders = holders.rename(columns=column_map)
            
            return holders
            
        except Exception as e:
            logger.error(f"Error getting holders for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_all_etf_flows(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get fund flow data for all tracked ETFs
        """
        all_flows = []
        
        for symbol in self.ETF_INFO.keys():
            logger.info(f"Fetching flows for {symbol}")
            df = self.estimate_fund_flows(symbol, start_date, end_date)
            if not df.empty:
                all_flows.append(df)
        
        if not all_flows:
            return pd.DataFrame()
        
        return pd.concat(all_flows, ignore_index=True)
    
    def get_flow_summary(self) -> Dict[str, Dict]:
        """
        Get current flow summary for all ETFs
        """
        summary = {}
        
        for symbol, info in self.ETF_INFO.items():
            # Get recent flows
            flows = self.estimate_fund_flows(symbol)
            
            if flows.empty:
                summary[symbol] = {"error": "No data available"}
                continue
            
            latest = flows.iloc[-1]
            
            # Get ETF profile
            profile = self.get_etf_profile(symbol)
            
            summary[symbol] = {
                "name": info["name"],
                "type": info["type"],
                "aum": profile.get("aum") if profile else None,
                "latest_flow": latest.get("net_flow", 0),
                "flow_5d": latest.get("flow_change_5d", 0),
                "flow_20d": latest.get("flow_change_20d", 0),
                "is_anomaly": latest.get("is_anomaly", False),
                "last_price": latest.get("close"),
                "last_updated": latest.get("time").isoformat() if pd.notna(latest.get("time")) else None
            }
        
        return summary


# Convenience functions
def fetch_etf_flows(
    symbols: Optional[List[str]] = None,
    start_date: Optional[str] = None
) -> pd.DataFrame:
    """Convenience function to fetch ETF flows"""
    fetcher = ETFFlowFetcher()
    
    if symbols is None:
        return fetcher.get_all_etf_flows(start_date)
    
    all_flows = []
    for symbol in symbols:
        df = fetcher.estimate_fund_flows(symbol, start_date)
        if not df.empty:
            all_flows.append(df)
    
    if not all_flows:
        return pd.DataFrame()
    
    return pd.concat(all_flows, ignore_index=True)


if __name__ == "__main__":
    # Test the fetcher
    fetcher = ETFFlowFetcher()
    
    # Get GLD profile
    profile = fetcher.get_etf_profile("GLD")
    print(f"GLD Profile: {profile}")
    
    # Get estimated flows
    flows = fetcher.estimate_fund_flows("GLD")
    print(f"\nGLD Flows ({len(flows)} days):")
    if not flows.empty:
        print(flows.tail())
    
    # Get flow summary
    summary = fetcher.get_flow_summary()
    print(f"\nFlow Summary:")
    for symbol, data in summary.items():
        print(f"  {symbol}: {data}")
