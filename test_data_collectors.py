"""
数据采集层测试脚本
用于测试各个采集模块是否正常工作
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_price_collector():
    """测试价格采集"""
    print("\n" + "="*50)
    print("测试 1: 价格数据采集")
    print("="*50)
    
    from DataCollector.PriceDataCollector.metals_api_client import MetalsAPIClient
    
    client = MetalsAPIClient()
    data = client.get_latest_rates()
    
    if data and data.get('success'):
        print("✓ 价格数据采集成功")
        print(f"  汇率数据: {data.get('rates')}")
        return True
    else:
        print("✗ 价格数据采集失败")
        print(f"  错误信息: {data}")
        return False

def test_news_fetcher():
    """测试新闻采集"""
    print("\n" + "="*50)
    print("测试 2: 新闻数据采集")
    print("="*50)
    
    from DataCollector.USNewsCrawler.news_fetcher import NewsFetcher
    
    fetcher = NewsFetcher()
    news = fetcher.fetch_news(limit=5)
    
    if news:
        print(f"✓ 新闻采集成功，获取 {len(news)} 条")
        for i, item in enumerate(news[:2], 1):
            print(f"  {i}. {item.get('title', 'N/A')[:60]}...")
        
        # 测试去重
        unique = fetcher.deduplicate(news)
        print(f"  去重后: {len(unique)} 条")
        return True
    else:
        print("✗ 新闻采集失败")
        return False

def test_sentiment_analyzer():
    """测试情感分析"""
    print("\n" + "="*50)
    print("测试 3: 情感分析")
    print("="*50)
    
    from DataCollector.USNewsCrawler.sentiment_analyzer import SentimentAnalyzer
    
    analyzer = SentimentAnalyzer()
    
    test_texts = [
        "Gold prices surge to record highs on strong investor demand",
        "Silver market faces headwinds from stronger dollar",
        "Precious metals market remains stable"
    ]
    
    print("✓ 情感分析模块加载成功")
    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"  文本: {text[:50]}...")
        print(f"  结果: {result.get('label')} (置信度: {result.get('score', 0):.2f})")
    
    return True

def test_keyword_matcher():
    """测试关键词匹配"""
    print("\n" + "="*50)
    print("测试 4: 关键词匹配")
    print("="*50)
    
    from DataCollector.keyword_matcher import KeywordMatcher
    
    matcher = KeywordMatcher()
    
    test_cases = [
        ("Gold price surge on inflation fears", True),
        ("Silver wedding anniversary party", False),
        ("Gold mining production increases", True),
        ("Pokemon gold edition game", False),
    ]
    
    print(f"✓ 关键词匹配器加载成功")
    print(f"  普通词: {len(matcher.general_words)} 个")
    print(f"  必须词: {len(matcher.must_words)} 个")
    print(f"  过滤词: {len(matcher.filter_words)} 个")
    
    all_passed = True
    for text, expected in test_cases:
        result = matcher.match(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{text[:40]}...' => {result}")
        if result != expected:
            all_passed = False
    
    return all_passed

def test_twitter_monitor():
    """测试 Twitter 监控"""
    print("\n" + "="*50)
    print("测试 5: Twitter 监控")
    print("="*50)
    
    from DataCollector.SocialMediaCrawler.twitter_monitor import TwitterMonitor
    
    monitor = TwitterMonitor()
    
    if not monitor.client:
        print("⚠ Twitter API 未配置（需要 TWITTER_BEARER_TOKEN）")
        return False
    
    tweets = monitor.search_tweets(query="gold", max_results=5)
    
    if tweets:
        print(f"✓ Twitter 采集成功，获取 {len(tweets)} 条推文")
        for i, tweet in enumerate(tweets[:2], 1):
            print(f"  {i}. {tweet.text[:60]}...")
        return True
    else:
        print("⚠ 未获取到推文")
        return False

def test_reddit_monitor():
    """测试 Reddit 监控"""
    print("\n" + "="*50)
    print("测试 6: Reddit 监控")
    print("="*50)
    
    from DataCollector.SocialMediaCrawler.reddit_monitor import RedditMonitor
    
    monitor = RedditMonitor()
    
    if not monitor.reddit:
        print("⚠ Reddit API 未配置（需要 REDDIT_CLIENT_ID 和 REDDIT_CLIENT_SECRET）")
        return False
    
    posts = monitor.get_hot_posts(subreddit_name='Gold', limit=5)
    
    if posts:
        print(f"✓ Reddit 采集成功，获取 {len(posts)} 条帖子")
        for i, post in enumerate(posts[:2], 1):
            print(f"  {i}. {post['title'][:60]}... (评分: {post['score']})")
        return True
    else:
        print("⚠ 未获取到帖子")
        return False

def main():
    print("开始测试数据采集层...")
    print("请确保已配置必要的 API 密钥（.env 文件）")
    
    results = {}
    
    # 运行所有测试
    results['价格采集'] = test_price_collector()
    results['新闻采集'] = test_news_fetcher()
    results['情感分析'] = test_sentiment_analyzer()
    results['关键词匹配'] = test_keyword_matcher()
    results['Twitter监控'] = test_twitter_monitor()
    results['Reddit监控'] = test_reddit_monitor()
    
    # 汇总结果
    print("\n" + "="*50)
    print("测试结果汇总")
    print("="*50)
    
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！数据采集层工作正常。")
    else:
        print("\n⚠️  部分测试失败，请检查配置和 API 密钥。")

if __name__ == '__main__':
    main()
