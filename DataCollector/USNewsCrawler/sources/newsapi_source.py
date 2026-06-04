import requests
from datetime import datetime, timedelta
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class NewsAPISource:
    """NewsAPI 数据源 (免费100次/天)"""
    
    name = "NewsAPI"
    BASE_URL = "https://newsapi.org/v2/everything"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def fetch(self, keywords: List[str], days_back: int = 7) -> List[Dict]:
        """获取新闻"""
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        # 构建查询语句
        query = ' OR '.join(keywords)
        
        params = {
            'q': query,
            'from': from_date,
            'sortBy': 'publishedAt',
            'language': 'en',
            'apiKey': self.api_key,
            'pageSize': 100
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get('articles', []):
                # Skip removed articles
                if article['title'] == '[Removed]':
                    continue
                    
                articles.append({
                    'title': article['title'],
                    'content': (article.get('description') or '') + '\n' + (article.get('content') or ''),
                    'url': article['url'],
                    'source': article['source']['name'],
                    'published_at': datetime.strptime(article['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'),
                    'image_url': article.get('urlToImage'),
                    'fetch_source': self.name
                })
            
            return articles
        
        except Exception as e:
            logger.error(f"NewsAPI fetch error: {e}")
            return []
