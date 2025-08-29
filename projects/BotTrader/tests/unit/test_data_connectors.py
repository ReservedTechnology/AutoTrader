"""
Test Suite for Data Connectors
Following TDD methodology for forex bot targeting 25% annual returns
Tests for OANDA, Alpha Vantage, and TraderMade API connectors
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import asyncio
from typing import Dict, List, Any


class TestOANDAConnector:
    """Test suite for OANDA v20 API connector"""
    
    @pytest.fixture
    def mock_oanda_response(self):
        """Mock OANDA API response"""
        return {
            'prices': [{
                'instrument': 'EUR_USD',
                'time': '2025-01-29T10:00:00Z',
                'bids': [{'price': '1.10500', 'liquidity': 10000000}],
                'asks': [{'price': '1.10502', 'liquidity': 10000000}],
                'closeoutBid': '1.10498',
                'closeoutAsk': '1.10504',
                'status': 'tradeable'
            }],
            'time': '2025-01-29T10:00:00Z'
        }
    
    @pytest.fixture
    def oanda_connector(self):
        """Initialize OANDA connector"""
        from src.data.connectors.oanda_connector import OANDAConnector
        
        connector = OANDAConnector(
            api_key='test_key',
            account_id='test_account',
            environment='practice'
        )
        return connector
    
    def test_initialization(self, oanda_connector):
        """
        Test 5.1.1: Initialize OANDA connector
        Acceptance: Connector initialized with credentials
        """
        assert oanda_connector.api_key == 'test_key'
        assert oanda_connector.account_id == 'test_account'
        assert oanda_connector.environment == 'practice'
        assert oanda_connector.base_url == 'https://api-fxpractice.oanda.com'
        assert oanda_connector.max_requests_per_second == 120
    
    @patch('requests.get')
    def test_fetch_price_data(self, mock_get, oanda_connector, mock_oanda_response):
        """
        Test 5.1.2: Fetch real-time price data
        Acceptance: Returns current bid/ask spreads
        """
        mock_get.return_value.json.return_value = mock_oanda_response
        mock_get.return_value.status_code = 200
        
        prices = oanda_connector.get_prices(['EUR_USD'])
        
        assert prices is not None
        assert 'EUR_USD' in prices
        assert 'bid' in prices['EUR_USD']
        assert 'ask' in prices['EUR_USD']
        assert prices['EUR_USD']['bid'] == 1.10500
        assert prices['EUR_USD']['ask'] == 1.10502
        assert prices['EUR_USD']['spread'] == 0.00002
    
    @patch('requests.get')
    def test_rate_limiting(self, mock_get, oanda_connector):
        """
        Test 5.1.3: Rate limiting enforcement
        Acceptance: Respects 120 requests/second limit
        """
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'prices': []}
        
        # Test rate limiter
        start_time = datetime.now()
        
        # Make 10 rapid requests
        for _ in range(10):
            oanda_connector.get_prices(['EUR_USD'])
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Should take at least 10/120 seconds (~0.083s)
        assert elapsed >= 0.08, "Rate limiting not enforced"
        assert mock_get.call_count == 10
    
    @patch('requests.get')
    def test_error_handling(self, mock_get, oanda_connector):
        """
        Test 5.1.4: Handle API errors gracefully
        Acceptance: Returns None on error with logged message
        """
        # Test 401 Unauthorized
        mock_get.return_value.status_code = 401
        mock_get.return_value.json.return_value = {
            'errorMessage': 'Unauthorized'
        }
        
        prices = oanda_connector.get_prices(['EUR_USD'])
        assert prices is None
        
        # Test 429 Rate Limit
        mock_get.return_value.status_code = 429
        prices = oanda_connector.get_prices(['EUR_USD'])
        assert prices is None
        
        # Test network error
        mock_get.side_effect = Exception("Network error")
        prices = oanda_connector.get_prices(['EUR_USD'])
        assert prices is None
    
    @patch('requests.get')
    def test_streaming_connection(self, mock_get, oanda_connector):
        """
        Test 5.1.5: Streaming price data
        Acceptance: Maintains persistent connection
        """
        # Mock streaming response
        mock_stream = MagicMock()
        mock_stream.iter_lines.return_value = [
            b'{"type":"PRICE","instrument":"EUR_USD","time":"2025-01-29T10:00:00Z","bids":[{"price":"1.10500"}],"asks":[{"price":"1.10502"}]}',
            b'{"type":"HEARTBEAT","time":"2025-01-29T10:00:05Z"}'
        ]
        mock_get.return_value = mock_stream
        mock_get.return_value.status_code = 200
        
        prices = []
        heartbeats = 0
        
        for message in oanda_connector.stream_prices(['EUR_USD']):
            if message['type'] == 'PRICE':
                prices.append(message)
            elif message['type'] == 'HEARTBEAT':
                heartbeats += 1
            
            if len(prices) >= 1 and heartbeats >= 1:
                break
        
        assert len(prices) == 1
        assert heartbeats == 1
        assert prices[0]['instrument'] == 'EUR_USD'
    
    @patch('requests.get')
    def test_historical_data(self, mock_get, oanda_connector):
        """
        Test 5.1.6: Fetch historical candles
        Acceptance: Returns OHLCV data for backtesting
        """
        mock_candles = {
            'candles': [
                {
                    'time': '2025-01-29T09:00:00Z',
                    'mid': {
                        'o': '1.10490',
                        'h': '1.10510',
                        'l': '1.10480',
                        'c': '1.10500'
                    },
                    'volume': 5000,
                    'complete': True
                }
            ]
        }
        mock_get.return_value.json.return_value = mock_candles
        mock_get.return_value.status_code = 200
        
        candles = oanda_connector.get_historical_data(
            'EUR_USD',
            'M5',
            count=100
        )
        
        assert len(candles) > 0
        assert 'time' in candles[0]
        assert 'open' in candles[0]
        assert 'high' in candles[0]
        assert 'low' in candles[0]
        assert 'close' in candles[0]
        assert 'volume' in candles[0]


class TestAlphaVantageConnector:
    """Test suite for Alpha Vantage API connector"""
    
    @pytest.fixture
    def alpha_connector(self):
        """Initialize Alpha Vantage connector"""
        from src.data.connectors.alpha_vantage_connector import AlphaVantageConnector
        
        connector = AlphaVantageConnector(api_key='test_key')
        return connector
    
    @pytest.fixture
    def mock_economic_data(self):
        """Mock economic calendar data"""
        return {
            'data': [
                {
                    'date': '2025-01-29',
                    'time': '08:30',
                    'currency': 'USD',
                    'event': 'Non-Farm Payrolls',
                    'impact': 'HIGH',
                    'actual': '200K',
                    'forecast': '185K',
                    'previous': '175K'
                }
            ]
        }
    
    def test_initialization(self, alpha_connector):
        """
        Test 5.2.1: Initialize Alpha Vantage connector
        Acceptance: Connector ready with API key
        """
        assert alpha_connector.api_key == 'test_key'
        assert alpha_connector.base_url == 'https://www.alphavantage.co/query'
        assert alpha_connector.max_requests_per_minute == 5
    
    @patch('requests.get')
    def test_fetch_economic_indicators(self, mock_get, alpha_connector):
        """
        Test 5.2.2: Fetch economic indicators
        Acceptance: Returns GDP, inflation, employment data
        """
        mock_response = {
            'name': 'Real GDP',
            'interval': 'quarterly',
            'unit': 'billions of dollars',
            'data': [
                {'date': '2025-01-01', 'value': '21500.0'}
            ]
        }
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.status_code = 200
        
        gdp_data = alpha_connector.get_economic_indicator('REAL_GDP')
        
        assert gdp_data is not None
        assert 'data' in gdp_data
        assert len(gdp_data['data']) > 0
        assert float(gdp_data['data'][0]['value']) > 0
    
    @patch('requests.get')
    def test_rate_limiting(self, mock_get, alpha_connector):
        """
        Test 5.2.3: Respect 5 requests/minute limit
        Acceptance: Throttles requests appropriately
        """
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'data': []}
        
        start_time = datetime.now()
        
        # Make 5 requests
        for _ in range(5):
            alpha_connector.get_economic_indicator('REAL_GDP')
        
        # 6th request should be throttled
        alpha_connector.get_economic_indicator('INFLATION')
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Should take at least 60 seconds for 6 requests
        assert elapsed >= 12, "Rate limiting not enforced for Alpha Vantage"
    
    @patch('requests.get')
    def test_sentiment_data(self, mock_get, alpha_connector):
        """
        Test 5.2.4: Fetch market sentiment
        Acceptance: Returns sentiment scores
        """
        mock_sentiment = {
            'sentiment': 'Bearish',
            'sentiment_score': -0.35,
            'news_items': 150,
            'last_update': '2025-01-29T10:00:00Z'
        }
        mock_get.return_value.json.return_value = mock_sentiment
        mock_get.return_value.status_code = 200
        
        sentiment = alpha_connector.get_market_sentiment('FOREX:EUR_USD')
        
        assert sentiment is not None
        assert 'sentiment_score' in sentiment
        assert -1 <= sentiment['sentiment_score'] <= 1
        assert sentiment['sentiment'] in ['Bullish', 'Bearish', 'Neutral']


class TestTraderMadeConnector:
    """Test suite for TraderMade API connector"""
    
    @pytest.fixture
    def tradermade_connector(self):
        """Initialize TraderMade connector"""
        from src.data.connectors.tradermade_connector import TraderMadeConnector
        
        connector = TraderMadeConnector(api_key='test_key')
        return connector
    
    def test_initialization(self, tradermade_connector):
        """
        Test 5.3.1: Initialize TraderMade connector
        Acceptance: Connector ready with credentials
        """
        assert tradermade_connector.api_key == 'test_key'
        assert tradermade_connector.base_url == 'https://marketdata.tradermade.com/api/v1'
        assert tradermade_connector.max_requests_per_day == 1000
    
    @patch('requests.get')
    def test_fetch_live_rates(self, mock_get, tradermade_connector):
        """
        Test 5.3.2: Fetch live forex rates
        Acceptance: Returns current market prices
        """
        mock_rates = {
            'endpoint': 'live',
            'quotes': [
                {
                    'instrument': 'EURUSD',
                    'bid': 1.10500,
                    'ask': 1.10502,
                    'mid': 1.10501,
                    'base_currency': 'EUR',
                    'quote_currency': 'USD',
                    'timestamp': 1706524800
                }
            ],
            'requested_time': 'Wed, 29 Jan 2025 10:00:00 GMT',
            'timestamp': 1706524800
        }
        mock_get.return_value.json.return_value = mock_rates
        mock_get.return_value.status_code = 200
        
        rates = tradermade_connector.get_live_rates(['EURUSD'])
        
        assert rates is not None
        assert 'EURUSD' in rates
        assert rates['EURUSD']['bid'] == 1.10500
        assert rates['EURUSD']['ask'] == 1.10502
        assert rates['EURUSD']['spread'] == 0.00002
    
    @patch('requests.get')
    def test_volatility_data(self, mock_get, tradermade_connector):
        """
        Test 5.3.3: Fetch volatility metrics
        Acceptance: Returns ATR and implied volatility
        """
        mock_volatility = {
            'instrument': 'EURUSD',
            'atr_14': 0.0055,
            'atr_20': 0.0058,
            'implied_volatility': 8.5,
            'historical_volatility': 7.8,
            'timestamp': 1706524800
        }
        mock_get.return_value.json.return_value = mock_volatility
        mock_get.return_value.status_code = 200
        
        volatility = tradermade_connector.get_volatility('EURUSD')
        
        assert volatility is not None
        assert 'atr_14' in volatility
        assert volatility['atr_14'] > 0
        assert 'implied_volatility' in volatility
        assert volatility['implied_volatility'] > 0
    
    def test_daily_request_limit(self, tradermade_connector):
        """
        Test 5.3.4: Track daily request limit
        Acceptance: Prevents exceeding 1000 requests/day
        """
        # Simulate request counter
        tradermade_connector.daily_requests = 999
        
        # Next request should succeed
        assert tradermade_connector.can_make_request() is True
        tradermade_connector.daily_requests += 1
        
        # 1001st request should be blocked
        assert tradermade_connector.can_make_request() is False
        
        # Reset counter (new day)
        tradermade_connector.reset_daily_counter()
        assert tradermade_connector.daily_requests == 0
        assert tradermade_connector.can_make_request() is True


class TestConnectorIntegration:
    """Test suite for connector integration and failover"""
    
    @pytest.fixture
    def connector_manager(self):
        """Initialize connector manager"""
        from src.data.connectors.connector_manager import ConnectorManager
        
        manager = ConnectorManager()
        return manager
    
    def test_primary_secondary_failover(self, connector_manager):
        """
        Test 5.4.1: Automatic failover between connectors
        Acceptance: Switches to backup on primary failure
        """
        # Set OANDA as primary
        connector_manager.set_primary('oanda')
        assert connector_manager.primary_connector == 'oanda'
        
        # Simulate OANDA failure
        with patch.object(connector_manager.oanda, 'get_prices', return_value=None):
            prices = connector_manager.get_prices(['EUR_USD'])
            
            # Should failover to TraderMade
            assert connector_manager.active_connector == 'tradermade'
            assert prices is not None
    
    def test_data_aggregation(self, connector_manager):
        """
        Test 5.4.2: Aggregate data from multiple sources
        Acceptance: Combines and validates data
        """
        # Mock data from different sources
        oanda_data = {'EUR_USD': {'bid': 1.10500, 'ask': 1.10502}}
        tradermade_data = {'EUR_USD': {'bid': 1.10498, 'ask': 1.10504}}
        
        with patch.object(connector_manager.oanda, 'get_prices', return_value=oanda_data):
            with patch.object(connector_manager.tradermade, 'get_live_rates', return_value=tradermade_data):
                
                aggregated = connector_manager.get_aggregated_prices(['EUR_USD'])
                
                assert 'EUR_USD' in aggregated
                assert 'bid' in aggregated['EUR_USD']
                assert 'ask' in aggregated['EUR_USD']
                assert 'sources' in aggregated['EUR_USD']
                assert len(aggregated['EUR_USD']['sources']) == 2
                
                # Should use best prices (highest bid, lowest ask)
                assert aggregated['EUR_USD']['bid'] == 1.10500  # OANDA's higher bid
                assert aggregated['EUR_USD']['ask'] == 1.10502  # OANDA's lower ask
    
    def test_connection_health_monitoring(self, connector_manager):
        """
        Test 5.4.3: Monitor connector health
        Acceptance: Tracks latency and success rates
        """
        # Simulate successful requests
        for _ in range(10):
            connector_manager.record_request('oanda', success=True, latency_ms=45)
        
        # Simulate some failures
        for _ in range(2):
            connector_manager.record_request('oanda', success=False, latency_ms=5000)
        
        health = connector_manager.get_health_status('oanda')
        
        assert health['total_requests'] == 12
        assert health['success_rate'] == 10/12
        assert health['average_latency_ms'] < 1000
        assert health['status'] in ['healthy', 'degraded', 'unhealthy']
    
    @pytest.mark.asyncio
    async def test_async_data_fetching(self, connector_manager):
        """
        Test 5.4.4: Asynchronous data fetching
        Acceptance: Fetches from multiple sources concurrently
        """
        pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        
        # Fetch data asynchronously
        tasks = [
            connector_manager.async_get_prices(pair) for pair in pairs
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == len(pairs)
        for result in results:
            assert result is not None
            assert 'bid' in result
            assert 'ask' in result


class TestDataValidation:
    """Test suite for data validation and cleaning"""
    
    @pytest.fixture
    def data_validator(self):
        """Initialize data validator"""
        from src.data.validators.price_validator import PriceValidator
        
        validator = PriceValidator()
        return validator
    
    def test_price_validation(self, data_validator):
        """
        Test 5.5.1: Validate price data
        Acceptance: Detects and flags invalid prices
        """
        # Valid price
        valid_price = {'bid': 1.10500, 'ask': 1.10502, 'time': datetime.now()}
        assert data_validator.validate_price(valid_price) is True
        
        # Invalid spread (negative)
        invalid_spread = {'bid': 1.10502, 'ask': 1.10500, 'time': datetime.now()}
        assert data_validator.validate_price(invalid_spread) is False
        
        # Invalid price (negative)
        negative_price = {'bid': -1.10500, 'ask': 1.10502, 'time': datetime.now()}
        assert data_validator.validate_price(negative_price) is False
        
        # Stale price (old timestamp)
        stale_price = {'bid': 1.10500, 'ask': 1.10502, 'time': datetime.now() - timedelta(minutes=10)}
        assert data_validator.validate_price(stale_price, max_age_seconds=300) is False
    
    def test_outlier_detection(self, data_validator):
        """
        Test 5.5.2: Detect price outliers
        Acceptance: Identifies abnormal price movements
        """
        # Normal price series
        prices = pd.Series([1.10500, 1.10502, 1.10498, 1.10503, 1.10501])
        
        # Add outlier
        prices = pd.concat([prices, pd.Series([1.20000])])  # 10% jump
        
        outliers = data_validator.detect_outliers(prices, threshold=3)
        
        assert len(outliers) == 1
        assert outliers[0] == len(prices) - 1  # Last price is outlier
    
    def test_data_interpolation(self, data_validator):
        """
        Test 5.5.3: Handle missing data
        Acceptance: Interpolates gaps appropriately
        """
        # Create data with gaps
        timestamps = pd.date_range(start='2025-01-29 10:00:00', periods=10, freq='1min')
        prices = pd.Series([1.10500, 1.10502, np.nan, np.nan, 1.10506, 1.10508, np.nan, 1.10510, 1.10512, 1.10514], index=timestamps)
        
        # Interpolate missing values
        filled_prices = data_validator.interpolate_missing(prices, method='linear')
        
        assert filled_prices.isna().sum() == 0
        assert filled_prices.iloc[2] == pytest.approx(1.10503, rel=1e-5)
        assert filled_prices.iloc[3] == pytest.approx(1.10504, rel=1e-5)
        assert filled_prices.iloc[6] == pytest.approx(1.10509, rel=1e-5)


if __name__ == "__main__":
    pytest.main([__file__, '-v'])