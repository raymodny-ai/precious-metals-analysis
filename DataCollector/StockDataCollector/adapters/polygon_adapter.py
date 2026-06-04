import requests
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PolygonAdapter:
    """Polygon.io 数据适配器"""
    
    BASE_URL = "https://api.polygon.io/v2"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def get_price(self, symbol: str) -> Optional[Dict]:
        """获取实时报价"""
        params = {
            'apiKey': self.api_key
        }
        
        try:
            # Polygon uses 'prev' endpoint for previous close/open/high/low if real-time is delayed/paid
            # But for free tier, we might use 'aggs/ticker/{symbol}/prev'
            # Or 'snapshot/locale/us/markets/stocks/tickers/{symbol}' (requires paid usually for real-time)
            # Let's use the Previous Close endpoint which is free
            
            # Actually, let's try the Aggregates (Bars) endpoint for the latest day
            # Or just use the 'Previous Close' endpoint as a fallback for free tier
            
            url = f"{self.BASE_URL}/aggs/ticker/{symbol}/prev"
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'OK' or not data.get('results'):
                logger.warning(f"Polygon: No data found for {symbol}")
                return None
            
            result = data['results'][0]
            
            return {
                'symbol': symbol,
                'price': float(result['c']),  # close price
                'previous_close': float(result['c']), # It is previous close
                'change': 0.0, # Can't calculate change from just prev close
                'change_percent': 0.0,
                'high': float(result['h']),
                'low': float(result['l']),
                'open': float(result['o']),
                'volume': int(result['v']),
                'timestamp': datetime.fromtimestamp(result['t'] / 1000),
                'source': 'polygon'
            }
        
        except Exception as e:
            logger.error(f"Polygon API error for {symbol}: {e}")
            return None
