# 🤖 CLAUDE.md - BotTrader Project Context

## Project Overview
BotTrader is a sophisticated forex automated trading system designed to achieve 25% annual returns using advanced ML models and Test-Driven Development (TDD) methodology.

## Key Project Goals
- **Primary Target**: 25% annual return with <15% max drawdown
- **Sharpe Ratio**: >1.2 (critical threshold: >0.75)
- **Win Rate**: >60% (critical: >55%)
- **Profit Factor**: >1.75 (critical: >1.25)
- **Risk Management**: 2% max risk per trade, 5% portfolio heat max

## Technology Stack
- **Language**: Python 3.11+
- **Database**: Supabase with TimescaleDB (time-series optimization)
- **Deployment**: Railway (cloud platform)
- **Data APIs**: OANDA v20 (primary), Alpha Vantage, TraderMade
- **ML Framework**: TensorFlow/PyTorch for Transformers, XGBoost for ensemble
- **Monitoring**: Prometheus + Grafana
- **Cache**: Redis
- **Containerization**: Docker with multi-stage builds

## ML Models Architecture
1. **Transformer Model** (Primary)
   - 12 attention heads, 6 layers
   - Sharpe ratio: 4.4, 68% accuracy
   - 15-minute predictions

2. **LSTM Model** (Secondary)
   - 4 layers, 256 units each
   - 73% directional accuracy
   - Ensemble weight: 30%

3. **XGBoost** (Support)
   - 500 estimators, depth 7
   - Feature engineering focused
   - Ensemble weight: 20%

## Priority Forex Pairs
1. **USD/ZAR** - Extreme volatility (1000+ pips/day)
2. **GBP/JPY** - "The Dragon" (180 pips/day)
3. **AUD/JPY** - Commodity correlation
4. **USD/TRY** - High volatility (1000-2000 pips)
5. **NZD/JPY** - Carry trade premium
6. **EUR/USD** - Maximum liquidity reference

## Project Structure
```
BotTrader/
├── src/                    # Source code
│   ├── core/              # Core trading logic
│   ├── strategies/        # Trading strategies
│   ├── ml/               # ML models
│   ├── data/             # Data collection
│   ├── risk/             # Risk management
│   ├── monitoring/       # System monitoring
│   └── utils/            # Utilities
├── tests/                 # TDD tests
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── requirements/          # Documentation
│   ├── 01_overview/      # Project overview
│   ├── 02_technical_specs/
│   ├── 03_implementation/
│   ├── 04_data_sources/
│   └── 05_ml_models/
├── config/               # Configuration files
├── models/               # Trained ML models
└── data/                 # Historical data
```

## Development Commands
```bash
# Testing
make test              # Run all tests
make test-unit         # Unit tests only
make test-coverage     # Coverage report

# Running
make run-dev          # Development mode
make run-prod         # Production mode
make run-backtest     # Backtesting

# ML Training
make train-transformer # Train Transformer
make train-lstm       # Train LSTM
make train-xgboost    # Train XGBoost
make train-all        # Train all models

# Docker
make docker-build     # Build containers
make docker-up        # Start services
make docker-down      # Stop services

# Code Quality
make lint             # Run linting
make format           # Format with black
```

## Implementation Timeline (30 Days)
- **Days 1-3**: Infrastructure setup (Supabase + Railway)
- **Days 4-7**: API connections and data pipeline
- **Days 8-14**: ML models training and validation
- **Days 15-21**: Trading logic implementation
- **Days 22-25**: Monitoring and alerting systems
- **Days 26-30**: Integration testing and optimization

## Testing Strategy (TDD)
14 organized tests covering:
1. Infrastructure connectivity
2. Data collection and validation
3. ML model predictions
4. Risk management rules
5. Order execution
6. Portfolio management
7. Monitoring and alerts
8. Error handling
9. Performance benchmarks

## Critical Risk Parameters
- **Position Sizing**: Kelly Criterion with 25% max per trade
- **Stop Loss**: Dynamic based on ATR (1.5x-2x)
- **Daily Loss Limit**: 5% of portfolio
- **Correlation Limit**: Max 0.7 between positions
- **Leverage**: Max 10:1 (conservative)
- **Trading Hours**: Focus on London-NY overlap (8AM-12PM ET)

## API Rate Limits
- **OANDA**: 120 requests/second
- **Alpha Vantage**: 5 requests/minute (free tier)
- **TraderMade**: 1000 requests/day (free tier)
- **Twitter API v2**: 500k tweets/month

## Performance Targets
- **Latency**: <100ms for signal generation
- **Data Processing**: <50ms per tick
- **Model Inference**: <200ms for ensemble
- **Order Execution**: <500ms total
- **Uptime**: 99.9% availability

## Security Considerations
- All API keys in environment variables
- Encrypted database connections
- Rate limiting on all endpoints
- Audit logging for all trades
- Two-factor authentication for admin
- Regular security audits

## Monitoring Metrics
- P&L in real-time
- Sharpe ratio (rolling 30-day)
- Maximum drawdown alerts
- API health checks
- Model performance drift
- System resource usage
- Error rates and types

## Important Files
- `/requirements/03_implementation/plan_tdd_completo_forex_bot.md` - Complete TDD plan
- `/requirements/03_implementation/guia_implementacion_orden.md` - Implementation timeline
- `/requirements/05_ml_models/ml_parameters_quantified_2025.md` - ML specifications
- `/requirements/02_technical_specs/configuraciones_especificas.md` - Trading configs
- `/config/config.yaml` - Main configuration
- `/config/pairs_config.yaml` - Forex pairs settings
- `/config/ml_config.yaml` - ML model parameters

## Environment Variables Required
```bash
# APIs
OANDA_API_KEY=
OANDA_ACCOUNT_ID=
ALPHA_VANTAGE_API_KEY=
TRADERMADE_API_KEY=
TWITTER_BEARER_TOKEN=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=

# Database
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=

# Monitoring
GRAFANA_API_KEY=
SLACK_WEBHOOK_URL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Trading
TRADING_MODE=paper  # paper or live
MAX_POSITIONS=5
RISK_PER_TRADE=0.02
```

## Next Steps Priority
1. Set up Supabase database with TimescaleDB extension
2. Configure OANDA API connection and test data stream
3. Implement core data collection pipeline
4. Train initial ML models with historical data
5. Develop risk management module
6. Create monitoring dashboard
7. Run comprehensive backtests
8. Deploy to Railway for paper trading
9. Monitor and optimize for 2 weeks
10. Transition to live trading with minimal capital

## Notes for Claude
- Always run tests before committing changes
- Use TDD approach - write tests first
- Focus on risk management above returns
- Document all trading decisions in logs
- Alert on any anomalies immediately
- Never exceed risk limits
- Prioritize system stability over features
- Keep ML models simple and interpretable
- Monitor for model drift continuously
- Maintain detailed audit trails

Last Updated: August 2025
Version: 1.0