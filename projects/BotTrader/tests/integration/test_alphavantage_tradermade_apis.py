"""
Test Suite for Alpha Vantage and TraderMade API Connections
Validates historical data and real-time streaming capabilities
"""
import pytest
import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json


class TestAlphaVantageAPI:
    """
    Test suite for Alpha Vantage historical data API
    Focus on forex technical indicators and economic data
    """
    
    @pytest.fixture
    async def alphavantage_client(self):
        """Initialize Alpha Vantage client"""
        from src.data.connectors.alphavantage_connector import AlphaVantageConnector
        
        client = AlphaVantageConnector(
            api_key=os.getenv('ALPHA_VANTAGE_API_KEY')
        )
        await client.initialize()
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_api_authentication(self, alphavantage_client):
        """
        Test 2.2.1: Verify Alpha Vantage API authentication
        Acceptance: Valid API key accepted
        """
        auth_status = await alphavantage_client.check_api_status()
        
        assert auth_status['authenticated'] is True, \
            "Alpha Vantage authentication failed"
        assert auth_status['rate_limit_remaining'] > 0, \
            "No API calls remaining"
        assert auth_status['api_tier'] in ['free', 'premium'], \
            "Invalid API tier"
    
    @pytest.mark.asyncio
    async def test_forex_daily_data(self, alphavantage_client):
        """
        Test 2.2.2: Retrieve daily forex data
        Acceptance: 2+ years of historical data available
        """
        pairs = ['EUR/USD', 'GBP/JPY', 'AUD/JPY', 'USD/TRY', 'NZD/JPY', 'USD/ZAR']
        
        for pair in pairs:
            # Convert to Alpha Vantage format
            from_currency = pair.split('/')[0]
            to_currency = pair.split('/')[1]
            
            daily_data = await alphavantage_client.get_fx_daily(
                from_symbol=from_currency,
                to_symbol=to_currency
            )
            
            assert daily_data is not None, f"No daily data for {pair}"
            assert len(daily_data) >= 500, \
                f"Insufficient history for {pair}: {len(daily_data)} days"
            
            # Verify data structure
            if len(daily_data) > 0:
                first_record = daily_data[0]
                required_fields = ['date', 'open', 'high', 'low', 'close']
                for field in required_fields:
                    assert field in first_record, \
                        f"Missing {field} in daily data"
    
    @pytest.mark.asyncio
    async def test_forex_intraday_data(self, alphavantage_client):
        """
        Test 2.2.3: Retrieve intraday forex data
        Acceptance: Multiple timeframes available (5min, 15min, 1h)
        """
        timeframes = ['5min', '15min', '60min']
        
        for interval in timeframes:
            intraday_data = await alphavantage_client.get_fx_intraday(
                from_symbol='EUR',
                to_symbol='USD',
                interval=interval
            )
            
            assert intraday_data is not None, \
                f"No intraday data for {interval}"
            assert len(intraday_data) > 0, \
                f"Empty intraday data for {interval}"
            
            # Verify proper time intervals
            if len(intraday_data) >= 2:
                time1 = datetime.fromisoformat(intraday_data[0]['timestamp'])
                time2 = datetime.fromisoformat(intraday_data[1]['timestamp'])
                
                expected_delta = {
                    '5min': 5,
                    '15min': 15,
                    '60min': 60
                }
                
                actual_delta = abs((time2 - time1).total_seconds() / 60)
                assert actual_delta == expected_delta[interval], \
                    f"Incorrect time interval for {interval}"
    
    @pytest.mark.asyncio
    async def test_technical_indicators_rsi(self, alphavantage_client):
        """
        Test 2.2.4: Retrieve RSI technical indicator
        Acceptance: RSI(10) data available as per specifications
        """
        rsi_data = await alphavantage_client.get_technical_indicator(
            function='RSI',
            symbol='EURUSD',
            interval='5min',
            time_period=10,  # RSI(10) for day trading
            series_type='close'
        )
        
        assert rsi_data is not None, "Failed to retrieve RSI data"
        assert len(rsi_data) > 0, "Empty RSI data"
        
        # Verify RSI values are in valid range
        for record in rsi_data[:10]:
            rsi_value = float(record['RSI'])
            assert 0 <= rsi_value <= 100, \
                f"Invalid RSI value: {rsi_value}"
    
    @pytest.mark.asyncio
    async def test_technical_indicators_macd(self, alphavantage_client):
        """
        Test 2.2.5: Retrieve MACD technical indicator
        Acceptance: MACD(12,26,9) configuration available
        """
        macd_data = await alphavantage_client.get_technical_indicator(
            function='MACD',
            symbol='EURUSD',
            interval='15min',
            fast_period=12,
            slow_period=26,
            signal_period=9,
            series_type='close'
        )
        
        assert macd_data is not None, "Failed to retrieve MACD data"
        assert len(macd_data) > 0, "Empty MACD data"
        
        # Verify MACD components
        if len(macd_data) > 0:
            first_record = macd_data[0]
            required_fields = ['MACD', 'MACD_Signal', 'MACD_Hist']
            for field in required_fields:
                assert field in first_record, \
                    f"Missing MACD component: {field}"
    
    @pytest.mark.asyncio
    async def test_rate_limiting_compliance(self, alphavantage_client):
        """
        Test 2.2.6: Verify rate limiting compliance
        Acceptance: Handle 5 requests/minute (free tier) gracefully
        """
        # Free tier: 5 calls per minute
        request_times = []
        max_requests = 5
        
        for i in range(max_requests):
            start_time = asyncio.get_event_loop().time()
            
            try:
                await alphavantage_client.get_fx_daily('EUR', 'USD')
                request_times.append(asyncio.get_event_loop().time())
            except Exception as e:
                if 'rate limit' in str(e).lower():
                    # Expected behavior
                    assert i >= 5, \
                        f"Rate limited too early at request {i+1}"
            
            # Ensure we're not exceeding rate limit
            if i < max_requests - 1:
                await asyncio.sleep(12)  # 60s / 5 requests = 12s minimum
        
        assert len(request_times) <= 5, \
            "Exceeded rate limit for free tier"


class TestTraderMadeWebSocket:
    """
    Test suite for TraderMade WebSocket streaming
    Ultra-low latency forex data feed validation
    """
    
    @pytest.fixture
    async def tradermade_client(self):
        """Initialize TraderMade WebSocket client"""
        from src.data.connectors.tradermade_connector import TraderMadeConnector
        
        client = TraderMadeConnector(
            api_key=os.getenv('TRADERMADE_API_KEY')
        )
        await client.initialize()
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, tradermade_client):
        """
        Test 2.3.1: Establish WebSocket connection
        Acceptance: Stable WSS connection established
        """
        connected = await tradermade_client.connect_websocket()
        
        assert connected is True, "Failed to establish WebSocket connection"
        assert tradermade_client.is_connected(), \
            "WebSocket not reporting connected status"
    
    @pytest.mark.asyncio
    async def test_subscribe_to_pairs(self, tradermade_client):
        """
        Test 2.3.2: Subscribe to multiple forex pairs
        Acceptance: Receive data for all 6 priority pairs
        """
        pairs = ['EURUSD', 'GBPJPY', 'AUDJPY', 'USDTRY', 'NZDJPY', 'USDZAR']
        
        # Subscribe to all pairs
        subscription_result = await tradermade_client.subscribe(pairs)
        
        assert subscription_result['success'] is True, \
            "Failed to subscribe to pairs"
        assert subscription_result['subscribed_pairs'] == pairs, \
            "Not all pairs subscribed"
        
        # Collect data to verify subscription
        received_pairs = set()
        timeout = 10  # seconds
        start_time = asyncio.get_event_loop().time()
        
        async for data in tradermade_client.stream_prices():
            if 'symbol' in data:
                received_pairs.add(data['symbol'])
            
            if len(received_pairs) == len(pairs):
                break
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                break
        
        assert len(received_pairs) == len(pairs), \
            f"Only received data for {received_pairs}, expected {pairs}"
    
    @pytest.mark.asyncio
    async def test_data_latency(self, tradermade_client):
        """
        Test 2.3.3: Measure WebSocket data latency
        Acceptance: <50ms latency from market event
        """
        await tradermade_client.subscribe(['EURUSD'])
        
        latencies = []
        samples = 20
        
        async for data in tradermade_client.stream_prices():
            if 'timestamp' in data:
                server_time = datetime.fromtimestamp(data['timestamp'])
                local_time = datetime.utcnow()
                latency_ms = (local_time - server_time).total_seconds() * 1000
                latencies.append(abs(latency_ms))
                
                if len(latencies) >= samples:
                    break
        
        avg_latency = sum(latencies) / len(latencies) if latencies else float('inf')
        
        assert avg_latency < 50, \
            f"Average latency {avg_latency:.1f}ms exceeds 50ms target"
        assert max(latencies) < 100, \
            f"Maximum latency {max(latencies):.1f}ms too high"
    
    @pytest.mark.asyncio
    async def test_data_structure_validation(self, tradermade_client):
        """
        Test 2.3.4: Validate streaming data structure
        Acceptance: Complete bid/ask/mid prices with timestamp
        """
        await tradermade_client.subscribe(['EURUSD'])
        
        data_sample = None
        async for data in tradermade_client.stream_prices():
            data_sample = data
            break
        
        assert data_sample is not None, "No data received"
        
        required_fields = ['symbol', 'timestamp', 'bid', 'ask', 'mid']
        for field in required_fields:
            assert field in data_sample, f"Missing field: {field}"
        
        # Validate price relationships
        bid = float(data_sample['bid'])
        ask = float(data_sample['ask'])
        mid = float(data_sample['mid'])
        
        assert bid < ask, "Bid should be less than ask"
        assert abs(mid - (bid + ask) / 2) < 0.00001, \
            "Mid price should be average of bid and ask"
    
    @pytest.mark.asyncio
    async def test_reconnection_handling(self, tradermade_client):
        """
        Test 2.3.5: Test automatic reconnection
        Acceptance: Reconnect within 5 seconds
        """
        await tradermade_client.subscribe(['EURUSD'])
        
        # Simulate disconnect
        await tradermade_client.disconnect()
        assert not tradermade_client.is_connected(), \
            "Should be disconnected"
        
        # Wait for automatic reconnection
        await asyncio.sleep(3)
        
        # Should be reconnected
        assert tradermade_client.is_connected(), \
            "Failed to automatically reconnect"
        
        # Verify data flow resumed
        data_received = False
        timeout = 5
        start_time = asyncio.get_event_loop().time()
        
        async for data in tradermade_client.stream_prices():
            data_received = True
            break
        
        assert data_received, "No data after reconnection"
    
    @pytest.mark.asyncio
    async def test_buffer_during_disconnect(self, tradermade_client):
        """
        Test 2.3.6: Verify data buffering during reconnection
        Acceptance: No data loss during brief disconnects
        """
        buffer_size = await tradermade_client.get_buffer_size()
        
        assert buffer_size > 0, "Buffer not configured"
        assert buffer_size >= 1000, \
            "Buffer size too small for reconnection scenarios"


class TestMultiSourceAggregation:
    """
    Test suite for aggregating data from multiple sources
    Ensures data consistency and redundancy
    """
    
    @pytest.mark.asyncio
    async def test_price_consistency_across_sources(self):
        """
        Test 2.4.1: Verify price consistency between sources
        Acceptance: Prices differ by <5 pips for major pairs
        """
        from src.data.aggregator import DataAggregator
        
        aggregator = DataAggregator()
        await aggregator.initialize_sources()
        
        # Get EUR/USD price from multiple sources
        prices = await aggregator.get_aggregated_price('EURUSD')
        
        assert 'oanda' in prices, "OANDA price missing"
        assert 'tradermade' in prices, "TraderMade price missing"
        
        # Compare prices (convert to pips)
        oanda_mid = (prices['oanda']['bid'] + prices['oanda']['ask']) / 2
        tradermade_mid = prices['tradermade']['mid']
        
        diff_pips = abs(oanda_mid - tradermade_mid) * 10000
        
        assert diff_pips < 5, \
            f"Price difference {diff_pips:.1f} pips exceeds threshold"
    
    @pytest.mark.asyncio
    async def test_failover_mechanism(self):
        """
        Test 2.4.2: Test failover when primary source fails
        Acceptance: Automatic switch to backup source
        """
        from src.data.aggregator import DataAggregator
        
        aggregator = DataAggregator()
        await aggregator.initialize_sources()
        
        # Simulate OANDA failure
        await aggregator.simulate_source_failure('oanda')
        
        # Should still get prices from backup sources
        prices = await aggregator.get_aggregated_price('EURUSD')
        
        assert prices is not None, "No prices available after failover"
        assert len(prices) > 0, "No backup sources available"
        assert 'tradermade' in prices or 'alphavantage' in prices, \
            "Backup sources not functioning"


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])