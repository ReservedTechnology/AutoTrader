# 📚 BotTrader Requirements Documentation

## 🎯 Project Overview
Comprehensive documentation for the BotTrader Forex automated trading system designed to achieve 25% annual returns using advanced ML models and TDD methodology.

## 📁 Documentation Structure

### 📊 [01_overview/](./01_overview/)
High-level project documentation and summaries
- **README_TDD_FOREX_BOT.md** - Executive summary and project overview
- **INDEX.md** - Complete documentation index with reading order

### ⚙️ [02_technical_specs/](./02_technical_specs/)
Detailed technical specifications and configurations
- **configuraciones_especificas.md** - Specific configurations for each forex pair
- **forex_pairs_specifications_2025.md** - Detailed analysis of the 6 priority forex pairs

### 🚀 [03_implementation/](./03_implementation/)
Implementation guides and development plans
- **plan_tdd_completo_forex_bot.md** - Complete TDD plan with 14 organized tests
- **guia_implementacion_orden.md** - 30-day implementation timeline with 6 phases

### 📡 [04_data_sources/](./04_data_sources/)
API documentation and data source specifications
- **forex_data_apis_2025.md** - Real-time forex data APIs (OANDA, Alpha Vantage, TraderMade)
- **news_sentiment_sources_2025.md** - News and sentiment data sources (Reuters, Twitter, Reddit)
- **forex_analysis_data.json** - Historical data for 10 main forex pairs

### 🧠 [05_ml_models/](./05_ml_models/)
Machine learning models and parameters
- **ml_parameters_quantified_2025.md** - Specific ML parameters for 25% annual target

---

## 📈 Key Metrics and Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| **Annual Return** | 25% | >20% |
| **Sharpe Ratio** | >1.2 | >0.75 |
| **Max Drawdown** | <15% | <20% |
| **Win Rate** | >60% | >55% |
| **Profit Factor** | >1.75 | >1.25 |

## 💱 Priority Forex Pairs

1. **USD/ZAR** - Extreme volatility (1000+ pips/day)
2. **GBP/JPY** - "The Dragon" (180 pips/day)
3. **AUD/JPY** - Commodity correlation
4. **USD/TRY** - High volatility (1000-2000 pips)
5. **NZD/JPY** - Carry trade premium
6. **EUR/USD** - Maximum liquidity reference

## 🔧 Technology Stack

- **Infrastructure**: Railway + Supabase (TimescaleDB)
- **APIs**: OANDA v20, Alpha Vantage, TraderMade
- **ML Models**: Transformers (primary), LSTM, XGBoost
- **Sentiment Analysis**: FinBERT, VADER, Twitter API v2
- **Development**: Python 3.11+, TDD with pytest

## 📅 Implementation Timeline

### Phase Overview (30 days)
1. **Days 1-3**: Infrastructure setup (Supabase + Railway)
2. **Days 4-7**: API connections
3. **Days 8-14**: ML models training
4. **Days 15-21**: Trading logic implementation
5. **Days 22-25**: Monitoring systems
6. **Days 26-30**: Integration and testing

## 📖 Reading Order by Role

### For Developers
1. Start with `03_implementation/plan_tdd_completo_forex_bot.md`
2. Review `02_technical_specs/configuraciones_especificas.md`
3. Follow `03_implementation/guia_implementacion_orden.md`

### For Project Managers
1. Begin with `01_overview/README_TDD_FOREX_BOT.md`
2. Check `03_implementation/guia_implementacion_orden.md`
3. Review `01_overview/INDEX.md`

### For Data Scientists
1. Study `05_ml_models/ml_parameters_quantified_2025.md`
2. Review `02_technical_specs/forex_pairs_specifications_2025.md`
3. Examine `04_data_sources/` folder

## 🎯 Quick Reference

- **TDD Plan**: [plan_tdd_completo_forex_bot.md](./03_implementation/plan_tdd_completo_forex_bot.md)
- **Implementation Guide**: [guia_implementacion_orden.md](./03_implementation/guia_implementacion_orden.md)
- **ML Parameters**: [ml_parameters_quantified_2025.md](./05_ml_models/ml_parameters_quantified_2025.md)
- **API Documentation**: [forex_data_apis_2025.md](./04_data_sources/forex_data_apis_2025.md)

## ⚠️ Important Notes

- All configurations are optimized for 25% annual return target
- Maximum drawdown must not exceed 15% (critical at 20%)
- Use Kelly Criterion with restrictions (max 25% per trade)
- Focus on London-NY overlap (8AM-12PM ET) for 70% of trading volume

---

**Last Updated**: August 2025  
**Version**: 1.0  
**Author**: MiniMax Agent