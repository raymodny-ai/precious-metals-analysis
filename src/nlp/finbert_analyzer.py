"""
FinBERT Sentiment Analyzer
FinBERT情绪分析模块
Based on FinBERT_DeepSeek_Kimi2.md guide
"""

import torch
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import warnings

from ..utils.logger import setup_logging
from ..utils.config import get_settings

warnings.filterwarnings("ignore")

logger = setup_logging("finbert_analyzer")
settings = get_settings()


@dataclass
class SentimentResult:
    """Sentiment analysis result for a single text"""
    positive: float
    negative: float
    neutral: float
    score: float  # Composite score: positive - negative (-1 to +1)
    label: str    # 'positive', 'negative', 'neutral'
    confidence: float  # Max probability


class FinBERTAnalyzer:
    """
    FinBERT-based sentiment analyzer for financial news
    
    Features:
    - Batch processing for efficiency
    - GPU acceleration when available
    - Composite sentiment scoring
    - Configurable thresholds
    """
    
    # Default model - specialized for financial sentiment
    DEFAULT_MODEL = "ProsusAI/finbert"
    
    # Sentiment thresholds
    POSITIVE_THRESHOLD = 0.6
    NEGATIVE_THRESHOLD = 0.6
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: int = 16
    ):
        """
        Initialize FinBERT analyzer
        
        Args:
            model_name: HuggingFace model name (default: ProsusAI/finbert)
            device: 'cuda', 'cpu', or None (auto-detect)
            batch_size: Batch size for inference
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.batch_size = batch_size
        
        # Set device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        logger.info(f"Initializing FinBERT on {self.device}")
        
        # Load model and tokenizer
        self._load_model()
    
    def _load_model(self):
        """Load FinBERT model and tokenizer"""
        try:
            logger.info(f"Loading model: {self.model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name
            )
            
            # Move to device
            self.model = self.model.to(self.device)
            self.model.eval()
            
            # Get label mapping
            self.id2label = self.model.config.id2label
            self.label2id = self.model.config.label2id
            
            logger.info(f"Model loaded successfully. Labels: {self.id2label}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def analyze(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of a single text
        
        Args:
            text: Text to analyze
        
        Returns:
            SentimentResult with probabilities and composite score
        """
        results = self.analyze_batch([text])
        return results[0]
    
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """
        Analyze sentiment of multiple texts in batches
        
        Args:
            texts: List of texts to analyze
        
        Returns:
            List of SentimentResult objects
        """
        if not texts:
            return []
        
        all_results = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_results = self._process_batch(batch_texts)
            all_results.extend(batch_results)
        
        return all_results
    
    def _process_batch(self, texts: List[str]) -> List[SentimentResult]:
        """Process a single batch of texts"""
        
        # Clean texts
        cleaned_texts = [self._clean_text(t) for t in texts]
        
        # Tokenize
        inputs = self.tokenizer(
            cleaned_texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        
        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=-1)
        
        # Parse results
        results = []
        for probs in probabilities:
            result = self._parse_probabilities(probs.cpu().numpy())
            results.append(result)
        
        return results
    
    def _parse_probabilities(self, probs: np.ndarray) -> SentimentResult:
        """Parse model output probabilities into SentimentResult"""
        
        # Map probabilities to sentiment classes
        # FinBERT typically has labels: positive, negative, neutral
        sentiment_probs = {}
        
        for idx, label in self.id2label.items():
            label_lower = label.lower()
            sentiment_probs[label_lower] = float(probs[idx])
        
        # Extract probabilities
        positive = sentiment_probs.get("positive", 0.0)
        negative = sentiment_probs.get("negative", 0.0)
        neutral = sentiment_probs.get("neutral", 0.0)
        
        # Calculate composite score: positive - negative
        score = positive - negative
        
        # Determine label based on max probability
        max_prob = max(sentiment_probs.values())
        label = max(sentiment_probs, key=sentiment_probs.get)
        
        return SentimentResult(
            positive=positive,
            negative=negative,
            neutral=neutral,
            score=score,
            label=label,
            confidence=max_prob
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for analysis"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Truncate if too long (keep first 1000 chars)
        if len(text) > 1000:
            text = text[:1000] + "..."
        
        return text.strip()
    
    def analyze_dataframe(
        self,
        df: pd.DataFrame,
        text_column: str = "content",
        title_column: Optional[str] = "title"
    ) -> pd.DataFrame:
        """
        Analyze sentiment for a DataFrame of news articles
        
        Args:
            df: DataFrame with text data
            text_column: Column containing main text
            title_column: Column containing title (combined with text)
        
        Returns:
            DataFrame with added sentiment columns
        """
        df = df.copy()
        
        # Combine title and content for analysis
        texts = []
        for _, row in df.iterrows():
            text_parts = []
            
            if title_column and title_column in df.columns:
                title = row.get(title_column, "")
                if title:
                    text_parts.append(str(title))
            
            if text_column in df.columns:
                content = row.get(text_column, "")
                if content:
                    text_parts.append(str(content))
            
            texts.append(" ".join(text_parts))
        
        logger.info(f"Analyzing sentiment for {len(texts)} texts...")
        
        # Analyze
        results = self.analyze_batch(texts)
        
        # Add results to DataFrame
        df["sentiment_positive"] = [r.positive for r in results]
        df["sentiment_negative"] = [r.negative for r in results]
        df["sentiment_neutral"] = [r.neutral for r in results]
        df["sentiment_score"] = [r.score for r in results]
        df["sentiment_label"] = [r.label for r in results]
        df["sentiment_confidence"] = [r.confidence for r in results]
        df["processed"] = True
        
        logger.info("Sentiment analysis complete")
        
        return df
    
    def get_sentiment_summary(self, results: List[SentimentResult]) -> Dict:
        """
        Get summary statistics for a list of sentiment results
        """
        if not results:
            return {}
        
        scores = [r.score for r in results]
        labels = [r.label for r in results]
        confidences = [r.confidence for r in results]
        
        return {
            "count": len(results),
            "avg_score": np.mean(scores),
            "std_score": np.std(scores),
            "min_score": np.min(scores),
            "max_score": np.max(scores),
            "positive_count": labels.count("positive"),
            "negative_count": labels.count("negative"),
            "neutral_count": labels.count("neutral"),
            "bullish_ratio": labels.count("positive") / len(labels),
            "bearish_ratio": labels.count("negative") / len(labels),
            "avg_confidence": np.mean(confidences),
            "sentiment_index": (np.mean(scores) + 1) * 50  # Convert to 0-100 scale
        }


class SentimentMetricsCalculator:
    """
    Calculate aggregated sentiment metrics from individual news sentiment
    """
    
    def __init__(self):
        pass
    
    def calculate_daily_metrics(
        self,
        df: pd.DataFrame,
        symbol: str
    ) -> pd.DataFrame:
        """
        Calculate daily aggregated sentiment metrics
        
        Args:
            df: DataFrame with sentiment analysis results
            symbol: Asset symbol
        
        Returns:
            DataFrame with daily metrics
        """
        if df.empty or "sentiment_score" not in df.columns:
            return pd.DataFrame()
        
        df = df.copy()
        
        # Ensure time column is datetime
        if "time" not in df.columns and "date" in df.columns:
            df["time"] = pd.to_datetime(df["date"])
        else:
            df["time"] = pd.to_datetime(df["time"])
        
        # Extract date
        df["date"] = df["time"].dt.date
        
        # Group by date
        daily = df.groupby("date").agg({
            "sentiment_score": ["mean", "std", "min", "max", "count"],
            "sentiment_positive": "mean",
            "sentiment_negative": "mean",
            "sentiment_neutral": "mean",
            "sentiment_label": lambda x: (x == "positive").sum()
        }).reset_index()
        
        # Flatten column names
        daily.columns = [
            "date", 
            "avg_sentiment", "sentiment_std", "min_sentiment", "max_sentiment", "news_volume",
            "avg_positive", "avg_negative", "avg_neutral",
            "positive_count"
        ]
        
        # Calculate additional metrics
        daily["symbol"] = symbol
        daily["time"] = pd.to_datetime(daily["date"])
        daily["interval_type"] = "daily"
        
        # Sentiment index (0-100 scale)
        daily["sentiment_index"] = (daily["avg_sentiment"] + 1) * 50
        
        # Bullish/Bearish ratio
        daily["bullish_ratio"] = daily["positive_count"] / daily["news_volume"]
        daily["bearish_ratio"] = 1 - daily["bullish_ratio"] - (daily["avg_neutral"])
        
        # Change metrics
        daily["sentiment_change_1d"] = daily["avg_sentiment"].diff()
        daily["sentiment_change_5d"] = daily["avg_sentiment"].diff(5)
        
        # Heat index (based on volume and sentiment extremity)
        daily["heat_index"] = daily["news_volume"] * (1 - daily["avg_neutral"])
        daily["heat_index"] = (daily["heat_index"] - daily["heat_index"].min()) / \
                              (daily["heat_index"].max() - daily["heat_index"].min() + 1e-6) * 100
        
        return daily


# Convenience functions
def analyze_news_sentiment(
    texts: Union[str, List[str]]
) -> Union[SentimentResult, List[SentimentResult]]:
    """Convenience function to analyze sentiment"""
    analyzer = FinBERTAnalyzer()
    
    if isinstance(texts, str):
        return analyzer.analyze(texts)
    
    return analyzer.analyze_batch(texts)


if __name__ == "__main__":
    # Test the analyzer
    analyzer = FinBERTAnalyzer()
    
    # Test single text
    text = "Gold prices surge as Federal Reserve signals rate pause"
    result = analyzer.analyze(text)
    print(f"Single text result: {result}")
    
    # Test batch
    texts = [
        "Gold hits record high amid inflation fears",
        "Silver prices drop on strong dollar",
        "Precious metals remain stable in quiet trading"
    ]
    results = analyzer.analyze_batch(texts)
    
    for text, result in zip(texts, results):
        print(f"\nText: {text[:50]}...")
        print(f"  Score: {result.score:.3f}, Label: {result.label}, Confidence: {result.confidence:.3f}")
    
    # Summary
    summary = analyzer.get_sentiment_summary(results)
    print(f"\nSummary: {summary}")
