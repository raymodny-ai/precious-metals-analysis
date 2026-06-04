import requests
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AlphaVantageAdapter:
    """Alpha Vantage 数据适配器"""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def get_price(self, symbol: str) -> Optional[Dict]:
        """获取实时报价"""
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol,
            'apikey': self.api_key
        }
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'Global Quote' not in data or not data['Global Quote']:
                logger.warning(f"Alpha Vantage: No data found for {symbol}")
                return None
            
            quote = data['Global Quote']
            
            # 转换时间戳
            latest_trading_day = quote.get('07. latest trading day', '')
            try:
                timestamp = datetime.strptime(latest_trading_day, '%Y-%m-%d')
            except ValueError:
                timestamp = datetime.now()

            return {
                'symbol': symbol,
                'price': float(quote.get('05. price', 0)),
                'previous_close': float(quote.get('08. previous close', 0)),
                'change': float(quote.get('09. change', 0)),
                'change_percent': float(quote.get('10. change percent', '0').rstrip('%')),
                'volume': int(quote.get('06. volume', 0)),
                'timestamp': timestamp,
                'source': 'alpha_vantage'
            }
        
        except Exception as e:
            logger.error(f"Alpha Vantage API error for {symbol}: {e}")
            return None
