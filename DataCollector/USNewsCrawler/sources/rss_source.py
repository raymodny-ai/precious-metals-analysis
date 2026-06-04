import feedparser
from datetime import datetime
from typing import List, Dict
import logging
import time

logger = logging.getLogger(__name__)

class RSSNewsSource:
    """RSS Feeds 数据源"""
    
    name = "RSS"
    
    def __init__(self, feed_urls: List[str]):
        self.feed_urls = feed_urls
    
    def fetch(self, keywords: List[str] = None, days_back: int = 7) -> List[Dict]:
        """获取新闻"""
        all_articles = []
        
        for url in self.feed_urls:
            try:
                feed = feedparser.parse(url)
                
                for entry in feed.entries:
                    # Parse date
                    published_at = None
                    if hasattr(entry, 'published_parsed'):
                        published_at = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    elif hasattr(entry, 'updated_parsed'):
                        published_at = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                    else:
                        published_at = datetime.now()
                    
                    # Filter by keywords if provided
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    content = title + ' ' + summary
                    
                    if keywords:
                        if not any(k.lower() in content.lower() for k in keywords):
                            continue
                    
                    all_articles.append({
                        'title': title,
                        'content': summary,
                        'url': entry.get('link', ''),
                        'source': feed.feed.get('title', 'RSS Feed'),
                        'published_at': published_at,
                        'image_url': None, # RSS usually doesn't have easy image extraction without parsing HTML
                        'fetch_source': self.name
                    })
                    
            except Exception as e:
                logger.error(f"RSS fetch error for {url}: {e}")
                continue
                
        return all_articles
