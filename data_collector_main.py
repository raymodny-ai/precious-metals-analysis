"""
数据采集层主控制器
协调运行所有数据采集模块
"""
import sys
import os
import time
import logging
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入采集器
from DataCollector.PriceDataCollector.metals_api_client import MetalsAPIClient
from DataCollector.USNewsCrawler.news_fetcher import NewsFetcher
from DataCollector.USNewsCrawler.sentiment_analyzer import SentimentAnalyzer
from DataCollector.SocialMediaCrawler.twitter_monitor import TwitterMonitor
from DataCollector.SocialMediaCrawler.reddit_monitor import RedditMonitor
from DataCollector.keyword_matcher import KeywordMatcher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataCollectorController:
    def __init__(self):
        self.price_client = MetalsAPIClient()
        self.news_fetcher = NewsFetcher()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.twitter_monitor = TwitterMonitor()
        self.reddit_monitor = RedditMonitor()
        self.keyword_matcher = KeywordMatcher()
        
    def collect_prices(self):
        """采集贵金属价格"""
        logger.info("开始采集价格数据...")
        try:
            data = self.price_client.get_latest_rates()
            if data and data.get('success'):
                logger.info(f"价格数据采集成功: {data.get('rates')}")
                return data
            else:
                logger.error(f"价格数据采集失败: {data}")
                return None
        except Exception as e:
            logger.error(f"价格采集异常: {e}")
            return None
    
    def collect_news(self):
        """采集并分析新闻"""
        logger.info("开始采集新闻数据...")
        try:
            # 采集新闻
            news_list = self.news_fetcher.fetch_news(ticker='GOLD.COMM', limit=10)
            logger.info(f"采集到 {len(news_list)} 条新闻")
            
            # 去重
            unique_news = self.news_fetcher.deduplicate(news_list)
            logger.info(f"去重后剩余 {len(unique_news)} 条新闻")
            
            # 关键词筛选和情感分析
            filtered_news = []
            for item in unique_news:
                title = item.get('title', '')
                content = item.get('content', '')
                
                # 关键词匹配
                if self.keyword_matcher.match(title + ' ' + content):
                    # 情感分析
                    sentiment = self.sentiment_analyzer.analyze(content)
                    item['sentiment'] = sentiment
                    filtered_news.append(item)
                    logger.info(f"新闻: {title[:50]}... | 情感: {sentiment.get('label')}")
            
            logger.info(f"筛选后剩余 {len(filtered_news)} 条相关新闻")
            return filtered_news
            
        except Exception as e:
            logger.error(f"新闻采集异常: {e}")
            return []
    
    def collect_social_media(self):
        """采集社交媒体数据"""
        logger.info("开始采集社交媒体数据...")
        results = {'twitter': [], 'reddit': []}
        
        # Twitter
        try:
            tweets = self.twitter_monitor.search_tweets(query='gold OR silver precious metals', max_results=10)
            logger.info(f"采集到 {len(tweets)} 条推文")
            results['twitter'] = tweets
        except Exception as e:
            logger.error(f"Twitter 采集异常: {e}")
        
        # Reddit
        try:
            posts = self.reddit_monitor.get_hot_posts(subreddit_name='Gold', limit=10)
            logger.info(f"采集到 {len(posts)} 条 Reddit 帖子")
            results['reddit'] = posts
        except Exception as e:
            logger.error(f"Reddit 采集异常: {e}")
        
        return results
    
    def run_once(self):
        """运行一次完整的数据采集"""
        logger.info("="*50)
        logger.info(f"开始数据采集 - {datetime.now()}")
        logger.info("="*50)
        
        # 1. 采集价格
        prices = self.collect_prices()
        
        # 2. 采集新闻
        news = self.collect_news()
        
        # 3. 采集社交媒体
        social = self.collect_social_media()
        
        logger.info("="*50)
        logger.info("数据采集完成")
        logger.info(f"价格数据: {'成功' if prices else '失败'}")
        logger.info(f"新闻数据: {len(news)} 条")
        logger.info(f"Twitter: {len(social.get('twitter', []))} 条")
        logger.info(f"Reddit: {len(social.get('reddit', []))} 条")
        logger.info("="*50)
        
        return {
            'prices': prices,
            'news': news,
            'social': social,
            'timestamp': datetime.now().isoformat()
        }
    
    def run_continuous(self, interval=300):
        """持续运行数据采集（默认5分钟间隔）"""
        logger.info(f"启动持续采集模式，间隔 {interval} 秒")
        while True:
            try:
                self.run_once()
                logger.info(f"等待 {interval} 秒后进行下一次采集...")
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("收到停止信号，退出采集")
                break
            except Exception as e:
                logger.error(f"采集过程异常: {e}")
                time.sleep(60)  # 出错后等待1分钟再试

def main():
    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)
    
    controller = DataCollectorController()
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        # 持续模式
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        controller.run_continuous(interval)
    else:
        # 单次运行
        result = controller.run_once()
        print("\n采集结果摘要:")
        print(f"- 价格数据: {'✓' if result['prices'] else '✗'}")
        print(f"- 新闻数据: {len(result['news'])} 条")
        print(f"- Twitter: {len(result['social']['twitter'])} 条")
        print(f"- Reddit: {len(result['social']['reddit'])} 条")

if __name__ == '__main__':
    main()
