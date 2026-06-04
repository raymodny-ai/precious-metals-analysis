import requests
import os
import hashlib
from bs4 import BeautifulSoup

class NewsFetcher:
    def __init__(self, api_token=None):
        self.api_token = api_token or os.getenv('FINANCIAL_DATASETS_API_KEY')
        self.base_url = "https://eodhd.com/api/news"
    
    def fetch_news(self, ticker='USA', limit=50):
        params = {
            's': ticker,
            'api_token': self.api_token,
            'limit': limit,
            'offset': 0
        }
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching news: {e}")
            return []

    def clean_text(self, text):
        if not text:
            return ""
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text(separator=' ').strip()

    def deduplicate(self, news_list):
        seen_hashes = set()
        unique_news = []
        for item in news_list:
            title = item.get('title', '')
            if not title:
                continue
            # Simple hash of title for deduplication
            title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()
            if title_hash not in seen_hashes:
                seen_hashes.add(title_hash)
                # Clean content
                item['content'] = self.clean_text(item.get('content', ''))
                unique_news.append(item)
        return unique_news
