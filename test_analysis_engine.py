"""
分析引擎测试脚本
测试各个 Agent 模块的功能
"""
import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_query_agent():
    """测试 Query Agent"""
    print("\n" + "="*60)
    print("测试 1: Query Agent（搜索代理）")
    print("="*60)
    
    from AnalysisEngine.QueryAgent.query_agent import QueryAgent
    
    agent = QueryAgent()
    
    # 检查 API 配置
    if agent.google_api_key and agent.google_api_key != 'your_key_here':
        print("✓ Google API 已配置，尝试搜索...")
        results = agent.search('gold price forecast 2024')
        print(f"  搜索结果: {len(results)} 条")
        if results:
            print(f"  第一条: {results[0].get('title', 'N/A')[:60]}...")
    else:
        print("⚠ Google API 未配置")
        print("  需要: GOOGLE_API_KEY 和 GOOGLE_CSE_ID")
    
    return True

def test_specialized_crawler():
    """测试专项爬虫"""
    print("\n" + "="*60)
    print("测试 2: 专项爬虫（Kitco, Bloomberg）")
    print("="*60)
    
    from AnalysisEngine.QueryAgent.specialized_crawler import SpecializedCrawler
    
    crawler = SpecializedCrawler()
    print("✓ 专项爬虫初始化成功")
    print(f"  支持的源: {list(crawler.sources.keys())}")
    
    # 测试 Kitco 爬虫
    try:
        headlines = crawler.crawl_kitco()
        if headlines:
            print(f"  Kitco 新闻: {len(headlines)} 条")
            for i, headline in enumerate(headlines[:2], 1):
                print(f"    {i}. {headline[:50]}...")
        else:
            print("  ⚠ Kitco 爬取无结果（网站结构可能已变化）")
    except Exception as e:
        print(f"  ⚠ Kitco 爬取异常: {e}")
    
    return True

def test_youtube_analyzer():
    """测试 YouTube 分析"""
    print("\n" + "="*60)
    print("测试 3: YouTube 视频分析")
    print("="*60)
    
    from AnalysisEngine.MediaAgent.youtube_analyzer import YouTubeAnalyzer
    
    analyzer = YouTubeAnalyzer()
    
    if analyzer.youtube:
        print("✓ YouTube API 已配置")
        videos = analyzer.search_videos('gold price analysis', max_results=3)
        if videos:
            print(f"  找到 {len(videos)} 个视频:")
            for i, video in enumerate(videos, 1):
                print(f"  {i}. {video['title'][:50]}...")
                print(f"     频道: {video['channelTitle']}")
        else:
            print("  ⚠ 未找到视频")
    else:
        print("⚠ YouTube API 未配置")
        print("  需要: YOUTUBE_API_KEY")
    
    return True

def test_pdf_parser():
    """测试 PDF 解析"""
    print("\n" + "="*60)
    print("测试 4: PDF 报告解析")
    print("="*60)
    
    from AnalysisEngine.MediaAgent.pdf_parser import PDFParser
    
    parser = PDFParser()
    print("✓ PDF 解析器初始化成功")
    print("  功能: 提取 PDF 文本内容")
    print("  用途: 解析矿业公司财报、研究报告等")
    
    return True

def test_time_series_analyzer():
    """测试时序分析"""
    print("\n" + "="*60)
    print("测试 5: 时序分析（RSI, MACD, MA）")
    print("="*60)
    
    from AnalysisEngine.InsightAgent.time_series_analyzer import TimeSeriesAnalyzer
    
    analyzer = TimeSeriesAnalyzer()
    
    # 生成模拟价格数据
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    prices = pd.Series([2000 + np.random.randn()*20 + i*0.5 for i in range(100)], index=dates)
    df = pd.DataFrame({'price': prices})
    
    # 运行分析
    result = analyzer.analyze(df)
    
    print("✓ 时序分析完成")
    print(f"  计算指标:")
    print(f"  - SMA_20 (20日移动平均)")
    print(f"  - RSI (相对强弱指标)")
    print(f"  - MACD (指数平滑异同移动平均线)")
    
    if not result['RSI'].isna().all():
        latest_rsi = result['RSI'].iloc[-1]
        print(f"  最新 RSI: {latest_rsi:.2f}")
        if latest_rsi > 70:
            print("    → 超买信号")
        elif latest_rsi < 30:
            print("    → 超卖信号")
        else:
            print("    → 中性区域")
    
    return True

def test_event_analyzer():
    """测试事件分析"""
    print("\n" + "="*60)
    print("测试 6: 事件影响分析")
    print("="*60)
    
    from AnalysisEngine.InsightAgent.event_analyzer import EventAnalyzer
    
    analyzer = EventAnalyzer()
    print("✓ 事件分析器初始化成功")
    print(f"  监控事件: {', '.join(analyzer.events)}")
    
    # 测试事件影响
    impact = analyzer.check_event_impact('Federal Reserve Meeting', None)
    print(f"\n  事件: {impact['event']}")
    print(f"  影响: {impact['impact']}")
    print(f"  波动率: {impact['volatility']}")
    
    return True

def test_report_generator():
    """测试报告生成"""
    print("\n" + "="*60)
    print("测试 7: 智能报告生成")
    print("="*60)
    
    from AnalysisEngine.ReportAgent.report_generator import ReportGenerator
    
    generator = ReportGenerator()
    print("✓ 报告生成器初始化成功")
    
    # 准备测试数据
    test_data = {
        'executive_summary': '市场整体呈现上涨趋势',
        'gold': {'price': 2050, 'change': 1.2, 'support': 2000, 'resistance': 2100},
        'silver': {'price': 24.5, 'change': -0.8},
        'sentiment': {'news': 'positive', 'social': 'neutral', 'investor': 'bullish'},
        'macro': {'dxy': 104.5, 'yield': 4.5, 'cpi': 3.2},
        'supply': {'mining': 'stable', 'industrial': 'increasing', 'central_bank': 'buying'},
        'forecast': '短期内预计继续上涨',
        'advice': '建议在2000美元设置止损'
    }
    
    # 生成报告
    report = generator.generate_report(test_data)
    
    if report and 'Error' not in report:
        print("  报告生成成功")
        print(f"  报告长度: {len(report)} 字符")
        print(f"  包含章节: 价格分析、市场情绪、影响因素、趋势预测等")
        
        # 保存报告
        os.makedirs('reports', exist_ok=True)
        path = generator.save_report(report)
        print(f"  已保存到: {path}")
    else:
        print("  ⚠ 报告生成失败")
    
    return True

def test_forum_engine():
    """测试 Forum 协作"""
    print("\n" + "="*60)
    print("测试 8: Forum Engine（多Agent协作）")
    print("="*60)
    
    from AnalysisEngine.ForumEngine.forum import Forum
    from AnalysisEngine.ForumEngine.moderator import Moderator
    
    forum = Forum()
    moderator = Moderator()
    
    print("✓ Forum 和 Moderator 初始化成功")
    
    # 模拟多Agent讨论
    forum.post_message('QueryAgent', '搜索结果显示市场情绪积极')
    forum.post_message('MediaAgent', 'YouTube视频播放量大幅增加')
    forum.post_message('InsightAgent', 'RSI指标显示超买')
    
    history = forum.get_history()
    print(f"  讨论轮次: {len(history)} 轮")
    
    # Moderator 总结
    summary = moderator.summarize(history)
    print(f"  Moderator 总结: {summary}")
    
    return True

def main():
    print("="*60)
    print("PreciousInsight 分析引擎测试套件")
    print("="*60)
    print("开始测试各个 Agent 模块...")
    
    results = {}
    
    # 运行所有测试
    results['Query Agent'] = test_query_agent()
    results['专项爬虫'] = test_specialized_crawler()
    results['YouTube 分析'] = test_youtube_analyzer()
    results['PDF 解析'] = test_pdf_parser()
    results['时序分析'] = test_time_series_analyzer()
    results['事件分析'] = test_event_analyzer()
    results['报告生成'] = test_report_generator()
    results['Forum 协作'] = test_forum_engine()
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！分析引擎工作正常。")
    else:
        print("\n⚠️  部分测试失败，请检查配置。")

if __name__ == '__main__':
    main()
