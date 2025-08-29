"""
Test Suite for Risk Calculations
Following TDD methodology for forex bot targeting 25% annual returns
Tests for position sizing, risk metrics, and portfolio limits
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from decimal import Decimal
import json


class TestPositionSizing:
    """Test suite for position sizing calculations"""
    
    @pytest.fixture
    def risk_calculator(self):
        """Initialize risk calculator"""
        from src.risk.position_sizing import PositionSizingCalculator
        
        calculator = PositionSizingCalculator(
            max_risk_per_trade=0.02,  # 2% max risk
            max_position_size=0.25,    # 25% max position
            min_position_size=0.01     # 1% min position
        )
        return calculator
    
    @pytest.fixture
    def account_data(self):
        """Mock account data"""
        return {
            'balance': 100000.00,
            'equity': 105000.00,
            'margin_used': 20000.00,
            'margin_available': 85000.00,
            'open_positions': 3,
            'unrealized_pnl': 5000.00
        }
    
    def test_kelly_criterion_sizing(self, risk_calculator, account_data):
        """
        Test 8.1.1: Kelly Criterion position sizing
        Acceptance: Optimal f calculation
        """
        # Historical trade data
        trade_history = pd.DataFrame({
            'profit': [120, -80, 150, -60, 200, -70, 180, -90, 160, -50],
            'risk': [100] * 10
        })
        
        # Calculate Kelly percentage
        kelly_pct = risk_calculator.calculate_kelly_criterion(trade_history)
        
        # Win rate = 6/10 = 0.6
        # Avg win = 165, Avg loss = 70
        # Win/loss ratio = 165/70 = 2.357
        # Kelly = (p*b - q)/b = (0.6*2.357 - 0.4)/2.357
        expected_kelly = (0.6 * 2.357 - 0.4) / 2.357
        
        assert abs(kelly_pct - expected_kelly) < 0.01
        assert 0 < kelly_pct < 1  # Should be fractional
        
        # Apply Kelly with safety factor
        position_size = risk_calculator.apply_kelly_sizing(
            account_data['equity'],
            kelly_pct,
            safety_factor=0.25  # Use 25% of Kelly
        )
        
        assert position_size == account_data['equity'] * kelly_pct * 0.25
        assert position_size <= account_data['equity'] * 0.25  # Max position limit
    
    def test_fixed_fractional_sizing(self, risk_calculator, account_data):
        """
        Test 8.1.2: Fixed fractional position sizing
        Acceptance: 2% risk per trade
        """
        stop_loss_pips = 50
        pip_value = 0.0001  # For EUR/USD
        
        position_size = risk_calculator.calculate_fixed_fractional(
            account_equity=account_data['equity'],
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            risk_percentage=0.02
        )
        
        # Risk amount = 105000 * 0.02 = 2100
        # Position size = 2100 / (50 * 0.0001) = 420000
        expected_size = (account_data['equity'] * 0.02) / (stop_loss_pips * pip_value)
        
        assert position_size == expected_size
        assert position_size == 420000
        
        # Verify risk amount
        risk_amount = position_size * stop_loss_pips * pip_value
        assert risk_amount == account_data['equity'] * 0.02
    
    def test_volatility_based_sizing(self, risk_calculator):
        """
        Test 8.1.3: ATR-based position sizing
        Acceptance: Adjusts for market volatility
        """
        account_equity = 100000
        atr_value = 0.0055  # 55 pips
        
        # Higher volatility = smaller position
        position_size_high_vol = risk_calculator.calculate_volatility_sizing(
            account_equity=account_equity,
            atr=atr_value,
            atr_multiplier=2.0,
            risk_percentage=0.02
        )
        
        # Lower volatility = larger position
        position_size_low_vol = risk_calculator.calculate_volatility_sizing(
            account_equity=account_equity,
            atr=0.0025,  # 25 pips
            atr_multiplier=2.0,
            risk_percentage=0.02
        )
        
        assert position_size_high_vol < position_size_low_vol
        
        # Verify risk calculation
        stop_distance = atr_value * 2.0
        risk_amount = position_size_high_vol * stop_distance
        assert abs(risk_amount - account_equity * 0.02) < 1
    
    def test_position_size_limits(self, risk_calculator, account_data):
        """
        Test 8.1.4: Enforce position size limits
        Acceptance: Min 1%, Max 25% of equity
        """
        # Test maximum limit
        large_position = risk_calculator.apply_position_limits(
            position_size=50000000,  # Very large
            account_equity=account_data['equity']
        )
        
        assert large_position == account_data['equity'] * 0.25  # 25% max
        
        # Test minimum limit
        small_position = risk_calculator.apply_position_limits(
            position_size=500,  # Very small
            account_equity=account_data['equity']
        )
        
        assert small_position == account_data['equity'] * 0.01  # 1% min
        
        # Test normal position (within limits)
        normal_position = risk_calculator.apply_position_limits(
            position_size=10000,
            account_equity=account_data['equity']
        )
        
        assert normal_position == 10000  # Unchanged
    
    def test_correlation_adjusted_sizing(self, risk_calculator):
        """
        Test 8.1.5: Adjust for correlated positions
        Acceptance: Reduces size for correlated pairs
        """
        existing_positions = [
            {'symbol': 'EUR_USD', 'size': 100000},
            {'symbol': 'GBP_USD', 'size': 50000}
        ]
        
        correlations = {
            ('EUR_USD', 'EUR_GBP'): 0.85,
            ('GBP_USD', 'EUR_GBP'): 0.75
        }
        
        # New position in EUR_GBP
        base_size = 80000
        
        adjusted_size = risk_calculator.adjust_for_correlation(
            symbol='EUR_GBP',
            base_size=base_size,
            existing_positions=existing_positions,
            correlations=correlations
        )
        
        # Should reduce size due to high correlation
        assert adjusted_size < base_size
        
        # Higher correlation = more reduction
        correlation_factor = 1 - max(0.85, 0.75) * 0.5  # 50% reduction for full correlation
        expected_size = base_size * correlation_factor
        assert abs(adjusted_size - expected_size) < 1000


class TestRiskMetrics:
    """Test suite for risk metrics calculation"""
    
    @pytest.fixture
    def metrics_calculator(self):
        """Initialize metrics calculator"""
        from src.risk.risk_metrics import RiskMetricsCalculator
        
        calculator = RiskMetricsCalculator()
        return calculator
    
    @pytest.fixture
    def portfolio_data(self):
        """Sample portfolio returns"""
        dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
        returns = np.random.normal(0.001, 0.02, 252)  # Daily returns
        
        return pd.Series(returns, index=dates)
    
    def test_sharpe_ratio_calculation(self, metrics_calculator, portfolio_data):
        """
        Test 8.2.1: Calculate Sharpe ratio
        Acceptance: Risk-adjusted returns > 1.2
        """
        risk_free_rate = 0.02  # 2% annual
        
        sharpe = metrics_calculator.calculate_sharpe_ratio(
            returns=portfolio_data,
            risk_free_rate=risk_free_rate,
            periods_per_year=252
        )
        
        # Manual calculation
        excess_returns = portfolio_data.mean() * 252 - risk_free_rate
        volatility = portfolio_data.std() * np.sqrt(252)
        expected_sharpe = excess_returns / volatility
        
        assert abs(sharpe - expected_sharpe) < 0.01
        
        # Test with actual profitable strategy
        profitable_returns = pd.Series(
            np.random.normal(0.002, 0.015, 252)  # Higher return, lower vol
        )
        
        good_sharpe = metrics_calculator.calculate_sharpe_ratio(
            returns=profitable_returns,
            risk_free_rate=risk_free_rate
        )
        
        assert good_sharpe > 1.2  # Target threshold
    
    def test_maximum_drawdown(self, metrics_calculator):
        """
        Test 8.2.2: Calculate maximum drawdown
        Acceptance: Track peak-to-trough decline
        """
        # Create equity curve with drawdown
        equity = pd.Series([
            100000, 102000, 105000, 103000, 98000,  # Drawdown from 105k to 98k
            99000, 101000, 104000, 106000, 108000   # Recovery
        ])
        
        max_dd, dd_duration = metrics_calculator.calculate_max_drawdown(equity)
        
        # Max drawdown = (98000 - 105000) / 105000 = -6.67%
        assert abs(max_dd - (-0.0667)) < 0.001
        
        # Duration from peak (index 2) to trough (index 4) = 2 periods
        assert dd_duration == 2
        
        # Test drawdown series
        dd_series = metrics_calculator.get_drawdown_series(equity)
        assert len(dd_series) == len(equity)
        assert dd_series.iloc[2] == 0  # Peak
        assert dd_series.iloc[4] == pytest.approx(-0.0667, rel=1e-3)  # Trough
    
    def test_value_at_risk(self, metrics_calculator, portfolio_data):
        """
        Test 8.2.3: Calculate VaR and CVaR
        Acceptance: 95% and 99% confidence levels
        """
        confidence_95 = 0.95
        confidence_99 = 0.99
        
        # Historical VaR
        var_95 = metrics_calculator.calculate_var(
            returns=portfolio_data,
            confidence=confidence_95,
            method='historical'
        )
        
        var_99 = metrics_calculator.calculate_var(
            returns=portfolio_data,
            confidence=confidence_99,
            method='historical'
        )
        
        # VaR at 99% should be more negative (higher risk)
        assert var_99 < var_95
        
        # Check percentile calculation
        expected_var_95 = np.percentile(portfolio_data, (1 - confidence_95) * 100)
        assert abs(var_95 - expected_var_95) < 0.001
        
        # Conditional VaR (Expected Shortfall)
        cvar_95 = metrics_calculator.calculate_cvar(
            returns=portfolio_data,
            confidence=confidence_95
        )
        
        # CVaR should be worse than VaR
        assert cvar_95 < var_95
        
        # Parametric VaR (assuming normal distribution)
        param_var_95 = metrics_calculator.calculate_var(
            returns=portfolio_data,
            confidence=confidence_95,
            method='parametric'
        )
        
        # Should be close to historical for normal distribution
        assert abs(param_var_95 - var_95) < 0.01
    
    def test_calmar_ratio(self, metrics_calculator):
        """
        Test 8.2.4: Calculate Calmar ratio
        Acceptance: Return/MaxDD ratio
        """
        # Create returns with known characteristics
        returns = pd.Series([0.01, 0.02, -0.03, 0.015, 0.025, -0.01, 0.02])
        equity = (1 + returns).cumprod() * 100000
        
        calmar = metrics_calculator.calculate_calmar_ratio(
            returns=returns,
            periods_per_year=252
        )
        
        # Annual return
        total_return = (1 + returns).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        
        # Max drawdown
        max_dd, _ = metrics_calculator.calculate_max_drawdown(equity)
        
        expected_calmar = annual_return / abs(max_dd)
        assert abs(calmar - expected_calmar) < 0.1
    
    def test_sortino_ratio(self, metrics_calculator, portfolio_data):
        """
        Test 8.2.5: Calculate Sortino ratio
        Acceptance: Downside deviation focus
        """
        target_return = 0.0  # Minimum acceptable return
        risk_free_rate = 0.02 / 252  # Daily risk-free rate
        
        sortino = metrics_calculator.calculate_sortino_ratio(
            returns=portfolio_data,
            target_return=target_return,
            risk_free_rate=risk_free_rate,
            periods_per_year=252
        )
        
        # Sortino uses downside deviation
        downside_returns = portfolio_data[portfolio_data < target_return]
        downside_std = np.sqrt(np.mean(downside_returns ** 2)) * np.sqrt(252)
        
        excess_return = portfolio_data.mean() * 252 - risk_free_rate * 252
        expected_sortino = excess_return / downside_std
        
        assert abs(sortino - expected_sortino) < 0.1
        
        # Sortino should be higher than Sharpe for same returns
        sharpe = metrics_calculator.calculate_sharpe_ratio(
            returns=portfolio_data,
            risk_free_rate=risk_free_rate * 252
        )
        
        assert sortino > sharpe  # Penalizes only downside volatility


class TestPortfolioRisk:
    """Test suite for portfolio-level risk management"""
    
    @pytest.fixture
    def portfolio_manager(self):
        """Initialize portfolio risk manager"""
        from src.risk.portfolio_risk import PortfolioRiskManager
        
        manager = PortfolioRiskManager(
            max_portfolio_heat=0.05,  # 5% max heat
            max_correlation_exposure=0.7,
            max_concentration=0.3
        )
        return manager
    
    @pytest.fixture
    def positions(self):
        """Sample portfolio positions"""
        return [
            {
                'symbol': 'EUR_USD',
                'size': 100000,
                'entry_price': 1.10500,
                'current_price': 1.10600,
                'stop_loss': 1.10400,
                'unrealized_pnl': 100
            },
            {
                'symbol': 'GBP_USD',
                'size': 50000,
                'entry_price': 1.25000,
                'current_price': 1.24950,
                'stop_loss': 1.24800,
                'unrealized_pnl': -25
            },
            {
                'symbol': 'USD_JPY',
                'size': 75000,
                'entry_price': 110.500,
                'current_price': 110.600,
                'stop_loss': 110.300,
                'unrealized_pnl': 75
            }
        ]
    
    def test_portfolio_heat_calculation(self, portfolio_manager, positions):
        """
        Test 8.3.1: Calculate portfolio heat
        Acceptance: Total risk exposure < 5%
        """
        account_equity = 100000
        
        heat = portfolio_manager.calculate_portfolio_heat(
            positions=positions,
            account_equity=account_equity
        )
        
        # Calculate expected heat
        total_risk = 0
        for pos in positions:
            risk = abs(pos['size'] * (pos['entry_price'] - pos['stop_loss']))
            total_risk += risk
        
        expected_heat = total_risk / account_equity
        
        assert abs(heat - expected_heat) < 0.001
        assert heat < 0.05  # Below 5% limit
        
        # Check if new position allowed
        new_position_risk = 0.015  # 1.5% risk
        can_add = portfolio_manager.can_add_position(
            current_heat=heat,
            new_position_risk=new_position_risk
        )
        
        assert can_add == (heat + new_position_risk < 0.05)
    
    def test_correlation_exposure(self, portfolio_manager, positions):
        """
        Test 8.3.2: Monitor correlation exposure
        Acceptance: Diversification metrics
        """
        correlations = pd.DataFrame({
            'EUR_USD': [1.0, 0.7, -0.3],
            'GBP_USD': [0.7, 1.0, -0.2],
            'USD_JPY': [-0.3, -0.2, 1.0]
        }, index=['EUR_USD', 'GBP_USD', 'USD_JPY'])
        
        exposure = portfolio_manager.calculate_correlation_exposure(
            positions=positions,
            correlations=correlations
        )
        
        assert 'total_correlation' in exposure
        assert 'max_pair_correlation' in exposure
        assert 'diversification_ratio' in exposure
        
        # Max correlation should be 0.7 (EUR_USD - GBP_USD)
        assert exposure['max_pair_correlation'] == 0.7
        
        # Check if portfolio is over-correlated
        is_over_correlated = portfolio_manager.is_over_correlated(
            exposure=exposure
        )
        
        assert is_over_correlated == (exposure['max_pair_correlation'] > 0.7)
    
    def test_position_concentration(self, portfolio_manager, positions):
        """
        Test 8.3.3: Monitor position concentration
        Acceptance: No position > 30% of portfolio
        """
        total_exposure = sum(p['size'] for p in positions)
        
        concentration = portfolio_manager.calculate_concentration(
            positions=positions
        )
        
        # EUR_USD is largest position
        assert concentration['largest_position'] == 'EUR_USD'
        assert concentration['largest_percentage'] == 100000 / total_exposure
        
        # Check concentration limit
        is_concentrated = portfolio_manager.is_over_concentrated(
            concentration=concentration
        )
        
        assert is_concentrated == (concentration['largest_percentage'] > 0.3)
        
        # Calculate HHI (Herfindahl-Hirschman Index)
        hhi = portfolio_manager.calculate_hhi(positions)
        
        # HHI = sum of squared market shares
        expected_hhi = sum((p['size'] / total_exposure) ** 2 for p in positions)
        assert abs(hhi - expected_hhi) < 0.001
    
    def test_risk_limits_enforcement(self, portfolio_manager):
        """
        Test 8.3.4: Enforce risk limits
        Acceptance: Prevents excessive risk
        """
        account_equity = 100000
        
        # Test daily loss limit
        daily_losses = -3500  # 3.5% loss
        
        should_stop = portfolio_manager.check_daily_loss_limit(
            daily_pnl=daily_losses,
            account_equity=account_equity,
            limit_percentage=0.03  # 3% daily limit
        )
        
        assert should_stop is True
        
        # Test consecutive losses
        trade_results = [-100, -150, -200, -175, -125]  # 5 consecutive losses
        
        should_pause = portfolio_manager.check_consecutive_losses(
            recent_trades=trade_results,
            max_consecutive=4
        )
        
        assert should_pause is True
        
        # Test win rate threshold
        last_20_trades = [1, -1, 1, -1, -1, -1, 1, -1, -1, -1,
                         -1, 1, -1, -1, -1, 1, -1, -1, -1, 1]  # 30% win rate
        
        win_rate = sum(1 for t in last_20_trades if t > 0) / len(last_20_trades)
        
        should_reduce = portfolio_manager.check_win_rate_threshold(
            win_rate=win_rate,
            min_threshold=0.4
        )
        
        assert should_reduce is True


class TestRiskAdjustment:
    """Test suite for dynamic risk adjustment"""
    
    @pytest.fixture
    def risk_adjuster(self):
        """Initialize risk adjuster"""
        from src.risk.risk_adjustment import DynamicRiskAdjuster
        
        adjuster = DynamicRiskAdjuster()
        return adjuster
    
    def test_volatility_scaling(self, risk_adjuster):
        """
        Test 8.4.1: Scale risk by market volatility
        Acceptance: Reduces risk in high volatility
        """
        base_risk = 0.02  # 2% base risk
        
        # Normal volatility
        normal_vol = 0.01  # 1% daily volatility
        adjusted_risk_normal = risk_adjuster.adjust_for_volatility(
            base_risk=base_risk,
            current_volatility=normal_vol,
            target_volatility=normal_vol
        )
        
        assert adjusted_risk_normal == base_risk
        
        # High volatility (2x normal)
        high_vol = 0.02
        adjusted_risk_high = risk_adjuster.adjust_for_volatility(
            base_risk=base_risk,
            current_volatility=high_vol,
            target_volatility=normal_vol
        )
        
        # Should reduce risk by half
        assert adjusted_risk_high == base_risk * (normal_vol / high_vol)
        assert adjusted_risk_high == 0.01
        
        # Low volatility (0.5x normal)
        low_vol = 0.005
        adjusted_risk_low = risk_adjuster.adjust_for_volatility(
            base_risk=base_risk,
            current_volatility=low_vol,
            target_volatility=normal_vol,
            max_multiplier=1.5  # Cap increase at 1.5x
        )
        
        # Should increase risk but capped at 1.5x
        assert adjusted_risk_low == base_risk * 1.5
    
    def test_regime_based_adjustment(self, risk_adjuster):
        """
        Test 8.4.2: Adjust risk based on market regime
        Acceptance: Adapts to market conditions
        """
        base_risk = 0.02
        
        # Trending market
        trending_adjustment = risk_adjuster.adjust_for_regime(
            base_risk=base_risk,
            regime='trending',
            regime_confidence=0.8
        )
        
        # Should maintain or increase risk in trends
        assert trending_adjustment >= base_risk
        
        # Ranging market
        ranging_adjustment = risk_adjuster.adjust_for_regime(
            base_risk=base_risk,
            regime='ranging',
            regime_confidence=0.7
        )
        
        # Should reduce risk in ranges
        assert ranging_adjustment < base_risk
        
        # Volatile/uncertain market
        volatile_adjustment = risk_adjuster.adjust_for_regime(
            base_risk=base_risk,
            regime='volatile',
            regime_confidence=0.9
        )
        
        # Should significantly reduce risk
        assert volatile_adjustment < ranging_adjustment
    
    def test_performance_based_scaling(self, risk_adjuster):
        """
        Test 8.4.3: Scale risk based on performance
        Acceptance: Increases risk when winning
        """
        base_risk = 0.02
        
        # Recent good performance
        good_performance = {
            'win_rate': 0.65,
            'profit_factor': 2.1,
            'sharpe_ratio': 1.8,
            'recent_returns': [0.02, 0.01, 0.03, -0.01, 0.02]
        }
        
        increased_risk = risk_adjuster.adjust_for_performance(
            base_risk=base_risk,
            performance=good_performance
        )
        
        assert increased_risk > base_risk
        assert increased_risk <= base_risk * 1.25  # Max 25% increase
        
        # Recent poor performance
        poor_performance = {
            'win_rate': 0.35,
            'profit_factor': 0.8,
            'sharpe_ratio': 0.3,
            'recent_returns': [-0.02, -0.01, 0.01, -0.03, -0.02]
        }
        
        reduced_risk = risk_adjuster.adjust_for_performance(
            base_risk=base_risk,
            performance=poor_performance
        )
        
        assert reduced_risk < base_risk
        assert reduced_risk >= base_risk * 0.5  # Min 50% of base


if __name__ == "__main__":
    pytest.main([__file__, '-v'])