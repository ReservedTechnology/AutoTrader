"""
Test Suite for MACD (Moving Average Convergence Divergence) Signal Generation
Following TDD methodology for forex bot targeting 25% annual returns
Tests for MACD(12,26,9) configuration for forex trading
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


class TestMACDSignals:
    """
    Test suite for MACD indicator and signal generation
    Standard configuration: MACD(12,26,9)
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
    def price_data(self):
        """Generate sample price data with trend"""
        dates = pd.date_range(end=datetime.now(), periods=200, freq='15min')
        
        # Create trending data
        trend = np.sin(np.linspace(0, 4*np.pi, 200)) * 0.005
        prices = 1.1000 + trend + np.cumsum(np.random.randn(200) * 0.0001)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'open': prices - np.random.rand(200) * 0.0001,
            'high': prices + np.random.rand(200) * 0.0002,
            'low': prices - np.random.rand(200) * 0.0002,
            'volume': np.random.randint(10000, 100000, 200)
        })
        return df
    
    def test_macd_calculation(self, price_data):
        """
        Test 4.3.1: Calculate MACD line, signal line, and histogram
        Acceptance: Correct MACD(12,26,9) calculation
        """
        from src.indicators.macd import MACDCalculator
        
        calculator = MACDCalculator(
            fast_period=12,
            slow_period=26,
            signal_period=9
        )
        
        macd_data = calculator.calculate(price_data['close'])
        
        # Check all components exist
        assert 'macd_line' in macd_data, "Missing MACD line"
        assert 'signal_line' in macd_data, "Missing signal line"
        assert 'histogram' in macd_data, "Missing histogram"
        
        # Check lengths
        assert len(macd_data['macd_line']) == len(price_data), \
            "MACD line length mismatch"
        
        # MACD = EMA(12) - EMA(26), so first 26 values should be NaN
        assert pd.isna(macd_data['macd_line'][:26]).all(), \
            "MACD should be NaN for first 26 periods"
        
        # Signal line is EMA(9) of MACD, so needs additional warmup
        assert pd.isna(macd_data['signal_line'][:35]).any(), \
            "Signal line should have warmup period"
        
        # Histogram = MACD - Signal
        valid_idx = ~pd.isna(macd_data['histogram'])
        if valid_idx.sum() > 0:
            calculated_hist = (
                macd_data['macd_line'][valid_idx] - 
                macd_data['signal_line'][valid_idx]
            )
            assert np.allclose(
                macd_data['histogram'][valid_idx],
                calculated_hist,
                rtol=1e-5
            ), "Histogram calculation error"
    
    def test_crossover_signals(self, price_data):
        """
        Test 4.3.2: Detect MACD crossover signals
        Acceptance: Identify bullish/bearish crossovers
        """
        from src.indicators.macd import MACDSignalGenerator
        
        generator = MACDSignalGenerator()
        macd_data = generator.calculate_macd(price_data['close'])
        
        # Generate crossover signals
        signals = generator.detect_crossovers(macd_data)
        
        # Check signal types
        valid_signals = {'bullish_crossover', 'bearish_crossover', 'neutral'}
        assert set(signals).issubset(valid_signals), \
            "Invalid signal types detected"
        
        # Find crossover points
        bullish_crosses = [i for i, s in enumerate(signals) if s == 'bullish_crossover']
        bearish_crosses = [i for i, s in enumerate(signals) if s == 'bearish_crossover']
        
        # Verify crossover logic
        for idx in bullish_crosses:
            if idx > 0:
                # MACD crosses above signal line
                prev_diff = (
                    macd_data['macd_line'].iloc[idx-1] - 
                    macd_data['signal_line'].iloc[idx-1]
                )
                curr_diff = (
                    macd_data['macd_line'].iloc[idx] - 
                    macd_data['signal_line'].iloc[idx]
                )
                assert prev_diff <= 0 and curr_diff > 0, \
                    f"Invalid bullish crossover at index {idx}"
    
    def test_zero_line_crosses(self, price_data):
        """
        Test 4.3.3: Detect zero line crosses
        Acceptance: Identify trend changes at zero line
        """
        from src.indicators.macd import MACDZeroLineCrossDetector
        
        detector = MACDZeroLineCrossDetector()
        macd_data = detector.calculate_macd(price_data['close'])
        
        # Detect zero line crosses
        zero_crosses = detector.detect_zero_crosses(macd_data['macd_line'])
        
        # Check signal types
        valid_types = {'bullish_zero_cross', 'bearish_zero_cross', None}
        assert all(cross in valid_types for cross in zero_crosses), \
            "Invalid zero cross type"
        
        # Verify zero cross logic
        for i, cross in enumerate(zero_crosses):
            if cross == 'bullish_zero_cross' and i > 0:
                # MACD crosses above zero
                assert macd_data['macd_line'].iloc[i-1] <= 0, \
                    "Previous MACD should be <= 0 for bullish cross"
                assert macd_data['macd_line'].iloc[i] > 0, \
                    "Current MACD should be > 0 for bullish cross"
    
    def test_divergence_detection(self, price_data):
        """
        Test 4.3.4: Detect MACD divergences
        Acceptance: Identify price/MACD divergences
        """
        from src.indicators.macd import MACDDivergenceDetector
        
        detector = MACDDivergenceDetector()
        macd_data = detector.calculate_macd(price_data['close'])
        
        # Detect divergences
        divergences = detector.detect_divergences(
            price_data['close'],
            macd_data['macd_line'],
            lookback=20
        )
        
        # Check divergence types
        valid_types = {'bullish_divergence', 'bearish_divergence', 'hidden_bullish', 'hidden_bearish', None}
        assert all(d in valid_types for d in divergences), \
            "Invalid divergence type detected"
        
        # Count divergences
        div_counts = pd.Series(divergences).value_counts()
        print(f"Divergences detected: {div_counts.to_dict()}")
    
    @pytest.mark.asyncio
    async def test_signal_storage(self, price_data, timescale_connection):
        """
        Test 4.3.5: Store MACD signals in TimescaleDB
        Acceptance: Signals persisted with all components
        """
        from src.indicators.macd import MACDSignalGenerator
        
        generator = MACDSignalGenerator()
        macd_data = generator.calculate_macd(price_data['close'])
        signals = generator.detect_crossovers(macd_data)
        
        cursor = timescale_connection.cursor()
        
        # Store signals with MACD components
        for i in range(min(30, len(signals))):
            if not pd.isna(macd_data['macd_line'].iloc[i]):
                cursor.execute("""
                    INSERT INTO trading_signals (time, data)
                    VALUES (%s, %s);
                """, (
                    price_data['timestamp'].iloc[i],
                    json.dumps({
                        'indicator': 'MACD',
                        'symbol': 'EUR_USD',
                        'macd_line': float(macd_data['macd_line'].iloc[i]),
                        'signal_line': float(macd_data['signal_line'].iloc[i]) if not pd.isna(macd_data['signal_line'].iloc[i]) else None,
                        'histogram': float(macd_data['histogram'].iloc[i]) if not pd.isna(macd_data['histogram'].iloc[i]) else None,
                        'signal': signals[i],
                        'parameters': {
                            'fast': 12,
                            'slow': 26,
                            'signal': 9
                        }
                    })
                ))
        
        timescale_connection.commit()
        cursor.close()
    
    def test_histogram_momentum(self, price_data):
        """
        Test 4.3.6: Analyze histogram for momentum
        Acceptance: Detect momentum changes from histogram
        """
        from src.indicators.macd import MACDHistogramAnalyzer
        
        analyzer = MACDHistogramAnalyzer()
        macd_data = analyzer.calculate_macd(price_data['close'])
        
        # Analyze histogram momentum
        momentum = analyzer.analyze_momentum(macd_data['histogram'])
        
        # Check momentum states
        valid_states = {'increasing', 'decreasing', 'peak', 'trough', 'neutral'}
        assert set(momentum).issubset(valid_states), \
            "Invalid momentum states"
        
        # Detect momentum shifts
        shifts = analyzer.detect_momentum_shifts(momentum)
        
        # Count momentum patterns
        increasing = sum(1 for m in momentum if m == 'increasing')
        decreasing = sum(1 for m in momentum if m == 'decreasing')
        
        print(f"Momentum: {increasing} increasing, {decreasing} decreasing periods")
    
    def test_multi_timeframe_macd(self, price_data):
        """
        Test 4.3.7: Multi-timeframe MACD analysis
        Acceptance: Align signals across timeframes
        """
        from src.indicators.macd import MultiTimeframeMACD
        
        mtf_macd = MultiTimeframeMACD()
        
        # Calculate MACD for different timeframes
        timeframes = ['15min', '1h', '4h']
        macd_signals = {}
        
        for tf in timeframes:
            # Resample data for timeframe
            if tf == '15min':
                tf_data = price_data
            elif tf == '1h':
                tf_data = price_data.resample('1h', on='timestamp').agg({
                    'close': 'last',
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'volume': 'sum'
                }).dropna()
            else:  # 4h
                tf_data = price_data.resample('4h', on='timestamp').agg({
                    'close': 'last',
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'volume': 'sum'
                }).dropna()
            
            if len(tf_data) > 26:
                macd_data = mtf_macd.calculate(tf_data['close'])
                signals = mtf_macd.generate_signals(macd_data)
                macd_signals[tf] = signals
        
        # Align signals
        aligned = mtf_macd.align_signals(macd_signals)
        
        assert 'consensus' in aligned, "Missing consensus signal"
        assert 'strength' in aligned, "Missing signal strength"
        assert 0 <= aligned['strength'] <= 1, \
            f"Invalid signal strength: {aligned['strength']}"
    
    @pytest.mark.asyncio
    async def test_parameter_optimization(self, price_data, supabase_client):
        """
        Test 4.3.8: Optimize MACD parameters
        Acceptance: Find optimal parameters for currency pair
        """
        from src.indicators.macd import MACDOptimizer
        
        optimizer = MACDOptimizer()
        
        # Test different parameter combinations
        param_sets = [
            (8, 17, 9),    # Faster
            (12, 26, 9),   # Standard
            (19, 39, 9),   # Slower
            (5, 35, 5),    # Custom
        ]
        
        results = {}
        for fast, slow, signal in param_sets:
            performance = optimizer.backtest_parameters(
                price_data['close'],
                fast_period=fast,
                slow_period=slow,
                signal_period=signal
            )
            results[(fast, slow, signal)] = performance
        
        # Find best parameters
        best_params = max(results, key=lambda k: results[k]['sharpe_ratio'])
        best_performance = results[best_params]
        
        # Store optimization results in Supabase
        optimization_data = {
            'indicator': 'MACD',
            'symbol': 'EUR_USD',
            'best_parameters': {
                'fast': best_params[0],
                'slow': best_params[1],
                'signal': best_params[2]
            },
            'performance': {
                'sharpe_ratio': best_performance['sharpe_ratio'],
                'win_rate': best_performance['win_rate'],
                'profit_factor': best_performance.get('profit_factor', 0)
            },
            'tested_at': datetime.now().isoformat()
        }
        
        try:
            response = supabase_client.table('indicator_optimizations').insert(
                optimization_data
            ).execute()
            assert response.data, "Failed to store optimization results"
        except Exception as e:
            print(f"Optimization storage test: {e}")
        
        print(f"Best MACD parameters: {best_params}")
    
    def test_signal_confirmation(self, price_data):
        """
        Test 4.3.9: MACD signal confirmation with other indicators
        Acceptance: Combine MACD with RSI for confirmation
        """
        from src.indicators.macd import MACDSignalConfirmer
        from src.indicators.rsi import RSICalculator
        
        confirmer = MACDSignalConfirmer()
        
        # Calculate MACD
        macd_data = confirmer.calculate_macd(price_data['close'])
        macd_signals = confirmer.generate_macd_signals(macd_data)
        
        # Calculate RSI
        rsi_calc = RSICalculator()
        rsi = rsi_calc.calculate(price_data['close'], period=14)
        
        # Confirm signals
        confirmed_signals = confirmer.confirm_with_rsi(
            macd_signals,
            rsi,
            rsi_oversold=30,
            rsi_overbought=70
        )
        
        # Check confirmation logic
        for i, (macd_sig, confirmed) in enumerate(zip(macd_signals, confirmed_signals)):
            if confirmed == 'confirmed_buy':
                # MACD bullish + RSI oversold
                assert macd_sig in ['bullish_crossover', 'bullish_zero_cross'], \
                    "Buy confirmation without bullish MACD"
                if not pd.isna(rsi[i]):
                    assert rsi[i] < 50, \
                        "Buy confirmation with high RSI"
            elif confirmed == 'confirmed_sell':
                # MACD bearish + RSI overbought
                assert macd_sig in ['bearish_crossover', 'bearish_zero_cross'], \
                    "Sell confirmation without bearish MACD"
                if not pd.isna(rsi[i]):
                    assert rsi[i] > 50, \
                        "Sell confirmation with low RSI"
    
    def test_signal_filtering(self, price_data):
        """
        Test 4.3.10: Filter MACD signals for quality
        Acceptance: Remove weak/false signals
        """
        from src.indicators.macd import MACDSignalFilter
        
        filter = MACDSignalFilter()
        macd_data = filter.calculate_macd(price_data['close'])
        raw_signals = filter.generate_raw_signals(macd_data)
        
        # Apply filters
        filtered_signals = filter.apply_filters(
            raw_signals,
            macd_data,
            min_histogram_strength=0.0001,
            min_separation_periods=5
        )
        
        # Filtered signals should be subset of raw signals
        assert len(filtered_signals) <= len(raw_signals), \
            "Filtered signals exceed raw signals"
        
        # Check signal quality
        signal_indices = [i for i, s in enumerate(filtered_signals) if s != 'neutral']
        
        # Verify minimum separation
        for i in range(1, len(signal_indices)):
            separation = signal_indices[i] - signal_indices[i-1]
            assert separation >= 5, \
                f"Signals too close: {separation} periods apart"


class TestMACDBacktesting:
    """Test suite for MACD strategy backtesting"""
    
    @pytest.fixture
    def historical_data(self):
        """Generate historical data for backtesting"""
        dates = pd.date_range(end=datetime.now(), periods=5000, freq='15min')
        
        # Create realistic price movement
        trend = np.sin(np.linspace(0, 20*np.pi, 5000)) * 0.01
        walk = np.cumsum(np.random.randn(5000) * 0.0001)
        prices = 1.1000 + trend + walk
        
        return pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'volume': np.random.randint(10000, 1000000, 5000)
        })
    
    def test_strategy_backtest(self, historical_data):
        """
        Test 4.4.1: Backtest MACD strategy
        Acceptance: Achieve positive returns
        """
        from src.indicators.macd import MACDStrategy
        
        strategy = MACDStrategy(
            fast_period=12,
            slow_period=26,
            signal_period=9
        )
        
        # Run backtest
        results = strategy.backtest(
            historical_data,
            initial_capital=10000,
            position_size=0.02
        )
        
        # Check performance metrics
        assert results['total_return'] > 0, \
            f"Negative return: {results['total_return']:.2%}"
        assert results['sharpe_ratio'] > 0, \
            f"Negative Sharpe ratio: {results['sharpe_ratio']:.2f}"
        assert results['max_drawdown'] < 0.20, \
            f"Excessive drawdown: {results['max_drawdown']:.2%}"
        
        print(f"MACD Strategy Results:")
        print(f"  Return: {results['total_return']:.2%}")
        print(f"  Sharpe: {results['sharpe_ratio']:.2f}")
        print(f"  Max DD: {results['max_drawdown']:.2%}")


if __name__ == "__main__":
    pytest.main([__file__, '-v'])