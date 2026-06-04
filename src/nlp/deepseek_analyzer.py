"""
DeepSeek Sentiment Analyzer
DeepSeek深度情绪分析模块
Based on FinBERT_DeepSeek_Kimi2.md hybrid architecture
"""

import aiohttp
import asyncio
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import re

from ..utils.logger import setup_logging
from ..utils.config import get_settings

logger = setup_logging("deepseek_analyzer")
settings = get_settings()


@dataclass
class DeepSeekResult:
    """DeepSeek analysis result"""
    sentiment_score: float  # -1 to +1
    sentiment_label: str    # 'bullish', 'bearish', 'neutral'
    confidence: float
    key_factors: List[str]
    market_impact: str      # 'high', 'medium', 'low'
    reasoning: str
    entities: List[str]
    time_horizon: str       # 'short_term', 'medium_term', 'long_term'
    

class DeepSeekAnalyzer:
    """
    DeepSeek-based deep sentiment analyzer for financial news
    
    Features:
    - Deep contextual understanding
    - Multi-factor analysis
    - Market impact assessment
    - Entity extraction
    - Reasoning chain
    
    Used for:
    - Ambiguous FinBERT results (confidence < threshold)
    - High-stakes news requiring deep analysis
    - Complex multi-topic articles
    """
    
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    # Prompts
    SYSTEM_PROMPT = """You are an expert financial analyst specializing in precious metals markets (gold and silver). 
Your task is to analyze news articles and provide detailed sentiment analysis with market impact assessment.

For each article, you must analyze:
1. Overall sentiment (bullish/bearish/neutral for precious metals)
2. Key factors driving the sentiment
3. Potential market impact
4. Relevant entities (companies, central banks, economic indicators)
5. Time horizon of the impact

Always respond in JSON format."""

    ANALYSIS_PROMPT_TEMPLATE = """Analyze the following news article for its impact on precious metals (gold/silver) markets:

TITLE: {title}

CONTENT: {content}

Provide your analysis in the following JSON format:
{{
    "sentiment_score": <float between -1.0 (very bearish) and 1.0 (very bullish)>,
    "sentiment_label": "<bullish|bearish|neutral>",
    "confidence": <float between 0.0 and 1.0>,
    "key_factors": ["<factor1>", "<factor2>", ...],
    "market_impact": "<high|medium|low>",
    "reasoning": "<brief explanation of your analysis>",
    "entities": ["<entity1>", "<entity2>", ...],
    "time_horizon": "<short_term|medium_term|long_term>"
}}

Focus on how this news affects:
- Gold and silver prices
- Precious metals ETFs (GLD, SLV, etc.)
- Safe-haven demand
- Dollar strength/weakness implications"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.deepseek_api_key
        
        if not self.api_key:
            logger.warning("DeepSeek API key not configured. Using mock responses.")
    
    async def analyze_async(
        self,
        title: str,
        content: str,
        timeout: int = 30
    ) -> DeepSeekResult:
        """
        Analyze a single news article asynchronously
        
        Args:
            title: Article title
            content: Article content
            timeout: Request timeout in seconds
        
        Returns:
            DeepSeekResult with detailed analysis
        """
        if not self.api_key:
            return self._get_mock_result(title, content)
        
        prompt = self.ANALYSIS_PROMPT_TEMPLATE.format(
            title=title,
            content=content[:2000]  # Limit content length
        )
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500,
            "response_format": {"type": "json_object"}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"DeepSeek API error: {response.status} - {error_text}")
                        return self._get_mock_result(title, content)
                    
                    data = await response.json()
                    return self._parse_response(data)
                    
        except asyncio.TimeoutError:
            logger.error("DeepSeek API timeout")
            return self._get_mock_result(title, content)
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return self._get_mock_result(title, content)
    
    def analyze(
        self,
        title: str,
        content: str,
        timeout: int = 30
    ) -> DeepSeekResult:
        """
        Synchronous wrapper for analyze_async
        """
        return asyncio.run(self.analyze_async(title, content, timeout))
    
    async def analyze_batch_async(
        self,
        articles: List[Dict[str, str]],
        max_concurrent: int = 5
    ) -> List[DeepSeekResult]:
        """
        Analyze multiple articles with concurrency limit
        
        Args:
            articles: List of dicts with 'title' and 'content' keys
            max_concurrent: Maximum concurrent requests
        
        Returns:
            List of DeepSeekResult objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(article):
            async with semaphore:
                return await self.analyze_async(
                    article.get("title", ""),
                    article.get("content", "")
                )
        
        tasks = [analyze_with_semaphore(article) for article in articles]
        results = await asyncio.gather(*tasks)
        
        return results
    
    def _parse_response(self, data: Dict) -> DeepSeekResult:
        """Parse DeepSeek API response"""
        try:
            content = data["choices"][0]["message"]["content"]
            
            # Parse JSON response
            analysis = json.loads(content)
            
            return DeepSeekResult(
                sentiment_score=float(analysis.get("sentiment_score", 0)),
                sentiment_label=analysis.get("sentiment_label", "neutral"),
                confidence=float(analysis.get("confidence", 0.5)),
                key_factors=analysis.get("key_factors", []),
                market_impact=analysis.get("market_impact", "medium"),
                reasoning=analysis.get("reasoning", ""),
                entities=analysis.get("entities", []),
                time_horizon=analysis.get("time_horizon", "short_term")
            )
            
        except (KeyError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing DeepSeek response: {e}")
            return DeepSeekResult(
                sentiment_score=0,
                sentiment_label="neutral",
                confidence=0.3,
                key_factors=[],
                market_impact="low",
                reasoning="Error parsing response",
                entities=[],
                time_horizon="short_term"
            )
    
    def _get_mock_result(self, title: str, content: str) -> DeepSeekResult:
        """Generate mock result for testing without API key"""
        # Simple keyword-based mock analysis
        text = (title + " " + content).lower()
        
        bullish_keywords = ["surge", "rally", "rise", "bullish", "gain", "record high", 
                          "safe haven", "inflation", "uncertainty", "central bank buying"]
        bearish_keywords = ["fall", "drop", "decline", "bearish", "loss", "sell-off",
                          "dollar strength", "rate hike", "risk-on"]
        
        bullish_count = sum(1 for kw in bullish_keywords if kw in text)
        bearish_count = sum(1 for kw in bearish_keywords if kw in text)
        
        if bullish_count > bearish_count:
            score = min(0.8, 0.3 + bullish_count * 0.1)
            label = "bullish"
        elif bearish_count > bullish_count:
            score = max(-0.8, -0.3 - bearish_count * 0.1)
            label = "bearish"
        else:
            score = 0
            label = "neutral"
        
        # Extract simple entities
        entities = []
        entity_patterns = ["fed", "federal reserve", "ecb", "china", "india", 
                         "gld", "slv", "comex", "lbma"]
        for entity in entity_patterns:
            if entity in text:
                entities.append(entity.upper())
        
        return DeepSeekResult(
            sentiment_score=score,
            sentiment_label=label,
            confidence=0.6,
            key_factors=["Mock analysis - API key not configured"],
            market_impact="medium",
            reasoning=f"Mock analysis based on keyword matching. Bullish: {bullish_count}, Bearish: {bearish_count}",
            entities=entities[:5],
            time_horizon="short_term"
        )


class HybridSentimentEngine:
    """
    Hybrid sentiment analysis engine combining FinBERT and DeepSeek
    
    Strategy:
    1. First pass: Use FinBERT for fast classification
    2. If FinBERT confidence < threshold OR ambiguous result, use DeepSeek
    3. Combine results with weighted averaging
    
    This optimizes for:
    - Speed (FinBERT is fast)
    - Accuracy (DeepSeek for complex cases)
    - Cost efficiency (DeepSeek only when needed)
    """
    
    # Thresholds for routing to DeepSeek
    CONFIDENCE_THRESHOLD = 0.6
    NEUTRAL_THRESHOLD = 0.4  # If neutral probability > this, use DeepSeek
    
    def __init__(
        self,
        finbert_analyzer=None,
        deepseek_analyzer=None
    ):
        # Lazy load analyzers
        self._finbert = finbert_analyzer
        self._deepseek = deepseek_analyzer
    
    @property
    def finbert(self):
        if self._finbert is None:
            from .finbert_analyzer import FinBERTAnalyzer
            self._finbert = FinBERTAnalyzer()
        return self._finbert
    
    @property
    def deepseek(self):
        if self._deepseek is None:
            self._deepseek = DeepSeekAnalyzer()
        return self._deepseek
    
    def analyze(
        self,
        title: str,
        content: str,
        force_deepseek: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze text with hybrid approach
        
        Args:
            title: Article title
            content: Article content
            force_deepseek: Always use DeepSeek (for high-stakes analysis)
        
        Returns:
            Combined analysis result
        """
        text = f"{title} {content}"
        
        # Step 1: FinBERT fast classification
        finbert_result = self.finbert.analyze(text)
        
        logger.info(f"FinBERT result: score={finbert_result.score:.3f}, "
                   f"label={finbert_result.label}, confidence={finbert_result.confidence:.3f}")
        
        # Determine if DeepSeek is needed
        needs_deepseek = (
            force_deepseek or
            finbert_result.confidence < self.CONFIDENCE_THRESHOLD or
            finbert_result.neutral > self.NEUTRAL_THRESHOLD
        )
        
        result = {
            "finbert": {
                "score": finbert_result.score,
                "label": finbert_result.label,
                "confidence": finbert_result.confidence,
                "positive": finbert_result.positive,
                "negative": finbert_result.negative,
                "neutral": finbert_result.neutral
            },
            "deepseek": None,
            "combined": None,
            "used_deepseek": needs_deepseek
        }
        
        if needs_deepseek:
            # Step 2: DeepSeek deep analysis
            logger.info("Routing to DeepSeek for deeper analysis...")
            
            deepseek_result = self.deepseek.analyze(title, content)
            
            result["deepseek"] = {
                "score": deepseek_result.sentiment_score,
                "label": deepseek_result.sentiment_label,
                "confidence": deepseek_result.confidence,
                "key_factors": deepseek_result.key_factors,
                "market_impact": deepseek_result.market_impact,
                "reasoning": deepseek_result.reasoning,
                "entities": deepseek_result.entities,
                "time_horizon": deepseek_result.time_horizon
            }
            
            # Step 3: Combine results
            result["combined"] = self._combine_results(finbert_result, deepseek_result)
        else:
            # Use FinBERT result directly
            result["combined"] = {
                "score": finbert_result.score,
                "label": finbert_result.label,
                "confidence": finbert_result.confidence,
                "source": "finbert_only"
            }
        
        return result
    
    def _combine_results(self, finbert_result, deepseek_result) -> Dict:
        """Combine FinBERT and DeepSeek results with weighted average"""
        
        # Weight based on confidence
        finbert_weight = finbert_result.confidence
        deepseek_weight = deepseek_result.confidence * 1.2  # Slight preference for DeepSeek
        
        total_weight = finbert_weight + deepseek_weight
        
        # Weighted average score
        combined_score = (
            finbert_result.score * finbert_weight +
            deepseek_result.sentiment_score * deepseek_weight
        ) / total_weight
        
        # Determine label
        if combined_score > 0.15:
            label = "bullish"
        elif combined_score < -0.15:
            label = "bearish"
        else:
            label = "neutral"
        
        # Combined confidence
        combined_confidence = (finbert_result.confidence + deepseek_result.confidence) / 2
        
        return {
            "score": combined_score,
            "label": label,
            "confidence": combined_confidence,
            "source": "hybrid",
            "finbert_weight": finbert_weight / total_weight,
            "deepseek_weight": deepseek_weight / total_weight
        }
    
    async def analyze_batch(
        self,
        articles: List[Dict[str, str]],
        force_deepseek: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Analyze batch of articles
        """
        results = []
        
        for article in articles:
            result = self.analyze(
                article.get("title", ""),
                article.get("content", ""),
                force_deepseek
            )
            results.append(result)
        
        return results


# Convenience functions
def analyze_with_deepseek(title: str, content: str) -> DeepSeekResult:
    """Convenience function for DeepSeek analysis"""
    analyzer = DeepSeekAnalyzer()
    return analyzer.analyze(title, content)


def hybrid_analyze(title: str, content: str) -> Dict[str, Any]:
    """Convenience function for hybrid analysis"""
    engine = HybridSentimentEngine()
    return engine.analyze(title, content)


if __name__ == "__main__":
    # Test DeepSeek analyzer
    analyzer = DeepSeekAnalyzer()
    
    result = analyzer.analyze(
        "Gold Prices Surge to Record High Amid Fed Rate Pause Signals",
        "Gold prices rallied sharply on Friday, hitting a new all-time high as the Federal Reserve signaled a potential pause in interest rate hikes. The precious metal benefited from dollar weakness and increased safe-haven demand."
    )
    
    print(f"DeepSeek Result:")
    print(f"  Score: {result.sentiment_score:.3f}")
    print(f"  Label: {result.sentiment_label}")
    print(f"  Confidence: {result.confidence:.3f}")
    print(f"  Key Factors: {result.key_factors}")
    print(f"  Market Impact: {result.market_impact}")
    print(f"  Reasoning: {result.reasoning}")
    
    # Test hybrid engine
    print("\nHybrid Analysis:")
    engine = HybridSentimentEngine()
    hybrid_result = engine.analyze(
        "Gold Prices Surge to Record High",
        "Gold rallied as the Fed signaled rate pause."
    )
    print(f"  Combined: {hybrid_result['combined']}")
    print(f"  Used DeepSeek: {hybrid_result['used_deepseek']}")
