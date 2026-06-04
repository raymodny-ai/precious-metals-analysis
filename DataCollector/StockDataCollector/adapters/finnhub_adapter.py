import requests
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FinnhubAdapter:
    """Finnhub 数据适配器"""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def get_price(self, symbol: str) -> Optional[Dict]:
        """获取实时报价"""
        headers = {'X-Finnhub-Token': self.api_key}
        
        try:
            # 获取实时报价
            response = self.session.get(
                f"{self.BASE_URL}/quote",
                params={'symbol': symbol},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Finnhub returns 0 for all fields if symbol not found
            if data.get('c', 0) == 0 and data.get('d', 0) == 0:
                logger.warning(f"Finnhub: No data found for {symbol}")
                return None
            
            return {
                'symbol': symbol,
                'price': float(data['c']),  # current price
                'previous_close': float(data['pc']),  # previous close
                'change': float(data['d']),  # change
                'change_percent': float(data['dp']),  # change percent
                'high': float(data['h']),  # day high
                'low': float(data['l']),  # day low
                'open': float(data['o']),  # day open
                'timestamp': datetime.fromtimestamp(data['t']),
                'source': 'finnhub'
            }
        
        except Exception as e:
            logger.error(f"Finnhub API error for {symbol}: {e}")
            return None
