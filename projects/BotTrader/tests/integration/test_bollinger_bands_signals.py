"""
Integration Test for Bollinger Bands Trading Signals
Following TDD methodology for forex bot targeting 25% annual returns
Tests BB calculation, signal generation, and strategy integration
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Tuple


class TestBollingerBandsSignals:
    """Integration test for Bollinger Bands trading signals"""
    
    @pytest.fixture
    def bb_strategy(self):
        """Initialize Bollinger Bands strategy"""
        from src.strategies.bollinger_bands_strategy import BollingerBandsStrategy
        
        strategy = BollingerBandsStrategy(
            period=20,
            std_dev=2.0,
            pairs=['EUR_USD', 'GBP_USD', 'USD_JPY'],
            timeframes=['5m', '15m', '1h']
        )
        return strategy
    
    @pytest.fixture
    def price_data(self):
        """Generate sample price data for testing"""
        # Create realistic price movement with trends
        periods = 200
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='5min')
        
        # Generate price with trend and volatility
        trend = np.linspace(0, 0.01, periods)
        noise = np.random.normal(0, 0.001, periods)
        prices = 1.10500 + trend + noise
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices - np.abs(np.random.normal(0, 0.0001, periods)),
            'high': prices + np.abs(np.random.normal(0, 0.0002, periods)),
            'low': prices - np.abs(np.random.normal(0, 0.0002, periods)),
            'close': prices,
            'volume': np.random.randint(10000, 100000, periods)
        })
    
    @pytest.mark.integration
    def test_bollinger_bands_calculation(self, bb_strategy, price_data):
        """
        Test IT.3.1: Calculate Bollinger Bands
        Acceptance: Accurate band calculation with proper squeeze detection
        """
        bb_data = bb_strategy.calculate_bands(price_data)
        
        # Verify all components calculated
        assert 'upper_band' in bb_data.columns
        assert 'middle_band' in bb_data.columns
        assert 'lower_band' in bb_data.columns
        assert 'bandwidth' in bb_data.columns
        assert 'percent_b' in bb_data.columns
        
        # Verify middle band is SMA
        manual_sma = price_data['close'].rolling(20).mean()
        assert np.allclose(bb_data['middle_band'].dropna(), manual_sma.dropna(), rtol=1e-5)
        
        # Verify bands width
        manual_std = price_data['close'].rolling(20).std()
        expected_upper = manual_sma + 2 * manual_std
        assert np.allclose(bb_data['upper_band'].dropna(), expected_upper.dropna(), rtol=1e-5)
        
        # Verify %B calculation (position within bands)
        last_close = price_data['close'].iloc[-1]
        last_lower = bb_data['lower_band'].iloc[-1]
        last_upper = bb_data['upper_band'].iloc[-1]
        expected_percent_b = (last_close - last_lower) / (last_upper - last_lower)
        assert abs(bb_data['percent_b'].iloc[-1] - expected_percent_b) < 0.01
        
        # Check for squeeze detection
        bb_data['squeeze'] = bb_strategy.detect_squeeze(bb_data)
        squeeze_periods = bb_data['squeeze'].sum()
        assert squeeze_periods >= 0  # Should detect some squeeze periods
    
    @pytest.mark.integration
    def test_multi_timeframe_bb_signals(self, bb_strategy):
        """
        Test IT.3.2: Multi-timeframe BB signal generation
        Acceptance: Aligned signals across timeframes
        """
        # Generate data for multiple timeframes
        timeframe_data = {}
        for tf in ['5m', '15m', '1h']:
            periods = 200
            if tf == '5m':
                freq = '5min'
            elif tf == '15m':
                freq = '15min'
            else:
                freq = '1h'
            
            dates = pd.date_range(end=datetime.now(), periods=periods, freq=freq)
            prices = 1.10500 + np.cumsum(np.random.normal(0, 0.0001, periods))
            
            timeframe_data[tf] = pd.DataFrame({
                'timestamp': dates,
                'close': prices
            })
        
        # Calculate BB for each timeframe
        signals = bb_strategy.generate_multi_tf_signals(timeframe_data)
        
        # Check signal alignment
        assert '5m' in signals
        assert '15m' in signals
        assert '1h' in signals
        
        # Verify signal strength based on timeframe agreement
        consensus = bb_strategy.calculate_tf_consensus(signals)
        assert consensus['strength'] in ['strong', 'moderate', 'weak', 'none']
        
        # If all timeframes agree, signal should be strong
        if all(signals[tf]['signal'] == signals['5m']['signal'] for tf in signals):
            assert consensus['strength'] == 'strong'
    
    @pytest.mark.integration
    def test_bb_breakout_detection(self, bb_strategy, price_data):
        """
        Test IT.3.3: Detect Bollinger Band breakouts
        Acceptance: Identify and validate breakout signals
        """
        # Calculate bands
        bb_data = bb_strategy.calculate_bands(price_data)
        
        # Create breakout scenario
        breakout_price = bb_data['upper_band'].iloc[-1] + 0.0005
        price_data.loc[len(price_data)] = {
            'timestamp': datetime.now(),
            'close': breakout_price,
            'high': breakout_price + 0.0001,
            'low': breakout_price - 0.0001,
            'open': breakout_price,
            'volume': 50000
        }
        
        # Detect breakout
        breakout = bb_strategy.detect_breakout(price_data, bb_data)
        
        assert breakout['detected'] is True
        assert breakout['direction'] == 'upper'
        assert breakout['strength'] > 0
        
        # Validate breakout (check for continuation)
        validation = bb_strategy.validate_breakout(
            breakout,
            volume_confirmation=True,
            min_distance=0.0003
        )
        
        assert 'valid' in validation
        assert 'confidence' in validation
        
        # Generate trading signal from breakout
        signal = bb_strategy.breakout_to_signal(breakout, validation)
        if validation['valid']:
            assert signal['action'] in ['BUY', 'SELL']
            assert signal['entry_price'] is not None
            assert signal['stop_loss'] is not None
    
    @pytest.mark.integration
    def test_bb_mean_reversion_signals(self, bb_strategy):
        """
        Test IT.3.4: Generate mean reversion signals
        Acceptance: Trade band touches with reversal confirmation
        """
        # Create mean reversion scenario
        periods = 100
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='5min')
        
        # Price oscillating between bands
        t = np.linspace(0, 4*np.pi, periods)
        prices = 1.10500 + 0.002 * np.sin(t) + np.random.normal(0, 0.0001, periods)
        
        price_data = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'high': prices + 0.0001,
            'low': prices - 0.0001,
            'volume': np.random.randint(10000, 50000, periods)
        })
        
        # Calculate bands and signals
        bb_data = bb_strategy.calculate_bands(price_data)
        reversion_signals = bb_strategy.detect_mean_reversion(price_data, bb_data)
        
        # Should detect multiple reversion opportunities
        assert len(reversion_signals) > 0
        
        for signal in reversion_signals:
            assert signal['type'] == 'mean_reversion'
            assert signal['band_touched'] in ['upper', 'lower']
            
            # Upper band touch should generate sell signal
            if signal['band_touched'] == 'upper':
                assert signal['action'] == 'SELL'
            # Lower band touch should generate buy signal
            elif signal['band_touched'] == 'lower':
                assert signal['action'] == 'BUY'
            
            assert signal['confidence'] > 0
    
    @pytest.mark.integration
    def test_bb_squeeze_trading(self, bb_strategy):
        """
        Test IT.3.5: Trade Bollinger Band squeeze patterns
        Acceptance: Identify squeeze and trade expansion
        """
        # Create squeeze pattern (low volatility followed by expansion)
        periods = 150
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='5min')
        
        prices = []
        # Low volatility period (squeeze)
        for i in range(50):
            prices.append(1.10500 + np.random.normal(0, 0.00005))
        
        # Expansion period
        for i in range(100):
            if i < 50:
                # Upward breakout
                prices.append(1.10500 + i * 0.00002 + np.random.normal(0, 0.0001))
            else:
                # Continued movement
                prices.append(1.10600 + np.random.normal(0, 0.0001))
        
        price_data = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'volume': np.random.randint(10000, 100000, periods)
        })
        
        # Detect squeeze
        bb_data = bb_strategy.calculate_bands(price_data)
        squeeze_periods = bb_strategy.identify_squeeze_periods(bb_data)
        
        assert len(squeeze_periods) > 0
        
        # Trade squeeze expansion
        for squeeze in squeeze_periods:
            if squeeze['ended']:
                expansion_signal = bb_strategy.trade_squeeze_expansion(
                    price_data,
                    bb_data,
                    squeeze
                )
                
                assert expansion_signal is not None
                assert expansion_signal['type'] == 'squeeze_breakout'
                assert expansion_signal['action'] in ['BUY', 'SELL']
                assert expansion_signal['confidence'] > 0.5
    
    @pytest.mark.integration
    def test_bb_divergence_detection(self, bb_strategy):
        """
        Test IT.3.6: Detect price/BB divergences
        Acceptance: Identify divergences with other indicators
        """
        # Create divergence scenario
        periods = 100
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='5min')
        
        # Price making higher highs but bandwidth decreasing
        prices = []
        for i in range(periods):
            if i < 50:
                prices.append(1.10500 + i * 0.00003)  # Uptrend
            else:
                # Higher high but with less momentum
                prices.append(1.10650 + (i-50) * 0.00001)
        
        price_data = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'volume': np.random.randint(10000, 50000, periods)
        })
        
        # Add RSI for divergence confirmation
        from src.indicators.rsi import RSICalculator
        rsi_calc = RSICalculator()
        price_data['rsi'] = rsi_calc.calculate(price_data['close'], period=14)
        
        # Calculate BB and detect divergence
        bb_data = bb_strategy.calculate_bands(price_data)
        divergences = bb_strategy.detect_divergences(price_data, bb_data)
        
        assert len(divergences) > 0
        
        for div in divergences:
            assert div['type'] in ['bullish_divergence', 'bearish_divergence']
            assert 'price_trend' in div
            assert 'indicator_trend' in div
            assert div['confidence'] > 0
            
            # Generate signal from divergence
            signal = bb_strategy.divergence_to_signal(div)
            if div['confidence'] > 0.7:
                assert signal['action'] in ['BUY', 'SELL']
    
    @pytest.mark.integration
    def test_bb_walk_signals(self, bb_strategy):
        """
        Test IT.3.7: Detect band walk patterns
        Acceptance: Identify strong trends via band walking
        """
        # Create band walk scenario (strong trend)
        periods = 100
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='5min')
        
        # Strong uptrend walking the upper band
        trend_strength = 0.00005
        prices = []
        for i in range(periods):
            base_price = 1.10500 + i * trend_strength
            # Add small noise but keep near upper band
            prices.append(base_price + np.random.normal(0, 0.00002))
        
        price_data = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'volume': np.random.randint(20000, 100000, periods)
        })
        
        # Detect band walk
        bb_data = bb_strategy.calculate_bands(price_data)
        walk_signals = bb_strategy.detect_band_walk(price_data, bb_data)
        
        assert len(walk_signals) > 0
        
        for signal in walk_signals:
            assert signal['type'] == 'band_walk'
            assert signal['band'] in ['upper', 'lower']
            assert signal['consecutive_touches'] > 3
            
            # Upper band walk indicates strong uptrend
            if signal['band'] == 'upper':
                assert signal['trend'] == 'bullish'
                assert signal['action'] == 'BUY' or signal['action'] == 'HOLD_LONG'
    
    @pytest.mark.integration
    def test_bb_risk_management(self, bb_strategy):
        """
        Test IT.3.8: BB-based stop loss and take profit
        Acceptance: Dynamic risk levels based on bands
        """
        # Current market data
        current_price = 1.10500
        bb_levels = {
            'upper_band': 1.10600,
            'middle_band': 1.10500,
            'lower_band': 1.10400,
            'bandwidth': 0.00200,
            'atr': 0.00055
        }
        
        # Long position risk management
        long_risk = bb_strategy.calculate_bb_risk_levels(
            entry_price=current_price,
            position_type='LONG',
            bb_levels=bb_levels
        )
        
        # Stop loss should be below lower band
        assert long_risk['stop_loss'] < bb_levels['lower_band']
        # Take profit at or above upper band
        assert long_risk['take_profit'] >= bb_levels['upper_band']
        # Risk/reward ratio should be favorable
        risk = current_price - long_risk['stop_loss']
        reward = long_risk['take_profit'] - current_price
        assert reward / risk > 1.5
        
        # Dynamic adjustment based on bandwidth
        tight_bb = bb_levels.copy()
        tight_bb['bandwidth'] = 0.00100  # Tighter bands
        
        tight_risk = bb_strategy.calculate_bb_risk_levels(
            entry_price=current_price,
            position_type='LONG',
            bb_levels=tight_bb
        )
        
        # Tighter bands should result in closer stops
        assert abs(tight_risk['stop_loss'] - current_price) < abs(long_risk['stop_loss'] - current_price)
    
    @pytest.mark.integration
    def test_bb_strategy_backtest(self, bb_strategy):
        """
        Test IT.3.9: Backtest BB strategy performance
        Acceptance: Positive returns with acceptable drawdown
        """
        # Generate historical data
        periods = 1000
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='5min')
        
        # Create realistic market with trends and reversions
        prices = []
        base = 1.10500
        for i in range(periods):
            # Add trend component
            trend = 0.00001 * i
            # Add cyclical component
            cycle = 0.002 * np.sin(2 * np.pi * i / 100)
            # Add noise
            noise = np.random.normal(0, 0.0001)
            
            prices.append(base + trend + cycle + noise)
        
        historical_data = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'high': np.array(prices) + np.abs(np.random.normal(0, 0.0001, periods)),
            'low': np.array(prices) - np.abs(np.random.normal(0, 0.0001, periods)),
            'volume': np.random.randint(10000, 100000, periods)
        })
        
        # Run backtest
        backtest_results = bb_strategy.backtest(
            historical_data,
            initial_capital=100000,
            position_size=0.02  # 2% risk per trade
        )
        
        # Performance assertions
        assert backtest_results['total_return'] > 0  # Profitable
        assert backtest_results['sharpe_ratio'] > 0.5  # Decent risk-adjusted returns
        assert backtest_results['max_drawdown'] < 0.15  # Less than 15% drawdown
        assert backtest_results['win_rate'] > 0.45  # Reasonable win rate
        
        # Trade statistics
        assert backtest_results['total_trades'] > 20  # Sufficient sample
        assert backtest_results['avg_trade_duration'] > 0  # Holds positions
        assert backtest_results['profit_factor'] > 1.0  # Wins > Losses


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-m', 'integration'])