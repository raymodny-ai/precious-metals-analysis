"""
Macroeconomic Data Fetcher
宏观经济数据采集模块
Supports: FRED API
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import requests

from ..utils.logger import setup_logging
from ..utils.config import get_settings

logger = setup_logging("macro_fetcher")
settings = get_settings()


class MacroFetcher:
    """
    Macroeconomic data fetcher using FRED API
    
    Supports:
    - Interest rates (10Y Treasury, Fed Funds Rate)
    - Inflation (CPI, Core CPI)
    - Dollar Index (DXY proxy via trade-weighted)
    - VIX (via FRED VIXCLS)
    """
    
    # FRED series IDs
    SERIES_MAP = {
        # Interest Rates
        "treasury_10y": "DGS10",  # 10-Year Treasury Constant Maturity Rate
        "treasury_2y": "DGS2",    # 2-Year Treasury
        "fed_funds": "FEDFUNDS",  # Federal Funds Effective Rate
        "real_rate": "REAINTRATREARAT10Y",  # 10-Year Real Interest Rate
        
        # Inflation
        "cpi": "CPIAUCSL",        # Consumer Price Index
        "core_cpi": "CPILFESL",   # Core CPI (excluding food and energy)
        "pce": "PCEPI",           # PCE Price Index
        
        # Dollar and Volatility
        "dxy_proxy": "DTWEXBGS",  # Trade Weighted U.S. Dollar Index (Broad)
        "vix": "VIXCLS",          # CBOE Volatility Index
        
        # Commodities related
        "gold_fixing": "GOLDAMGBD228NLBM",  # Gold Fixing Price (London)
        "silver_fixing": "SLVPRUSD",         # Silver Fixing Price
        
        # Economic indicators
        "gdp": "GDP",             # Gross Domestic Product
        "unemployment": "UNRATE", # Unemployment Rate
        "industrial_prod": "INDPRO",  # Industrial Production Index
    }
    
    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.fred_api_key
        if not self.api_key:
            logger.warning("FRED API key not configured. Some features may not work.")
    
    def _make_request(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[Dict]:
        """Make request to FRED API"""
        
        if not self.api_key:
            logger.error("FRED API key required")
            return None
        
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "asc"
        }
        
        if start_date:
            params["observation_start"] = start_date
        if end_date:
            params["observation_end"] = end_date
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"FRED API request failed: {e}")
            return None
    
    def fetch_series(
        self,
        series_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch a single FRED series
        
        Args:
            series_name: Name from SERIES_MAP or raw FRED series ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            DataFrame with columns: time, value, series_id
        """
        # Resolve series ID
        series_id = self.SERIES_MAP.get(series_name, series_name)
        
        logger.info(f"Fetching FRED series: {series_id}")
        
        data = self._make_request(series_id, start_date, end_date)
        
        if not data or "observations" not in data:
            logger.warning(f"No data returned for {series_id}")
            return pd.DataFrame()
        
        # Parse observations
        observations = data["observations"]
        
        df = pd.DataFrame(observations)
        
        if df.empty:
            return pd.DataFrame()
        
        # Clean data
        df["time"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["series_id"] = series_id
        df["series_name"] = series_name
        
        # Remove missing values (FRED uses "." for missing)
        df = df.dropna(subset=["value"])
        
        # Select columns
        df = df[["time", "value", "series_id", "series_name"]]
        
        logger.info(f"Fetched {len(df)} observations for {series_id}")
        return df
    
    def fetch_multiple_series(
        self,
        series_names: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        pivot: bool = False
    ) -> pd.DataFrame:
        """
        Fetch multiple FRED series
        
        Args:
            series_names: List of series names
            start_date: Start date
            end_date: End date
            pivot: If True, pivot to wide format with series as columns
        
        Returns:
            DataFrame with all series
        """
        all_data = []
        
        for series_name in series_names:
            df = self.fetch_series(series_name, start_date, end_date)
            if not df.empty:
                all_data.append(df)
        
        if not all_data:
            return pd.DataFrame()
        
        combined = pd.concat(all_data, ignore_index=True)
        
        if pivot:
            # Pivot to wide format
            combined = combined.pivot(
                index="time",
                columns="series_name",
                values="value"
            ).reset_index()
        
        return combined
    
    def fetch_key_indicators(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch key macroeconomic indicators for precious metals analysis
        
        Includes:
        - 10Y Treasury yield
        - Real interest rate
        - CPI
        - VIX
        - Dollar index proxy
        """
        key_series = [
            "treasury_10y",
            "real_rate",
            "cpi",
            "vix",
            "dxy_proxy"
        ]
        
        return self.fetch_multiple_series(
            key_series,
            start_date,
            end_date,
            pivot=True
        )
    
    def fetch_gold_drivers(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch data specifically relevant to gold price drivers
        """
        gold_drivers = [
            "treasury_10y",   # Real rates (inverse relationship with gold)
            "real_rate",      # Direct measure of real rates
            "cpi",            # Inflation (positive for gold)
            "vix",            # Risk/volatility (positive for gold)
            "dxy_proxy",      # Dollar strength (inverse for gold)
            "fed_funds"       # Fed policy
        ]
        
        df = self.fetch_multiple_series(
            gold_drivers,
            start_date,
            end_date,
            pivot=True
        )
        
        if df.empty:
            return df
        
        # Calculate derived metrics
        if "treasury_10y" in df.columns and "treasury_2y" in df.columns:
            df["yield_curve_spread"] = df["treasury_10y"] - df["treasury_2y"]
        
        # Calculate month-over-month CPI change (annualized inflation)
        if "cpi" in df.columns:
            df["cpi_yoy"] = df["cpi"].pct_change(periods=12) * 100
        
        return df
    
    def get_latest_values(self) -> Dict[str, Any]:
        """
        Get the latest values for key indicators
        """
        key_series = ["treasury_10y", "vix", "dxy_proxy", "cpi"]
        
        latest = {}
        
        for series_name in key_series:
            df = self.fetch_series(series_name)
            if not df.empty:
                latest[series_name] = {
                    "value": df["value"].iloc[-1],
                    "date": df["time"].iloc[-1].strftime("%Y-%m-%d"),
                    "series_id": df["series_id"].iloc[-1]
                }
        
        return latest


# Convenience function
def fetch_macro_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """Convenience function to fetch key macro indicators"""
    fetcher = MacroFetcher()
    return fetcher.fetch_key_indicators(start_date, end_date)


if __name__ == "__main__":
    # Test the fetcher
    fetcher = MacroFetcher()
    
    # Fetch 10Y Treasury
    df = fetcher.fetch_series("treasury_10y", start_date="2023-01-01")
    print(f"Fetched {len(df)} rows for Treasury 10Y")
    if not df.empty:
        print(df.tail())
    
    # Fetch gold drivers
    drivers = fetcher.fetch_gold_drivers(start_date="2023-01-01")
    print(f"\nGold drivers shape: {drivers.shape}")
    if not drivers.empty:
        print(drivers.tail())
