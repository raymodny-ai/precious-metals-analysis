"""
Async Batch Request Utilities
批量请求优化 - 优化项 #5
"""

import asyncio
from typing import List, Dict, Any, Callable, TypeVar, Optional
from dataclasses import dataclass
from datetime import datetime

from .logger import setup_logging

logger = setup_logging("batch")

T = TypeVar('T')


@dataclass
class BatchResult:
    """Result of a batch operation"""
    symbol: str
    data: Any
    success: bool
    error: Optional[str] = None
    latency_ms: float = 0.0


async def fetch_multiple_symbols(
    symbols: List[str],
    fetcher_func: Callable,
    max_concurrent: int = 5,
    timeout: float = 30.0
) -> Dict[str, BatchResult]:
    """
    Fetch data for multiple symbols concurrently
    
    Args:
        symbols: List of symbols to fetch
        fetcher_func: Async function that takes symbol and returns data
        max_concurrent: Maximum concurrent requests
        timeout: Timeout per request in seconds
    
    Returns:
        Dict mapping symbol to BatchResult
    
    Usage:
        async def fetch_price(symbol: str):
            return await price_fetcher.fetch_async(symbol)
        
        results = await fetch_multiple_symbols(
            symbols=['GLD', 'SLV', 'IAU'],
            fetcher_func=fetch_price
        )
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_one(symbol: str) -> BatchResult:
        async with semaphore:
            start = datetime.utcnow()
            try:
                data = await asyncio.wait_for(
                    fetcher_func(symbol),
                    timeout=timeout
                )
                latency = (datetime.utcnow() - start).total_seconds() * 1000
                
                return BatchResult(
                    symbol=symbol,
                    data=data,
                    success=True,
                    latency_ms=latency
                )
            except asyncio.TimeoutError:
                return BatchResult(
                    symbol=symbol,
                    data=None,
                    success=False,
                    error="Timeout"
                )
            except Exception as e:
                return BatchResult(
                    symbol=symbol,
                    data=None,
                    success=False,
                    error=str(e)
                )
    
    # Create tasks for all symbols
    tasks = [fetch_one(symbol) for symbol in symbols]
    
    # Execute concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Build result dict
    result_dict = {}
    for result in results:
        if isinstance(result, BatchResult):
            result_dict[result.symbol] = result
        elif isinstance(result, Exception):
            logger.error(f"Batch fetch error: {result}")
    
    return result_dict


async def batch_process(
    items: List[Any],
    processor_func: Callable,
    batch_size: int = 10,
    delay_between_batches: float = 0.1
) -> List[Any]:
    """
    Process items in batches
    
    Args:
        items: List of items to process
        processor_func: Async function to process each item
        batch_size: Number of items per batch
        delay_between_batches: Delay between batches in seconds
    
    Returns:
        List of results
    """
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        tasks = [processor_func(item) for item in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        results.extend(batch_results)
        
        # Rate limiting between batches
        if i + batch_size < len(items):
            await asyncio.sleep(delay_between_batches)
    
    return results


class ParallelFetcher:
    """
    Parallel data fetcher with rate limiting and error handling
    """
    
    def __init__(
        self,
        max_concurrent: int = 5,
        request_timeout: float = 30.0,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ):
        self.max_concurrent = max_concurrent
        self.timeout = request_timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Fetch with automatic retry"""
        last_error = None
        
        for attempt in range(self.retry_count):
            try:
                async with self._semaphore:
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self.timeout
                    )
            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        raise last_error
    
    async def fetch_all(
        self,
        func: Callable,
        items: List[Any]
    ) -> List[Any]:
        """Fetch all items in parallel"""
        tasks = [
            self.fetch_with_retry(func, item)
            for item in items
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)


# ============================================================================
# Specialized Batch Fetchers
# ============================================================================

async def fetch_all_prices(symbols: List[str]) -> Dict[str, Any]:
    """Fetch prices for all symbols"""
    from ..api.dependencies import get_price_fetcher
    
    fetcher = get_price_fetcher()
    
    async def fetch_one(symbol: str):
        return await fetcher.fetch_latest_prices([symbol])
    
    return await fetch_multiple_symbols(symbols, fetch_one)


async def fetch_all_news(symbols: List[str]) -> Dict[str, Any]:
    """Fetch news for all symbols"""
    from ..api.dependencies import get_news_fetcher
    
    fetcher = get_news_fetcher()
    
    async def fetch_one(symbol: str):
        # Use generic news for precious metals
        if symbol in ['GLD', 'IAU', 'GLDM', 'SGOL', 'PHYS']:
            return await fetcher.fetch_gold_news(limit=20)
        else:
            return await fetcher.fetch_silver_news(limit=20)
    
    return await fetch_multiple_symbols(symbols, fetch_one)


if __name__ == "__main__":
    print("Testing Batch Utilities...")
    
    async def test():
        # Mock fetcher
        async def mock_fetch(symbol: str):
            await asyncio.sleep(0.1)  # Simulate network delay
            return {"symbol": symbol, "price": 200.0}
        
        # Test batch fetch
        symbols = ['GLD', 'SLV', 'IAU', 'SIVR', 'PSLV']
        results = await fetch_multiple_symbols(symbols, mock_fetch)
        
        for symbol, result in results.items():
            print(f"{symbol}: success={result.success}, latency={result.latency_ms:.1f}ms")
        
        # Test parallel fetcher
        fetcher = ParallelFetcher(max_concurrent=3)
        results = await fetcher.fetch_all(mock_fetch, symbols)
        print(f"Parallel results: {len(results)}")
    
    asyncio.run(test())
    print("Batch utilities test complete!")
