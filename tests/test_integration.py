"""
PreciousInsight 综合测试套件
测试所有核心组件的功能和集成
"""
import unittest
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestDataCollectors(unittest.TestCase):
    """数据采集层测试"""
    
    def test_keyword_matcher(self):
        """测试关键词匹配器"""
        from DataCollector.keyword_matcher import KeywordMatcher
        
        matcher = KeywordMatcher()
        
        # 应该匹配
        self.assertTrue(matcher.match("Gold price surge on inflation fears"))
        self.assertTrue(matcher.match("Silver mining production increases"))
        
        # 不应该匹配
        self.assertFalse(matcher.match("Silver wedding anniversary party"))
        self.assertFalse(matcher.match("Pokemon gold edition game"))
    
    def test_metals_api_client(self):
        """测试金属API客户端"""
        from DataCollector.PriceDataCollector.metals_api_client import MetalsAPIClient
        
        client = MetalsAPIClient()
        self.assertIsNotNone(client.api_key)

class TestAnalysisEngine(unittest.TestCase):
    """分析引擎测试"""
    
    def test_time_series_analyzer(self):
        """测试时序分析器"""
        from AnalysisEngine.InsightAgent.time_series_analyzer import TimeSeriesAnalyzer
        import pandas as pd
        import numpy as np
        
        analyzer = TimeSeriesAnalyzer()
        
        # 生成测试数据
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices = pd.Series([2000 + i*0.5 + np.random.randn()*10 for i in range(100)], index=dates)
        df = pd.DataFrame({'price': prices})
        
        # 运行分析
        result = analyzer.analyze(df)
        
        # 验证指标存在
        self.assertIn('SMA_20', result.columns)
        self.assertIn('RSI', result.columns)
        self.assertIn('MACD', result.columns)
        self.assertIn('BB_Upper', result.columns)
        
        # 验证斐波那契水平
        self.assertIn('fibonacci_levels', result.attrs)
        fib = result.attrs['fibonacci_levels']
        self.assertIn('level_618', fib)
    
    def test_trading_signals(self):
        """测试交易信号生成"""
        from AnalysisEngine.InsightAgent.time_series_analyzer import TimeSeriesAnalyzer
        import pandas as pd
        import numpy as np
        
        analyzer = TimeSeriesAnalyzer()
        
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices = pd.Series([2000 + i*0.5 for i in range(100)], index=dates)
        df = pd.DataFrame({'price': prices})
        
        result = analyzer.analyze(df)
        signals = analyzer.get_trading_signals(result)
        
        # 验证信号存在
        self.assertIn('rsi_signal', signals)
        self.assertIn('macd_signal', signals)
        self.assertIn('bollinger_signal', signals)
    
    def test_report_generator(self):
        """测试报告生成器"""
        from AnalysisEngine.ReportAgent.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        
        test_data = {
            'executive_summary': '测试摘要',
            'gold': {'price': 2050, 'change': 1.2, 'support': 2000, 'resistance': 2100},
            'silver': {'price': 24.5, 'change': -0.8},
            'sentiment': {'news': 'positive', 'social': 'neutral', 'investor': 'bullish'},
            'macro': {'dxy': 104.5, 'yield': 4.5, 'cpi': 3.2},
            'supply': {'mining': 'stable', 'industrial': 'increasing', 'central_bank': 'buying'},
            'forecast': '预计上涨',
            'advice': '建议逢低买入'
        }
        
        report = generator.generate_report(test_data)
        
        self.assertIsNotNone(report)
        self.assertIn('贵金属', report)

class TestNotificationSystem(unittest.TestCase):
    """通知系统测试"""
    
    def test_notification_manager_init(self):
        """测试通知管理器初始化"""
        from NotificationSystem.notification_manager import NotificationManager
        
        manager = NotificationManager()
        self.assertIsNotNone(manager.email_notifier)
        self.assertIsNotNone(manager.telegram_notifier)
    
    def test_email_notifier_init(self):
        """测试邮件通知器初始化"""
        from NotificationSystem.email_notifier import EmailNotifier
        
        notifier = EmailNotifier()
        self.assertIsNotNone(notifier.smtp_server)

class TestMonitoring(unittest.TestCase):
    """监控系统测试"""
    
    def test_app_monitor(self):
        """测试应用监控器"""
        from Monitoring.app_monitor import ApplicationMonitor
        
        monitor = ApplicationMonitor()
        
        # 收集系统指标
        metrics = monitor.collect_system_metrics()
        self.assertIn('cpu_percent', metrics)
        self.assertIn('memory_percent', metrics)
        
        # 健康检查
        health = monitor.check_health()
        self.assertIn('status', health)
        self.assertIn('checks', health)
    
    def test_alert_manager(self):
        """测试告警管理器"""
        from Monitoring.app_monitor import AlertManager
        
        alert_manager = AlertManager()
        
        # 发送测试告警（不实际发送）
        alert_manager.send_alert('test_alert', 'Test message', 'info')
        
        # 验证告警历史
        self.assertTrue(len(alert_manager.alert_history) > 0)

class TestI18n(unittest.TestCase):
    """国际化测试"""
    
    def test_i18n_loading(self):
        """测试翻译加载"""
        from utils.i18n import i18n
        
        self.assertIn('en', i18n.translations)
        self.assertIn('zh', i18n.translations)
        self.assertIn('es', i18n.translations)
    
    def test_translations(self):
        """测试翻译功能"""
        from utils.i18n import t, set_language
        
        # 测试英语
        set_language('en')
        self.assertEqual(t('metrics.gold_price'), 'Gold Price')
        
        # 测试中文
        set_language('zh')
        self.assertEqual(t('metrics.gold_price'), '黄金价格')
        
        # 测试西班牙语
        set_language('es')
        self.assertEqual(t('metrics.gold_price'), 'Precio del Oro')

class TestMLPredictor(unittest.TestCase):
    """机器学习预测器测试"""
    
    def test_simple_ma_predictor(self):
        """测试简单移动平均预测器"""
        from AnalysisEngine.InsightAgent.ml_price_predictor import SimpleMovingAveragePredictor
        import pandas as pd
        import numpy as np
        
        predictor = SimpleMovingAveragePredictor(window=30)
        
        # 生成测试数据
        prices = pd.Series([2000 + i*0.5 + np.random.randn()*5 for i in range(100)])
        
        # 预测
        predictions = predictor.predict(prices, days_ahead=7)
        
        self.assertIsNotNone(predictions)
        self.assertEqual(len(predictions), 7)

class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_analysis_pipeline(self):
        """测试完整分析流程"""
        from AnalysisEngine.InsightAgent.time_series_analyzer import TimeSeriesAnalyzer
        from AnalysisEngine.InsightAgent.ml_price_predictor import SimpleMovingAveragePredictor
        from AnalysisEngine.ReportAgent.report_generator import ReportGenerator
        import pandas as pd
        import numpy as np
        
        # 生成测试数据
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices = pd.Series([2000 + i*0.5 + np.random.randn()*10 for i in range(100)], index=dates)
        df = pd.DataFrame({'price': prices})
        
        # 技术分析
        analyzer = TimeSeriesAnalyzer()
        df_analyzed = analyzer.analyze(df)
        signals = analyzer.get_trading_signals(df_analyzed)
        
        # 价格预测
        predictor = SimpleMovingAveragePredictor()
        future_prices = predictor.predict(df['price'], days_ahead=7)
        
        # 生成报告
        generator = ReportGenerator()
        report_data = {
            'executive_summary': signals.get('rsi_signal', 'N/A'),
            'gold': {'price': df['price'].iloc[-1], 'change': 1.2, 'support': 2000, 'resistance': 2100},
            'silver': {'price': 24.5, 'change': -0.8},
            'sentiment': {'news': 'positive', 'social': 'neutral', 'investor': 'bullish'},
            'macro': {'dxy': 104.5, 'yield': 4.5, 'cpi': 3.2},
            'supply': {'mining': 'stable', 'industrial': 'increasing', 'central_bank': 'buying'},
            'forecast': f"未来7天预测: ${future_prices[0]:.2f}",
            'advice': '建议关注支撑位'
        }
        report = generator.generate_report(report_data)
        
        # 验证流程完整性
        self.assertIsNotNone(df_analyzed)
        self.assertIsNotNone(signals)
        self.assertIsNotNone(future_prices)
        self.assertIsNotNone(report)

def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestDataCollectors))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalysisEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestNotificationSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestMonitoring))
    suite.addTests(loader.loadTestsFromTestCase(TestI18n))
    suite.addTests(loader.loadTestsFromTestCase(TestMLPredictor))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印摘要
    print("\n" + "="*70)
    print("测试摘要")
    print("="*70)
    print(f"运行测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
