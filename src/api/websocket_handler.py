"""
WebSocket Handler for Real-time Updates
WebSocket实时推送模块
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import asyncio
import json
from datetime import datetime

from ..utils.logger import setup_logging

logger = setup_logging("websocket")


class ConnectionManager:
    """
    WebSocket connection manager
    
    Features:
    - Multiple channels (prices, news, sentiment)
    - Broadcast to specific channels
    - Connection tracking
    """
    
    def __init__(self):
        # Active connections per channel
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "prices": set(),
            "news": set(),
            "sentiment": set(),
            "signals": set(),
            "all": set()
        }
        
        # Connection metadata
        self.connection_info: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, channel: str = "all"):
        """Accept new connection and add to channel"""
        await websocket.accept()
        
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        
        self.active_connections[channel].add(websocket)
        self.active_connections["all"].add(websocket)
        
        self.connection_info[websocket] = {
            "channel": channel,
            "connected_at": datetime.now().isoformat(),
            "messages_sent": 0
        }
        
        logger.info(f"New connection to channel '{channel}'. Active: {len(self.active_connections[channel])}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection from all channels"""
        for channel in self.active_connections.values():
            channel.discard(websocket)
        
        if websocket in self.connection_info:
            del self.connection_info[websocket]
        
        logger.info("Connection closed")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific connection"""
        try:
            await websocket.send_json(message)
            if websocket in self.connection_info:
                self.connection_info[websocket]["messages_sent"] += 1
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def broadcast(self, message: dict, channel: str = "all"):
        """Broadcast message to all connections in channel"""
        if channel not in self.active_connections:
            return
        
        disconnected = []
        
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
                if connection in self.connection_info:
                    self.connection_info[connection]["messages_sent"] += 1
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)
    
    def get_connection_count(self, channel: str = "all") -> int:
        """Get number of active connections"""
        return len(self.active_connections.get(channel, set()))


# Global manager instance
manager = ConnectionManager()


async def price_stream_handler(websocket: WebSocket, symbols: List[str]):
    """
    Stream real-time price updates
    
    Args:
        websocket: WebSocket connection
        symbols: List of symbols to track
    """
    from ..data_collection.price_fetcher import PriceFetcher
    
    fetcher = PriceFetcher()
    
    while True:
        try:
            prices = fetcher.fetch_latest_prices(symbols)
            
            message = {
                "type": "price_update",
                "timestamp": datetime.now().isoformat(),
                "data": prices
            }
            
            await websocket.send_json(message)
            
            # Update every 30 seconds
            await asyncio.sleep(30)
            
        except WebSocketDisconnect:
            break
        except Exception as e:
            logger.error(f"Price stream error: {e}")
            await asyncio.sleep(5)


async def sentiment_stream_handler(websocket: WebSocket, symbol: str):
    """
    Stream real-time sentiment updates
    """
    from ..data_collection.news_fetcher import NewsFetcher
    from ..nlp.finbert_analyzer import FinBERTAnalyzer
    from ..nlp.sentiment_metrics import SentimentMetricsEngine
    
    fetcher = NewsFetcher()
    engine = SentimentMetricsEngine()
    
    try:
        analyzer = FinBERTAnalyzer()
    except Exception:
        analyzer = None
    
    while True:
        try:
            # Fetch recent news
            df = fetcher.fetch_precious_metals_news(limit=20)
            
            # Analyze sentiment
            if analyzer and not df.empty:
                df = analyzer.analyze_dataframe(df)
            
            # Get dashboard
            dashboard = engine.get_realtime_dashboard(df, symbol)
            
            message = {
                "type": "sentiment_update",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "symbol": dashboard.symbol,
                    "current_sentiment": dashboard.current_sentiment,
                    "sentiment_label": dashboard.sentiment_label,
                    "trend": dashboard.trend,
                    "news_volume_24h": dashboard.news_volume_24h,
                    "bullish_ratio": dashboard.bullish_ratio,
                    "bearish_ratio": dashboard.bearish_ratio,
                    "heat_index": dashboard.heat_index
                }
            }
            
            await websocket.send_json(message)
            
            # Update every 5 minutes
            await asyncio.sleep(300)
            
        except WebSocketDisconnect:
            break
        except Exception as e:
            logger.error(f"Sentiment stream error: {e}")
            await asyncio.sleep(30)


def setup_websocket_routes(app):
    """Setup WebSocket routes on FastAPI app"""
    
    @app.websocket("/ws/prices")
    async def websocket_prices(websocket: WebSocket):
        """WebSocket endpoint for price updates"""
        await manager.connect(websocket, "prices")
        
        try:
            # Get symbols from query params or use defaults
            symbols = ["GLD", "SLV", "IAU"]
            await price_stream_handler(websocket, symbols)
        except WebSocketDisconnect:
            manager.disconnect(websocket)
    
    @app.websocket("/ws/sentiment/{symbol}")
    async def websocket_sentiment(websocket: WebSocket, symbol: str):
        """WebSocket endpoint for sentiment updates"""
        await manager.connect(websocket, "sentiment")
        
        try:
            await sentiment_stream_handler(websocket, symbol)
        except WebSocketDisconnect:
            manager.disconnect(websocket)
    
    @app.websocket("/ws/all")
    async def websocket_all(websocket: WebSocket):
        """WebSocket endpoint for all updates"""
        await manager.connect(websocket, "all")
        
        try:
            while True:
                # Wait for messages from client
                data = await websocket.receive_text()
                
                # Echo or process command
                response = {
                    "type": "ack",
                    "received": data,
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_json(response)
                
        except WebSocketDisconnect:
            manager.disconnect(websocket)
    
    logger.info("WebSocket routes configured")
