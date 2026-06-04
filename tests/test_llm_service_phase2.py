import unittest
import json
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from AnalysisEngine.LLMService.prompts.market_analysis_prompt import MarketAnalysisPromptBuilder
from AnalysisEngine.LLMService.prompts.news_summary_prompt import NewsSummaryPromptBuilder
from AnalysisEngine.LLMService.prompts.qa_prompt import QAPromptBuilder
from AnalysisEngine.LLMService.llm_service import LLMService

class TestLLMServicePhase2(unittest.TestCase):
    
    def setUp(self):
        self.llm_service = LLMService(enable_cache=False)

    def test_market_analysis_prompt_builder(self):
        price_data = {'symbol': 'GLD', 'price': 180.0}
        technical_indicators = {'rsi': 50}
        news_summary = "Market is stable."
        
        prompts = MarketAnalysisPromptBuilder.build_comprehensive_analysis(
            price_data, news_summary, technical_indicators
        )
        
        self.assertIn('system', prompts)
        self.assertIn('user', prompts)
        self.assertIn('JSON', prompts['system'])
        self.assertIn('GLD', prompts['user'])

    def test_news_summary_prompt_builder(self):
        articles = [{'title': 'Gold rises', 'content': 'Gold prices went up today.', 'source': 'Test'}]
        prompts = NewsSummaryPromptBuilder.build_focused_summary(articles)
        
        self.assertIn('system', prompts)
        self.assertIn('user', prompts)
        self.assertIn('Gold rises', prompts['user'])

    def test_qa_prompt_builder(self):
        question = "What is the price of gold?"
        context = {'gold_price': 2000}
        prompts = QAPromptBuilder.build_contextual_qa(question, context)
        
        self.assertIn('system', prompts)
        self.assertIn('user', prompts)
        self.assertIn('2000', prompts['user'])

    def test_json_parsing(self):
        # 1. Valid JSON
        valid_json = '{"key": "value"}'
        parsed = self.llm_service._parse_json_response(valid_json)
        self.assertEqual(parsed, {'key': 'value'})
        
        # 2. Markdown JSON
        markdown_json = '```json\n{"key": "value"}\n```'
        parsed = self.llm_service._parse_json_response(markdown_json)
        self.assertEqual(parsed, {'key': 'value'})
        
        # 3. Text with JSON
        text_json = 'Here is the result: {"key": "value"}'
        parsed = self.llm_service._parse_json_response(text_json)
        self.assertEqual(parsed, {'key': 'value'})
        
        # 4. Invalid JSON
        invalid_json = 'Not a json'
        parsed = self.llm_service._parse_json_response(invalid_json)
        self.assertIsNone(parsed)

if __name__ == '__main__':
    unittest.main()
