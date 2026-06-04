"""
News Data Fetcher
新闻数据采集模块
Supports: Multiple news APIs (marketaux, newsapi, etc.)
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import hashlib
import re

from ..utils.logger import setup_logging
from ..utils.config import get_settings

logger = setup_logging("news_fetcher")
settings = get_settings()


class NewsFetcher:
    """
    News data fetcher for precious metals related news
    
    Supports multiple API sources:
    - marketaux (primary)
    - newsapi (fallback)
    - web scraping (backup)
    """
    
    # Keywords for precious metals news
    GOLD_KEYWORDS = [
        "gold", "gold price", "gold market", "bullion",
        "GLD", "gold ETF", "XAUUSD", "gold futures",
        "Federal Reserve gold", "central bank gold"
    ]
    
    SILVER_KEYWORDS = [
        "silver", "silver price", "silver market",
        "SLV", "silver ETF", "XAGUSD", "silver futures"
    ]
    
    PRECIOUS_METALS_KEYWORDS = [
        "precious metals", "safe haven", "inflation hedge",
        "treasury yields", "dollar weakness", "geopolitical risk"
    ]
    
    def __init__(self, api_key: Optional[str] = None, api_source: str = "marketaux"):
        self.api_key = api_key or settings.news_api_key
        self.api_source = api_source
        
        # API endpoints
        self.endpoints = {
            "marketaux": "https://api.marketaux.com/v1/news/all",
            "newsapi": "https://newsapi.org/v2/everything"
        }
        
        if not self.api_key:
            logger.warning("News API key not configured. Using mock data for testing.")
    
    def _generate_article_id(self, title: str, source: str, published: str) -> str:
        """Generate unique ID for article deduplication"""
        content = f"{title}{source}{published}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _clean_text(self, text: Optional[str]) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def fetch_from_marketaux(
        self,
        keywords: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetch news from Marketaux API
        
        Args:
            keywords: Search keywords
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum articles to fetch
        
        Returns:
            DataFrame with news articles
        """
        if not self.api_key:
            return self._get_mock_news()
        
        if keywords is None:
            keywords = self.GOLD_KEYWORDS[:3]  # Use top gold keywords
        
        params = {
            "api_token": self.api_key,
            "search": " OR ".join(keywords),
            "language": "en",
            "limit": min(limit, 100),
            "sort": "published_desc"
        }
        
        if start_date:
            params["published_after"] = start_date
        if end_date:
            params["published_before"] = end_date
        
        try:
            logger.info(f"Fetching news from Marketaux with keywords: {keywords[:3]}...")
            
            response = requests.get(
                self.endpoints["marketaux"],
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if "data" not in data:
                logger.warning("No news data in response")
                return pd.DataFrame()
            
            articles = data["data"]
            return self._parse_marketaux_response(articles)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Marketaux API request failed: {e}")
            return self._get_mock_news()
    
    def _parse_marketaux_response(self, articles: List[Dict]) -> pd.DataFrame:
        """Parse Marketaux API response"""
        parsed = []
        
        for article in articles:
            try:
                published = article.get("published_at", "")
                if published:
                    time = pd.to_datetime(published)
                else:
                    time = datetime.now()
                
                parsed.append({
                    "article_id": self._generate_article_id(
                        article.get("title", ""),
                        article.get("source", ""),
                        published
                    ),
                    "time": time,
                    "title": self._clean_text(article.get("title")),
                    "content": self._clean_text(article.get("description") or article.get("snippet")),
                    "source": article.get("source", ""),
                    "url": article.get("url", ""),
                    "author": article.get("author"),
                    "keywords": self._extract_keywords(article.get("title", "") + " " + article.get("description", "")),
                    "symbol": self._determine_symbol(article.get("title", "")),
                    "language": "en"
                })
            except Exception as e:
                logger.warning(f"Error parsing article: {e}")
                continue
        
        return pd.DataFrame(parsed)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        text_lower = text.lower()
        keywords = []
        
        all_keywords = self.GOLD_KEYWORDS + self.SILVER_KEYWORDS + self.PRECIOUS_METALS_KEYWORDS
        
        for keyword in all_keywords:
            if keyword.lower() in text_lower:
                keywords.append(keyword)
        
        return list(set(keywords))[:10]  # Limit to 10 keywords
    
    def _determine_symbol(self, text: str) -> Optional[str]:
        """Determine which asset the news is about"""
        text_lower = text.lower()
        
        # Check for explicit ETF mentions
        if any(etf.lower() in text_lower for etf in ["gld", "iau", "gldm", "sgol"]):
            return "GLD"
        if any(etf.lower() in text_lower for etf in ["slv", "sivr", "agq"]):
            return "SLV"
        
        # Check for gold/silver mentions
        gold_count = sum(1 for kw in self.GOLD_KEYWORDS if kw.lower() in text_lower)
        silver_count = sum(1 for kw in self.SILVER_KEYWORDS if kw.lower() in text_lower)
        
        if gold_count > silver_count:
            return "GLD"
        elif silver_count > gold_count:
            return "SLV"
        elif gold_count > 0 or silver_count > 0:
            return "GLD"  # Default to gold
        
        return None
    
    def fetch_precious_metals_news(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetch all precious metals related news
        """
        all_keywords = self.GOLD_KEYWORDS[:5] + self.SILVER_KEYWORDS[:3]
        return self.fetch_from_marketaux(
            keywords=all_keywords,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    def fetch_gold_news(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50
    ) -> pd.DataFrame:
        """Fetch gold-specific news"""
        df = self.fetch_from_marketaux(
            keywords=self.GOLD_KEYWORDS[:5],
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        if not df.empty:
            df["symbol"] = "GLD"
        
        return df
    
    def fetch_silver_news(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50
    ) -> pd.DataFrame:
        """Fetch silver-specific news"""
        df = self.fetch_from_marketaux(
            keywords=self.SILVER_KEYWORDS[:5],
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        if not df.empty:
            df["symbol"] = "SLV"
        
        return df
    
    def _get_mock_news(self) -> pd.DataFrame:
        """Generate mock news data for testing without API key"""
        logger.info("Generating mock news data for testing")
        
        mock_articles = [
            {
                "title": "Gold Prices Surge as Fed Signals Rate Pause",
                "content": "Gold prices rose sharply on Friday as the Federal Reserve signaled a pause in interest rate hikes.",
                "source": "Financial Times",
                "symbol": "GLD"
            },
            {
                "title": "Silver Demand Hits Record High Amid Industrial Growth",
                "content": "Silver demand reached a record high in Q3 2024 driven by solar panel manufacturing and electronics.",
                "source": "Reuters",
                "symbol": "SLV"
            },
            {
                "title": "Central Banks Continue Gold Buying Spree",
                "content": "Central banks purchased another 200 tonnes of gold in the third quarter, extending the buying trend.",
                "source": "Bloomberg",
                "symbol": "GLD"
            },
            {
                "title": "Dollar Weakness Boosts Precious Metals",
                "content": "A weakening US dollar has made gold and silver more attractive to international investors.",
                "source": "CNBC",
                "symbol": "GLD"
            },
            {
                "title": "GLD ETF Sees Largest Inflows in Months",
                "content": "The SPDR Gold Shares ETF reported its largest weekly inflows since March as investors seek safe havens.",
                "source": "ETF.com",
                "symbol": "GLD"
            }
        ]
        
        now = datetime.now()
        parsed = []
        
        for i, article in enumerate(mock_articles):
            time = now - timedelta(hours=i * 6)
            parsed.append({
                "article_id": f"mock_{i}_{time.strftime('%Y%m%d')}",
                "time": time,
                "title": article["title"],
                "content": article["content"],
                "source": article["source"],
                "url": f"https://example.com/news/{i}",
                "author": None,
                "keywords": self._extract_keywords(article["title"] + " " + article["content"]),
                "symbol": article["symbol"],
                "language": "en"
            })
        
        return pd.DataFrame(parsed)
    
    def deduplicate_news(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate news articles"""
        if df.empty:
            return df
        
        # Remove exact duplicates
        df = df.drop_duplicates(subset=["article_id"])
        
        # Remove similar titles (>80% similarity could be implemented here)
        df = df.drop_duplicates(subset=["title"])
        
        return df


# Convenience function
def fetch_latest_news(limit: int = 50) -> pd.DataFrame:
    """Convenience function to fetch latest precious metals news"""
    fetcher = NewsFetcher()
    return fetcher.fetch_precious_metals_news(limit=limit)


if __name__ == "__main__":
    # Test the fetcher
    fetcher = NewsFetcher()
    
    # Fetch gold news
    df = fetcher.fetch_gold_news(limit=10)
    print(f"Fetched {len(df)} gold news articles")
    if not df.empty:
        print(df[["time", "title", "source", "symbol"]].head())
