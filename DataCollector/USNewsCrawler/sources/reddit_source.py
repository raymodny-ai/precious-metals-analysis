import praw
from datetime import datetime
from typing import List, Dict
import logging
import os

logger = logging.getLogger(__name__)

class RedditNewsSource:
    """Reddit 数据源"""
    
    name = "Reddit"
    
    def __init__(self):
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        user_agent = os.getenv('REDDIT_USER_AGENT', 'PreciousInsight/1.0')
        
        if client_id and client_secret:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
        else:
            self.reddit = None
            logger.warning("Reddit credentials not found")
    
    def fetch(self, keywords: List[str], days_back: int = 7) -> List[Dict]:
        """获取新闻 (从特定Subreddit)"""
        if not self.reddit:
            return []
            
        subreddits = ['Gold', 'Silverbugs', 'investing', 'stocks', 'wallstreetbets']
        articles = []
        
        try:
            # Combine subreddits
            subreddit = self.reddit.subreddit('+'.join(subreddits))
            
            # Search or get hot/new
            # Let's search for keywords to be more specific
            query = ' OR '.join(keywords)
            
            for submission in subreddit.search(query, sort='new', time_filter='week', limit=100):
                published_at = datetime.fromtimestamp(submission.created_utc)
                
                articles.append({
                    'title': submission.title,
                    'content': submission.selftext,
                    'url': submission.url,
                    'source': f"Reddit/r/{submission.subreddit.display_name}",
                    'published_at': published_at,
                    'image_url': None,
                    'fetch_source': self.name
                })
                
        except Exception as e:
            logger.error(f"Reddit fetch error: {e}")
            return []
            
        return articles
