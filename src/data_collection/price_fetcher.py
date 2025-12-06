"""
Price Data Fetcher
市场价格数据采集模块
Supports: Yahoo Finance API
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..utils.logger import setup_logging
from ..utils.config import get_settings

logger = setup_logging("price_fetcher")
settings = get_settings()


class PriceFetcher:
    """
    Price data fetcher using Yahoo Finance
    
    Supports:
    - Gold ETFs: GLD, IAU, GLDM, SGOL
    - Silver ETFs: SLV, SIVR, AGQ
    - Macro indices: DXY, VIX, ^TNX
    """
    
    # Default symbols to track
    GOLD_ETFS = ["GLD", "IAU", "GLDM", "SGOL"]
    SILVER_ETFS = ["SLV", "SIVR", "AGQ"]
    MACRO_SYMBOLS = ["DX-Y.NYB", "^VIX", "^TNX"]  # DXY, VIX, 10Y Treasury
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    def fetch_price_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch OHLCV price data for a single symbol
        
        Args:
            symbol: Ticker symbol (e.g., 'GLD')
            start_date: Start date (YYYY-MM-DD), defaults to 1 year ago
            end_date: End date (YYYY-MM-DD), defaults to today
            interval: Data interval ('1m', '5m', '1h', '1d', '1wk', '1mo')
        
        Returns:
            DataFrame with columns: time, symbol, open, high, low, close, volume, adj_close
        """
        try:
            # Default date range: 1 year
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            logger.info(f"Fetching {symbol} from {start_date} to {end_date}, interval={interval}")
            
            # Fetch data
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            # Clean and format
            df = df.reset_index()
            df.columns = df.columns.str.lower()
            
            # Rename columns to match schema
            column_mapping = {
                "date": "time",
                "datetime": "time",
                "adj close": "adj_close"
            }
            df = df.rename(columns=column_mapping)
            
            # Add metadata
            df["symbol"] = symbol
            df["source"] = "yfinance"
            
            # Ensure datetime timezone
            if df["time"].dt.tz is None:
                df["time"] = df["time"].dt.tz_localize("UTC")
            else:
                df["time"] = df["time"].dt.tz_convert("UTC")
            
            # Select columns
            columns = ["time", "symbol", "open", "high", "low", "close", "volume", "adj_close", "source"]
            available_cols = [c for c in columns if c in df.columns]
            df = df[available_cols]
            
            # Drop rows with missing close price
            df = df.dropna(subset=["close"])
            
            logger.info(f"Fetched {len(df)} rows for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def fetch_multiple_symbols(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch price data for multiple symbols
        
        Returns:
            Combined DataFrame with all symbols
        """
        all_data = []
        
        for symbol in symbols:
            df = self.fetch_price_data(symbol, start_date, end_date, interval)
            if not df.empty:
                all_data.append(df)
        
        if not all_data:
            return pd.DataFrame()
        
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.sort_values(["symbol", "time"])
        
        return combined
    
    def fetch_all_precious_metals(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch all gold and silver ETF data
        """
        symbols = self.GOLD_ETFS + self.SILVER_ETFS
        return self.fetch_multiple_symbols(symbols, start_date, end_date, interval)
    
    def fetch_latest_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Fetch latest price for symbols
        
        Returns:
            Dict with symbol -> {price, change, change_pct, volume, time}
        """
        if symbols is None:
            symbols = self.GOLD_ETFS + self.SILVER_ETFS
        
        results = {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.fast_info
                
                results[symbol] = {
                    "price": info.get("lastPrice", info.get("regularMarketPrice")),
                    "previous_close": info.get("previousClose", info.get("regularMarketPreviousClose")),
                    "change": None,
                    "change_pct": None,
                    "volume": info.get("lastVolume", info.get("regularMarketVolume")),
                    "time": datetime.now().isoformat()
                }
                
                # Calculate change
                if results[symbol]["price"] and results[symbol]["previous_close"]:
                    change = results[symbol]["price"] - results[symbol]["previous_close"]
                    results[symbol]["change"] = round(change, 4)
                    results[symbol]["change_pct"] = round(change / results[symbol]["previous_close"] * 100, 2)
                    
            except Exception as e:
                logger.error(f"Error fetching latest price for {symbol}: {e}")
                results[symbol] = {"error": str(e)}
        
        return results
    
    def validate_data(self, df: pd.DataFrame) -> tuple[bool, List[str]]:
        """
        Validate price data quality
        
        Returns:
            (is_valid, list of issues)
        """
        issues = []
        
        if df.empty:
            return False, ["DataFrame is empty"]
        
        # Check for required columns
        required = ["time", "symbol", "close"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            issues.append(f"Missing required columns: {missing}")
        
        # Check for missing values in close
        null_close = df["close"].isnull().sum()
        if null_close > 0:
            issues.append(f"Found {null_close} null close prices")
        
        # Check for extreme price changes (>20% daily)
        if len(df) > 1:
            returns = df.groupby("symbol")["close"].pct_change()
            extreme = (returns.abs() > 0.2).sum()
            if extreme > 0:
                issues.append(f"Found {extreme} extreme price changes (>20%)")
        
        # Check for duplicate timestamps per symbol
        duplicates = df.groupby(["symbol", "time"]).size()
        dup_count = (duplicates > 1).sum()
        if dup_count > 0:
            issues.append(f"Found {dup_count} duplicate timestamp entries")
        
        return len(issues) == 0, issues
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add basic technical indicators to price data
        """
        df = df.copy()
        
        for symbol in df["symbol"].unique():
            mask = df["symbol"] == symbol
            symbol_df = df[mask].copy()
            
            # Returns
            df.loc[mask, "returns"] = symbol_df["close"].pct_change()
            
            # Moving averages
            df.loc[mask, "ma_5"] = symbol_df["close"].rolling(5).mean()
            df.loc[mask, "ma_20"] = symbol_df["close"].rolling(20).mean()
            df.loc[mask, "ma_50"] = symbol_df["close"].rolling(50).mean()
            
            # Volatility
            df.loc[mask, "volatility_20"] = symbol_df["close"].pct_change().rolling(20).std()
            
            # RSI (14-period)
            delta = symbol_df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df.loc[mask, "rsi_14"] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            ma_20 = symbol_df["close"].rolling(20).mean()
            std_20 = symbol_df["close"].rolling(20).std()
            df.loc[mask, "bb_upper"] = ma_20 + 2 * std_20
            df.loc[mask, "bb_lower"] = ma_20 - 2 * std_20
        
        return df


# Convenience function
def fetch_gold_silver_prices(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = "1d"
) -> pd.DataFrame:
    """Convenience function to fetch all gold and silver ETF prices"""
    fetcher = PriceFetcher()
    return fetcher.fetch_all_precious_metals(start_date, end_date, interval)


if __name__ == "__main__":
    # Test the fetcher
    fetcher = PriceFetcher()
    
    # Fetch GLD data
    df = fetcher.fetch_price_data("GLD", interval="1d")
    print(f"Fetched {len(df)} rows for GLD")
    print(df.head())
    
    # Validate
    is_valid, issues = fetcher.validate_data(df)
    print(f"Valid: {is_valid}, Issues: {issues}")
    
    # Latest prices
    latest = fetcher.fetch_latest_prices(["GLD", "SLV"])
    print(f"Latest prices: {latest}")
