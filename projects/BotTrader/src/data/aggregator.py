"""
Multi-Source Data Aggregator for Forex Trading
Provides failover, consistency checking, and data fusion
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from statistics import median
import numpy as np

from src.data.connectors.oanda_connector import OandaV20Connector
from src.data.connectors.alphavantage_connector import AlphaVantageConnector
from src.data.connectors.tradermade_connector import TraderMadeConnector

logger = logging.getLogger(__name__)


class DataAggregator:
    """
    Aggregates forex data from multiple sources
    Provides redundancy and consistency validation
    """
    
    def __init__(self):
        """Initialize data aggregator"""
        self.sources = {}
        self.source_status = {}
        self.primary_source = 'oanda'
        self.failover_order = ['oanda', 'tradermade', 'alphavantage']
        
        # Data quality thresholds
        self.max_price_deviation_pips = 5  # Maximum acceptable deviation
        self.stale_data_threshold_seconds = 5
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failovers': 0,
            'consistency_violations': 0
        }
    
    async def initialize_sources(self):
        """Initialize all data source connectors"""
        import os
        
        # Initialize OANDA
        try:
            self.sources['oanda'] = OandaV20Connector(
                api_key=os.getenv('OANDA_API_KEY'),
                account_id=os.getenv('OANDA_ACCOUNT_ID'),
                environment=os.getenv('OANDA_ENVIRONMENT', 'practice')
            )
            await self.sources['oanda'].initialize()
            self.source_status['oanda'] = 'active'
            logger.info("OANDA source initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OANDA: {e}")
            self.source_status['oanda'] = 'failed'
        
        # Initialize TraderMade
        try:
            self.sources['tradermade'] = TraderMadeConnector(
                api_key=os.getenv('TRADERMADE_API_KEY')
            )
            await self.sources['tradermade'].initialize()
            self.source_status['tradermade'] = 'active'
            logger.info("TraderMade source initialized")
        except Exception as e:
            logger.error(f"Failed to initialize TraderMade: {e}")
            self.source_status['tradermade'] = 'failed'
        
        # Initialize Alpha Vantage
        try:
            self.sources['alphavantage'] = AlphaVantageConnector(
                api_key=os.getenv('ALPHA_VANTAGE_API_KEY'),
                premium=False
            )
            await self.sources['alphavantage'].initialize()
            self.source_status['alphavantage'] = 'active'
            logger.info("Alpha Vantage source initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Alpha Vantage: {e}")
            self.source_status['alphavantage'] = 'failed'
        
        # Verify at least one source is active
        active_sources = [s for s, status in self.source_status.items() if status == 'active']
        if not active_sources:
            raise Exception("No data sources available!")
        
        logger.info(f"Data aggregator initialized with {len(active_sources)} active sources")
    
    async def get_aggregated_price(
        self, 
        symbol: str,
        use_all_sources: bool = False
    ) -> Dict[str, Any]:
        """
        Get aggregated price from multiple sources
        
        Args:
            symbol: Currency pair (e.g., 'EURUSD')
            use_all_sources: Whether to query all sources or just primary
        
        Returns:
            Aggregated price data with source information
        """
        self.stats['total_requests'] += 1
        prices = {}
        
        # Convert symbol format for each source
        symbol_formats = {
            'oanda': symbol.replace('/', '_'),  # EUR/USD -> EUR_USD
            'tradermade': symbol.replace('/', ''),  # EUR/USD -> EURUSD
            'alphavantage': symbol  # Uses original format
        }
        
        if use_all_sources:
            # Query all active sources in parallel
            tasks = []
            for source_name, source in self.sources.items():
                if self.source_status.get(source_name) == 'active':
                    tasks.append(
                        self._get_price_from_source(
                            source_name, 
                            source, 
                            symbol_formats[source_name]
                        )
                    )
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, dict) and 'source' in result:
                    prices[result['source']] = result
        else:
            # Use failover mechanism
            for source_name in self.failover_order:
                if (source_name in self.sources and 
                    self.source_status.get(source_name) == 'active'):
                    
                    result = await self._get_price_from_source(
                        source_name,
                        self.sources[source_name],
                        symbol_formats[source_name]
                    )
                    
                    if result:
                        prices[source_name] = result
                        break
                    else:
                        self.stats['failovers'] += 1
                        logger.warning(f"Failed to get price from {source_name}, trying next")
        
        if prices:
            self.stats['successful_requests'] += 1
            
            # Validate consistency if multiple sources
            if len(prices) > 1:
                self._validate_price_consistency(prices)
            
            # Calculate consensus price
            consensus = self._calculate_consensus_price(prices)
            
            return {
                'symbol': symbol,
                'timestamp': datetime.utcnow().isoformat(),
                'consensus': consensus,
                'sources': prices
            }
        else:
            logger.error(f"No prices available for {symbol}")
            return None
    
    async def _get_price_from_source(
        self, 
        source_name: str,
        source: Any,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get price from a specific source
        
        Args:
            source_name: Name of the source
            source: Source connector instance
            symbol: Currency pair in source-specific format
        
        Returns:
            Price data or None if failed
        """
        try:
            if source_name == 'oanda':
                prices = await source.get_current_prices([symbol])
                if symbol in prices:
                    price_data = prices[symbol]
                    return {
                        'source': 'oanda',
                        'bid': float(price_data['bid']),
                        'ask': float(price_data['ask']),
                        'timestamp': price_data['time'],
                        'tradeable': price_data.get('tradeable', True)
                    }
            
            elif source_name == 'tradermade':
                # For TraderMade, we need to get from stream or REST
                rest_connector = TraderMadeRESTConnector(source.api_key)
                quotes = await rest_connector.get_live_quote([symbol])
                
                if symbol in quotes:
                    quote = quotes[symbol]
                    return {
                        'source': 'tradermade',
                        'bid': quote['bid'],
                        'ask': quote['ask'],
                        'mid': quote['mid'],
                        'timestamp': datetime.utcnow().isoformat()
                    }
            
            elif source_name == 'alphavantage':
                # Alpha Vantage doesn't provide real-time streaming
                # Get most recent exchange rate
                from_curr = symbol[:3]
                to_curr = symbol[3:6] if len(symbol) == 6 else symbol[4:7]
                
                params = {
                    'function': 'CURRENCY_EXCHANGE_RATE',
                    'from_currency': from_curr,
                    'to_currency': to_curr
                }
                
                data = await source._make_request(params)
                
                if 'Realtime Currency Exchange Rate' in data:
                    rate_data = data['Realtime Currency Exchange Rate']
                    exchange_rate = float(rate_data['5. Exchange Rate'])
                    
                    # Estimate bid/ask with typical spread
                    typical_spread = 0.0001  # 1 pip for majors
                    
                    return {
                        'source': 'alphavantage',
                        'bid': exchange_rate - typical_spread / 2,
                        'ask': exchange_rate + typical_spread / 2,
                        'timestamp': rate_data['6. Last Refreshed']
                    }
                    
        except Exception as e:
            logger.error(f"Error getting price from {source_name}: {e}")
            return None
        
        return None
    
    def _validate_price_consistency(self, prices: Dict[str, Dict]) -> bool:
        """
        Validate price consistency across sources
        
        Args:
            prices: Dictionary of prices from different sources
        
        Returns:
            True if prices are consistent
        """
        if len(prices) < 2:
            return True
        
        # Extract mid prices
        mid_prices = []
        for source_data in prices.values():
            if 'mid' in source_data:
                mid_prices.append(source_data['mid'])
            elif 'bid' in source_data and 'ask' in source_data:
                mid_prices.append((source_data['bid'] + source_data['ask']) / 2)
        
        if len(mid_prices) < 2:
            return True
        
        # Calculate maximum deviation in pips
        max_price = max(mid_prices)
        min_price = min(mid_prices)
        deviation_pips = (max_price - min_price) * 10000
        
        if deviation_pips > self.max_price_deviation_pips:
            self.stats['consistency_violations'] += 1
            logger.warning(
                f"Price consistency violation: {deviation_pips:.1f} pips deviation"
            )
            return False
        
        return True
    
    def _calculate_consensus_price(self, prices: Dict[str, Dict]) -> Dict[str, float]:
        """
        Calculate consensus price from multiple sources
        
        Args:
            prices: Dictionary of prices from different sources
        
        Returns:
            Consensus price data
        """
        bids = []
        asks = []
        
        for source_data in prices.values():
            if 'bid' in source_data:
                bids.append(source_data['bid'])
            if 'ask' in source_data:
                asks.append(source_data['ask'])
        
        if not bids or not asks:
            return {}
        
        # Use median for robustness against outliers
        consensus_bid = median(bids)
        consensus_ask = median(asks)
        consensus_mid = (consensus_bid + consensus_ask) / 2
        consensus_spread = consensus_ask - consensus_bid
        
        return {
            'bid': consensus_bid,
            'ask': consensus_ask,
            'mid': consensus_mid,
            'spread': consensus_spread,
            'spread_pips': consensus_spread * 10000,
            'sources_used': len(prices)
        }
    
    async def simulate_source_failure(self, source_name: str):
        """
        Simulate a source failure for testing
        
        Args:
            source_name: Name of source to simulate failure
        """
        if source_name in self.source_status:
            self.source_status[source_name] = 'failed'
            logger.warning(f"Simulated failure for {source_name}")
    
    async def restore_source(self, source_name: str):
        """
        Restore a failed source
        
        Args:
            source_name: Name of source to restore
        """
        if source_name in self.source_status:
            self.source_status[source_name] = 'active'
            logger.info(f"Restored {source_name}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregator statistics"""
        success_rate = (
            self.stats['successful_requests'] / self.stats['total_requests']
            if self.stats['total_requests'] > 0 else 0
        )
        
        return {
            **self.stats,
            'success_rate': success_rate,
            'active_sources': [s for s, status in self.source_status.items() 
                             if status == 'active'],
            'failed_sources': [s for s, status in self.source_status.items() 
                             if status == 'failed']
        }
    
    async def close(self):
        """Close all data source connections"""
        for source_name, source in self.sources.items():
            try:
                await source.close()
                logger.info(f"Closed {source_name} connection")
            except Exception as e:
                logger.error(f"Error closing {source_name}: {e}")