"""
RAG (Retrieval-Augmented Generation) 系统
使用ChromaDB向量数据库增强LLM上下文
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import hashlib
from datetime import datetime, timedelta
import logging
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class RAGSystem:
    """RAG检索增强生成系统"""
    
    def __init__(self, persist_directory: str = None):
        """
        初始化RAG系统
        
        Args:
            persist_directory: ChromaDB持久化目录
        """
        if persist_directory is None:
            persist_directory = os.getenv('CHROMA_DB_PATH', './data/chromadb')
            
        try:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            self.enabled = True
            logger.info(f"ChromaDB initialized at {persist_directory}")
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}. RAG disabled.")
            self.client = None
            self.enabled = False
        
        # 创建或获取集合
        if self.enabled:
            self._init_collections()
    
    def _init_collections(self):
        """初始化文档集合"""
        try:
            # 历史报告集合
            self.reports_collection = self.client.get_or_create_collection(
                name="historical_reports",
                metadata={"description": "Historical analysis reports"}
            )
            
            # 新闻文章集合
            self.news_collection = self.client.get_or_create_collection(
                name="news_articles",
                metadata={"description": "News articles and summaries"}
            )
            
            # 市场知识库集合
            self.knowledge_collection = self.client.get_or_create_collection(
                name="market_knowledge",
                metadata={"description": "Market knowledge base"}
            )
            
            logger.info("ChromaDB collections initialized")
        except Exception as e:
            logger.error(f"Failed to initialize collections: {e}")
            self.enabled = False
    
    def add_report(self, report_id: str, content: str, metadata: Optional[Dict] = None):
        """
        添加历史报告到向量库
        
        Args:
            report_id: 报告ID
            content: 报告内容
            metadata: 元数据（日期、类型等）
        """
        if not self.enabled:
            return
        
        try:
            metadata = metadata or {}
            metadata['timestamp'] = metadata.get('timestamp', datetime.now().isoformat())
            metadata['type'] = 'report'
            
            self.reports_collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[report_id]
            )
            
            logger.info(f"Added report {report_id} to vector DB")
        except Exception as e:
            logger.error(f"Failed to add report: {e}")
    
    def add_news(self, news_url: str, title: str, content: str, metadata: Optional[Dict] = None):
        """
        添加新闻文章到向量库
        
        Args:
            news_url: 新闻URL（用作ID）
            title: 标题
            content: 内容
            metadata: 元数据
        """
        if not self.enabled:
            return
        
        try:
            # 使用URL哈希作为ID
            news_id = hashlib.md5(news_url.encode()).hexdigest()
            
            # 合并标题和内容
            full_text = f"{title}\n\n{content}"
            
            metadata = metadata or {}
            metadata['url'] = news_url
            metadata['title'] = title
            metadata['timestamp'] = metadata.get('timestamp', datetime.now().isoformat())
            metadata['type'] = 'news'
            
            self.news_collection.add(
                documents=[full_text],
                metadatas=[metadata],
                ids=[news_id]
            )
            
            logger.debug(f"Added news article to vector DB")
        except Exception as e:
            logger.error(f"Failed to add news: {e}")
    
    def add_knowledge(self, topic: str, content: str, metadata: Optional[Dict] = None):
        """
        添加知识条目到知识库
        
        Args:
            topic: 主题/标题
            content: 内容
            metadata: 元数据
        """
        if not self.enabled:
            return
        
        try:
            # 使用主题哈希作为ID
            knowledge_id = hashlib.md5(topic.encode()).hexdigest()
            
            metadata = metadata or {}
            metadata['topic'] = topic
            metadata['timestamp'] = metadata.get('timestamp', datetime.now().isoformat())
            metadata['type'] = 'knowledge'
            
            self.knowledge_collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[knowledge_id]
            )
            
            logger.info(f"Added knowledge: {topic}")
        except Exception as e:
            logger.error(f"Failed to add knowledge: {e}")
    
    def _calculate_time_decay_weight(self, timestamp_str: str, decay_days: int = 30) -> float:
        """
        计算时间衰减权重
        
        Args:
            timestamp_str: ISO格式时间戳
            decay_days: 衰减周期（天）
        
        Returns:
            权重（0-1之间，越新权重越高）
        """
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            age_days = (datetime.now() - timestamp).days
            
            # 使用指数衰减: weight = exp(-age / decay_days)
            weight = np.exp(-age_days / decay_days)
            return float(weight)
        except:
            return 0.5  # 默认权重
    
    def _mmr_rerank(self, documents: List[Dict], query: str, lambda_param: float = 0.7, top_k: int = 5) -> List[Dict]:
        """
        使用MMR (Maximal Marginal Relevance) 算法重排序
        
        Args:
            documents: 候选文档列表
            query: 查询文本
            lambda_param: 多样性参数 (0-1, 越大越看重相关性, 越小越看重多样性)
            top_k: 返回文档数
        
        Returns:
            重排序后的文档列表
        """
        if not documents or len(documents) <= top_k:
            return documents[:top_k]
        
        try:
            # 简化版MMR: 基于距离分数选择多样化文档
            selected = []
            candidates = documents.copy()
            
            # 第一个文档选择相关性最高的
            selected.append(candidates.pop(0))
            
            while len(selected) < top_k and candidates:
                max_mmr_score = -float('inf')
                best_idx = 0
                
                for idx, candidate in enumerate(candidates):
                    # 相关性分数 (距离越小越相关)
                    relevance = 1 - candidate['distance']
                    
                    # 多样性分数 (与已选文档的最小距离)
                    diversity = min([
                        abs(candidate['distance'] - s['distance'])
                        for s in selected
                    ])
                    
                    # MMR分数
                    mmr_score = lambda_param * relevance + (1 - lambda_param) * diversity
                    
                    if mmr_score > max_mmr_score:
                        max_mmr_score = mmr_score
                        best_idx = idx
                
                selected.append(candidates.pop(best_idx))
            
            return selected
        except Exception as e:
            logger.error(f"MMR reranking failed: {e}")
            return documents[:top_k]
    
    def search_reports(self, query: str, n_results: int = 5, use_time_decay: bool = True) -> List[Dict]:
        """
        搜索相关历史报告（增强版）
        
        Args:
            query: 搜索查询
            n_results: 返回结果数
            use_time_decay: 是否使用时间衰减权重
        
        Returns:
            相关报告列表
        """
        if not self.enabled:
            return []
        
        try:
            # 检索更多候选结果用于re-ranking
            results = self.reports_collection.query(
                query_texts=[query],
                n_results=min(n_results * 2, 20)
            )
            
            documents = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 0
                    
                    # 时间衰减权重
                    if use_time_decay and 'timestamp' in metadata:
                        time_weight = self._calculate_time_decay_weight(metadata['timestamp'])
                        # 调整距离分数（距离越小越好）
                        adjusted_distance = distance * (1 / (time_weight + 0.1))
                    else:
                        adjusted_distance = distance
                    
                    documents.append({
                        'content': doc,
                        'metadata': metadata,
                        'distance': adjusted_distance,
                        'original_distance': distance
                    })
            
            # 按调整后的距离重新排序
            documents.sort(key=lambda x: x['distance'])
            
            # MMR re-ranking
            documents = self._mmr_rerank(documents, query, top_k=n_results)
            
            return documents
        except Exception as e:
            logger.error(f"Failed to search reports: {e}")
            return []
    
    def search_news(self, query: str, n_results: int = 10, use_time_decay: bool = True) -> List[Dict]:
        """搜索相关新闻（增强版）"""
        if not self.enabled:
            return []
        
        try:
            results = self.news_collection.query(
                query_texts=[query],
                n_results=min(n_results * 2, 30)
            )
            
            documents = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 0
                    
                    # 时间衰减权重（新闻更看重时效性）
                    if use_time_decay and 'timestamp' in metadata:
                        time_weight = self._calculate_time_decay_weight(metadata['timestamp'], decay_days=7)
                        adjusted_distance = distance * (1 / (time_weight + 0.1))
                    else:
                        adjusted_distance = distance
                    
                    documents.append({
                        'content': doc,
                        'metadata': metadata,
                        'distance': adjusted_distance,
                        'original_distance': distance
                    })
            
            documents.sort(key=lambda x: x['distance'])
            
            # MMR re-ranking（新闻需要更多样性）
            documents = self._mmr_rerank(documents, query, lambda_param=0.5, top_k=n_results)
            
            return documents
        except Exception as e:
            logger.error(f"Failed to search news: {e}")
            return []
    
    def search_knowledge(self, query: str, n_results: int = 3) -> List[Dict]:
        """搜索知识库"""
        if not self.enabled:
            return []
        
        try:
            results = self.knowledge_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            documents = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    documents.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0
                    })
            
            return documents
        except Exception as e:
            logger.error(f"Failed to search knowledge: {e}")
            return []
    
    def build_context(self, query: str, max_reports: int = 3, max_news: int = 5, include_sources: bool = True) -> Dict:
        """
        为查询构建增强上下文（增强版）
        
        Args:
            query: 用户查询
            max_reports: 最大报告数
            max_news: 最大新闻数
            include_sources: 是否包含来源引用
        
        Returns:
            包含上下文文本和引用来源的字典
        """
        if not self.enabled:
            return {"context": "", "sources": []}
        
        context_parts = []
        sources = []
        
        # 搜索相关报告
        reports = self.search_reports(query, n_results=max_reports)
        if reports:
            context_parts.append("## 相关历史报告")
            for i, report in enumerate(reports, 1):
                date = report['metadata'].get('timestamp', 'Unknown')
                relevance = 1 - report['distance']  # 转换为相似度
                context_parts.append(f"\n### 报告 {i} ({date[:10]}, 相关度: {relevance:.2f})")
                context_parts.append(report['content'][:500])  # 限制长度
                
                if include_sources:
                    sources.append({
                        'type': 'report',
                        'date': date[:10],
                        'relevance': float(relevance),
                        'content_preview': report['content'][:100]
                    })
        
        # 搜索相关新闻
        news = self.search_news(query, n_results=max_news)
        if news:
            context_parts.append("\n## 相关新闻")
            for i, article in enumerate(news, 1):
                title = article['metadata'].get('title', 'Untitled')
                date = article['metadata'].get('timestamp', 'Unknown')
                relevance = 1 - article['distance']
                context_parts.append(f"\n### {i}. {title} ({date[:10]}, 相关度: {relevance:.2f})")
                context_parts.append(article['content'][:300])
                
                if include_sources:
                    sources.append({
                        'type': 'news',
                        'title': title,
                        'date': date[:10],
                        'url': article['metadata'].get('url', ''),
                        'relevance': float(relevance)
                    })
        
        # 搜索知识库
        knowledge = self.search_knowledge(query, n_results=2)
        if knowledge:
            context_parts.append("\n## 相关知识")
            for item in knowledge:
                topic = item['metadata'].get('topic', 'Unknown')
                context_parts.append(f"\n**{topic}**: {item['content'][:200]}")
                
                if include_sources:
                    sources.append({
                        'type': 'knowledge',
                        'topic': topic,
                        'relevance': float(1 - item['distance'])
                    })
        
        return {
            "context": "\n".join(context_parts),
            "sources": sources
        }
    
    def get_stats(self) -> Dict:
        """获取向量库统计"""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            return {
                "enabled": True,
                "reports_count": self.reports_collection.count(),
                "news_count": self.news_collection.count(),
                "knowledge_count": self.knowledge_collection.count()
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"enabled": True, "error": str(e)}

# 全局RAG系统实例
_rag_system = None

def get_rag_system() -> RAGSystem:
    """获取RAG系统单例"""
    global _rag_system
    if _rag_system is None:
        _rag_system = RAGSystem()
    return _rag_system
