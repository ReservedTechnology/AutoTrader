"""
Test Suite for Smart Order Routing and Execution
Following TDD methodology for forex bot targeting 25% annual returns
Tests for intelligent order routing with <500ms execution
"""
import pytest
import pytest_asyncio
import asyncio
import numpy as np
import pandas as pd
import os
import psycopg2
from supabase import create_client, Client
from datetime import datetime, timedelta
import json
import time
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()


class TestSmartOrderRouting:
    """
    Test suite for smart order routing and execution
    Target: <500ms execution, optimal liquidity sourcing
    """
    
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
    def supabase_client(self) -> Client:
        """Initialize Supabase client"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        client = create_client(url, key)
        return client
    
    @pytest.fixture
    async def order_router(self):
        """Initialize smart order router"""
        from src.execution.smart_order_router import SmartOrderRouter
        
        router = SmartOrderRouter(
            primary_broker='oanda',
            backup_brokers=['tradermade'],
            max_slippage=0.0002,  # 2 pips
            execution_timeout=500  # 500ms
        )
        await router.initialize()
        yield router
        await router.close()
    
    @pytest.mark.asyncio
    async def test_order_routing_logic(self, order_router):
        """
        Test 6.1.1: Test order routing decision logic
        Acceptance: Route to best execution venue
        """
        # Sample order
        order = {
            'symbol': 'EUR_USD',
            'type': 'market',
            'side': 'buy',
            'quantity': 100000,
            'max_slippage': 0.0002
        }
        
        # Get routing decision
        routing_decision = await order_router.determine_route(order)
        
        assert 'venue' in routing_decision, "Missing venue in routing decision"
        assert 'estimated_cost' in routing_decision, "Missing cost estimate"
        assert 'estimated_time' in routing_decision, "Missing time estimate"
        
        # Verify venue selection
        valid_venues = ['oanda', 'tradermade', 'aggregated']
        assert routing_decision['venue'] in valid_venues, \
            f"Invalid venue: {routing_decision['venue']}"
        
        # Check execution time estimate
        assert routing_decision['estimated_time'] < 500, \
            f"Estimated time {routing_decision['estimated_time']}ms exceeds 500ms"
    
    @pytest.mark.asyncio
    async def test_liquidity_aggregation(self, order_router):
        """
        Test 6.1.2: Test liquidity aggregation from multiple sources
        Acceptance: Aggregate best bid/ask from all sources
        """
        symbol = 'EUR_USD'
        
        # Get aggregated liquidity
        liquidity = await order_router.aggregate_liquidity(symbol)
        
        assert 'best_bid' in liquidity, "Missing best bid"
        assert 'best_ask' in liquidity, "Missing best ask"
        assert 'total_bid_size' in liquidity, "Missing bid size"
        assert 'total_ask_size' in liquidity, "Missing ask size"
        assert 'sources' in liquidity, "Missing source breakdown"
        
        # Verify spread
        spread = liquidity['best_ask'] - liquidity['best_bid']
        assert spread > 0, "Invalid spread (ask <= bid)"
        assert spread < 0.001, f"Spread too wide: {spread:.5f}"
        
        # Check source diversity
        assert len(liquidity['sources']) > 0, "No liquidity sources"
    
    @pytest.mark.asyncio
    async def test_execution_speed(self, order_router, timescale_connection):
        """
        Test 6.1.3: Test order execution speed
        Acceptance: Execute orders in <500ms
        """
        order = {
            'symbol': 'EUR_USD',
            'type': 'market',
            'side': 'buy',
            'quantity': 10000,
            'order_id': f'test_{datetime.now().timestamp()}'
        }
        
        # Measure execution time
        start_time = time.time()
        result = await order_router.execute_order(order)
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        
        assert execution_time < 500, \
            f"Execution time {execution_time:.1f}ms exceeds 500ms limit"
        
        # Store execution metrics
        cursor = timescale_connection.cursor()
        cursor.execute("""
            INSERT INTO execution_metrics (time, data)
            VALUES (%s, %s);
        """, (
            datetime.now(),
            json.dumps({
                'order_id': order['order_id'],
                'symbol': order['symbol'],
                'execution_time_ms': execution_time,
                'venue': result.get('venue', 'unknown'),
                'status': result.get('status', 'unknown')
            })
        ))
        timescale_connection.commit()
        cursor.close()
        
        print(f"Order executed in {execution_time:.1f}ms")
    
    @pytest.mark.asyncio
    async def test_slippage_control(self, order_router):
        """
        Test 6.1.4: Test slippage control
        Acceptance: Slippage within specified limits
        """
        order = {
            'symbol': 'GBP_JPY',
            'type': 'market',
            'side': 'sell',
            'quantity': 50000,
            'max_slippage': 0.0003,  # 3 pips max
            'expected_price': 150.500
        }
        
        # Execute with slippage control
        result = await order_router.execute_with_slippage_control(order)
        
        if result['status'] == 'filled':
            actual_price = result['fill_price']
            slippage = abs(actual_price - order['expected_price'])
            
            assert slippage <= order['max_slippage'], \
                f"Slippage {slippage:.5f} exceeds max {order['max_slippage']}"
            
            print(f"Executed at {actual_price:.3f}, slippage: {slippage:.5f}")
        elif result['status'] == 'rejected':
            assert result['reason'] == 'slippage_exceeded', \
                "Order rejected for wrong reason"
    
    @pytest.mark.asyncio
    async def test_order_splitting(self, order_router):
        """
        Test 6.1.5: Test large order splitting
        Acceptance: Split large orders for better execution
        """
        large_order = {
            'symbol': 'USD_ZAR',
            'type': 'market',
            'side': 'buy',
            'quantity': 1000000,  # Large order
            'split_threshold': 100000
        }
        
        # Split order
        split_orders = await order_router.split_order(large_order)
        
        assert len(split_orders) > 1, "Large order not split"
        
        # Verify total quantity
        total_qty = sum(o['quantity'] for o in split_orders)
        assert total_qty == large_order['quantity'], \
            f"Split quantity {total_qty} doesn't match original {large_order['quantity']}"
        
        # Each child order should be below threshold
        for child_order in split_orders:
            assert child_order['quantity'] <= large_order['split_threshold'], \
                f"Child order {child_order['quantity']} exceeds threshold"
            assert 'parent_id' in child_order, "Missing parent reference"
    
    @pytest.mark.asyncio
    async def test_venue_failover(self, order_router, supabase_client):
        """
        Test 6.1.6: Test automatic venue failover
        Acceptance: Switch to backup venue on failure
        """
        order = {
            'symbol': 'EUR_USD',
            'type': 'market',
            'side': 'buy',
            'quantity': 25000
        }
        
        # Simulate primary venue failure
        await order_router.simulate_venue_failure('oanda')
        
        # Execute order (should use backup)
        result = await order_router.execute_order(order)
        
        assert result['status'] in ['filled', 'partial', 'pending'], \
            "Order failed completely"
        assert result['venue'] != 'oanda', \
            "Still using failed venue"
        
        # Log failover event
        failover_event = {
            'event_type': 'venue_failover',
            'failed_venue': 'oanda',
            'backup_venue': result['venue'],
            'order_id': order.get('order_id', 'test'),
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            response = supabase_client.table('system_events').insert(failover_event).execute()
            assert response.data, "Failed to log failover event"
        except Exception as e:
            print(f"Failover logging: {e}")
    
    @pytest.mark.asyncio
    async def test_partial_fill_handling(self, order_router, timescale_connection):
        """
        Test 6.1.7: Test partial fill handling
        Acceptance: Properly handle and track partial fills
        """
        order = {
            'symbol': 'USD_TRY',
            'type': 'limit',
            'side': 'sell',
            'quantity': 200000,
            'limit_price': 30.500,
            'order_id': f'partial_test_{datetime.now().timestamp()}'
        }
        
        # Execute order (may result in partial fill)
        result = await order_router.execute_order(order)
        
        if result['status'] == 'partial':
            assert 'filled_quantity' in result, "Missing filled quantity"
            assert 'remaining_quantity' in result, "Missing remaining quantity"
            assert result['filled_quantity'] > 0, "No quantity filled"
            assert result['filled_quantity'] < order['quantity'], \
                "Full fill reported as partial"
            
            # Store partial fill info
            cursor = timescale_connection.cursor()
            cursor.execute("""
                INSERT INTO order_fills (time, data)
                VALUES (%s, %s);
            """, (
                datetime.now(),
                json.dumps({
                    'order_id': order['order_id'],
                    'status': 'partial',
                    'filled_quantity': result['filled_quantity'],
                    'remaining_quantity': result['remaining_quantity'],
                    'avg_fill_price': result.get('avg_fill_price')
                })
            ))
            timescale_connection.commit()
            cursor.close()
    
    @pytest.mark.asyncio
    async def test_order_types(self, order_router):
        """
        Test 6.1.8: Test different order types
        Acceptance: Support market, limit, stop, and stop-limit orders
        """
        order_types = [
            {
                'type': 'market',
                'symbol': 'EUR_USD',
                'side': 'buy',
                'quantity': 10000
            },
            {
                'type': 'limit',
                'symbol': 'GBP_JPY',
                'side': 'sell',
                'quantity': 15000,
                'limit_price': 150.500
            },
            {
                'type': 'stop',
                'symbol': 'AUD_JPY',
                'side': 'buy',
                'quantity': 20000,
                'stop_price': 95.000
            },
            {
                'type': 'stop_limit',
                'symbol': 'NZD_JPY',
                'side': 'sell',
                'quantity': 12000,
                'stop_price': 87.500,
                'limit_price': 87.450
            }
        ]
        
        for order in order_types:
            validation = await order_router.validate_order(order)
            
            assert validation['valid'], \
                f"Order type {order['type']} validation failed: {validation.get('reason')}"
            
            # Verify required fields
            if order['type'] == 'limit':
                assert 'limit_price' in order, "Missing limit price"
            elif order['type'] == 'stop':
                assert 'stop_price' in order, "Missing stop price"
            elif order['type'] == 'stop_limit':
                assert 'stop_price' in order and 'limit_price' in order, \
                    "Missing stop or limit price"
    
    @pytest.mark.asyncio
    async def test_time_in_force(self, order_router):
        """
        Test 6.1.9: Test time-in-force options
        Acceptance: Support IOC, FOK, GTC, GTD
        """
        tif_options = [
            {'tif': 'IOC', 'description': 'Immediate or Cancel'},
            {'tif': 'FOK', 'description': 'Fill or Kill'},
            {'tif': 'GTC', 'description': 'Good Till Cancelled'},
            {'tif': 'GTD', 'description': 'Good Till Date', 'expire_time': datetime.now() + timedelta(hours=4)}
        ]
        
        for tif_config in tif_options:
            order = {
                'symbol': 'EUR_USD',
                'type': 'limit',
                'side': 'buy',
                'quantity': 5000,
                'limit_price': 1.1000,
                'time_in_force': tif_config['tif']
            }
            
            if tif_config['tif'] == 'GTD':
                order['expire_time'] = tif_config['expire_time']
            
            result = await order_router.submit_order(order)
            
            assert 'order_id' in result, f"No order ID for {tif_config['tif']}"
            assert result['time_in_force'] == tif_config['tif'], \
                f"TIF mismatch for {tif_config['tif']}"
    
    @pytest.mark.asyncio
    async def test_order_modification(self, order_router):
        """
        Test 6.1.10: Test order modification
        Acceptance: Modify pending orders
        """
        # Create initial order
        original_order = {
            'symbol': 'EUR_USD',
            'type': 'limit',
            'side': 'buy',
            'quantity': 10000,
            'limit_price': 1.0950,
            'time_in_force': 'GTC'
        }
        
        result = await order_router.submit_order(original_order)
        order_id = result['order_id']
        
        # Modify order
        modifications = {
            'limit_price': 1.0960,
            'quantity': 12000
        }
        
        mod_result = await order_router.modify_order(order_id, modifications)
        
        assert mod_result['status'] == 'modified', \
            f"Modification failed: {mod_result.get('reason')}"
        assert mod_result['new_price'] == modifications['limit_price'], \
            "Price not updated"
        assert mod_result['new_quantity'] == modifications['quantity'], \
            "Quantity not updated"
        
        # Cancel order
        cancel_result = await order_router.cancel_order(order_id)
        assert cancel_result['status'] == 'cancelled', \
            "Failed to cancel order"


class TestOrderExecutionMonitoring:
    """Test suite for order execution monitoring and analytics"""
    
    @pytest.fixture
    def execution_history(self):
        """Generate sample execution history"""
        executions = []
        for i in range(100):
            executions.append({
                'order_id': f'order_{i}',
                'symbol': np.random.choice(['EUR_USD', 'GBP_JPY', 'AUD_JPY']),
                'execution_time': np.random.uniform(50, 450),  # ms
                'slippage': np.random.uniform(-0.0003, 0.0003),
                'venue': np.random.choice(['oanda', 'tradermade']),
                'status': np.random.choice(['filled', 'partial'], p=[0.9, 0.1])
            })
        return pd.DataFrame(executions)
    
    @pytest.mark.asyncio
    async def test_execution_analytics(self, execution_history, supabase_client):
        """
        Test 6.2.1: Analyze execution quality
        Acceptance: Track and report execution metrics
        """
        from src.execution.analytics import ExecutionAnalyzer
        
        analyzer = ExecutionAnalyzer()
        metrics = analyzer.calculate_metrics(execution_history)
        
        # Verify metrics
        assert 'avg_execution_time' in metrics, "Missing avg execution time"
        assert 'avg_slippage' in metrics, "Missing avg slippage"
        assert 'fill_rate' in metrics, "Missing fill rate"
        assert 'venue_distribution' in metrics, "Missing venue distribution"
        
        # Check performance
        assert metrics['avg_execution_time'] < 500, \
            f"Avg execution time {metrics['avg_execution_time']:.1f}ms exceeds 500ms"
        assert abs(metrics['avg_slippage']) < 0.0002, \
            f"Avg slippage {metrics['avg_slippage']:.5f} too high"
        
        # Store analytics in Supabase
        analytics_data = {
            'period': 'daily',
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            response = supabase_client.table('execution_analytics').insert(analytics_data).execute()
            assert response.data, "Failed to store analytics"
        except Exception as e:
            print(f"Analytics storage: {e}")
        
        print(f"Execution Analytics:")
        print(f"  Avg Time: {metrics['avg_execution_time']:.1f}ms")
        print(f"  Avg Slippage: {metrics['avg_slippage']:.5f}")
        print(f"  Fill Rate: {metrics['fill_rate']:.1%}")
    
    def test_venue_performance_comparison(self, execution_history):
        """
        Test 6.2.2: Compare venue performance
        Acceptance: Identify best performing venues
        """
        from src.execution.analytics import VenueComparator
        
        comparator = VenueComparator()
        venue_stats = comparator.compare_venues(execution_history)
        
        for venue, stats in venue_stats.items():
            print(f"\n{venue} Performance:")
            print(f"  Avg Execution: {stats['avg_time']:.1f}ms")
            print(f"  Avg Slippage: {stats['avg_slippage']:.5f}")
            print(f"  Fill Rate: {stats['fill_rate']:.1%}")
            
            # Verify stats
            assert stats['avg_time'] > 0, f"Invalid avg time for {venue}"
            assert stats['fill_rate'] >= 0 and stats['fill_rate'] <= 1, \
                f"Invalid fill rate for {venue}"


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])