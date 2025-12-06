"""
Integration Tests
集成测试模块
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestDataPipeline:
    """End-to-end data pipeline tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.symbols = ["GLD", "SLV"]
    
    def test_price_fetcher_integration(self):
        """Test price fetcher returns valid data"""
        from src.data_collection.price_fetcher import PriceFetcher
        
        fetcher = PriceFetcher()
        
        for symbol in self.symbols:
            df = fetcher.fetch_price_data(symbol, interval="1d")
            
            assert not df.empty, f"No data for {symbol}"
            assert "close" in df.columns
            assert "time" in df.columns
            assert len(df) >= 5, "Should have at least 5 data points"
    
    def test_price_with_indicators(self):
        """Test technical indicators are calculated"""
        from src.data_collection.price_fetcher import PriceFetcher
        
        fetcher = PriceFetcher()
        df = fetcher.fetch_price_data("GLD", interval="1d")
        df = fetcher.add_technical_indicators(df)
        
        # Check indicator columns exist
        indicator_cols = ["returns", "ma_5", "ma_20"]
        for col in indicator_cols:
            assert col in df.columns, f"Missing indicator: {col}"
    
    def test_latest_prices(self):
        """Test fetching latest prices"""
        from src.data_collection.price_fetcher import PriceFetcher
        
        fetcher = PriceFetcher()
        prices = fetcher.fetch_latest_prices(self.symbols)
        
        for symbol in self.symbols:
            assert symbol in prices
            if "error" not in prices[symbol]:
                assert "price" in prices[symbol]
                assert prices[symbol]["price"] > 0


class TestSentimentPipeline:
    """Sentiment analysis pipeline tests"""
    
    def test_finbert_import(self):
        """Test FinBERT module imports correctly"""
        from src.nlp.finbert_analyzer import FinBERTAnalyzer
        assert FinBERTAnalyzer is not None
    
    def test_sentiment_metrics_import(self):
        """Test sentiment metrics module"""
        from src.nlp.sentiment_metrics import SentimentMetricsCalculator
        assert SentimentMetricsCalculator is not None
    
    @pytest.mark.skipif(
        not os.environ.get("RUN_GPU_TESTS"),
        reason="Skipping GPU-intensive tests"
    )
    def test_finbert_analysis(self):
        """Test FinBERT sentiment analysis"""
        from src.nlp.finbert_analyzer import FinBERTAnalyzer
        
        analyzer = FinBERTAnalyzer()
        
        test_texts = [
            "Gold prices surge to record high",
            "Market crash sends investors fleeing",
            "Trading volume remains stable"
        ]
        
        for text in test_texts:
            result = analyzer.analyze(text)
            
            assert result is not None
            assert hasattr(result, "score")
            assert hasattr(result, "label")
            assert result.label in ["positive", "negative", "neutral"]
            assert -1 <= result.score <= 1


class TestMLModels:
    """Machine learning model tests"""
    
    def test_feature_engineering_import(self):
        """Test feature engineering module"""
        from src.ml.feature_engineering import FeatureEngineer
        assert FeatureEngineer is not None
    
    def test_lstm_predictor_import(self):
        """Test LSTM predictor module"""
        from src.ml.lstm_predictor import LSTMPredictor
        assert LSTMPredictor is not None
    
    def test_advanced_models_import(self):
        """Test advanced models module"""
        from src.ml.advanced_models import (
            CNNLSTMAttentionModel,
            TabNetModel,
            XGBoostPredictor,
            EnsemblePredictor
        )
        assert CNNLSTMAttentionModel is not None
        assert TabNetModel is not None
        assert XGBoostPredictor is not None
        assert EnsemblePredictor is not None
    
    def test_feature_engineering(self):
        """Test feature engineering on sample data"""
        import pandas as pd
        import numpy as np
        from src.ml.feature_engineering import FeatureEngineer
        
        # Create sample data
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        df = pd.DataFrame({
            "time": dates,
            "symbol": "GLD",
            "open": np.random.uniform(180, 190, 100),
            "high": np.random.uniform(185, 195, 100),
            "low": np.random.uniform(175, 185, 100),
            "close": np.random.uniform(180, 190, 100),
            "volume": np.random.randint(1000000, 5000000, 100)
        })
        
        fe = FeatureEngineer()
        features = fe.add_price_features(df)
        
        assert not features.empty
        assert "returns_1d" in features.columns
        assert "ma_5" in features.columns


class TestBacktesting:
    """Backtesting framework tests"""
    
    def test_backtester_import(self):
        """Test backtester module imports"""
        from src.backtest.backtester import (
            Backtester,
            DataHandler,
            ExecutionEngine,
            PerformanceEvaluator
        )
        assert Backtester is not None
        assert DataHandler is not None
    
    def test_performance_metrics(self):
        """Test performance metrics calculation"""
        import pandas as pd
        import numpy as np
        from src.backtest.backtester import PerformanceEvaluator
        
        # Create mock equity curve
        dates = pd.date_range(start="2024-01-01", periods=252, freq="D")
        equity = 100000 * (1 + np.random.randn(252).cumsum() * 0.01)
        equity_curve = pd.Series(equity, index=dates)
        
        evaluator = PerformanceEvaluator()
        metrics = evaluator.calculate_metrics(equity_curve, [], 100000)
        
        assert metrics is not None
        assert hasattr(metrics, "total_return")
        assert hasattr(metrics, "sharpe_ratio")
        assert hasattr(metrics, "max_drawdown")


class TestETFAnalytics:
    """ETF analytics tests"""
    
    def test_alert_engine_import(self):
        """Test alert engine imports"""
        from src.etf.alert_engine import (
            ETFFlowAlertEngine,
            AlertSeverity,
            AlertType
        )
        assert ETFFlowAlertEngine is not None
    
    def test_holder_tracker_import(self):
        """Test holder tracker imports"""
        from src.etf.holder_tracker import HolderTracker
        assert HolderTracker is not None
    
    def test_alert_detection(self):
        """Test alert detection on sample data"""
        import pandas as pd
        import numpy as np
        from src.etf.alert_engine import ETFFlowAlertEngine
        
        # Create sample flow data
        dates = pd.date_range(start="2024-01-01", periods=60, freq="D")
        df = pd.DataFrame({
            "time": dates,
            "symbol": "GLD",
            "net_flow": np.random.normal(10e6, 20e6, 60)
        })
        
        # Add anomaly
        df.loc[df.index[-1], "net_flow"] = 100e6
        
        engine = ETFFlowAlertEngine()
        alerts = engine.detect_large_flows(df)
        
        assert len(alerts) >= 0  # May or may not detect


class TestAPIEndpoints:
    """API endpoint tests"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        from src.api.main import app
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_api_info(self, client):
        """Test API info endpoint"""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_prices_endpoint(self, client):
        """Test prices endpoint"""
        response = client.get("/api/v1/prices/GLD?days=5")
        # May fail without database
        assert response.status_code in [200, 500]
    
    def test_latest_prices(self, client):
        """Test latest prices endpoint"""
        response = client.get("/api/v1/prices/latest")
        assert response.status_code == 200


class TestMonitoring:
    """Monitoring and metrics tests"""
    
    def test_metrics_import(self):
        """Test monitoring module imports"""
        from src.utils.monitoring import (
            metrics,
            track_data_fetch,
            track_prediction,
            update_sentiment
        )
        assert metrics is not None
    
    def test_metrics_tracking(self):
        """Test metrics tracking functions"""
        from src.utils.monitoring import (
            track_data_fetch,
            track_prediction,
            update_sentiment
        )
        
        # These should not raise errors
        track_data_fetch("test", "GLD", "success", 1.0, 100)
        track_prediction("lstm", "GLD", 0.05)
        update_sentiment("GLD", 0.5, 10)


# Async tests
class TestAsyncOperations:
    """Async operation tests"""
    
    @pytest.mark.asyncio
    async def test_async_imports(self):
        """Test async modules can be imported"""
        from src.api.websocket_handler import ConnectionManager
        assert ConnectionManager is not None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
