# Setting Up PostgreSQL with TimescaleDB on Railway

## Steps to Add PostgreSQL Service to Railway

### 1. Add PostgreSQL Service via Railway Dashboard

1. Go to your Railway project dashboard: https://railway.app
2. Click on "New Service" or "+"
3. Select "Database" → "Add PostgreSQL"
4. Railway will automatically create the PostgreSQL service with these variables:
   - `PGHOST`
   - `PGPORT`
   - `PGDATABASE`
   - `PGUSER`
   - `PGPASSWORD`
   - `DATABASE_URL`

### 2. Enable TimescaleDB Extension

Once the PostgreSQL service is running, you need to enable TimescaleDB:

```bash
# Connect to the database using Railway CLI
railway connect postgres

# Or use the DATABASE_URL from Railway to connect with psql
psql $DATABASE_URL
```

Then run these SQL commands:

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Verify installation
SELECT default_version, installed_version 
FROM pg_available_extensions 
WHERE name = 'timescaledb';

-- Create the database for time-series data
CREATE DATABASE bottrader_timeseries;

-- Connect to the new database
\c bottrader_timeseries

-- Enable TimescaleDB in the new database
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

### 3. Create TimescaleDB Tables

```sql
-- Create forex prices hypertable
CREATE TABLE forex_prices (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    bid DECIMAL(10,5),
    ask DECIMAL(10,5),
    spread DECIMAL(10,5),
    volume BIGINT
);

-- Convert to hypertable
SELECT create_hypertable('forex_prices', 'time');

-- Create index for faster queries
CREATE INDEX idx_forex_prices_symbol_time ON forex_prices (symbol, time DESC);

-- Create economic calendar hypertable
CREATE TABLE economic_calendar (
    time TIMESTAMPTZ NOT NULL,
    currency VARCHAR(3) NOT NULL,
    event VARCHAR(255),
    impact VARCHAR(10),
    actual DECIMAL(10,2),
    forecast DECIMAL(10,2),
    previous DECIMAL(10,2)
);

SELECT create_hypertable('economic_calendar', 'time');

-- Create ML predictions hypertable
CREATE TABLE ml_predictions (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    model_type VARCHAR(50),
    prediction VARCHAR(10),
    confidence DECIMAL(5,4)
);

SELECT create_hypertable('ml_predictions', 'time');

-- Create trading signals hypertable
CREATE TABLE trading_signals (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    signal_type VARCHAR(20),
    strength DECIMAL(5,2),
    indicators_used TEXT
);

SELECT create_hypertable('trading_signals', 'time');

-- Create live positions hypertable
CREATE TABLE live_positions (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    position_size DECIMAL(15,2),
    entry_price DECIMAL(10,5),
    stop_loss DECIMAL(10,5),
    take_profit DECIMAL(10,5),
    status VARCHAR(20)
);

SELECT create_hypertable('live_positions', 'time');

-- Set up compression policy (compress data older than 7 days)
SELECT add_compression_policy('forex_prices', INTERVAL '7 days');

-- Set up retention policy (keep 2 years of data)
SELECT add_retention_policy('forex_prices', INTERVAL '2 years');
```

### 4. Update Railway Variables

After PostgreSQL is added, Railway will automatically set these variables. The TimescaleDB mapping variables we set earlier will then reference them:

- `TIMESCALE_HOST` → Will use `${{PGHOST}}`
- `TIMESCALE_PORT` → Will use `${{PGPORT}}`
- `TIMESCALE_DB` → Will use `${{PGDATABASE}}`
- `TIMESCALE_USER` → Will use `${{PGUSER}}`
- `TIMESCALE_PASSWORD` → Will use `${{PGPASSWORD}}`
- `TIMESCALE_URL` → Will use `${{DATABASE_URL}}`

### 5. Verify Setup

After adding PostgreSQL, verify the variables:

```bash
# Check all database-related variables
railway variables | grep -E "PG|DATABASE|TIMESCALE"

# Test database connection
railway run python -c "
import os
import psycopg2
url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(url)
print('✅ Database connection successful!')
conn.close()
"
```

### 6. Deploy Application

Once everything is set up:

```bash
# Deploy the application with new variables
railway up

# Check deployment status
railway status

# View logs
railway logs
```

## Alternative: Use Railway Template

If you prefer, you can use a Railway template that includes PostgreSQL:

1. Go to: https://railway.app/new
2. Select "Deploy a Template"
3. Search for "PostgreSQL" or "TimescaleDB"
4. Deploy the template
5. Connect it to your existing project

## Notes

- Railway's PostgreSQL service automatically handles backups
- Connection pooling is managed by Railway
- SSL is enabled by default
- The database URL includes all connection parameters

## Troubleshooting

If TimescaleDB extension is not available:

1. Check PostgreSQL version (needs 12+):
   ```sql
   SELECT version();
   ```

2. If not available, you might need to use a custom Docker image:
   - Create a `Dockerfile` with TimescaleDB
   - Deploy as a custom service instead

## Next Steps

After setting up the database:

1. Run the TDD tests to verify connectivity
2. Start ingesting forex data
3. Monitor performance in Railway dashboard
4. Set up alerts for database metrics