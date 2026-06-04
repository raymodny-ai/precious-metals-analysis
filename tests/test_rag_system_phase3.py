import unittest
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from AnalysisEngine.LLMService.rag_system import RAGSystem

class TestRAGSystemPhase3(unittest.TestCase):
    
    def setUp(self):
        # Use a test directory
        self.rag = RAGSystem(persist_directory='./data/test_chromadb')
        
    def test_add_and_search_report(self):
        """Test adding and searching reports"""
        if not self.rag.enabled:
            self.skipTest("ChromaDB not available")
            
        # Add a test report
        self.rag.add_report(
            report_id='test_report_1',
            content='黄金价格在2024年突破2000美元，创历史新高',
            metadata={'timestamp': '2024-01-01T00:00:00'}
        )
        
        # Search for it
        results = self.rag.search_reports('黄金价格 历史新高', n_results=1)
        self.assertGreater(len(results), 0)
        self.assertIn('黄金', results[0]['content'])
    
    def test_time_decay_weight(self):
        """Test time decay weighting"""
        if not self.rag.enabled:
            self.skipTest("ChromaDB not available")
            
        # Recent timestamp should have higher weight
        recent_weight = self.rag._calculate_time_decay_weight('2024-11-20T00:00:00')
        old_weight = self.rag._calculate_time_decay_weight('2023-01-01T00:00:00')
        
        self.assertGreater(recent_weight, old_weight)
        self.assertGreater(recent_weight, 0.5)  # Recent should be > 0.5
    
    def test_mmr_rerank(self):
        """Test MMR re-ranking"""
        if not self.rag.enabled:
            self.skipTest("ChromaDB not available")
            
        documents = [
            {'content': 'doc1', 'distance': 0.1},
            {'content': 'doc2', 'distance': 0.2},
            {'content': 'doc3', 'distance': 0.3},
            {'content': 'doc4', 'distance': 0.4}
        ]
        
        reranked = self.rag._mmr_rerank(documents, 'test', top_k=2)
        self.assertEqual(len(reranked), 2)
    
    def test_build_context_with_sources(self):
        """Test building context with source tracking"""
        if not self.rag.enabled:
            self.skipTest("ChromaDB not available")
            
        # Add some test data
        self.rag.add_news(
            news_url='http://test.com/news1',
            title='Gold Hits Record High',
            content='Gold prices surged to new records today.',
            metadata={'timestamp': datetime.now().isoformat()}
        )
        
        result = self.rag.build_context('gold prices record', max_news=5, include_sources=True)
        
        self.assertIn('context', result)
        self.assertIn('sources', result)
        self.assertIsInstance(result['sources'], list)
    
    def test_rag_stats(self):
        """Test getting RAG statistics"""
        stats = self.rag.get_stats()
        
        if self.rag.enabled:
            self.assertTrue(stats['enabled'])
            self.assertIn('reports_count', stats)
            self.assertIn('news_count', stats)
        else:
            self.assertFalse(stats['enabled'])

if __name__ == '__main__':
    unittest.main()
