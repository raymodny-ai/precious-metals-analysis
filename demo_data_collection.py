"""
数据采集层演示脚本（简化版）
不需要所有 API 密钥即可运行基本功能演示
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("PreciousInsight 数据采集层演示")
print("="*60)

# 1. 测试关键词匹配（无需API）
print("\n【模块 1】关键词匹配系统")
print("-"*60)
from DataCollector.keyword_matcher import KeywordMatcher

matcher = KeywordMatcher()
print(f"✓ 关键词匹配器加载成功")
print(f"  - 普通关键词: {len(matcher.general_words)} 个")
print(f"  - 必须关键词: {len(matcher.must_words)} 个")
print(f"  - 过滤关键词: {len(matcher.filter_words)} 个")

test_cases = [
    "Gold price surge on inflation fears",
    "Silver wedding anniversary party",
    "Federal Reserve raises interest rates affecting gold",
    "Pokemon gold edition video game",
    "Barrick Gold reports strong earnings"
]

print("\n测试文本匹配:")
for text in test_cases:
    result = matcher.match(text)
    icon = "✓" if result else "✗"
    print(f"  {icon} {text}")

# 2. 测试价格采集（需要 Metals-API key）
print("\n【模块 2】贵金属价格采集")
print("-"*60)
from DataCollector.PriceDataCollector.metals_api_client import MetalsAPIClient

client = MetalsAPIClient()
api_key = os.getenv('METALS_API_KEY')

if api_key and api_key != 'your_key_here':
    print("✓ API 密钥已配置，尝试获取实时价格...")
    data = client.get_latest_rates()
    if data and data.get('success'):
        rates = data.get('rates', {})
        print(f"  当前汇率:")
        for metal, rate in rates.items():
            price = 1 / rate if rate else 0
            print(f"  - {metal}: ${price:.2f}/oz")
    else:
        print(f"  ✗ 采集失败: {data}")
else:
    print("⚠ 未配置 METALS_API_KEY")
    print("  示例: 如配置密钥，将显示实时价格")
    print("  - XAU (黄金): $2,050.00/oz")
    print("  - XAG (白银): $24.50/oz")
    print("  - XPT (铂金): $950.00/oz")
    print("  - XPD (钯金): $1,100.00/oz")

# 3. 测试新闻采集（不需要API也能演示结构）
print("\n【模块 3】新闻数据采集")
print("-"*60)
from DataCollector.USNewsCrawler.news_fetcher import NewsFetcher

fetcher = NewsFetcher()
api_key = os.getenv('FINANCIAL_DATASETS_API_KEY')

if api_key and api_key != 'your_key_here':
    print("✓ API 密钥已配置，尝试获取新闻...")
    news = fetcher.fetch_news(limit=3)
    if news:
        print(f"  采集到 {len(news)} 条新闻:")
        for i, item in enumerate(news, 1):
            print(f"  {i}. {item.get('title', 'N/A')[:50]}...")
    else:
        print("  ⚠ 暂无新闻数据")
else:
    print("⚠ 未配置 FINANCIAL_DATASETS_API_KEY")
    print("  示例: 如配置密钥，将显示实时财经新闻")
    print("  1. Gold prices surge on Federal Reserve policy...")
    print("  2. Silver market shows strong momentum amid...")
    print("  3. Mining sector outlook remains positive...")

# 4. 测试社交媒体监控
print("\n【模块 4】社交媒体监控")
print("-"*60)

# Twitter
from DataCollector.SocialMediaCrawler.twitter_monitor import TwitterMonitor
twitter = TwitterMonitor()

if twitter.client:
    print("✓ Twitter API 已配置")
    tweets = twitter.search_tweets(query="gold OR silver", max_results=3)
    if tweets:
        print(f" 采集到 {len(tweets)} 条推文")
    else:
        print("  暂无推文数据")
else:
    print("⚠ Twitter API 未配置")
    print("  需要: TWITTER_BEARER_TOKEN")

# Reddit
from DataCollector.SocialMediaCrawler.reddit_monitor import RedditMonitor
reddit = RedditMonitor()

if reddit.reddit:
    print("✓ Reddit API 已配置")
    posts = reddit.get_hot_posts('Gold', limit=3)
    if posts:
        print(f"  采集到 {len(posts)} 条帖子")
    else:
        print("  暂无帖子数据")
else:
    print("⚠ Reddit API 未配置")
    print("  需要: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET")

# 5. 演示数据采集工作流
print("\n【完整工作流演示】")
print("-"*60)
print("数据采集流程:")
print("1. ✓ 从 Metals-API 获取实时价格")
print("2. ✓ 从 EODHD 采集美国财经新闻")
print("3. ✓ 使用关键词匹配器筛选相关新闻")
print("4. ✓ 使用 FinBERT 进行情感分析")
print("5. ✓ 从 Twitter/Reddit 采集社交媒体数据")
print("6. ✓ 存储到 MySQL 数据库")

print("\n数据采集层已就绪！")
print("\n下一步:")
print("1. 配置 API 密钥（编辑 .env 文件）")
print("2. 运行: python data_collector_main.py")
print("3. 或持续采集: python data_collector_main.py --continuous 300")

print("\n详细指南请查看: QUICKSTART_DATA_COLLECTION.md")
print("="*60)
