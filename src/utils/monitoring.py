"""
Prometheus Metrics and Monitoring
Prometheus监控指标模块
"""

from functools import wraps
import time
from typing import Dict, Optional, Callable, Any
from contextlib import contextmanager

from ..utils.logger import setup_logging
from ..utils.config import get_settings

logger = setup_logging("monitoring")
settings = get_settings()


# Try to import prometheus_client
try:
    from prometheus_client import Counter, Gauge, Histogram, Summary, Info
    from prometheus_client import start_http_server, generate_latest, REGISTRY
    from prometheus_client import CollectorRegistry, multiprocess
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed. Using mock metrics.")


# ============================================================================
# Metric Definitions
# ============================================================================

class MetricsRegistry:
    """
    Central registry for all Prometheus metrics
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._init_metrics()
    
    def _init_metrics(self):
        """Initialize all metrics"""
        
        if not PROMETHEUS_AVAILABLE:
            self._create_mock_metrics()
            return
        
        # ========== Data Collection Metrics ==========
        self.data_fetch_total = Counter(
            'precious_metals_data_fetch_total',
            'Total number of data fetch operations',
            ['source', 'symbol', 'status']
        )
        
        self.data_fetch_duration = Histogram(
            'precious_metals_data_fetch_duration_seconds',
            'Duration of data fetch operations',
            ['source', 'symbol'],
            buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
        )
        
        self.data_rows_fetched = Counter(
            'precious_metals_data_rows_total',
            'Total rows of data fetched',
            ['source', 'symbol']
        )
        
        # ========== Model Metrics ==========
        self.model_prediction_total = Counter(
            'precious_metals_predictions_total',
            'Total number of predictions made',
            ['model', 'symbol']
        )
        
        self.model_prediction_latency = Histogram(
            'precious_metals_prediction_latency_seconds',
            'Prediction latency in seconds',
            ['model'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1]
        )
        
        self.model_accuracy = Gauge(
            'precious_metals_model_accuracy',
            'Model accuracy metric',
            ['model', 'metric_type']
        )
        
        # ========== Sentiment Metrics ==========
        self.sentiment_analysis_total = Counter(
            'precious_metals_sentiment_analysis_total',
            'Total sentiment analyses performed',
            ['analyzer', 'status']
        )
        
        self.sentiment_score = Gauge(
            'precious_metals_current_sentiment',
            'Current aggregated sentiment score',
            ['symbol']
        )
        
        self.news_volume = Gauge(
            'precious_metals_news_volume_24h',
            'News volume in last 24 hours',
            ['symbol']
        )
        
        # ========== ETF Metrics ==========
        self.etf_flow = Gauge(
            'precious_metals_etf_flow',
            'Current ETF fund flow',
            ['symbol', 'flow_type']
        )
        
        self.etf_alerts_total = Counter(
            'precious_metals_etf_alerts_total',
            'Total ETF alerts generated',
            ['symbol', 'severity']
        )
        
        # ========== API Metrics ==========
        self.api_requests_total = Counter(
            'precious_metals_api_requests_total',
            'Total API requests',
            ['endpoint', 'method', 'status']
        )
        
        self.api_request_duration = Histogram(
            'precious_metals_api_request_duration_seconds',
            'API request duration',
            ['endpoint', 'method'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5]
        )
        
        self.websocket_connections = Gauge(
            'precious_metals_websocket_connections',
            'Current WebSocket connections',
            ['stream_type']
        )
        
        # ========== System Metrics ==========
        self.kafka_messages_sent = Counter(
            'precious_metals_kafka_messages_sent_total',
            'Total Kafka messages sent',
            ['topic']
        )
        
        self.kafka_messages_received = Counter(
            'precious_metals_kafka_messages_received_total',
            'Total Kafka messages received',
            ['topic']
        )
        
        self.db_query_duration = Histogram(
            'precious_metals_db_query_duration_seconds',
            'Database query duration',
            ['operation'],
            buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1]
        )
        
        # ========== Backtest Metrics ==========
        self.backtest_runs_total = Counter(
            'precious_metals_backtest_runs_total',
            'Total backtest runs',
            ['strategy']
        )
        
        self.backtest_sharpe = Gauge(
            'precious_metals_backtest_sharpe_ratio',
            'Latest backtest Sharpe ratio',
            ['strategy']
        )
        
        self.backtest_return = Gauge(
            'precious_metals_backtest_return',
            'Latest backtest return percentage',
            ['strategy']
        )
        
        # ========== Info Metric ==========
        self.app_info = Info(
            'precious_metals_app',
            'Application information'
        )
        self.app_info.info({
            'version': '1.0.0',
            'environment': settings.environment if hasattr(settings, 'environment') else 'development'
        })
        
        logger.info("Prometheus metrics initialized")
    
    def _create_mock_metrics(self):
        """Create mock metrics when prometheus_client not available"""
        
        class MockMetric:
            def labels(self, *args, **kwargs):
                return self
            def inc(self, *args, **kwargs):
                pass
            def dec(self, *args, **kwargs):
                pass
            def set(self, *args, **kwargs):
                pass
            def observe(self, *args, **kwargs):
                pass
            def info(self, *args, **kwargs):
                pass
        
        self.data_fetch_total = MockMetric()
        self.data_fetch_duration = MockMetric()
        self.data_rows_fetched = MockMetric()
        self.model_prediction_total = MockMetric()
        self.model_prediction_latency = MockMetric()
        self.model_accuracy = MockMetric()
        self.sentiment_analysis_total = MockMetric()
        self.sentiment_score = MockMetric()
        self.news_volume = MockMetric()
        self.etf_flow = MockMetric()
        self.etf_alerts_total = MockMetric()
        self.api_requests_total = MockMetric()
        self.api_request_duration = MockMetric()
        self.websocket_connections = MockMetric()
        self.kafka_messages_sent = MockMetric()
        self.kafka_messages_received = MockMetric()
        self.db_query_duration = MockMetric()
        self.backtest_runs_total = MockMetric()
        self.backtest_sharpe = MockMetric()
        self.backtest_return = MockMetric()
        self.app_info = MockMetric()


# Global metrics instance
metrics = MetricsRegistry()


# ============================================================================
# Decorators and Context Managers
# ============================================================================

def track_time(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """
    Decorator to track function execution time
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            histogram = getattr(metrics, metric_name, None)
            
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                if histogram and labels:
                    histogram.labels(**labels).observe(duration)
        
        return wrapper
    return decorator


@contextmanager
def timer(histogram, labels: Dict[str, str]):
    """
    Context manager for timing operations
    """
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        if hasattr(histogram, 'labels'):
            histogram.labels(**labels).observe(duration)


def count_request(endpoint: str, method: str, status: int):
    """Track API request"""
    metrics.api_requests_total.labels(
        endpoint=endpoint,
        method=method,
        status=str(status)
    ).inc()


def track_data_fetch(source: str, symbol: str, status: str, duration: float, rows: int = 0):
    """Track data fetch operation"""
    metrics.data_fetch_total.labels(source=source, symbol=symbol, status=status).inc()
    metrics.data_fetch_duration.labels(source=source, symbol=symbol).observe(duration)
    if rows > 0:
        metrics.data_rows_fetched.labels(source=source, symbol=symbol).inc(rows)


def track_prediction(model: str, symbol: str, latency: float):
    """Track prediction"""
    metrics.model_prediction_total.labels(model=model, symbol=symbol).inc()
    metrics.model_prediction_latency.labels(model=model).observe(latency)


def update_sentiment(symbol: str, score: float, news_count: int):
    """Update current sentiment metrics"""
    metrics.sentiment_score.labels(symbol=symbol).set(score)
    metrics.news_volume.labels(symbol=symbol).set(news_count)


def track_alert(symbol: str, severity: str):
    """Track ETF alert"""
    metrics.etf_alerts_total.labels(symbol=symbol, severity=severity).inc()


def update_model_accuracy(model: str, metric_type: str, value: float):
    """Update model accuracy metric"""
    metrics.model_accuracy.labels(model=model, metric_type=metric_type).set(value)


def update_backtest_results(strategy: str, sharpe: float, total_return: float):
    """Update backtest results"""
    metrics.backtest_runs_total.labels(strategy=strategy).inc()
    metrics.backtest_sharpe.labels(strategy=strategy).set(sharpe)
    metrics.backtest_return.labels(strategy=strategy).set(total_return)


# ============================================================================
# HTTP Server
# ============================================================================

def start_metrics_server(port: int = 8001):
    """Start Prometheus metrics HTTP server"""
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus not available. Metrics server not started.")
        return False
    
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
        return True
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        return False


def get_metrics() -> str:
    """Get current metrics in Prometheus format"""
    if not PROMETHEUS_AVAILABLE:
        return "# Prometheus not available"
    
    return generate_latest().decode()


# ============================================================================
# FastAPI Integration
# ============================================================================

def create_metrics_middleware():
    """
    Create FastAPI middleware for request metrics
    """
    try:
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import Response
    except ImportError:
        return None
    
    class MetricsMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            start = time.time()
            response = await call_next(request)
            duration = time.time() - start
            
            endpoint = request.url.path
            method = request.method
            status = response.status_code
            
            metrics.api_requests_total.labels(
                endpoint=endpoint,
                method=method,
                status=str(status)
            ).inc()
            
            metrics.api_request_duration.labels(
                endpoint=endpoint,
                method=method
            ).observe(duration)
            
            return response
    
    return MetricsMiddleware


if __name__ == "__main__":
    print("Testing Prometheus Monitoring...")
    
    # Test metrics
    track_data_fetch("yahoo", "GLD", "success", 1.5, 100)
    track_prediction("lstm", "GLD", 0.05)
    update_sentiment("GLD", 0.65, 47)
    track_alert("GLD", "high")
    update_backtest_results("ma_crossover", 1.25, 15.5)
    
    print("Metrics recorded successfully!")
    
    # Print current metrics
    if PROMETHEUS_AVAILABLE:
        print("\nCurrent metrics:")
        print(get_metrics()[:500] + "...")
    else:
        print("\n(Prometheus not installed - using mock metrics)")
