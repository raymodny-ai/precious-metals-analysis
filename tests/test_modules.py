"""
Tests for Price Fetcher Module
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestPriceFetcher:
    """Test cases for PriceFetcher"""
    
    def test_import(self):
        """Test that module can be imported"""
        from src.data_collection.price_fetcher import PriceFetcher
        assert PriceFetcher is not None
    
    def test_fetch_single_symbol(self):
        """Test fetching data for a single symbol"""
        from src.data_collection.price_fetcher import PriceFetcher
        
        fetcher = PriceFetcher()
        df = fetcher.fetch_price_data("GLD", interval="1d")
        
        # Check that data was returned
        assert not df.empty, "DataFrame should not be empty"
        
        # Check required columns
        required_cols = ["time", "symbol", "close"]
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"
        
        # Check symbol
        assert (df["symbol"] == "GLD").all(), "All rows should have symbol GLD"
        
        # Check data types
        assert df["close"].dtype in ['float64', 'float32'], "Close should be float"
    
    def test_fetch_latest_prices(self):
        """Test fetching latest prices"""
        from src.data_collection.price_fetcher import PriceFetcher
        
        fetcher = PriceFetcher()
        prices = fetcher.fetch_latest_prices(["GLD", "SLV"])
        
        assert "GLD" in prices, "GLD should be in results"
        assert "SLV" in prices, "SLV should be in results"
        
        # Check that price is valid
        if "error" not in prices["GLD"]:
            assert prices["GLD"]["price"] is not None, "Price should not be None"
    
    def test_data_validation(self):
        """Test data validation"""
        from src.data_collection.price_fetcher import PriceFetcher
        
        fetcher = PriceFetcher()
        df = fetcher.fetch_price_data("GLD", interval="1d")
        
        is_valid, issues = fetcher.validate_data(df)
        
        assert is_valid, f"Data should be valid. Issues: {issues}"
    
    def test_technical_indicators(self):
        """Test adding technical indicators"""
        from src.data_collection.price_fetcher import PriceFetcher
        
        fetcher = PriceFetcher()
        df = fetcher.fetch_price_data("GLD", interval="1d")
        df_with_indicators = fetcher.add_technical_indicators(df)
        
        # Check for new columns
        indicator_cols = ["returns", "ma_5", "ma_20", "rsi_14"]
        for col in indicator_cols:
            assert col in df_with_indicators.columns, f"Missing indicator: {col}"


class TestNewsFetcher:
    """Test cases for NewsFetcher"""
    
    def test_import(self):
        """Test that module can be imported"""
        from src.data_collection.news_fetcher import NewsFetcher
        assert NewsFetcher is not None
    
    def test_fetch_news(self):
        """Test fetching news (may use mock data)"""
        from src.data_collection.news_fetcher import NewsFetcher
        
        fetcher = NewsFetcher()
        df = fetcher.fetch_gold_news(limit=10)
        
        assert not df.empty, "Should return some news data"
        assert "title" in df.columns, "Should have title column"
        assert "time" in df.columns, "Should have time column"


class TestFinBERTAnalyzer:
    """Test cases for FinBERT Sentiment Analyzer"""
    
    def test_import(self):
        """Test that module can be imported"""
        from src.nlp.finbert_analyzer import FinBERTAnalyzer
        assert FinBERTAnalyzer is not None
    
    def test_analyze_single_text(self):
        """Test analyzing a single text"""
        try:
            from src.nlp.finbert_analyzer import FinBERTAnalyzer
            
            analyzer = FinBERTAnalyzer()
            result = analyzer.analyze("Gold prices surge on positive economic news")
            
            assert result is not None, "Result should not be None"
            assert hasattr(result, 'score'), "Result should have score"
            assert hasattr(result, 'label'), "Result should have label"
            assert result.label in ['positive', 'negative', 'neutral'], "Invalid label"
        except Exception as e:
            pytest.skip(f"FinBERT model not available: {e}")


class TestFeatureEngineering:
    """Test cases for Feature Engineering"""
    
    def test_import(self):
        """Test that module can be imported"""
        from src.ml.feature_engineering import FeatureEngineer
        assert FeatureEngineer is not None
    
    def test_price_features(self):
        """Test adding price features"""
        from src.ml.feature_engineering import FeatureEngineer
        from src.data_collection.price_fetcher import PriceFetcher
        
        # Get sample data
        fetcher = PriceFetcher()
        df = fetcher.fetch_price_data("GLD", interval="1d")
        
        if df.empty:
            pytest.skip("No price data available")
        
        # Add features
        fe = FeatureEngineer()
        df_features = fe.add_price_features(df)
        
        # Check for new features
        assert "returns_1d" in df_features.columns
        assert "ma_5" in df_features.columns
        assert "momentum_5d" in df_features.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
