"""
Test Suite for Supabase TimescaleDB Infrastructure Setup
Following TDD methodology for forex bot targeting 25% annual returns
"""
import asyncio
import pytest
import pytest_asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import numpy as np
from dotenv import load_dotenv

load_dotenv()


class TestSupabaseTimescaleSetup:
    """
    Test suite for validating Supabase with TimescaleDB extension setup
    Critical for handling high-frequency forex data (6 pairs, multiple timeframes)
    """
    
    @pytest_asyncio.fixture
    async def supabase_client(self):
        """Initialize Supabase client with connection pooling"""
        from src.data.database.supabase_manager import SupabaseManager
        
        manager = SupabaseManager(
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_ANON_KEY'),
            service_key=os.getenv('SUPABASE_SERVICE_KEY')
        )
        yield manager
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_supabase_connection(self, supabase_client):
        """
        Test 1.1.1: Verify successful connection to Supabase
        Acceptance: Connection established with valid credentials
        """
        assert await supabase_client.health_check(), \
            "Failed to establish Supabase connection"
        
        connection_info = await supabase_client.get_connection_info()
        assert connection_info['status'] == 'connected'
        assert connection_info['latency_ms'] < 100  # Sub-100ms latency required
    
    @pytest.mark.asyncio
    async def test_timescaledb_extension_enabled(self, supabase_client):
        """
        Test 1.1.2: Verify TimescaleDB extension is active
        Acceptance: TimescaleDB extension enabled and functional
        """
        extensions = await supabase_client.get_extensions()
        assert 'timescaledb' in extensions, \
            "TimescaleDB extension not found in database"
        
        # Verify version is recent enough for our requirements
        timescale_version = await supabase_client.get_timescale_version()
        assert timescale_version >= '2.10.0', \
            f"TimescaleDB version {timescale_version} too old, need >= 2.10.0"
    
    @pytest.mark.asyncio
    async def test_create_hypertables_schema(self, supabase_client):
        """
        Test 1.1.3: Create optimized hypertables for forex time-series data
        Acceptance: All required tables created with proper structure
        """
        tables_config = {
            'forex_prices': {
                'columns': {
                    'timestamp': 'TIMESTAMPTZ NOT NULL',
                    'symbol': 'VARCHAR(10) NOT NULL',
                    'bid': 'DECIMAL(18,5) NOT NULL',
                    'ask': 'DECIMAL(18,5) NOT NULL',
                    'spread': 'DECIMAL(10,5) GENERATED ALWAYS AS (ask - bid) STORED',
                    'volume': 'BIGINT',
                    'timeframe': 'VARCHAR(10)'
                },
                'partition_by': 'timestamp',
                'chunk_interval': '1 day'
            },
            'economic_calendar': {
                'columns': {
                    'timestamp': 'TIMESTAMPTZ NOT NULL',
                    'currency': 'VARCHAR(3) NOT NULL',
                    'event': 'TEXT NOT NULL',
                    'impact': 'VARCHAR(10)',
                    'actual': 'DECIMAL(10,2)',
                    'forecast': 'DECIMAL(10,2)',
                    'previous': 'DECIMAL(10,2)'
                },
                'partition_by': 'timestamp',
                'chunk_interval': '1 week'
            },
            'ml_predictions': {
                'columns': {
                    'timestamp': 'TIMESTAMPTZ NOT NULL',
                    'symbol': 'VARCHAR(10) NOT NULL',
                    'model_type': 'VARCHAR(20) NOT NULL',
                    'prediction': 'DECIMAL(18,5) NOT NULL',
                    'confidence': 'DECIMAL(5,4) NOT NULL',
                    'features_hash': 'VARCHAR(64)',
                    'timeframe': 'VARCHAR(10)'
                },
                'partition_by': 'timestamp',
                'chunk_interval': '1 day'
            },
            'trading_signals': {
                'columns': {
                    'timestamp': 'TIMESTAMPTZ NOT NULL',
                    'symbol': 'VARCHAR(10) NOT NULL',
                    'signal_type': 'VARCHAR(20) NOT NULL',
                    'strength': 'DECIMAL(5,4) NOT NULL',
                    'indicators_used': 'JSONB',
                    'ml_confidence': 'DECIMAL(5,4)',
                    'expected_pips': 'INTEGER'
                },
                'partition_by': 'timestamp',
                'chunk_interval': '1 day'
            },
            'portfolio_positions': {
                'columns': {
                    'timestamp': 'TIMESTAMPTZ NOT NULL',
                    'position_id': 'UUID DEFAULT gen_random_uuid()',
                    'symbol': 'VARCHAR(10) NOT NULL',
                    'position_size': 'DECIMAL(18,2) NOT NULL',
                    'entry_price': 'DECIMAL(18,5) NOT NULL',
                    'stop_loss': 'DECIMAL(18,5)',
                    'take_profit': 'DECIMAL(18,5)',
                    'status': 'VARCHAR(20) DEFAULT \'open\'',
                    'kelly_percentage': 'DECIMAL(5,4)',
                    'risk_amount': 'DECIMAL(18,2)'
                },
                'partition_by': 'timestamp',
                'chunk_interval': '1 week'
            }
        }
        
        for table_name, config in tables_config.items():
            result = await supabase_client.create_hypertable(
                table_name=table_name,
                **config
            )
            assert result['success'], f"Failed to create hypertable {table_name}"
            
            # Verify indexes are created
            indexes = await supabase_client.get_table_indexes(table_name)
            assert f'idx_{table_name}_timestamp_symbol' in indexes
    
    @pytest.mark.asyncio
    async def test_data_insertion_performance(self, supabase_client):
        """
        Test 1.1.4: Verify high-speed data insertion capability
        Acceptance: Insert >10K records in <5 seconds
        """
        # Generate test data for 6 forex pairs
        forex_pairs = ['USD/ZAR', 'GBP/JPY', 'AUD/JPY', 'USD/TRY', 'NZD/JPY', 'EUR/USD']
        timeframes = ['5min', '15min', '1H', '4H', 'Daily']
        
        test_data = []
        base_time = datetime.utcnow() - timedelta(hours=24)
        
        for i in range(10000):
            test_data.append({
                'timestamp': base_time + timedelta(seconds=i),
                'symbol': forex_pairs[i % len(forex_pairs)],
                'bid': np.random.uniform(0.5, 200.0),
                'ask': np.random.uniform(0.5, 200.0),
                'volume': np.random.randint(1000, 100000),
                'timeframe': timeframes[i % len(timeframes)]
            })
        
        start_time = asyncio.get_event_loop().time()
        result = await supabase_client.batch_insert('forex_prices', test_data)
        elapsed = asyncio.get_event_loop().time() - start_time
        
        assert result['rows_inserted'] == 10000, \
            f"Expected 10000 rows inserted, got {result['rows_inserted']}"
        assert elapsed < 5.0, \
            f"Insertion took {elapsed:.2f}s, exceeds 5s limit"
    
    @pytest.mark.asyncio
    async def test_aggregation_query_performance(self, supabase_client):
        """
        Test 1.1.5: Verify OHLC aggregation performance
        Acceptance: Daily OHLC queries complete in <500ms
        """
        # Test OHLC aggregation for each pair
        forex_pairs = ['USD/ZAR', 'GBP/JPY', 'AUD/JPY', 'USD/TRY', 'NZD/JPY', 'EUR/USD']
        
        for symbol in forex_pairs:
            start_time = asyncio.get_event_loop().time()
            
            ohlc_data = await supabase_client.get_ohlc(
                symbol=symbol,
                timeframe='Daily',
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow()
            )
            
            elapsed = (asyncio.get_event_loop().time() - start_time) * 1000  # Convert to ms
            
            assert elapsed < 500, \
                f"OHLC query for {symbol} took {elapsed:.0f}ms, exceeds 500ms limit"
            assert len(ohlc_data) > 0, f"No OHLC data returned for {symbol}"
    
    @pytest.mark.asyncio
    async def test_data_retention_policies(self, supabase_client):
        """
        Test 1.1.6: Verify data retention and compression policies
        Acceptance: Proper retention (2 years) and compression (7 days) configured
        """
        policies = await supabase_client.get_retention_policies()
        
        assert policies['forex_prices']['retention_days'] == 730, \
            "Forex prices retention should be 730 days (2 years)"
        assert policies['forex_prices']['compression_after_days'] == 7, \
            "Compression should occur after 7 days"
        assert policies['trading_signals']['retention_days'] == 30, \
            "Trading signals should retain for 30 days"
    
    @pytest.mark.asyncio
    async def test_row_level_security(self, supabase_client):
        """
        Test 1.1.7: Verify Row Level Security (RLS) configuration
        Acceptance: RLS enabled for data isolation
        """
        rls_status = await supabase_client.get_rls_status()
        
        critical_tables = ['portfolio_positions', 'trading_signals']
        for table in critical_tables:
            assert rls_status[table]['enabled'], \
                f"RLS must be enabled for {table}"
            assert len(rls_status[table]['policies']) > 0, \
                f"No RLS policies defined for {table}"
    
    @pytest.mark.asyncio
    async def test_connection_pooling(self, supabase_client):
        """
        Test 1.1.8: Verify connection pooling for API scalability
        Acceptance: Support multiple concurrent connections
        """
        # Simulate concurrent API connections
        concurrent_tasks = []
        for i in range(20):  # Test with 20 concurrent connections
            task = supabase_client.health_check()
            concurrent_tasks.append(task)
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if r is True)
        assert successful == 20, \
            f"Only {successful}/20 concurrent connections succeeded"
    
    @pytest.mark.asyncio
    async def test_backup_configuration(self, supabase_client):
        """
        Test 1.1.9: Verify automated backup configuration
        Acceptance: Daily backups configured and accessible
        """
        backup_config = await supabase_client.get_backup_configuration()
        
        assert backup_config['enabled'], "Automated backups not enabled"
        assert backup_config['frequency'] == 'daily', \
            "Backup frequency should be daily"
        assert backup_config['retention_days'] >= 7, \
            "Backup retention should be at least 7 days"
        
        # Verify last backup was recent
        last_backup = await supabase_client.get_last_backup_time()
        hours_since_backup = (datetime.utcnow() - last_backup).total_seconds() / 3600
        assert hours_since_backup < 25, \
            f"Last backup was {hours_since_backup:.1f} hours ago, should be <25 hours"
    
    @pytest.mark.asyncio
    async def test_monitoring_alerts(self, supabase_client):
        """
        Test 1.1.10: Verify performance monitoring and alerting
        Acceptance: Alerts configured for latency >1s
        """
        alert_config = await supabase_client.get_alert_configuration()
        
        assert alert_config['latency_threshold_ms'] == 1000, \
            "Latency alert threshold should be 1000ms"
        assert alert_config['error_rate_threshold'] == 0.01, \
            "Error rate threshold should be 1%"
        assert len(alert_config['notification_channels']) > 0, \
            "No notification channels configured for alerts"


class TestDataPartitioning:
    """Test suite for TimescaleDB partitioning strategies"""
    
    @pytest.mark.asyncio
    async def test_daily_partitioning_forex_prices(self, supabase_client):
        """
        Test 1.2.1: Verify daily partitioning for price data
        Acceptance: Chunks created per day for efficient querying
        """
        chunk_info = await supabase_client.get_chunk_info('forex_prices')
        
        assert chunk_info['chunk_interval'] == '1 day', \
            "Forex prices should be partitioned daily"
        assert chunk_info['total_chunks'] > 0, \
            "No chunks created for forex_prices"
        assert chunk_info['avg_chunk_size_mb'] < 1000, \
            "Chunk size exceeds 1GB, consider smaller intervals"
    
    @pytest.mark.asyncio
    async def test_continuous_aggregates(self, supabase_client):
        """
        Test 1.2.2: Verify continuous aggregates for performance
        Acceptance: Real-time OHLC aggregates maintained
        """
        aggregates = await supabase_client.get_continuous_aggregates()
        
        expected_aggregates = [
            'forex_prices_5min_ohlc',
            'forex_prices_15min_ohlc',
            'forex_prices_1h_ohlc',
            'forex_prices_4h_ohlc',
            'forex_prices_daily_ohlc'
        ]
        
        for agg_name in expected_aggregates:
            assert agg_name in aggregates, \
                f"Missing continuous aggregate: {agg_name}"
            assert aggregates[agg_name]['refresh_policy'] == 'real_time', \
                f"{agg_name} should have real-time refresh policy"


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])