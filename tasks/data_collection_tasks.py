"""
数据采集异步任务
"""
from celery_app import celery_app
from celery.utils.log import get_task_logger
import asyncio
from datetime import datetime

# 导入数据采集客户端
from DataCollector.StockDataCollector.yfinance_client import YFinanceStockClient
from DataCollector.StockDataCollector.yahoo_news_scraper import scrape_sync

logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=3)
def update_stock_prices(self):
    """更新所有监控股票的价格"""
    try:
        logger.info("Starting stock price update task")
        client = YFinanceStockClient()
        
        # 获取所有监控代码
        symbols = client.all_symbols
        
        # 批量获取价格
        prices = client.get_all_current_prices(symbols)
        
        # TODO: 保存到数据库
        # save_prices_to_db(prices)
        
        logger.info(f"Updated prices for {len(prices)} stocks")
        return {"status": "success", "count": len(prices)}
        
    except Exception as e:
        logger.error(f"Error updating stock prices: {e}")
        # 指数退避重试
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

@celery_app.task(bind=True)
def fetch_stock_news(self, symbol: str, max_items: int = 10):
    """抓取特定股票的新闻"""
    try:
        logger.info(f"Fetching news for {symbol}")
        
        # 使用同步包装器调用爬虫
        news_items = scrape_sync(symbol, max_items=max_items)
        
        # TODO: 保存到数据库和向量库
        # save_news_to_db(news_items)
        # add_news_to_vector_db(news_items)
        
        logger.info(f"Fetched {len(news_items)} news items for {symbol}")
        return {"status": "success", "symbol": symbol, "count": len(news_items)}
        
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        raise self.retry(exc=e, countdown=300)

@celery_app.task
def batch_fetch_news(symbols: list):
    """批量抓取新闻"""
    for symbol in symbols:
        fetch_stock_news.delay(symbol)
    return {"status": "queued", "count": len(symbols)}
