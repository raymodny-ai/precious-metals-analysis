"""
API Budget Manager
API成本控制 - 优化项 #20
"""

from datetime import datetime, date
from typing import Dict, Optional
from dataclasses import dataclass, field
import asyncio

from .cache import cache
from .logger import setup_logging

logger = setup_logging("budget")


@dataclass
class APIUsage:
    """Track API usage and costs"""
    api_name: str
    calls_today: int = 0
    cost_today: float = 0.0
    last_reset: str = ""


class APIBudgetManager:
    """
    Manage API call budgets to control costs
    
    Tracks:
    - DeepSeek API calls
    - News API calls
    - Any other paid API services
    
    Features:
    - Daily budget limits
    - Usage tracking
    - Alert thresholds
    - Automatic reset at midnight
    """
    
    # Estimated costs per API call (USD)
    COST_PER_CALL = {
        "deepseek": 0.002,      # ~$0.002 per request
        "news_api": 0.001,      # ~$0.001 per request
        "openai": 0.003,        # ~$0.003 per request
        "default": 0.001
    }
    
    def __init__(
        self,
        daily_budget: float = 10.0,
        alert_threshold_pct: float = 80.0
    ):
        self.daily_budget = daily_budget
        self.alert_threshold = daily_budget * (alert_threshold_pct / 100)
        
        self._usage: Dict[str, APIUsage] = {}
        self._today = date.today().isoformat()
        self._lock = asyncio.Lock()
    
    def _get_today(self) -> str:
        return date.today().isoformat()
    
    def _check_reset(self):
        """Reset counters if day changed"""
        today = self._get_today()
        if today != self._today:
            self._today = today
            self._usage.clear()
            logger.info("Budget counters reset for new day")
    
    def _get_usage(self, api_name: str) -> APIUsage:
        """Get or create usage tracker"""
        if api_name not in self._usage:
            self._usage[api_name] = APIUsage(
                api_name=api_name,
                last_reset=self._today
            )
        return self._usage[api_name]
    
    def get_cost_estimate(self, api_name: str, num_calls: int = 1) -> float:
        """Estimate cost for API calls"""
        cost_per_call = self.COST_PER_CALL.get(api_name, self.COST_PER_CALL["default"])
        return cost_per_call * num_calls
    
    async def check_budget(
        self,
        api_name: str,
        num_calls: int = 1
    ) -> tuple[bool, str]:
        """
        Check if API call is within budget
        
        Returns:
            (allowed, reason)
        """
        async with self._lock:
            self._check_reset()
            
            estimated_cost = self.get_cost_estimate(api_name, num_calls)
            total_spent = self.get_total_spent()
            
            if total_spent + estimated_cost > self.daily_budget:
                logger.warning(
                    f"API budget exceeded: ${total_spent:.2f} / ${self.daily_budget:.2f}"
                )
                return False, f"Daily budget exceeded (${total_spent:.2f}/${self.daily_budget:.2f})"
            
            # Warn if approaching threshold
            if total_spent + estimated_cost > self.alert_threshold:
                logger.warning(
                    f"API budget alert: ${total_spent:.2f} approaching limit"
                )
            
            return True, "ok"
    
    async def record_usage(
        self,
        api_name: str,
        num_calls: int = 1,
        actual_cost: Optional[float] = None
    ):
        """Record API usage"""
        async with self._lock:
            self._check_reset()
            
            usage = self._get_usage(api_name)
            usage.calls_today += num_calls
            
            cost = actual_cost or self.get_cost_estimate(api_name, num_calls)
            usage.cost_today += cost
            
            # Store in Redis for persistence
            cache_key = f"api_cost:{self._today}:{api_name}"
            cache.set(cache_key, {
                "calls": usage.calls_today,
                "cost": usage.cost_today
            }, ttl=86400 * 2)  # 2 days
            
            logger.debug(
                f"API usage recorded: {api_name} +{num_calls} calls, "
                f"total: ${usage.cost_today:.4f}"
            )
    
    def get_total_spent(self) -> float:
        """Get total spent today across all APIs"""
        return sum(u.cost_today for u in self._usage.values())
    
    def get_usage_summary(self) -> Dict:
        """Get usage summary for all APIs"""
        self._check_reset()
        
        total_spent = self.get_total_spent()
        
        return {
            "date": self._today,
            "daily_budget": self.daily_budget,
            "total_spent": round(total_spent, 4),
            "remaining": round(self.daily_budget - total_spent, 4),
            "usage_pct": round((total_spent / self.daily_budget) * 100, 1),
            "by_api": {
                name: {
                    "calls": usage.calls_today,
                    "cost": round(usage.cost_today, 4)
                }
                for name, usage in self._usage.items()
            }
        }
    
    def is_budget_available(self) -> bool:
        """Quick check if any budget remains"""
        return self.get_total_spent() < self.daily_budget


# Global budget manager
budget_manager = APIBudgetManager()


# ============================================================================
# Decorator for automatic budget checking
# ============================================================================

def budget_check(api_name: str, num_calls: int = 1):
    """
    Decorator to check budget before API calls
    
    Usage:
        @budget_check("deepseek")
        async def call_deepseek(prompt: str):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            allowed, reason = await budget_manager.check_budget(api_name, num_calls)
            
            if not allowed:
                raise BudgetExceededError(reason)
            
            try:
                result = await func(*args, **kwargs)
                await budget_manager.record_usage(api_name, num_calls)
                return result
            except Exception as e:
                # Still record the call even if it failed
                await budget_manager.record_usage(api_name, num_calls)
                raise
        
        return wrapper
    return decorator


class BudgetExceededError(Exception):
    """Raised when API budget is exceeded"""
    pass


# ============================================================================
# HTTP Client with Budget Control
# ============================================================================

class BudgetAwareHTTPClient:
    """
    HTTP client with automatic budget tracking
    """
    
    def __init__(self, api_name: str):
        self.api_name = api_name
        self._session = None
    
    async def __aenter__(self):
        import aiohttp
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()
    
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ):
        """Make HTTP request with budget check"""
        allowed, reason = await budget_manager.check_budget(self.api_name)
        
        if not allowed:
            raise BudgetExceededError(reason)
        
        response = await self._session.request(method, url, **kwargs)
        await budget_manager.record_usage(self.api_name)
        
        return response
    
    async def get(self, url: str, **kwargs):
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs):
        return await self.request("POST", url, **kwargs)


if __name__ == "__main__":
    print("Testing API Budget Manager...")
    
    async def test():
        # Check budget
        allowed, reason = await budget_manager.check_budget("deepseek", 10)
        print(f"Budget check: {allowed}, {reason}")
        
        # Record usage
        await budget_manager.record_usage("deepseek", 5)
        await budget_manager.record_usage("news_api", 10)
        
        # Get summary
        summary = budget_manager.get_usage_summary()
        print(f"Usage summary: {summary}")
    
    asyncio.run(test())
    print("Budget manager test complete!")
