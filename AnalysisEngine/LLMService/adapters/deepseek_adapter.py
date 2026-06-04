"""
DeepSeek API适配器
支持DeepSeek Chat和DeepSeek Coder
"""
import requests
import time
import asyncio
from typing import Optional
import logging

from ..base import BaseLLMAdapter, LLMConfig, LLMRequest, LLMResponse, LLMProvider

logger = logging.getLogger(__name__)

class DeepSeekAdapter(BaseLLMAdapter):
    """DeepSeek API适配器（兼容OpenAI格式）"""
    
    PRICING = {
        "deepseek-chat": {"input": 0.14, "output": 0.28},
        "deepseek-coder": {"input": 0.14, "output": 0.28},
    }
    
    BASE_URL = "https://api.deepseek.com/v1"
    
    def __init__(self, api_key: str, config: Optional[LLMConfig] = None):
        super().__init__(api_key, config)
    
    def _default_config(self) -> LLMConfig:
        return LLMConfig(
            provider=LLMProvider.DEEPSEEK,
            model="deepseek-chat",
            temperature=0.7,
            max_tokens=2000
        )
    
    async def complete_async(self, request: LLMRequest) -> LLMResponse:
        return await asyncio.to_thread(self.complete_sync, request)
    
    def complete_sync(self, request: LLMRequest) -> LLMResponse:
        start_time = time.time()
        config = request.config or self.config
        
        # 构建消息
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=config.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            tokens_used = data["usage"]["total_tokens"]
            
            cost = self.calculate_cost(tokens_used, config.model)
            latency = time.time() - start_time
            
            logger.info(f"DeepSeek {config.model}: {tokens_used} tokens, ${cost:.4f}, {latency:.2f}s")
            
            return LLMResponse(
                content=content,
                provider=LLMProvider.DEEPSEEK,
                model=config.model,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                metadata={
                    "finish_reason": data["choices"][0]["finish_reason"],
                    "prompt_tokens": data["usage"]["prompt_tokens"],
                    "completion_tokens": data["usage"]["completion_tokens"]
                }
            )
        
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API error: {e}")
            raise Exception(f"DeepSeek API error: {e}")
    
    def calculate_cost(self, tokens: int, model: str) -> float:
        if model not in self.PRICING:
            return 0.0
        pricing = self.PRICING[model]
        avg_price = (pricing["input"] + pricing["output"]) / 2
        return (tokens / 1_000_000) * avg_price
