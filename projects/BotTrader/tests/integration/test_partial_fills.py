"""
Integration Test for Partial Fill Handling
Following TDD methodology for forex bot targeting 25% annual returns
Tests partial order execution, position tracking, and cost averaging
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional
from decimal import Decimal


class TestPartialFills:
    """Integration test for partial fill handling"""
    
    @pytest.fixture
    def fill_manager(self):
        """Initialize partial fill manager"""
        from src.trading.partial_fill_manager import PartialFillManager
        
        manager = PartialFillManager(
            min_fill_size=1000,
            max_slices=10,
            timeout_minutes=30
        )
        return manager
    
    @pytest.fixture
    def order_data(self):
        """Sample order for testing"""
        return {
            'order_id': 'ORD123456',
            'pair': 'EUR_USD',
            'side': 'BUY',
            'total_quantity': 100000,
            'order_type': 'LIMIT',
            'limit_price': 1.10500,
            'created_at': datetime.now()
        }
    
    @pytest.mark.integration
    def test_partial_fill_tracking(self, fill_manager, order_data):
        """
        Test IT.6.1: Track partial fills accurately
        Acceptance: Maintain correct fill status
        """
        # Initial order
        fill_manager.register_order(order_data)
        
        # First partial fill
        fill1 = {
            'fill_id': 'FILL001',
            'quantity': 30000,
            'price': 1.10498,
            'timestamp': datetime.now(),
            'commission': 2.50
        }
        
        fill_manager.process_fill(order_data['order_id'], fill1)
        
        status = fill_manager.get_order_status(order_data['order_id'])
        assert status['filled_quantity'] == 30000
        assert status['remaining_quantity'] == 70000
        assert status['fill_percentage'] == 30.0
        assert status['status'] == 'PARTIAL_FILLED'
        
        # Second partial fill
        fill2 = {
            'fill_id': 'FILL002',
            'quantity': 50000,
            'price': 1.10499,
            'timestamp': datetime.now() + timedelta(seconds=5),
            'commission': 4.20
        }
        
        fill_manager.process_fill(order_data['order_id'], fill2)
        
        status = fill_manager.get_order_status(order_data['order_id'])
        assert status['filled_quantity'] == 80000
        assert status['remaining_quantity'] == 20000
        assert status['fill_percentage'] == 80.0
        
        # Final fill
        fill3 = {
            'fill_id': 'FILL003',
            'quantity': 20000,
            'price': 1.10501,
            'timestamp': datetime.now() + timedelta(seconds=10),
            'commission': 1.70
        }
        
        fill_manager.process_fill(order_data['order_id'], fill3)
        
        status = fill_manager.get_order_status(order_data['order_id'])
        assert status['filled_quantity'] == 100000
        assert status['remaining_quantity'] == 0
        assert status['fill_percentage'] == 100.0
        assert status['status'] == 'FILLED'
    
    @pytest.mark.integration
    def test_average_price_calculation(self, fill_manager, order_data):
        """
        Test IT.6.2: Calculate weighted average fill price
        Acceptance: Accurate cost basis calculation
        """
        fill_manager.register_order(order_data)
        
        fills = [
            {'quantity': 25000, 'price': 1.10495, 'commission': 2.00},
            {'quantity': 35000, 'price': 1.10498, 'commission': 2.80},
            {'quantity': 40000, 'price': 1.10502, 'commission': 3.20}
        ]
        
        for fill in fills:
            fill_manager.process_fill(order_data['order_id'], fill)
        
        # Calculate average price
        avg_price = fill_manager.calculate_average_price(order_data['order_id'])
        
        # Manual calculation
        total_cost = sum(f['quantity'] * f['price'] for f in fills)
        total_quantity = sum(f['quantity'] for f in fills)
        expected_avg = total_cost / total_quantity
        
        assert abs(avg_price - expected_avg) < 0.00001
        
        # Calculate average with commissions
        avg_with_comm = fill_manager.calculate_average_price(
            order_data['order_id'],
            include_commission=True
        )
        
        total_commission = sum(f['commission'] for f in fills)
        commission_per_unit = total_commission / total_quantity
        expected_with_comm = expected_avg + (commission_per_unit / total_quantity)
        
        assert avg_with_comm > avg_price  # Should be higher with commission
    
    @pytest.mark.integration
    def test_fill_timeout_handling(self, fill_manager):
        """
        Test IT.6.3: Handle order timeout with partial fills
        Acceptance: Cancel remaining after timeout
        """
        order = {
            'order_id': 'ORD789',
            'total_quantity': 50000,
            'created_at': datetime.now() - timedelta(minutes=35)  # Past timeout
        }
        
        fill_manager.register_order(order)
        
        # Partial fill before timeout
        fill_manager.process_fill(order['order_id'], {
            'quantity': 20000,
            'price': 1.10500,
            'timestamp': datetime.now() - timedelta(minutes=25)
        })
        
        # Check timeout
        timed_out = fill_manager.check_timeouts()
        
        assert order['order_id'] in timed_out
        
        status = fill_manager.get_order_status(order['order_id'])
        assert status['status'] == 'CANCELLED'
        assert status['cancel_reason'] == 'timeout'
        assert status['filled_quantity'] == 20000
        assert status['cancelled_quantity'] == 30000
    
    @pytest.mark.integration
    def test_fill_slippage_analysis(self, fill_manager):
        """
        Test IT.6.4: Analyze fill slippage
        Acceptance: Track execution quality
        """
        order = {
            'order_id': 'ORD456',
            'side': 'BUY',
            'total_quantity': 100000,
            'limit_price': 1.10500,
            'expected_price': 1.10500
        }
        
        fill_manager.register_order(order)
        
        # Fills with varying slippage
        fills = [
            {'quantity': 30000, 'price': 1.10502},  # 2 pip negative slippage
            {'quantity': 40000, 'price': 1.10498},  # 2 pip positive slippage
            {'quantity': 30000, 'price': 1.10505}   # 5 pip negative slippage
        ]
        
        for fill in fills:
            fill_manager.process_fill(order['order_id'], fill)
        
        # Analyze slippage
        slippage = fill_manager.analyze_slippage(order['order_id'])
        
        assert 'total_slippage' in slippage
        assert 'average_slippage_pips' in slippage
        assert 'positive_slippage' in slippage
        assert 'negative_slippage' in slippage
        
        # Calculate expected slippage
        avg_fill = sum(f['quantity'] * f['price'] for f in fills) / order['total_quantity']
        expected_slippage = (avg_fill - order['expected_price']) * 10000  # in pips
        
        assert abs(slippage['average_slippage_pips'] - expected_slippage) < 0.1
    
    @pytest.mark.integration
    def test_partial_fill_position_management(self, fill_manager):
        """
        Test IT.6.5: Manage positions with partial fills
        Acceptance: Correct position sizing and risk
        """
        position = {
            'pair': 'EUR_USD',
            'intended_size': 100000,
            'stop_loss': 1.10400,
            'take_profit': 1.10700
        }
        
        order_id = 'ORD999'
        fill_manager.register_order({
            'order_id': order_id,
            'total_quantity': position['intended_size']
        })
        
        # Partial fills
        fills = [
            {'quantity': 40000, 'price': 1.10500},
            {'quantity': 35000, 'price': 1.10502}
        ]
        
        for fill in fills:
            fill_manager.process_fill(order_id, fill)
        
        # Update position based on fills
        updated_position = fill_manager.update_position(order_id, position)
        
        assert updated_position['actual_size'] == 75000  # 75% filled
        assert updated_position['average_entry'] > 1.10500
        
        # Adjust risk parameters
        risk_adjustment = fill_manager.adjust_risk_for_partial(
            updated_position,
            original_risk_amount=2000  # Original risk for full position
        )
        
        assert risk_adjustment['adjusted_risk'] == 1500  # 75% of original
        assert risk_adjustment['adjusted_stop'] == position['stop_loss']  # Stop unchanged
        
        # Optionally widen stop to maintain risk
        maintain_risk = fill_manager.maintain_risk_amount(
            updated_position,
            target_risk=2000
        )
        
        assert maintain_risk['new_stop'] < position['stop_loss']  # Wider stop
    
    @pytest.mark.integration
    def test_fill_completion_strategies(self, fill_manager):
        """
        Test IT.6.6: Strategies for completing partial fills
        Acceptance: Smart order completion logic
        """
        order = {
            'order_id': 'ORD111',
            'total_quantity': 100000,
            'limit_price': 1.10500,
            'side': 'BUY',
            'urgency': 'medium'
        }
        
        fill_manager.register_order(order)
        
        # Initial partial fill
        fill_manager.process_fill(order['order_id'], {
            'quantity': 30000,
            'price': 1.10500
        })
        
        # Market moves away
        current_market = {
            'bid': 1.10510,
            'ask': 1.10512
        }
        
        # Determine completion strategy
        strategy = fill_manager.determine_completion_strategy(
            order['order_id'],
            current_market,
            time_elapsed_minutes=10
        )
        
        assert strategy['action'] in ['chase', 'wait', 'cancel', 'market_order']
        
        if order['urgency'] == 'high':
            assert strategy['action'] in ['chase', 'market_order']
        elif order['urgency'] == 'low':
            assert strategy['action'] in ['wait', 'cancel']
        
        # Generate new order for remaining
        if strategy['action'] == 'chase':
            new_order = fill_manager.create_chase_order(
                order['order_id'],
                current_market,
                max_chase_pips=5
            )
            
            assert new_order['quantity'] == 70000  # Remaining
            assert new_order['limit_price'] >= current_market['ask']
            assert new_order['limit_price'] <= order['limit_price'] + 0.0005  # Max 5 pips
    
    @pytest.mark.integration
    def test_multi_venue_fills(self, fill_manager):
        """
        Test IT.6.7: Handle fills from multiple venues
        Acceptance: Aggregate fills across venues
        """
        order = {
            'order_id': 'ORD222',
            'total_quantity': 200000,
            'venues': ['oanda', 'interactive_brokers', 'currenex']
        }
        
        fill_manager.register_order(order)
        
        # Fills from different venues
        venue_fills = [
            {'venue': 'oanda', 'quantity': 80000, 'price': 1.10501, 'latency_ms': 45},
            {'venue': 'interactive_brokers', 'quantity': 70000, 'price': 1.10499, 'latency_ms': 62},
            {'venue': 'currenex', 'quantity': 50000, 'price': 1.10500, 'latency_ms': 38}
        ]
        
        for fill in venue_fills:
            fill_manager.process_venue_fill(order['order_id'], fill)
        
        # Analyze venue performance
        venue_analysis = fill_manager.analyze_venue_performance(order['order_id'])
        
        assert 'best_venue' in venue_analysis
        assert 'worst_venue' in venue_analysis
        assert 'average_latency_by_venue' in venue_analysis
        
        # Best execution venue (best price and latency)
        assert venue_analysis['best_venue'] == 'currenex'  # Best price and latency
        
        # Venue fill distribution
        distribution = venue_analysis['fill_distribution']
        assert distribution['oanda'] == 80000 / 200000
        assert distribution['interactive_brokers'] == 70000 / 200000
        assert distribution['currenex'] == 50000 / 200000
    
    @pytest.mark.integration
    def test_fill_reconciliation(self, fill_manager):
        """
        Test IT.6.8: Reconcile fills with broker confirmations
        Acceptance: Detect and resolve discrepancies
        """
        # Internal fill records
        internal_fills = [
            {'fill_id': 'INT001', 'quantity': 50000, 'price': 1.10500},
            {'fill_id': 'INT002', 'quantity': 30000, 'price': 1.10502}
        ]
        
        # Broker confirmations (with discrepancy)
        broker_fills = [
            {'fill_id': 'BRK001', 'quantity': 50000, 'price': 1.10500},
            {'fill_id': 'BRK002', 'quantity': 30000, 'price': 1.10503}  # Price mismatch
        ]
        
        # Reconcile
        reconciliation = fill_manager.reconcile_fills(
            internal_fills,
            broker_fills,
            order_id='ORD333'
        )
        
        assert reconciliation['has_discrepancies'] is True
        assert len(reconciliation['discrepancies']) > 0
        
        discrepancy = reconciliation['discrepancies'][0]
        assert discrepancy['type'] == 'price_mismatch'
        assert discrepancy['internal_price'] == 1.10502
        assert discrepancy['broker_price'] == 1.10503
        
        # Resolve discrepancies (use broker as truth)
        resolved = fill_manager.resolve_discrepancies(
            reconciliation['discrepancies'],
            resolution_rule='broker_override'
        )
        
        assert resolved['INT002']['price'] == 1.10503  # Updated to broker price
        assert resolved['INT002']['adjustment_reason'] == 'broker_confirmation'
    
    @pytest.mark.integration
    def test_partial_fill_reporting(self, fill_manager):
        """
        Test IT.6.9: Generate partial fill reports
        Acceptance: Comprehensive fill analytics
        """
        # Create multiple orders with various fill patterns
        orders = [
            {'order_id': 'RPT001', 'total': 100000, 'fills': [30000, 40000, 30000]},
            {'order_id': 'RPT002', 'total': 50000, 'fills': [50000]},  # Complete fill
            {'order_id': 'RPT003', 'total': 75000, 'fills': [25000, 25000]}  # Partial
        ]
        
        for order in orders:
            fill_manager.register_order({
                'order_id': order['order_id'],
                'total_quantity': order['total']
            })
            
            for i, fill_qty in enumerate(order['fills']):
                fill_manager.process_fill(order['order_id'], {
                    'quantity': fill_qty,
                    'price': 1.10500 + i * 0.00001
                })
        
        # Generate report
        report = fill_manager.generate_fill_report(
            start_date=datetime.now() - timedelta(hours=1),
            end_date=datetime.now()
        )
        
        assert report['total_orders'] == 3
        assert report['fully_filled'] == 2
        assert report['partially_filled'] == 1
        assert report['average_fill_rate'] > 0.8  # Good fill rate
        
        # Fill statistics
        assert 'average_slices_per_order' in report
        assert 'average_time_to_fill' in report
        assert 'fill_rate_by_hour' in report


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-m', 'integration'])