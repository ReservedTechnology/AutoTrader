"""
Integration Test for Multi-Asset Position Sizing
Following TDD methodology for forex bot targeting 25% annual returns
Tests portfolio-wide position sizing with correlations and risk limits
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Tuple


class TestMultiAssetPositionSizing:
    """Integration test for multi-asset position sizing and risk management"""
    
    @pytest.fixture
    def position_manager(self):
        """Initialize multi-asset position manager"""
        from src.portfolio.multi_asset_position_manager import MultiAssetPositionManager
        
        manager = MultiAssetPositionManager(
            account_equity=100000,
            max_portfolio_heat=0.05,  # 5% max risk
            max_positions=5,
            correlation_threshold=0.7
        )
        return manager
    
    @pytest.fixture
    def correlation_matrix(self):
        """Currency pair correlation matrix"""
        pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD']
        
        # Realistic correlation matrix
        corr_data = np.array([
            [1.00, 0.75, -0.30, 0.65, -0.40],  # EUR_USD
            [0.75, 1.00, -0.25, 0.60, -0.35],  # GBP_USD
            [-0.30, -0.25, 1.00, -0.20, 0.50],  # USD_JPY
            [0.65, 0.60, -0.20, 1.00, -0.45],  # AUD_USD
            [-0.40, -0.35, 0.50, -0.45, 1.00]   # USD_CAD
        ])
        
        return pd.DataFrame(corr_data, index=pairs, columns=pairs)
    
    @pytest.fixture
    def market_conditions(self):
        """Current market conditions for each pair"""
        return {
            'EUR_USD': {'volatility': 0.0055, 'spread': 0.00002, 'liquidity': 'high'},
            'GBP_USD': {'volatility': 0.0075, 'spread': 0.00003, 'liquidity': 'high'},
            'USD_JPY': {'volatility': 0.0065, 'spread': 0.003, 'liquidity': 'high'},
            'AUD_USD': {'volatility': 0.0060, 'spread': 0.00003, 'liquidity': 'medium'},
            'USD_CAD': {'volatility': 0.0050, 'spread': 0.00003, 'liquidity': 'medium'}
        }
    
    @pytest.mark.integration
    def test_correlated_position_sizing(self, position_manager, correlation_matrix):
        """
        Test IT.4.1: Size positions considering correlations
        Acceptance: Reduce size for highly correlated pairs
        """
        # Existing positions
        existing_positions = [
            {
                'pair': 'EUR_USD',
                'size': 50000,
                'direction': 'LONG',
                'risk_amount': 1000  # 1% risk
            }
        ]
        
        # New position request (GBP_USD - highly correlated with EUR_USD)
        new_position = {
            'pair': 'GBP_USD',
            'direction': 'LONG',
            'base_size': 50000,
            'stop_loss_pips': 50
        }
        
        # Calculate adjusted size
        adjusted_size = position_manager.calculate_position_size(
            new_position,
            existing_positions,
            correlation_matrix
        )
        
        # Should reduce size due to 0.75 correlation
        assert adjusted_size < new_position['base_size']
        
        # Expected reduction factor
        correlation = correlation_matrix.loc['EUR_USD', 'GBP_USD']
        max_reduction = 0.5  # 50% reduction for perfect correlation
        expected_reduction = correlation * max_reduction
        expected_size = new_position['base_size'] * (1 - expected_reduction)
        
        assert abs(adjusted_size - expected_size) < 1000
        
        # Test with negatively correlated pair (hedge)
        hedge_position = {
            'pair': 'USD_JPY',
            'direction': 'LONG',
            'base_size': 50000,
            'stop_loss_pips': 50
        }
        
        hedge_size = position_manager.calculate_position_size(
            hedge_position,
            existing_positions,
            correlation_matrix
        )
        
        # Should allow full or increased size for hedging
        assert hedge_size >= hedge_position['base_size'] * 0.9
    
    @pytest.mark.integration
    def test_portfolio_heat_management(self, position_manager):
        """
        Test IT.4.2: Manage total portfolio heat
        Acceptance: Never exceed 5% total risk
        """
        positions = []
        
        # Add positions until heat limit
        pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD']
        
        for pair in pairs:
            position = {
                'pair': pair,
                'size': 30000,
                'stop_loss_pips': 50,
                'pip_value': 0.0001 if 'JPY' not in pair else 0.01
            }
            
            # Calculate risk
            risk = position_manager.calculate_position_risk(position)
            
            # Check if can add position
            current_heat = position_manager.calculate_portfolio_heat(positions)
            
            if current_heat + risk['risk_percentage'] <= 0.05:
                positions.append({
                    **position,
                    'risk_amount': risk['risk_amount'],
                    'risk_percentage': risk['risk_percentage']
                })
            else:
                # Should reject position that exceeds heat
                assert current_heat + risk['risk_percentage'] > 0.05
                break
        
        # Final portfolio heat should be at or below limit
        final_heat = position_manager.calculate_portfolio_heat(positions)
        assert final_heat <= 0.05
        assert final_heat > 0  # Should have some positions
    
    @pytest.mark.integration
    def test_dynamic_position_sizing(self, position_manager, market_conditions):
        """
        Test IT.4.3: Adjust position size based on market conditions
        Acceptance: Smaller positions in high volatility
        """
        base_position = {
            'pair': 'EUR_USD',
            'base_size': 50000,
            'stop_loss_pips': 50
        }
        
        # Normal volatility
        normal_size = position_manager.calculate_volatility_adjusted_size(
            base_position,
            market_conditions['EUR_USD']
        )
        
        # High volatility scenario
        high_vol_conditions = market_conditions['EUR_USD'].copy()
        high_vol_conditions['volatility'] = 0.015  # Much higher
        
        high_vol_size = position_manager.calculate_volatility_adjusted_size(
            base_position,
            high_vol_conditions
        )
        
        # Should reduce size in high volatility
        assert high_vol_size < normal_size
        
        # Expected adjustment based on volatility ratio
        vol_ratio = market_conditions['EUR_USD']['volatility'] / high_vol_conditions['volatility']
        expected_size = base_position['base_size'] * vol_ratio
        
        assert abs(high_vol_size - expected_size) < 5000
    
    @pytest.mark.integration
    def test_currency_exposure_limits(self, position_manager):
        """
        Test IT.4.4: Enforce currency exposure limits
        Acceptance: Max 40% exposure to single currency
        """
        positions = [
            {'pair': 'EUR_USD', 'size': 30000, 'direction': 'LONG'},  # Long EUR
            {'pair': 'EUR_GBP', 'size': 25000, 'direction': 'LONG'},  # Long EUR
            {'pair': 'EUR_JPY', 'size': 20000, 'direction': 'LONG'}   # Long EUR
        ]
        
        # Calculate EUR exposure
        eur_exposure = position_manager.calculate_currency_exposure(positions, 'EUR')
        
        total_exposure = sum(p['size'] for p in positions)
        eur_percentage = eur_exposure / position_manager.account_equity
        
        # Check if new EUR position would exceed limit
        new_position = {'pair': 'EUR_AUD', 'size': 30000, 'direction': 'LONG'}
        
        can_add = position_manager.check_currency_limit(
            new_position,
            positions,
            max_exposure=0.4  # 40% limit
        )
        
        if eur_percentage + (new_position['size'] / position_manager.account_equity) > 0.4:
            assert can_add is False
        else:
            assert can_add is True
    
    @pytest.mark.integration
    def test_optimal_portfolio_allocation(self, position_manager, correlation_matrix):
        """
        Test IT.4.5: Calculate optimal portfolio allocation
        Acceptance: Maximize Sharpe ratio with constraints
        """
        # Expected returns and risks for each pair
        pair_metrics = {
            'EUR_USD': {'expected_return': 0.12, 'volatility': 0.15},
            'GBP_USD': {'expected_return': 0.10, 'volatility': 0.18},
            'USD_JPY': {'expected_return': 0.08, 'volatility': 0.12},
            'AUD_USD': {'expected_return': 0.11, 'volatility': 0.16},
            'USD_CAD': {'expected_return': 0.09, 'volatility': 0.14}
        }
        
        # Calculate optimal weights
        optimal_weights = position_manager.optimize_portfolio(
            pair_metrics,
            correlation_matrix,
            target_return=0.10,
            max_risk=0.15
        )
        
        # Verify constraints
        assert abs(sum(optimal_weights.values()) - 1.0) < 0.001  # Weights sum to 1
        assert all(0 <= w <= 0.4 for w in optimal_weights.values())  # Max 40% per pair
        
        # Calculate portfolio metrics
        portfolio_return = sum(
            optimal_weights[pair] * pair_metrics[pair]['expected_return']
            for pair in optimal_weights
        )
        
        assert portfolio_return >= 0.09  # Close to target
        
        # Verify diversification
        assert len([w for w in optimal_weights.values() if w > 0.05]) >= 3  # At least 3 pairs
    
    @pytest.mark.integration
    def test_position_rebalancing(self, position_manager):
        """
        Test IT.4.6: Rebalance positions based on performance
        Acceptance: Adjust sizes while maintaining risk limits
        """
        # Current positions with P&L
        current_positions = [
            {'pair': 'EUR_USD', 'size': 50000, 'pnl': 500, 'pnl_percent': 0.01},
            {'pair': 'GBP_USD', 'size': 30000, 'pnl': -200, 'pnl_percent': -0.0067},
            {'pair': 'USD_JPY', 'size': 40000, 'pnl': 300, 'pnl_percent': 0.0075}
        ]
        
        # Target allocations
        target_weights = {
            'EUR_USD': 0.35,
            'GBP_USD': 0.30,
            'USD_JPY': 0.35
        }
        
        # Calculate rebalancing trades
        rebalancing = position_manager.calculate_rebalancing(
            current_positions,
            target_weights,
            min_trade_size=5000  # Minimum trade to avoid excessive trading
        )
        
        assert 'trades' in rebalancing
        assert 'total_turnover' in rebalancing
        
        # Verify rebalancing improves allocation
        for trade in rebalancing['trades']:
            assert abs(trade['size']) >= 5000  # Respects minimum
            assert trade['action'] in ['increase', 'decrease']
        
        # Check turnover is reasonable
        assert rebalancing['total_turnover'] < 0.3  # Less than 30% portfolio turnover
    
    @pytest.mark.integration
    def test_risk_parity_allocation(self, position_manager, correlation_matrix):
        """
        Test IT.4.7: Risk parity position sizing
        Acceptance: Equal risk contribution from each position
        """
        pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD']
        volatilities = {
            'EUR_USD': 0.0055,
            'GBP_USD': 0.0075,
            'USD_JPY': 0.0065,
            'AUD_USD': 0.0060,
            'USD_CAD': 0.0050
        }
        
        # Calculate risk parity weights
        rp_weights = position_manager.calculate_risk_parity(
            volatilities,
            correlation_matrix
        )
        
        # Calculate risk contributions
        risk_contributions = position_manager.calculate_risk_contributions(
            rp_weights,
            volatilities,
            correlation_matrix
        )
        
        # All positions should contribute equally to risk
        contributions = list(risk_contributions.values())
        mean_contribution = np.mean(contributions)
        
        # Check equal risk contribution (within 10% tolerance)
        for contrib in contributions:
            assert abs(contrib - mean_contribution) / mean_contribution < 0.10
        
        # Higher volatility pairs should have lower weights
        assert rp_weights['USD_CAD'] > rp_weights['GBP_USD']
    
    @pytest.mark.integration
    def test_drawdown_position_adjustment(self, position_manager):
        """
        Test IT.4.8: Adjust position sizes during drawdown
        Acceptance: Reduce risk during losing streaks
        """
        # Track performance
        performance_history = [
            {'date': datetime.now() - timedelta(days=i), 'equity': equity}
            for i, equity in enumerate([
                100000, 99500, 98800, 98000, 97200, 96500  # Drawdown
            ])
        ]
        
        # Calculate drawdown
        current_equity = performance_history[-1]['equity']
        peak_equity = max(p['equity'] for p in performance_history)
        drawdown = (peak_equity - current_equity) / peak_equity
        
        assert drawdown > 0.03  # In drawdown
        
        # Adjust position sizing based on drawdown
        base_size = 50000
        adjusted_size = position_manager.adjust_for_drawdown(
            base_size,
            drawdown,
            max_reduction=0.5  # Max 50% reduction
        )
        
        # Should reduce size during drawdown
        assert adjusted_size < base_size
        
        # Linear reduction based on drawdown magnitude
        if drawdown >= 0.10:  # 10% drawdown
            assert adjusted_size <= base_size * 0.5  # Max reduction
        elif drawdown >= 0.05:  # 5% drawdown
            assert adjusted_size <= base_size * 0.75
        else:  # Small drawdown
            assert adjusted_size >= base_size * 0.85
    
    @pytest.mark.integration
    def test_multi_strategy_position_sizing(self, position_manager):
        """
        Test IT.4.9: Size positions across multiple strategies
        Acceptance: Allocate capital to different strategies
        """
        strategies = {
            'trend_following': {
                'allocation': 0.40,
                'current_positions': 2,
                'max_positions': 3,
                'performance': {'sharpe': 1.2, 'win_rate': 0.55}
            },
            'mean_reversion': {
                'allocation': 0.30,
                'current_positions': 1,
                'max_positions': 2,
                'performance': {'sharpe': 1.5, 'win_rate': 0.65}
            },
            'breakout': {
                'allocation': 0.30,
                'current_positions': 1,
                'max_positions': 2,
                'performance': {'sharpe': 1.0, 'win_rate': 0.50}
            }
        }
        
        # New signal from trend following strategy
        new_signal = {
            'strategy': 'trend_following',
            'pair': 'EUR_USD',
            'confidence': 0.75,
            'expected_return': 0.02
        }
        
        # Calculate position size considering strategy allocation
        position_size = position_manager.calculate_strategy_position_size(
            new_signal,
            strategies,
            total_capital=100000
        )
        
        # Should respect strategy allocation
        strategy_capital = 100000 * strategies['trend_following']['allocation']
        max_position = strategy_capital / strategies['trend_following']['max_positions']
        
        assert position_size <= max_position
        
        # Adjust based on confidence and performance
        if new_signal['confidence'] > 0.7:
            assert position_size >= max_position * 0.7
        
        # Check if can add position to strategy
        can_add = position_manager.can_add_to_strategy(
            'trend_following',
            strategies
        )
        
        assert can_add is True  # Has room for one more position


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-m', 'integration'])