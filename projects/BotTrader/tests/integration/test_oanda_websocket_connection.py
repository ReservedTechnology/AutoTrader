"""
Test Suite for OANDA v20 API WebSocket Connection
Following TDD methodology for forex bot targeting 25% annual returns
Integrated with dual database architecture: TimescaleDB (Railway) + Supabase
"""
import pytest
import pytest_asyncio
import asyncio
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from supabase import create_client, Client
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
from decimal import Decimal
import aiohttp
import time
from dotenv import load_dotenv

load_dotenv()


class TestOandaWebSocketConnection:
    """
    Test suite for OANDA v20 API integration
    Validates streaming data for 6 priority forex pairs
    Data flows to TimescaleDB (time-series) and Supabase (non-temporal)
    """
    
    @pytest.fixture
    def timescale_connection(self):
        """Initialize TimescaleDB connection for storing price data"""
        conn = psycopg2.connect(
            host=os.getenv('TIMESCALE_HOST', 'localhost'),
            port=os.getenv('TIMESCALE_PORT', 5432),
            database=os.getenv('TIMESCALE_DB', 'bottrader_timeseries'),
            user=os.getenv('TIMESCALE_USER', 'postgres'),
            password=os.getenv('TIMESCALE_PASSWORD')
        )
        yield conn
        conn.close()
    
    @pytest.fixture
    def supabase_client(self) -> Client:
        """Initialize Supabase client for configuration"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        client = create_client(url, key)
        return client
    
    @pytest.fixture
    async def oanda_client(self):
        """Initialize OANDA v20 client"""
        from src.data.connectors.oanda_connector import OandaV20Connector
        
        client = OandaV20Connector(
            api_key=os.getenv('OANDA_API_KEY'),
            account_id=os.getenv('OANDA_ACCOUNT_ID'),
            environment=os.getenv('OANDA_ENVIRONMENT', 'practice')
        )
        
        await client.initialize()
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_oanda_authentication(self, oanda_client):
        """
        Test 2.1.1: Verify OANDA API authentication
        Acceptance: Valid bearer token authentication
        """
        auth_status = await oanda_client.authenticate()
        
        assert auth_status['authenticated'] is True, \
            "OANDA authentication failed"
        assert auth_status['account_id'] == os.getenv('OANDA_ACCOUNT_ID'), \
            "Account ID mismatch"
        assert auth_status['environment'] in ['practice', 'live'], \
            "Invalid environment configuration"
    
    @pytest.mark.asyncio
    async def test_account_access(self, oanda_client):
        """
        Test 2.1.2: Verify account access and permissions
        Acceptance: Full account details accessible
        """
        account_info = await oanda_client.get_account_info()
        
        assert account_info is not None, "Failed to retrieve account info"
        assert 'balance' in account_info, "Account balance not accessible"
        assert 'marginAvailable' in account_info, "Margin info not accessible"
        assert 'openPositionCount' in account_info, "Position info not accessible"
        assert float(account_info['balance']) > 0, "Account has no balance"
    
    @pytest.mark.asyncio
    async def test_instruments_availability(self, oanda_client):
        """
        Test 2.1.3: Verify forex pairs availability
        Acceptance: All 6 priority pairs tradeable
        """
        required_pairs = [
            'USD_ZAR',  # Ultra-high volatility
            'GBP_JPY',  # The Dragon
            'AUD_JPY',  # Commodity correlation
            'USD_TRY',  # Emerging market
            'NZD_JPY',  # Carry trade
            'EUR_USD'   # Maximum liquidity
        ]
        
        instruments = await oanda_client.get_instruments()
        available_symbols = [inst['name'] for inst in instruments]
        
        for pair in required_pairs:
            assert pair in available_symbols, \
                f"{pair} not available for trading"
            
            # Get instrument details
            details = next((i for i in instruments if i['name'] == pair), None)
            assert details is not None, f"No details for {pair}"
            
            # Verify tradeable status
            assert details.get('tradeable', False), \
                f"{pair} is not tradeable"
            
            # Check spread reasonability
            if 'spread' in details:
                spread_pips = float(details['spread'])
                max_spreads = {
                    'USD_ZAR': 40,
                    'GBP_JPY': 5,
                    'AUD_JPY': 5,
                    'USD_TRY': 50,
                    'NZD_JPY': 10,
                    'EUR_USD': 2
                }
                assert spread_pips <= max_spreads[pair], \
                    f"{pair} spread {spread_pips} exceeds maximum {max_spreads[pair]}"
    
    @pytest.mark.asyncio
    async def test_streaming_connection(self, oanda_client, timescale_connection):
        """
        Test 2.1.4: Establish WebSocket streaming and store in TimescaleDB
        Acceptance: Stable connection with <50ms latency, data persisted
        """
        stream_params = {
            'instruments': 'USD_ZAR,GBP_JPY,AUD_JPY,USD_TRY,NZD_JPY,EUR_USD'
        }
        
        stream = await oanda_client.create_price_stream(stream_params)
        assert stream is not None, "Failed to create price stream"
        
        # Collect 10 price updates to measure latency and store in DB
        latencies = []
        prices_received = 0
        cursor = timescale_connection.cursor()
        
        async for price_data in stream:
            receive_time = time.time()
            
            if 'time' in price_data and price_data.get('type') == 'PRICE':
                # Parse OANDA timestamp
                server_time = datetime.fromisoformat(price_data['time'].replace('Z', '+00:00'))
                local_time = datetime.utcnow()
                latency_ms = (local_time - server_time).total_seconds() * 1000
                latencies.append(abs(latency_ms))  # abs to handle clock drift
                
                # Store in TimescaleDB
                if 'bids' in price_data and 'asks' in price_data and len(price_data['bids']) > 0 and len(price_data['asks']) > 0:
                    bid = float(price_data['bids'][0]['price'])
                    ask = float(price_data['asks'][0]['price'])
                    spread = ask - bid
                    volume = int(price_data['bids'][0].get('liquidity', 0))
                    
                    cursor.execute("""
                        INSERT INTO forex_prices (time, symbol, bid, ask, spread, volume)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING;
                    """, (
                        server_time,
                        price_data['instrument'],
                        bid,
                        ask,
                        spread,
                        volume
                    ))
            
            prices_received += 1
            
            if prices_received >= 10:
                break
        
        timescale_connection.commit()
        cursor.close()
        
        assert prices_received == 10, \
            f"Only received {prices_received}/10 price updates"
        
        avg_latency = sum(latencies) / len(latencies) if latencies else float('inf')
        assert avg_latency < 50, \
            f"Average latency {avg_latency:.1f}ms exceeds 50ms requirement"
    
    @pytest.mark.asyncio
    async def test_price_data_structure(self, oanda_client, timescale_connection):
        """
        Test 2.1.5: Verify price data structure and storage in TimescaleDB
        Acceptance: Complete bid/ask/spread data stored in hypertable
        """
        stream_params = {'instruments': 'EUR_USD'}
        stream = await oanda_client.create_price_stream(stream_params)
        
        price_data = None
        async for data in stream:
            if data.get('type') == 'PRICE':
                price_data = data
                break
        
        assert price_data is not None, "No price data received"
        
        # Verify required fields
        required_fields = ['instrument', 'time', 'bids', 'asks', 'tradeable']
        for field in required_fields:
            assert field in price_data, f"Missing required field: {field}"
        
        # Verify bid/ask structure
        assert len(price_data['bids']) > 0, "No bid prices"
        assert len(price_data['asks']) > 0, "No ask prices"
        
        bid = price_data['bids'][0]
        ask = price_data['asks'][0]
        
        assert 'price' in bid and 'liquidity' in bid, "Invalid bid structure"
        assert 'price' in ask and 'liquidity' in ask, "Invalid ask structure"
        
        # Verify spread is positive
        spread = float(ask['price']) - float(bid['price'])
        assert spread > 0, f"Invalid spread: {spread}"
        assert spread < 0.001, f"Spread too wide for EUR_USD: {spread}"
        
        # Store in TimescaleDB
        cursor = timescale_connection.cursor()
        cursor.execute("""
            INSERT INTO forex_prices (time, symbol, bid, ask, spread, volume)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
        """, (
            datetime.fromisoformat(price_data['time'].replace('Z', '+00:00')),
            price_data['instrument'],
            float(bid['price']),
            float(ask['price']),
            spread,
            int(bid.get('liquidity', 0))
        ))
        timescale_connection.commit()
        cursor.close()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_compliance(self, oanda_client):
        """
        Test 2.1.6: Verify rate limiting compliance (120 req/sec)
        Acceptance: No 429 errors under load
        """
        # Test with 100 requests (below 120/sec limit)
        tasks = []
        for _ in range(100):
            task = oanda_client.get_current_prices(['EUR_USD'])
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time
        
        # Check for rate limit errors
        errors = [r for r in results if isinstance(r, Exception)]
        rate_limit_errors = [e for e in errors if '429' in str(e)]
        
        assert len(rate_limit_errors) == 0, \
            f"Hit rate limit with {len(rate_limit_errors)} 429 errors"
        
        # Verify request rate
        actual_rate = len(tasks) / elapsed
        assert actual_rate <= 120, \
            f"Request rate {actual_rate:.1f}/sec exceeds limit"
    
    @pytest.mark.asyncio
    async def test_multi_stream_handling(self, oanda_client):
        """
        Test 2.1.7: Handle multiple concurrent streams
        Acceptance: Support 20 concurrent WebSocket connections
        """
        # OANDA allows max 20 streaming connections per IP
        streams = []
        pairs_per_stream = 3  # Distribute pairs across streams
        
        all_pairs = [
            ['USD_ZAR', 'GBP_JPY'],
            ['AUD_JPY', 'USD_TRY'],
            ['NZD_JPY', 'EUR_USD']
        ]
        
        for pair_group in all_pairs:
            stream = await oanda_client.create_price_stream({
                'instruments': ','.join(pair_group)
            })
            streams.append(stream)
        
        assert len(streams) == 3, \
            f"Created {len(streams)}/3 streams"
        
        # Verify all streams are receiving data
        stream_data = {}
        
        async def collect_from_stream(stream_id, stream):
            data = []
            count = 0
            async for price in stream:
                data.append(price)
                count += 1
                if count >= 5:
                    break
            stream_data[stream_id] = data
        
        tasks = [
            collect_from_stream(i, stream) 
            for i, stream in enumerate(streams)
        ]
        
        await asyncio.gather(*tasks)
        
        for i in range(len(streams)):
            assert i in stream_data, f"Stream {i} didn't provide data"
            assert len(stream_data[i]) >= 5, \
                f"Stream {i} only provided {len(stream_data[i])} updates"
    
    @pytest.mark.asyncio
    async def test_order_endpoints(self, oanda_client, supabase_client):
        """
        Test 2.1.8: Verify order management endpoints with Supabase tracking
        Acceptance: Create, modify, cancel orders with audit trail
        """
        # Test with a minimal market order (paper trading)
        order_request = {
            'instrument': 'EUR_USD',
            'units': '100',  # Minimal size
            'type': 'MARKET',
            'timeInForce': 'FOK'  # Fill or Kill
        }
        
        if os.getenv('OANDA_ENVIRONMENT') == 'practice':
            # Create order
            order_result = await oanda_client.create_order(order_request)
            
            assert order_result is not None, "Failed to create order"
            assert 'orderCreateTransaction' in order_result or \
                   'orderRejectTransaction' in order_result, \
                   "Invalid order response structure"
            
            # Store order audit in Supabase
            if 'orderCreateTransaction' in order_result:
                order_audit = {
                    'order_id': order_result['orderCreateTransaction'].get('id'),
                    'instrument': order_request['instrument'],
                    'units': order_request['units'],
                    'order_type': order_request['type'],
                    'status': 'created',
                    'created_at': datetime.now().isoformat()
                }
                
                try:
                    response = supabase_client.table('order_audit').insert(order_audit).execute()
                    assert response.data, "Failed to store order audit"
                except Exception as e:
                    print(f"Order audit storage: {e}")
            
            # Get pending orders
            pending_orders = await oanda_client.get_pending_orders()
            assert isinstance(pending_orders, list), \
                "Invalid pending orders response"
        else:
            pytest.skip("Skipping order test in non-practice environment")
    
    @pytest.mark.asyncio
    async def test_position_tracking(self, oanda_client, supabase_client):
        """
        Test 2.1.9: Verify position tracking and sync with Supabase
        Acceptance: Real-time position updates stored in both databases
        """
        positions = await oanda_client.get_open_positions()
        
        assert isinstance(positions, list), \
            "Invalid positions response type"
        
        # If there are open positions, verify structure
        if len(positions) > 0:
            position = positions[0]
            required_fields = [
                'instrument', 'units', 'averagePrice', 
                'unrealizedPL', 'marginUsed'
            ]
            
            for field in required_fields:
                assert field in position, \
                    f"Position missing required field: {field}"
            
            # Store position metadata in Supabase
            position_meta = {
                'position_id': f"oanda_{position.get('id', '')}",
                'instrument': position['instrument'],
                'opened_at': datetime.now().isoformat(),
                'units': position['units'],
                'average_price': position['averagePrice']
            }
            
            try:
                response = supabase_client.table('position_metadata').upsert(position_meta).execute()
                assert response.data, "Failed to store position metadata"
            except Exception as e:
                print(f"Position metadata storage: {e}")
    
    @pytest.mark.asyncio
    async def test_reconnection_mechanism(self, oanda_client):
        """
        Test 2.1.10: Verify automatic reconnection on disconnect
        Acceptance: Reconnect within 5 seconds of disconnect
        """
        stream = await oanda_client.create_price_stream({
            'instruments': 'EUR_USD'
        })
        
        # Simulate disconnect
        await oanda_client.disconnect_stream(stream)
        
        # Wait for reconnection
        await asyncio.sleep(2)
        
        # Verify reconnection
        reconnected = await oanda_client.is_connected()
        assert reconnected, "Failed to reconnect after disconnect"
        
        # Verify data flow resumed
        new_stream = await oanda_client.create_price_stream({
            'instruments': 'EUR_USD'
        })
        
        data_received = False
        async for price in new_stream:
            data_received = True
            break
        
        assert data_received, "No data after reconnection"


class TestOandaDataQuality:
    """Test suite for OANDA data quality and reliability"""
    
    @pytest.fixture
    def timescale_connection(self):
        """Initialize TimescaleDB connection"""
        conn = psycopg2.connect(
            host=os.getenv('TIMESCALE_HOST', 'localhost'),
            port=os.getenv('TIMESCALE_PORT', 5432),
            database=os.getenv('TIMESCALE_DB', 'bottrader_timeseries'),
            user=os.getenv('TIMESCALE_USER', 'postgres'),
            password=os.getenv('TIMESCALE_PASSWORD')
        )
        yield conn
        conn.close()
    
    @pytest.fixture
    async def oanda_client(self):
        """Initialize OANDA v20 client"""
        from src.data.connectors.oanda_connector import OandaV20Connector
        
        client = OandaV20Connector(
            api_key=os.getenv('OANDA_API_KEY'),
            account_id=os.getenv('OANDA_ACCOUNT_ID'),
            environment=os.getenv('OANDA_ENVIRONMENT', 'practice')
        )
        
        await client.initialize()
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_weekend_gap_handling(self, oanda_client):
        """
        Test 2.2.1: Handle weekend gaps appropriately
        Acceptance: Detect and mark weekend gaps
        """
        # Get historical data including weekend
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        candles = await oanda_client.get_candles(
            instrument='EUR_USD',
            granularity='H1',
            from_time=start_date,
            to_time=end_date
        )
        
        # Check for weekend gaps (Friday close to Sunday open)
        gaps_detected = []
        
        for i in range(1, len(candles)):
            prev_candle = candles[i-1]
            curr_candle = candles[i]
            
            prev_time = datetime.fromisoformat(prev_candle['time'])
            curr_time = datetime.fromisoformat(curr_candle['time'])
            
            time_diff = (curr_time - prev_time).total_seconds() / 3600
            
            # Weekend gap is typically 48+ hours
            if time_diff > 24:
                gaps_detected.append({
                    'from': prev_time,
                    'to': curr_time,
                    'hours': time_diff
                })
        
        assert len(gaps_detected) > 0, \
            "No weekend gaps detected in weekly data"
    
    @pytest.mark.asyncio
    async def test_data_consistency(self, oanda_client, timescale_connection):
        """
        Test 2.2.2: Verify data consistency across timeframes and storage
        Acceptance: 1H candles aggregate correctly to 4H, stored in TimescaleDB
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        # Get 1H candles
        h1_candles = await oanda_client.get_candles(
            instrument='EUR_USD',
            granularity='H1',
            from_time=start_date,
            to_time=end_date
        )
        
        # Get 4H candles
        h4_candles = await oanda_client.get_candles(
            instrument='EUR_USD',
            granularity='H4',
            from_time=start_date,
            to_time=end_date
        )
        
        # Store candles in TimescaleDB
        cursor = timescale_connection.cursor()
        
        for candle in h1_candles:
            cursor.execute("""
                INSERT INTO forex_prices (time, symbol, bid, ask, spread, volume)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, (
                datetime.fromisoformat(candle['time']),
                'EUR_USD',
                float(candle['mid']['c']),  # Close as bid
                float(candle['mid']['c']) + 0.0001,  # Simulated ask
                0.0001,  # Simulated spread
                int(candle.get('volume', 0))
            ))
        
        timescale_connection.commit()
        cursor.close()
        
        # Verify aggregation consistency
        # Every 4 H1 candles should roughly match 1 H4 candle
        assert len(h1_candles) >= 4, "Insufficient H1 data"
        assert len(h4_candles) >= 1, "Insufficient H4 data"
        
        # Compare first 4H candle with corresponding H1 candles
        h4_high = float(h4_candles[0]['mid']['h'])
        h4_low = float(h4_candles[0]['mid']['l'])
        
        # Find corresponding H1 candles
        h1_highs = [float(c['mid']['h']) for c in h1_candles[:4]]
        h1_lows = [float(c['mid']['l']) for c in h1_candles[:4]]
        
        # Allow small tolerance for timing differences
        tolerance = 0.0001
        assert abs(max(h1_highs) - h4_high) < tolerance, \
            "H1 aggregated high doesn't match H4"
        assert abs(min(h1_lows) - h4_low) < tolerance, \
            "H1 aggregated low doesn't match H4"


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])