"""
Yahoo Finance 新闻爬虫
使用 Playwright 进行动态网页爬取
"""
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import re
import random

logger = logging.getLogger(__name__)

class YahooNewsScraper:
    """Yahoo Finance 新闻爬虫"""
    
    BASE_URL = "https://finance.yahoo.com/quote/{}/news"
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    
    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.playwright = None
        self.browser = None
        self.context = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def initialize(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        
        # 启动浏览器
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # 创建上下文
        context_options = {
            'user_agent': random.choice(self.USER_AGENTS),
            'viewport': {'width': 1920, 'height': 1080},
            'locale': 'en-US',
            'timezone_id': 'America/New_York'
        }
        
        if self.proxy:
            context_options['proxy'] = {'server': self.proxy}
        
        self.context = await self.browser.new_context(**context_options)
        
        # 添加stealth脚本
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        logger.info("Playwright browser initialized")
    
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright browser closed")
    
    async def scrape_stock_news(self, symbol: str, max_items: int = 20) -> List[Dict]:
        """
        爬取指定股票的新闻
        
        Args:
            symbol: 股票代码
            max_items: 最大新闻数量
        
        Returns:
            新闻列表
        """
        url = self.BASE_URL.format(symbol)
        
        page = await self.context.new_page()
        
        # 拦截不必要的资源以提高速度
        await page.route('**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}', 
                        lambda route: route.abort())
        
        try:
            # 访问页面
            logger.info(f"Scraping news for {symbol} from {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # 等待新闻列表加载
            try:
                await page.wait_for_selector('li[class*="stream-item"]', timeout=10000)
            except PlaywrightTimeout:
                logger.warning(f"News list not found for {symbol}, trying alternative selector")
                await page.wait_for_selector('article', timeout=10000)
            
            # 滚动加载更多内容
            for i in range(3):
                await page.evaluate('window.scrollBy(0, window.innerHeight)')
                await asyncio.sleep(1)
            
            # 获取页面内容
            content = await page.content()
            
            # 解析HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            news_items = []
            
            # 尝试多种选择器
            articles = soup.find_all('li', class_=re.compile('stream-item'))
            if not articles:
                articles = soup.find_all('article')
            
            logger.info(f"Found {len(articles)} article elements for {symbol}")
            
            for article in articles[:max_items]:
                try:
                    news_data = self._parse_article(article, symbol)
                    if news_data:
                        news_items.append(news_data)
                except Exception as e:
                    logger.warning(f"Error parsing article: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(news_items)} news items for {symbol}")
            return news_items
        
        except PlaywrightTimeout:
            logger.error(f"Timeout while scraping {symbol}")
            return []
        
        except Exception as e:
            logger.error(f"Error scraping {symbol}: {e}")
            return []
        
        finally:
            await page.close()
    
    def _parse_article(self, article_element, symbol: str) -> Optional[Dict]:
        """解析单个新闻元素"""
        try:
            # 提取标题和链接
            title_elem = article_element.find('h3')
            if not title_elem:
                title_elem = article_element.find('h2')
            
            if not title_elem:
                return None
            
            link_elem = title_elem.find('a')
            if not link_elem:
                link_elem = article_element.find('a')
            
            if not link_elem:
                return None
            
            title = link_elem.get_text(strip=True)
            url = link_elem.get('href', '')
            
            # 补全URL
            if url.startswith('/'):
                url = f"https://finance.yahoo.com{url}"
            elif not url.startswith('http'):
                return None
            
            # 提取摘要
            summary_elem = article_element.find('p')
            summary = summary_elem.get_text(strip=True) if summary_elem else ''
            
            # 提取来源
            source_elem = article_element.find('div', class_=re.compile('provider'))
            if not source_elem:
                source_elem = article_element.find('span', class_=re.compile('source'))
            source = source_elem.get_text(strip=True) if source_elem else 'Yahoo Finance'
            
            # 提取时间
            time_elem = article_element.find('time')
            published_at = None
            
            if time_elem and time_elem.get('datetime'):
                try:
                    published_at = datetime.fromisoformat(
                        time_elem['datetime'].replace('Z', '+00:00')
                    )
                except:
                    published_at = datetime.now()
            else:
                published_at = datetime.now()
            
            return {
                'symbol': symbol,
                'title': title,
                'summary': summary[:500] if summary else '',  # 限制摘要长度
                'url': url,
                'source': source,
                'published_at': published_at
            }
        
        except Exception as e:
            logger.debug(f"Error parsing article element: {e}")
            return None
    
    async def scrape_multiple_stocks(self, symbols: List[str], 
                                    max_items_per_stock: int = 10) -> Dict[str, List[Dict]]:
        """
        批量爬取多个股票的新闻
        
        Args:
            symbols: 股票代码列表
            max_items_per_stock: 每个股票最大新闻数
        
        Returns:
            字典，键为股票代码，值为新闻列表
        """
        results = {}
        
        for i, symbol in enumerate(symbols):
            try:
                logger.info(f"Scraping {i+1}/{len(symbols)}: {symbol}")
                news = await self.scrape_stock_news(symbol, max_items_per_stock)
                results[symbol] = news
                
                # 随机延迟，避免被检测
                if i < len(symbols) - 1:
                    delay = 2 + random.uniform(1, 3)
                    logger.info(f"Waiting {delay:.1f}s before next request...")
                    await asyncio.sleep(delay)
            
            except Exception as e:
                logger.error(f"Error scraping {symbol}: {e}")
                results[symbol] = []
        
        return results

# 同步包装器
def scrape_sync(symbol: str, max_items: int = 20, headless: bool = True) -> List[Dict]:
    """同步方式爬取新闻"""
    async def _scrape():
        async with YahooNewsScraper(headless=headless) as scraper:
            return await scraper.scrape_stock_news(symbol, max_items)
    
    return asyncio.run(_scrape())

# 使用示例
async def demo():
    """演示用法"""
    symbols = ['GLD', 'NEM', 'GOLD']
    
    async with YahooNewsScraper(headless=True) as scraper:
        results = await scraper.scrape_multiple_stocks(symbols, max_items_per_stock=5)
        
        for symbol, news_list in results.items():
            print(f"\n{symbol}: {len(news_list)} news items")
            for news in news_list[:2]:
                print(f"  - {news['title'][:60]}...")

if __name__ == '__main__':
    asyncio.run(demo())
