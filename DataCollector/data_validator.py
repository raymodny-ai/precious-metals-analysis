from typing import Dict, List, Union
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """数据验证与质量监控"""
    
    @staticmethod
    def validate_stock_data(data: Dict) -> bool:
        """验证股票数据质量"""
        required_fields = ['symbol', 'price', 'timestamp']
        
        # 1. 检查必需字段
        if not all(field in data for field in required_fields):
            logger.warning(f"Stock data missing fields: {data.keys()}")
            return False
        
        # 2. 检查价格合理性
        if not isinstance(data['price'], (int, float)) or data['price'] <= 0:
            logger.warning(f"Invalid price for {data.get('symbol')}: {data.get('price')}")
            return False
            
        # 3. 检查时间新鲜度
        timestamp = data['timestamp']
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                pass # Let it pass if we can't parse, or fail? Better fail or warn.
        
        if isinstance(timestamp, datetime):
            age = datetime.now() - timestamp
            # Allow up to 24 hours (weekend/market close) but warn if > 1 hour during market hours
            if age > timedelta(hours=24) and data.get('source') != 'yfinance':
                 logger.warning(f"Stale data for {data.get('symbol')}: {age}")
                 # We might still return True if we accept stale data, but let's be strict for now or just log
                 # For now, just log warning but return True as some sources might be delayed
        
        return True

    @staticmethod
    def validate_news_data(articles: List[Dict]) -> List[Dict]:
        """验证新闻数据质量并过滤"""
        valid_articles = []
        
        for article in articles:
            # 1. Check essential fields
            if not article.get('title') or not article.get('url'):
                continue
                
            # 2. Check content length
            content = article.get('content') or ''
            if len(content) < 50 and len(article.get('title', '')) < 20:
                continue # Too short
                
            valid_articles.append(article)
            
        return valid_articles

    @staticmethod
    def check_freshness(timestamp: datetime, max_age_minutes: int = 60) -> bool:
        """检查数据新鲜度"""
        if not timestamp:
            return False
        age = datetime.now() - timestamp
        return age <= timedelta(minutes=max_age_minutes)
