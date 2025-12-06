"""
Kafka Data Pipeline
Kafka实时数据管道
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from abc import ABC, abstractmethod
import threading

from ..utils.logger import setup_logging
from ..utils.config import get_settings

logger = setup_logging("kafka_pipeline")
settings = get_settings()


@dataclass
class DataMessage:
    """Standard data message format"""
    topic: str
    key: str
    value: Dict[str, Any]
    timestamp: datetime
    headers: Optional[Dict[str, str]] = None
    
    def to_json(self) -> str:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "DataMessage":
        data = json.loads(json_str)
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class KafkaProducer:
    """
    Kafka producer for publishing data
    
    Topics:
    - prices: Real-time price updates
    - news: News articles
    - sentiment: Sentiment scores
    - signals: Trading signals
    - alerts: ETF flow alerts
    """
    
    TOPICS = {
        "prices": "precious-metals-prices",
        "news": "precious-metals-news",
        "sentiment": "precious-metals-sentiment",
        "signals": "precious-metals-signals",
        "alerts": "precious-metals-alerts"
    }
    
    def __init__(self, bootstrap_servers: Optional[str] = None):
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.producer = None
        self._initialized = False
        
        self._init_producer()
    
    def _init_producer(self):
        """Initialize Kafka producer"""
        try:
            from kafka import KafkaProducer as KP
            
            self.producer = KP(
                bootstrap_servers=self.bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                retries=3,
                acks="all"
            )
            self._initialized = True
            logger.info(f"Kafka producer connected to {self.bootstrap_servers}")
            
        except ImportError:
            logger.warning("kafka-python not installed. Using mock producer.")
        except Exception as e:
            logger.warning(f"Kafka connection failed: {e}. Using mock producer.")
    
    def send(
        self,
        topic: str,
        key: str,
        value: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send message to Kafka topic
        """
        topic_name = self.TOPICS.get(topic, topic)
        
        message = {
            **value,
            "_timestamp": datetime.now().isoformat(),
            "_key": key
        }
        
        if not self._initialized:
            logger.debug(f"[MOCK] Sending to {topic_name}: {key}")
            return True
        
        try:
            future = self.producer.send(
                topic_name,
                key=key,
                value=message,
                headers=[(k, v.encode()) for k, v in (headers or {}).items()]
            )
            # Wait for send to complete
            future.get(timeout=10)
            logger.debug(f"Sent to {topic_name}: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def send_price_update(self, symbol: str, price_data: Dict) -> bool:
        """Send price update"""
        return self.send("prices", symbol, price_data)
    
    def send_sentiment(self, symbol: str, sentiment_data: Dict) -> bool:
        """Send sentiment update"""
        return self.send("sentiment", symbol, sentiment_data)
    
    def send_signal(self, symbol: str, signal_data: Dict) -> bool:
        """Send trading signal"""
        return self.send("signals", symbol, signal_data)
    
    def send_alert(self, alert_id: str, alert_data: Dict) -> bool:
        """Send ETF alert"""
        return self.send("alerts", alert_id, alert_data)
    
    def flush(self):
        """Flush pending messages"""
        if self._initialized and self.producer:
            self.producer.flush()
    
    def close(self):
        """Close producer"""
        if self._initialized and self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")


class KafkaConsumer:
    """
    Kafka consumer for subscribing to data streams
    """
    
    def __init__(
        self,
        topics: List[str],
        group_id: str = "precious-metals-consumer",
        bootstrap_servers: Optional[str] = None
    ):
        self.topics = [
            KafkaProducer.TOPICS.get(t, t) for t in topics
        ]
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.consumer = None
        self._initialized = False
        self._running = False
        
        self._init_consumer()
    
    def _init_consumer(self):
        """Initialize Kafka consumer"""
        try:
            from kafka import KafkaConsumer as KC
            
            self.consumer = KC(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers.split(","),
                group_id=self.group_id,
                auto_offset_reset="latest",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                enable_auto_commit=True
            )
            self._initialized = True
            logger.info(f"Kafka consumer subscribed to {self.topics}")
            
        except ImportError:
            logger.warning("kafka-python not installed. Using mock consumer.")
        except Exception as e:
            logger.warning(f"Kafka connection failed: {e}. Using mock consumer.")
    
    def consume(
        self,
        handler: Callable[[str, str, Dict], None],
        timeout_ms: int = 1000
    ):
        """
        Start consuming messages
        
        Args:
            handler: Function to handle messages (topic, key, value)
            timeout_ms: Poll timeout in milliseconds
        """
        if not self._initialized:
            logger.info("[MOCK] Consumer started (no actual messages)")
            return
        
        self._running = True
        logger.info("Starting message consumption...")
        
        try:
            while self._running:
                messages = self.consumer.poll(timeout_ms=timeout_ms)
                
                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            handler(
                                record.topic,
                                record.key,
                                record.value
                            )
                        except Exception as e:
                            logger.error(f"Handler error: {e}")
                            
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            self._running = False
    
    def consume_async(
        self,
        handler: Callable[[str, str, Dict], None]
    ) -> threading.Thread:
        """
        Start consuming in a background thread
        """
        thread = threading.Thread(
            target=self.consume,
            args=(handler,),
            daemon=True
        )
        thread.start()
        return thread
    
    def stop(self):
        """Stop consuming"""
        self._running = False
        if self._initialized and self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")


class StreamProcessor(ABC):
    """
    Abstract base class for stream processing
    """
    
    @abstractmethod
    def process(self, topic: str, key: str, value: Dict) -> Optional[Dict]:
        """Process a single message"""
        pass


class PriceFeatureProcessor(StreamProcessor):
    """
    Real-time feature calculation from price stream
    """
    
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.price_buffers: Dict[str, List[float]] = {}
    
    def process(self, topic: str, key: str, value: Dict) -> Optional[Dict]:
        """
        Calculate real-time features from price data
        """
        symbol = key
        price = value.get("close") or value.get("price")
        
        if price is None:
            return None
        
        # Update buffer
        if symbol not in self.price_buffers:
            self.price_buffers[symbol] = []
        
        self.price_buffers[symbol].append(float(price))
        
        # Keep window size
        if len(self.price_buffers[symbol]) > self.window_size:
            self.price_buffers[symbol] = self.price_buffers[symbol][-self.window_size:]
        
        prices = self.price_buffers[symbol]
        
        if len(prices) < 2:
            return None
        
        # Calculate features
        import numpy as np
        prices_arr = np.array(prices)
        
        features = {
            "symbol": symbol,
            "price": price,
            "returns": (prices[-1] / prices[-2] - 1) * 100,
            "ma_short": np.mean(prices_arr[-min(5, len(prices)):]),
            "volatility": np.std(prices_arr) if len(prices) >= 5 else 0,
            "momentum": prices[-1] - prices[0] if len(prices) >= 5 else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        if len(prices) >= self.window_size:
            features["ma_long"] = np.mean(prices_arr)
            features["signal"] = "bullish" if features["ma_short"] > features["ma_long"] else "bearish"
        
        return features


class SentimentAggregator(StreamProcessor):
    """
    Aggregate sentiment scores from news stream
    """
    
    def __init__(self, decay_factor: float = 0.95):
        self.decay_factor = decay_factor
        self.sentiment_accum: Dict[str, float] = {}
        self.message_counts: Dict[str, int] = {}
    
    def process(self, topic: str, key: str, value: Dict) -> Optional[Dict]:
        """
        Aggregate sentiment with exponential decay
        """
        symbol = value.get("symbol", key)
        score = value.get("sentiment_score", 0)
        
        # Exponential moving average
        if symbol in self.sentiment_accum:
            self.sentiment_accum[symbol] = (
                self.decay_factor * self.sentiment_accum[symbol] +
                (1 - self.decay_factor) * score
            )
            self.message_counts[symbol] += 1
        else:
            self.sentiment_accum[symbol] = score
            self.message_counts[symbol] = 1
        
        return {
            "symbol": symbol,
            "current_sentiment": self.sentiment_accum[symbol],
            "message_count": self.message_counts[symbol],
            "timestamp": datetime.now().isoformat()
        }


class DataPipeline:
    """
    Complete data pipeline orchestration
    """
    
    def __init__(self):
        self.producer = KafkaProducer()
        self.consumers: List[KafkaConsumer] = []
        self.processors: Dict[str, StreamProcessor] = {}
    
    def add_processor(self, topic: str, processor: StreamProcessor):
        """Add a stream processor for a topic"""
        self.processors[topic] = processor
    
    def start(self):
        """Start the pipeline"""
        def handle_message(topic: str, key: str, value: Dict):
            # Get processor for topic
            short_topic = topic.replace("precious-metals-", "")
            processor = self.processors.get(short_topic)
            
            if processor:
                result = processor.process(topic, key, value)
                if result:
                    # Forward processed data
                    self.producer.send(f"{short_topic}-processed", key, result)
        
        # Create consumer for all topics with processors
        topics = list(self.processors.keys())
        if topics:
            consumer = KafkaConsumer(topics)
            self.consumers.append(consumer)
            consumer.consume_async(handle_message)
            logger.info(f"Pipeline started for topics: {topics}")
    
    def stop(self):
        """Stop the pipeline"""
        for consumer in self.consumers:
            consumer.stop()
        self.producer.close()
        logger.info("Pipeline stopped")


if __name__ == "__main__":
    # Test Kafka pipeline
    print("Testing Kafka Pipeline...")
    
    # Test producer
    producer = KafkaProducer()
    
    producer.send_price_update("GLD", {
        "price": 185.50,
        "volume": 1234567,
        "change": 0.5
    })
    
    producer.send_sentiment("GLD", {
        "score": 0.65,
        "label": "positive",
        "source": "finbert"
    })
    
    print("Messages sent (mock mode)")
    
    # Test processor
    processor = PriceFeatureProcessor(window_size=10)
    
    for i in range(15):
        result = processor.process(
            "prices", 
            "GLD", 
            {"close": 185 + i * 0.1}
        )
        if result:
            print(f"Processed: {result.get('returns', 0):.2f}% return, signal: {result.get('signal', 'N/A')}")
    
    print("\nKafka pipeline test complete!")
