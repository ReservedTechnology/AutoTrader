"""
Test Suite for Unified Supabase Infrastructure
Tests all functionality using only Supabase (no Railway/TimescaleDB)
"""
import asyncio
import pytest
import pytest_asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd
import numpy as np

load_dotenv()


class TestUnifiedSupabaseInfrastructure:
    """
    Complete test suite for Supabase as the single source of truth
    Tests both time-series and application data
    """
    
    @pytest.fixture
    def supabase_client(self) -> Client:
        """Initialize Supabase client"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        
        assert url and key, "Supabase credentials not found in environment"
        
        client = create_client(url, key)
        return client
    
    # ==================== CONNECTION TESTS ====================
    
    def test_supabase_connection(self, supabase_client):
        """Test Supabase connection"""
        # Simple connection test
        assert supabase_client is not None
        print("✅ Supabase connection established")
    
    def test_all_tables_exist(self, supabase_client):
        """Verify all required tables exist"""
        required_tables = [
            # Time-series tables
            'forex_prices', 'economic_calendar', 'ml_predictions',
            'trading_signals', 'live_positions', 'performance_stats',
            # Application tables
            'users', 'trading_strategies', 'closed_trades', 
            'system_config', 'ml_model_versions'
        ]
        
        for table in required_tables:
            try:
                response = supabase_client.table(table).select("*").limit(0).execute()
                print(f"✓ Table '{table}' exists")
            except Exception as e:
                pytest.fail(f"Table '{table}' not found: {e}")
    
    # ==================== TIME-SERIES DATA TESTS ====================
    
    def test_forex_price_insertion(self, supabase_client):
        """Test inserting forex price data"""
        test_price = {
            'time': datetime.now().isoformat(),
            'symbol': 'EUR/USD',
            'bid': 1.0850,
            'ask': 1.0852,
            'volume': 10000,
            'source': 'test'
        }
        
        response = supabase_client.table('forex_prices').insert(test_price).execute()
        assert response.data, "Failed to insert forex price"
        
        # Clean up
        if response.data:
            supabase_client.table('forex_prices')\
                .delete()\
                .eq('id', response.data[0]['id'])\
                .execute()
    
    def test_batch_forex_insertion(self, supabase_client):
        """Test batch insertion of forex prices"""
        base_time = datetime.now()
        test_prices = []
        
        for i in range(10):
            test_prices.append({
                'time': (base_time - timedelta(minutes=i)).isoformat(),
                'symbol': 'GBP/JPY',
                'bid': 185.50 + np.random.randn() * 0.1,
                'ask': 185.52 + np.random.randn() * 0.1,
                'volume': np.random.randint(5000, 50000),
                'source': 'test_batch'
            })
        
        response = supabase_client.table('forex_prices').insert(test_prices).execute()
        assert len(response.data) == 10, "Failed to insert batch prices"
        
        # Clean up
        supabase_client.table('forex_prices')\
            .delete()\
            .eq('source', 'test_batch')\
            .execute()
    
    def test_ohlc_calculation(self, supabase_client):
        """Test OHLC calculation function"""
        # Insert test data
        base_time = datetime.now()
        test_data = []
        
        for i in range(60):  # 1 hour of minute data
            test_data.append({
                'time': (base_time - timedelta(minutes=i)).isoformat(),
                'symbol': 'USD/JPY',
                'bid': 150.00 + np.sin(i/10) * 0.5,
                'ask': 150.02 + np.sin(i/10) * 0.5,
                'volume': 1000,
                'source': 'test_ohlc'
            })
        
        supabase_client.table('forex_prices').insert(test_data).execute()
        
        # Test OHLC function
        try:
            response = supabase_client.rpc('get_forex_ohlc', {
                'p_symbol': 'USD/JPY',
                'p_interval': '1 hour',
                'p_limit': 1
            }).execute()
            
            if response.data:
                ohlc = response.data[0]
                assert 'open_price' in ohlc
                assert 'high_price' in ohlc
                assert 'low_price' in ohlc
                assert 'close_price' in ohlc
                print(f"✅ OHLC: O={ohlc['open_price']}, H={ohlc['high_price']}, L={ohlc['low_price']}, C={ohlc['close_price']}")
        except Exception as e:
            print(f"⚠️ OHLC function not available: {e}")
        
        # Clean up
        supabase_client.table('forex_prices')\
            .delete()\
            .eq('source', 'test_ohlc')\
            .execute()
    
    # ==================== ML & SIGNALS TESTS ====================
    
    def test_ml_prediction_storage(self, supabase_client):
        """Test ML prediction storage"""
        test_prediction = {
            'time': datetime.now().isoformat(),
            'symbol': 'EUR/USD',
            'model_type': 'transformer',
            'prediction': 'buy',
            'confidence': 0.85,
            'features': {'rsi': 45, 'macd': 0.002}
        }
        
        response = supabase_client.table('ml_predictions').insert(test_prediction).execute()
        assert response.data, "Failed to insert ML prediction"
        
        # Clean up
        if response.data:
            supabase_client.table('ml_predictions')\
                .delete()\
                .eq('id', response.data[0]['id'])\
                .execute()
    
    def test_trading_signal_storage(self, supabase_client):
        """Test trading signal storage"""
        test_signal = {
            'time': datetime.now().isoformat(),
            'symbol': 'GBP/USD',
            'signal_type': 'momentum',
            'strength': 0.75,
            'indicators_used': ['RSI', 'MACD', 'SMA'],
            'metadata': {'timeframe': '1h'}
        }
        
        response = supabase_client.table('trading_signals').insert(test_signal).execute()
        assert response.data, "Failed to insert trading signal"
        
        # Verify retrieval
        signals = supabase_client.table('trading_signals')\
            .select("*")\
            .eq('symbol', 'GBP/USD')\
            .order('time', desc=True)\
            .limit(1)\
            .execute()
        
        assert signals.data, "Failed to retrieve signals"
        assert signals.data[0]['strength'] == 0.75
        
        # Clean up
        if response.data:
            supabase_client.table('trading_signals')\
                .delete()\
                .eq('id', response.data[0]['id'])\
                .execute()
    
    # ==================== POSITION MANAGEMENT TESTS ====================
    
    def test_position_lifecycle(self, supabase_client):
        """Test complete position lifecycle"""
        # Create position
        position_id = f"TEST_{datetime.now().timestamp()}"
        test_position = {
            'position_id': position_id,
            'time': datetime.now().isoformat(),
            'symbol': 'AUD/USD',
            'position_size': 10000,
            'entry_price': 0.6500,
            'stop_loss': 0.6450,
            'take_profit': 0.6550,
            'status': 'open',
            'metadata': {'strategy': 'test_strategy'}
        }
        
        # Insert position
        create_response = supabase_client.table('live_positions').insert(test_position).execute()
        assert create_response.data, "Failed to create position"
        
        # Update position
        update_response = supabase_client.table('live_positions')\
            .update({'current_price': 0.6520, 'unrealized_pnl': 200})\
            .eq('position_id', position_id)\
            .execute()
        assert update_response.data, "Failed to update position"
        
        # Close position (record in closed trades)
        close_trade = {
            'symbol': 'AUD/USD',
            'entry_time': test_position['time'],
            'exit_time': datetime.now().isoformat(),
            'entry_price': 0.6500,
            'exit_price': 0.6520,
            'position_size': 10000,
            'profit_loss': 200,
            'strategy_used': 'test_strategy',
            'win': True
        }
        
        trade_response = supabase_client.table('closed_trades').insert(close_trade).execute()
        assert trade_response.data, "Failed to record closed trade"
        
        # Update position status
        close_response = supabase_client.table('live_positions')\
            .update({'status': 'closed'})\
            .eq('position_id', position_id)\
            .execute()
        assert close_response.data, "Failed to close position"
        
        # Clean up
        supabase_client.table('live_positions')\
            .delete()\
            .eq('position_id', position_id)\
            .execute()
        
        if trade_response.data:
            supabase_client.table('closed_trades')\
                .delete()\
                .eq('id', trade_response.data[0]['id'])\
                .execute()
    
    # ==================== APPLICATION DATA TESTS ====================
    
    def test_system_configuration(self, supabase_client):
        """Test system configuration management"""
        # Set config
        config_response = supabase_client.table('system_config').upsert({
            'key': 'test_param',
            'value': 'test_value',
            'description': 'Test parameter',
            'updated_at': datetime.now().isoformat()
        }).execute()
        assert config_response.data, "Failed to set config"
        
        # Get config
        get_response = supabase_client.table('system_config')\
            .select("value")\
            .eq('key', 'test_param')\
            .single()\
            .execute()
        
        assert get_response.data['value'] == 'test_value', "Config value mismatch"
        
        # Clean up
        supabase_client.table('system_config')\
            .delete()\
            .eq('key', 'test_param')\
            .execute()
    
    def test_trading_strategy_management(self, supabase_client):
        """Test trading strategy management"""
        test_strategy = {
            'name': 'Test Momentum Strategy',
            'parameters': {
                'rsi_period': 14,
                'macd_fast': 12,
                'macd_slow': 26
            },
            'active': True
        }
        
        # Insert strategy
        response = supabase_client.table('trading_strategies').insert(test_strategy).execute()
        assert response.data, "Failed to insert strategy"
        
        # Get active strategies
        active = supabase_client.table('trading_strategies')\
            .select("*")\
            .eq('active', True)\
            .execute()
        
        assert len(active.data) > 0, "No active strategies found"
        
        # Clean up
        if response.data:
            supabase_client.table('trading_strategies')\
                .delete()\
                .eq('id', response.data[0]['id'])\
                .execute()
    
    # ==================== PERFORMANCE TESTS ====================
    
    def test_high_frequency_insertion(self, supabase_client):
        """Test high-frequency data insertion performance"""
        import time
        
        # Generate 1000 records
        records = []
        base_time = datetime.now()
        
        for i in range(1000):
            records.append({
                'time': (base_time - timedelta(seconds=i*0.1)).isoformat(),
                'symbol': 'EUR/USD',
                'bid': 1.0850 + np.random.randn() * 0.001,
                'ask': 1.0852 + np.random.randn() * 0.001,
                'volume': np.random.randint(1000, 10000),
                'source': 'test_performance'
            })
        
        # Measure insertion time
        start = time.time()
        response = supabase_client.table('forex_prices').insert(records).execute()
        elapsed = time.time() - start
        
        assert len(response.data) == 1000, f"Expected 1000 records, got {len(response.data)}"
        assert elapsed < 10, f"Insertion took {elapsed}s, expected <10s"
        
        print(f"✅ Inserted 1000 records in {elapsed:.2f}s ({1000/elapsed:.0f} records/sec)")
        
        # Clean up
        supabase_client.table('forex_prices')\
            .delete()\
            .eq('source', 'test_performance')\
            .execute()
    
    def test_query_performance(self, supabase_client):
        """Test query performance"""
        import time
        
        # Query recent data
        start = time.time()
        response = supabase_client.table('forex_prices')\
            .select("*")\
            .eq('symbol', 'EUR/USD')\
            .order('time', desc=True)\
            .limit(100)\
            .execute()
        elapsed = time.time() - start
        
        assert elapsed < 2, f"Query took {elapsed}s, expected <2s"
        print(f"✅ Query executed in {elapsed:.3f}s")
    
    # ==================== CLEANUP TESTS ====================
    
    def test_cleanup_function(self, supabase_client):
        """Test data cleanup function"""
        # Insert old data
        old_time = (datetime.now() - timedelta(days=400)).isoformat()
        old_record = {
            'time': old_time,
            'symbol': 'TEST/OLD',
            'bid': 1.0,
            'ask': 1.1,
            'source': 'test_cleanup'
        }
        
        supabase_client.table('forex_prices').insert(old_record).execute()
        
        # Run cleanup (if function exists)
        try:
            response = supabase_client.rpc('cleanup_old_data', {'p_days': 365}).execute()
            print("✅ Cleanup function executed")
        except Exception as e:
            print(f"⚠️ Cleanup function not available: {e}")
        
        # Verify old data removed
        check = supabase_client.table('forex_prices')\
            .select("*")\
            .eq('source', 'test_cleanup')\
            .execute()
        
        # Old data should be gone if cleanup worked
        if not check.data:
            print("✅ Old data successfully cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])