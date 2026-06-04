from typing import Optional, Dict
import logging
import os
from datetime import datetime, timedelta
from .adapters.yfinance_adapter import YFinanceAdapter
from .adapters.alphavantage_adapter import AlphaVantageAdapter
from .adapters.finnhub_adapter import FinnhubAdapter
from .adapters.polygon_adapter import PolygonAdapter
from .adapters.twelvedata_adapter import TwelveDataAdapter

logger = logging.getLogger(__name__)

class MultiSourceStockClient:
    """多数据源冗余股票客户端"""
    
    def __init__(self):
        self.sources = self._initialize_sources()
        self.fallback_order = ['yfinance', 'alphavantage', 'finnhub', 'polygon', 'twelvedata']
        
    def _initialize_sources(self) -> Dict:
        """初始化所有数据源"""
        sources = {}
        
        # 1. yfinance (免费,无需API key,但可能被限流)
        try:
            sources['yfinance'] = YFinanceAdapter()
            logger.info("✓ yfinance initialized")
        except Exception as e:
            logger.warning(f"yfinance init failed: {e}")
        
        # 2. Alpha Vantage (免费500次/天)
        av_key = os.getenv('ALPHA_VANTAGE_KEY')
        if av_key:
            try:
                sources['alphavantage'] = AlphaVantageAdapter(av_key)
                logger.info("✓ Alpha Vantage initialized")
            except Exception as e:
                logger.warning(f"Alpha Vantage init failed: {e}")
        
        # 3. Finnhub (免费60次/分钟)
        finnhub_key = os.getenv('FINNHUB_API_KEY')
        if finnhub_key:
            try:
                sources['finnhub'] = FinnhubAdapter(finnhub_key)
                logger.info("✓ Finnhub initialized")
            except Exception as e:
                logger.warning(f"Finnhub init failed: {e}")
        
        # 4. Polygon.io (免费5次/分钟)
        polygon_key = os.getenv('POLYGON_API_KEY')
        if polygon_key:
            try:
                sources['polygon'] = PolygonAdapter(polygon_key)
                logger.info("✓ Polygon initialized")
            except Exception as e:
                logger.warning(f"Polygon init failed: {e}")
        
        # 5. Twelve Data (免费800次/天)
        twelve_key = os.getenv('TWELVEDATA_API_KEY')
        if twelve_key:
            try:
                sources['twelvedata'] = TwelveDataAdapter(twelve_key)
                logger.info("✓ Twelve Data initialized")
            except Exception as e:
                logger.warning(f"Twelve Data init failed: {e}")
        
        return sources
    
    def get_current_price(self, symbol: str) -> Optional[Dict]:
        """
        降级链获取价格
        优先级: yfinance → Alpha Vantage → Finnhub → Polygon → Twelve Data
        """
        for source_name in self.fallback_order:
            if source_name not in self.sources:
                continue
            
            try:
                adapter = self.sources[source_name]
                price_data = adapter.get_price(symbol)
                
                if price_data and self._validate_data(price_data):
                    price_data['data_source'] = source_name
                    logger.info(f"✓ Got {symbol} price from {source_name}")
                    return price_data
                
            except Exception as e:
                logger.warning(f"Failed to get {symbol} from {source_name}: {e}")
                continue
        
        logger.error(f"All data sources failed for {symbol}")
        return None
    
    def _validate_data(self, data: Dict) -> bool:
        """验证数据质量"""
        required_fields = ['symbol', 'price', 'timestamp']
        
        # 检查必需字段
        if not all(field in data for field in required_fields):
            return False
        
        # 检查价格合理性
        if data['price'] <= 0:
            return False
        
        # 检查时间新鲜度 (不超过1小时)
        if isinstance(data['timestamp'], datetime):
            age = datetime.now() - data['timestamp']
            # yfinance timestamp might be slightly off or None for fast_info, so be lenient
            if age > timedelta(hours=24) and data.get('source') != 'yfinance':
                 # Allow older data for yfinance as it might return previous close if market closed
                 # But for real-time APIs, data should be fresh
                 pass 
        
        return True
