"""
Test Suite for Order Management System
Following TDD methodology for forex bot targeting 25% annual returns
Tests for order creation, validation, execution, and lifecycle management
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import json
import asyncio
from enum import Enum


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"


class OrderStatus(Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIAL_FILLED = "PARTIAL_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class TestOrderCreation:
    """Test suite for order creation and validation"""
    
    @pytest.fixture
    def order_manager(self):
        """Initialize order management system"""
        from src.trading.order_management import OrderManager
        
        manager = OrderManager(
            broker='oanda',
            account_id='test_account',
            max_slippage=0.0002
        )
        return manager
    
    @pytest.fixture
    def market_data(self):
        """Current market prices"""
        return {
            'EUR_USD': {'bid': 1.10500, 'ask': 1.10502, 'spread': 0.00002},
            'GBP_USD': {'bid': 1.25000, 'ask': 1.25003, 'spread': 0.00003},
            'USD_JPY': {'bid': 110.500, 'ask': 110.503, 'spread': 0.003}
        }
    
    def test_create_market_order(self, order_manager, market_data):
        """
        Test 7.1.1: Create market order
        Acceptance: Order created with correct parameters
        """
        order = order_manager.create_order(
            symbol='EUR_USD',
            side='BUY',
            quantity=10000,
            order_type=OrderType.MARKET,
            current_price=market_data['EUR_USD']
        )
        
        assert order is not None
        assert order.symbol == 'EUR_USD'
        assert order.side == 'BUY'
        assert order.quantity == 10000
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.PENDING
        assert order.order_id is not None
        assert order.created_at is not None
        
        # Market orders should use ask price for buy
        assert order.expected_price == market_data['EUR_USD']['ask']
    
    def test_create_limit_order(self, order_manager, market_data):
        """
        Test 7.1.2: Create limit order
        Acceptance: Limit order with price validation
        """
        limit_price = 1.10450
        
        order = order_manager.create_order(
            symbol='EUR_USD',
            side='BUY',
            quantity=10000,
            order_type=OrderType.LIMIT,
            limit_price=limit_price,
            current_price=market_data['EUR_USD']
        )
        
        assert order.order_type == OrderType.LIMIT
        assert order.limit_price == limit_price
        assert order.status == OrderStatus.PENDING
        
        # Limit buy should be below current ask
        assert limit_price < market_data['EUR_USD']['ask']
        
        # Test sell limit order
        sell_order = order_manager.create_order(
            symbol='EUR_USD',
            side='SELL',
            quantity=10000,
            order_type=OrderType.LIMIT,
            limit_price=1.10550,
            current_price=market_data['EUR_USD']
        )
        
        assert sell_order.limit_price > market_data['EUR_USD']['bid']
    
    def test_create_stop_loss_order(self, order_manager, market_data):
        """
        Test 7.1.3: Create stop-loss order
        Acceptance: Stop order with trigger price
        """
        stop_price = 1.10400  # Below current price for long position
        
        order = order_manager.create_order(
            symbol='EUR_USD',
            side='SELL',  # Closing long position
            quantity=10000,
            order_type=OrderType.STOP,
            stop_price=stop_price,
            current_price=market_data['EUR_USD'],
            position_side='LONG'
        )
        
        assert order.order_type == OrderType.STOP
        assert order.stop_price == stop_price
        assert order.triggered == False
        
        # Stop loss for long should be below current bid
        assert stop_price < market_data['EUR_USD']['bid']
    
    def test_create_trailing_stop(self, order_manager, market_data):
        """
        Test 7.1.4: Create trailing stop order
        Acceptance: Dynamic stop adjustment
        """
        trailing_distance = 0.0020  # 20 pips
        
        order = order_manager.create_order(
            symbol='EUR_USD',
            side='SELL',
            quantity=10000,
            order_type=OrderType.TRAILING_STOP,
            trailing_distance=trailing_distance,
            current_price=market_data['EUR_USD'],
            position_side='LONG'
        )
        
        assert order.order_type == OrderType.TRAILING_STOP
        assert order.trailing_distance == trailing_distance
        assert order.stop_price == market_data['EUR_USD']['bid'] - trailing_distance
        assert order.high_water_mark == market_data['EUR_USD']['bid']
        
        # Update with higher price
        new_price = {'bid': 1.10600, 'ask': 1.10602}
        order_manager.update_trailing_stop(order, new_price)
        
        assert order.high_water_mark == 1.10600
        assert order.stop_price == 1.10600 - trailing_distance
    
    def test_order_validation(self, order_manager):
        """
        Test 7.1.5: Order validation rules
        Acceptance: Rejects invalid orders
        """
        # Test invalid symbol
        with pytest.raises(ValueError, match="Invalid symbol"):
            order_manager.create_order(
                symbol='INVALID_PAIR',
                side='BUY',
                quantity=10000,
                order_type=OrderType.MARKET
            )
        
        # Test invalid quantity (negative)
        with pytest.raises(ValueError, match="Invalid quantity"):
            order_manager.create_order(
                symbol='EUR_USD',
                side='BUY',
                quantity=-10000,
                order_type=OrderType.MARKET
            )
        
        # Test invalid side
        with pytest.raises(ValueError, match="Invalid side"):
            order_manager.create_order(
                symbol='EUR_USD',
                side='INVALID',
                quantity=10000,
                order_type=OrderType.MARKET
            )
        
        # Test limit order without price
        with pytest.raises(ValueError, match="Limit price required"):
            order_manager.create_order(
                symbol='EUR_USD',
                side='BUY',
                quantity=10000,
                order_type=OrderType.LIMIT
            )


class TestOrderExecution:
    """Test suite for order execution and fills"""
    
    @pytest.fixture
    def execution_engine(self):
        """Initialize execution engine"""
        from src.trading.execution_engine import ExecutionEngine
        
        engine = ExecutionEngine(
            broker='oanda',
            latency_ms=50,
            max_retries=3
        )
        return engine
    
    @patch('requests.post')
    def test_market_order_execution(self, mock_post, execution_engine):
        """
        Test 7.2.1: Execute market order
        Acceptance: Immediate execution at market price
        """
        # Create order
        order = Mock()
        order.order_id = 'ORD123'
        order.symbol = 'EUR_USD'
        order.side = 'BUY'
        order.quantity = 10000
        order.order_type = OrderType.MARKET
        order.status = OrderStatus.PENDING
        
        # Mock broker response
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            'orderCreateTransaction': {
                'id': 'TXN123',
                'orderID': 'ORD123',
                'price': '1.10502',
                'units': '10000',
                'time': '2025-01-29T10:00:00Z'
            },
            'orderFillTransaction': {
                'id': 'FILL123',
                'orderID': 'ORD123',
                'price': '1.10502',
                'units': '10000',
                'pl': '0.00',
                'time': '2025-01-29T10:00:00.050Z'
            }
        }
        
        # Execute order
        result = execution_engine.execute_order(order)
        
        assert result['status'] == 'FILLED'
        assert result['fill_price'] == 1.10502
        assert result['fill_quantity'] == 10000
        assert result['execution_time_ms'] <= 100
        assert order.status == OrderStatus.FILLED
    
    def test_partial_fill_handling(self, execution_engine):
        """
        Test 7.2.2: Handle partial fills
        Acceptance: Tracks cumulative fills
        """
        order = Mock()
        order.order_id = 'ORD124'
        order.symbol = 'EUR_USD'
        order.quantity = 100000
        order.filled_quantity = 0
        order.status = OrderStatus.PENDING
        
        # First partial fill
        execution_engine.process_fill(order, {
            'fill_quantity': 30000,
            'fill_price': 1.10502,
            'timestamp': datetime.now()
        })
        
        assert order.filled_quantity == 30000
        assert order.status == OrderStatus.PARTIAL_FILLED
        assert order.remaining_quantity == 70000
        
        # Second partial fill
        execution_engine.process_fill(order, {
            'fill_quantity': 50000,
            'fill_price': 1.10503,
            'timestamp': datetime.now()
        })
        
        assert order.filled_quantity == 80000
        assert order.status == OrderStatus.PARTIAL_FILLED
        
        # Final fill
        execution_engine.process_fill(order, {
            'fill_quantity': 20000,
            'fill_price': 1.10504,
            'timestamp': datetime.now()
        })
        
        assert order.filled_quantity == 100000
        assert order.status == OrderStatus.FILLED
        assert order.average_fill_price == pytest.approx(
            (30000*1.10502 + 50000*1.10503 + 20000*1.10504) / 100000,
            rel=1e-6
        )
    
    def test_slippage_tracking(self, execution_engine):
        """
        Test 7.2.3: Track execution slippage
        Acceptance: Measures price improvement/slippage
        """
        order = Mock()
        order.expected_price = 1.10502
        order.side = 'BUY'
        
        # Positive slippage (price improvement)
        slippage = execution_engine.calculate_slippage(
            order,
            fill_price=1.10500
        )
        
        assert slippage == -0.00002  # Negative means improvement for buy
        assert execution_engine.is_price_improvement(order, slippage)
        
        # Negative slippage
        slippage = execution_engine.calculate_slippage(
            order,
            fill_price=1.10510
        )
        
        assert slippage == 0.00008  # Positive means worse price for buy
        assert not execution_engine.is_price_improvement(order, slippage)
        
        # Track cumulative slippage
        execution_engine.record_slippage('EUR_USD', slippage)
        stats = execution_engine.get_slippage_stats('EUR_USD')
        
        assert 'average' in stats
        assert 'total' in stats
        assert 'count' in stats
    
    @patch('requests.post')
    def test_order_rejection(self, mock_post, execution_engine):
        """
        Test 7.2.4: Handle order rejections
        Acceptance: Proper error handling and status update
        """
        order = Mock()
        order.order_id = 'ORD125'
        order.status = OrderStatus.PENDING
        
        # Mock rejection response
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {
            'errorCode': 'INSUFFICIENT_MARGIN',
            'errorMessage': 'Insufficient margin to execute order'
        }
        
        result = execution_engine.execute_order(order)
        
        assert result['status'] == 'REJECTED'
        assert result['error_code'] == 'INSUFFICIENT_MARGIN'
        assert order.status == OrderStatus.REJECTED
        assert order.rejection_reason == 'Insufficient margin to execute order'
    
    @pytest.mark.asyncio
    async def test_async_execution(self, execution_engine):
        """
        Test 7.2.5: Asynchronous order execution
        Acceptance: Concurrent order processing
        """
        orders = []
        for i in range(5):
            order = Mock()
            order.order_id = f'ORD{i}'
            order.symbol = 'EUR_USD'
            order.quantity = 10000
            order.order_type = OrderType.MARKET
            orders.append(order)
        
        # Execute orders concurrently
        tasks = [execution_engine.async_execute(order) for order in orders]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for result in results:
            assert result['status'] in ['FILLED', 'REJECTED']


class TestOrderLifecycle:
    """Test suite for order lifecycle management"""
    
    @pytest.fixture
    def lifecycle_manager(self):
        """Initialize lifecycle manager"""
        from src.trading.order_lifecycle import OrderLifecycleManager
        
        manager = OrderLifecycleManager()
        return manager
    
    def test_order_state_transitions(self, lifecycle_manager):
        """
        Test 7.3.1: Valid state transitions
        Acceptance: Enforces state machine rules
        """
        order = Mock()
        order.status = OrderStatus.PENDING
        
        # Valid transitions from PENDING
        assert lifecycle_manager.can_transition(order, OrderStatus.SUBMITTED)
        assert lifecycle_manager.can_transition(order, OrderStatus.CANCELLED)
        assert lifecycle_manager.can_transition(order, OrderStatus.REJECTED)
        
        # Invalid transitions from PENDING
        assert not lifecycle_manager.can_transition(order, OrderStatus.FILLED)
        assert not lifecycle_manager.can_transition(order, OrderStatus.PARTIAL_FILLED)
        
        # Transition to SUBMITTED
        lifecycle_manager.transition(order, OrderStatus.SUBMITTED)
        assert order.status == OrderStatus.SUBMITTED
        
        # Valid transitions from SUBMITTED
        assert lifecycle_manager.can_transition(order, OrderStatus.FILLED)
        assert lifecycle_manager.can_transition(order, OrderStatus.PARTIAL_FILLED)
        assert lifecycle_manager.can_transition(order, OrderStatus.CANCELLED)
        
        # Cannot go back to PENDING
        assert not lifecycle_manager.can_transition(order, OrderStatus.PENDING)
    
    def test_order_expiration(self, lifecycle_manager):
        """
        Test 7.3.2: Time-based order expiration
        Acceptance: Auto-cancels expired orders
        """
        order = Mock()
        order.order_id = 'ORD126'
        order.status = OrderStatus.SUBMITTED
        order.created_at = datetime.now() - timedelta(hours=2)
        order.time_in_force = 'GTD'  # Good Till Date
        order.expire_time = datetime.now() - timedelta(minutes=1)
        
        # Check expiration
        assert lifecycle_manager.is_expired(order)
        
        # Process expiration
        lifecycle_manager.process_expiration(order)
        assert order.status == OrderStatus.EXPIRED
        assert order.expiration_time is not None
        
        # FOK order (Fill or Kill) - immediate expiration
        fok_order = Mock()
        fok_order.status = OrderStatus.SUBMITTED
        fok_order.time_in_force = 'FOK'
        fok_order.created_at = datetime.now() - timedelta(seconds=1)
        
        assert lifecycle_manager.is_expired(fok_order)
    
    def test_order_modification(self, lifecycle_manager):
        """
        Test 7.3.3: Modify pending orders
        Acceptance: Updates price/quantity for open orders
        """
        order = Mock()
        order.order_id = 'ORD127'
        order.status = OrderStatus.SUBMITTED
        order.order_type = OrderType.LIMIT
        order.limit_price = 1.10450
        order.quantity = 10000
        order.filled_quantity = 0
        
        # Modify price
        success = lifecycle_manager.modify_order(
            order,
            new_price=1.10460
        )
        
        assert success
        assert order.limit_price == 1.10460
        assert order.modified_at is not None
        assert order.modification_count == 1
        
        # Modify quantity
        success = lifecycle_manager.modify_order(
            order,
            new_quantity=15000
        )
        
        assert success
        assert order.quantity == 15000
        assert order.modification_count == 2
        
        # Cannot modify filled order
        order.status = OrderStatus.FILLED
        success = lifecycle_manager.modify_order(
            order,
            new_price=1.10470
        )
        
        assert not success
    
    def test_order_cancellation(self, lifecycle_manager):
        """
        Test 7.3.4: Cancel open orders
        Acceptance: Cancels with reason tracking
        """
        order = Mock()
        order.order_id = 'ORD128'
        order.status = OrderStatus.SUBMITTED
        order.filled_quantity = 0
        
        # Cancel order
        success = lifecycle_manager.cancel_order(
            order,
            reason='User requested'
        )
        
        assert success
        assert order.status == OrderStatus.CANCELLED
        assert order.cancellation_reason == 'User requested'
        assert order.cancelled_at is not None
        
        # Cannot cancel filled order
        filled_order = Mock()
        filled_order.status = OrderStatus.FILLED
        
        success = lifecycle_manager.cancel_order(filled_order)
        assert not success
        
        # Can cancel partially filled
        partial_order = Mock()
        partial_order.status = OrderStatus.PARTIAL_FILLED
        partial_order.filled_quantity = 5000
        partial_order.quantity = 10000
        
        success = lifecycle_manager.cancel_order(
            partial_order,
            reason='Partial fill sufficient'
        )
        
        assert success
        assert partial_order.status == OrderStatus.CANCELLED
        assert partial_order.final_quantity == 5000
    
    def test_order_history_tracking(self, lifecycle_manager):
        """
        Test 7.3.5: Track order history
        Acceptance: Complete audit trail
        """
        order = Mock()
        order.order_id = 'ORD129'
        order.status = OrderStatus.PENDING
        order.history = []
        
        # Track state changes
        lifecycle_manager.record_event(order, {
            'event': 'created',
            'timestamp': datetime.now(),
            'details': {'initial_quantity': 10000}
        })
        
        lifecycle_manager.transition(order, OrderStatus.SUBMITTED)
        lifecycle_manager.record_event(order, {
            'event': 'submitted',
            'timestamp': datetime.now(),
            'details': {'broker_id': 'BRK123'}
        })
        
        lifecycle_manager.transition(order, OrderStatus.PARTIAL_FILLED)
        lifecycle_manager.record_event(order, {
            'event': 'partial_fill',
            'timestamp': datetime.now(),
            'details': {'filled': 3000, 'price': 1.10502}
        })
        
        lifecycle_manager.transition(order, OrderStatus.FILLED)
        lifecycle_manager.record_event(order, {
            'event': 'filled',
            'timestamp': datetime.now(),
            'details': {'final_fill': 7000, 'price': 1.10503}
        })
        
        # Check history
        assert len(order.history) == 4
        assert order.history[0]['event'] == 'created'
        assert order.history[-1]['event'] == 'filled'
        
        # Calculate order metrics
        metrics = lifecycle_manager.calculate_order_metrics(order)
        assert 'total_duration_ms' in metrics
        assert 'time_to_fill_ms' in metrics
        assert 'modification_count' in metrics


class TestOrderMonitoring:
    """Test suite for order monitoring and alerts"""
    
    @pytest.fixture
    def order_monitor(self):
        """Initialize order monitor"""
        from src.trading.order_monitor import OrderMonitor
        
        monitor = OrderMonitor(
            alert_threshold_ms=500,
            max_pending_duration_s=300
        )
        return monitor
    
    def test_latency_monitoring(self, order_monitor):
        """
        Test 7.4.1: Monitor execution latency
        Acceptance: Alerts on high latency
        """
        # Record normal latency
        for _ in range(10):
            order_monitor.record_latency('EUR_USD', 45)
        
        # Record high latency
        order_monitor.record_latency('EUR_USD', 600)
        
        alerts = order_monitor.check_latency_alerts()
        assert len(alerts) > 0
        assert alerts[0]['symbol'] == 'EUR_USD'
        assert alerts[0]['latency_ms'] == 600
        assert alerts[0]['severity'] == 'WARNING'
        
        # Check statistics
        stats = order_monitor.get_latency_stats('EUR_USD')
        assert stats['average'] < 100
        assert stats['p95'] < 600
        assert stats['max'] == 600
    
    def test_stuck_order_detection(self, order_monitor):
        """
        Test 7.4.2: Detect stuck orders
        Acceptance: Identifies orders pending too long
        """
        # Create stuck order
        stuck_order = Mock()
        stuck_order.order_id = 'ORD130'
        stuck_order.status = OrderStatus.SUBMITTED
        stuck_order.created_at = datetime.now() - timedelta(minutes=10)
        
        # Create normal order
        normal_order = Mock()
        normal_order.order_id = 'ORD131'
        normal_order.status = OrderStatus.SUBMITTED
        normal_order.created_at = datetime.now() - timedelta(seconds=30)
        
        orders = [stuck_order, normal_order]
        stuck = order_monitor.find_stuck_orders(orders)
        
        assert len(stuck) == 1
        assert stuck[0].order_id == 'ORD130'
        
        # Generate alert
        alert = order_monitor.create_stuck_order_alert(stuck[0])
        assert alert['severity'] == 'HIGH'
        assert 'pending_duration_s' in alert
        assert alert['pending_duration_s'] > 300
    
    def test_fill_rate_monitoring(self, order_monitor):
        """
        Test 7.4.3: Monitor fill rates
        Acceptance: Tracks success/rejection rates
        """
        # Record order outcomes
        for _ in range(80):
            order_monitor.record_outcome('EUR_USD', 'FILLED')
        
        for _ in range(15):
            order_monitor.record_outcome('EUR_USD', 'PARTIAL_FILLED')
        
        for _ in range(5):
            order_monitor.record_outcome('EUR_USD', 'REJECTED')
        
        # Calculate fill rates
        rates = order_monitor.calculate_fill_rates('EUR_USD')
        
        assert rates['fill_rate'] == 0.80
        assert rates['partial_rate'] == 0.15
        assert rates['rejection_rate'] == 0.05
        assert rates['total_orders'] == 100
        
        # Check if alert needed (low fill rate)
        order_monitor.record_outcome('GBP_USD', 'REJECTED')
        order_monitor.record_outcome('GBP_USD', 'REJECTED')
        order_monitor.record_outcome('GBP_USD', 'FILLED')
        
        alerts = order_monitor.check_fill_rate_alerts()
        gbp_alert = [a for a in alerts if a['symbol'] == 'GBP_USD']
        assert len(gbp_alert) > 0
        assert gbp_alert[0]['fill_rate'] < 0.5


if __name__ == "__main__":
    pytest.main([__file__, '-v'])