"""
Alpha Vantage API客户端
作为yfinance的备用数据源
"""
import requests
import time
from typing import Optional, Dict, List
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AlphaVantageClient:
    """Alpha Vantage API客户端"""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.last_request_time = 0
        self.min_interval = 12  # 免费版限制: 5请求/分钟
    
    def _rate_limit(self):
        """速率限制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            logger.info(f"Rate limiting: waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        self.last_request_time = time.time()
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """发送API请求"""
        self._rate_limit()
        
        params['apikey'] = self.api_key
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # 检查错误
            if 'Error Message' in data:
                logger.error(f"API Error: {data['Error Message']}")
                return None
            
            if 'Note' in data:
                logger.warning(f"API Note: {data['Note']}")
                return None
            
            return data
        
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        获取实时报价
        
        Args:
            symbol: 股票代码
        
        Returns:
            报价数据
        """
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol
        }
        
        data = self._make_request(params)
        
        if not data or 'Global Quote' not in data:
            return None
        
        quote = data['Global Quote']
        
        if not quote:
            return None
        
        try:
            return {
                'symbol': symbol,
                'price': float(quote.get('05. price', 0)),
                'volume': int(quote.get('06. volume', 0)),
                'previous_close': float(quote.get('08. previous close', 0)),
                'change': float(quote.get('09. change', 0)),
                'change_percent': float(quote.get('10. change percent', '0').rstrip('%')),
                'timestamp': datetime.now()
            }
        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing quote data: {e}")
            return None
    
    def get_daily_prices(self, symbol: str, outputsize: str = 'compact') -> Optional[pd.DataFrame]:
        """
        获取日线数据
        
        Args:
            symbol: 股票代码
            outputsize: 'compact' (100条) 或 'full' (全部历史)
        
        Returns:
            价格DataFrame
        """
        params = {
            'function': 'TIME_SERIES_DAILY_ADJUSTED',
            'symbol': symbol,
            'outputsize': outputsize
        }
        
        data = self._make_request(params)
        
        if not data or 'Time Series (Daily)' not in data:
            return None
        
        time_series = data['Time Series (Daily)']
        
        # 转换为DataFrame
        records = []
        for date_str, values in time_series.items():
            try:
                records.append({
                    'date': pd.to_datetime(date_str),
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close']),
                    'adjusted_close': float(values['5. adjusted close']),
                    'volume': int(values['6. volume']),
                    'dividend': float(values['7. dividend amount']),
                    'split_coefficient': float(values['8. split coefficient'])
                })
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping date {date_str}: {e}")
                continue
        
        if not records:
            return None
        
        df = pd.DataFrame(records)
        df = df.sort_values('date').reset_index(drop=True)
        df['symbol'] = symbol
        
        return df
    
    def get_company_overview(self, symbol: str) -> Optional[Dict]:
        """
        获取公司基本信息
        
        Returns:
            公司信息字典
        """
        params = {
            'function': 'OVERVIEW',
            'symbol': symbol
        }
        
        data = self._make_request(params)
        
        if not data or 'Symbol' not in data:
            return None
        
        try:
            return {
                'symbol': data.get('Symbol'),
                'company_name': data.get('Name'),
                'sector': data.get('Sector'),
                'industry': data.get('Industry'),
                'market_cap': int(data.get('MarketCapitalization', 0)),
                'pe_ratio': float(data.get('PERatio', 0) or 0),
                'peg_ratio': float(data.get('PEGRatio', 0) or 0),
                'book_value': float(data.get('BookValue', 0) or 0),
                'dividend_yield': float(data.get('DividendYield', 0) or 0),
                'eps': float(data.get('EPS', 0) or 0),
                'revenue_per_share': float(data.get('RevenuePerShareTTM', 0) or 0),
                'profit_margin': float(data.get('ProfitMargin', 0) or 0),
                'operating_margin': float(data.get('OperatingMarginTTM', 0) or 0),
                'return_on_assets': float(data.get('ReturnOnAssetsTTM', 0) or 0),
                'return_on_equity': float(data.get('ReturnOnEquityTTM', 0) or 0),
                'revenue_ttm': int(data.get('RevenueTTM', 0) or 0),
                'gross_profit_ttm': int(data.get('GrossProfitTTM', 0) or 0),
                '52_week_high': float(data.get('52WeekHigh', 0) or 0),
                '52_week_low': float(data.get('52WeekLow', 0) or 0),
                '50_day_ma': float(data.get('50DayMovingAverage', 0) or 0),
                '200_day_ma': float(data.get('200DayMovingAverage', 0) or 0),
                'beta': float(data.get('Beta', 0) or 0),
                'description': data.get('Description', ''),
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing company overview: {e}")
            return None
    
    def search_symbol(self, keywords: str) -> List[Dict]:
        """
        搜索股票代码
        
        Args:
            keywords: 搜索关键词
        
        Returns:
            匹配的股票列表
        """
        params = {
            'function': 'SYMBOL_SEARCH',
            'keywords': keywords
        }
        
        data = self._make_request(params)
        
        if not data or 'bestMatches' not in data:
            return []
        
        results = []
        for match in data['bestMatches']:
            results.append({
                'symbol': match.get('1. symbol'),
                'name': match.get('2. name'),
                'type': match.get('3. type'),
                'region': match.get('4. region'),
                'currency': match.get('8. currency'),
                'match_score': float(match.get('9. matchScore', 0))
            })
        
        return results

# 使用示例
def demo():
    """演示功能"""
    import os
    
    api_key = os.getenv('ALPHA_VANTAGE_KEY', 'demo')
    client = AlphaVantageClient(api_key)
    
    print("="*60)
    print("Alpha Vantage Client Demo")
    print("="*60)
    
    # 1. 获取报价
    print("\n【1】获取 GLD 报价:")
    quote = client.get_quote('GLD')
    if quote:
        print(f"  价格: ${quote['price']:.2f}")
        print(f"  涨跌: {quote['change_percent']:+.2f}%")
    
    # 2. 搜索股票
    print("\n【2】搜索 'gold mining':")
    results = client.search_symbol('gold mining')
    for i, result in enumerate(results[:3], 1):
        print(f"  {i}. {result['symbol']} - {result['name']}")
    
    # 3. 公司信息
    print("\n【3】获取 NEM 公司信息:")
    overview = client.get_company_overview('NEM')
    if overview:
        print(f"  公司: {overview['company_name']}")
        print(f"  行业: {overview['sector']}")
        print(f"  市值: ${overview['market_cap']/1e9:.1f}B")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    demo()
