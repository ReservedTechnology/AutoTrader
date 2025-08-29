"""
Database Manager with Hybrid Architecture
TimescaleDB (Railway) for time-series forex data
Supabase for application data and auth
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncpg
from supabase import create_client, Client
import os

logger = logging.getLogger(__name__)


class HybridDatabaseManager:
    """
    Manages connections to both TimescaleDB (Railway) and Supabase
    Optimized data separation for forex trading system
    """
    
    def __init__(self):
        """Initialize both database connections"""
        # TimescaleDB connection for time-series data
        self.timescale_pool: Optional[asyncpg.Pool] = None
        self.timescale_url = os.getenv('DATABASE_URL')  # Railway PostgreSQL
        
        # Supabase connection for application data
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        self.supabase: Optional[Client] = None
        self.supabase_admin: Optional[Client] = None
        
    async def initialize(self):
        """Initialize both database connections"""
        await self._init_timescale()
        await self._init_supabase()
        logger.info("Hybrid database manager initialized")
    
    async def _init_timescale(self):
        """Initialize TimescaleDB connection pool"""
        if self.timescale_url:
            try:
                self.timescale_pool = await asyncpg.create_pool(
                    self.timescale_url,
                    min_size=5,
                    max_size=20,
                    command_timeout=60,
                    max_queries=50000
                )
                
                # Enable TimescaleDB extension
                async with self.timescale_pool.acquire() as conn:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
                    
                logger.info("TimescaleDB connection established")
            except Exception as e:
                logger.error(f"Failed to connect to TimescaleDB: {e}")
    
    async def _init_supabase(self):
        """Initialize Supabase connections"""
        if self.supabase_url and self.supabase_key:
            try:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                if self.supabase_service_key:
                    self.supabase_admin = create_client(
                        self.supabase_url, 
                        self.supabase_service_key
                    )
                logger.info("Supabase connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {e}")
    
    # ==================== TIMESCALEDB METHODS (Time-series data) ====================
    
    async def create_forex_tables(self):
        """Create optimized forex tables in TimescaleDB"""
        if not self.timescale_pool:
            return
            
        async with self.timescale_pool.acquire() as conn:
            # Forex prices table with automatic partitioning
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS forex_prices (
                    timestamp TIMESTAMPTZ NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    bid DECIMAL(18,5) NOT NULL,
                    ask DECIMAL(18,5) NOT NULL,
                    spread DECIMAL(10,5) GENERATED ALWAYS AS (ask - bid) STORED,
                    volume BIGINT,
                    timeframe VARCHAR(10),
                    source VARCHAR(20) DEFAULT 'oanda'
                );
            """)
            
            # Convert to hypertable (TimescaleDB)
            try:
                await conn.execute("""
                    SELECT create_hypertable('forex_prices', 'timestamp', 
                        chunk_time_interval => INTERVAL '1 day',
                        if_not_exists => TRUE
                    );
                """)
            except Exception as e:
                logger.warning(f"Hypertable creation warning: {e}")
            
            # Create indexes for performance
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_forex_prices_symbol_time 
                ON forex_prices (symbol, timestamp DESC);
            """)
            
            # Trading signals table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS trading_signals (
                    timestamp TIMESTAMPTZ NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    signal_type VARCHAR(20) NOT NULL,
                    strength DECIMAL(5,4) NOT NULL,
                    price DECIMAL(18,5) NOT NULL,
                    indicators_used JSONB,
                    ml_confidence DECIMAL(5,4),
                    expected_pips INTEGER
                );
            """)
            
            # Convert signals to hypertable
            try:
                await conn.execute("""
                    SELECT create_hypertable('trading_signals', 'timestamp',
                        chunk_time_interval => INTERVAL '1 day',
                        if_not_exists => TRUE
                    );
                """)
            except Exception as e:
                logger.warning(f"Signals hypertable creation warning: {e}")
            
        logger.info("TimescaleDB forex tables created")
    
    async def insert_forex_prices(self, prices_data: List[Dict]) -> int:
        """Insert forex prices into TimescaleDB"""
        if not self.timescale_pool or not prices_data:
            return 0
            
        async with self.timescale_pool.acquire() as conn:
            records = [
                (
                    price['timestamp'],
                    price['symbol'], 
                    price['bid'],
                    price['ask'],
                    price.get('volume'),
                    price.get('timeframe', '1min'),
                    price.get('source', 'oanda')
                )
                for price in prices_data
            ]
            
            result = await conn.executemany("""
                INSERT INTO forex_prices 
                (timestamp, symbol, bid, ask, volume, timeframe, source)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT DO NOTHING
            """, records)
            
        return len(records)
    
    async def get_ohlc_data(
        self, 
        symbol: str, 
        timeframe: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict]:
        """Get OHLC data from TimescaleDB"""
        if not self.timescale_pool:
            return []
            
        # Map timeframe to interval
        interval_map = {
            '1min': '1 minute',
            '5min': '5 minutes', 
            '15min': '15 minutes',
            '1H': '1 hour',
            '4H': '4 hours',
            'Daily': '1 day'
        }
        
        interval = interval_map.get(timeframe, '1 hour')
        
        async with self.timescale_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    time_bucket($1::interval, timestamp) as time_bucket,
                    symbol,
                    FIRST(bid, timestamp) as open_bid,
                    MAX(bid) as high_bid,
                    MIN(bid) as low_bid,
                    LAST(bid, timestamp) as close_bid,
                    FIRST(ask, timestamp) as open_ask,
                    MAX(ask) as high_ask,
                    MIN(ask) as low_ask,
                    LAST(ask, timestamp) as close_ask,
                    SUM(volume) as total_volume,
                    COUNT(*) as tick_count
                FROM forex_prices 
                WHERE symbol = $2 
                    AND timestamp >= $3 
                    AND timestamp <= $4
                GROUP BY time_bucket, symbol
                ORDER BY time_bucket DESC
            """, interval, symbol, start_time, end_time)
            
        return [dict(row) for row in rows]
    
    # ==================== SUPABASE METHODS (Application data) ====================
    
    async def get_user_portfolios(self, user_id: str) -> List[Dict]:
        """Get user portfolios from Supabase"""
        if not self.supabase:
            return []
            
        try:
            response = self.supabase.table('portfolios')\
                .select('*')\
                .eq('user_id', user_id)\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching portfolios: {e}")
            return []
    
    async def save_trading_strategy(self, strategy_data: Dict) -> bool:
        """Save trading strategy configuration to Supabase"""
        if not self.supabase:
            return False
            
        try:
            response = self.supabase.table('trading_strategies')\
                .upsert(strategy_data)\
                .execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error saving strategy: {e}")
            return False
    
    async def get_active_alerts(self, user_id: str) -> List[Dict]:
        """Get active alerts from Supabase"""
        if not self.supabase:
            return []
            
        try:
            response = self.supabase.table('alerts')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('active', True)\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []
    
    async def close(self):
        """Close all database connections"""
        if self.timescale_pool:
            await self.timescale_pool.close()
        logger.info("Database connections closed")


# Global instance
db_manager = HybridDatabaseManager()
