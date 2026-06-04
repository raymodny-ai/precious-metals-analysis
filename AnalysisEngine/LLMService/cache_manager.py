"""
LLM响应缓存管理器
使用Redis缓存以减少API调用和成本
"""
import redis
import hashlib
import json
from typing import Optional
import logging

from .base import LLMRequest, LLMResponse, LLMProvider

logger = logging.getLogger(__name__)

class CacheManager:
    """LLM响应缓存管理器"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # 测试连接
            self.redis_client.ping()
            self.enabled = True
            logger.info("Redis cache enabled")
        except (redis.ConnectionError, redis.ResponseError) as e:
            logger.warning(f"Redis connection failed: {e}. Cache disabled.")
            self.redis_client = None
            self.enabled = False
        
        self.default_ttl = 3600  # 1小时
    
    def _generate_cache_key(self, request: LLMRequest) -> str:
        """生成缓存键"""
        # 使用任务类型、提示和系统提示的哈希作为键
        content = f"{request.task_type.value}:{request.system_prompt}:{request.prompt}"
        return f"llm_cache:{hashlib.sha256(content.encode()).hexdigest()}"
    
    def get(self, request: LLMRequest) -> Optional[LLMResponse]:
        """获取缓存"""
        if not self.enabled or not request.use_cache:
            return None
        
        key = self._generate_cache_key(request)
        
        try:
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                # 重建LLMResponse对象
                response = LLMResponse(
                    content=data['content'],
                    provider=LLMProvider(data['provider']),
                    model=data['model'],
                    tokens_used=data['tokens_used'],
                    cost=data['cost'],
                    latency=data['latency'],
                    cached=True,
                    metadata=data.get('metadata')
                )
                logger.info(f"Cache HIT for {request.task_type.value}")
                return response
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    def set(self, request: LLMRequest, response: LLMResponse, ttl: Optional[int] = None):
        """设置缓存"""
        if not self.enabled or not request.use_cache:
            return
        
        key = self._generate_cache_key(request)
        ttl = ttl or self.default_ttl
        
        try:
            # 序列化响应（排除cached字段）
            data = {
                "content": response.content,
                "provider": response.provider.value,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "cost": response.cost,
                "latency": response.latency,
                "metadata": response.metadata
            }
            
            self.redis_client.setex(key, ttl, json.dumps(data))
            logger.debug(f"Cached response for {request.task_type.value}")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def invalidate(self, pattern: str = "llm_cache:*"):
        """清除缓存"""
        if not self.enabled:
            return
        
        try:
            count = 0
            for key in self.redis_client.scan_iter(pattern):
                self.redis_client.delete(key)
                count += 1
            logger.info(f"Invalidated {count} cache entries")
        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
    
    def get_stats(self) -> dict:
        """获取缓存统计"""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            keys = list(self.redis_client.scan_iter("llm_cache:*"))
            info = self.redis_client.info()
            
            return {
                "enabled": True,
                "total_cached": len(keys),
                "memory_used": info.get("used_memory_human", "N/A")
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"enabled": True, "error": str(e)}
