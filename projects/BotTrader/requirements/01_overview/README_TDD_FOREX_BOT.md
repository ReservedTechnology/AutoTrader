# 🚀 Plan TDD Completo - Bot Trading Forex 25% Anual

> **Objetivo**: Sistema de trading forex automatizado con rendimientos anuales del 25%
> **Metodología**: Test-Driven Development (TDD) con especificaciones operacionales exactas
> **Autor**: MiniMax Agent | **Fecha**: 2025-08-28

## 📁 Estructura de Documentación

### 🎯 **ARCHIVO PRINCIPAL**
- **[`plan_tdd_completo_forex_bot.md`](./plan_tdd_completo_forex_bot.md)** - Plan TDD completo con todos los tests y prompts

### 📊 **ESPECIFICACIONES TÉCNICAS DETALLADAS**
- **[`forex_pairs_specifications_2025.md`](./forex_pairs_specifications_2025.md)** - 6 pares principales con análisis completo
- **[`forex_data_apis_2025.md`](./forex_data_apis_2025.md)** - APIs de datos en tiempo real (OANDA, Alpha Vantage)
- **[`news_sentiment_sources_2025.md`](./news_sentiment_sources_2025.md)** - Fuentes de noticias y sentiment
- **[`ml_parameters_quantified_2025.md`](./ml_parameters_quantified_2025.md)** - Parámetros ML para 25% anual

## 🎯 Resumen Ejecutivo

### **Pares de Trading Confirmados**
1. **USD/ZAR** - Volatilidad extrema (1000+ pips/día)
2. **GBP/JPY** - "El Dragón" (180 pips/día, equilibrio óptimo)
3. **AUD/JPY** - Correlación commodities
4. **USD/TRY** - Alta volatilidad (1000-2000 pips)
5. **NZD/JPY** - Carry trade premium
6. **EUR/USD** - Liquidez máxima (90 pips, spreads mínimos)

### **Stack Tecnológico**
- **Backend**: Railway (microservicios Python)
- **Base de Datos**: Supabase + TimescaleDB
- **APIs Datos**: OANDA v20 (primaria), Alpha Vantage, TraderMade
- **ML/IA**: Transformers (18 heads), LSTM híbrido, XGBoost
- **News**: Reuters API, ForexFactory, Twitter v2, Reddit

### **Métricas Objetivo**
- **Rendimiento Anual**: 25%
- **Sharpe Ratio**: >1.2 (objetivo), >2.0 (excelente)
- **Maximum Drawdown**: <15%
- **Win Rate**: >60%
- **Profit Factor**: >1.75

## 🗂️ Orden de Implementación TDD

### **FASE 1: Infraestructura** (Tests 1-2)
- Configuración Supabase TimescaleDB
- Deploy Railway microservicios

### **FASE 2: Conexiones de Datos** (Tests 3-5)
- APIs OANDA v20 WebSocket
- Alpha Vantage REST
- Fuentes de noticias

### **FASE 3: Procesamiento ML** (Tests 6-8)
- Modelos Transformer
- LSTM híbrido
- Sistema Ensemble

### **FASE 4: Trading Logic** (Tests 9-11)
- Generación de señales
- Gestión de riesgo Kelly
- Ejecución órdenes

### **FASE 5: Monitoreo** (Tests 12-13)
- Métricas tiempo real
- Sistema alertas

### **FASE 6: Integración** (Test 14)
- Validación end-to-end
- Tests producción

## 📈 Performance Esperada

### **Por Nivel de Capital**
| Capital | Pares | Posiciones | Retorno Esperado |
|---------|-------|------------|------------------|
| $10K | 2-3 | 1-2 | 15-25% |
| $50K | 4-6 | 3-5 | 20-30% |
| $100K+ | 6 | 5-10 | 25-35% |

### **Horarios Óptimos**
- **Londres-NY** (8AM-12PM ET): 70% del volumen
- **Asia-Londres** (3AM-8AM ET): Volatilidad JPY
- **Sydney-Asia** (5PM-3AM ET): AUD/NZD momentum

## ⚠️ Consideraciones Importantes

### **Factores de Riesgo**
- Market regime changes (políticas bancos centrales)
- Geopolitical events (guerras, crisis)
- Technical failures (API downtime, conexión)
- Overfitting models (concept drift)

### **Mitigación**
- Diversificación por pares y timeframes
- Stop-loss automáticos
- Position sizing conservador
- Monitoreo continuo performance

---

**🎯 NEXT STEPS**: Seguir el orden exacto de tests en `plan_tdd_completo_forex_bot.md`