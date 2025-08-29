# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Commands

### Testing (TDD Approach)
```bash
# Run all tests with coverage
make test-coverage

# Run specific test categories
make test-unit                           # Unit tests only
make test-integration                     # Integration tests  
make test-e2e                            # End-to-end tests

# Run tests by marker
pytest -m infrastructure -v              # Database infrastructure tests
pytest -m api -v                         # API connection tests
pytest -m ml -v                          # ML model tests
pytest -m critical -v                    # Critical tests that must pass

# Run a single test file
pytest tests/integration/test_dual_database_sync.py -v

# Run with specific verbosity and stop on first failure
pytest tests/ -vv --maxfail=1 --tb=short
```

### Development & Running
```bash
# Install dependencies
make install

# Run in development mode (Note: correct module path)
python -m src.core.main --env development

# Run in production mode  
python -m src.core.main --env production

# Run specific module
python -m src.core.bot
```

### Code Quality
```bash
# Linting
make lint

# Format code
make format

# Clean temporary files
make clean
```

### ML Model Training
```bash
# Train individual models
make train-transformer
make train-lstm
make train-xgboost

# Train all models
make train-all
```

### Deployment
```bash
# Deploy using your preferred platform
# Configure environment variables in your deployment platform
```

## Architecture Overview

### Database System
- **Supabase PostgreSQL**: All data operations including time-series forex data and application data
  - Forex Tables: `forex_prices`, `economic_calendar`, `ml_predictions`, `trading_signals`, `live_positions`
  - Application Tables: `users`, `portfolios`, `trading_strategies`, `closed_trades`, `system_config`, `alerts`
  - Connection: Via `src.data.database.supabase_only_manager.db_manager.supabase`

### Core Components

**Main Entry Point**: `src/core/main.py`
- ForexTradingBot class orchestrates the entire system
- Web server with health/status endpoints for Railway monitoring
- Initializes database connections and API clients
- Port configured via `PORT` env var (default: 8000)

**Data Flow Pipeline**:
1. **API Connectors** (`src/data/connectors/`): Fetch real-time forex data
   - OANDA v20: Primary data feed (120 req/s)
   - Alpha Vantage: Economic data (5 req/min)
   - TraderMade: Alternative pricing (1000 req/day)

2. **Data Storage** (`src/data/database/`): Supabase handles all data
   - Time-series forex data
   - Application and user data
   - ML model predictions and trading signals

3. **ML Models** (`src/ml/`): Ensemble prediction system
   - Transformer (primary): 12 attention heads, Sharpe 4.4
   - LSTM: 73% directional accuracy
   - XGBoost: Feature engineering focus

4. **Trading Logic** (`src/strategies/`): Signal generation and execution
   - RSI (9-10 period), MACD (12,26,9)
   - Kelly Criterion position sizing
   - Smart Order Routing

5. **Risk Management** (`src/risk/`): Portfolio protection
   - 2% max risk per trade
   - 5% portfolio heat limit
   - Dynamic ATR-based stops

### Critical Forex Pairs Configuration
Priority pairs with specific volatility profiles:
1. USD/ZAR - Ultra-high volatility (1000+ pips/day)
2. GBP/JPY - "The Dragon" (180 pips/day)
3. AUD/JPY - Commodity correlation
4. USD/TRY - Extreme volatility (1000-2000 pips)
5. NZD/JPY - Carry trade premium
6. EUR/USD - Maximum liquidity reference

### Performance Targets
- Annual Return: 25% (critical: >20%)
- Sharpe Ratio: >1.2 (critical: >0.75)
- Max Drawdown: <15% (critical: <20%)
- Win Rate: >60% (critical: >55%)
- Profit Factor: >1.75 (critical: >1.25)

## Test Organization (TDD)

Tests follow strict TDD methodology with 80% minimum coverage:

1. **Infrastructure** (`tests/integration/test_infrastructure_*.py`)
   - Dual database connectivity
   - Table creation and sync

2. **APIs** (`tests/integration/test_*_apis.py`)
   - Connection validation
   - Rate limit handling

3. **ML Models** (`tests/unit/test_*_model.py`)
   - Prediction accuracy
   - Performance benchmarks

4. **Trading Signals** (`tests/unit/test_*_signals.py`)
   - Indicator calculations
   - Signal generation

5. **Risk Management** (`tests/unit/test_risk_*.py`)
   - Position sizing
   - Portfolio limits

## Environment Configuration

Required environment variables:
```bash
# APIs
OANDA_API_KEY=
OANDA_ACCOUNT_ID=
OANDA_ENVIRONMENT=practice  # or live
ALPHA_VANTAGE_API_KEY=
TRADERMADE_API_KEY=

# Database
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=

# Trading
TRADING_MODE=paper  # or live
MAX_POSITIONS=5
RISK_PER_TRADE=0.02

# Deployment
PORT=8000
NODE_ENV=development  # or production
```

## Key Implementation Files

- **TDD Plan**: `/requirements/03_implementation/plan_tdd_completo_forex_bot.md`
- **Implementation Timeline**: `/requirements/03_implementation/guia_implementacion_orden.md`
- **ML Specifications**: `/requirements/05_ml_models/ml_parameters_quantified_2025.md`
- **Trading Configs**: `/requirements/02_technical_specs/configuraciones_especificas.md`
- **Main Config**: `/config/config.yaml`
- **Pairs Config**: `/config/pairs_config.yaml`
- **ML Config**: `/config/ml_config.yaml`

## Development Workflow

1. **Always write tests first** (TDD)
2. **Run tests before committing**: `make test`
3. **Check coverage**: Must maintain >80%
4. **Lint before push**: `make lint`
5. **Monitor performance**: Sharpe ratio is critical metric
6. **Risk limits are absolute**: Never exceed 2% per trade
7. **Document trading decisions**: All trades must be logged
8. **Alert on anomalies**: Immediate notification required

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`) runs:
- Unit, integration, and E2E tests
- Code linting and type checking
- Security scanning (Trivy, Trufflehog)
- Docker image building
- Health check validation