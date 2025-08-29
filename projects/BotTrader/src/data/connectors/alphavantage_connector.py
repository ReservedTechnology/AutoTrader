"""
Alpha Vantage API Connector for Historical Forex Data
Handles technical indicators and economic data with rate limiting
"""
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
from collections import deque
import time

logger = logging.getLogger(__name__)


class AlphaVantageConnector:
    """
    Alpha Vantage API connector for historical forex data and indicators
    Handles rate limiting for free tier (5 calls/minute)
    """
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    # Rate limiting
    FREE_TIER_LIMIT = 5  # calls per minute
    PREMIUM_TIER_LIMIT = 75  # calls per minute
    
    def __init__(self, api_key: str, premium: bool = False):
        """
        Initialize Alpha Vantage connector
        
        Args:
            api_key: Alpha Vantage API key
            premium: Whether using premium tier
        """
        self.api_key = api_key
        self.premium = premium
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting setup
        self.rate_limit = self.PREMIUM_TIER_LIMIT if premium else self.FREE_TIER_LIMIT
        self.call_times = deque(maxlen=self.rate_limit)
        self.rate_limit_remaining = self.rate_limit
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize HTTP session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        
        self._initialized = True
        logger.info(f"Alpha Vantage connector initialized ({'premium' if self.premium else 'free'} tier)")
    
    async def _rate_limit_check(self):
        """Check and enforce rate limiting"""
        now = time.time()
        
        # Remove calls older than 1 minute
        while self.call_times and now - self.call_times[0] > 60:
            self.call_times.popleft()
        
        # If at limit, wait
        if len(self.call_times) >= self.rate_limit:
            wait_time = 61 - (now - self.call_times[0])
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                # Clear old calls after waiting
                self.call_times.clear()
        
        # Record this call
        self.call_times.append(now)
        self.rate_limit_remaining = self.rate_limit - len(self.call_times)
    
    async def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make API request with rate limiting
        
        Args:
            params: Request parameters
        
        Returns:
            API response data
        """
        await self._rate_limit_check()
        
        params['apikey'] = self.api_key
        
        try:
            async with self.session.get(self.BASE_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check for API errors
                    if 'Error Message' in data:
                        raise Exception(f"API Error: {data['Error Message']}")
                    if 'Note' in data:
                        # Rate limit message
                        raise Exception(f"API Note: {data['Note']}")
                    
                    return data
                else:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")
                    
        except Exception as e:
            logger.error(f"Alpha Vantage request failed: {e}")
            raise
    
    async def check_api_status(self) -> Dict[str, Any]:
        """
        Check API authentication and status
        
        Returns:
            API status information
        """
        try:
            # Make a simple request to verify API key
            params = {
                'function': 'CURRENCY_EXCHANGE_RATE',
                'from_currency': 'EUR',
                'to_currency': 'USD'
            }
            
            result = await self._make_request(params)
            
            return {
                'authenticated': True,
                'rate_limit_remaining': self.rate_limit_remaining,
                'api_tier': 'premium' if self.premium else 'free'
            }
        except Exception as e:
            return {
                'authenticated': False,
                'error': str(e),
                'rate_limit_remaining': 0,
                'api_tier': 'unknown'
            }
    
    async def get_fx_daily(
        self, 
        from_symbol: str, 
        to_symbol: str
    ) -> List[Dict[str, Any]]:
        """
        Get daily forex data
        
        Args:
            from_symbol: From currency (e.g., 'EUR')
            to_symbol: To currency (e.g., 'USD')
        
        Returns:
            List of daily OHLC records
        """
        params = {
            'function': 'FX_DAILY',
            'from_symbol': from_symbol,
            'to_symbol': to_symbol,
            'outputsize': 'full'  # Get full history
        }
        
        data = await self._make_request(params)
        
        if 'Time Series FX (Daily)' in data:
            time_series = data['Time Series FX (Daily)']
            
            records = []
            for date, values in time_series.items():
                records.append({
                    'date': date,
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close'])
                })
            
            # Sort by date (newest first)
            records.sort(key=lambda x: x['date'], reverse=True)
            
            return records
        
        return []
    
    async def get_fx_intraday(
        self,
        from_symbol: str,
        to_symbol: str,
        interval: str = '5min'
    ) -> List[Dict[str, Any]]:
        """
        Get intraday forex data
        
        Args:
            from_symbol: From currency
            to_symbol: To currency
            interval: Time interval (1min, 5min, 15min, 30min, 60min)
        
        Returns:
            List of intraday records
        """
        params = {
            'function': 'FX_INTRADAY',
            'from_symbol': from_symbol,
            'to_symbol': to_symbol,
            'interval': interval,
            'outputsize': 'full'
        }
        
        data = await self._make_request(params)
        
        # The key changes based on interval
        key = f'Time Series FX ({interval})'
        
        if key in data:
            time_series = data[key]
            
            records = []
            for timestamp, values in time_series.items():
                records.append({
                    'timestamp': timestamp,
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close'])
                })
            
            # Sort by timestamp (newest first)
            records.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return records
        
        return []
    
    async def get_technical_indicator(
        self,
        function: str,
        symbol: str,
        interval: str = '5min',
        time_period: int = None,
        series_type: str = 'close',
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Get technical indicator data
        
        Args:
            function: Indicator function (RSI, MACD, BBANDS, etc.)
            symbol: Currency pair (e.g., 'EURUSD')
            interval: Time interval
            time_period: Period for the indicator
            series_type: Price type (close, open, high, low)
            **kwargs: Additional parameters for specific indicators
        
        Returns:
            List of indicator values
        """
        params = {
            'function': function,
            'symbol': symbol,
            'interval': interval,
            'series_type': series_type
        }
        
        # Add time period if specified
        if time_period:
            params['time_period'] = time_period
        
        # Add any additional parameters (for MACD, etc.)
        params.update(kwargs)
        
        data = await self._make_request(params)
        
        # Find the technical analysis key
        ta_key = None
        for key in data.keys():
            if 'Technical Analysis' in key:
                ta_key = key
                break
        
        if ta_key:
            ta_data = data[ta_key]
            
            records = []
            for timestamp, values in ta_data.items():
                record = {'timestamp': timestamp}
                record.update(values)
                records.append(record)
            
            # Sort by timestamp (newest first)
            records.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return records
        
        return []
    
    async def get_economic_calendar(
        self,
        currency: str = 'USD'
    ) -> List[Dict[str, Any]]:
        """
        Get economic calendar events
        Note: Alpha Vantage doesn't provide economic calendar directly,
        this would need to be sourced elsewhere
        
        Args:
            currency: Currency to filter events
        
        Returns:
            List of economic events
        """
        # Alpha Vantage doesn't provide economic calendar
        # This is a placeholder for integration with other sources
        logger.warning("Economic calendar not available from Alpha Vantage")
        return []
    
    async def get_sector_performance(self) -> Dict[str, Any]:
        """
        Get sector performance data (useful for correlation analysis)
        
        Returns:
            Sector performance data
        """
        params = {
            'function': 'SECTOR'
        }
        
        data = await self._make_request(params)
        
        return data
    
    async def get_market_sentiment(
        self,
        ticker: str = 'FOREX:USD'
    ) -> Dict[str, Any]:
        """
        Get market sentiment indicators
        
        Args:
            ticker: Market ticker
        
        Returns:
            Sentiment data
        """
        params = {
            'function': 'NEWS_SENTIMENT',
            'tickers': ticker
        }
        
        try:
            data = await self._make_request(params)
            return data
        except:
            # News sentiment might require premium
            logger.warning("News sentiment may require premium API")
            return {}
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
        
        self._initialized = False
        logger.info("Alpha Vantage connector closed")