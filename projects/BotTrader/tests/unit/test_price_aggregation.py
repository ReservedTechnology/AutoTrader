"""
Test Suite for Price Aggregation
Following TDD methodology for forex bot targeting 25% annual returns
Tests for multi-source price aggregation and best price selection
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import json
import asyncio


class TestPriceAggregator:
    """Test suite for price aggregation from multiple sources"""
    
    @pytest.fixture
    def price_aggregator(self):
        """Initialize price aggregator"""
        from src.data.aggregation.price_aggregator import PriceAggregator
        
        aggregator = PriceAggregator(
            sources=['oanda', 'tradermade', 'alpha_vantage'],
            weights={'oanda': 0.5, 'tradermade': 0.3, 'alpha_vantage': 0.2}
        )
        return aggregator
    
    @pytest.fixture
    def sample_prices(self):
        """Sample prices from different sources"""
        return {
            'oanda': {
                'EUR_USD': {'bid': 1.10500, 'ask': 1.10502, 'timestamp': datetime.now()},
                'GBP_USD': {'bid': 1.25000, 'ask': 1.25003, 'timestamp': datetime.now()}
            },
            'tradermade': {
                'EUR_USD': {'bid': 1.10498, 'ask': 1.10504, 'timestamp': datetime.now()},
                'GBP_USD': {'bid': 1.24998, 'ask': 1.25005, 'timestamp': datetime.now()}
            },
            'alpha_vantage': {
                'EUR_USD': {'bid': 1.10499, 'ask': 1.10503, 'timestamp': datetime.now()},
                'GBP_USD': None  # Source doesn't have this pair
            }
        }
    
    def test_best_bid_ask_selection(self, price_aggregator, sample_prices):
        """
        Test 10.1.1: Select best bid/ask across sources
        Acceptance: Highest bid, lowest ask
        """
        aggregated = price_aggregator.aggregate_best_prices(sample_prices)
        
        # EUR_USD: Best bid = 1.10500 (oanda), Best ask = 1.10502 (oanda)
        assert aggregated['EUR_USD']['bid'] == 1.10500
        assert aggregated['EUR_USD']['ask'] == 1.10502
        assert aggregated['EUR_USD']['bid_source'] == 'oanda'
        assert aggregated['EUR_USD']['ask_source'] == 'oanda'
        
        # GBP_USD: Best bid = 1.25000 (oanda), Best ask = 1.25003 (oanda)
        assert aggregated['GBP_USD']['bid'] == 1.25000
        assert aggregated['GBP_USD']['ask'] == 1.25003
    
    def test_weighted_average_price(self, price_aggregator, sample_prices):
        """
        Test 10.1.2: Calculate weighted average prices
        Acceptance: Weighted by source reliability
        """
        weighted_prices = price_aggregator.calculate_weighted_average(sample_prices)
        
        # EUR_USD weighted bid = 0.5*1.10500 + 0.3*1.10498 + 0.2*1.10499
        expected_bid = (0.5 * 1.10500 + 0.3 * 1.10498 + 0.2 * 1.10499)
        assert abs(weighted_prices['EUR_USD']['bid'] - expected_bid) < 0.00001
        
        # Handle missing sources
        # GBP_USD (no alpha_vantage): Reweight remaining sources
        # New weights: oanda = 0.5/0.8 = 0.625, tradermade = 0.3/0.8 = 0.375
        expected_gbp_bid = (0.625 * 1.25000 + 0.375 * 1.24998)
        assert abs(weighted_prices['GBP_USD']['bid'] - expected_gbp_bid) < 0.00001
    
    def test_outlier_detection(self, price_aggregator):
        """
        Test 10.1.3: Detect and filter price outliers
        Acceptance: Remove anomalous prices
        """
        prices_with_outlier = {
            'oanda': {'EUR_USD': {'bid': 1.10500, 'ask': 1.10502}},
            'tradermade': {'EUR_USD': {'bid': 1.10498, 'ask': 1.10504}},
            'alpha_vantage': {'EUR_USD': {'bid': 1.20000, 'ask': 1.20002}}  # Outlier
        }
        
        filtered = price_aggregator.filter_outliers(
            prices_with_outlier,
            symbol='EUR_USD',
            threshold=3  # 3 standard deviations
        )
        
        # Alpha Vantage should be filtered out
        assert 'alpha_vantage' not in filtered or filtered['alpha_vantage']['EUR_USD'] is None
        assert 'oanda' in filtered
        assert 'tradermade' in filtered
    
    def test_spread_validation(self, price_aggregator):
        """
        Test 10.1.4: Validate bid-ask spreads
        Acceptance: Flag abnormal spreads
        """
        prices = {
            'source1': {'EUR_USD': {'bid': 1.10500, 'ask': 1.10502}},  # Normal 2 pip spread
            'source2': {'EUR_USD': {'bid': 1.10500, 'ask': 1.10600}}   # Abnormal 100 pip spread
        }
        
        validation = price_aggregator.validate_spreads(
            prices,
            max_spread={'EUR_USD': 0.0005}  # 5 pips max
        )
        
        assert validation['source1']['EUR_USD']['valid'] is True
        assert validation['source2']['EUR_USD']['valid'] is False
        assert validation['source2']['EUR_USD']['reason'] == 'Spread too wide'
    
    def test_latency_based_weighting(self, price_aggregator):
        """
        Test 10.1.5: Weight prices by source latency
        Acceptance: Prefer low-latency sources
        """
        prices_with_latency = {
            'oanda': {
                'data': {'EUR_USD': {'bid': 1.10500, 'ask': 1.10502}},
                'latency_ms': 45
            },
            'tradermade': {
                'data': {'EUR_USD': {'bid': 1.10498, 'ask': 1.10504}},
                'latency_ms': 120
            }
        }
        
        # Adjust weights based on latency
        adjusted_weights = price_aggregator.adjust_weights_by_latency(
            prices_with_latency,
            latency_threshold=100
        )
        
        # OANDA should have higher weight due to lower latency
        assert adjusted_weights['oanda'] > adjusted_weights['tradermade']
        assert adjusted_weights['oanda'] > 0.5  # Increased from base weight
    
    @pytest.mark.asyncio
    async def test_async_price_collection(self, price_aggregator):
        """
        Test 10.1.6: Collect prices asynchronously
        Acceptance: Parallel price fetching
        """
        async def mock_fetch_oanda():
            await asyncio.sleep(0.05)
            return {'EUR_USD': {'bid': 1.10500, 'ask': 1.10502}}
        
        async def mock_fetch_tradermade():
            await asyncio.sleep(0.08)
            return {'EUR_USD': {'bid': 1.10498, 'ask': 1.10504}}
        
        start_time = datetime.now()
        prices = await price_aggregator.fetch_all_prices_async(
            [mock_fetch_oanda(), mock_fetch_tradermade()]
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Should complete in ~0.08s (max of individual times), not 0.13s (sum)
        assert elapsed < 0.10
        assert len(prices) == 2
        assert prices[0]['EUR_USD']['bid'] == 1.10500


class TestPriceCache:
    """Test suite for price caching mechanism"""
    
    @pytest.fixture
    def price_cache(self):
        """Initialize price cache"""
        from src.data.aggregation.price_cache import PriceCache
        
        cache = PriceCache(
            ttl_ms=100,  # 100ms TTL for testing
            max_size=1000
        )
        return cache
    
    def test_cache_insertion_retrieval(self, price_cache):
        """
        Test 10.2.1: Cache price data
        Acceptance: Fast retrieval of recent prices
        """
        price_data = {
            'bid': 1.10500,
            'ask': 1.10502,
            'timestamp': datetime.now()
        }
        
        # Insert into cache
        price_cache.set('EUR_USD', price_data)
        
        # Retrieve from cache
        cached = price_cache.get('EUR_USD')
        assert cached is not None
        assert cached['bid'] == 1.10500
        assert cached['ask'] == 1.10502
    
    def test_cache_expiration(self, price_cache):
        """
        Test 10.2.2: Cache TTL expiration
        Acceptance: Stale data removed
        """
        import time
        
        price_cache.set('EUR_USD', {'bid': 1.10500})
        
        # Should be in cache
        assert price_cache.get('EUR_USD') is not None
        
        # Wait for expiration
        time.sleep(0.15)  # 150ms > 100ms TTL
        
        # Should be expired
        assert price_cache.get('EUR_USD') is None
    
    def test_cache_size_limit(self, price_cache):
        """
        Test 10.2.3: Cache size management
        Acceptance: LRU eviction when full
        """
        price_cache.max_size = 3  # Small cache for testing
        
        # Fill cache
        price_cache.set('EUR_USD', {'bid': 1.10500})
        price_cache.set('GBP_USD', {'bid': 1.25000})
        price_cache.set('USD_JPY', {'bid': 110.500})
        
        # Access EUR_USD to make it recently used
        price_cache.get('EUR_USD')
        
        # Add new item (should evict GBP_USD as LRU)
        price_cache.set('AUD_USD', {'bid': 0.75000})
        
        assert price_cache.get('EUR_USD') is not None  # Recently used
        assert price_cache.get('GBP_USD') is None      # Evicted
        assert price_cache.get('USD_JPY') is not None
        assert price_cache.get('AUD_USD') is not None
    
    def test_cache_statistics(self, price_cache):
        """
        Test 10.2.4: Track cache performance
        Acceptance: Monitor hit/miss rates
        """
        # Populate cache
        price_cache.set('EUR_USD', {'bid': 1.10500})
        
        # Cache hits
        price_cache.get('EUR_USD')
        price_cache.get('EUR_USD')
        
        # Cache misses
        price_cache.get('GBP_USD')
        price_cache.get('USD_JPY')
        
        stats = price_cache.get_statistics()
        
        assert stats['hits'] == 2
        assert stats['misses'] == 2
        assert stats['hit_rate'] == 0.5
        assert stats['size'] == 1


class TestSpreadAnalyzer:
    """Test suite for spread analysis"""
    
    @pytest.fixture
    def spread_analyzer(self):
        """Initialize spread analyzer"""
        from src.data.aggregation.spread_analyzer import SpreadAnalyzer
        
        analyzer = SpreadAnalyzer()
        return analyzer
    
    def test_effective_spread_calculation(self, spread_analyzer):
        """
        Test 10.3.1: Calculate effective spread
        Acceptance: Include market impact
        """
        trades = [
            {'price': 1.10503, 'side': 'buy', 'size': 10000},
            {'price': 1.10499, 'side': 'sell', 'size': 10000},
            {'price': 1.10504, 'side': 'buy', 'size': 20000}
        ]
        
        midpoint = 1.10501
        
        effective_spread = spread_analyzer.calculate_effective_spread(
            trades, midpoint
        )
        
        # Effective spread = 2 * |trade_price - midpoint|
        expected = np.mean([
            2 * abs(1.10503 - 1.10501),
            2 * abs(1.10499 - 1.10501),
            2 * abs(1.10504 - 1.10501)
        ])
        
        assert abs(effective_spread - expected) < 0.00001
    
    def test_time_weighted_spread(self, spread_analyzer):
        """
        Test 10.3.2: Time-weighted average spread
        Acceptance: Weight by duration
        """
        spread_history = [
            {'spread': 0.00002, 'duration_s': 30},
            {'spread': 0.00003, 'duration_s': 45},
            {'spread': 0.00001, 'duration_s': 25}
        ]
        
        twas = spread_analyzer.calculate_time_weighted_spread(spread_history)
        
        total_time = 100
        expected = (0.00002 * 30 + 0.00003 * 45 + 0.00001 * 25) / total_time
        
        assert abs(twas - expected) < 0.000001
    
    def test_spread_percentile_analysis(self, spread_analyzer):
        """
        Test 10.3.3: Spread distribution analysis
        Acceptance: Track percentiles for optimization
        """
        spreads = np.random.uniform(0.00001, 0.00005, 1000)
        
        percentiles = spread_analyzer.calculate_spread_percentiles(
            spreads,
            percentiles=[25, 50, 75, 90, 95, 99]
        )
        
        assert percentiles['p50'] == np.median(spreads)
        assert percentiles['p25'] < percentiles['p50'] < percentiles['p75']
        assert percentiles['p99'] > percentiles['p95']


class TestPriceAnomalyDetection:
    """Test suite for price anomaly detection"""
    
    @pytest.fixture
    def anomaly_detector(self):
        """Initialize anomaly detector"""
        from src.data.aggregation.anomaly_detector import PriceAnomalyDetector
        
        detector = PriceAnomalyDetector(
            methods=['zscore', 'isolation_forest', 'mad']
        )
        return detector
    
    def test_zscore_anomaly_detection(self, anomaly_detector):
        """
        Test 10.4.1: Z-score based anomaly detection
        Acceptance: Identify statistical outliers
        """
        prices = pd.Series([
            1.10500, 1.10502, 1.10498, 1.10501, 1.10499,
            1.10503, 1.10497, 1.11000,  # Anomaly
            1.10502, 1.10500
        ])
        
        anomalies = anomaly_detector.detect_zscore_anomalies(
            prices,
            threshold=3
        )
        
        assert len(anomalies) == 1
        assert anomalies[0] == 7  # Index of 1.11000
    
    def test_isolation_forest_detection(self, anomaly_detector):
        """
        Test 10.4.2: Isolation Forest anomaly detection
        Acceptance: ML-based outlier detection
        """
        # Generate normal data with anomalies
        np.random.seed(42)
        normal_data = np.random.normal(1.10500, 0.00005, 100)
        anomalies = [1.11000, 1.10000]  # Clear outliers
        
        data = np.concatenate([normal_data, anomalies])
        np.random.shuffle(data)
        
        detected = anomaly_detector.detect_isolation_forest(
            data,
            contamination=0.02  # Expect 2% anomalies
        )
        
        # Should detect approximately 2% of data as anomalies
        assert len(detected) > 0
        assert len(detected) < 5  # Not too many false positives
    
    def test_mad_anomaly_detection(self, anomaly_detector):
        """
        Test 10.4.3: Median Absolute Deviation detection
        Acceptance: Robust to outliers
        """
        prices = pd.Series([
            1.10500, 1.10502, 1.10498, 1.10501, 1.10499,
            1.20000,  # Extreme outlier
            1.10503, 1.10497, 1.10502, 1.10500
        ])
        
        anomalies = anomaly_detector.detect_mad_anomalies(
            prices,
            threshold=3.5
        )
        
        assert 5 in anomalies  # Should detect the extreme outlier
        assert len(anomalies) == 1  # Only the extreme one
    
    def test_contextual_anomaly_detection(self, anomaly_detector):
        """
        Test 10.4.4: Context-aware anomaly detection
        Acceptance: Consider market conditions
        """
        # Normal spread during regular hours
        regular_prices = {
            'time': datetime(2025, 1, 29, 14, 0),  # 2 PM
            'bid': 1.10500,
            'ask': 1.10502,
            'spread': 0.00002
        }
        
        # Wide spread during off-hours (acceptable)
        offhours_prices = {
            'time': datetime(2025, 1, 29, 2, 0),  # 2 AM
            'bid': 1.10500,
            'ask': 1.10510,
            'spread': 0.00010
        }
        
        # Wide spread during regular hours (anomaly)
        anomaly_prices = {
            'time': datetime(2025, 1, 29, 14, 0),
            'bid': 1.10500,
            'ask': 1.10510,
            'spread': 0.00010
        }
        
        assert not anomaly_detector.is_contextual_anomaly(regular_prices)
        assert not anomaly_detector.is_contextual_anomaly(offhours_prices)
        assert anomaly_detector.is_contextual_anomaly(anomaly_prices)


class TestPriceSmoothing:
    """Test suite for price smoothing algorithms"""
    
    @pytest.fixture
    def price_smoother(self):
        """Initialize price smoother"""
        from src.data.aggregation.price_smoother import PriceSmoother
        
        smoother = PriceSmoother()
        return smoother
    
    def test_exponential_smoothing(self, price_smoother):
        """
        Test 10.5.1: Exponential weighted moving average
        Acceptance: Smooth price series
        """
        prices = pd.Series([
            1.10500, 1.10510, 1.10495, 1.10520, 1.10490,
            1.10515, 1.10485, 1.10525, 1.10480, 1.10530
        ])
        
        smoothed = price_smoother.exponential_smoothing(
            prices,
            alpha=0.3  # Smoothing factor
        )
        
        # Smoothed series should have less variance
        assert smoothed.std() < prices.std()
        
        # First value unchanged
        assert smoothed.iloc[0] == prices.iloc[0]
        
        # Check EWMA calculation
        assert smoothed.iloc[1] == prices.iloc[0] * 0.7 + prices.iloc[1] * 0.3
    
    def test_kalman_filter_smoothing(self, price_smoother):
        """
        Test 10.5.2: Kalman filter for price estimation
        Acceptance: Optimal state estimation
        """
        # Noisy price observations
        true_price = 1.10500
        observations = true_price + np.random.normal(0, 0.00005, 100)
        
        filtered = price_smoother.kalman_filter(
            observations,
            process_variance=1e-7,
            measurement_variance=1e-6
        )
        
        # Filtered estimate should converge to true price
        final_estimate = filtered[-1]
        assert abs(final_estimate - true_price) < 0.0001
        
        # Filtered series should be smoother
        assert np.std(filtered) < np.std(observations)
    
    def test_savitzky_golay_filter(self, price_smoother):
        """
        Test 10.5.3: Savitzky-Golay smoothing
        Acceptance: Preserve features while smoothing
        """
        # Create price series with trend
        t = np.linspace(0, 1, 100)
        prices = 1.10500 + 0.001 * t + 0.00005 * np.random.randn(100)
        
        smoothed = price_smoother.savitzky_golay(
            prices,
            window_length=11,
            polyorder=3
        )
        
        # Should preserve trend
        trend_original = np.polyfit(range(len(prices)), prices, 1)[0]
        trend_smoothed = np.polyfit(range(len(smoothed)), smoothed, 1)[0]
        
        assert abs(trend_original - trend_smoothed) < 0.0001
        
        # Should reduce noise
        noise_original = prices - np.polyval(np.polyfit(range(len(prices)), prices, 1), range(len(prices)))
        noise_smoothed = smoothed - np.polyval(np.polyfit(range(len(smoothed)), smoothed, 1), range(len(smoothed)))
        
        assert np.std(noise_smoothed) < np.std(noise_original)


if __name__ == "__main__":
    pytest.main([__file__, '-v'])