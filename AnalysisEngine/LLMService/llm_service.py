"""
统一LLM服务
自动路由到合适的提供商，集成缓存和成本追踪
"""
import os
import json
import re
from typing import Optional, Dict, List, Union, Any
import logging

from .base import LLMProvider, TaskType, LLMRequest, LLMResponse, LLMConfig
from .adapters.openai_adapter import OpenAIAdapter
from .adapters.anthropic_adapter import AnthropicAdapter
from .adapters.google_adapter import GoogleAdapter
from .adapters.deepseek_adapter import DeepSeekAdapter
from .cache_manager import CacheManager
from .prompts.market_analysis_prompt import MarketAnalysisPromptBuilder
from .prompts.news_summary_prompt import NewsSummaryPromptBuilder
from .prompts.qa_prompt import QAPromptBuilder

logger = logging.getLogger(__name__)

class LLMService:
    """统一LLM服务"""
    
    # 任务类型到推荐模型的映射
    TASK_ROUTING = {
        TaskType.SUMMARIZATION: ("openai", "gpt-4o-mini"),
        TaskType.ANALYSIS: ("anthropic", "claude-3-5-sonnet-20241022"),
        TaskType.PREDICTION: ("anthropic", "claude-3-5-sonnet-20241022"),
        TaskType.QA: ("openai", "gpt-4o"),
        TaskType.CODE_GEN: ("deepseek", "deepseek-coder"),
        TaskType.TRANSLATION: ("google", "gemini-2.0-flash-exp"),
        TaskType.SENTIMENT: ("openai", "gpt-4o-mini"),
    }
    
    def __init__(self, enable_cache: bool = True):
        self.adapters: Dict[LLMProvider, any] = {}
        self.cache_manager = CacheManager() if enable_cache else None
        
        self.usage_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'by_provider': {}
        }
        
        self._initialize_adapters()
    
    def _initialize_adapters(self):
        """初始化所有可用的LLM适配器"""
        # OpenAI
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            try:
                self.adapters[LLMProvider.OPENAI] = OpenAIAdapter(openai_key)
                logger.info("✓ OpenAI adapter initialized")
            except Exception as e:
                logger.warning(f"OpenAI initialization failed: {e}")
        
        # Anthropic
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            try:
                self.adapters[LLMProvider.ANTHROPIC] = AnthropicAdapter(anthropic_key)
                logger.info("✓ Anthropic adapter initialized")
            except Exception as e:
                logger.warning(f"Anthropic initialization failed: {e}")
        
        # Google
        google_key = os.getenv('GOOGLE_API_KEY')
        if google_key:
            try:
                self.adapters[LLMProvider.GOOGLE] = GoogleAdapter(google_key)
                logger.info("✓ Google adapter initialized")
            except Exception as e:
                logger.warning(f"Google initialization failed: {e}")
        
        # DeepSeek
        deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        if deepseek_key:
            try:
                self.adapters[LLMProvider.DEEPSEEK] = DeepSeekAdapter(deepseek_key)
                logger.info("✓ DeepSeek adapter initialized")
            except Exception as e:
                logger.warning(f"DeepSeek initialization failed: {e}")
    
    def complete(self, request: LLMRequest) -> Optional[LLMResponse]:
        """
        完成LLM请求
        
        Args:
            request: LLM请求对象
        
        Returns:
            LLM响应对象
        """
        # 检查缓存
        if self.cache_manager and request.use_cache:
            cached = self.cache_manager.get(request)
            if cached:
                self.usage_stats['cache_hits'] += 1
                self.usage_stats['total_requests'] += 1
                return cached
        
        # 选择提供商和模型
        try:
            provider_name, model_name = self._select_provider_and_model(request)
        except Exception as e:
            logger.error(f"Provider selection failed: {e}")
            return None
        
        if provider_name not in self.adapters:
            logger.error(f"Provider {provider_name} not available")
            return None
        
        # 设置配置
        if not request.config:
            request.config = LLMConfig(
                provider=LLMProvider(provider_name),
                model=model_name
            )
        
        # 调用适配器
        adapter = self.adapters[provider_name]
        
        try:
            response = adapter.complete_sync(request)
            
            # 更新统计
            self._update_stats(response)
            
            # 缓存结果
            if self.cache_manager and request.use_cache:
                self.cache_manager.set(request, response)
            
            return response
            
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return None
    
    def _select_provider_and_model(self, request: LLMRequest) -> tuple:
        """根据任务类型选择提供商和模型"""
        if request.config:
            return request.config.provider.value, request.config.model
        
        # 使用任务路由
        if request.task_type in self.TASK_ROUTING:
            provider, model = self.TASK_ROUTING[request.task_type]
            
            # 检查提供商是否可用
            if LLMProvider(provider) in self.adapters:
                return provider, model
        
        # 降级策略：使用第一个可用的提供商
        if self.adapters:
            provider = list(self.adapters.keys())[0]
            adapter = self.adapters[provider]
            return provider.value, adapter.config.model
        
        raise Exception("No LLM providers available")
    
    def _update_stats(self, response: LLMResponse):
        """更新使用统计"""
        self.usage_stats['total_requests'] += 1
        self.usage_stats['total_tokens'] += response.tokens_used
        self.usage_stats['total_cost'] += response.cost
        
        provider_key = response.provider.value
        if provider_key not in self.usage_stats['by_provider']:
            self.usage_stats['by_provider'][provider_key] = {
                'requests': 0,
                'tokens': 0,
                'cost': 0.0
            }
        
        self.usage_stats['by_provider'][provider_key]['requests'] += 1
        self.usage_stats['by_provider'][provider_key]['tokens'] += response.tokens_used
        self.usage_stats['by_provider'][provider_key]['cost'] += response.cost
    
    def get_stats(self) -> Dict:
        """获取使用统计"""
        stats = {**self.usage_stats}
        
        if self.usage_stats['total_requests'] > 0:
            stats['cache_hit_rate'] = self.usage_stats['cache_hits'] / self.usage_stats['total_requests']
            stats['avg_cost_per_request'] = self.usage_stats['total_cost'] / self.usage_stats['total_requests']
        else:
            stats['cache_hit_rate'] = 0.0
            stats['avg_cost_per_request'] = 0.0
        
        # 添加缓存统计
        if self.cache_manager:
            stats['cache'] = self.cache_manager.get_stats()
        
        return stats
    
    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """鲁棒的JSON解析"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试从Markdown代码块中提取
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # 尝试查找第一个 { 和最后一个 }
            try:
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    return json.loads(content[start:end+1])
            except json.JSONDecodeError:
                pass
                
            logger.error(f"Failed to parse JSON from response: {content[:100]}...")
            return None

    # 便捷方法
    def summarize_news(self, articles: List[Dict], focus_topics: List[str] = None) -> Optional[Dict]:
        """新闻摘要"""
        prompts = NewsSummaryPromptBuilder.build_focused_summary(articles, focus_topics)
        
        request = LLMRequest(
            task_type=TaskType.SUMMARIZATION,
            system_prompt=prompts['system'],
            prompt=prompts['user']
        )
        
        response = self.complete(request)
        if not response:
            return None
            
        return self._parse_json_response(response.content)
    
    def analyze_market(self, price_data: Dict, news_summary: str, technical_indicators: Dict, historical_context: List[str] = None, use_rag: bool = True) -> Optional[Dict]:
        """市场分析（增强RAG版本）"""
        # 如果启用RAG且没有提供历史上下文，从RAG系统检索
        if use_rag and not historical_context:
            try:
                from .rag_system import get_rag_system
                rag = get_rag_system()
                
                # 构建检索查询
                query = f"黄金 白银 贵金属 市场分析 {price_data.get('symbol', '')}"
                rag_result = rag.build_context(query, max_reports=3, max_news=5)
                
                # 提取上下文文本（限制长度避免超token）
                rag_context = rag_result.get('context', '')[:2000]
                if rag_context:
                    historical_context = [rag_context]
                    logger.info(f"RAG retrieved {len(rag_result.get('sources', []))} sources for market analysis")
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")
        
        prompts = MarketAnalysisPromptBuilder.build_comprehensive_analysis(
            price_data, news_summary, technical_indicators, historical_context
        )
        
        request = LLMRequest(
            task_type=TaskType.ANALYSIS,
            system_prompt=prompts['system'],
            prompt=prompts['user'],
            temperature=0.3 # Lower temperature for analysis
        )
        
        response = self.complete(request)
        if not response:
            return None
            
        return self._parse_json_response(response.content)
    
    def ask(self, question: str, context_data: Dict = None, chat_history: List[Dict] = None) -> Optional[str]:
        """问答"""
        context_data = context_data or {}
        prompts = QAPromptBuilder.build_contextual_qa(question, context_data, chat_history)
        
        request = LLMRequest(
            task_type=TaskType.QA,
            system_prompt=prompts['system'],
            prompt=prompts['user']
        )
        
        response = self.complete(request)
        return response.content if response else None

    # 兼容旧接口
    def summarize(self, text: str, max_length: int = 200) -> Optional[str]:
        """简单文本摘要 (旧接口兼容)"""
        prompt = f"请用简洁的中文总结以下文本的核心内容，不超过{max_length}字：\n\n{text}\n\n摘要："
        request = LLMRequest(task_type=TaskType.SUMMARIZATION, prompt=prompt)
        response = self.complete(request)
        return response.content if response else None

    def analyze(self, data: Dict, analysis_type: str = "market") -> Optional[str]:
        """通用分析 (旧接口兼容)"""
        if analysis_type == "market":
            # 尝试转换为新格式，如果数据结构匹配
            # 这里简单返回文本
            pass
            
        prompt = f"请分析以下{analysis_type}数据并提供专业洞察：\n\n{data}"
        request = LLMRequest(
            task_type=TaskType.ANALYSIS,
            prompt=prompt,
            system_prompt="你是一位资深的金融市场分析师，精通贵金属市场。"
        )
        response = self.complete(request)
        return response.content if response else None

# 全局LLM服务实例
_llm_service = None

def get_llm_service() -> LLMService:
    """获取LLM服务单例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
