"""
Test Suite for Database Manager (Supabase Only)
Following TDD methodology for forex bot targeting 25% annual returns
Tests for single database architecture: Supabase for all data
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import asyncio
import os
from supabase import create_client, Client


class TestSupabaseOnlyManager:
    """Test suite for Supabase-only database manager handling all data"""
    
    @pytest.fixture
    def db_manager(self):
        """Initialize Supabase database manager"""
        from src.data.database.supabase_only_manager import SupabaseOnlyManager
        
        manager = SupabaseOnlyManager(
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_ANON_KEY'),
            service_key=os.getenv('SUPABASE_SERVICE_KEY')
        )
        return manager
    
    def test_initialization(self, db_manager):
        """
        Test 9.1.1: Initialize Supabase connection
        Acceptance: Connection established successfully
        """
        assert db_manager.client is not None
        assert hasattr(db_manager.client, 'table')
        assert hasattr(db_manager.client, 'auth')
        assert hasattr(db_manager.client, 'storage')
        assert hasattr(db_manager.client, 'functions')
    
    @patch('supabase.create_client')
    def test_connection_retry(self, mock_create_client, db_manager):
        """
        Test 9.1.2: Retry logic for Supabase connection
        Acceptance: Retries on failure with backoff
        """
        # Simulate connection failures then success
        mock_create_client.side_effect = [
            Exception("Connection failed"),
            Exception("Connection failed"),
            MagicMock()  # Success on third try
        ]
        
        # Attempt connection with retry
        success = db_manager.connect_with_retry(max_retries=3)
        
        assert success is True
        assert mock_create_client.call_count == 3
    
    def test_time_series_table_creation(self, db_manager):
        """
        Test 9.1.3: Create optimized time-series tables in Supabase
        Acceptance: Tables with proper indexes for time-series data
        """
        with patch.object(db_manager, 'execute_sql') as mock_sql:
            # Create forex prices table with time-series optimizations
            db_manager.create_time_series_table(
                table_name='forex_prices',
                schema={
                    'id': 'BIGSERIAL PRIMARY KEY',
                    'timestamp': 'TIMESTAMPTZ NOT NULL',
                    'symbol': 'VARCHAR(10) NOT NULL',
                    'bid': 'DECIMAL(10, 5)',
                    'ask': 'DECIMAL(10, 5)',
                    'volume': 'INTEGER'
                }
            )
            
            # Verify table creation with indexes
            calls = mock_sql.call_args_list
            create_table_sql = calls[0][0][0]
            
            assert 'CREATE TABLE IF NOT EXISTS forex_prices' in create_table_sql
            assert 'timestamp TIMESTAMPTZ NOT NULL' in create_table_sql
            
            # Should create indexes for time-series queries
            assert any('CREATE INDEX' in str(call) for call in calls)
            assert any('timestamp' in str(call) for call in calls)
            assert any('symbol, timestamp' in str(call) for call in calls)
    
    @pytest.mark.asyncio
    async def test_parallel_queries(self, db_manager):
        """
        Test 9.1.4: Execute parallel queries in Supabase
        Acceptance: Concurrent access to different tables
        """
        # Define parallel queries
        tasks = [
            db_manager.async_query('forex_prices', {'symbol': 'EUR_USD'}),
            db_manager.async_query('user_settings', {'user_id': 'usr_123'}),
            db_manager.async_query('ml_predictions', {'model': 'transformer'})
        ]
        
        with patch.object(db_manager.client, 'table') as mock_table:
            mock_table.return_value.select.return_value.execute.return_value.data = []
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            assert len(results) == 3
            # All queries should complete without errors
            for result in results:
                assert not isinstance(result, Exception)


class TestSupabaseTimeSeriesOperations:
    """Test suite for time-series specific operations in Supabase"""
    
    @pytest.fixture
    def db_manager(self):
        """Initialize database manager"""
        from src.data.database.supabase_manager import SupabaseDatabaseManager
        return SupabaseDatabaseManager(
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_ANON_KEY')
        )
    
    def test_time_partitioning(self, db_manager):
        """
        Test 9.2.1: Create time-partitioned tables in Supabase
        Acceptance: Optimized time-series storage
        """
        with patch.object(db_manager, 'execute_sql') as mock_execute:
            db_manager.create_partitioned_table(
                table_name='forex_prices',
                partition_by='timestamp',
                interval='monthly'
            )
            
            # Verify partitioning SQL
            call_args = mock_execute.call_args[0][0]
            assert 'PARTITION BY RANGE' in call_args
            assert 'timestamp' in call_args
            assert 'forex_prices' in call_args
    
    def test_data_archival(self, db_manager):
        """
        Test 9.2.2: Archive old data to storage
        Acceptance: Move old data to Supabase storage after 7 days
        """
        with patch.object(db_manager.client.storage, 'from_') as mock_storage:
            mock_bucket = MagicMock()
            mock_storage.return_value = mock_bucket
            
            # Archive old data
            success = db_manager.archive_old_data(
                table_name='forex_prices',
                older_than_days=7
            )
            
            assert success is True
            mock_storage.assert_called_with('archived-data')
    
    def test_data_retention(self, db_manager):
        """
        Test 9.2.3: Implement data retention in Supabase
        Acceptance: Auto-delete data older than 2 years
        """
        with patch.object(db_manager, 'execute_sql') as mock_execute:
            db_manager.setup_retention_policy(
                table_name='forex_prices',
                retention_days=730
            )
            
            # Verify retention implementation
            call_args = mock_execute.call_args[0][0]
            assert 'DELETE FROM forex_prices' in call_args
            assert 'timestamp <' in call_args
            assert '730' in call_args or '2 years' in call_args
    
    def test_materialized_views(self, db_manager):
        """
        Test 9.2.4: Create materialized views for OHLCV
        Acceptance: Pre-computed candles for performance
        """
        with patch.object(db_manager, 'execute_sql') as mock_execute:
            db_manager.create_ohlcv_view(
                view_name='ohlcv_5min',
                source_table='forex_prices',
                interval='5 minutes'
            )
            
            # Verify materialized view SQL
            call_args = mock_execute.call_args[0][0]
            assert 'CREATE MATERIALIZED VIEW' in call_args
            assert 'ohlcv_5min' in call_args
            assert 'date_trunc' in call_args
            assert 'GROUP BY' in call_args
    
    def test_batch_insert_performance(self, db_manager):
        """
        Test 9.2.5: Batch insert optimization in Supabase
        Acceptance: Insert 10000+ rows efficiently
        """
        # Generate large dataset
        data = []
        base_time = datetime.now()
        for i in range(10000):
            data.append({
                'timestamp': base_time + timedelta(seconds=i),
                'symbol': 'EUR_USD',
                'bid': 1.10500 + np.random.normal(0, 0.0001),
                'ask': 1.10502 + np.random.normal(0, 0.0001),
                'volume': np.random.randint(1000, 10000)
            })
        
        with patch.object(db_manager.client.table('forex_prices'), 'insert') as mock_insert:
            mock_insert.return_value.execute.return_value = MagicMock()
            
            db_manager.batch_insert('forex_prices', data, batch_size=1000)
            
            # Verify batch inserts were called
            assert mock_insert.call_count == 10  # 10000 rows / 1000 batch size
    
    def test_time_range_query(self, db_manager):
        """
        Test 9.2.6: Optimized time-range queries in Supabase
        Acceptance: Fast retrieval of time-series data
        """
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        
        with patch.object(db_manager.client, 'table') as mock_table:
            mock_query = MagicMock()
            mock_table.return_value.select.return_value = mock_query
            mock_query.gte.return_value = mock_query
            mock_query.lte.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value.data = []
            
            results = db_manager.query_time_range(
                table='forex_prices',
                start_time=start_time,
                end_time=end_time,
                symbol='EUR_USD'
            )
            
            # Verify time range filters were applied
            mock_query.gte.assert_called_with('timestamp', start_time.isoformat())
            mock_query.lte.assert_called_with('timestamp', end_time.isoformat())
            mock_query.eq.assert_called_with('symbol', 'EUR_USD')


class TestSupabaseOperations:
    """Test suite for Supabase-specific operations"""
    
    @pytest.fixture
    def db_manager(self):
        """Initialize Supabase manager"""
        from src.data.database.supabase_only_manager import SupabaseOnlyManager
        
        manager = SupabaseOnlyManager(
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_ANON_KEY'),
            service_key=os.getenv('SUPABASE_SERVICE_KEY')
        )
        return manager
    
    def test_user_authentication(self, db_manager):
        """
        Test 9.3.1: User authentication via Supabase
        Acceptance: Secure user management
        """
        with patch.object(db_manager.client.auth, 'sign_up') as mock_signup:
            mock_signup.return_value.user = Mock(id='usr_123')
            
            user = db_manager.create_user(
                email='trader@example.com',
                password='SecurePass123!'
            )
            
            assert user is not None
            assert user.id == 'usr_123'
            mock_signup.assert_called_once()
    
    def test_realtime_subscriptions(self, db_manager):
        """
        Test 9.3.2: Realtime data subscriptions
        Acceptance: Live updates for configuration changes
        """
        with patch.object(db_manager.client, 'table') as mock_table:
            mock_channel = MagicMock()
            mock_table.return_value.on.return_value = mock_channel
            
            # Subscribe to changes
            channel = db_manager.subscribe_to_changes(
                table='trading_config',
                callback=lambda x: print(x)
            )
            
            assert channel is not None
            mock_table.assert_called_with('trading_config')
    
    def test_row_level_security(self, db_manager):
        """
        Test 9.3.3: Row-level security policies
        Acceptance: Users access only their data
        """
        with patch.object(db_manager, 'execute_sql') as mock_sql:
            db_manager.create_rls_policy(
                table='user_trades',
                policy_name='users_own_trades',
                operation='SELECT',
                check='auth.uid() = user_id'
            )
            
            # Verify RLS policy SQL
            call_args = mock_sql.call_args[0][0]
            assert 'CREATE POLICY' in call_args
            assert 'users_own_trades' in call_args
            assert 'auth.uid()' in call_args
    
    def test_storage_operations(self, db_manager):
        """
        Test 9.3.4: File storage operations
        Acceptance: Store ML models and reports
        """
        with patch.object(db_manager.client.storage, 'from_') as mock_storage:
            mock_bucket = MagicMock()
            mock_storage.return_value = mock_bucket
            mock_bucket.upload.return_value = {'path': 'models/transformer_v1.pkl'}
            
            # Upload model file
            file_path = db_manager.upload_file(
                bucket='ml-models',
                file_name='transformer_v1.pkl',
                file_data=b'model_data'
            )
            
            assert file_path == 'models/transformer_v1.pkl'
            mock_storage.assert_called_with('ml-models')
            mock_bucket.upload.assert_called_once()
    
    def test_edge_functions_trigger(self, db_manager):
        """
        Test 9.3.5: Trigger edge functions
        Acceptance: Serverless function execution
        """
        with patch.object(db_manager.client.functions, 'invoke') as mock_invoke:
            mock_invoke.return_value = {'data': {'result': 'success'}}
            
            result = db_manager.invoke_edge_function(
                function_name='process-trade',
                payload={'trade_id': 'TRD123'}
            )
            
            assert result['result'] == 'success'
            mock_invoke.assert_called_with(
                'process-trade',
                invoke_options={'body': {'trade_id': 'TRD123'}}
            )


class TestDataOptimization:
    """Test suite for data optimization in Supabase"""
    
    @pytest.fixture
    def db_manager(self):
        """Initialize database manager"""
        from src.data.database.supabase_only_manager import SupabaseOnlyManager
        
        manager = SupabaseOnlyManager(
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_ANON_KEY')
        )
        return manager
    
    def test_index_optimization(self, db_manager):
        """
        Test 9.4.1: Optimize indexes for time-series queries
        Acceptance: Fast query performance
        """
        with patch.object(db_manager, 'execute_sql') as mock_sql:
            # Create optimized indexes
            db_manager.optimize_time_series_indexes('forex_prices')
            
            # Verify index creation
            calls = [str(call) for call in mock_sql.call_args_list]
            assert any('CREATE INDEX' in call and 'timestamp' in call for call in calls)
            assert any('CREATE INDEX' in call and 'symbol, timestamp' in call for call in calls)
            assert any('CREATE INDEX' in call and 'BRIN' in call for call in calls)  # BRIN index for time-series
    
    def test_query_performance(self, db_manager):
        """
        Test 9.4.2: Monitor query performance
        Acceptance: Queries complete within SLA
        """
        with patch.object(db_manager, 'execute_sql') as mock_sql:
            mock_sql.return_value = [{'avg_time_ms': 45, 'p95_time_ms': 120}]
            
            performance = db_manager.analyze_query_performance(
                table='forex_prices',
                time_window='1 hour'
            )
            
            assert performance['avg_time_ms'] < 100  # Average under 100ms
            assert performance['p95_time_ms'] < 200  # 95th percentile under 200ms
    
    def test_data_pruning(self, db_manager):
        """
        Test 9.4.3: Prune old data efficiently
        Acceptance: Remove old data without blocking
        """
        with patch.object(db_manager, 'execute_sql') as mock_sql:
            mock_sql.return_value = [{'deleted_rows': 50000}]
            
            result = db_manager.prune_old_data(
                table='forex_prices',
                older_than_days=730,
                batch_size=10000
            )
            
            assert result['deleted_rows'] == 50000
            # Should use batched deletes
            assert mock_sql.call_count >= 5  # 50000 / 10000 = 5 batches
    
    def test_vacuum_operations(self, db_manager):
        """
        Test 9.4.4: Vacuum and analyze tables
        Acceptance: Maintain optimal table performance
        """
        with patch.object(db_manager, 'execute_sql') as mock_sql:
            db_manager.vacuum_and_analyze('forex_prices')
            
            # Verify vacuum and analyze commands
            calls = [call[0][0] for call in mock_sql.call_args_list]
            assert any('VACUUM' in call for call in calls)
            assert any('ANALYZE' in call for call in calls)


class TestSupabasePerformance:
    """Test suite for Supabase performance optimization"""
    
    @pytest.fixture
    def db_manager(self):
        """Initialize database manager"""
        from src.data.database.supabase_only_manager import SupabaseOnlyManager
        
        manager = SupabaseOnlyManager(
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_ANON_KEY')
        )
        return manager
    
    def test_connection_management(self, db_manager):
        """
        Test 9.5.1: Manage Supabase connections efficiently
        Acceptance: Reuse connections and handle rate limits
        """
        # Test connection reuse
        assert db_manager.client is not None
        initial_client = db_manager.client
        
        # Make multiple requests - should reuse same client
        for _ in range(5):
            db_manager.get_client()
        
        assert db_manager.client is initial_client
    
    def test_rate_limit_handling(self, db_manager):
        """
        Test 9.5.2: Handle Supabase rate limits
        Acceptance: Graceful degradation and retry
        """
        with patch.object(db_manager.client.table('test'), 'select') as mock_select:
            # Simulate rate limit error
            mock_select.side_effect = [
                Exception("Rate limit exceeded"),
                MagicMock()  # Success on retry
            ]
            
            result = db_manager.query_with_retry('test', {})
            
            assert result is not None
            assert mock_select.call_count == 2
    
    def test_batch_operations(self, db_manager):
        """
        Test 9.5.3: Optimize batch operations
        Acceptance: Efficient bulk inserts and updates
        """
        data = [{'id': i, 'value': f'test_{i}'} for i in range(1000)]
        
        with patch.object(db_manager.client.table('test'), 'upsert') as mock_upsert:
            mock_upsert.return_value.execute.return_value = MagicMock()
            
            db_manager.batch_upsert('test', data, batch_size=100)
            
            # Should split into 10 batches
            assert mock_upsert.call_count == 10
    
    def test_query_optimization(self, db_manager):
        """
        Test 9.5.4: Optimize query performance
        Acceptance: Use proper filters and limits
        """
        with patch.object(db_manager.client, 'table') as mock_table:
            mock_query = MagicMock()
            mock_table.return_value.select.return_value = mock_query
            
            # Test optimized query with filters
            db_manager.query_optimized(
                table='forex_prices',
                columns=['symbol', 'bid', 'ask'],
                filters={'symbol': 'EUR_USD'},
                limit=1000,
                order_by='timestamp'
            )
            
            # Verify optimization techniques were used
            mock_table.assert_called_with('forex_prices')
            mock_query.eq.assert_called()
            mock_query.limit.assert_called_with(1000)
            mock_query.order.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, '-v'])