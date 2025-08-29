"""
TraderMade WebSocket Connector for Ultra-Low Latency Forex Streaming
Production-grade implementation with <50ms latency target
"""
import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator
from collections import deque
import time

logger = logging.getLogger(__name__)


class TraderMadeConnector:
    """
    TraderMade WebSocket connector for real-time forex streaming
    Provides ultra-low latency data feed with automatic reconnection
    """
    
    WEBSOCKET_URL = "wss://marketdata.tradermade.com/feedadv"
    
    def __init__(self, api_key: str):
        """
        Initialize TraderMade connector
        
        Args:
            api_key: TraderMade API key
        """
        self.api_key = api_key
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.subscribed_pairs: List[str] = []
        self._connected = False
        self._reconnect_delay = 1
        self._max_reconnect_delay = 30
        self._should_reconnect = True
        
        # Data buffer for disconnect scenarios
        self.buffer = deque(maxlen=1000)
        self._buffer_enabled = True
        
        # Connection statistics
        self.connection_stats = {
            'connects': 0,
            'disconnects': 0,
            'messages_received': 0,
            'last_message_time': None,
            'average_latency_ms': 0,
            'latency_samples': deque(maxlen=100)
        }
    
    async def initialize(self):
        """Initialize WebSocket connection"""
        await self.connect_websocket()
        logger.info("TraderMade connector initialized")
    
    async def connect_websocket(self) -> bool:
        """
        Establish WebSocket connection
        
        Returns:
            True if connection successful
        """
        try:
            self.websocket = await websockets.connect(
                self.WEBSOCKET_URL,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            # Send authentication
            auth_message = {
                "userKey": self.api_key,
                "symbol": "EURUSD"  # Default symbol to start stream
            }
            
            await self.websocket.send(json.dumps(auth_message))
            
            # Wait for connection confirmation
            response = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=5.0
            )
            
            data = json.loads(response)
            
            if data.get('event') == 'connected' or 'price' in data:
                self._connected = True
                self.connection_stats['connects'] += 1
                self._reconnect_delay = 1  # Reset delay on successful connection
                logger.info("TraderMade WebSocket connected successfully")
                return True
            else:
                logger.error(f"Unexpected connection response: {data}")
                return False
                
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self._connected = False
            return False
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return (
            self._connected and 
            self.websocket is not None and 
            not self.websocket.closed
        )
    
    async def subscribe(self, pairs: List[str]) -> Dict[str, Any]:
        """
        Subscribe to forex pairs
        
        Args:
            pairs: List of currency pairs (e.g., ['EURUSD', 'GBPJPY'])
        
        Returns:
            Subscription result
        """
        if not self.is_connected():
            await self.connect_websocket()
        
        try:
            # TraderMade format: comma-separated symbols
            symbols = ','.join(pairs)
            
            subscribe_message = {
                "userKey": self.api_key,
                "symbol": symbols
            }
            
            await self.websocket.send(json.dumps(subscribe_message))
            
            self.subscribed_pairs = pairs
            
            logger.info(f"Subscribed to: {pairs}")
            
            return {
                'success': True,
                'subscribed_pairs': pairs
            }
            
        except Exception as e:
            logger.error(f"Subscription failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'subscribed_pairs': []
            }
    
    async def stream_prices(self) -> AsyncGenerator[Dict, None]:
        """
        Stream real-time price data
        
        Yields:
            Price update dictionaries
        """
        while self._should_reconnect:
            try:
                if not self.is_connected():
                    await self._reconnect()
                    
                    # Resubscribe to pairs after reconnection
                    if self.subscribed_pairs:
                        await self.subscribe(self.subscribed_pairs)
                
                # Receive message
                message = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=30.0  # 30 second timeout
                )
                
                data = json.loads(message)
                
                # Process price data
                if 'symbol' in data and 'bid' in data and 'ask' in data:
                    # Calculate latency if timestamp provided
                    if 'ts' in data:
                        server_time = data['ts']
                        local_time = time.time() * 1000  # Convert to milliseconds
                        latency = abs(local_time - server_time)
                        
                        self.connection_stats['latency_samples'].append(latency)
                        self.connection_stats['average_latency_ms'] = (
                            sum(self.connection_stats['latency_samples']) / 
                            len(self.connection_stats['latency_samples'])
                        )
                    
                    # Format price data
                    price_data = {
                        'symbol': data['symbol'],
                        'timestamp': data.get('ts', time.time() * 1000) / 1000,
                        'bid': float(data['bid']),
                        'ask': float(data['ask']),
                        'mid': float(data.get('mid', (data['bid'] + data['ask']) / 2))
                    }
                    
                    # Update statistics
                    self.connection_stats['messages_received'] += 1
                    self.connection_stats['last_message_time'] = datetime.utcnow()
                    
                    # Buffer data if enabled
                    if self._buffer_enabled:
                        self.buffer.append(price_data)
                    
                    yield price_data
                
            except asyncio.TimeoutError:
                logger.warning("No data received for 30 seconds, checking connection")
                if not self.is_connected():
                    await self._reconnect()
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self._connected = False
                self.connection_stats['disconnects'] += 1
                await self._reconnect()
                
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await asyncio.sleep(1)
    
    async def _reconnect(self):
        """Handle reconnection with exponential backoff"""
        if not self._should_reconnect:
            return
        
        logger.info(f"Attempting reconnection in {self._reconnect_delay}s")
        await asyncio.sleep(self._reconnect_delay)
        
        success = await self.connect_websocket()
        
        if success:
            self._reconnect_delay = 1
            logger.info("Reconnection successful")
        else:
            self._reconnect_delay = min(
                self._reconnect_delay * 2,
                self._max_reconnect_delay
            )
            logger.error(f"Reconnection failed, next attempt in {self._reconnect_delay}s")
    
    async def disconnect(self):
        """Disconnect WebSocket"""
        self._connected = False
        self._should_reconnect = False
        
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            
            self.websocket = None
        
        logger.info("TraderMade WebSocket disconnected")
    
    async def get_buffer_size(self) -> int:
        """Get current buffer size configuration"""
        return self.buffer.maxlen
    
    def get_buffered_data(self) -> List[Dict]:
        """Get buffered data during disconnection"""
        return list(self.buffer)
    
    def clear_buffer(self):
        """Clear data buffer"""
        self.buffer.clear()
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return self.connection_stats.copy()
    
    async def send_heartbeat(self):
        """Send heartbeat to keep connection alive"""
        if self.is_connected():
            try:
                heartbeat = {"event": "heartbeat"}
                await self.websocket.send(json.dumps(heartbeat))
                return True
            except:
                return False
        return False
    
    async def close(self):
        """Close WebSocket connection and cleanup"""
        await self.disconnect()
        logger.info("TraderMade connector closed")


class TraderMadeRESTConnector:
    """
    TraderMade REST API connector for historical data
    Supplements WebSocket with historical data capabilities
    """
    
    BASE_URL = "https://marketdata.tradermade.com/api/v1"
    
    def __init__(self, api_key: str):
        """
        Initialize REST API connector
        
        Args:
            api_key: TraderMade API key
        """
        self.api_key = api_key
    
    async def get_historical_data(
        self,
        currency_pair: str,
        date_from: str,
        date_to: str,
        interval: str = 'daily'
    ) -> List[Dict[str, Any]]:
        """
        Get historical forex data
        
        Args:
            currency_pair: Currency pair (e.g., 'EURUSD')
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            interval: Data interval (minute, hourly, daily)
        
        Returns:
            List of historical price records
        """
        import aiohttp
        
        endpoint = f"{self.BASE_URL}/timeseries"
        
        params = {
            'currency': currency_pair,
            'api_key': self.api_key,
            'start_date': date_from,
            'end_date': date_to,
            'interval': interval
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'quotes' in data:
                        return data['quotes']
                    
                    return []
                else:
                    error = await response.text()
                    raise Exception(f"API error: {error}")
    
    async def get_live_quote(
        self,
        currency_pairs: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Get current quotes for multiple pairs
        
        Args:
            currency_pairs: List of currency pairs
        
        Returns:
            Dictionary of current quotes
        """
        import aiohttp
        
        endpoint = f"{self.BASE_URL}/live"
        
        params = {
            'currency': ','.join(currency_pairs),
            'api_key': self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    quotes = {}
                    if 'quotes' in data:
                        for quote in data['quotes']:
                            quotes[quote['instrument']] = {
                                'bid': quote['bid'],
                                'ask': quote['ask'],
                                'mid': quote['mid']
                            }
                    
                    return quotes
                else:
                    error = await response.text()
                    raise Exception(f"API error: {error}")