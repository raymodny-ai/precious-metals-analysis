"""
综合测试套件
测试PreciousInsight系统的所有核心组件
"""
import unittest
import sys
import os
import logging
from unittest.mock import MagicMock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestSystemComponents(unittest.TestCase):
    """系统组件测试"""

    def setUp(self):
        logger.info(f"Starting test: {self._testMethodName}")

    def test_01_stock_data_collector(self):
        """测试股票数据采集模块"""
        try:
            from DataCollector.StockDataCollector.yfinance_client import YFinanceStockClient
            
            # Mock yfinance
            with patch('yfinance.Ticker') as mock_ticker:
                mock_ticker.return_value.info = {
                    'currentPrice': 2000.0,
                    'marketCap': 10000000000,
                    'volume': 5000000
                }
                
                client = YFinanceStockClient()
                price = client.get_current_price('GLD')
                
                self.assertIsNotNone(price)
                self.assertEqual(price['symbol'], 'GLD')
                logger.info("StockDataCollector test passed")
        except ImportError as e:
            self.fail(f"Failed to import StockDataCollector: {e}")
        except Exception as e:
            self.fail(f"StockDataCollector test failed: {e}")

    def test_02_llm_service(self):
        """测试LLM服务模块"""
        try:
            from AnalysisEngine.LLMService.llm_service import LLMService
            from AnalysisEngine.LLMService.base import LLMRequest, TaskType, LLMResponse, LLMProvider
            
            # Mock adapters
            with patch('AnalysisEngine.LLMService.adapters.openai_adapter.OpenAIAdapter') as mock_adapter:
                mock_instance = mock_adapter.return_value
                mock_instance.complete_sync.return_value = LLMResponse(
                    content="Test response",
                    provider=LLMProvider.OPENAI,
                    model="gpt-4o-mini",
                    tokens_used=10,
                    cost=0.001,
                    latency=0.5
                )
                
                service = LLMService(enable_cache=False)
                # Inject mock adapter
                service.adapters[LLMProvider.OPENAI] = mock_instance
                
                response = service.summarize("Test text")
                self.assertEqual(response, "Test response")
                logger.info("LLMService test passed")
        except ImportError as e:
            self.fail(f"Failed to import LLMService: {e}")
        except Exception as e:
            self.fail(f"LLMService test failed: {e}")

    def test_03_rag_system(self):
        """测试RAG系统"""
        try:
            from AnalysisEngine.LLMService.rag_system import RAGSystem
            
            # Mock chromadb
            with patch('chromadb.PersistentClient') as mock_client:
                rag = RAGSystem()
                # Mock collections
                rag.reports_collection = MagicMock()
                rag.news_collection = MagicMock()
                rag.knowledge_collection = MagicMock()
                rag.enabled = True
                
                rag.add_knowledge("Test Topic", "Test Content")
                rag.knowledge_collection.add.assert_called_once()
                logger.info("RAGSystem test passed")
        except ImportError as e:
            self.fail(f"Failed to import RAGSystem: {e}")
        except Exception as e:
            self.fail(f"RAGSystem test failed: {e}")

    def test_04_alert_manager(self):
        """测试预警管理器"""
        try:
            from NotificationSystem.stock_alert_manager import StockAlertManager, PriceBreakoutRule
            
            manager = StockAlertManager()
            rule = PriceBreakoutRule('test_rule', 'GLD', 2000.0)
            manager.add_rule(rule)
            
            self.assertEqual(len(manager.rules), 1)
            self.assertEqual(manager.rules[0].rule_id, 'test_rule')
            logger.info("AlertManager test passed")
        except ImportError as e:
            self.fail(f"Failed to import AlertManager: {e}")
        except Exception as e:
            self.fail(f"AlertManager test failed: {e}")

    def test_05_api_extensions(self):
        """测试API扩展"""
        try:
            from flask import Flask
            from api_extensions import register_extended_apis
            
            app = Flask(__name__)
            register_extended_apis(app)
            
            # Check if blueprints are registered
            self.assertIn('stocks', app.blueprints)
            self.assertIn('llm', app.blueprints)
            self.assertIn('correlation', app.blueprints)
            logger.info("API Extensions test passed")
        except ImportError as e:
            self.fail(f"Failed to import API Extensions: {e}")
        except Exception as e:
            self.fail(f"API Extensions test failed: {e}")

    def test_06_alpha_vantage(self):
        """测试Alpha Vantage客户端"""
        try:
            from DataCollector.StockDataCollector.alpha_vantage_client import AlphaVantageClient
            
            client = AlphaVantageClient("demo")
            self.assertIsNotNone(client)
            logger.info("AlphaVantageClient test passed")
        except ImportError as e:
            self.fail(f"Failed to import AlphaVantageClient: {e}")

    def test_07_cost_tracker(self):
        """测试成本追踪器"""
        try:
            from AnalysisEngine.LLMService.cost_tracker import CostTracker
            
            # Use in-memory DB for testing
            tracker = CostTracker(":memory:")
            tracker.log_call("openai", "gpt-4", "test", 10, 10, 20, 0.01, 0.5)
            
            daily_cost = tracker.get_daily_cost()
            self.assertEqual(daily_cost, 0.01)
            logger.info("CostTracker test passed")
        except ImportError as e:
            self.fail(f"Failed to import CostTracker: {e}")
        except Exception as e:
            self.fail(f"CostTracker test failed: {e}")

if __name__ == '__main__':
    unittest.main()
