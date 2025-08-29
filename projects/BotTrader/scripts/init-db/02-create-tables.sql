-- BotTrader Forex Database Schema with TimescaleDB
-- Optimized for high-frequency trading data

-- =====================================================
-- FOREX PRICES TABLE - Main time-series data
-- =====================================================
CREATE TABLE IF NOT EXISTS forex_prices (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    bid DECIMAL(18,5) NOT NULL,
    ask DECIMAL(18,5) NOT NULL,
    spread DECIMAL(10,5) GENERATED ALWAYS AS (ask - bid) STORED,
    volume BIGINT,
    timeframe VARCHAR(10),
    PRIMARY KEY (timestamp, symbol)
);

-- Convert to hypertable with daily partitioning
SELECT create_hypertable('forex_prices', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

-- Create indexes for optimal query performance
CREATE INDEX IF NOT EXISTS idx_forex_prices_symbol_time 
    ON forex_prices (symbol, timestamp DESC);

-- Add compression policy for older data (compress after 7 days)
SELECT add_compression_policy('forex_prices', 
    INTERVAL '7 days',
    if_not_exists => TRUE);

-- =====================================================
-- ECONOMIC CALENDAR TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS economic_calendar (
    timestamp TIMESTAMPTZ NOT NULL,
    currency VARCHAR(3) NOT NULL,
    event TEXT NOT NULL,
    impact VARCHAR(10),
    actual DECIMAL(10,2),
    forecast DECIMAL(10,2),
    previous DECIMAL(10,2),
    PRIMARY KEY (timestamp, currency, event)
);

-- Convert to hypertable with weekly partitioning
SELECT create_hypertable('economic_calendar', 'timestamp',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_economic_calendar_currency 
    ON economic_calendar (currency, timestamp DESC);

-- =====================================================
-- ML PREDICTIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS ml_predictions (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    model_type VARCHAR(20) NOT NULL, -- transformer, lstm, xgboost
    prediction DECIMAL(18,5) NOT NULL,
    confidence DECIMAL(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    features_hash VARCHAR(64),
    timeframe VARCHAR(10),
    PRIMARY KEY (timestamp, symbol, model_type)
);

-- Convert to hypertable with daily partitioning
SELECT create_hypertable('ml_predictions', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_ml_predictions_symbol_model 
    ON ml_predictions (symbol, model_type, timestamp DESC);

-- Add compression policy
SELECT add_compression_policy('ml_predictions', 
    INTERVAL '7 days',
    if_not_exists => TRUE);

-- =====================================================
-- TRADING SIGNALS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS trading_signals (
    timestamp TIMESTAMPTZ NOT NULL,
    signal_id UUID DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    signal_type VARCHAR(20) NOT NULL, -- buy, sell, hold
    strength DECIMAL(5,4) NOT NULL CHECK (strength >= 0 AND strength <= 1),
    indicators_used JSONB,
    ml_confidence DECIMAL(5,4),
    expected_pips INTEGER,
    PRIMARY KEY (timestamp, signal_id)
);

-- Convert to hypertable with daily partitioning
SELECT create_hypertable('trading_signals', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol 
    ON trading_signals (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_type 
    ON trading_signals (signal_type, timestamp DESC);

-- =====================================================
-- PORTFOLIO POSITIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS portfolio_positions (
    timestamp TIMESTAMPTZ NOT NULL,
    position_id UUID DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    position_size DECIMAL(18,2) NOT NULL,
    entry_price DECIMAL(18,5) NOT NULL,
    stop_loss DECIMAL(18,5),
    take_profit DECIMAL(18,5),
    status VARCHAR(20) DEFAULT 'open', -- open, closed, partial
    kelly_percentage DECIMAL(5,4),
    risk_amount DECIMAL(18,2),
    exit_price DECIMAL(18,5),
    exit_timestamp TIMESTAMPTZ,
    pnl DECIMAL(18,2),
    PRIMARY KEY (timestamp, position_id)
);

-- Convert to hypertable with weekly partitioning
SELECT create_hypertable('portfolio_positions', 'timestamp',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_portfolio_positions_status 
    ON portfolio_positions (status, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_symbol 
    ON portfolio_positions (symbol, timestamp DESC);

-- =====================================================
-- CONTINUOUS AGGREGATES for OHLC data
-- =====================================================

-- 5-minute OHLC
CREATE MATERIALIZED VIEW IF NOT EXISTS forex_prices_5min_ohlc
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('5 minutes', timestamp) AS bucket,
    symbol,
    FIRST(bid, timestamp) AS open,
    MAX(bid) AS high,
    MIN(bid) AS low,
    LAST(bid, timestamp) AS close,
    SUM(volume) AS volume,
    AVG(spread) AS avg_spread
FROM forex_prices
GROUP BY bucket, symbol
WITH NO DATA;

-- Add refresh policy for real-time updates
SELECT add_continuous_aggregate_policy('forex_prices_5min_ohlc',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE);

-- 15-minute OHLC
CREATE MATERIALIZED VIEW IF NOT EXISTS forex_prices_15min_ohlc
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('15 minutes', timestamp) AS bucket,
    symbol,
    FIRST(bid, timestamp) AS open,
    MAX(bid) AS high,
    MIN(bid) AS low,
    LAST(bid, timestamp) AS close,
    SUM(volume) AS volume,
    AVG(spread) AS avg_spread
FROM forex_prices
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('forex_prices_15min_ohlc',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE);

-- 1-hour OHLC
CREATE MATERIALIZED VIEW IF NOT EXISTS forex_prices_1h_ohlc
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', timestamp) AS bucket,
    symbol,
    FIRST(bid, timestamp) AS open,
    MAX(bid) AS high,
    MIN(bid) AS low,
    LAST(bid, timestamp) AS close,
    SUM(volume) AS volume,
    AVG(spread) AS avg_spread
FROM forex_prices
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('forex_prices_1h_ohlc',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '10 minutes',
    if_not_exists => TRUE);

-- 4-hour OHLC
CREATE MATERIALIZED VIEW IF NOT EXISTS forex_prices_4h_ohlc
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('4 hours', timestamp) AS bucket,
    symbol,
    FIRST(bid, timestamp) AS open,
    MAX(bid) AS high,
    MIN(bid) AS low,
    LAST(bid, timestamp) AS close,
    SUM(volume) AS volume,
    AVG(spread) AS avg_spread
FROM forex_prices
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('forex_prices_4h_ohlc',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '30 minutes',
    if_not_exists => TRUE);

-- Daily OHLC
CREATE MATERIALIZED VIEW IF NOT EXISTS forex_prices_daily_ohlc
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', timestamp) AS bucket,
    symbol,
    FIRST(bid, timestamp) AS open,
    MAX(bid) AS high,
    MIN(bid) AS low,
    LAST(bid, timestamp) AS close,
    SUM(volume) AS volume,
    AVG(spread) AS avg_spread
FROM forex_prices
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('forex_prices_daily_ohlc',
    start_offset => INTERVAL '1 week',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- =====================================================
-- DATA RETENTION POLICIES
-- =====================================================

-- Keep detailed forex prices for 2 years
SELECT add_retention_policy('forex_prices', 
    INTERVAL '730 days',
    if_not_exists => TRUE);

-- Keep signals for 30 days
SELECT add_retention_policy('trading_signals', 
    INTERVAL '30 days',
    if_not_exists => TRUE);

-- Keep ML predictions for 90 days
SELECT add_retention_policy('ml_predictions', 
    INTERVAL '90 days',
    if_not_exists => TRUE);

-- Keep economic calendar for 1 year
SELECT add_retention_policy('economic_calendar', 
    INTERVAL '365 days',
    if_not_exists => TRUE);

-- Keep portfolio positions for 2 years
SELECT add_retention_policy('portfolio_positions', 
    INTERVAL '730 days',
    if_not_exists => TRUE);

-- =====================================================
-- ROW LEVEL SECURITY (RLS) for sensitive tables
-- =====================================================

-- Enable RLS on portfolio positions
ALTER TABLE portfolio_positions ENABLE ROW LEVEL SECURITY;

-- Enable RLS on trading signals
ALTER TABLE trading_signals ENABLE ROW LEVEL SECURITY;

-- Create policies (to be customized based on user roles)
CREATE POLICY "portfolio_read_policy" ON portfolio_positions
    FOR SELECT
    USING (true);

CREATE POLICY "signals_read_policy" ON trading_signals
    FOR SELECT
    USING (true);

-- =====================================================
-- PERFORMANCE MONITORING VIEWS
-- =====================================================

CREATE OR REPLACE VIEW system_performance AS
SELECT 
    'forex_prices' as table_name,
    pg_size_pretty(hypertable_size('forex_prices')) as table_size,
    (SELECT count(*) FROM forex_prices) as row_count
UNION ALL
SELECT 
    'ml_predictions' as table_name,
    pg_size_pretty(hypertable_size('ml_predictions')) as table_size,
    (SELECT count(*) FROM ml_predictions) as row_count
UNION ALL
SELECT 
    'trading_signals' as table_name,
    pg_size_pretty(hypertable_size('trading_signals')) as table_size,
    (SELECT count(*) FROM trading_signals) as row_count;

-- Grant appropriate permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;