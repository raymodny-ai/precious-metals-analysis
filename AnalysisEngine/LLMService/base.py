"""
LLM服务基础定义
统一接口和数据结构
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class LLMProvider(Enum):
    """LLM提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    LOCAL = "local"

class TaskType(Enum):
    """任务类型分类"""
    SUMMARIZATION = "summarization"      # 新闻摘要
    ANALYSIS = "analysis"                # 深度分析
    PREDICTION = "prediction"            # 预测分析
    QA = "qa"                           # 问答
    CODE_GEN = "code_generation"        # 代码生成
    TRANSLATION = "translation"         # 翻译
    SENTIMENT = "sentiment"             # 情感分析

@dataclass
class LLMConfig:
    """LLM配置"""
    provider: LLMProvider
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 30
    retry_times: int = 3

@dataclass
class LLMRequest:
    """LLM请求对象"""
    task_type: TaskType
    prompt: str
    system_prompt: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    config: Optional[LLMConfig] = None
    use_cache: bool = True
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class LLMResponse:
    """LLM响应对象"""
    content: str
    provider: LLMProvider
    model: str
    tokens_used: int
    cost: float
    latency: float
    cached: bool = False
    metadata: Optional[Dict[str, Any]] = None

class BaseLLMAdapter(ABC):
    """LLM适配器基类"""
    
    def __init__(self, api_key: str, config: Optional[LLMConfig] = None):
        self.api_key = api_key
        self.config = config or self._default_config()
    
    @abstractmethod
    def _default_config(self) -> LLMConfig:
        """默认配置"""
        pass
    
    @abstractmethod
    async def complete_async(self, request: LLMRequest) -> LLMResponse:
        """异步补全请求"""
        pass
    
    @abstractmethod
    def complete_sync(self, request: LLMRequest) -> LLMResponse:
        """同步补全请求"""
        pass
    
    @abstractmethod
    def calculate_cost(self, tokens: int, model: str) -> float:
        """计算成本"""
        pass
