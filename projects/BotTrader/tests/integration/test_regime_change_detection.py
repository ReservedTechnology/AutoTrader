"""
Integration Test for Market Regime Change Detection
Following TDD methodology for forex bot targeting 25% annual returns
Tests regime identification, transitions, and strategy adaptation
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional, Tuple
from enum import Enum


class MarketRegime(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    BREAKOUT = "breakout"
    RISK_OFF = "risk_off"
    RISK_ON = "risk_on"


class TestRegimeChangeDetection:
    """Integration test for market regime detection and adaptation"""
    
    @pytest.fixture
    def regime_detector(self):
        """Initialize regime change detector"""
        from src.analysis.regime_detector import MarketRegimeDetector
        
        detector = MarketRegimeDetector(
            lookback_periods=100,
            transition_threshold=0.7,
            min_regime_duration=20
        )
        return detector
    
    @pytest.fixture
    def market_data(self):
        """Generate market data with different regimes"""
        periods = 500
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='15min')
        
        # Create data with regime changes
        prices = []
        regimes = []
        
        # Trending up (100 periods)
        for i in range(100):
            prices.append(1.10000 + i * 0.00015 + np.random.normal(0, 0.00005))
            regimes.append(MarketRegime.TRENDING_UP)
        
        # Ranging (100 periods)
        for i in range(100):
            prices.append(1.11500 + np.sin(i/10) * 0.001 + np.random.normal(0, 0.00003))
            regimes.append(MarketRegime.RANGING)
        
        # Volatile (100 periods)
        for i in range(100):
            prices.append(1.11500 + np.random.normal(0, 0.002))
            regimes.append(MarketRegime.VOLATILE)
        
        # Trending down (100 periods)
        for i in range(100):
            prices.append(1.11500 - i * 0.00012 + np.random.normal(0, 0.00005))
            regimes.append(MarketRegime.TRENDING_DOWN)
        
        # Breakout (100 periods)
        for i in range(100):
            if i < 50:
                prices.append(1.10500 + np.random.normal(0, 0.00003))
            else:
                prices.append(1.10700 + (i-50) * 0.00020 + np.random.normal(0, 0.00005))
            regimes.append(MarketRegime.BREAKOUT if i >= 50 else MarketRegime.RANGING)
        
        return pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'actual_regime': regimes
        })
    
    @pytest.mark.integration
    def test_regime_identification(self, regime_detector, market_data):
        """
        Test IT.8.1: Identify current market regime
        Acceptance: Accurate regime classification
        """
        # Calculate regime indicators
        regime_features = regime_detector.calculate_features(market_data['close'])
        
        assert 'trend_strength' in regime_features
        assert 'volatility' in regime_features
        assert 'hurst_exponent' in regime_features
        assert 'fractal_dimension' in regime_features
        
        # Identify regime for different periods
        for start_idx in [0, 100, 200, 300, 400]:
            window_data = market_data.iloc[start_idx:start_idx+50]
            identified_regime = regime_detector.identify_regime(window_data['close'])
            
            # Get most common actual regime in window
            actual_regime = window_data['actual_regime'].mode()[0]
            
            # Should match or be close
            if actual_regime == MarketRegime.TRENDING_UP:
                assert identified_regime in [MarketRegime.TRENDING_UP, MarketRegime.RISK_ON]
            elif actual_regime == MarketRegime.RANGING:
                assert identified_regime == MarketRegime.RANGING
            elif actual_regime == MarketRegime.VOLATILE:
                assert identified_regime in [MarketRegime.VOLATILE, MarketRegime.RISK_OFF]
    
    @pytest.mark.integration
    def test_regime_transition_detection(self, regime_detector, market_data):
        """
        Test IT.8.2: Detect regime transitions
        Acceptance: Timely transition identification
        """
        # Process data in windows
        window_size = 50
        transitions = []
        
        for i in range(0, len(market_data) - window_size, 10):
            window = market_data.iloc[i:i+window_size]
            current_regime = regime_detector.identify_regime(window['close'])
            
            if i > 0:
                if current_regime != transitions[-1]['regime']:
                    transition = {
                        'from': transitions[-1]['regime'],
                        'to': current_regime,
                        'timestamp': window['timestamp'].iloc[-1],
                        'confidence': regime_detector.transition_confidence
                    }
                    transitions.append({
                        'regime': current_regime,
                        'transition': transition
                    })
                else:
                    transitions.append({'regime': current_regime})
            else:
                transitions.append({'regime': current_regime})
        
        # Should detect major transitions
        detected_transitions = [t for t in transitions if 'transition' in t]
        assert len(detected_transitions) >= 3  # At least 3 regime changes
        
        # Check transition timing
        for trans in detected_transitions:
            if trans['transition']['confidence'] > 0.7:
                # High confidence transitions should be accurate
                assert trans['transition']['from'] != trans['transition']['to']
    
    @pytest.mark.integration
    def test_regime_persistence_analysis(self, regime_detector):
        """
        Test IT.8.3: Analyze regime persistence
        Acceptance: Estimate regime duration
        """
        # Historical regime sequence
        regime_history = [
            {'regime': MarketRegime.TRENDING_UP, 'duration': 45},
            {'regime': MarketRegime.RANGING, 'duration': 30},
            {'regime': MarketRegime.TRENDING_DOWN, 'duration': 50},
            {'regime': MarketRegime.VOLATILE, 'duration': 20},
            {'regime': MarketRegime.TRENDING_UP, 'duration': 40}
        ]
        
        # Calculate persistence statistics
        persistence = regime_detector.analyze_persistence(regime_history)
        
        assert 'average_duration' in persistence
        assert 'regime_durations' in persistence
        
        # Trending regimes should last longer than volatile
        trending_avg = persistence['regime_durations'][MarketRegime.TRENDING_UP]['average']
        volatile_avg = persistence['regime_durations'].get(
            MarketRegime.VOLATILE, {'average': 20}
        )['average']
        
        assert trending_avg > volatile_avg
        
        # Predict current regime duration
        current_regime = MarketRegime.TRENDING_UP
        elapsed_periods = 15
        
        expected_remaining = regime_detector.predict_remaining_duration(
            current_regime,
            elapsed_periods,
            persistence
        )
        
        assert expected_remaining > 0
        assert 'confidence_interval' in expected_remaining
    
    @pytest.mark.integration
    def test_multi_timeframe_regime(self, regime_detector):
        """
        Test IT.8.4: Multi-timeframe regime analysis
        Acceptance: Consistent regime across timeframes
        """
        # Generate data for multiple timeframes
        base_data = pd.Series(1.10000 + np.cumsum(np.random.normal(0, 0.0001, 1000)))
        
        timeframes = {
            '5m': base_data,
            '15m': base_data.iloc[::3].reset_index(drop=True),  # Every 3rd point
            '1h': base_data.iloc[::12].reset_index(drop=True),  # Every 12th point
            '4h': base_data.iloc[::48].reset_index(drop=True)   # Every 48th point
        }
        
        # Identify regime in each timeframe
        regime_by_tf = {}
        for tf, data in timeframes.items():
            if len(data) > 50:
                regime = regime_detector.identify_regime(data)
                regime_by_tf[tf] = regime
        
        # Calculate consensus
        consensus = regime_detector.calculate_regime_consensus(regime_by_tf)
        
        assert consensus['primary_regime'] is not None
        assert consensus['confidence'] > 0
        assert consensus['agreement_score'] <= 1.0
        
        # Higher timeframes should have more weight
        assert consensus['timeframe_weights']['4h'] > consensus['timeframe_weights']['5m']
    
    @pytest.mark.integration
    def test_regime_based_strategy_selection(self, regime_detector):
        """
        Test IT.8.5: Select strategy based on regime
        Acceptance: Optimal strategy for each regime
        """
        strategies = {
            'trend_following': {
                'optimal_regimes': [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN],
                'performance': {'trending': 1.5, 'ranging': 0.7, 'volatile': 0.8}
            },
            'mean_reversion': {
                'optimal_regimes': [MarketRegime.RANGING],
                'performance': {'trending': 0.6, 'ranging': 1.4, 'volatile': 0.9}
            },
            'breakout': {
                'optimal_regimes': [MarketRegime.BREAKOUT],
                'performance': {'trending': 1.1, 'ranging': 0.8, 'volatile': 1.2}
            },
            'volatility_trading': {
                'optimal_regimes': [MarketRegime.VOLATILE],
                'performance': {'trending': 0.7, 'ranging': 0.9, 'volatile': 1.6}
            }
        }
        
        # Test strategy selection for each regime
        test_regimes = [
            MarketRegime.TRENDING_UP,
            MarketRegime.RANGING,
            MarketRegime.VOLATILE,
            MarketRegime.BREAKOUT
        ]
        
        for regime in test_regimes:
            selected = regime_detector.select_strategy(regime, strategies)
            
            assert selected is not None
            assert 'strategy' in selected
            assert 'confidence' in selected
            assert 'expected_performance' in selected
            
            # Should select optimal strategy
            if regime == MarketRegime.TRENDING_UP:
                assert selected['strategy'] == 'trend_following'
            elif regime == MarketRegime.RANGING:
                assert selected['strategy'] == 'mean_reversion'
            elif regime == MarketRegime.VOLATILE:
                assert selected['strategy'] == 'volatility_trading'
    
    @pytest.mark.integration
    def test_regime_change_risk_adjustment(self, regime_detector):
        """
        Test IT.8.6: Adjust risk based on regime changes
        Acceptance: Dynamic risk adaptation
        """
        # Define risk parameters by regime
        risk_params = {
            MarketRegime.TRENDING_UP: {
                'position_size': 1.2,  # 120% of base
                'stop_distance': 1.0,   # Normal stops
                'max_positions': 5
            },
            MarketRegime.VOLATILE: {
                'position_size': 0.5,   # 50% of base
                'stop_distance': 1.5,   # Wider stops
                'max_positions': 2
            },
            MarketRegime.RANGING: {
                'position_size': 0.8,   # 80% of base
                'stop_distance': 0.7,   # Tighter stops
                'max_positions': 4
            }
        }
        
        # Transition from trending to volatile
        transition = {
            'from': MarketRegime.TRENDING_UP,
            'to': MarketRegime.VOLATILE,
            'confidence': 0.85
        }
        
        # Calculate risk adjustments
        adjustments = regime_detector.calculate_risk_adjustments(
            transition,
            risk_params,
            current_positions=4
        )
        
        assert adjustments['reduce_positions'] == 2  # From 4 to 2
        assert adjustments['position_size_multiplier'] == 0.5/1.2
        assert adjustments['stop_adjustment'] == 1.5
        assert adjustments['action_urgency'] == 'high'  # Volatile regime
    
    @pytest.mark.integration
    def test_regime_prediction(self, regime_detector, market_data):
        """
        Test IT.8.7: Predict next regime
        Acceptance: Probabilistic regime forecasting
        """
        # Use historical data to train predictor
        historical_regimes = []
        for i in range(0, len(market_data)-50, 50):
            window = market_data.iloc[i:i+50]
            regime = regime_detector.identify_regime(window['close'])
            historical_regimes.append(regime)
        
        # Create transition matrix
        transition_matrix = regime_detector.build_transition_matrix(historical_regimes)
        
        # Predict next regime
        current_regime = MarketRegime.TRENDING_UP
        prediction = regime_detector.predict_next_regime(
            current_regime,
            transition_matrix,
            horizon=5  # 5 periods ahead
        )
        
        assert 'probabilities' in prediction
        assert sum(prediction['probabilities'].values()) == pytest.approx(1.0, rel=1e-3)
        assert 'most_likely' in prediction
        assert 'confidence' in prediction
        
        # Most likely should have highest probability
        most_likely_prob = prediction['probabilities'][prediction['most_likely']]
        assert most_likely_prob == max(prediction['probabilities'].values())
    
    @pytest.mark.integration
    def test_regime_performance_tracking(self, regime_detector):
        """
        Test IT.8.8: Track performance by regime
        Acceptance: Analyze strategy effectiveness per regime
        """
        # Historical trades with regimes
        trades = [
            {'regime': MarketRegime.TRENDING_UP, 'profit': 150, 'strategy': 'trend_following'},
            {'regime': MarketRegime.TRENDING_UP, 'profit': 200, 'strategy': 'trend_following'},
            {'regime': MarketRegime.RANGING, 'profit': -50, 'strategy': 'trend_following'},
            {'regime': MarketRegime.RANGING, 'profit': 100, 'strategy': 'mean_reversion'},
            {'regime': MarketRegime.VOLATILE, 'profit': -100, 'strategy': 'trend_following'},
            {'regime': MarketRegime.VOLATILE, 'profit': 180, 'strategy': 'volatility_trading'}
        ]
        
        # Analyze performance
        performance = regime_detector.analyze_regime_performance(trades)
        
        # Check performance by regime
        assert MarketRegime.TRENDING_UP in performance
        assert performance[MarketRegime.TRENDING_UP]['total_profit'] == 350
        assert performance[MarketRegime.TRENDING_UP]['win_rate'] == 1.0
        
        # Check strategy effectiveness by regime
        strategy_performance = regime_detector.analyze_strategy_by_regime(trades)
        
        assert strategy_performance['trend_following'][MarketRegime.TRENDING_UP]['profit'] == 350
        assert strategy_performance['trend_following'][MarketRegime.RANGING]['profit'] == -50
        assert strategy_performance['mean_reversion'][MarketRegime.RANGING]['profit'] == 100
        
        # Generate recommendations
        recommendations = regime_detector.generate_strategy_recommendations(
            strategy_performance
        )
        
        assert recommendations[MarketRegime.TRENDING_UP] == 'trend_following'
        assert recommendations[MarketRegime.RANGING] == 'mean_reversion'
        assert recommendations[MarketRegime.VOLATILE] == 'volatility_trading'
    
    @pytest.mark.integration
    def test_regime_alert_system(self, regime_detector):
        """
        Test IT.8.9: Regime change alert system
        Acceptance: Timely notifications of regime shifts
        """
        # Current regime
        current = {
            'regime': MarketRegime.TRENDING_UP,
            'confidence': 0.85,
            'duration': 25
        }
        
        # Potential transition detected
        potential = {
            'regime': MarketRegime.VOLATILE,
            'confidence': 0.72,
            'indicators': {
                'volatility_spike': True,
                'trend_breakdown': True,
                'volume_surge': False
            }
        }
        
        # Generate alerts
        alerts = regime_detector.generate_regime_alerts(current, potential)
        
        assert len(alerts) > 0
        
        # Check alert content
        primary_alert = alerts[0]
        assert primary_alert['type'] == 'regime_change_warning'
        assert primary_alert['severity'] in ['medium', 'high']
        assert 'message' in primary_alert
        assert 'suggested_actions' in primary_alert
        
        # Suggested actions for volatile regime
        if potential['regime'] == MarketRegime.VOLATILE:
            assert 'reduce_exposure' in primary_alert['suggested_actions']
            assert 'widen_stops' in primary_alert['suggested_actions']


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-m', 'integration'])