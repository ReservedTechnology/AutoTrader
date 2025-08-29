"""
Test Suite for Portfolio Management
Following TDD methodology for forex bot targeting 25% annual returns
Tests for portfolio optimization, position management, and performance tracking
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import json


class TestPortfolioManager:
    """Test suite for portfolio management"""
    
    @pytest.fixture
    def portfolio_manager(self):
        """Initialize portfolio manager"""
        from src.portfolio.portfolio_manager import PortfolioManager
        
        manager = PortfolioManager(
            initial_capital=100000,
            max_positions=5,
            max_portfolio_heat=0.05
        )
        return manager
    
    @pytest.fixture
    def positions(self):
        """Sample portfolio positions"""
        return [
            {
                'position_id': 'POS001',
                'symbol': 'EUR_USD',
                'side': 'LONG',
                'quantity': 100000,
                'entry_price': 1.10500,
                'current_price': 1.10600,
                'stop_loss': 1.10400,
                'take_profit': 1.10700,
                'opened_at': datetime.now() - timedelta(hours=2),
                'unrealized_pnl': 100.00
            },
            {
                'position_id': 'POS002',
                'symbol': 'GBP_USD',
                'side': 'SHORT',
                'quantity': 50000,
                'entry_price': 1.25000,
                'current_price': 1.24950,
                'stop_loss': 1.25100,
                'take_profit': 1.24800,
                'opened_at': datetime.now() - timedelta(hours=1),
                'unrealized_pnl': 25.00
            }
        ]
    
    def test_portfolio_initialization(self, portfolio_manager):
        """
        Test 12.1.1: Initialize portfolio
        Acceptance: Track capital and positions
        """
        assert portfolio_manager.initial_capital == 100000
        assert portfolio_manager.current_equity == 100000
        assert portfolio_manager.max_positions == 5
        assert len(portfolio_manager.open_positions) == 0
        assert portfolio_manager.realized_pnl == 0
        assert portfolio_manager.unrealized_pnl == 0
    
    def test_add_position(self, portfolio_manager):
        """
        Test 12.1.2: Add new position to portfolio
        Acceptance: Update portfolio metrics
        """
        position = {
            'symbol': 'EUR_USD',
            'side': 'LONG',
            'quantity': 100000,
            'entry_price': 1.10500,
            'stop_loss': 1.10400,
            'take_profit': 1.10700
        }
        
        success = portfolio_manager.add_position(position)
        
        assert success is True
        assert len(portfolio_manager.open_positions) == 1
        assert portfolio_manager.open_positions[0]['symbol'] == 'EUR_USD'
        assert portfolio_manager.position_count == 1
        
        # Check position limits
        for _ in range(4):
            portfolio_manager.add_position(position.copy())
        
        # Should reject 6th position
        assert len(portfolio_manager.open_positions) == 5
        sixth_position = portfolio_manager.add_position(position.copy())
        assert sixth_position is False
    
    def test_update_position_prices(self, portfolio_manager, positions):
        """
        Test 12.1.3: Update position prices
        Acceptance: Calculate real-time P&L
        """
        # Add positions
        for pos in positions:
            portfolio_manager.open_positions.append(pos)
        
        # Update prices
        new_prices = {
            'EUR_USD': {'bid': 1.10650, 'ask': 1.10652},
            'GBP_USD': {'bid': 1.24900, 'ask': 1.24902}
        }
        
        portfolio_manager.update_prices(new_prices)
        
        # Check EUR_USD P&L (long position)
        eur_pnl = 100000 * (1.10650 - 1.10500)
        assert abs(portfolio_manager.open_positions[0]['unrealized_pnl'] - eur_pnl) < 1
        
        # Check GBP_USD P&L (short position)
        gbp_pnl = 50000 * (1.25000 - 1.24900)
        assert abs(portfolio_manager.open_positions[1]['unrealized_pnl'] - gbp_pnl) < 1
        
        # Total unrealized P&L
        total_unrealized = portfolio_manager.calculate_unrealized_pnl()
        assert abs(total_unrealized - (eur_pnl + gbp_pnl)) < 1
    
    def test_close_position(self, portfolio_manager, positions):
        """
        Test 12.1.4: Close position
        Acceptance: Update realized P&L
        """
        # Add position
        portfolio_manager.open_positions.append(positions[0])
        
        # Close with profit
        closed = portfolio_manager.close_position(
            position_id='POS001',
            exit_price=1.10650
        )
        
        assert closed is True
        assert len(portfolio_manager.open_positions) == 0
        
        # Calculate realized P&L
        realized_pnl = 100000 * (1.10650 - 1.10500)
        assert abs(portfolio_manager.realized_pnl - realized_pnl) < 1
        
        # Check trade history
        assert len(portfolio_manager.trade_history) == 1
        assert portfolio_manager.trade_history[0]['exit_price'] == 1.10650
        assert portfolio_manager.trade_history[0]['profit'] == realized_pnl
    
    def test_portfolio_metrics(self, portfolio_manager):
        """
        Test 12.1.5: Calculate portfolio metrics
        Acceptance: Track performance indicators
        """
        # Simulate trading history
        trades = [
            {'profit': 150, 'return': 0.0015},
            {'profit': -80, 'return': -0.0008},
            {'profit': 200, 'return': 0.0020},
            {'profit': -60, 'return': -0.0006},
            {'profit': 180, 'return': 0.0018}
        ]
        
        portfolio_manager.trade_history = trades
        portfolio_manager.realized_pnl = sum(t['profit'] for t in trades)
        
        metrics = portfolio_manager.calculate_metrics()
        
        # Win rate
        assert metrics['win_rate'] == 0.6  # 3 wins out of 5
        
        # Profit factor
        total_wins = 150 + 200 + 180
        total_losses = 80 + 60
        assert metrics['profit_factor'] == total_wins / total_losses
        
        # Average win/loss
        assert metrics['avg_win'] == total_wins / 3
        assert metrics['avg_loss'] == total_losses / 2
        
        # Risk/reward ratio
        assert metrics['risk_reward_ratio'] == metrics['avg_win'] / metrics['avg_loss']
        
        # Total return
        assert metrics['total_return'] == portfolio_manager.realized_pnl / 100000


class TestPositionOptimization:
    """Test suite for position optimization"""
    
    @pytest.fixture
    def position_optimizer(self):
        """Initialize position optimizer"""
        from src.portfolio.position_optimizer import PositionOptimizer
        
        optimizer = PositionOptimizer()
        return optimizer
    
    def test_optimal_position_weights(self, position_optimizer):
        """
        Test 12.2.1: Calculate optimal position weights
        Acceptance: Maximize Sharpe ratio
        """
        # Historical returns for different pairs
        returns = pd.DataFrame({
            'EUR_USD': [0.001, 0.002, -0.001, 0.003, 0.001],
            'GBP_USD': [0.002, -0.001, 0.002, 0.001, 0.002],
            'USD_JPY': [-0.001, 0.001, 0.001, -0.002, 0.001]
        })
        
        # Calculate optimal weights
        weights = position_optimizer.optimize_weights(
            returns,
            target_return=0.001,
            max_risk=0.002
        )
        
        assert len(weights) == 3
        assert abs(sum(weights.values()) - 1.0) < 0.001  # Weights sum to 1
        assert all(0 <= w <= 1 for w in weights.values())  # Valid weights
        
        # Verify risk constraint
        portfolio_risk = position_optimizer.calculate_portfolio_risk(returns, weights)
        assert portfolio_risk <= 0.002
    
    def test_risk_parity_allocation(self, position_optimizer):
        """
        Test 12.2.2: Risk parity position sizing
        Acceptance: Equal risk contribution
        """
        volatilities = {
            'EUR_USD': 0.005,
            'GBP_USD': 0.008,
            'USD_JPY': 0.006
        }
        
        correlations = pd.DataFrame({
            'EUR_USD': [1.0, 0.7, -0.2],
            'GBP_USD': [0.7, 1.0, -0.1],
            'USD_JPY': [-0.2, -0.1, 1.0]
        }, index=['EUR_USD', 'GBP_USD', 'USD_JPY'])
        
        weights = position_optimizer.risk_parity_weights(
            volatilities,
            correlations
        )
        
        # Calculate risk contributions
        risk_contributions = position_optimizer.calculate_risk_contributions(
            weights,
            volatilities,
            correlations
        )
        
        # Should be approximately equal
        contributions = list(risk_contributions.values())
        assert np.std(contributions) < 0.001  # Low variance in contributions
    
    def test_maximum_diversification(self, position_optimizer):
        """
        Test 12.2.3: Maximum diversification portfolio
        Acceptance: Minimize concentration risk
        """
        returns = pd.DataFrame(np.random.randn(100, 5) * 0.01)
        
        weights = position_optimizer.maximize_diversification(returns)
        
        # Calculate diversification ratio
        div_ratio = position_optimizer.calculate_diversification_ratio(
            returns,
            weights
        )
        
        assert div_ratio > 1.0  # Should achieve some diversification
        
        # Compare to equal weights
        equal_weights = {i: 0.2 for i in range(5)}
        equal_div_ratio = position_optimizer.calculate_diversification_ratio(
            returns,
            equal_weights
        )
        
        # Optimized should be better than equal weights
        assert div_ratio >= equal_div_ratio
    
    def test_conditional_rebalancing(self, position_optimizer):
        """
        Test 12.2.4: Conditional portfolio rebalancing
        Acceptance: Rebalance when thresholds exceeded
        """
        current_weights = {
            'EUR_USD': 0.35,
            'GBP_USD': 0.40,
            'USD_JPY': 0.25
        }
        
        target_weights = {
            'EUR_USD': 0.33,
            'GBP_USD': 0.33,
            'USD_JPY': 0.34
        }
        
        # Check if rebalancing needed
        should_rebalance = position_optimizer.should_rebalance(
            current_weights,
            target_weights,
            threshold=0.05  # 5% deviation threshold
        )
        
        # GBP_USD deviation is 7%, should trigger rebalance
        assert should_rebalance is True
        
        # Calculate rebalancing trades
        trades = position_optimizer.calculate_rebalancing_trades(
            current_weights,
            target_weights,
            portfolio_value=100000
        )
        
        assert trades['EUR_USD'] < 0  # Sell EUR_USD
        assert trades['GBP_USD'] < 0  # Sell GBP_USD
        assert trades['USD_JPY'] > 0  # Buy USD_JPY


class TestPerformanceTracking:
    """Test suite for performance tracking"""
    
    @pytest.fixture
    def performance_tracker(self):
        """Initialize performance tracker"""
        from src.portfolio.performance_tracker import PerformanceTracker
        
        tracker = PerformanceTracker(
            benchmark='EUR_USD',
            reporting_currency='USD'
        )
        return tracker
    
    def test_daily_performance_calculation(self, performance_tracker):
        """
        Test 12.3.1: Calculate daily performance
        Acceptance: Track daily returns and metrics
        """
        # Simulate daily equity curve
        equity_curve = pd.Series([
            100000, 100500, 99800, 101000, 101500, 100800
        ], index=pd.date_range(start='2025-01-24', periods=6, freq='D'))
        
        daily_stats = performance_tracker.calculate_daily_stats(equity_curve)
        
        # Daily returns
        assert len(daily_stats['returns']) == 5
        assert abs(daily_stats['returns'][0] - 0.005) < 0.0001  # 0.5% return
        
        # Average daily return
        assert 'avg_return' in daily_stats
        assert 'volatility' in daily_stats
        assert 'sharpe_daily' in daily_stats
    
    def test_drawdown_tracking(self, performance_tracker):
        """
        Test 12.3.2: Track drawdowns
        Acceptance: Monitor peak-to-trough declines
        """
        equity_curve = pd.Series([
            100000, 102000, 105000, 103000, 98000,  # Drawdown
            99000, 101000, 106000, 108000          # Recovery to new high
        ])
        
        dd_analysis = performance_tracker.analyze_drawdowns(equity_curve)
        
        # Maximum drawdown
        assert abs(dd_analysis['max_drawdown'] - (-0.0667)) < 0.001  # -6.67%
        
        # Current drawdown (should be 0 at new high)
        assert dd_analysis['current_drawdown'] == 0
        
        # Drawdown duration
        assert dd_analysis['max_dd_duration'] == 4  # From peak to recovery
        
        # Number of drawdowns
        assert dd_analysis['drawdown_count'] >= 1
    
    def test_rolling_performance_windows(self, performance_tracker):
        """
        Test 12.3.3: Calculate rolling performance
        Acceptance: Track performance over time windows
        """
        # Generate sample returns
        dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
        returns = pd.Series(np.random.normal(0.001, 0.01, 252), index=dates)
        
        rolling_stats = performance_tracker.calculate_rolling_stats(
            returns,
            windows=[30, 60, 90]
        )
        
        # 30-day rolling
        assert len(rolling_stats['30d']['returns']) > 200
        assert 'sharpe' in rolling_stats['30d']
        assert 'volatility' in rolling_stats['30d']
        
        # Check consistency
        assert rolling_stats['30d']['volatility'].mean() < rolling_stats['90d']['volatility'].mean()
    
    def test_benchmark_comparison(self, performance_tracker):
        """
        Test 12.3.4: Compare to benchmark
        Acceptance: Track alpha and beta
        """
        # Portfolio returns
        portfolio_returns = pd.Series(np.random.normal(0.0015, 0.01, 100))
        
        # Benchmark returns (correlated but different)
        benchmark_returns = portfolio_returns * 0.8 + np.random.normal(0.0005, 0.005, 100)
        
        comparison = performance_tracker.compare_to_benchmark(
            portfolio_returns,
            benchmark_returns
        )
        
        # Alpha (excess return)
        assert 'alpha' in comparison
        
        # Beta (correlation to benchmark)
        assert 'beta' in comparison
        assert 0 <= comparison['beta'] <= 2  # Reasonable beta range
        
        # Information ratio
        assert 'information_ratio' in comparison
        
        # Tracking error
        assert 'tracking_error' in comparison
        assert comparison['tracking_error'] > 0
    
    def test_performance_attribution(self, performance_tracker):
        """
        Test 12.3.5: Performance attribution analysis
        Acceptance: Identify profit sources
        """
        trades = pd.DataFrame({
            'symbol': ['EUR_USD', 'GBP_USD', 'EUR_USD', 'USD_JPY', 'GBP_USD'],
            'profit': [100, -50, 150, 75, -25],
            'strategy': ['trend', 'mean_reversion', 'trend', 'breakout', 'mean_reversion'],
            'holding_time': [120, 45, 180, 60, 30]  # minutes
        })
        
        attribution = performance_tracker.analyze_attribution(trades)
        
        # By symbol
        assert attribution['by_symbol']['EUR_USD']['total_profit'] == 250
        assert attribution['by_symbol']['EUR_USD']['trade_count'] == 2
        assert attribution['by_symbol']['GBP_USD']['total_profit'] == -75
        
        # By strategy
        assert attribution['by_strategy']['trend']['total_profit'] == 250
        assert attribution['by_strategy']['mean_reversion']['total_profit'] == -75
        
        # By holding time
        assert 'short_term' in attribution['by_holding_time']  # < 60 min
        assert 'medium_term' in attribution['by_holding_time']  # 60-120 min
        assert 'long_term' in attribution['by_holding_time']   # > 120 min


class TestRiskAdjustedReturns:
    """Test suite for risk-adjusted return calculations"""
    
    @pytest.fixture
    def risk_metrics(self):
        """Initialize risk metrics calculator"""
        from src.portfolio.risk_adjusted_metrics import RiskAdjustedMetrics
        
        metrics = RiskAdjustedMetrics()
        return metrics
    
    def test_sharpe_ratio_calculation(self, risk_metrics):
        """
        Test 12.4.1: Calculate Sharpe ratio
        Acceptance: Accurate risk-adjusted returns
        """
        returns = pd.Series(np.random.normal(0.001, 0.01, 252))
        risk_free_rate = 0.02  # Annual
        
        sharpe = risk_metrics.calculate_sharpe(
            returns,
            risk_free_rate,
            periods_per_year=252
        )
        
        # Manual calculation
        excess_return = returns.mean() * 252 - risk_free_rate
        volatility = returns.std() * np.sqrt(252)
        expected_sharpe = excess_return / volatility
        
        assert abs(sharpe - expected_sharpe) < 0.01
    
    def test_sortino_ratio_calculation(self, risk_metrics):
        """
        Test 12.4.2: Calculate Sortino ratio
        Acceptance: Focus on downside risk
        """
        returns = pd.Series(np.random.normal(0.001, 0.01, 252))
        target_return = 0
        
        sortino = risk_metrics.calculate_sortino(
            returns,
            target_return,
            periods_per_year=252
        )
        
        # Should penalize only negative returns
        downside_returns = returns[returns < target_return]
        downside_deviation = np.sqrt(np.mean(downside_returns**2)) * np.sqrt(252)
        
        expected_sortino = (returns.mean() * 252 - target_return) / downside_deviation
        assert abs(sortino - expected_sortino) < 0.1
    
    def test_calmar_ratio_calculation(self, risk_metrics):
        """
        Test 12.4.3: Calculate Calmar ratio
        Acceptance: Return over maximum drawdown
        """
        equity_curve = pd.Series([
            100000, 102000, 98000, 101000, 105000, 103000, 108000
        ])
        
        calmar = risk_metrics.calculate_calmar(
            equity_curve,
            periods_per_year=252
        )
        
        # Annual return
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1)
        annual_return = (1 + total_return) ** (252 / len(equity_curve)) - 1
        
        # Max drawdown
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max
        max_dd = drawdown.min()
        
        expected_calmar = annual_return / abs(max_dd)
        assert abs(calmar - expected_calmar) < 0.1
    
    def test_omega_ratio_calculation(self, risk_metrics):
        """
        Test 12.4.4: Calculate Omega ratio
        Acceptance: Probability-weighted gains/losses
        """
        returns = pd.Series(np.random.normal(0.001, 0.01, 252))
        threshold = 0
        
        omega = risk_metrics.calculate_omega(returns, threshold)
        
        # Gains above threshold
        gains = returns[returns > threshold] - threshold
        # Losses below threshold
        losses = threshold - returns[returns <= threshold]
        
        expected_omega = gains.sum() / losses.sum() if losses.sum() > 0 else float('inf')
        
        if not np.isinf(expected_omega):
            assert abs(omega - expected_omega) < 0.1


if __name__ == "__main__":
    pytest.main([__file__, '-v'])