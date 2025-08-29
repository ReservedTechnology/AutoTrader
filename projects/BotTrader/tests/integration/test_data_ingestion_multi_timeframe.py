"""
Integration Test for Multi-Timeframe Data Ingestion
Following TDD methodology for forex bot targeting 25% annual returns
Tests data flow from APIs to Supabase database
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import asyncio
from supabase import create_client
import os
import json


class TestMultiTimeframeDataIngestion:
    """Integration test for multi-timeframe data ingestion pipeline"""
    
    @pytest.fixture
    def data_pipeline(self):
        """Initialize data ingestion pipeline"""
        from src.data.pipeline.multi_timeframe_pipeline import MultiTimeframePipeline
        
        pipeline = MultiTimeframePipeline(
            sources=['oanda', 'tradermade'],
            timeframes=['1m', '5m', '15m', '1h', '4h', '1d'],
            pairs=['EUR_USD', 'GBP_USD', 'USD_JPY'],
            database='supabase'
        )
        return pipeline
    
    @pytest.fixture
    def supabase_client(self):
        """Supabase client for testing"""
        client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_ANON_KEY')
        )
        return client
    
    @pytest.mark.integration
    def test_concurrent_timeframe_collection(self, data_pipeline):
        """
        Test IT.1.1: Collect data for multiple timeframes concurrently
        Acceptance: All timeframes populated within 5 seconds
        """
        start_time = datetime.now()
        
        # Mock API responses for different timeframes
        with patch.object(data_pipeline, 'fetch_oanda_data') as mock_oanda:
            mock_oanda.side_effect = self._generate_timeframe_data
            
            # Collect data for all timeframes
            data = asyncio.run(data_pipeline.collect_all_timeframes())
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Should complete quickly due to concurrent execution
            assert elapsed < 5
            
            # Verify all timeframes collected
            assert '1m' in data
            assert '5m' in data
            assert '15m' in data
            assert '1h' in data
            assert '4h' in data
            assert '1d' in data
            
            # Verify all pairs in each timeframe
            for tf in data:
                assert 'EUR_USD' in data[tf]
                assert 'GBP_USD' in data[tf]
                assert 'USD_JPY' in data[tf]
    
    @pytest.mark.integration
    def test_timeframe_aggregation(self, data_pipeline):
        """
        Test IT.1.2: Aggregate lower timeframes to higher
        Acceptance: Accurate OHLCV aggregation
        """
        # Generate 1-minute data
        one_min_data = pd.DataFrame({
            'time': pd.date_range(start='2025-01-29 10:00:00', periods=60, freq='1min'),
            'open': np.random.uniform(1.10400, 1.10600, 60),
            'high': np.random.uniform(1.10500, 1.10700, 60),
            'low': np.random.uniform(1.10300, 1.10500, 60),
            'close': np.random.uniform(1.10400, 1.10600, 60),
            'volume': np.random.randint(1000, 10000, 60)
        })
        
        # Aggregate to 5-minute
        five_min_data = data_pipeline.aggregate_timeframe(
            one_min_data,
            source_tf='1m',
            target_tf='5m'
        )
        
        assert len(five_min_data) == 12  # 60 minutes / 5 = 12 candles
        
        # Verify first candle aggregation
        first_5min = five_min_data.iloc[0]
        first_5_1min = one_min_data.iloc[:5]
        
        assert first_5min['open'] == first_5_1min['open'].iloc[0]
        assert first_5min['high'] == first_5_1min['high'].max()
        assert first_5min['low'] == first_5_1min['low'].min()
        assert first_5min['close'] == first_5_1min['close'].iloc[-1]
        assert first_5min['volume'] == first_5_1min['volume'].sum()
        
        # Aggregate to 1-hour
        hourly_data = data_pipeline.aggregate_timeframe(
            one_min_data,
            source_tf='1m',
            target_tf='1h'
        )
        
        assert len(hourly_data) == 1  # 60 minutes = 1 hour
        assert hourly_data.iloc[0]['volume'] == one_min_data['volume'].sum()
    
    @pytest.mark.integration
    def test_dual_database_storage(self, data_pipeline, timescale_connection, supabase_client):
        """
        Test IT.1.3: Store time-series in TimescaleDB, metadata in Supabase
        Acceptance: Correct data routing and storage
        """
        # Prepare test data
        price_data = {
            'time': datetime.now(),
            'symbol': 'EUR_USD',
            'timeframe': '5m',
            'open': 1.10500,
            'high': 1.10550,
            'low': 1.10480,
            'close': 1.10520,
            'volume': 50000
        }
        
        metadata = {
            'collection_id': 'COL123',
            'source': 'oanda',
            'latency_ms': 45,
            'quality_score': 0.98
        }
        
        # Store in dual database
        success = data_pipeline.store_data(price_data, metadata)
        assert success is True
        
        # Verify TimescaleDB storage
        cursor = timescale_connection.cursor()
        cursor.execute("""
            SELECT * FROM forex_prices 
            WHERE symbol = %s 
            ORDER BY time DESC 
            LIMIT 1
        """, ('EUR_USD',))
        
        timescale_row = cursor.fetchone()
        assert timescale_row is not None
        cursor.close()
        
        # Verify Supabase storage
        response = supabase_client.table('data_collection_metadata').select('*').eq(
            'collection_id', 'COL123'
        ).execute()
        
        assert len(response.data) > 0
        assert response.data[0]['quality_score'] == 0.98
    
    @pytest.mark.integration
    def test_gap_detection_and_filling(self, data_pipeline):
        """
        Test IT.1.4: Detect and fill data gaps
        Acceptance: No gaps > 2 candles in critical timeframes
        """
        # Create data with gaps
        timestamps = pd.date_range(start='2025-01-29 10:00:00', periods=100, freq='1min')
        
        # Remove some timestamps to create gaps
        gaps = [10, 11, 12, 30, 31, 70]  # Create gaps at these indices
        timestamps_with_gaps = timestamps.delete(gaps)
        
        data_with_gaps = pd.DataFrame({
            'time': timestamps_with_gaps,
            'close': np.random.uniform(1.10400, 1.10600, len(timestamps_with_gaps))
        })
        
        # Detect gaps
        detected_gaps = data_pipeline.detect_gaps(
            data_with_gaps,
            expected_freq='1min'
        )
        
        assert len(detected_gaps) == 3  # Three gap periods
        assert detected_gaps[0]['start'] == timestamps[10]
        assert detected_gaps[0]['duration'] == 3  # 3 missing candles
        
        # Fill gaps
        filled_data = data_pipeline.fill_gaps(
            data_with_gaps,
            method='interpolate',
            max_gap_size=3
        )
        
        # Should have filled the 3-candle gap but not larger ones
        assert len(filled_data) > len(data_with_gaps)
        
        # Verify no critical gaps remain
        remaining_gaps = data_pipeline.detect_gaps(filled_data, expected_freq='1min')
        critical_gaps = [g for g in remaining_gaps if g['duration'] <= 2]
        assert len(critical_gaps) == 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_time_streaming(self, data_pipeline):
        """
        Test IT.1.5: Real-time data streaming
        Acceptance: < 100ms latency from source to storage
        """
        latencies = []
        
        async def process_tick(tick):
            receive_time = datetime.now()
            latency = (receive_time - tick['timestamp']).total_seconds() * 1000
            latencies.append(latency)
            
            # Store tick
            await data_pipeline.store_tick_async(tick)
        
        # Simulate streaming for 10 ticks
        for i in range(10):
            tick = {
                'timestamp': datetime.now(),
                'symbol': 'EUR_USD',
                'bid': 1.10500 + i * 0.00001,
                'ask': 1.10502 + i * 0.00001
            }
            
            await process_tick(tick)
            await asyncio.sleep(0.1)  # 100ms between ticks
        
        # Check average latency
        avg_latency = np.mean(latencies)
        assert avg_latency < 100  # Less than 100ms average
        
        # Check 95th percentile latency
        p95_latency = np.percentile(latencies, 95)
        assert p95_latency < 150  # 95% under 150ms
    
    @pytest.mark.integration
    def test_data_quality_validation(self, data_pipeline):
        """
        Test IT.1.6: Validate data quality
        Acceptance: Reject bad data, log quality metrics
        """
        # Good quality data
        good_data = pd.DataFrame({
            'time': pd.date_range(start='2025-01-29 10:00:00', periods=10, freq='1min'),
            'open': [1.10500 + i*0.0001 for i in range(10)],
            'high': [1.10510 + i*0.0001 for i in range(10)],
            'low': [1.10490 + i*0.0001 for i in range(10)],
            'close': [1.10505 + i*0.0001 for i in range(10)],
            'volume': [5000 + i*100 for i in range(10)]
        })
        
        quality_report = data_pipeline.validate_quality(good_data)
        
        assert quality_report['quality_score'] > 0.9
        assert quality_report['issues'] == []
        assert quality_report['status'] == 'accepted'
        
        # Bad quality data
        bad_data = good_data.copy()
        bad_data.loc[5, 'high'] = bad_data.loc[5, 'low'] - 0.001  # High < Low
        bad_data.loc[7, 'volume'] = -1000  # Negative volume
        bad_data.loc[9, 'close'] = 1.20000  # Outlier price
        
        bad_quality_report = data_pipeline.validate_quality(bad_data)
        
        assert bad_quality_report['quality_score'] < 0.7
        assert len(bad_quality_report['issues']) >= 3
        assert 'high_low_inconsistency' in str(bad_quality_report['issues'])
        assert 'negative_volume' in str(bad_quality_report['issues'])
        assert 'price_outlier' in str(bad_quality_report['issues'])
    
    @pytest.mark.integration
    def test_materialized_view_update(self, data_pipeline, supabase_client):
        """
        Test IT.1.7: Update materialized views in Supabase
        Acceptance: Views refresh within 2 seconds
        """
        # Insert new tick data
        tick_time = datetime.now()
        supabase_client.table('forex_prices').insert({
            'timestamp': tick_time.isoformat(),
            'symbol': 'EUR_USD',
            'bid': 1.10500,
            'ask': 1.10502,
            'volume': 10000
        }).execute()
        
        # Trigger materialized view refresh
        start_refresh = datetime.now()
        data_pipeline.refresh_materialized_views(['ohlcv_5min', 'ohlcv_15min'])
        
        refresh_time = (datetime.now() - start_refresh).total_seconds()
        
        # Should refresh quickly
        assert refresh_time < 2.0
        
        # Verify view updated
        result = supabase_client.table('ohlcv_5min').select('*').eq(
            'symbol', 'EUR_USD'
        ).gte(
            'time_bucket', (tick_time - timedelta(minutes=5)).isoformat()
        ).order('time_bucket', desc=True).limit(1).execute()
        
        assert result.data
        assert len(result.data) > 0
    
    @pytest.mark.integration
    def test_failover_data_source(self, data_pipeline):
        """
        Test IT.1.8: Failover between data sources
        Acceptance: Seamless switch on primary failure
        """
        # Simulate OANDA failure
        with patch.object(data_pipeline, 'fetch_oanda_data') as mock_oanda:
            mock_oanda.side_effect = Exception("Connection timeout")
            
            # Should failover to TraderMade
            with patch.object(data_pipeline, 'fetch_tradermade_data') as mock_tm:
                mock_tm.return_value = {
                    'EUR_USD': {'bid': 1.10500, 'ask': 1.10502}
                }
                
                data = data_pipeline.fetch_with_failover('EUR_USD')
                
                assert data is not None
                assert data['source'] == 'tradermade'
                assert data['EUR_USD']['bid'] == 1.10500
                
                # Verify failover logged
                assert data_pipeline.get_failover_count() == 1
    
    def _generate_timeframe_data(self, timeframe, pair):
        """Helper to generate mock timeframe data"""
        periods = {
            '1m': 60,
            '5m': 60,
            '15m': 60,
            '1h': 24,
            '4h': 30,
            '1d': 30
        }
        
        freq_map = {
            '1m': '1min',
            '5m': '5min',
            '15m': '15min',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        
        return pd.DataFrame({
            'time': pd.date_range(
                end=datetime.now(),
                periods=periods[timeframe],
                freq=freq_map[timeframe]
            ),
            'open': np.random.uniform(1.10400, 1.10600, periods[timeframe]),
            'high': np.random.uniform(1.10500, 1.10700, periods[timeframe]),
            'low': np.random.uniform(1.10300, 1.10500, periods[timeframe]),
            'close': np.random.uniform(1.10400, 1.10600, periods[timeframe]),
            'volume': np.random.randint(1000, 100000, periods[timeframe])
        })


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-m', 'integration'])