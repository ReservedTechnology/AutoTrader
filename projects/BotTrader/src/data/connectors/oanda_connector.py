"""
OANDA v20 API Connector for Real-time Forex Data
Production-grade implementation with <50ms latency target
"""
import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, AsyncGenerator
from decimal import Decimal
import time
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class OandaV20Connector:
    """
    High-performance OANDA v20 API connector
    Handles streaming data for 6 priority forex pairs with automatic reconnection
    """
    
    # API endpoints
    PRACTICE_API = "https://api-fxpractice.oanda.com"
    LIVE_API = "https://api-fxtrade.oanda.com"
    PRACTICE_STREAM = "https://stream-fxpractice.oanda.com"
    LIVE_STREAM = "https://stream-fxtrade.oanda.com"
    
    def __init__(self, api_key: str, account_id: str, environment: str = 'practice'):
        """
        Initialize OANDA connector
        
        Args:
            api_key: OANDA API key
            account_id: Trading account ID
            environment: 'practice' or 'live'
        """
        self.api_key = api_key
        self.account_id = account_id
        self.environment = environment
        
        # Set endpoints based on environment
        if environment == 'live':
            self.api_url = self.LIVE_API
            self.stream_url = self.LIVE_STREAM
        else:
            self.api_url = self.PRACTICE_API
            self.stream_url = self.PRACTICE_STREAM
        
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept-Datetime-Format': 'RFC3339'
        }
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.streams: List[aiohttp.ClientResponse] = []
        self._connected = False
        self._reconnect_delay = 1  # Start with 1 second
        self._max_reconnect_delay = 30
    
    async def initialize(self):
        """Initialize HTTP session and verify connection"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
        
        # Verify authentication
        await self.authenticate()
        self._connected = True
        logger.info(f"OANDA connector initialized for {self.environment} environment")
    
    async def authenticate(self) -> Dict[str, Any]:
        """
        Authenticate with OANDA API
        
        Returns:
            Authentication status and account details
        """
        try:
            url = f"{self.api_url}/v3/accounts/{self.account_id}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'authenticated': True,
                        'account_id': data['account']['id'],
                        'environment': self.environment,
                        'currency': data['account'].get('currency', 'USD'),
                        'balance': data['account'].get('balance', '0')
                    }
                else:
                    error = await response.text()
                    logger.error(f"Authentication failed: {error}")
                    return {
                        'authenticated': False,
                        'error': error
                    }
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return {
                'authenticated': False,
                'error': str(e)
            }
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get detailed account information
        
        Returns:
            Account details including balance, margin, positions
        """
        url = f"{self.api_url}/v3/accounts/{self.account_id}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data['account']
            else:
                raise Exception(f"Failed to get account info: {response.status}")
    
    async def get_instruments(self) -> List[Dict[str, Any]]:
        """
        Get list of tradeable instruments
        
        Returns:
            List of available forex pairs with details
        """
        url = f"{self.api_url}/v3/accounts/{self.account_id}/instruments"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                
                # Add current spread information
                instruments = data['instruments']
                
                # Get current prices for spread calculation
                symbols = [inst['name'] for inst in instruments[:50]]  # Limit for API
                prices = await self.get_current_prices(symbols)
                
                for inst in instruments:
                    if inst['name'] in prices:
                        price = prices[inst['name']]
                        if 'bid' in price and 'ask' in price:
                            spread_pips = (float(price['ask']) - float(price['bid'])) * 10000
                            inst['spread'] = round(spread_pips, 2)
                    
                    # Ensure tradeable status
                    inst['tradeable'] = inst.get('type') in ['CURRENCY', 'CFD']
                
                return instruments
            else:
                raise Exception(f"Failed to get instruments: {response.status}")
    
    async def get_current_prices(self, instruments: List[str]) -> Dict[str, Dict]:
        """
        Get current prices for specified instruments
        
        Args:
            instruments: List of instrument names
        
        Returns:
            Dictionary of current prices by instrument
        """
        # OANDA limits to 50 instruments per request
        instruments = instruments[:50]
        params = {'instruments': ','.join(instruments)}
        
        url = f"{self.api_url}/v3/accounts/{self.account_id}/pricing"
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                prices = {}
                
                for price in data.get('prices', []):
                    prices[price['instrument']] = {
                        'bid': price['bids'][0]['price'] if price['bids'] else None,
                        'ask': price['asks'][0]['price'] if price['asks'] else None,
                        'time': price['time'],
                        'tradeable': price.get('tradeable', False)
                    }
                
                return prices
            else:
                raise Exception(f"Failed to get prices: {response.status}")
    
    async def create_price_stream(
        self, 
        params: Dict[str, str]
    ) -> AsyncGenerator[Dict, None]:
        """
        Create streaming price connection
        
        Args:
            params: Stream parameters including instruments
        
        Yields:
            Price update dictionaries
        """
        url = f"{self.stream_url}/v3/accounts/{self.account_id}/pricing/stream"
        
        try:
            async with self.session.get(url, params=params) as response:
                self.streams.append(response)
                
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line)
                            yield data
                        except json.JSONDecodeError:
                            continue
                        
        except asyncio.CancelledError:
            logger.info("Stream cancelled")
            raise
        except Exception as e:
            logger.error(f"Stream error: {e}")
            # Attempt reconnection
            await self._reconnect_stream(params)
    
    async def _reconnect_stream(self, params: Dict[str, str]):
        """Handle stream reconnection with exponential backoff"""
        while self._connected:
            try:
                await asyncio.sleep(self._reconnect_delay)
                
                logger.info(f"Attempting reconnection after {self._reconnect_delay}s")
                
                # Recreate stream
                async for data in self.create_price_stream(params):
                    yield data
                
                # Reset delay on successful reconnection
                self._reconnect_delay = 1
                break
                
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, 
                    self._max_reconnect_delay
                )
    
    async def create_order(self, order_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a market or limit order
        
        Args:
            order_request: Order specifications
        
        Returns:
            Order creation response
        """
        url = f"{self.api_url}/v3/accounts/{self.account_id}/orders"
        
        body = {'order': order_request}
        
        async with self.session.post(url, json=body) as response:
            data = await response.json()
            
            if response.status in [200, 201]:
                return data
            else:
                logger.error(f"Order creation failed: {data}")
                return data
    
    async def get_pending_orders(self) -> List[Dict[str, Any]]:
        """
        Get list of pending orders
        
        Returns:
            List of pending order details
        """
        url = f"{self.api_url}/v3/accounts/{self.account_id}/pendingOrders"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('orders', [])
            else:
                return []
    
    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get list of open positions
        
        Returns:
            List of open position details
        """
        url = f"{self.api_url}/v3/accounts/{self.account_id}/openPositions"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('positions', [])
            else:
                return []
    
    async def get_candles(
        self,
        instrument: str,
        granularity: str,
        from_time: datetime,
        to_time: datetime,
        price: str = 'M'  # Mid prices
    ) -> List[Dict[str, Any]]:
        """
        Get historical candlestick data
        
        Args:
            instrument: Forex pair
            granularity: Time period (M5, M15, H1, H4, D)
            from_time: Start time
            to_time: End time
            price: Price type (M=mid, B=bid, A=ask)
        
        Returns:
            List of candles
        """
        url = f"{self.api_url}/v3/instruments/{instrument}/candles"
        
        params = {
            'granularity': granularity,
            'from': from_time.isoformat() + 'Z',
            'to': to_time.isoformat() + 'Z',
            'price': price
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('candles', [])
            else:
                raise Exception(f"Failed to get candles: {response.status}")
    
    async def disconnect_stream(self, stream: AsyncGenerator):
        """
        Disconnect a specific stream
        
        Args:
            stream: Stream to disconnect
        """
        # Cancel the stream task
        if stream in self.streams:
            self.streams.remove(stream)
        
        # Stream will be closed automatically when generator is garbage collected
        logger.info("Stream disconnected")
    
    async def is_connected(self) -> bool:
        """
        Check if connector is connected
        
        Returns:
            Connection status
        """
        if not self._connected:
            return False
        
        # Verify with a simple API call
        try:
            await self.get_account_info()
            return True
        except:
            self._connected = False
            
            # Try to reconnect
            await self.initialize()
            return self._connected
    
    async def close(self):
        """Close all connections and cleanup"""
        self._connected = False
        
        # Close all streams
        for stream in self.streams:
            try:
                stream.close()
            except:
                pass
        
        self.streams.clear()
        
        # Close session
        if self.session:
            await self.session.close()
            self.session = None
        
        logger.info("OANDA connector closed")