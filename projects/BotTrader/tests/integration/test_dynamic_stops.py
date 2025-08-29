"""
Integration Test for Dynamic Stop Loss Management
Following TDD methodology for forex bot targeting 25% annual returns
Tests ATR-based stops, trailing stops, and breakeven management
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional


class TestDynamicStops:
    """Integration test for dynamic stop loss management"""
    
    @pytest.fixture
    def stop_manager(self):
        """Initialize dynamic stop manager"""
        from src.risk.dynamic_stop_manager import DynamicStopManager
        
        manager = DynamicStopManager(
            atr_multiplier=2.0,
            trailing_distance_atr=1.5,
            breakeven_trigger_atr=1.0,
            max_stop_distance=0.005  # 50 pips max
        )
        return manager
    
    @pytest.fixture
    def market_data(self):
        """Generate market data with ATR"""
        periods = 100
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='5min')
        
        # Create price data with volatility
        prices = 1.10500 + np.cumsum(np.random.normal(0, 0.0001, periods))
        
        df = pd.DataFrame({
            'timestamp': dates,
            'high': prices + np.abs(np.random.normal(0, 0.0002, periods)),
            'low': prices - np.abs(np.random.normal(0, 0.0002, periods)),
            'close': prices,
            'volume': np.random.randint(10000, 100000, periods)
        })
        
        # Calculate ATR
        df['tr'] = df[['high', 'low', 'close']].apply(
            lambda x: max(x['high'] - x['low'], 
                         abs(x['high'] - x['close']), 
                         abs(x['low'] - x['close'])), axis=1
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        return df
    
    @pytest.mark.integration
    def test_atr_based_stop_calculation(self, stop_manager, market_data):
        """
        Test IT.5.1: Calculate ATR-based stop loss
        Acceptance: Dynamic stops based on volatility
        """
        current_price = market_data['close'].iloc[-1]
        current_atr = market_data['atr'].iloc[-1]
        
        # Long position stop
        long_stop = stop_manager.calculate_atr_stop(
            entry_price=current_price,
            position_type='LONG',
            atr=current_atr,
            multiplier=2.0
        )
        
        # Stop should be below entry
        assert long_stop < current_price
        
        # Distance should be ATR * multiplier
        expected_distance = current_atr * 2.0
        actual_distance = current_price - long_stop
        assert abs(actual_distance - expected_distance) < 0.00001
        
        # Short position stop
        short_stop = stop_manager.calculate_atr_stop(
            entry_price=current_price,
            position_type='SHORT',
            atr=current_atr,
            multiplier=2.0
        )
        
        # Stop should be above entry
        assert short_stop > current_price
        assert abs(short_stop - current_price - expected_distance) < 0.00001
        
        # Respect maximum stop distance
        large_atr = 0.010  # Very large ATR
        capped_stop = stop_manager.calculate_atr_stop(
            entry_price=current_price,
            position_type='LONG',
            atr=large_atr,
            multiplier=2.0
        )
        
        max_distance = stop_manager.max_stop_distance
        assert current_price - capped_stop <= max_distance
    
    @pytest.mark.integration
    def test_trailing_stop_management(self, stop_manager, market_data):
        """
        Test IT.5.2: Manage trailing stops
        Acceptance: Trail profits while protecting gains
        """
        # Initialize position
        position = {
            'entry_price': 1.10500,
            'current_stop': 1.10400,
            'highest_price': 1.10500,
            'position_type': 'LONG',
            'trailing_activated': False
        }
        
        # Simulate price movement
        price_sequence = [
            1.10520, 1.10540, 1.10560, 1.10550, 1.10580,  # Upward
            1.10570, 1.10590, 1.10585, 1.10600, 1.10595   # Consolidation
        ]
        
        current_atr = 0.00055
        
        for price in price_sequence:
            # Update trailing stop
            updated = stop_manager.update_trailing_stop(
                position,
                current_price=price,
                atr=current_atr
            )
            
            # Stop should only move up (for long position)
            assert updated['stop_loss'] >= position['current_stop']
            
            # Update position
            position['current_stop'] = updated['stop_loss']
            position['highest_price'] = max(position['highest_price'], price)
            position['trailing_activated'] = updated['trailing_activated']
        
        # Trailing should be activated
        assert position['trailing_activated'] is True
        
        # Stop should have moved up
        assert position['current_stop'] > 1.10400
        
        # Stop should maintain minimum distance
        min_distance = current_atr * stop_manager.trailing_distance_atr
        assert position['highest_price'] - position['current_stop'] >= min_distance * 0.9
    
    @pytest.mark.integration
    def test_breakeven_stop_management(self, stop_manager):
        """
        Test IT.5.3: Move stop to breakeven
        Acceptance: Protect capital after minimum profit
        """
        position = {
            'entry_price': 1.10500,
            'current_stop': 1.10400,
            'position_type': 'LONG',
            'breakeven_set': False,
            'commission': 0.00002  # 2 pip commission
        }
        
        current_atr = 0.00055
        
        # Price hasn't reached breakeven trigger
        low_price = 1.10530
        result = stop_manager.check_breakeven(
            position,
            current_price=low_price,
            atr=current_atr
        )
        
        assert result['move_to_breakeven'] is False
        
        # Price reaches breakeven trigger (1 ATR profit)
        trigger_price = position['entry_price'] + (current_atr * 1.0)
        result = stop_manager.check_breakeven(
            position,
            current_price=trigger_price,
            atr=current_atr
        )
        
        assert result['move_to_breakeven'] is True
        assert result['new_stop'] >= position['entry_price'] + position['commission']
        
        # Update position
        position['current_stop'] = result['new_stop']
        position['breakeven_set'] = True
        
        # Shouldn't move again once set
        result2 = stop_manager.check_breakeven(
            position,
            current_price=trigger_price + 0.001,
            atr=current_atr
        )
        
        assert result2['move_to_breakeven'] is False
    
    @pytest.mark.integration
    def test_volatility_adjusted_stops(self, stop_manager, market_data):
        """
        Test IT.5.4: Adjust stops based on volatility regime
        Acceptance: Wider stops in high volatility
        """
        # Calculate volatility percentile
        volatility_history = market_data['atr'].dropna()
        current_atr = volatility_history.iloc[-1]
        
        # Low volatility scenario
        low_vol_percentile = 20
        low_vol_stop = stop_manager.calculate_volatility_adjusted_stop(
            entry_price=1.10500,
            base_stop=1.10400,
            volatility_percentile=low_vol_percentile
        )
        
        # High volatility scenario  
        high_vol_percentile = 80
        high_vol_stop = stop_manager.calculate_volatility_adjusted_stop(
            entry_price=1.10500,
            base_stop=1.10400,
            volatility_percentile=high_vol_percentile
        )
        
        # High volatility should have wider stop
        assert abs(1.10500 - high_vol_stop) > abs(1.10500 - low_vol_stop)
        
        # Calculate adjustment factor
        low_factor = stop_manager.get_volatility_factor(low_vol_percentile)
        high_factor = stop_manager.get_volatility_factor(high_vol_percentile)
        
        assert low_factor < 1.0  # Tighter stops
        assert high_factor > 1.0  # Wider stops
    
    @pytest.mark.integration
    def test_time_based_stop_adjustment(self, stop_manager):
        """
        Test IT.5.5: Adjust stops based on holding time
        Acceptance: Tighten stops over time
        """
        position = {
            'entry_price': 1.10500,
            'entry_time': datetime.now() - timedelta(hours=2),
            'initial_stop': 1.10400,
            'current_stop': 1.10420,
            'position_type': 'LONG'
        }
        
        # Calculate time-based adjustment
        holding_hours = 2
        adjusted_stop = stop_manager.adjust_stop_by_time(
            position,
            current_time=datetime.now(),
            tightening_rate=0.1  # 10% per hour
        )
        
        # Stop should move closer to entry over time
        initial_distance = position['entry_price'] - position['initial_stop']
        current_distance = position['entry_price'] - adjusted_stop['new_stop']
        
        # Distance should decrease
        assert current_distance < initial_distance
        
        # Expected tightening
        expected_reduction = initial_distance * (holding_hours * 0.1)
        expected_stop = position['initial_stop'] + expected_reduction
        
        assert abs(adjusted_stop['new_stop'] - expected_stop) < 0.00005
    
    @pytest.mark.integration
    def test_correlated_stops_adjustment(self, stop_manager):
        """
        Test IT.5.6: Adjust stops for correlated positions
        Acceptance: Tighter stops when holding correlated pairs
        """
        positions = [
            {
                'pair': 'EUR_USD',
                'entry_price': 1.10500,
                'stop_loss': 1.10400,
                'position_type': 'LONG'
            },
            {
                'pair': 'GBP_USD',
                'entry_price': 1.25000,
                'stop_loss': 1.24850,
                'position_type': 'LONG'
            }
        ]
        
        correlation = 0.75  # High correlation
        
        # Adjust stops for correlation
        adjusted_stops = stop_manager.adjust_correlated_stops(
            positions,
            correlation,
            tightening_factor=0.2  # 20% tighter for perfect correlation
        )
        
        # Stops should be tighter
        for i, pos in enumerate(positions):
            original_distance = abs(pos['entry_price'] - pos['stop_loss'])
            new_distance = abs(pos['entry_price'] - adjusted_stops[i])
            
            # New distance should be smaller
            assert new_distance < original_distance
            
            # Expected adjustment
            expected_distance = original_distance * (1 - correlation * 0.2)
            assert abs(new_distance - expected_distance) < 0.00005
    
    @pytest.mark.integration
    def test_stop_loss_cascade_prevention(self, stop_manager):
        """
        Test IT.5.7: Prevent stop loss cascade
        Acceptance: Avoid triggering multiple stops simultaneously
        """
        positions = [
            {'pair': 'EUR_USD', 'stop': 1.10400, 'size': 50000},
            {'pair': 'GBP_USD', 'stop': 1.24900, 'size': 30000},
            {'pair': 'AUD_USD', 'stop': 0.74950, 'size': 40000}
        ]
        
        current_prices = {
            'EUR_USD': 1.10420,  # Close to stop
            'GBP_USD': 1.24920,  # Close to stop
            'AUD_USD': 0.74970   # Close to stop
        }
        
        # Check cascade risk
        cascade_risk = stop_manager.assess_cascade_risk(
            positions,
            current_prices,
            threshold_pips=5
        )
        
        assert cascade_risk['risk_level'] == 'high'
        assert cascade_risk['positions_at_risk'] >= 2
        
        # Suggest adjustments to prevent cascade
        adjustments = stop_manager.prevent_cascade(
            positions,
            current_prices,
            min_separation_pips=10
        )
        
        # Should stagger stops
        assert len(adjustments) > 0
        
        for adj in adjustments:
            assert 'pair' in adj
            assert 'new_stop' in adj
            assert 'adjustment_pips' in adj
            
            # New stops should be more separated
            assert adj['adjustment_pips'] >= 5
    
    @pytest.mark.integration
    def test_guaranteed_stop_loss(self, stop_manager):
        """
        Test IT.5.8: Manage guaranteed stop losses
        Acceptance: Handle guaranteed stops with premium
        """
        position = {
            'pair': 'EUR_USD',
            'entry_price': 1.10500,
            'size': 100000,
            'guaranteed_stop': True,
            'stop_premium_pips': 2  # 2 pip premium for guarantee
        }
        
        # Calculate guaranteed stop placement
        guaranteed_stop = stop_manager.calculate_guaranteed_stop(
            position,
            desired_stop=1.10400,
            min_distance_pips=10  # Broker requirement
        )
        
        # Should respect minimum distance
        actual_distance_pips = (position['entry_price'] - guaranteed_stop['stop_price']) * 10000
        assert actual_distance_pips >= 10
        
        # Calculate cost
        assert guaranteed_stop['premium_cost'] == position['size'] * position['stop_premium_pips'] * 0.0001
        
        # Decide if worth the premium
        worth_it = stop_manager.evaluate_guaranteed_stop(
            potential_loss_without=500,  # Potential slippage loss
            premium_cost=guaranteed_stop['premium_cost'],
            probability_of_gap=0.05  # 5% chance of gap
        )
        
        # Should use guaranteed stop if expected savings > premium
        expected_savings = 500 * 0.05  # Expected loss from gaps
        assert worth_it == (expected_savings > guaranteed_stop['premium_cost'])
    
    @pytest.mark.integration
    def test_dynamic_stop_monitoring(self, stop_manager):
        """
        Test IT.5.9: Real-time stop monitoring and alerts
        Acceptance: Alert when price approaches stops
        """
        positions = [
            {
                'pair': 'EUR_USD',
                'entry': 1.10500,
                'stop': 1.10400,
                'current_price': 1.10425,
                'position_type': 'LONG'
            }
        ]
        
        # Monitor stop proximity
        alerts = stop_manager.monitor_stop_proximity(
            positions,
            warning_distance_pips=5,
            critical_distance_pips=2
        )
        
        assert len(alerts) > 0
        
        alert = alerts[0]
        assert alert['pair'] == 'EUR_USD'
        assert alert['level'] in ['warning', 'critical']
        
        # 2.5 pips from stop should be critical
        distance_pips = (positions[0]['current_price'] - positions[0]['stop']) * 10000
        if distance_pips <= 2:
            assert alert['level'] == 'critical'
        elif distance_pips <= 5:
            assert alert['level'] == 'warning'
        
        # Suggest action
        assert 'suggested_action' in alert
        assert alert['suggested_action'] in ['close', 'hedge', 'monitor', 'widen_stop']


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-m', 'integration'])