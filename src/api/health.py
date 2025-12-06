"""
Enhanced Health Check
完善的健康检查 - 优化项 #18
"""

from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils.db_pool import db_manager
from ..utils.cache import cache
from ..utils.logger import setup_logging

logger = setup_logging("health")

router = APIRouter(tags=["Health"])


class HealthChecker:
    """
    Comprehensive health checker for all system components
    """
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            async with db_manager.get_async_session() as session:
                start = datetime.utcnow()
                await session.execute(text("SELECT 1"))
                latency = (datetime.utcnow() - start).total_seconds() * 1000
                
                return {
                    "status": "healthy",
                    "latency_ms": round(latency, 2)
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            if not cache._initialized:
                return {"status": "not_configured"}
            
            start = datetime.utcnow()
            cache._sync_client.ping()
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            
            info = cache._sync_client.info()
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients")
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_models(self) -> Dict[str, Any]:
        """Check ML models availability"""
        try:
            from ..ml.model_manager import model_registry
            
            models = model_registry.list_models()
            production_models = [m for m in models if m.stage == "production"]
            
            return {
                "status": "healthy" if models else "no_models",
                "total_models": len(models),
                "production_models": len(production_models)
            }
        except Exception as e:
            return {
                "status": "not_available",
                "error": str(e)
            }
    
    async def check_external_apis(self) -> Dict[str, Any]:
        """Check external API availability"""
        import aiohttp
        
        apis = {}
        
        # Check yfinance (via Yahoo)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://query1.finance.yahoo.com/v8/finance/chart/GLD",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    apis["yahoo_finance"] = "healthy" if resp.status == 200 else f"status_{resp.status}"
        except Exception as e:
            apis["yahoo_finance"] = f"unhealthy: {str(e)[:50]}"
        
        return apis
    
    async def full_check(self) -> Dict[str, Any]:
        """Perform full health check"""
        checks = {
            "database": await self.check_database(),
            "redis": await self.check_redis(),
            "models": await self.check_models(),
        }
        
        # Determine overall status
        statuses = [c.get("status", "unknown") for c in checks.values()]
        
        if all(s == "healthy" for s in statuses):
            overall = "healthy"
        elif "unhealthy" in statuses:
            overall = "unhealthy"
        else:
            overall = "degraded"
        
        return {
            "status": overall,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "checks": checks
        }


# Global health checker
health_checker = HealthChecker()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return await health_checker.full_check()


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    result = await health_checker.full_check()
    
    if result["status"] == "unhealthy":
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=result)
    
    return result


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including external APIs"""
    result = await health_checker.full_check()
    result["checks"]["external_apis"] = await health_checker.check_external_apis()
    return result
