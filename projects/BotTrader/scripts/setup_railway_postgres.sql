-- PostgreSQL Setup Script for Forex Bot (Railway)
-- Alternative approach when TimescaleDB is not available

-- Create optimized tables for time-series data without TimescaleDB
-- Using PostgreSQL native partitioning and optimization

-- 1. Create forex prices table with partitioning
CREATE TABLE forex_prices (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    bid DECIMAL(18,5) NOT NULL,
    ask DECIMAL(18,5) NOT NULL,
    spread DECIMAL(10,5) GENERATED ALWAYS AS (ask - bid) STORED,
    volume BIGINT,
    timeframe VARCHAR(10) DEFAULT '1min',
    source VARCHAR(20) DEFAULT 'oanda'
) PARTITION BY RANGE (time);

-- Create monthly partitions for current and next month
CREATE TABLE forex_prices_2025_08 PARTITION OF forex_prices
FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

CREATE TABLE forex_prices_2025_09 PARTITION OF forex_prices
FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

CREATE TABLE forex_prices_2025_10 PARTITION OF forex_prices
FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

-- Create indexes for performance
CREATE INDEX idx_forex_prices_symbol_time ON forex_prices (symbol, time DESC);
CREATE INDEX idx_forex_prices_timeframe ON forex_prices (timeframe, time DESC);

-- 2. Create economic calendar table
CREATE TABLE economic_calendar (
    time TIMESTAMPTZ NOT NULL,
    currency VARCHAR(3) NOT NULL,
    event TEXT NOT NULL,
    impact VARCHAR(10),
    actual DECIMAL(10,2),
    forecast DECIMAL(10,2),
    previous DECIMAL(10,2),
    PRIMARY KEY (time, currency, event)
);

CREATE INDEX idx_economic_calendar_currency_time ON economic_calendar (currency, time DESC);

-- 3. Create ML predictions table
CREATE TABLE ml_predictions (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    prediction VARCHAR(10) NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    features_hash VARCHAR(64),
    timeframe VARCHAR(10),
    PRIMARY KEY (time, symbol, model_type)
);

CREATE INDEX idx_ml_predictions_symbol_time ON ml_predictions (symbol, time DESC);

-- 4. Create trading signals table
CREATE TABLE trading_signals (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,
    strength DECIMAL(5,4) NOT NULL,
    price DECIMAL(18,5) NOT NULL,
    indicators_used JSONB,
    ml_confidence DECIMAL(5,4),
    expected_pips INTEGER,
    PRIMARY KEY (time, symbol, signal_type)
);

CREATE INDEX idx_trading_signals_symbol_time ON trading_signals (symbol, time DESC);
CREATE INDEX idx_trading_signals_strength ON trading_signals (strength DESC);

-- 5. Create live positions table
CREATE TABLE live_positions (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol VARCHAR(10) NOT NULL,
    position_size DECIMAL(18,2) NOT NULL,
    entry_price DECIMAL(18,5) NOT NULL,
    stop_loss DECIMAL(18,5),
    take_profit DECIMAL(18,5),
    status VARCHAR(20) DEFAULT 'open',
    kelly_percentage DECIMAL(5,4),
    risk_amount DECIMAL(18,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_live_positions_symbol_status ON live_positions (symbol, status);
CREATE INDEX idx_live_positions_time ON live_positions (time DESC);

-- 6. Create OHLC aggregation views for performance
CREATE MATERIALIZED VIEW forex_prices_5min AS
SELECT 
    date_trunc('minute', time) + 
    INTERVAL '5 min' * FLOOR(EXTRACT(MINUTE FROM time)::int / 5) as time_bucket,
    symbol,
    FIRST_VALUE(bid ORDER BY time) as open_bid,
    MAX(bid) as high_bid,
    MIN(bid) as low_bid,
    LAST_VALUE(bid ORDER BY time ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as close_bid,
    FIRST_VALUE(ask ORDER BY time) as open_ask,
    MAX(ask) as high_ask,
    MIN(ask) as low_ask,
    LAST_VALUE(ask ORDER BY time ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as close_ask,
    SUM(volume) as total_volume,
    COUNT(*) as tick_count
FROM forex_prices 
WHERE timeframe = '1min'
GROUP BY time_bucket, symbol;

CREATE UNIQUE INDEX idx_forex_5min_symbol_time ON forex_prices_5min (symbol, time_bucket);

-- 7. Create functions for automatic partition creation
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
DECLARE
    partition_name text;
    end_date date;
BEGIN
    partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
    end_date := start_date + interval '1 month';
    
    EXECUTE format('CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- 8. Create data retention function
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Delete forex prices older than 2 years
    DELETE FROM forex_prices WHERE time < NOW() - INTERVAL '2 years';
    
    -- Delete trading signals older than 30 days
    DELETE FROM trading_signals WHERE time < NOW() - INTERVAL '30 days';
    
    -- Refresh materialized views
    REFRESH MATERIALIZED VIEW forex_prices_5min;
END;
$$ LANGUAGE plpgsql;

-- 9. Set up basic performance optimization
-- Enable pg_stat_statements for query analysis
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create performance monitoring view
CREATE VIEW performance_stats AS
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE schemaname = 'public' 
AND tablename IN ('forex_prices', 'trading_signals', 'ml_predictions');

-- 10. Insert sample data for testing
INSERT INTO forex_prices (time, symbol, bid, ask, volume) VALUES
    (NOW() - INTERVAL '1 hour', 'EUR_USD', 1.0850, 1.0852, 1000000),
    (NOW() - INTERVAL '55 minutes', 'EUR_USD', 1.0851, 1.0853, 950000),
    (NOW() - INTERVAL '50 minutes', 'GBP_JPY', 189.45, 189.47, 750000),
    (NOW() - INTERVAL '45 minutes', 'USD_ZAR', 18.2500, 18.2750, 500000);

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO CURRENT_USER;

-- Display setup completion message
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL forex database setup completed successfully!';
    RAISE NOTICE 'Tables created: forex_prices, economic_calendar, ml_predictions, trading_signals, live_positions';
    RAISE NOTICE 'Materialized view: forex_prices_5min';
    RAISE NOTICE 'Sample data inserted for testing';
END $$;
