# Environment Variables Documentation - BotTrader

## Overview

BotTrader uses a dual database architecture:
- **TimescaleDB (Railway)**: For all time-series data (prices, signals, predictions)
- **Supabase**: For non-temporal data (users, configurations, closed trades)

## Environment Files

### `.env` - Main configuration file
- Used for local development and testing
- Contains actual credentials for test environment
- **Never commit this file to version control**

### `.env.example` - Template file
- Template showing all required variables
- Safe to commit to version control
- Copy to `.env` and fill in your values

### `.env.railway` - Railway deployment
- Specific configuration for Railway deployment
- Uses Railway's environment variable injection
- TimescaleDB runs as a Railway service

### `.env.docker` - Docker development
- Configuration for Docker Compose development
- TimescaleDB runs as a Docker container
- Supabase connects to cloud instance

### `config/.env.example` - Config directory template
- Alternative configuration location
- Used by configuration management system

## Required Environment Variables

### Database Configuration

#### TimescaleDB (Time-Series Data)
```bash
# Connection details for TimescaleDB on Railway
TIMESCALE_HOST=your-timescale-host.railway.app
TIMESCALE_PORT=5432
TIMESCALE_DB=bottrader_timeseries
TIMESCALE_USER=postgres
TIMESCALE_PASSWORD=your-secure-password
TIMESCALE_URL=postgresql://user:password@host:port/database
```

**Stores:**
- `forex_prices`: Real-time price data
- `economic_calendar`: Economic events
- `ml_predictions`: Model predictions
- `trading_signals`: Generated signals
- `live_positions`: Current open positions

#### Supabase (Non-Temporal Data)
```bash
# Supabase project credentials
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
```

**Stores:**
- `users`: User accounts and settings
- `trading_strategies`: Strategy configurations
- `closed_trades`: Historical trade records
- `system_config`: System configuration
- `ml_model_versions`: Model metadata

### API Credentials

#### Forex Data APIs
```bash
# OANDA v20 API (Primary data source)
OANDA_API_KEY=your-oanda-api-key
OANDA_ACCOUNT_ID=your-account-id
OANDA_ENVIRONMENT=practice  # or 'live' for production

# Alpha Vantage (Historical data)
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key

# TraderMade (Real-time WebSocket)
TRADERMADE_API_KEY=your-tradermade-key
```

#### Social Media APIs (Sentiment Analysis)
```bash
# Twitter/X API v2
TWITTER_BEARER_TOKEN=your-bearer-token

# Reddit API
REDDIT_CLIENT_ID=your-client-id
REDDIT_CLIENT_SECRET=your-client-secret
REDDIT_USER_AGENT=BotTrader/1.0
```

### Deployment Configuration

#### Railway
```bash
RAILWAY_PROJECT_ID=your-project-id
RAILWAY_API_TOKEN=your-api-token
RAILWAY_ENVIRONMENT=production
RAILWAY_STATIC_URL=https://your-app.railway.app
```

### Monitoring & Notifications

#### Monitoring
```bash
# Grafana
GRAFANA_API_KEY=your-grafana-key
GRAFANA_URL=http://localhost:3000

# Prometheus
PROMETHEUS_URL=http://localhost:9090
```

#### Notifications
```bash
# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

### Application Settings

#### Environment
```bash
ENVIRONMENT=development  # development, staging, production
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
```

#### Redis Cache
```bash
REDIS_URL=redis://localhost:6379/0
```

#### Trading Parameters
```bash
TRADING_MODE=paper       # paper or live
MAX_POSITIONS=5          # Maximum simultaneous positions
RISK_PER_TRADE=0.02     # 2% risk per trade
PORTFOLIO_HEAT_MAX=0.05 # 5% maximum portfolio exposure
```

#### Database Connection Pools
```bash
DB_POOL_MIN=2           # Minimum connections
DB_POOL_MAX=10          # Maximum connections
DB_STATEMENT_TIMEOUT=30000    # 30 seconds
DB_CONNECTION_TIMEOUT=10000   # 10 seconds
```

#### Performance Settings
```bash
CACHE_TTL=300          # Cache time-to-live in seconds
BATCH_SIZE=1000        # Batch size for bulk operations
WORKER_THREADS=4       # Number of worker threads
```

## Environment-Specific Configurations

### Development
- Uses local TimescaleDB or Docker container
- Connects to Supabase cloud (development project)
- Debug logging enabled
- Paper trading mode

### Staging
- Uses Railway TimescaleDB service
- Connects to Supabase cloud (staging project)
- Info logging level
- Paper trading mode

### Production
- Uses Railway TimescaleDB service (scaled)
- Connects to Supabase cloud (production project)
- Warning/Error logging only
- Live trading mode (when enabled)

## Security Best Practices

1. **Never commit `.env` files** containing real credentials
2. **Use strong passwords** for database connections
3. **Rotate API keys** regularly
4. **Use read-only keys** where possible
5. **Encrypt sensitive data** in transit and at rest
6. **Limit API key permissions** to minimum required
7. **Use environment-specific credentials** (dev/staging/prod)

## Setting Up Environment Variables

### Local Development
```bash
# Copy the example file
cp .env.example .env

# Edit with your credentials
nano .env

# Verify configuration
python scripts/verify_env.py
```

### Railway Deployment
1. Go to Railway dashboard
2. Navigate to your project
3. Click on "Variables"
4. Add each required variable
5. Railway will inject these automatically

### Docker Development
```bash
# Copy Docker environment file
cp .env.docker .env

# Start services with Docker Compose
docker-compose --env-file .env.docker up
```

## Troubleshooting

### Common Issues

#### TimescaleDB Connection Failed
- Verify `TIMESCALE_URL` is correct
- Check network connectivity to Railway
- Ensure TimescaleDB service is running
- Verify credentials are correct

#### Supabase Connection Failed
- Check `SUPABASE_URL` format
- Verify API keys are valid
- Ensure Supabase project is active
- Check network connectivity

#### API Rate Limits
- Monitor API usage in logs
- Implement exponential backoff
- Consider upgrading API plans
- Use caching to reduce calls

## Variable Validation Script

Create `scripts/verify_env.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()

required_vars = [
    'TIMESCALE_URL',
    'SUPABASE_URL',
    'SUPABASE_ANON_KEY',
    'OANDA_API_KEY',
    'OANDA_ACCOUNT_ID'
]

missing = []
for var in required_vars:
    if not os.getenv(var):
        missing.append(var)

if missing:
    print(f"Missing required variables: {', '.join(missing)}")
else:
    print("All required variables are set!")
```

## Contact

For issues with environment configuration, please check:
1. This documentation
2. `.env.example` files
3. Railway/Supabase dashboards
4. Project README.md