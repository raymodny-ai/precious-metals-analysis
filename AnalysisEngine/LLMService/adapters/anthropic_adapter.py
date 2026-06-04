"""
Anthropic Claude API适配器
支持Claude 3.5 Sonnet, Claude 3.5 Haiku等模型
"""
import anthropic
import time
import asyncio
from typing import Optional
import logging

from ..base import BaseLLMAdapter, LLMConfig, LLMRequest, LLMResponse, LLMProvider

logger = logging.getLogger(__name__)

class AnthropicAdapter(BaseLLMAdapter):
    """Anthropic Claude API适配器"""
    
    PRICING = {
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku-20241022": {"input": 1.00, "output": 5.00},
        "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    }
    
    def __init__(self, api_key: str, config: Optional[LLMConfig] = None):
        super().__init__(api_key, config)
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def _default_config(self) -> LLMConfig:
        return LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
            max_tokens=4000
        )
    
    async def complete_async(self, request: LLMRequest) -> LLMResponse:
        return await asyncio.to_thread(self.complete_sync, request)
    
    def complete_sync(self, request: LLMRequest) -> LLMResponse:
        start_time = time.time()
        config = request.config or self.config
        
        try:
            response = self.client.messages.create(
                model=config.model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                system=request.system_prompt or "",
                messages=[{
                    "role": "user",
                    "content": request.prompt
                }]
            )
            
            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            # 计算成本（区分输入输出）
            input_cost = (response.usage.input_tokens / 1_000_000) * self.PRICING[config.model]["input"]
            output_cost = (response.usage.output_tokens / 1_000_000) * self.PRICING[config.model]["output"]
            total_cost = input_cost + output_cost
            
            latency = time.time() - start_time
            
            logger.info(f"Anthropic {config.model}: {tokens_used} tokens, ${total_cost:.4f}, {latency:.2f}s")
            
            return LLMResponse(
                content=content,
                provider=LLMProvider.ANTHROPIC,
                model=config.model,
                tokens_used=tokens_used,
                cost=total_cost,
                latency=latency,
                metadata={
                    "stop_reason": response.stop_reason,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            )
        
        except anthropic.RateLimitError as e:
            logger.error(f"Anthropic rate limit: {e}")
            raise Exception(f"Anthropic rate limit: {e}")
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            raise Exception(f"Anthropic error: {e}")
    
    def calculate_cost(self, tokens: int, model: str) -> float:
        if model not in self.PRICING:
            return 0.0
        pricing = self.PRICING[model]
        avg_price = (pricing["input"] + pricing["output"]) / 2
        return (tokens / 1_000_000) * avg_price
