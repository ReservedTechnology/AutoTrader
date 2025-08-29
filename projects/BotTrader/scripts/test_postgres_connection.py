#!/usr/bin/env python3
"""
Test script to verify PostgreSQL TimescaleDB connection from Railway
"""
import os
import asyncio
import asyncpg
from datetime import datetime

async def test_database_connection():
    """Test the PostgreSQL connection and TimescaleDB setup"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    try:
        # Connect to the database
        conn = await asyncpg.connect(database_url)
        print("✅ Database connection successful!")
        
        # Test basic query
        version = await conn.fetchval('SELECT version()')
        print(f"📊 PostgreSQL Version: {version}")
        
        # Check if our tables exist
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('forex_prices', 'trading_signals', 'ml_predictions')
        """)
        
        print(f"📋 Tables found: {[table['tablename'] for table in tables]}")
        
        # Test inserting sample data
        await conn.execute("""
            INSERT INTO forex_prices (time, symbol, bid, ask, volume, source) 
            VALUES ($1, $2, $3, $4, $5, $6)
        """, datetime.utcnow(), 'TEST_PAIR', 1.2345, 1.2347, 100000, 'test')
        
        print("✅ Sample data insertion successful!")
        
        # Test querying data
        count = await conn.fetchval('SELECT COUNT(*) FROM forex_prices')
        print(f"📈 Total forex price records: {count}")
        
        # Test recent data
        recent = await conn.fetch("""
            SELECT symbol, bid, ask, time 
            FROM forex_prices 
            ORDER BY time DESC 
            LIMIT 3
        """)
        
        print("🕒 Recent forex data:")
        for row in recent:
            print(f"   {row['symbol']}: {row['bid']}/{row['ask']} at {row['time']}")
        
        await conn.close()
        print("✅ All database tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_database_connection())
    exit(0 if result else 1)
