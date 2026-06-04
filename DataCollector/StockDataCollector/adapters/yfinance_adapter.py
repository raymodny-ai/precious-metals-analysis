import yfinance as yf
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class YFinanceAdapter:
    """yfinance 数据适配器"""
    
    def get_price(self, symbol: str) -> Optional[Dict]:
        """获取实时报价"""
        try:
            ticker = yf.Ticker(symbol)
            # fast_info is faster than info
            info = ticker.fast_info
            
            # Check if we have valid data
            if info.last_price is None:
                # Fallback to history
                hist = ticker.history(period="1d")
                if hist.empty:
                    logger.warning(f"yfinance: No data found for {symbol}")
                    return None
                price = hist['Close'].iloc[-1]
                prev_close = hist['Open'].iloc[0] # Approximation if no other data
            else:
                price = info.last_price
                prev_close = info.previous_close
            
            change = price - prev_close
            change_percent = (change / prev_close) * 100 if prev_close else 0
            
            return {
                'symbol': symbol,
                'price': float(price),
                'previous_close': float(prev_close),
                'change': float(change),
                'change_percent': float(change_percent),
                'volume': int(info.last_volume) if hasattr(info, 'last_volume') else 0,
                'timestamp': datetime.now(), # yfinance doesn't give precise timestamp for fast_info
                'source': 'yfinance'
            }
        
        except Exception as e:
            logger.error(f"yfinance error for {symbol}: {e}")
            return None
