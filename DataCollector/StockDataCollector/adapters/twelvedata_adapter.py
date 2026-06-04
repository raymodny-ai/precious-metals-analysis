import requests
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TwelveDataAdapter:
    """Twelve Data 数据适配器"""
    
    BASE_URL = "https://api.twelvedata.com"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def get_price(self, symbol: str) -> Optional[Dict]:
        """获取实时报价"""
        params = {
            'symbol': symbol,
            'apikey': self.api_key
        }
        
        try:
            response = self.session.get(f"{self.BASE_URL}/quote", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'code' in data and data['code'] != 200:
                logger.warning(f"Twelve Data: {data.get('message', 'Unknown error')}")
                return None
            
            return {
                'symbol': symbol,
                'price': float(data['close']), # Real-time price if market open, else close
                'previous_close': float(data['previous_close']),
                'change': float(data['change']),
                'change_percent': float(data['percent_change']),
                'high': float(data['high']),
                'low': float(data['low']),
                'open': float(data['open']),
                'volume': int(data.get('volume', 0) or 0), # Sometimes volume is null
                'timestamp': datetime.fromtimestamp(int(data['timestamp'])),
                'source': 'twelvedata'
            }
        
        except Exception as e:
            logger.error(f"Twelve Data API error for {symbol}: {e}")
            return None
