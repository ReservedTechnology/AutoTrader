"""
Test Suite for Trade Execution
Following TDD methodology for forex bot targeting 25% annual returns
Tests for trade execution, smart order routing, and execution algorithms
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


class ExecutionAlgorithm(Enum):
    MARKET = "MARKET"
    TWAP = "TWAP"
    VWAP = "VWAP"
    ICEBERG = "ICEBERG"
    SMART = "SMART"


class TestTradeExecutor:
    """Test suite for trade execution engine"""
    
    @pytest.fixture
    def trade_executor(self):
        """Initialize trade executor"""
        from src.trading.execution.trade_executor import TradeExecutor
        
        executor = TradeExecutor(
            broker='oanda',
            max_slippage_pips=2,
            execution_timeout_ms=500
        )
        return executor
    
    @pytest.fixture
    def market_conditions(self):
        """Current market conditions"""
        return {
            'liquidity': 'high',
            'volatility': 0.0055,  # ATR
            'spread': 0.00002,
            'volume': 1500000,
            'time': datetime.now()
        }
    
    def test_immediate_execution(self, trade_executor):
        """
        Test 11.1.1: Execute trade immediately
        Acceptance: < 50ms execution time
        """
        trade = {
            'symbol': 'EUR_USD',
            'side': 'BUY',
            'quantity': 100000,
            'type': 'MARKET'
        }
        
        with patch.object(trade_executor, 'send_order') as mock_send:
            mock_send.return_value = {
                'status': 'FILLED',
                'fill_price': 1.10502,
                'fill_time': datetime.now(),
                'execution_time_ms': 45
            }
            
            result = trade_executor.execute_immediate(trade)
            
            assert result['status'] == 'FILLED'
            assert result['execution_time_ms'] < 50
            mock_send.assert_called_once()
    
    def test_smart_order_routing(self, trade_executor, market_conditions):
        """
        Test 11.1.2: Smart order routing logic
        Acceptance: Routes to best execution venue
        """
        trade = {
            'symbol': 'EUR_USD',
            'side': 'BUY',
            'quantity': 1000000,  # Large order
            'algorithm': ExecutionAlgorithm.SMART
        }
        
        # Determine best execution method
        execution_plan = trade_executor.create_execution_plan(
            trade, 
            market_conditions
        )
        
        # Large order in high liquidity should use TWAP or Iceberg
        assert execution_plan['algorithm'] in [ExecutionAlgorithm.TWAP, ExecutionAlgorithm.ICEBERG]
        assert 'slices' in execution_plan
        assert execution_plan['slices'] > 1
        
        # Small order should use market execution
        small_trade = trade.copy()
        small_trade['quantity'] = 10000
        
        small_plan = trade_executor.create_execution_plan(
            small_trade,
            market_conditions
        )
        
        assert small_plan['algorithm'] == ExecutionAlgorithm.MARKET
        assert small_plan['slices'] == 1
    
    def test_slippage_control(self, trade_executor):
        """
        Test 11.1.3: Control execution slippage
        Acceptance: Reject if slippage > threshold
        """
        trade = {
            'symbol': 'EUR_USD',
            'side': 'BUY',
            'quantity': 100000,
            'expected_price': 1.10500
        }
        
        # Acceptable slippage
        with patch.object(trade_executor, 'get_current_price') as mock_price:
            mock_price.return_value = {'ask': 1.10502}  # 2 pips slippage
            
            can_execute = trade_executor.check_slippage(trade)
            assert can_execute is True
        
        # Excessive slippage
        with patch.object(trade_executor, 'get_current_price') as mock_price:
            mock_price.return_value = {'ask': 1.10525}  # 25 pips slippage
            
            can_execute = trade_executor.check_slippage(trade)
            assert can_execute is False
    
    def test_execution_retry_logic(self, trade_executor):
        """
        Test 11.1.4: Retry failed executions
        Acceptance: Retry with exponential backoff
        """
        trade = {
            'symbol': 'EUR_USD',
            'side': 'BUY',
            'quantity': 100000
        }
        
        with patch.object(trade_executor, 'send_order') as mock_send:
            # Fail twice, then succeed
            mock_send.side_effect = [
                {'status': 'REJECTED', 'error': 'Temporary failure'},
                {'status': 'REJECTED', 'error': 'Temporary failure'},
                {'status': 'FILLED', 'fill_price': 1.10502}
            ]
            
            result = trade_executor.execute_with_retry(
                trade,
                max_retries=3,
                backoff_ms=100
            )
            
            assert result['status'] == 'FILLED'
            assert mock_send.call_count == 3
    
    def test_partial_fill_handling(self, trade_executor):
        """
        Test 11.1.5: Handle partial fills
        Acceptance: Complete remaining quantity
        """
        trade = {
            'symbol': 'EUR_USD',
            'side': 'BUY',
            'quantity': 100000,
            'order_id': 'ORD123'
        }
        
        # Simulate partial fills
        fills = [
            {'quantity': 30000, 'price': 1.10502},
            {'quantity': 50000, 'price': 1.10503},
            {'quantity': 20000, 'price': 1.10504}
        ]
        
        with patch.object(trade_executor, 'get_fill_status') as mock_status:
            mock_status.side_effect = [
                {'filled': 30000, 'remaining': 70000},
                {'filled': 80000, 'remaining': 20000},
                {'filled': 100000, 'remaining': 0}
            ]
            
            for fill in fills:
                trade_executor.process_fill(trade['order_id'], fill)
            
            final_status = trade_executor.get_order_status(trade['order_id'])
            assert final_status['filled_quantity'] == 100000
            assert final_status['status'] == 'FILLED'
            
            # Calculate average price
            avg_price = trade_executor.calculate_average_price(trade['order_id'])
            expected_avg = (30000*1.10502 + 50000*1.10503 + 20000*1.10504) / 100000
            assert abs(avg_price - expected_avg) < 0.00001


class TestExecutionAlgorithms:
    """Test suite for execution algorithms"""
    
    @pytest.fixture
    def algo_executor(self):
        """Initialize algorithmic executor"""
        from src.trading.execution.algo_executor import AlgorithmicExecutor
        
        executor = AlgorithmicExecutor()
        return executor
    
    def test_twap_execution(self, algo_executor):
        """
        Test 11.2.1: Time-Weighted Average Price execution
        Acceptance: Even distribution over time
        """
        order = {
            'symbol': 'EUR_USD',
            'side': 'BUY',
            'quantity': 1000000,
            'duration_seconds': 300  # 5 minutes
        }
        
        slices = algo_executor.calculate_twap_slices(
            order,
            slice_interval_seconds=30
        )
        
        assert len(slices) == 10  # 300/30 = 10 slices
        assert all(s['quantity'] == 100000 for s in slices)  # Even distribution
        assert slices[0]['execute_at'] < slices[-1]['execute_at']
        
        # Verify time spacing
        for i in range(1, len(slices)):
            time_diff = (slices[i]['execute_at'] - slices[i-1]['execute_at']).total_seconds()
            assert abs(time_diff - 30) < 1
    
    def test_vwap_execution(self, algo_executor):
        """
        Test 11.2.2: Volume-Weighted Average Price execution
        Acceptance: Match market volume profile
        """
        order = {
            'symbol': 'EUR_USD',
            'side': 'BUY',
            'quantity': 1000000
        }
        
        # Historical volume profile (U-shaped)
        volume_profile = {
            '09:00': 0.15,  # 15% of daily volume
            '10:00': 0.10,
            '11:00': 0.08,
            '12:00': 0.07,
            '13:00': 0.08,
            '14:00': 0.12,
            '15:00': 0.15,
            '16:00': 0.25   # Highest at close
        }
        
        slices = algo_executor.calculate_vwap_slices(
            order,
            volume_profile
        )
        
        # Should match volume distribution
        assert len(slices) == len(volume_profile)
        assert slices[-1]['quantity'] == 250000  # 25% of total
        assert slices[3]['quantity'] == 70000    # 7% of total
        
        # Total should match order quantity
        total_quantity = sum(s['quantity'] for s in slices)
        assert total_quantity == order['quantity']
    
    def test_iceberg_execution(self, algo_executor):
        """
        Test 11.2.3: Iceberg order execution
        Acceptance: Hide large order size
        """
        order = {
            'symbol': 'EUR_USD',
            'side': 'BUY',
            'quantity': 1000000,
            'visible_quantity': 50000  # Only show 50k at a time
        }
        
        iceberg_orders = algo_executor.create_iceberg_orders(order)
        
        # Each visible slice should be 50k or less
        assert all(o['visible'] <= 50000 for o in iceberg_orders)
        
        # Total should match
        total = sum(o['total'] for o in iceberg_orders)
        assert total == order['quantity']
        
        # Should create multiple orders
        assert len(iceberg_orders) >= order['quantity'] / order['visible_quantity']
    
    def test_adaptive_execution(self, algo_executor):
        """
        Test 11.2.4: Adaptive execution based on market conditions
        Acceptance: Adjust strategy dynamically
        """
        order = {
            'symbol': 'EUR_USD',
            'side': 'BUY',
            'quantity': 500000,
            'urgency': 'medium'
        }
        
        # High volatility conditions
        high_vol_conditions = {
            'volatility': 0.015,  # High
            'spread': 0.00005,    # Wide
            'liquidity': 'low'
        }
        
        high_vol_strategy = algo_executor.select_adaptive_strategy(
            order,
            high_vol_conditions
        )
        
        # Should use careful execution in high volatility
        assert high_vol_strategy['algorithm'] in [ExecutionAlgorithm.TWAP, ExecutionAlgorithm.ICEBERG]
        assert high_vol_strategy['aggression'] == 'passive'
        
        # Low volatility conditions
        low_vol_conditions = {
            'volatility': 0.003,   # Low
            'spread': 0.00001,     # Tight
            'liquidity': 'high'
        }
        
        low_vol_strategy = algo_executor.select_adaptive_strategy(
            order,
            low_vol_conditions
        )
        
        # Can be more aggressive in good conditions
        assert low_vol_strategy['aggression'] == 'aggressive'
        assert low_vol_strategy['slices'] < high_vol_strategy['slices']
    
    def test_implementation_shortfall(self, algo_executor):
        """
        Test 11.2.5: Minimize implementation shortfall
        Acceptance: Balance market impact vs opportunity cost
        """
        order = {
            'symbol': 'EUR_USD',
            'side': 'BUY',
            'quantity': 2000000,
            'benchmark_price': 1.10500
        }
        
        market_params = {
            'volatility': 0.005,
            'avg_volume': 10000000,
            'spread': 0.00002
        }
        
        strategy = algo_executor.minimize_implementation_shortfall(
            order,
            market_params
        )
        
        # Should balance urgency with market impact
        assert 'participation_rate' in strategy
        assert 0.05 <= strategy['participation_rate'] <= 0.30  # 5-30% of market volume
        
        # Estimate costs
        costs = algo_executor.estimate_execution_costs(order, strategy)
        assert 'market_impact' in costs
        assert 'opportunity_cost' in costs
        assert 'spread_cost' in costs
        
        # Total cost should be reasonable
        total_cost_bps = costs['total_bps']
        assert total_cost_bps < 10  # Less than 10 basis points


class TestExecutionMonitoring:
    """Test suite for execution monitoring"""
    
    @pytest.fixture
    def execution_monitor(self):
        """Initialize execution monitor"""
        from src.trading.execution.execution_monitor import ExecutionMonitor
        
        monitor = ExecutionMonitor()
        return monitor
    
    def test_real_time_monitoring(self, execution_monitor):
        """
        Test 11.3.1: Real-time execution monitoring
        Acceptance: Track execution progress
        """
        order = {
            'order_id': 'ORD123',
            'symbol': 'EUR_USD',
            'quantity': 1000000,
            'algorithm': 'TWAP',
            'slices': 10
        }
        
        execution_monitor.start_monitoring(order)
        
        # Simulate slice executions
        for i in range(5):
            execution_monitor.record_slice_execution(
                order['order_id'],
                slice_num=i+1,
                quantity=100000,
                price=1.10500 + i*0.00001,
                timestamp=datetime.now()
            )
        
        progress = execution_monitor.get_execution_progress(order['order_id'])
        
        assert progress['executed_quantity'] == 500000
        assert progress['remaining_quantity'] == 500000
        assert progress['completion_percentage'] == 50.0
        assert progress['slices_completed'] == 5
        assert progress['slices_remaining'] == 5
    
    def test_execution_analytics(self, execution_monitor):
        """
        Test 11.3.2: Post-execution analytics
        Acceptance: Calculate execution quality metrics
        """
        execution_data = {
            'order_id': 'ORD124',
            'symbol': 'EUR_USD',
            'side': 'BUY',
            'quantity': 500000,
            'benchmark_price': 1.10500,
            'fills': [
                {'quantity': 100000, 'price': 1.10502, 'time': datetime.now()},
                {'quantity': 200000, 'price': 1.10505, 'time': datetime.now()},
                {'quantity': 200000, 'price': 1.10508, 'time': datetime.now()}
            ]
        }
        
        analytics = execution_monitor.calculate_execution_analytics(execution_data)
        
        # Average execution price
        avg_price = (100000*1.10502 + 200000*1.10505 + 200000*1.10508) / 500000
        assert abs(analytics['average_price'] - avg_price) < 0.00001
        
        # Slippage from benchmark
        slippage = avg_price - 1.10500
        assert abs(analytics['slippage'] - slippage) < 0.00001
        assert analytics['slippage_bps'] == round(slippage / 1.10500 * 10000, 2)
        
        # Implementation shortfall
        assert analytics['implementation_shortfall'] > 0
    
    def test_execution_alerts(self, execution_monitor):
        """
        Test 11.3.3: Generate execution alerts
        Acceptance: Alert on anomalies
        """
        # Normal execution
        normal_execution = {
            'order_id': 'ORD125',
            'slippage_bps': 2,
            'execution_time_ms': 45,
            'fill_rate': 1.0
        }
        
        alerts = execution_monitor.check_execution_alerts(normal_execution)
        assert len(alerts) == 0
        
        # High slippage
        high_slippage = {
            'order_id': 'ORD126',
            'slippage_bps': 15,
            'execution_time_ms': 45,
            'fill_rate': 1.0
        }
        
        alerts = execution_monitor.check_execution_alerts(high_slippage)
        assert len(alerts) > 0
        assert any('slippage' in alert['message'].lower() for alert in alerts)
        
        # Slow execution
        slow_execution = {
            'order_id': 'ORD127',
            'slippage_bps': 2,
            'execution_time_ms': 600,
            'fill_rate': 1.0
        }
        
        alerts = execution_monitor.check_execution_alerts(slow_execution)
        assert any('execution time' in alert['message'].lower() for alert in alerts)
    
    def test_execution_reporting(self, execution_monitor):
        """
        Test 11.3.4: Generate execution reports
        Acceptance: Detailed execution summaries
        """
        executions = [
            {
                'order_id': f'ORD{i}',
                'symbol': 'EUR_USD',
                'quantity': 100000 * (i+1),
                'avg_price': 1.10500 + i*0.00001,
                'slippage_bps': i,
                'execution_time_ms': 40 + i*10,
                'algorithm': 'TWAP' if i % 2 == 0 else 'MARKET'
            }
            for i in range(10)
        ]
        
        report = execution_monitor.generate_execution_report(
            executions,
            period='daily'
        )
        
        assert report['total_orders'] == 10
        assert report['total_volume'] == sum(e['quantity'] for e in executions)
        assert 'average_slippage_bps' in report
        assert 'average_execution_time_ms' in report
        
        # Algorithm breakdown
        assert 'algorithm_breakdown' in report
        assert report['algorithm_breakdown']['TWAP']['count'] == 5
        assert report['algorithm_breakdown']['MARKET']['count'] == 5
        
        # Performance metrics
        assert 'best_execution' in report
        assert 'worst_execution' in report


class TestPreTradeAnalysis:
    """Test suite for pre-trade analysis"""
    
    @pytest.fixture
    def pre_trade_analyzer(self):
        """Initialize pre-trade analyzer"""
        from src.trading.execution.pre_trade_analysis import PreTradeAnalyzer
        
        analyzer = PreTradeAnalyzer()
        return analyzer
    
    def test_market_impact_estimation(self, pre_trade_analyzer):
        """
        Test 11.4.1: Estimate market impact
        Acceptance: Predict price movement from trade
        """
        trade = {
            'symbol': 'EUR_USD',
            'side': 'BUY',
            'quantity': 5000000  # Large order
        }
        
        market_data = {
            'avg_daily_volume': 100000000,
            'volatility': 0.005,
            'spread': 0.00002,
            'depth': 10000000  # Available at best price
        }
        
        impact = pre_trade_analyzer.estimate_market_impact(trade, market_data)
        
        # Temporary impact (immediate)
        assert impact['temporary_impact_bps'] > 0
        assert impact['temporary_impact_bps'] < 20  # Reasonable range
        
        # Permanent impact (information)
        assert impact['permanent_impact_bps'] > 0
        assert impact['permanent_impact_bps'] < impact['temporary_impact_bps']
        
        # Total expected cost
        assert impact['total_cost_bps'] == (
            impact['temporary_impact_bps'] + 
            impact['permanent_impact_bps'] + 
            impact['spread_cost_bps']
        )
    
    def test_optimal_execution_strategy(self, pre_trade_analyzer):
        """
        Test 11.4.2: Recommend optimal execution strategy
        Acceptance: Select best algorithm for conditions
        """
        # Small urgent order
        small_urgent = {
            'symbol': 'EUR_USD',
            'quantity': 50000,
            'urgency': 'high'
        }
        
        strategy = pre_trade_analyzer.recommend_strategy(small_urgent)
        assert strategy['algorithm'] == 'MARKET'
        
        # Large patient order
        large_patient = {
            'symbol': 'EUR_USD',
            'quantity': 5000000,
            'urgency': 'low'
        }
        
        strategy = pre_trade_analyzer.recommend_strategy(large_patient)
        assert strategy['algorithm'] in ['TWAP', 'VWAP', 'ICEBERG']
        
        # Medium order with price limit
        limit_order = {
            'symbol': 'EUR_USD',
            'quantity': 500000,
            'urgency': 'medium',
            'limit_price': 1.10500
        }
        
        strategy = pre_trade_analyzer.recommend_strategy(limit_order)
        assert strategy['algorithm'] == 'LIMIT_ALGO'
        assert strategy['passive_ratio'] > 0.5  # More passive execution
    
    def test_execution_timing_analysis(self, pre_trade_analyzer):
        """
        Test 11.4.3: Analyze optimal execution timing
        Acceptance: Identify best time to trade
        """
        trade = {
            'symbol': 'EUR_USD',
            'quantity': 1000000
        }
        
        current_time = datetime(2025, 1, 29, 14, 30)  # 2:30 PM
        
        timing_analysis = pre_trade_analyzer.analyze_execution_timing(
            trade,
            current_time
        )
        
        # Should consider market sessions
        assert 'current_session' in timing_analysis
        assert timing_analysis['current_session'] in ['london', 'newyork', 'overlap']
        
        # Liquidity assessment
        assert 'liquidity_score' in timing_analysis
        assert 0 <= timing_analysis['liquidity_score'] <= 1
        
        # Recommendation
        assert 'recommendation' in timing_analysis
        if timing_analysis['liquidity_score'] > 0.7:
            assert timing_analysis['recommendation'] == 'execute_now'
        else:
            assert timing_analysis['recommendation'] in ['wait', 'split_execution']


if __name__ == "__main__":
    pytest.main([__file__, '-v'])