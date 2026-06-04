"""
Google Gemini API适配器
支持Gemini 2.0 Flash, Gemini 1.5 Pro等模型
"""
import google.generativeai as genai
import time
import asyncio
from typing import Optional
import logging

from ..base import BaseLLMAdapter, LLMConfig, LLMRequest, LLMResponse, LLMProvider

logger = logging.getLogger(__name__)

class GoogleAdapter(BaseLLMAdapter):
    """Google Gemini API适配器"""
    
    PRICING = {
        "gemini-2.0-flash-exp": {"input": 0.00, "output": 0.00},  # 免费
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    }
    
    def __init__(self, api_key: str, config: Optional[LLMConfig] = None):
        super().__init__(api_key, config)
        genai.configure(api_key=api_key)
        config = config or self._default_config()
        self.model = genai.GenerativeModel(config.model)
    
    def _default_config(self) -> LLMConfig:
        return LLMConfig(
            provider=LLMProvider.GOOGLE,
            model="gemini-2.0-flash-exp",
            temperature=0.7,
            max_tokens=2000
        )
    
    async def complete_async(self, request: LLMRequest) -> LLMResponse:
        return await asyncio.to_thread(self.complete_sync, request)
    
    def complete_sync(self, request: LLMRequest) -> LLMResponse:
        start_time = time.time()
        config = request.config or self.config
        
        try:
            # 构建完整提示
            full_prompt = request.prompt
            if request.system_prompt:
                full_prompt = f"{request.system_prompt}\n\n{request.prompt}"
            
            # 配置生成参数
            generation_config = genai.types.GenerationConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
                top_p=config.top_p
            )
            
            # 生成响应
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            content = response.text
            
            # Gemini API暂不返回token数，估算
            tokens_used = self._estimate_tokens(full_prompt, content)
            cost = self.calculate_cost(tokens_used, config.model)
            latency = time.time() - start_time
            
            logger.info(f"Google {config.model}: ~{tokens_used} tokens, ${cost:.4f}, {latency:.2f}s")
            
            return LLMResponse(
                content=content,
                provider=LLMProvider.GOOGLE,
                model=config.model,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                metadata={
                    "finish_reason": response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
                }
            )
        
        except Exception as e:
            logger.error(f"Google Gemini error: {e}")
            raise Exception(f"Google Gemini error: {e}")
    
    def _estimate_tokens(self, prompt: str, response: str) -> int:
        """估算token数 (1 token ≈ 4 字符)"""
        return (len(prompt) + len(response)) // 4
    
    def calculate_cost(self, tokens: int, model: str) -> float:
        if model not in self.PRICING:
            return 0.0
        pricing = self.PRICING[model]
        avg_price = (pricing["input"] + pricing["output"]) / 2
        return (tokens / 1_000_000) * avg_price
