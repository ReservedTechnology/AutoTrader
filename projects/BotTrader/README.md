# 🚀 BotTrader - Automated Forex Trading System

## 📊 Overview
Professional automated forex trading system designed to achieve 25% annual returns using advanced ML models and risk management strategies.

## 🎯 Key Features
- **Target Return**: 25% annual
- **Risk Control**: Maximum drawdown <15%
- **ML Models**: Transformer (primary), LSTM, XGBoost ensemble
- **TDD Approach**: Complete test coverage
- **Real-time Trading**: Sub-second execution latency

## 💱 Supported Forex Pairs
1. **USD/ZAR** - High volatility (1000+ pips/day)
2. **GBP/JPY** - "The Dragon" (180 pips/day)
3. **AUD/JPY** - Commodity correlation
4. **USD/TRY** - Extreme volatility (1000-2000 pips)
5. **NZD/JPY** - Carry trade premium
6. **EUR/USD** - Maximum liquidity reference

## 🛠️ Technology Stack
- **Backend**: Python 3.11+
- **Database**: Supabase with TimescaleDB
- **Deployment**: Railway
- **APIs**: OANDA v20, Alpha Vantage, TraderMade
- **ML Framework**: TensorFlow, PyTorch, XGBoost

## 📁 Project Structure
```
BotTrader/
├── src/               # Source code
│   ├── core/         # Core bot logic
│   ├── data/         # Data ingestion & processing
│   ├── ml/           # Machine learning models
│   ├── strategies/   # Trading strategies
│   ├── execution/    # Order execution
│   └── monitoring/   # Performance monitoring
├── tests/            # TDD test suite
├── config/           # Configuration files
├── requirements/     # Project requirements
└── docker/           # Docker configuration
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Supabase account
- OANDA API credentials
- Railway account (for deployment)

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/BotTrader.git
cd BotTrader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp config/.env.example config/.env
# Edit config/.env with your credentials
```

### Configuration
1. Edit `config/.env` with your API credentials
2. Review `config/config.yaml` for trading parameters
3. Check `config/pairs_config.yaml` for forex pair settings
4. Adjust `config/ml_config.yaml` for ML model parameters

### Running Tests (TDD)
```bash
# Run all tests
make test

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
make test-coverage
```

### Running the Bot
```bash
# Development mode
make run-dev

# Production mode
make run-prod

# Docker mode
docker-compose up
```

## 📊 Performance Metrics
| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Annual Return | 25% | >20% |
| Sharpe Ratio | >1.2 | >0.75 |
| Max Drawdown | <15% | <20% |
| Win Rate | >60% | >55% |
| Profit Factor | >1.75 | >1.25 |

## 🔒 Risk Management
- **Position Sizing**: Kelly Criterion with 25% max position
- **Risk per Trade**: 2% maximum account risk
- **Portfolio Heat**: 5% maximum total exposure
- **Stop Loss**: Dynamic ATR-based stops
- **Correlation Limits**: Max 0.7 correlation between positions

## 📈 ML Models Configuration
### Transformer (Primary)
- 12 attention heads
- Sharpe ratio target: 4.4
- Expected return: 18.7%

### LSTM Hybrid
- 73% directional accuracy
- Macro + technical features

### XGBoost Ensemble
- 1000 estimators
- Feature importance ranking

## 🔧 Development Workflow

### TDD Cycle
1. **Red**: Write failing test
2. **Green**: Write minimal code to pass
3. **Refactor**: Improve code quality

### Implementation Phases (30 days)
- **Days 1-3**: Infrastructure setup
- **Days 4-7**: API connections
- **Days 8-14**: ML models training
- **Days 15-21**: Trading logic
- **Days 22-25**: Monitoring systems
- **Days 26-30**: Integration testing

## 📝 Documentation
Detailed documentation available in `/requirements/bot/`:
- `plan_tdd_completo_forex_bot.md` - Complete TDD plan
- `guia_implementacion_orden.md` - Implementation guide
- `configuraciones_especificas.md` - Technical configurations
- `ml_parameters_quantified_2025.md` - ML parameters

## ⚠️ Disclaimer
This is a trading system that involves substantial risk. Past performance does not guarantee future results. Use at your own risk.

## 📄 License
Proprietary - All rights reserved

## 🤝 Contributing
Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## 📧 Contact
For questions or support, please contact: [your-email@example.com]

---
**Version**: 1.0.0  
**Last Updated**: August 2025