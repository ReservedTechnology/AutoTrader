"""
Test Suite for Feature Engineering
Following TDD methodology for forex bot targeting 25% annual returns
Tests for technical indicators, market microstructure, and derived features
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import json


class TestTechnicalFeatures:
    """Test suite for technical indicator feature engineering"""
    
    @pytest.fixture
    def price_data(self):
        """Generate sample OHLCV data"""
        dates = pd.date_range(end=datetime.now(), periods=200, freq='5min')
        np.random.seed(42)
        
        # Generate realistic price movement
        returns = np.random.normal(0.0001, 0.001, 200)
        prices = 1.1000 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 - np.random.uniform(0, 0.0002, 200)),
            'high': prices * (1 + np.random.uniform(0, 0.0005, 200)),
            'low': prices * (1 - np.random.uniform(0, 0.0005, 200)),
            'close': prices,
            'volume': np.random.randint(10000, 100000, 200)
        })
        return df
    
    def test_moving_average_features(self, price_data):
        """
        Test 6.1.1: Calculate moving average features
        Acceptance: SMA, EMA, WMA correctly computed
        """
        from src.ml.features.technical_features import MovingAverageFeatures
        
        ma_features = MovingAverageFeatures()
        
        # Calculate different MAs
        features = ma_features.calculate(price_data)
        
        # Check SMA
        assert 'sma_10' in features.columns
        assert 'sma_20' in features.columns
        assert 'sma_50' in features.columns
        
        # Verify SMA calculation
        manual_sma_10 = price_data['close'].rolling(10).mean()
        assert np.allclose(features['sma_10'].dropna(), manual_sma_10.dropna(), rtol=1e-5)
        
        # Check EMA
        assert 'ema_12' in features.columns
        assert 'ema_26' in features.columns
        
        # Check WMA (Weighted Moving Average)
        assert 'wma_10' in features.columns
        
        # Check crossover signals
        assert 'golden_cross' in features.columns  # SMA50 crosses above SMA200
        assert 'death_cross' in features.columns   # SMA50 crosses below SMA200
    
    def test_volatility_features(self, price_data):
        """
        Test 6.1.2: Calculate volatility features
        Acceptance: ATR, Bollinger Bands, realized volatility
        """
        from src.ml.features.volatility_features import VolatilityFeatures
        
        vol_features = VolatilityFeatures()
        features = vol_features.calculate(price_data)
        
        # Check ATR
        assert 'atr_14' in features.columns
        assert all(features['atr_14'].dropna() > 0)
        
        # Check Bollinger Bands
        assert 'bb_upper' in features.columns
        assert 'bb_middle' in features.columns
        assert 'bb_lower' in features.columns
        assert 'bb_width' in features.columns
        assert 'bb_percent' in features.columns
        
        # Verify BB calculation
        sma_20 = price_data['close'].rolling(20).mean()
        std_20 = price_data['close'].rolling(20).std()
        expected_upper = sma_20 + 2 * std_20
        assert np.allclose(features['bb_upper'].dropna(), expected_upper.dropna(), rtol=1e-4)
        
        # Check realized volatility
        assert 'realized_vol_5min' in features.columns
        assert 'realized_vol_hourly' in features.columns
        assert 'realized_vol_daily' in features.columns
        
        # Check Parkinson volatility (using high-low)
        assert 'parkinson_vol' in features.columns
    
    def test_momentum_features(self, price_data):
        """
        Test 6.1.3: Calculate momentum features
        Acceptance: ROC, momentum, acceleration features
        """
        from src.ml.features.momentum_features import MomentumFeatures
        
        mom_features = MomentumFeatures()
        features = mom_features.calculate(price_data)
        
        # Check Rate of Change (ROC)
        assert 'roc_10' in features.columns
        assert 'roc_20' in features.columns
        
        # Check momentum
        assert 'momentum_10' in features.columns
        manual_momentum = price_data['close'] - price_data['close'].shift(10)
        assert np.allclose(features['momentum_10'].dropna(), manual_momentum.dropna(), rtol=1e-5)
        
        # Check acceleration (momentum of momentum)
        assert 'acceleration' in features.columns
        
        # Check TSI (True Strength Index)
        assert 'tsi' in features.columns
        assert all(-100 <= val <= 100 for val in features['tsi'].dropna())
    
    def test_volume_features(self, price_data):
        """
        Test 6.1.4: Calculate volume-based features
        Acceptance: OBV, VWAP, volume profile
        """
        from src.ml.features.volume_features import VolumeFeatures
        
        vol_features = VolumeFeatures()
        features = vol_features.calculate(price_data)
        
        # Check On-Balance Volume (OBV)
        assert 'obv' in features.columns
        
        # Check VWAP
        assert 'vwap' in features.columns
        typical_price = (price_data['high'] + price_data['low'] + price_data['close']) / 3
        expected_vwap = (typical_price * price_data['volume']).cumsum() / price_data['volume'].cumsum()
        assert np.allclose(features['vwap'].dropna(), expected_vwap.dropna(), rtol=1e-4)
        
        # Check volume rate of change
        assert 'volume_roc' in features.columns
        
        # Check Money Flow Index (MFI)
        assert 'mfi' in features.columns
        assert all(0 <= val <= 100 for val in features['mfi'].dropna())
        
        # Check Accumulation/Distribution Line
        assert 'adl' in features.columns


class TestMarketMicrostructure:
    """Test suite for market microstructure features"""
    
    @pytest.fixture
    def tick_data(self):
        """Generate sample tick data"""
        timestamps = pd.date_range(start='2025-01-29 10:00:00', periods=1000, freq='100ms')
        
        # Simulate bid-ask spread
        mid_price = 1.10500
        spread = 0.00002
        
        bids = mid_price - spread/2 + np.cumsum(np.random.normal(0, 0.00001, 1000))
        asks = bids + spread + np.random.uniform(0, 0.00003, 1000)
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'bid': bids,
            'ask': asks,
            'bid_size': np.random.randint(100000, 10000000, 1000),
            'ask_size': np.random.randint(100000, 10000000, 1000)
        })
    
    def test_spread_features(self, tick_data):
        """
        Test 6.2.1: Calculate spread-based features
        Acceptance: Bid-ask spread, effective spread, quoted spread
        """
        from src.ml.features.microstructure_features import SpreadFeatures
        
        spread_features = SpreadFeatures()
        features = spread_features.calculate(tick_data)
        
        # Check raw spread
        assert 'spread' in features.columns
        expected_spread = tick_data['ask'] - tick_data['bid']
        assert np.allclose(features['spread'], expected_spread, rtol=1e-5)
        
        # Check relative spread (percentage)
        assert 'spread_pct' in features.columns
        mid_price = (tick_data['bid'] + tick_data['ask']) / 2
        expected_spread_pct = expected_spread / mid_price * 100
        assert np.allclose(features['spread_pct'], expected_spread_pct, rtol=1e-5)
        
        # Check effective spread (with trades)
        assert 'effective_spread' in features.columns
        
        # Check time-weighted average spread
        assert 'twap_spread' in features.columns
    
    def test_order_flow_features(self, tick_data):
        """
        Test 6.2.2: Calculate order flow imbalance
        Acceptance: Buy/sell pressure, order flow toxicity
        """
        from src.ml.features.orderflow_features import OrderFlowFeatures
        
        of_features = OrderFlowFeatures()
        features = of_features.calculate(tick_data)
        
        # Check order imbalance
        assert 'order_imbalance' in features.columns
        expected_imbalance = (tick_data['bid_size'] - tick_data['ask_size']) / (tick_data['bid_size'] + tick_data['ask_size'])
        assert np.allclose(features['order_imbalance'], expected_imbalance, rtol=1e-5)
        
        # Check volume imbalance
        assert 'volume_imbalance' in features.columns
        
        # Check VPIN (Volume-synchronized Probability of Informed Trading)
        assert 'vpin' in features.columns
        assert all(0 <= val <= 1 for val in features['vpin'].dropna())
        
        # Check Kyle's Lambda (price impact)
        assert 'kyle_lambda' in features.columns
    
    def test_liquidity_features(self, tick_data):
        """
        Test 6.2.3: Calculate liquidity measures
        Acceptance: Depth, resilience, tightness
        """
        from src.ml.features.liquidity_features import LiquidityFeatures
        
        liq_features = LiquidityFeatures()
        features = liq_features.calculate(tick_data)
        
        # Check market depth
        assert 'market_depth' in features.columns
        assert 'depth_imbalance' in features.columns
        
        # Check liquidity ratio
        assert 'liquidity_ratio' in features.columns
        
        # Check Amihud illiquidity
        assert 'amihud_illiquidity' in features.columns
        
        # Check Roll measure (implicit transaction cost)
        assert 'roll_measure' in features.columns


class TestDerivedFeatures:
    """Test suite for derived and composite features"""
    
    @pytest.fixture
    def feature_data(self):
        """Generate sample features"""
        dates = pd.date_range(end=datetime.now(), periods=100, freq='5min')
        
        return pd.DataFrame({
            'timestamp': dates,
            'rsi': np.random.uniform(20, 80, 100),
            'macd': np.random.normal(0, 0.001, 100),
            'atr': np.random.uniform(0.0005, 0.002, 100),
            'volume': np.random.randint(10000, 100000, 100),
            'spread': np.random.uniform(0.00001, 0.00005, 100)
        })
    
    def test_interaction_features(self, feature_data):
        """
        Test 6.3.1: Create interaction features
        Acceptance: Multiplicative and ratio features
        """
        from src.ml.features.interaction_features import InteractionFeatures
        
        interaction = InteractionFeatures()
        features = interaction.calculate(feature_data)
        
        # Check RSI-MACD interaction
        assert 'rsi_macd_interaction' in features.columns
        
        # Check volume-volatility interaction
        assert 'volume_atr_ratio' in features.columns
        expected_ratio = feature_data['volume'] / (feature_data['atr'] * 10000)
        assert np.allclose(features['volume_atr_ratio'], expected_ratio, rtol=1e-4)
        
        # Check spread-volatility ratio
        assert 'spread_atr_ratio' in features.columns
        
        # Polynomial features
        assert 'rsi_squared' in features.columns
        assert 'macd_cubed' in features.columns
    
    def test_lag_features(self, feature_data):
        """
        Test 6.3.2: Create lagged features
        Acceptance: Multiple lag periods for time series
        """
        from src.ml.features.lag_features import LagFeatures
        
        lag_features = LagFeatures()
        features = lag_features.calculate(feature_data, lags=[1, 5, 10, 20])
        
        # Check lagged RSI
        assert 'rsi_lag_1' in features.columns
        assert 'rsi_lag_5' in features.columns
        assert 'rsi_lag_10' in features.columns
        assert 'rsi_lag_20' in features.columns
        
        # Verify lag calculation
        assert np.allclose(features['rsi_lag_1'].dropna(), feature_data['rsi'].shift(1).dropna(), rtol=1e-5)
        
        # Check difference features
        assert 'rsi_diff_1' in features.columns
        expected_diff = feature_data['rsi'] - feature_data['rsi'].shift(1)
        assert np.allclose(features['rsi_diff_1'].dropna(), expected_diff.dropna(), rtol=1e-5)
        
        # Check rolling statistics
        assert 'rsi_rolling_mean_10' in features.columns
        assert 'rsi_rolling_std_10' in features.columns
    
    def test_cyclical_features(self):
        """
        Test 6.3.3: Create time-based cyclical features
        Acceptance: Hour, day, week encoding
        """
        from src.ml.features.cyclical_features import CyclicalFeatures
        
        # Create time series data
        dates = pd.date_range(start='2025-01-01', end='2025-01-31', freq='1h')
        df = pd.DataFrame({'timestamp': dates})
        
        cyclical = CyclicalFeatures()
        features = cyclical.calculate(df)
        
        # Check hour encoding (sin/cos)
        assert 'hour_sin' in features.columns
        assert 'hour_cos' in features.columns
        assert all(-1 <= val <= 1 for val in features['hour_sin'])
        assert all(-1 <= val <= 1 for val in features['hour_cos'])
        
        # Check day of week encoding
        assert 'dow_sin' in features.columns
        assert 'dow_cos' in features.columns
        
        # Check month encoding
        assert 'month_sin' in features.columns
        assert 'month_cos' in features.columns
        
        # Check trading session indicators
        assert 'london_session' in features.columns  # 08:00-17:00 UTC
        assert 'newyork_session' in features.columns  # 13:00-22:00 UTC
        assert 'tokyo_session' in features.columns    # 00:00-09:00 UTC
        assert 'session_overlap' in features.columns  # When sessions overlap


class TestFeatureSelection:
    """Test suite for feature selection and importance"""
    
    @pytest.fixture
    def feature_matrix(self):
        """Generate feature matrix with target"""
        n_samples = 1000
        n_features = 50
        
        np.random.seed(42)
        X = np.random.randn(n_samples, n_features)
        
        # Create target with some correlation to specific features
        y = (0.5 * X[:, 0] + 0.3 * X[:, 1] + 0.2 * X[:, 5] + 
             0.1 * np.random.randn(n_samples))
        y = (y > 0).astype(int)  # Binary classification
        
        feature_names = [f'feature_{i}' for i in range(n_features)]
        
        return pd.DataFrame(X, columns=feature_names), pd.Series(y, name='target')
    
    def test_correlation_filtering(self, feature_matrix):
        """
        Test 6.4.1: Remove highly correlated features
        Acceptance: Reduces multicollinearity
        """
        from src.ml.features.feature_selection import CorrelationFilter
        
        X, y = feature_matrix
        
        # Add highly correlated features
        X['feature_duplicate'] = X['feature_0'] + np.random.normal(0, 0.01, len(X))
        
        filter = CorrelationFilter(threshold=0.95)
        X_filtered = filter.fit_transform(X)
        
        assert X_filtered.shape[1] < X.shape[1]
        assert 'feature_duplicate' not in X_filtered.columns or 'feature_0' not in X_filtered.columns
        
        # Check correlation matrix of filtered features
        corr_matrix = X_filtered.corr().abs()
        upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        assert all(upper_tri.max() < 0.95)
    
    def test_mutual_information(self, feature_matrix):
        """
        Test 6.4.2: Calculate mutual information scores
        Acceptance: Identifies informative features
        """
        from src.ml.features.feature_selection import MutualInformationSelector
        
        X, y = feature_matrix
        
        selector = MutualInformationSelector(n_features=10)
        X_selected = selector.fit_transform(X, y)
        
        assert X_selected.shape[1] == 10
        
        # Most important features should be selected
        assert 'feature_0' in X_selected.columns  # Highest correlation
        assert 'feature_1' in X_selected.columns  # Second highest
        
        # Get feature scores
        scores = selector.get_feature_scores()
        assert len(scores) == X.shape[1]
        assert scores['feature_0'] > scores['feature_10']  # Random feature
    
    def test_recursive_feature_elimination(self, feature_matrix):
        """
        Test 6.4.3: RFE with cross-validation
        Acceptance: Optimal feature subset selection
        """
        from src.ml.features.feature_selection import RFECVSelector
        
        X, y = feature_matrix
        
        selector = RFECVSelector(min_features=5, cv=3)
        X_selected = selector.fit_transform(X, y)
        
        assert X_selected.shape[1] >= 5
        assert X_selected.shape[1] <= X.shape[1]
        
        # Check cross-validation scores
        cv_scores = selector.get_cv_scores()
        assert len(cv_scores) > 0
        assert max(cv_scores) > 0.5  # Better than random
    
    def test_boruta_selection(self, feature_matrix):
        """
        Test 6.4.4: Boruta all-relevant feature selection
        Acceptance: Finds all relevant features
        """
        from src.ml.features.feature_selection import BorutaSelector
        
        X, y = feature_matrix
        
        selector = BorutaSelector(max_iter=100)
        X_selected = selector.fit_transform(X, y)
        
        # Should select relevant features
        assert 'feature_0' in X_selected.columns
        assert 'feature_1' in X_selected.columns
        assert 'feature_5' in X_selected.columns
        
        # Get feature ranking
        ranking = selector.get_feature_ranking()
        assert ranking['feature_0'] == 1  # Confirmed important
        assert ranking['feature_49'] > 1  # Likely rejected


class TestFeaturePipeline:
    """Test suite for complete feature engineering pipeline"""
    
    def test_feature_pipeline_integration(self):
        """
        Test 6.5.1: End-to-end feature pipeline
        Acceptance: Transforms raw data to ML-ready features
        """
        from src.ml.features.feature_pipeline import FeaturePipeline
        
        # Create sample data
        dates = pd.date_range(end=datetime.now(), periods=500, freq='5min')
        prices = 1.1000 + np.cumsum(np.random.normal(0.0001, 0.001, 500))
        
        raw_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.9995,
            'high': prices * 1.0005,
            'low': prices * 0.9995,
            'close': prices,
            'volume': np.random.randint(10000, 100000, 500),
            'bid': prices - 0.00001,
            'ask': prices + 0.00001
        })
        
        # Initialize pipeline
        pipeline = FeaturePipeline()
        
        # Transform data
        features = pipeline.fit_transform(raw_data)
        
        # Check output shape
        assert features.shape[0] > 0
        assert features.shape[1] > 20  # Should have many features
        
        # Check for NaN handling
        assert features.isna().sum().sum() == 0
        
        # Check feature scaling
        assert features.max().max() < 100  # Reasonable scale
        assert features.min().min() > -100
        
        # Get feature importance
        importance = pipeline.get_feature_importance()
        assert len(importance) == features.shape[1]
    
    def test_feature_versioning(self):
        """
        Test 6.5.2: Feature versioning and reproducibility
        Acceptance: Consistent feature generation
        """
        from src.ml.features.feature_pipeline import FeaturePipeline
        
        # Create pipeline with specific configuration
        config = {
            'version': '1.0.0',
            'features': ['technical', 'microstructure', 'derived'],
            'scaling': 'standard',
            'selection': 'mutual_information'
        }
        
        pipeline1 = FeaturePipeline(config=config)
        pipeline2 = FeaturePipeline(config=config)
        
        # Generate sample data
        data = pd.DataFrame({
            'timestamp': pd.date_range(end=datetime.now(), periods=100, freq='5min'),
            'close': 1.1000 + np.cumsum(np.random.normal(0, 0.001, 100)),
            'volume': np.random.randint(10000, 100000, 100)
        })
        
        # Transform with both pipelines
        features1 = pipeline1.fit_transform(data)
        features2 = pipeline2.fit_transform(data)
        
        # Should produce identical results
        assert features1.shape == features2.shape
        assert list(features1.columns) == list(features2.columns)
        assert np.allclose(features1.values, features2.values, rtol=1e-10)


if __name__ == "__main__":
    pytest.main([__file__, '-v'])