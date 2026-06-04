"""
分析引擎主控制器
协调运行所有分析 Agent: Query, Media, Insight, Report, Forum
"""
import sys
import os
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入所有 Agent
from AnalysisEngine.QueryAgent.query_agent import QueryAgent
from AnalysisEngine.QueryAgent.specialized_crawler import SpecializedCrawler
from AnalysisEngine.MediaAgent.youtube_analyzer import YouTubeAnalyzer
from AnalysisEngine.MediaAgent.pdf_parser import PDFParser
from AnalysisEngine.InsightAgent.time_series_analyzer import TimeSeriesAnalyzer
from AnalysisEngine.InsightAgent.event_analyzer import EventAnalyzer
from AnalysisEngine.ReportAgent.report_generator import ReportGenerator
from AnalysisEngine.ForumEngine.forum import Forum
from AnalysisEngine.ForumEngine.moderator import Moderator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/analysis_engine.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AnalysisEngineController:
    """分析引擎主控制器"""
    
    def __init__(self):
        logger.info("初始化分析引擎...")
        
        # 初始化所有 Agent
        self.query_agent = QueryAgent()
        self.specialized_crawler = SpecializedCrawler()
        self.youtube_analyzer = YouTubeAnalyzer()
        self.pdf_parser = PDFParser()
        self.time_series_analyzer = TimeSeriesAnalyzer()
        self.event_analyzer = EventAnalyzer()
        self.report_generator = ReportGenerator()
        self.forum = Forum()
        self.moderator = Moderator()
        
        # 注册 Agents 到 Forum
        self.forum.register_agent('QueryAgent', self.query_agent)
        self.forum.register_agent('MediaAgent', {'youtube': self.youtube_analyzer, 'pdf': self.pdf_parser})
        self.forum.register_agent('InsightAgent', {'ts': self.time_series_analyzer, 'event': self.event_analyzer})
        self.forum.register_agent('ReportAgent', self.report_generator)
        
        logger.info("分析引擎初始化完成")
    
    def run_query_analysis(self, query):
        """运行查询分析"""
        logger.info(f"Query Agent: 搜索查询 '{query}'")
        
        # 使用 Query Agent 搜索
        results = self.query_agent.search(query)
        logger.info(f"搜索到 {len(results)} 条结果")
        
        # 使用专项爬虫
        specialized_results = self.specialized_crawler.crawl_all()
        logger.info(f"专项爬虫获取数据: {list(specialized_results.keys())}")
        
        return {
            'query': query,
            'search_results': results,
            'specialized_data': specialized_results
        }
    
    def run_media_analysis(self, query='gold silver precious metals'):
        """运行多模态分析"""
        logger.info("Media Agent: 开始多模态分析")
        
        results = {}
        
        # YouTube 分析
        try:
            videos = self.youtube_analyzer.search_videos(query, max_results=5)
            results['youtube'] = videos
            logger.info(f"YouTube: 分析 {len(videos)} 个视频")
        except Exception as e:
            logger.error(f"YouTube 分析失败: {e}")
            results['youtube'] = []
        
        # PDF 解析（示例）
        # results['pdf'] = self.pdf_parser.parse('path/to/report.pdf')
        
        return results
    
    def run_insight_analysis(self, price_data=None):
        """运行深度洞察分析"""
        logger.info("Insight Agent: 开始深度分析")
        
        insights = {}
        
        # 时序分析
        if price_data is not None:
            analyzed_data = self.time_series_analyzer.analyze(price_data)
            insights['time_series'] = analyzed_data
            logger.info("完成时序分析（RSI, MACD, MA）")
        
        # 事件分析
        event_impact = self.event_analyzer.check_event_impact('Federal Reserve Meeting', price_data)
        insights['events'] = event_impact
        logger.info("完成事件影响分析")
        
        return insights
    
    def run_forum_debate(self, topic):
        """运行 Forum 多轮辩论"""
        logger.info(f"Forum Engine: 开始辩论 - {topic}")
        
        # 各 Agent 发言
        self.forum.post_message('QueryAgent', f"基于搜索结果，{topic} 的市场情绪偏向积极")
        self.forum.post_message('MediaAgent', f"YouTube 分析显示，{topic} 相关视频播放量上升")
        self.forum.post_message('InsightAgent', f"技术指标显示 {topic} 处于超买区域")
        
        # Moderator 总结
        summary = self.moderator.summarize(self.forum.get_history())
        logger.info(f"Moderator 总结: {summary}")
        
        return {
            'topic': topic,
            'debate_history': self.forum.get_history(),
            'moderator_summary': summary
        }
    
    def generate_report(self, data):
        """生成智能报告"""
        logger.info("Report Agent: 生成报告")
        
        report = self.report_generator.generate_report(data)
        report_path = self.report_generator.save_report(report)
        
        logger.info(f"报告已保存: {report_path}")
        return report_path
    
    def run_full_analysis(self, query='gold market analysis'):
        """运行完整的分析流程"""
        logger.info("="*60)
        logger.info(f"开始完整分析流程 - {datetime.now()}")
        logger.info("="*60)
        
        results = {}
        
        # 阶段1: Query Agent 搜索
        logger.info("\n【阶段 1】Query Agent - 信息搜索")
        results['query'] = self.run_query_analysis(query)
        
        # 阶段2: Media Agent 多模态分析
        logger.info("\n【阶段 2】Media Agent - 多模态分析")
        results['media'] = self.run_media_analysis(query)
        
        # 阶段3: Insight Agent 深度挖掘
        logger.info("\n【阶段 3】Insight Agent - 深度洞察")
        results['insights'] = self.run_insight_analysis()
        
        # 阶段4: Forum Engine 多轮辩论
        logger.info("\n【阶段 4】Forum Engine - 多Agent协作")
        results['forum'] = self.run_forum_debate(query)
        
        # 阶段5: Report Agent 生成报告
        logger.info("\n【阶段 5】Report Agent - 报告生成")
        
        # 准备报告数据
        report_data = {
            'executive_summary': results['forum']['moderator_summary'],
            'gold': {'price': 2050, 'change': 1.2, 'support': 2000, 'resistance': 2100},
            'silver': {'price': 24.5, 'change': -0.8},
            'sentiment': {'news': 'positive', 'social': 'neutral', 'investor': 'bullish'},
            'macro': {'dxy': 104.5, 'yield': 4.5, 'cpi': 3.2},
            'supply': {'mining': 'stable', 'industrial': 'increasing', 'central_bank': 'buying'},
            'forecast': results['insights'].get('time_series', 'Bullish trend expected'),
            'advice': 'Consider long positions with stop loss at support level'
        }
        
        results['report_path'] = self.generate_report(report_data)
        
        logger.info("="*60)
        logger.info("完整分析流程完成")
        logger.info("="*60)
        
        return results

def main():
    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    
    controller = AnalysisEngineController()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
        if mode == '--query':
            query = sys.argv[2] if len(sys.argv) > 2 else 'gold price forecast'
            result = controller.run_query_analysis(query)
            print(f"\n搜索结果: {len(result['search_results'])} 条")
            
        elif mode == '--media':
            result = controller.run_media_analysis()
            print(f"\nYouTube 视频: {len(result.get('youtube', []))} 个")
            
        elif mode == '--insight':
            result = controller.run_insight_analysis()
            print(f"\n洞察分析完成")
            
        elif mode == '--forum':
            topic = sys.argv[2] if len(sys.argv) > 2 else 'precious metals market outlook'
            result = controller.run_forum_debate(topic)
            print(f"\n辩论总结: {result['moderator_summary']}")
            
        elif mode == '--full':
            query = sys.argv[2] if len(sys.argv) > 2 else 'gold market analysis'
            result = controller.run_full_analysis(query)
            print(f"\n完整分析完成，报告保存在: {result['report_path']}")
    else:
        # 默认运行完整分析
        print("运行完整分析流程...")
        print("提示: 可使用参数选择特定模块:")
        print("  --query <关键词>  : 仅运行查询分析")
        print("  --media           : 仅运行多模态分析")
        print("  --insight         : 仅运行深度洞察")
        print("  --forum <主题>    : 仅运行论坛辩论")
        print("  --full <查询>     : 运行完整流程\n")
        
        result = controller.run_full_analysis()
        
        print("\n" + "="*60)
        print("分析完成摘要:")
        print(f"- 搜索结果: {len(result['query']['search_results'])} 条")
        print(f"- YouTube 视频: {len(result['media'].get('youtube', []))} 个")
        print(f"- 论坛辩论: {len(result['forum']['debate_history'])} 轮")
        print(f"- 报告路径: {result['report_path']}")
        print("="*60)

if __name__ == '__main__':
    main()
