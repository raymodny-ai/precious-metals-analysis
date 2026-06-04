"""
OpenAI API适配器
支持GPT-4o, GPT-4o-mini等模型
"""
import openai
import time
import asyncio
from typing import Optional
import logging

from ..base import BaseLLMAdapter, LLMConfig, LLMRequest, LLMResponse, LLMProvider

logger = logging.getLogger(__name__)

class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI API适配器"""
    
    # 定价表 (每1M tokens的价格, USD)
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    }
    
    def __init__(self, api_key: str, config: Optional[LLMConfig] = None):
        super().__init__(api_key, config)
        self.client = openai.OpenAI(api_key=api_key)
    
    def _default_config(self) -> LLMConfig:
        return LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=2000
        )
    
    async def complete_async(self, request: LLMRequest) -> LLMResponse:
        """异步请求"""
        return await asyncio.to_thread(self.complete_sync, request)
    
    def complete_sync(self, request: LLMRequest) -> LLMResponse:
        """同步请求"""
        start_time = time.time()
        
        # 构建消息
        messages = []
        if request.system_prompt:
            messages.append({
                "role": "system",
                "content": request.system_prompt
            })
        messages.append({
            "role": "user",
            "content": request.prompt
        })
        
        # 配置
        config = request.config or self.config
        
        try:
            # 调用API
            response = self.client.chat.completions.create(
                model=config.model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                timeout=config.timeout
            )
            
            # 解析响应
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            # 计算成本和延迟
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = self._calculate_detailed_cost(input_tokens, output_tokens, config.model)
            latency = time.time() - start_time
            
            logger.info(f"OpenAI {config.model}: {tokens_used} tokens, ${cost:.4f}, {latency:.2f}s")
            
            return LLMResponse(
                content=content,
                provider=LLMProvider.OPENAI,
                model=config.model,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens
                }
            )
        
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise Exception(f"OpenAI rate limit exceeded: {e}")
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise Exception(f"Unexpected error: {e}")
    
    def _calculate_detailed_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """详细成本计算"""
        if model not in self.PRICING:
            return 0.0
        
        pricing = self.PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
    
    def calculate_cost(self, tokens: int, model: str) -> float:
        """简化成本计算"""
        if model not in self.PRICING:
            return 0.0
        
        pricing = self.PRICING[model]
        avg_price = (pricing["input"] + pricing["output"]) / 2
        return (tokens / 1_000_000) * avg_price
