from typing import List, Dict
import logging
import os
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

class MultiSourceNewsFetcher:
    """多源新闻聚合器"""
    
    def __init__(self):
        self.sources = []
        self._initialize_sources()
        
    def _initialize_sources(self):
        """初始化所有新闻源"""
        # 1. NewsAPI (免费100次/天)
        newsapi_key = os.getenv('NEWSAPI_KEY')
        if newsapi_key:
            try:
                from .sources.newsapi_source import NewsAPISource
                self.sources.append(NewsAPISource(newsapi_key))
                logger.info("✓ NewsAPI initialized")
            except Exception as e:
                logger.warning(f"NewsAPI init failed: {e}")
        
        # 2. RSS Feeds (完全免费)
        try:
            from .sources.rss_source import RSSNewsSource
            self.sources.append(RSSNewsSource([
                'https://www.kitco.com/rss/KitcoNews.xml',  # 贵金属专业新闻
                'https://www.mining.com/feed/',  # 矿业新闻
                'https://seekingalpha.com/feed.xml',  # 投资分析
                'https://finance.yahoo.com/news/rssindex' # Yahoo Finance
            ]))
            logger.info("✓ RSS Feeds initialized")
        except Exception as e:
            logger.warning(f"RSS init failed: {e}")
        
        # 3. Reddit (免费,但需注册应用)
        reddit_client = os.getenv('REDDIT_CLIENT_ID')
        if reddit_client:
            try:
                from .sources.reddit_source import RedditNewsSource
                self.sources.append(RedditNewsSource())
                logger.info("✓ Reddit initialized")
            except Exception as e:
                logger.warning(f"Reddit init failed: {e}")
    
    def fetch_all_news(self, keywords: List[str] = None) -> List[Dict]:
        """从所有源获取新闻"""
        if keywords is None:
            keywords = ['gold', 'silver', 'precious metals', 'mining', 'XAU', 'XAG']
        
        all_news = []
        
        for source in self.sources:
            try:
                news = source.fetch(keywords=keywords)
                all_news.extend(news)
                logger.info(f"✓ Fetched {len(news)} articles from {source.name}")
            except Exception as e:
                logger.warning(f"Failed to fetch from {source.name}: {e}")
        
        # 去重并按时间排序
        unique_news = self._deduplicate(all_news)
        unique_news.sort(key=lambda x: x['published_at'], reverse=True)
        
        return unique_news
    
    def _deduplicate(self, news_list: List[Dict]) -> List[Dict]:
        """智能去重 - 基于标题相似度"""
        if not news_list:
            return []
            
        if len(news_list) < 2:
            return news_list
        
        try:
            # 提取所有标题
            titles = [item['title'] for item in news_list]
            
            # 计算TF-IDF向量
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(titles)
            
            # 计算相似度矩阵
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # 保留不相似的文章
            unique_indices = []
            seen = set()
            
            for i in range(len(news_list)):
                if i in seen:
                    continue
                
                unique_indices.append(i)
                
                # 标记所有与当前文章相似的文章 (相似度 > 0.8)
                similar = np.where(similarity_matrix[i] > 0.8)[0]
                # Exclude self
                similar = [idx for idx in similar if idx != i]
                seen.update(similar)
            
            return [news_list[i] for i in unique_indices]
            
        except Exception as e:
            logger.error(f"Deduplication failed: {e}")
            # Fallback to simple URL deduplication
            seen_urls = set()
            unique = []
            for news in news_list:
                if news['url'] not in seen_urls:
                    unique.append(news)
                    seen_urls.add(news['url'])
            return unique
