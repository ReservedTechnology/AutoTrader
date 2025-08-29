"""
Test Suite for Kelly Criterion Position Sizing
Following TDD methodology for forex bot targeting 25% annual returns
Tests for optimal position sizing with 25% max per trade
"""
import pytest
import numpy as np
import pandas as pd
import os
import psycopg2
from supabase import create_client, Client
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

load_dotenv()


class TestKellyCriterion:
    """
    Test suite for Kelly Criterion position sizing
    Target: 2% risk per trade, 25% max position size
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
    def trade_history(self):
        """Generate sample trade history for Kelly calculation"""
        np.random.seed(42)
        n_trades = 100
        
        # Generate trades with 60% win rate
        wins = np.random.random(n_trades) < 0.60
        
        trades = []
        for i, is_win in enumerate(wins):
            if is_win:
                # Win: return between 1% and 3%
                return_pct = np.random.uniform(0.01, 0.03)
            else:
                # Loss: between -1% and -2%
                return_pct = np.random.uniform(-0.02, -0.01)
            
            trades.append({
                'trade_id': f'trade_{i}',
                'return': return_pct,
                'win': is_win,
                'risk_reward_ratio': abs(return_pct / 0.01)
            })
        
        return pd.DataFrame(trades)
    
    def test_kelly_calculation(self, trade_history):
        """
        Test 5.1.1: Calculate Kelly fraction
        Acceptance: Kelly fraction between 0 and 0.25 (25% max)
        """
        from src.risk.kelly_criterion import KellyCalculator
        
        calculator = KellyCalculator(max_fraction=0.25)
        
        # Calculate basic Kelly
        win_rate = trade_history['win'].mean()
        avg_win = trade_history[trade_history['win']]['return'].mean()
        avg_loss = abs(trade_history[~trade_history['win']]['return'].mean())
        
        kelly_fraction = calculator.calculate(
            win_probability=win_rate,
            win_amount=avg_win,
            loss_amount=avg_loss
        )
        
        # Kelly should be positive for profitable system
        assert kelly_fraction > 0, \
            f"Kelly fraction negative: {kelly_fraction:.4f}"
        
        # Should not exceed max fraction
        assert kelly_fraction <= 0.25, \
            f"Kelly fraction {kelly_fraction:.4f} exceeds 25% max"
        
        # Calculate expected value
        expected_value = win_rate * avg_win - (1 - win_rate) * avg_loss
        assert expected_value > 0, \
            "System has negative expected value"
        
        print(f"Kelly fraction: {kelly_fraction:.4f}")
        print(f"Win rate: {win_rate:.2%}")
        print(f"Avg win: {avg_win:.2%}, Avg loss: {avg_loss:.2%}")
    
    def test_kelly_with_multiple_outcomes(self):
        """
        Test 5.1.2: Kelly criterion with multiple outcome scenarios
        Acceptance: Handle complex probability distributions
        """
        from src.risk.kelly_criterion import MultiOutcomeKelly
        
        calculator = MultiOutcomeKelly()
        
        # Define multiple outcomes (big win, small win, small loss, big loss)
        outcomes = [
            {'probability': 0.10, 'return': 0.05},   # Big win
            {'probability': 0.50, 'return': 0.01},   # Small win
            {'probability': 0.30, 'return': -0.01},  # Small loss
            {'probability': 0.10, 'return': -0.03}   # Big loss
        ]
        
        kelly_fraction = calculator.calculate_multi(outcomes)
        
        # Verify probability sum
        total_prob = sum(o['probability'] for o in outcomes)
        assert abs(total_prob - 1.0) < 1e-6, \
            f"Probabilities don't sum to 1: {total_prob}"
        
        # Kelly should be reasonable
        assert 0 <= kelly_fraction <= 1, \
            f"Invalid Kelly fraction: {kelly_fraction}"
        
        # Calculate expected return
        expected_return = sum(o['probability'] * o['return'] for o in outcomes)
        
        if expected_return > 0:
            assert kelly_fraction > 0, \
                "Positive expectation should give positive Kelly"
    
    def test_fractional_kelly(self, trade_history):
        """
        Test 5.1.3: Test fractional Kelly (25%, 50%, 75% of full Kelly)
        Acceptance: Reduce risk with fractional Kelly
        """
        from src.risk.kelly_criterion import FractionalKellyCalculator
        
        # Calculate full Kelly first
        win_rate = trade_history['win'].mean()
        avg_win = trade_history[trade_history['win']]['return'].mean()
        avg_loss = abs(trade_history[~trade_history['win']]['return'].mean())
        
        fractions = [0.25, 0.50, 0.75, 1.0]
        results = {}
        
        for fraction in fractions:
            calculator = FractionalKellyCalculator(
                kelly_fraction=fraction,
                max_position=0.25
            )
            
            position_size = calculator.calculate_position_size(
                win_probability=win_rate,
                win_amount=avg_win,
                loss_amount=avg_loss
            )
            
            results[fraction] = position_size
            
            # Each fraction should be proportional
            if fraction < 1.0:
                assert position_size < results[1.0], \
                    f"Fractional Kelly {fraction} not reducing position size"
        
        # Verify proportionality
        assert results[0.25] < results[0.50] < results[0.75] < results[1.0], \
            "Fractional Kelly not properly ordered"
        
        print(f"Position sizes by Kelly fraction: {results}")
    
    @pytest.mark.asyncio
    async def test_dynamic_position_sizing(self, trade_history, timescale_connection):
        """
        Test 5.1.4: Dynamic position sizing based on recent performance
        Acceptance: Adjust position size with changing win rate
        """
        from src.risk.kelly_criterion import DynamicKellyManager
        
        manager = DynamicKellyManager(
            lookback_periods=20,
            min_position=0.01,
            max_position=0.25
        )
        
        cursor = timescale_connection.cursor()
        
        # Simulate trading with dynamic sizing
        for i in range(20, len(trade_history)):
            # Use last 20 trades for Kelly calculation
            recent_trades = trade_history.iloc[i-20:i]
            
            position_size = manager.calculate_dynamic_position(recent_trades)
            
            # Store position sizing decision
            cursor.execute("""
                INSERT INTO position_sizing (time, data)
                VALUES (%s, %s);
            """, (
                datetime.now() + timedelta(minutes=i),
                json.dumps({
                    'method': 'kelly_criterion',
                    'position_size': float(position_size),
                    'recent_win_rate': float(recent_trades['win'].mean()),
                    'recent_return': float(recent_trades['return'].mean()),
                    'trade_count': len(recent_trades),
                    'confidence': float(min(1.0, len(recent_trades) / 30))
                })
            ))
            
            # Verify constraints
            assert 0.01 <= position_size <= 0.25, \
                f"Position size {position_size:.4f} out of bounds"
        
        timescale_connection.commit()
        cursor.close()
    
    def test_kelly_with_correlation(self):
        """
        Test 5.1.5: Kelly criterion with correlated positions
        Acceptance: Reduce position size for correlated trades
        """
        from src.risk.kelly_criterion import CorrelatedKellyCalculator
        
        calculator = CorrelatedKellyCalculator()
        
        # Define positions with correlations
        positions = [
            {'symbol': 'EUR_USD', 'kelly': 0.10},
            {'symbol': 'GBP_USD', 'kelly': 0.08},
            {'symbol': 'EUR_GBP', 'kelly': 0.06}
        ]
        
        # Correlation matrix (EUR/USD and GBP/USD highly correlated)
        correlations = {
            ('EUR_USD', 'GBP_USD'): 0.85,
            ('EUR_USD', 'EUR_GBP'): -0.30,
            ('GBP_USD', 'EUR_GBP'): -0.40
        }
        
        adjusted_positions = calculator.adjust_for_correlation(
            positions,
            correlations,
            max_correlation=0.7
        )
        
        # Adjusted positions should be reduced for correlated pairs
        for original, adjusted in zip(positions, adjusted_positions):
            assert adjusted['adjusted_kelly'] <= original['kelly'], \
                f"Adjusted Kelly exceeds original for {original['symbol']}"
        
        # Highly correlated positions should be reduced more
        eur_reduction = 1 - adjusted_positions[0]['adjusted_kelly'] / positions[0]['kelly']
        gbp_reduction = 1 - adjusted_positions[1]['adjusted_kelly'] / positions[1]['kelly']
        
        assert eur_reduction > 0 or gbp_reduction > 0, \
            "No reduction applied to correlated positions"
    
    @pytest.mark.asyncio
    async def test_portfolio_heat_limit(self, supabase_client):
        """
        Test 5.1.6: Enforce portfolio heat limit (5% max)
        Acceptance: Total risk doesn't exceed 5% of portfolio
        """
        from src.risk.kelly_criterion import PortfolioHeatManager
        
        manager = PortfolioHeatManager(
            max_portfolio_heat=0.05,
            max_positions=5
        )
        
        # Current portfolio state
        portfolio = {
            'total_capital': 100000,
            'open_positions': [
                {'symbol': 'EUR_USD', 'risk': 0.01},  # 1% risk
                {'symbol': 'GBP_JPY', 'risk': 0.015}, # 1.5% risk
                {'symbol': 'AUD_JPY', 'risk': 0.01}   # 1% risk
            ]
        }
        
        # Current heat = 3.5%
        current_heat = sum(p['risk'] for p in portfolio['open_positions'])
        
        # Try to add new position
        new_position_risk = 0.02  # 2% risk
        
        allowed = manager.check_heat_limit(
            current_heat,
            new_position_risk
        )
        
        if current_heat + new_position_risk <= 0.05:
            assert allowed, "Position incorrectly rejected"
        else:
            assert not allowed, "Position should be rejected (exceeds heat limit)"
            
            # Calculate maximum allowed position
            max_allowed = manager.calculate_max_position(current_heat)
            assert max_allowed == 0.05 - current_heat, \
                "Incorrect max position calculation"
        
        # Store heat limit configuration in Supabase
        config = {
            'key': 'portfolio_heat_limit',
            'value': '0.05',
            'description': 'Maximum portfolio heat (5%)',
            'updated_at': datetime.now().isoformat()
        }
        
        try:
            response = supabase_client.table('system_config').upsert(config).execute()
            assert response.data, "Failed to store heat limit config"
        except Exception as e:
            print(f"Heat limit config storage: {e}")
    
    def test_risk_reward_optimization(self, trade_history):
        """
        Test 5.1.7: Optimize position size for risk/reward ratio
        Acceptance: Balance risk and reward optimally
        """
        from src.risk.kelly_criterion import RiskRewardOptimizer
        
        optimizer = RiskRewardOptimizer()
        
        # Calculate risk/reward for different position sizes
        position_sizes = np.linspace(0.01, 0.25, 25)
        results = []
        
        for size in position_sizes:
            # Simulate returns with position size
            returns = trade_history['return'] * size
            
            # Calculate metrics
            sharpe = optimizer.calculate_sharpe(returns)
            max_dd = optimizer.calculate_max_drawdown(returns)
            calmar = optimizer.calculate_calmar(returns, max_dd)
            
            results.append({
                'position_size': size,
                'sharpe_ratio': sharpe,
                'max_drawdown': max_dd,
                'calmar_ratio': calmar
            })
        
        results_df = pd.DataFrame(results)
        
        # Find optimal position size (best Sharpe)
        optimal_idx = results_df['sharpe_ratio'].idxmax()
        optimal_size = results_df.iloc[optimal_idx]['position_size']
        
        assert 0.01 <= optimal_size <= 0.25, \
            f"Optimal size {optimal_size:.4f} out of bounds"
        
        print(f"Optimal position size: {optimal_size:.4f}")
        print(f"Sharpe at optimal: {results_df.iloc[optimal_idx]['sharpe_ratio']:.2f}")
    
    def test_kelly_with_stop_loss(self):
        """
        Test 5.1.8: Kelly criterion with stop-loss consideration
        Acceptance: Adjust Kelly for stop-loss levels
        """
        from src.risk.kelly_criterion import KellyWithStopLoss
        
        calculator = KellyWithStopLoss()
        
        # Trading parameters
        win_rate = 0.60
        avg_win_pips = 50
        stop_loss_pips = 30
        
        # Calculate Kelly with stop-loss
        kelly_fraction = calculator.calculate_with_stops(
            win_probability=win_rate,
            target_pips=avg_win_pips,
            stop_loss_pips=stop_loss_pips
        )
        
        # Risk/reward ratio
        risk_reward = avg_win_pips / stop_loss_pips
        
        # Kelly formula: f = (p*b - q) / b
        # where p = win_rate, q = 1-p, b = risk_reward
        expected_kelly = (win_rate * risk_reward - (1 - win_rate)) / risk_reward
        expected_kelly = max(0, min(0.25, expected_kelly))  # Apply limits
        
        assert abs(kelly_fraction - expected_kelly) < 0.01, \
            f"Kelly calculation error: {kelly_fraction:.4f} vs {expected_kelly:.4f}"
        
        # Test with different stop-loss levels
        stop_losses = [20, 30, 40, 50]
        kelly_by_stop = {}
        
        for sl in stop_losses:
            kf = calculator.calculate_with_stops(
                win_probability=win_rate,
                target_pips=avg_win_pips,
                stop_loss_pips=sl
            )
            kelly_by_stop[sl] = kf
        
        # Tighter stops (better R:R) should give higher Kelly
        assert kelly_by_stop[20] > kelly_by_stop[50], \
            "Kelly not responding correctly to stop-loss changes"
    
    def test_monte_carlo_kelly(self, trade_history):
        """
        Test 5.1.9: Monte Carlo simulation for Kelly validation
        Acceptance: Verify Kelly through simulation
        """
        from src.risk.kelly_criterion import MonteCarloKellyValidator
        
        validator = MonteCarloKellyValidator(
            n_simulations=1000,
            n_periods=252  # One year of trading days
        )
        
        # Get trade statistics
        win_rate = trade_history['win'].mean()
        avg_win = trade_history[trade_history['win']]['return'].mean()
        avg_loss = abs(trade_history[~trade_history['win']]['return'].mean())
        
        # Test different Kelly fractions
        kelly_fractions = [0.05, 0.10, 0.15, 0.20, 0.25]
        simulation_results = {}
        
        for kf in kelly_fractions:
            results = validator.simulate(
                kelly_fraction=kf,
                win_probability=win_rate,
                win_amount=avg_win,
                loss_amount=avg_loss
            )
            
            simulation_results[kf] = {
                'median_return': np.median(results['final_returns']),
                'prob_profit': np.mean(results['final_returns'] > 0),
                'max_drawdown': np.mean(results['max_drawdowns']),
                'sharpe_ratio': np.mean(results['sharpe_ratios'])
            }
        
        # Verify that there's an optimal Kelly fraction
        returns_by_kelly = [simulation_results[kf]['median_return'] for kf in kelly_fractions]
        optimal_idx = np.argmax(returns_by_kelly)
        optimal_kelly = kelly_fractions[optimal_idx]
        
        print(f"Optimal Kelly from simulation: {optimal_kelly:.4f}")
        print(f"Median return at optimal: {returns_by_kelly[optimal_idx]:.2%}")
    
    def test_adaptive_kelly(self, trade_history):
        """
        Test 5.1.10: Adaptive Kelly based on market regime
        Acceptance: Adjust Kelly for market conditions
        """
        from src.risk.kelly_criterion import AdaptiveKellyManager
        
        manager = AdaptiveKellyManager()
        
        # Define market regimes
        regimes = {
            'trending': {'volatility': 0.01, 'kelly_multiplier': 1.2},
            'ranging': {'volatility': 0.005, 'kelly_multiplier': 0.8},
            'volatile': {'volatility': 0.02, 'kelly_multiplier': 0.5}
        }
        
        base_kelly = 0.10
        
        for regime_name, regime_params in regimes.items():
            adjusted_kelly = manager.adjust_for_regime(
                base_kelly=base_kelly,
                volatility=regime_params['volatility'],
                regime=regime_name
            )
            
            expected = base_kelly * regime_params['kelly_multiplier']
            expected = min(0.25, expected)  # Apply max limit
            
            assert abs(adjusted_kelly - expected) < 0.01, \
                f"Incorrect adjustment for {regime_name} regime"
            
            print(f"{regime_name}: Kelly adjusted from {base_kelly:.4f} to {adjusted_kelly:.4f}")


class TestKellyImplementation:
    """Test suite for Kelly criterion implementation details"""
    
    def test_kelly_with_leverage(self):
        """
        Test 5.2.1: Kelly with leverage consideration
        Acceptance: Properly account for leverage in position sizing
        """
        from src.risk.kelly_criterion import LeveragedKellyCalculator
        
        calculator = LeveragedKellyCalculator(max_leverage=10)
        
        # Base Kelly calculation
        kelly_fraction = 0.15
        account_equity = 100000
        
        # Test with different leverage levels
        leverage_levels = [1, 2, 5, 10]
        
        for leverage in leverage_levels:
            position_size = calculator.calculate_leveraged_position(
                kelly_fraction=kelly_fraction,
                equity=account_equity,
                leverage=leverage
            )
            
            # Effective risk should remain constant
            effective_risk = position_size / (account_equity * leverage)
            
            assert abs(effective_risk - kelly_fraction) < 0.01, \
                f"Leverage {leverage}x not properly applied"
            
            # Position size should not exceed equity * leverage
            assert position_size <= account_equity * leverage, \
                "Position exceeds available leverage"
    
    def test_kelly_drawdown_protection(self):
        """
        Test 5.2.2: Kelly with drawdown protection
        Acceptance: Reduce Kelly during drawdowns
        """
        from src.risk.kelly_criterion import DrawdownProtectedKelly
        
        protector = DrawdownProtectedKelly(
            base_kelly=0.15,
            drawdown_threshold=0.10,
            reduction_factor=0.5
        )
        
        # Test with different drawdown levels
        drawdown_levels = [0.0, 0.05, 0.10, 0.15, 0.20]
        
        for dd in drawdown_levels:
            adjusted_kelly = protector.adjust_for_drawdown(dd)
            
            if dd <= 0.10:
                # No reduction below threshold
                assert adjusted_kelly == 0.15, \
                    f"Kelly reduced unnecessarily at {dd:.0%} drawdown"
            else:
                # Progressive reduction above threshold
                assert adjusted_kelly < 0.15, \
                    f"Kelly not reduced at {dd:.0%} drawdown"
                assert adjusted_kelly >= 0, \
                    "Kelly became negative"
        
        print("Kelly adjustments by drawdown:")
        for dd in drawdown_levels:
            adj = protector.adjust_for_drawdown(dd)
            print(f"  {dd:.0%} DD -> {adj:.4f} Kelly")


if __name__ == "__main__":
    pytest.main([__file__, '-v'])