"""
LLM 服务适配器
统一接口支持多个LLM提供商（OpenAI, Anthropic, DeepSeek）
"""
import os
import logging
from typing import Optional, Dict, List
import time
from functools import wraps

logger = logging.getLogger(__name__)

class LLMRateLimiter:
    """速率限制器"""
    
    def __init__(self, max_requests_per_minute=20):
        self.max_requests = max_requests_per_minute
        self.requests = []
    
    def wait_if_needed(self):
        """如果超过速率限制则等待"""
        now = time.time()
        # 清除1分钟前的请求记录
        self.requests = [r for r in self.requests if now - r < 60]
        
        if len(self.requests) >= self.max_requests:
            wait_time = 60 - (now - self.requests[0])
            if wait_time > 0:
                logger.warning(f"达到速率限制，等待 {wait_time:.1f}秒")
                time.sleep(wait_time)
                self.requests = []
        
        self.requests.append(now)

class LLMCache:
    """简单的LLM响应缓存"""
    
    def __init__(self, max_size=100):
        self.cache = {}
        self.max_size = max_size
    
    def get_cache_key(self, prompt: str, model: str) -> str:
        """生成缓存键"""
        return f"{model}:{hash(prompt)}"
    
    def get(self, prompt: str, model: str) -> Optional[str]:
        """获取缓存"""
        key = self.get_cache_key(prompt, model)
        return self.cache.get(key)
    
    def set(self, prompt: str, model: str, response: str):
        """设置缓存"""
        if len(self.cache) >= self.max_size:
            # 简单的LRU：删除最旧的项
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        key = self.get_cache_key(prompt, model)
        self.cache[key] = response

class LLMAdapter:
    """LLM统一适配器"""
    
    def __init__(self, enable_cache=True, enable_rate_limit=True):
        self.openai_client = None
        self.anthropic_client = None
        self.deepseek_client = None
        
        self.cache = LLMCache() if enable_cache else None
        self.rate_limiter = LLMRateLimiter() if enable_rate_limit else None
        
        self.usage_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'total_tokens': 0,
            'estimated_cost': 0.0
        }
        
        self._initialize_clients()
    
    def _initialize_clients(self):
        """初始化LLM客户端"""
        # OpenAI
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=openai_key)
                logger.info("✓ OpenAI客户端初始化成功")
            except ImportError:
                logger.warning("openai包未安装，跳过OpenAI初始化")
            except Exception as e:
                logger.error(f"OpenAI初始化失败: {e}")
        
        # Anthropic
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
                logger.info("✓ Anthropic客户端初始化成功")
            except ImportError:
                logger.warning("anthropic包未安装，跳过Anthropic初始化")
            except Exception as e:
                logger.error(f"Anthropic初始化失败: {e}")
    
    def generate(self, 
                prompt: str, 
                model: str = 'gpt-4o-mini',
                max_tokens: int = 1000,
                temperature: float = 0.7,
                use_cache: bool = True) -> Optional[str]:
        """
        生成文本
        
        Args:
            prompt: 提示词
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
            use_cache: 是否使用缓存
        
        Returns:
            生成的文本
        """
        # 检查缓存
        if use_cache and self.cache:
            cached = self.cache.get(prompt, model)
            if cached:
                self.usage_stats['cache_hits'] += 1
                logger.info(f"缓存命中: {model}")
                return cached
        
        # 速率限制
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()
        
        # 选择客户端
        try:
            if model.startswith('gpt'):
                response = self._call_openai(prompt, model, max_tokens, temperature)
            elif model.startswith('claude'):
                response = self._call_anthropic(prompt, model, max_tokens, temperature)
            else:
                raise ValueError(f"不支持的模型: {model}")
            
            # 更新统计
            self.usage_stats['total_requests'] += 1
            
            # 缓存结果
            if use_cache and self.cache and response:
                self.cache.set(prompt, model, response)
            
            return response
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return None
    
    def _call_openai(self, prompt: str, model: str, max_tokens: int, temperature: float) -> Optional[str]:
        """调用OpenAI API"""
        if not self.openai_client:
            raise ValueError("OpenAI客户端未初始化")
        
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # 更新token统计
            if hasattr(response, 'usage'):
                self.usage_stats['total_tokens'] += response.usage.total_tokens
                # 估算成本（gpt-4o-mini: $0.15/1M input, $0.60/1M output）
                cost = (response.usage.prompt_tokens * 0.15 + response.usage.completion_tokens * 0.60) / 1_000_000
                self.usage_stats['estimated_cost'] += cost
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API错误: {e}")
            raise
    
    def _call_anthropic(self, prompt: str, model: str, max_tokens: int, temperature: float) -> Optional[str]:
        """调用Anthropic API"""
        if not self.anthropic_client:
            raise ValueError("Anthropic客户端未初始化")
        
        try:
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # 更新token统计
            if hasattr(response, 'usage'):
                self.usage_stats['total_tokens'] += response.usage.input_tokens + response.usage.output_tokens
                # 估算成本（Claude 3.5 Sonnet: $3/1M input, $15/1M output）
                cost = (response.usage.input_tokens * 3 + response.usage.output_tokens * 15) / 1_000_000
                self.usage_stats['estimated_cost'] += cost
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic API错误: {e}")
            raise
    
    def summarize(self, text: str, max_length: int = 200) -> Optional[str]:
        """
        文本摘要
        
        Args:
            text: 原文
            max_length: 摘要最大长度（字符）
        
        Returns:
            摘要文本
        """
        prompt = f"""请用简洁的中文总结以下文本的核心内容，不超过{max_length}字：

{text}

摘要："""
        
        return self.generate(prompt, model='gpt-4o-mini', max_tokens=max_length)
    
    def analyze_sentiment_llm(self, text: str) -> Optional[Dict]:
        """
        使用LLM进行情感分析
        
        Returns:
            dict: {'label': 'positive/negative/neutral', 'reasoning': '原因'}
        """
        prompt = f"""分析以下金融文本的情感倾向，返回JSON格式：

文本：{text}

请返回格式：{{"label": "positive/negative/neutral", "reasoning": "分析原因"}}"""
        
        response = self.generate(prompt, model='gpt-4o-mini', max_tokens=200)
        
        if response:
            try:
                import json
                return json.loads(response)
            except:
                return {'label': 'neutral', 'reasoning': response}
        
        return None
    
    def extract_insights(self, data: Dict) -> Optional[str]:
        """
        从数据中提取洞察
        
        Args:
            data: 市场数据字典
        
        Returns:
            洞察文本
        """
        prompt = f"""基于以下市场数据，生成专业的投资洞察分析：

{data}

请提供：
1. 市场趋势分析
2. 关键风险因素
3. 投资建议

分析："""
        
        return self.generate(prompt, model='claude-3-5-sonnet-20241022', max_tokens=1000)
    
    def get_usage_stats(self) -> Dict:
        """获取使用统计"""
        return {
            **self.usage_stats,
            'cache_size': len(self.cache.cache) if self.cache else 0,
            'cache_hit_rate': self.usage_stats['cache_hits'] / max(self.usage_stats['total_requests'], 1)
        }

# 全局LLM适配器实例
llm_adapter = LLMAdapter()

def get_llm_adapter() -> LLMAdapter:
    """获取LLM适配器实例"""
    return llm_adapter
