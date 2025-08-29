"""
Test Suite for RSI (Relative Strength Index) Signal Generation
Following TDD methodology for forex bot targeting 25% annual returns
Tests for RSI(10) day trading and RSI(9) scalping configurations
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


class TestRSISignals:
    """
    Test suite for RSI indicator and signal generation
    RSI(10) for day trading, RSI(9) for scalping
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
    def price_data(self):
        """Generate sample price data"""
        dates = pd.date_range(end=datetime.now(), periods=100, freq='5min')
        prices = 1.1000 + np.cumsum(np.random.randn(100) * 0.0001)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'open': prices - np.random.rand(100) * 0.0001,
            'high': prices + np.random.rand(100) * 0.0002,
            'low': prices - np.random.rand(100) * 0.0002,
            'volume': np.random.randint(10000, 100000, 100)
        })
        return df
    
    def test_rsi_calculation(self, price_data):
        """
        Test 4.1.1: Calculate RSI values
        Acceptance: RSI values between 0 and 100
        """
        from src.indicators.rsi import RSICalculator
        
        calculator = RSICalculator()
        
        # Test RSI(10) for day trading
        rsi_10 = calculator.calculate(price_data['close'], period=10)
        
        assert len(rsi_10) == len(price_data), \
            "RSI array length mismatch"
        
        # First few values should be NaN due to warmup period
        assert pd.isna(rsi_10[:10]).any(), \
            "Should have NaN values during warmup"
        
        # Valid RSI values should be between 0 and 100
        valid_rsi = rsi_10[~pd.isna(rsi_10)]
        assert all(0 <= val <= 100 for val in valid_rsi), \
            "RSI values out of range [0, 100]"
        
        # Test RSI(9) for scalping
        rsi_9 = calculator.calculate(price_data['close'], period=9)
        valid_rsi_9 = rsi_9[~pd.isna(rsi_9)]
        assert all(0 <= val <= 100 for val in valid_rsi_9), \
            "RSI(9) values out of range"
    
    def test_oversold_overbought_signals(self, price_data):
        """
        Test 4.1.2: Generate oversold/overbought signals
        Acceptance: Signals at 30/70 thresholds
        """
        from src.indicators.rsi import RSISignalGenerator
        
        generator = RSISignalGenerator(
            oversold_threshold=30,
            overbought_threshold=70
        )
        
        # Calculate RSI
        rsi_values = generator.calculate_rsi(price_data['close'], period=10)
        
        # Generate signals
        signals = generator.generate_signals(rsi_values)
        
        # Check signal types
        assert set(signals['signal'].unique()).issubset({'buy', 'sell', 'neutral'}), \
            "Invalid signal types"
        
        # Verify oversold signals (RSI < 30 -> buy)
        oversold_mask = rsi_values < 30
        oversold_signals = signals[oversold_mask & ~pd.isna(rsi_values)]
        if len(oversold_signals) > 0:
            assert all(s == 'buy' for s in oversold_signals['signal']), \
                "Oversold should generate buy signals"
        
        # Verify overbought signals (RSI > 70 -> sell)
        overbought_mask = rsi_values > 70
        overbought_signals = signals[overbought_mask & ~pd.isna(rsi_values)]
        if len(overbought_signals) > 0:
            assert all(s == 'sell' for s in overbought_signals['signal']), \
                "Overbought should generate sell signals"
    
    def test_divergence_detection(self, price_data):
        """
        Test 4.1.3: Detect RSI divergence
        Acceptance: Identify bullish/bearish divergences
        """
        from src.indicators.rsi import RSIDivergenceDetector
        
        detector = RSIDivergenceDetector()
        
        # Calculate RSI
        rsi = detector.calculate_rsi(price_data['close'], period=10)
        
        # Detect divergences
        divergences = detector.detect_divergences(
            price_data['close'],
            rsi,
            lookback=20
        )
        
        # Check divergence types
        valid_types = {'bullish', 'bearish', 'hidden_bullish', 'hidden_bearish', None}
        assert all(d in valid_types for d in divergences), \
            "Invalid divergence types detected"
        
        # Bullish divergence: price makes lower low, RSI makes higher low
        # Bearish divergence: price makes higher high, RSI makes lower high
        
        # Count divergences
        bullish_count = sum(1 for d in divergences if d == 'bullish')
        bearish_count = sum(1 for d in divergences if d == 'bearish')
        
        print(f"Detected {bullish_count} bullish and {bearish_count} bearish divergences")
    
    @pytest.mark.asyncio
    async def test_signal_storage(self, price_data, timescale_connection):
        """
        Test 4.1.4: Store RSI signals in TimescaleDB
        Acceptance: Signals persisted with metadata
        """
        from src.indicators.rsi import RSISignalGenerator
        
        generator = RSISignalGenerator()
        rsi_values = generator.calculate_rsi(price_data['close'], period=10)
        signals = generator.generate_signals(rsi_values)
        
        cursor = timescale_connection.cursor()
        
        # Store signals
        for i in range(min(20, len(signals))):
            if not pd.isna(rsi_values.iloc[i]):
                cursor.execute("""
                    INSERT INTO trading_signals (time, data)
                    VALUES (%s, %s);
                """, (
                    price_data['timestamp'].iloc[i],
                    json.dumps({
                        'indicator': 'RSI',
                        'period': 10,
                        'value': float(rsi_values.iloc[i]),
                        'signal': signals['signal'].iloc[i],
                        'strength': signals.get('strength', [None] * len(signals)).iloc[i],
                        'symbol': 'EUR_USD'
                    })
                ))
        
        timescale_connection.commit()
        cursor.close()
    
    def test_multi_timeframe_rsi(self, price_data):
        """
        Test 4.1.5: Multi-timeframe RSI analysis
        Acceptance: Consistent signals across timeframes
        """
        from src.indicators.rsi import MultiTimeframeRSI
        
        mtf_rsi = MultiTimeframeRSI()
        
        # Calculate RSI for different timeframes
        timeframes = {
            '5min': 9,   # Scalping
            '15min': 10, # Day trading
            '1h': 14     # Swing trading
        }
        
        rsi_values = {}
        for tf, period in timeframes.items():
            # Resample data for timeframe (simplified)
            if tf == '5min':
                tf_data = price_data
            elif tf == '15min':
                tf_data = price_data.resample('15min', on='timestamp').agg({
                    'close': 'last',
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'volume': 'sum'
                }).dropna()
            else:  # 1h
                tf_data = price_data.resample('1h', on='timestamp').agg({
                    'close': 'last',
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'volume': 'sum'
                }).dropna()
            
            if len(tf_data) > period:
                rsi_values[tf] = mtf_rsi.calculate(tf_data['close'], period)
        
        # Check alignment of signals
        aligned_signals = mtf_rsi.align_signals(rsi_values)
        
        assert 'consensus' in aligned_signals, \
            "Missing consensus signal"
        assert aligned_signals['confidence'] >= 0, \
            "Invalid confidence score"
    
    def test_rsi_velocity(self):
        """
        Test 4.1.6: Calculate RSI velocity (rate of change)
        Acceptance: Detect momentum changes
        """
        from src.indicators.rsi import RSIVelocity
        
        # Create trending data
        periods = 100
        trend = np.linspace(0, 1, periods)
        noise = np.random.randn(periods) * 0.1
        prices = pd.Series(1.1000 + trend * 0.01 + noise)
        
        velocity_calc = RSIVelocity()
        
        # Calculate RSI and velocity
        rsi = velocity_calc.calculate_rsi(prices, period=10)
        velocity = velocity_calc.calculate_velocity(rsi, lookback=5)
        
        # Velocity should exist for valid RSI values
        valid_idx = ~pd.isna(rsi) & ~pd.isna(velocity)
        assert valid_idx.sum() > 0, "No valid velocity values"
        
        # High positive velocity indicates strengthening momentum
        high_velocity = velocity[velocity > 5]
        if len(high_velocity) > 0:
            print(f"Detected {len(high_velocity)} periods of strong momentum")
    
    def test_rsi_failure_swings(self):
        """
        Test 4.1.7: Detect RSI failure swings
        Acceptance: Identify reversal patterns
        """
        from src.indicators.rsi import RSIFailureSwingDetector
        
        # Create data with reversal pattern
        prices = pd.Series([
            1.1000, 1.1010, 1.1020, 1.1015, 1.1005,  # Peak
            1.0995, 1.0985, 1.0990, 1.1000, 1.1010,  # Trough and recovery
            1.1005, 1.0995, 1.0985, 1.0975, 1.0970   # Failure swing
        ])
        
        detector = RSIFailureSwingDetector()
        rsi = detector.calculate_rsi(prices, period=5)
        
        # Detect failure swings
        swings = detector.detect_failure_swings(rsi, prices)
        
        # Check for valid swing types
        valid_swings = {'bullish_failure_swing', 'bearish_failure_swing', None}
        assert all(s in valid_swings for s in swings), \
            "Invalid failure swing detected"
    
    def test_rsi_with_volume(self, price_data):
        """
        Test 4.1.8: Volume-weighted RSI
        Acceptance: Incorporate volume in RSI calculation
        """
        from src.indicators.rsi import VolumeWeightedRSI
        
        vw_rsi = VolumeWeightedRSI()
        
        # Calculate standard and volume-weighted RSI
        standard_rsi = vw_rsi.calculate_standard(price_data['close'], period=10)
        volume_rsi = vw_rsi.calculate_volume_weighted(
            price_data['close'],
            price_data['volume'],
            period=10
        )
        
        # Both should be valid RSI values
        valid_standard = standard_rsi[~pd.isna(standard_rsi)]
        valid_volume = volume_rsi[~pd.isna(volume_rsi)]
        
        assert all(0 <= val <= 100 for val in valid_standard), \
            "Standard RSI out of range"
        assert all(0 <= val <= 100 for val in valid_volume), \
            "Volume-weighted RSI out of range"
        
        # Volume-weighted should differ from standard
        diff = abs(valid_standard - valid_volume[:len(valid_standard)])
        assert diff.mean() > 0, \
            "Volume-weighted RSI identical to standard RSI"


class TestRSIOptimization:
    """Test suite for RSI parameter optimization"""
    
    def test_period_optimization(self):
        """
        Test 4.2.1: Optimize RSI period
        Acceptance: Find optimal period for currency pair
        """
        from src.indicators.rsi import RSIOptimizer
        
        # Generate sample data
        prices = pd.Series(1.1000 + np.cumsum(np.random.randn(500) * 0.0001))
        
        optimizer = RSIOptimizer()
        
        # Test different periods
        periods = [7, 9, 10, 14, 21]
        results = {}
        
        for period in periods:
            performance = optimizer.backtest_period(
                prices,
                period=period,
                oversold=30,
                overbought=70
            )
            results[period] = performance
        
        # Find best period
        best_period = max(results, key=lambda k: results[k]['sharpe_ratio'])
        
        assert best_period in periods, \
            f"Best period {best_period} not in test range"
        assert results[best_period]['sharpe_ratio'] > 0, \
            "Best period has negative Sharpe ratio"
    
    def test_threshold_optimization(self):
        """
        Test 4.2.2: Optimize oversold/overbought thresholds
        Acceptance: Find optimal thresholds for signals
        """
        from src.indicators.rsi import RSIThresholdOptimizer
        
        # Generate trending data
        prices = pd.Series(1.1000 + np.cumsum(np.random.randn(500) * 0.0001))
        
        optimizer = RSIThresholdOptimizer()
        
        # Test different threshold combinations
        threshold_pairs = [
            (20, 80),  # Extreme
            (30, 70),  # Standard
            (35, 65),  # Conservative
            (25, 75),  # Moderate
        ]
        
        results = {}
        for oversold, overbought in threshold_pairs:
            performance = optimizer.backtest_thresholds(
                prices,
                period=10,
                oversold=oversold,
                overbought=overbought
            )
            results[(oversold, overbought)] = performance
        
        # Find best thresholds
        best_thresholds = max(results, key=lambda k: results[k]['win_rate'])
        
        assert best_thresholds in threshold_pairs, \
            "Best thresholds not in test range"
        
        print(f"Optimal thresholds: {best_thresholds}")


if __name__ == "__main__":
    pytest.main([__file__, '-v'])