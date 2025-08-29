# Plan TDD Completo para Bot de Trading Forex - Especificaciones Operacionales Exactas

## Resumen Ejecutivo

Este plan TDD (Test-Driven Development) proporciona una estructura completa de tests organizados para desarrollar un bot de trading forex capaz de generar rendimientos anuales del 25%. Basado en la investigación de 4 documentos especializados, el plan incluye especificaciones técnicas precisas, parámetros cuantificados y prompts detallados para cada componente del sistema.

**Target de Performance**:
- Rendimiento anual: 25%
- Sharpe Ratio: >1.2
- Maximum Drawdown: <15%
- Profit Factor: >1.75

**Infraestructura Tecnológica**:
- Base de datos temporal: TimescaleDB en Railway (time-series data)
- Base de datos no temporal: Supabase (configuraciones, usuarios, trading history)
- Deployment: Railway
- APIs principales: OANDA v20, Alpha Vantage, TraderMade
- Modelos ML: Transformers (primario), LSTM, XGBoost

---

## 1. ESTRUCTURA DE TESTS ORGANIZADOS POR ORDEN DE EJECUCIÓN
### 1.1 Tests de Infraestructura (TimescaleDB en Railway, Supabase)
### 1.2 Tests de Conexiones API (OANDA v20, Alpha Vantage, TraderMade)
### 1.3 Tests de Ingesta de Datos (6 pares específicos, múltiples timeframes)
### 1.4 Tests de Modelos ML (Transformers, LSTM, XGBoost)
### 1.5 Tests de Generación de Señales (RSI 9-10, MACD 12,26,9)
### 1.6 Tests de Gestión de Riesgo (Kelly Criterion, position sizing)
### 1.7 Tests de Ejecución de Órdenes (Smart Order Routing)
### 1.8 Tests de Monitoreo (Sharpe >1.2, drawdown <15%)
### 1.9 Tests de Integración End-to-End

---

## 2. PROMPTS DETALLADOS PARA CADA CATEGORÍA DE TESTS

## 2.1 Tests de Infraestructura (TimescaleDB en Railway, Supabase)

### 2.1.1 Test de Configuración Dual: TimescaleDB (Railway) + Supabase

**Objetivo**: Verificar la configuración correcta del sistema de bases de datos dual: TimescaleDB en Railway para series temporales y Supabase para datos no temporales.

**Especificaciones Técnicas - TimescaleDB (Railway)**:
- **Base de datos**: PostgreSQL con extensión TimescaleDB en Railway
- **Tablas de series temporales**:
  - `forex_prices`: timestamp, symbol, bid, ask, spread, volume
  - `economic_calendar`: timestamp, currency, event, impact, actual, forecast, previous
  - `ml_predictions`: timestamp, symbol, model_type, prediction, confidence
  - `trading_signals`: timestamp, symbol, signal_type, strength, indicators_used
  - `live_positions`: timestamp, symbol, position_size, entry_price, stop_loss, take_profit

**Especificaciones Técnicas - Supabase**:
- **Base de datos**: PostgreSQL estándar en Supabase
- **Tablas no temporales**:
  - `users`: id, email, api_keys, settings, created_at
  - `trading_strategies`: id, name, parameters, active, created_at
  - `closed_trades`: id, symbol, entry_time, exit_time, profit_loss, strategy_used
  - `system_config`: key, value, description, updated_at
  - `ml_model_versions`: id, model_type, version, parameters, performance_metrics

**Configuraciones Específicas - TimescaleDB (Railway)**:
- **Particionado temporal**: Por día para tablas de precios
- **Índices**: timestamp + symbol para todas las tablas de series temporales
- **Retención de datos**: 2 años para precios históricos, 30 días para señales
- **Compresión**: Automática cada 7 días para datos >1 semana
- **Chunks**: 1 día para forex_prices, 7 días para otras tablas

**Configuraciones Específicas - Supabase**:
- **Row-Level Security (RLS)**: Habilitado para todas las tablas
- **Realtime subscriptions**: Para system_config y trading_strategies
- **Backup**: Automático diario con retención de 30 días
- **Índices**: Por id y created_at para queries eficientes

**Criterios de Aceptación - Sistema Dual**:
- Conexión exitosa a TimescaleDB en Railway para datos temporales
- Conexión exitosa a Supabase para datos no temporales
- TimescaleDB extension activada y funcional en Railway
- Creación de hypertables para series temporales en Railway
- Inserción de >10K registros de prueba en <5 segundos (TimescaleDB)
- Consultas de agregación (OHLC diario) completadas en <500ms (TimescaleDB)
- Sincronización de closed_trades entre TimescaleDB y Supabase
- Queries cross-database funcionando correctamente

**Consideraciones de Arquitectura - Sistema Dual**:
- Connection pooling separado para cada base de datos
- Sincronización asíncrona de trades cerrados a Supabase
- Cache Redis para reducir queries cross-database
- Monitoring de performance para ambas bases de datos
- Fallback a Supabase si TimescaleDB no disponible (read-only mode)
- Data consistency checks entre ambas bases de datos

### 2.1.2 Test de Deployment en Railway con TimescaleDB

**Objetivo**: Validar el deployment automatizado de la aplicación y TimescaleDB en Railway.

**Especificaciones de Deployment**:
- **Runtime**: Python 3.11+ con requirements.txt
- **Database Service**: PostgreSQL con TimescaleDB extension
- **Environment variables**: 
  - `TIMESCALE_URL`, `TIMESCALE_USER`, `TIMESCALE_PASSWORD` (Railway)
  - `SUPABASE_URL`, `SUPABASE_KEY` (Supabase)
  - `OANDA_API_KEY`, `OANDA_ACCOUNT_ID`
  - `ALPHA_VANTAGE_KEY`, `TRADERMADE_KEY`
- **Health checks**: 
  - Endpoint `/health` respondiendo status 200
  - Endpoint `/health/db` verificando ambas conexiones
- **Resource limits**: 
  - App: 512MB RAM mínimo, 1GB recomendado
  - TimescaleDB: 1GB RAM mínimo, 2GB recomendado

**Criterios de Aceptación**:
- Build exitoso desde GitHub repository
- Aplicación accesible via URL public railway.app
- TimescaleDB service running en Railway
- Variables de entorno configuradas para ambas DBs
- Logs estructurados disponibles en Railway dashboard
- Health check endpoints verificando ambas DBs
- Restart automático en caso de crash
- Data persistence verificada tras restart

**Patrones de Desarrollo Recomendados**:
- Usar Docker con multi-stage builds para optimización
- Implementar graceful shutdown para procesos largos
- Configurar CI/CD pipeline con GitHub Actions
- Separar configuraciones dev/staging/production

---

## 2.2 Tests de Conexiones API (OANDA v20, Alpha Vantage, TraderMade)

### 2.2.1 Test de Conexión OANDA v20 API

**Objetivo**: Verificar conectividad completa con OANDA v20 para datos en tiempo real y ejecución de órdenes.

**Especificaciones de Conexión**:
- **Base URL Live**: `https://api-fxtrade.oanda.com`
- **Base URL Practice**: `https://api-fxpractice.oanda.com`
- **Autenticación**: Bearer token en header `Authorization: Bearer <token>`
- **Rate limits**: 120 requests/segundo por IP
- **Streaming**: 20 conexiones simultáneas máximo por IP

**Endpoints Críticos a Testear**:
- `/v3/accounts`: Validar acceso a cuenta
- `/v3/instruments`: Listar instrumentos disponibles
- `/v3/pricing/stream`: WebSocket para precios en tiempo real
- `/v3/orders`: Creación y gestión de órdenes
- `/v3/positions`: Consulta de posiciones abiertas

**Configuraciones Específicas por Par Forex**:
- **USD/ZAR**: Spread típico 15-25 pips, volatilidad 1000+ pips/día
- **GBP/JPY**: Spread típico 0.5-2.0 pips, volatilidad 180 pips/día
- **AUD/JPY**: Spread típico 1.2-1.8 pips, volatilidad alta
- **USD/TRY**: Spread típico 20-40 pips, volatilidad 1000-2000 pips/día
- **NZD/JPY**: Spread variable, volatilidad extrema
- **EUR/USD**: Spread típico 0.8-1.11 pips, volatilidad 90 pips/día

**Criterios de Aceptación**:
- Autenticación exitosa y acceso a account details
- Streaming de precios funcional con latencia <50ms
- Rate limiting respetado sin errors 429
- Respuesta JSON válida en todos los endpoints
- Reconexión automática en caso de disconnect WebSocket

### 2.2.2 Test de Conexión Alpha Vantage API

**Objetivo**: Validar acceso a datos históricos y técnicos desde Alpha Vantage.

**Especificaciones de API**:
- **Base URL**: `https://www.alphavantage.co/query`
- **Autenticación**: API key como parámetro `apikey=YOUR_KEY`
- **Rate limits**: 25 calls/día (free), ilimitado (premium)
- **Funciones forex específicas**: `FX_DAILY`, `FX_INTRADAY`, `CURRENCY_EXCHANGE_RATE`

**Parámetros de Consulta por Timeframe**:
- **Intradía**: Intervalos 1min, 5min, 15min, 30min, 60min
- **Daily**: Datos diarios históricos extensos
- **Real-time**: Tasa de cambio actual

**Criterios de Aceptación**:
- Respuesta exitosa para los 6 pares forex prioritarios
- Datos históricos disponibles para mínimo 2 años
- Formato JSON válido con timestamps UTC
- Error handling para rate limit exceeded
- Datos técnicos (RSI, MACD, BB) disponibles y calculados correctamente

### 2.2.3 Test de Conexión TraderMade WebSocket

**Objetivo**: Implementar streaming de baja latencia para datos de precio en tiempo real.

**Especificaciones WebSocket**:
- **URL**: `wss://marketdata.tradermade.com/feedadv`
- **Protocolo**: WSS (WebSocket Secure)
- **Autenticación**: userKey en mensaje inicial de conexión
- **Formato datos**: JSON con {symbol, ts, bid, ask, mid}
- **Latencia target**: <50ms

**Configuración de Suscripción**:
```json
{
  "userKey": "API_KEY",
  "symbol": "EURUSD,GBPUSD,USDJPY,AUDJPY,NZDJPY,USDZAR,USDTRY"
}
```

**Criterios de Aceptación**:
- Conexión WebSocket estable durante >1 hora
- Recepción de datos para los 7 símbolos suscritos
- Latencia promedio <50ms desde market event
- Reconexión automática en caso de disconnect
- Buffer de datos para evitar pérdida durante reconexiones

---

## 2.3 Tests de Ingesta de Datos (6 pares específicos, múltiples timeframes)

### 2.3.1 Test de Ingesta Multi-Timeframe

**Objetivo**: Validar la ingesta simultánea y sincronizada de datos para múltiples timeframes y pares de divisas.

**Especificaciones de Timeframes**:
- **Primarios**: 4H (recomendado para mejor señal/ruido ratio)
- **Confirmación**: Daily (máxima calidad de señal)
- **Intradía**: 5min, 15min (para day trading activo)
- **Referencia**: 1H (swing intradiario)

**Pares Forex Prioritarios y Características**:
1. **USD/ZAR**: Volatilidad 1000+ pips/día, sensible a commodities
2. **GBP/JPY**: Volatilidad 180 pips, "El Dragón"
3. **AUD/JPY**: Correlación +82 con EUR/JPY, sensible a China
4. **USD/TRY**: Volatilidad 1000-2000 pips, inflación alta
5. **NZD/JPY**: Extrema volatilidad, commodities agrícolas
6. **EUR/USD**: 90 pips promedio, máxima liquidez

**Horarios Óptimos por Par**:
- **Solapamiento Londres-Nueva York**: 8:00 AM - 12:00 PM ET (70% volumen global)
- **GBP/JPY, AUD/JPY**: Durante solapamiento + apertura asiática
- **USD/ZAR**: Sesión Londres (3 AM - 12 PM ET)
- **EUR/USD**: Todo el solapamiento Londres-NY

**Criterios de Aceptación**:
- Ingesta sin pérdidas durante horarios de alta volatilidad
- Sincronización correcta entre timeframes (5min, 15min, 1H, 4H, Daily)
- Almacenamiento de OHLCV + spread para cada timeframe
- Detección y manejo de gaps en datos de fin de semana
- Validación de calidad: detección de datos anómalos (spikes >5 sigma)

### 2.3.2 Test de Procesamiento de Noticias y Sentiment

**Objetivo**: Integrar feeds de noticias económicas y análisis de sentiment en tiempo real.

**Fuentes de Noticias Configuradas**:
- **ForexFactory**: Calendario económico con filtro de impacto alto
- **Investing.com**: Economic calendar para 14 divisas principales
- **Twitter API v2**: Hashtags relevantes (#EURUSD, #forex, #ForexMarketAnalysis)
- **Reddit API**: Subreddits r/forex, r/algotrading

**Configuración de Análisis de Sentiment**:
- **Modelo Principal**: FinBERT para análisis financiero especializado
- **Backup**: VADER Sentiment para redes sociales
- **Score Range**: -1.5 (muy negativo) a +1.5 (muy positivo)
- **Umbral de señal**: |sentiment| > 0.3 para consideración

**Criterios de Aceptación**:
- Ingesta de mínimo 50 eventos económicos/día de alto impacto
- Análisis de sentiment de >100 tweets/hora para pares principales
- Correlación de eventos news con movimientos de precio >±50 pips
- Storage de sentiment scores con timestamp para analysis posterior
- Rate limiting compliance para todas las APIs sociales

---

## 2.4 Tests de Modelos ML (Transformers, LSTM, XGBoost)

### 2.4.1 Test de Modelo Transformer Principal

**Objetivo**: Implementar y validar el modelo Transformer optimizado para predicción forex según especificaciones de research.

**Arquitectura del Transformer**:
- **Tipo**: Encoder-only Transformer con Time2Vec embeddings
- **Attention heads**: 12 cabezas de atención
- **Input features**: 1,273 características técnicas y fundamentales
- **Sequence length**: 128 períodos
- **Dimensiones**: Key/Query/Value = 256

**Parámetros de Entrenamiento**:
- **Batch size**: 32
- **Epochs**: 100
- **Learning rate**: 0.0001
- **Optimizer**: Adam
- **Loss function**: Mean Squared Error (MSE)
- **Validación**: Walk-forward analysis 70%/30%

**Features de Entrada Específicas**:
- **Técnicas**: RSI(9), MACD(12,26,9), Bollinger Bands(20,2), ATR(14)
- **Macroeconómicas**: Tasas de interés, inflación, índices S&P 500, DAX
- **Sentiment**: Scores de noticias y social media (-1.5 a +1.5)
- **Volatilidad**: ATR, implied volatility, spreads

**Targets de Performance Esperados** (basados en research):
- **EURUSD**: 9.2% retorno anual, Sharpe ratio 2.4
- **USDJPY**: 22.9% retorno anual, Sharpe ratio 5.5
- **GBPUSD**: 24.1% retorno anual, Sharpe ratio 5.2
- **Promedio objetivo**: 18.7% retornos, 4.4 Sharpe ratio

**Criterios de Aceptación**:
- Sharpe ratio >2.0 en validation set
- Maximum drawdown <20% durante backtesting
- Prediction accuracy >60% para direccionalidad
- Latencia de predicción <100ms por inference
- Estabilidad de performance en walk-forward analysis

### 2.4.2 Test de Modelo LSTM Híbrido

**Objetivo**: Implementar arquitectura LSTM híbrida como modelo complementario y backup.

**Arquitectura Híbrida Específica**:
- **ME-LSTM**: Macro-Economic LSTM para features fundamentales
- **TI-LSTM**: Technical Indicators LSTM para análisis técnico
- **ME-TI-LSTM**: Modelo mixto combinando ambos enfoques

**Features por Componente**:
- **ME-LSTM**: Tasas de interés, inflación, S&P 500, DAX, EUR/USD base
- **TI-LSTM**: MA(10), MACD(12,26), ROC(2), Momentum(4), RSI(10), BB(20), CCI(20)

**Performance Target** (basado en research):
- **Profit accuracy**: 73-79% promedio según horizonte
- **Complementariedad**: Correlation <0.7 con Transformer predictions

**Criterios de Aceptación**:
- Accuracy direccional >70% en test set
- Performance diferenciada vs Transformer (diversificación)
- Tiempo de entrenamiento <2 horas en GPU estándar
- Memory footprint <2GB durante inference

### 2.4.3 Test de Modelo XGBoost Ensemble

**Objetivo**: Desarrollar modelo XGBoost como component de ensemble y validación cruzada.

**Hiperparámetros Base** (requieren optimización específica):
- **n_estimators**: 100-1000 (optimizar via grid search)
- **max_depth**: 3-10 (balance overfitting vs capacity)
- **learning_rate**: 0.01-0.3 (típicamente 0.1 inicial)
- **subsample**: 0.8-1.0
- **colsample_bytree**: 0.8-1.0

**Feature Engineering Específico**:
- **Lag features**: Precios t-1, t-2, t-5, t-10
- **Rolling statistics**: MA, STD, percentiles over 20, 50 períodos
- **Interacciones**: RSI × MACD, BB position × volatility
- **Time features**: Hour, day_of_week, month (seasonality)

**Criterios de Aceptación**:
- Performance comparable con otros modelos (Sharpe >1.0)
- Feature importance analysis interpretable
- Resistencia a overfitting (validation curve estable)
- Ensemble contribution positiva (weight >0.2 en voting)

---

## 2.5 Tests de Generación de Señales (RSI 9-10, MACD 12,26,9)

### 2.5.1 Test de RSI Optimizado por Timeframe

**Objetivo**: Validar configuraciones RSI específicas según el style de trading y timeframe.

**Configuraciones RSI por Estrategia**:
- **Day Trading (5-15min)**: RSI(9-10), niveles 75/25, alta sensibilidad
- **Active Trading (15-60min)**: RSI(10-12), niveles 70/30, moderada sensibilidad
- **Swing Trading (4H-Daily)**: RSI(14), niveles 70/30, baja sensibilidad

**Parámetros de Señal Específicos**:
- **Oversold entry**: RSI < 25 (day trading), RSI < 30 (swing)
- **Overbought exit**: RSI > 75 (day trading), RSI > 70 (swing)
- **Momentum confirmation**: RSI slope > 5 puntos/período
- **Divergence detection**: Price vs RSI correlation <-0.5

**Criterios de Aceptación**:
- Signal generation latency <10ms post price update
- False positive rate <30% en condiciones normales de mercado
- Sensitivity adjustment automático según volatility regime
- Integration con ML predictions (correlation >0.4)

### 2.5.2 Test de MACD Multi-Configuración

**Objetivo**: Implementar sistema MACD adaptativo para diferentes condiciones de mercado.

**Configuraciones MACD por Condición**:
- **Estándar**: (12, 26, 9) para condiciones normales
- **Sensible**: (8, 17, 9) para day trading activo
- **Muy rápida**: (5, 35, 5) para alta frecuencia

**Tipos de Señales MACD**:
- **Line cross**: MACD line cruza signal line
- **Zero cross**: MACD line cruza nivel zero
- **Histogram**: Cambios en momentum (histogram slope)
- **Divergence**: MACD vs price action divergence

**Criterios de Aceptación**:
- Detección correcta de crossovers con 0 lag false signals
- Filtrado de whipsaws en mercados laterales
- Integration con volatility filters (ATR threshold)
- Backtested win rate >55% en condiciones trending

### 2.5.3 Test de Bollinger Bands Dinámicos

**Objetivo**: Implementar Bollinger Bands adaptativos según volatilidad del mercado.

**Configuración Adaptativa**:
- **Período base**: 20-day SMA estándar
- **Desviaciones estándar**:
  - Baja volatilidad (ATR percentile <25%): 1.5 SD
  - Normal volatilidad (ATR percentile 25-75%): 2.0 SD
  - Alta volatilidad (ATR percentile >75%): 2.5 SD

**Señales Bollinger Específicas**:
- **Band squeeze**: Bandwidth < percentile 10 → breakout pending
- **Band expansion**: Bandwidth > percentile 90 → trend continuation
- **Mean reversion**: Price touch banda + RSI confirmation
- **Breakout**: Price close beyond banda + volume confirmation

**Criterios de Aceptación**:
- Squeeze detection accuracy >80% para predicción breakouts
- Mean reversion signals con win rate >60%
- Adaptive period adjustment según market regime
- Integration con ML confidence scores

---

## 2.6 Tests de Gestión de Riesgo (Kelly Criterion, Position Sizing)

### 2.6.1 Test de Kelly Criterion con Restricciones

**Objetivo**: Implementar position sizing óptimo usando Kelly Criterion modificado para control de drawdown.

**Fórmulas Kelly Implementadas**:
- **Kelly Básico**: f* = (bp - q) / b
  - b = ratio ganancia/pérdida promedio
  - p = probabilidad de ganar
  - q = probabilidad de perder (1-p)

- **Kelly con Restricciones**: Incluye límite de riqueza mínima
  - Restricción: Prob(Wealth < α) < β
  - α = objetivo riqueza mínima (0.5-0.8)
  - β = límite probabilidad de caída

**Parámetros de Riesgo Específicos**:
- **Account risk máximo**: 2% por trade (retail trader standard)
- **Position size máximo**: 25% del capital (Kelly restringido)
- **Kelly % típico**: 10-37% según historical performance
- **Drawdown limit**: Stop operativo a 15% portfolio drawdown

**Criterios de Aceptación**:
- Position sizes nunca exceden 25% del capital total
- Kelly calculation completa en <50ms
- Adjustment automático basado en rolling win/loss statistics
- Portfolio heat monitoring con alertas a 10% total risk

### 2.6.2 Test de Multi-Asset Position Sizing

**Objetivo**: Gestionar exposición simultánea across múltiples pares forex con correlaciones.

**Matriz de Correlaciones Críticas**:
- **EUR/USD vs GBP/USD**: +84% (evitar over-exposure)
- **AUD/JPY vs EUR/JPY**: +82% (diversificación limitada)
- **EUR/USD vs USD/JPY**: -80% (cobertura natural)
- **GBP/USD vs USD/JPY**: -86% (cobertura fuerte)

**Reglas de Exposición**:
- **Maximum portfolio exposure**: 5% simultáneo total
- **Correlated pairs limit**: No >2 pares con correlation >0.8
- **Single currency exposure**: No >10% exposure a USD, EUR, JPY
- **Emerging market limit**: No >15% exposure a ZAR, TRY combinados

**Criterios de Aceptación**:
- Correlation matrix updated diariamente con 30-day rolling window
- Position rejection automática si excede correlation limits
- Portfolio diversification score >0.6 (scale 0-1)
- Real-time exposure monitoring dashboard

### 2.6.3 Test de Dynamic Stop Loss y Take Profit

**Objetivo**: Implementar stops dinámicos basados en volatilidad y market conditions.

**ATR-Based Stop Loss**:
- **Cálculo**: Stop distance = ATR(14) × multiplier
- **Multipliers por volatility**:
  - Baja volatilidad: 1.5 × ATR
  - Normal volatilidad: 2.0 × ATR
  - Alta volatilidad: 2.5-3.0 × ATR

**Take Profit Dinámico**:
- **Risk/Reward ratio mínimo**: 1:1.5 (conservative)
- **Target optimal**: 1:2.0 basado en historical data
- **Trailing stop**: Activate when profit >1.5x initial risk
- **Partial profits**: Close 50% position at 1:1, rest trails

**Criterios de Aceptación**:
- Stop loss adjustment automático con volatility changes
- Take profit triggers funcionando sin slippage >5 pips
- Trailing stops capturing >70% de favorable moves
- Risk/reward maintenance según market regime

---

## 2.7 Tests de Ejecución de Órdenes (Smart Order Routing)

### 2.7.1 Test de Smart Order Routing

**Objetivo**: Implementar routing inteligente de órdenes para minimizar slippage y optimizar fills.

**Algoritmos de Ejecución**:
- **VWAP (Volume Weighted Average Price)**: Para órdenes grandes
- **TWAP (Time Weighted Average Price)**: Para ejecución gradual
- **Market timing**: Execution durante horarios de alta liquidez
- **Iceberg orders**: Fragmentar órdenes grandes (>100K units)

**Timing Óptimo por Par**:
- **EUR/USD, GBP/USD**: Durante solapamiento Londres-NY (8AM-12PM ET)
- **JPY pairs**: Durante overlap Tokyo-London + NY sessions
- **Exotic pairs (ZAR, TRY)**: Durante London session únicamente
- **London Fix timing**: 15-30min antes 4PM London para volatility

**Criterios de Aceptación**:
- Slippage promedio <2 pips para major pairs, <5 pips exotic pairs
- Orden fill rate >95% durante horarios normales
- Execution latency <200ms desde signal generation
- Smart routing evita impact >0.5% en spread durante execution

### 2.7.2 Test de Partial Fills y Order Management

**Objetivo**: Gestionar ejecuciones parciales y manejo avanzado de órdenes.

**Escenarios de Partial Fills**:
- **Large orders**: Split en chunks de max 50K units
- **Low liquidity periods**: Accept partial fills >80% size
- **High volatility**: Cancel y re-submit if partial <50%
- **Weekend gaps**: Special handling para Sunday opens

**Order Types Soportados**:
- **Market orders**: Ejecución inmediata, slippage acceptable
- **Limit orders**: Price improvement opportunities
- **Stop orders**: Risk management automation
- **OCO (One-Cancels-Other)**: Advanced order management

**Criterios de Aceptación**:
- Partial fill aggregation correcta hasta complete fill
- Order cancellation dentro 100ms si required
- Proper handling de rejected orders con retry logic
- Commission calculation accuracy dentro 1bp

---

## 2.8 Tests de Monitoreo (Sharpe >1.2, Drawdown <15%)

### 2.8.1 Test de Real-Time Performance Monitoring

**Objetivo**: Implementar monitoring continuo de métricas clave de performance y riesgo.

**Métricas Críticas en Tiempo Real**:
- **Sharpe Ratio**: Target >1.2, alert si <0.75, stop si <0.5
- **Maximum Drawdown**: Target <15%, alert 10%, stop 20%
- **Profit Factor**: Target >1.75, acceptable >1.25
- **Win Rate**: Monitor trend, alert si decline >10% sustained
- **Daily PnL**: Track vs expected (+0.07% daily para 25% annual)

**Ventanas de Cálculo**:
- **Intraday**: Rolling 4-hour windows durante trading activo
- **Daily**: Rolling 30-day Sharpe, 90-day drawdown analysis
- **Weekly**: Performance vs benchmark, risk-adjusted returns
- **Monthly**: Deep dive analysis, strategy adjustment signals

**Criterios de Aceptación**:
- Metric calculation latency <1 segundo
- Alert system functional con notifications push/email
- Dashboard update real-time durante market hours
- Historical metric storage para trend analysis

### 2.8.2 Test de Automatic Trading Halt Systems

**Objetivo**: Implementar sistemas automáticos de parada para protección de capital.

**Trigger Conditions**:
- **Hard Stop**: Maximum drawdown >20% (emergency halt)
- **Soft Warning**: Sharpe ratio <0.75 por 5 días consecutivos
- **Volatility Circuit Breaker**: Market volatility >5 sigma event
- **Technical Error**: API connectivity issues >5 minutos
- **Model Degradation**: Prediction accuracy <45% por 48 horas

**Recovery Protocols**:
- **Gradual Restart**: Reduce position sizes 50% post-halt
- **Model Retraining**: Trigger automático si accuracy decline
- **Manual Override**: Requiere human approval para restart
- **Risk Reassessment**: Full risk model review requerido

**Criterios de Aceptación**:
- Halt system response time <30 segundos
- Position closure completed <2 minutos durante halt
- Proper logging de halt reasons y recovery actions
- Alert escalation funcional (email + SMS + dashboard)

### 2.8.3 Test de Regime Change Detection

**Objetivo**: Detectar cambios en regime de mercado que afecten strategy performance.

**Indicadores de Regime Change**:
- **Volatility Shift**: ATR change >50% sustained 5+ days
- **Correlation Breakdown**: Historical correlations change >0.3
- **Volume Pattern Changes**: Volume profile disruption
- **Central Bank Policy**: Interest rate decisions impact
- **Geopolitical Events**: News sentiment extremes

**Adaptive Responses**:
- **Position Size Reduction**: Reduce exposure 30-50% durante uncertainty
- **Model Rebalancing**: Adjust ML model weights por regime
- **Strategy Switching**: Activate mean reversion vs trend following
- **Risk Parameter Adjustment**: Tighten stops, reduce leverage

**Criterios de Aceptación**:
- Regime change detection dentro 24-48 horas
- Strategy adaptation automática basada en regime type
- Performance tracking per regime para optimization
- Human notification para major regime shifts

---

## 2.9 Tests de Integración End-to-End

### 2.9.1 Test de Pipeline Completo de Trading

**Objetivo**: Validar el flujo completo desde data ingestion hasta order execution en un ambiente realista.

**Flujo End-to-End Completo**:
1. **Data Ingestion**: Múltiples APIs simultáneas (OANDA, TraderMade, Alpha Vantage)
2. **Feature Engineering**: Indicadores técnicos + sentiment + macro data
3. **ML Prediction**: Ensemble prediction (Transformer + LSTM + XGBoost)
4. **Signal Generation**: RSI + MACD + BB confirmation
5. **Risk Management**: Position sizing, correlation check, drawdown validation
6. **Order Execution**: Smart routing, partial fill handling
7. **Monitoring**: Real-time metrics update, performance tracking

**Ambiente de Testing**:
- **Duración**: 72 horas continuas de operación
- **Condiciones**: Mix de low/normal/high volatility periods
- **Data volume**: >50K price updates procesados
- **Trades**: Minimum 20 señales ejecutadas completamente

**Criterios de Aceptación**:
- Zero data loss durante el periodo de testing
- Latency total (data → execution) <500ms percentile 95
- All components functioning sin critical errors
- Performance metrics dentro de ranges esperados

### 2.9.2 Test de Disaster Recovery

**Objetivo**: Validar recuperación completa del sistema ante fallos críticos.

**Scenarios de Fallo**:
- **API Outage**: Primary data provider down >5 minutos
- **Database Failure**: TimescaleDB o Supabase connectivity lost
- **Model Failure**: ML prediction accuracy drops <30%
- **Network Issues**: Internet connectivity intermittent
- **Railway Deployment**: Application crash o memory issues

**Recovery Procedures**:
- **Failover**: Automatic switch a backup data providers
- **Graceful Degradation**: Operate con subset de features si needed
- **Position Safety**: Close all positions si critical failure detected
- **Data Recovery**: Restore from backup within 15 minutos
- **Manual Override**: Human takeover capabilities

**Criterios de Aceptación**:
- Failover automation completo <2 minutos
- Zero position abandonment durante recovery
- Data integrity mantenida post-recovery
- Full system restoration documented y tested
- Alert system functional durante all failure scenarios

---

## 3. CONSIDERACIONES DE IMPLEMENTACIÓN

### 3.1 Patrones de Desarrollo Recomendados

**Arquitectura**:
- **Microservices**: Separate data ingestion, ML training, signal generation, execution
- **Event-driven**: Use message queues (Redis/RabbitMQ) para component communication
- **Containerization**: Docker containers para consistent deployment
- **CI/CD**: GitHub Actions para automated testing y deployment

**Testing Strategy**:
- **Unit Tests**: 80%+ code coverage para business logic crítica
- **Integration Tests**: API connectivity y data flow validation
- **Performance Tests**: Load testing con synthetic market data
- **End-to-End Tests**: Full pipeline validation weekly

### 3.2 Métricas de Success y KPIs

**Performance Targets**:
- **Annual Return**: 25% target, 20% acceptable minimum
- **Sharpe Ratio**: >1.2 target, >0.75 minimum acceptable
- **Maximum Drawdown**: <15% target, <25% absolute limit
- **Win Rate**: >55% target para trend strategies
- **Profit Factor**: >1.75 target, >1.25 minimum

**Operational Metrics**:
- **System Uptime**: >99.5% durante market hours
- **Data Quality**: <0.1% missing/corrupt data points
- **Execution Quality**: <2 pips average slippage majors
- **Latency**: <500ms end-to-end processing time

### 3.3 Risk Management Framework

**Capital Protection**:
- **Stop Loss**: Never risk >2% account per trade
- **Portfolio Heat**: Max 5% total exposure simultaneous
- **Correlation Limits**: Avoid over-concentration correlated positions
- **Emergency Stops**: Automatic halt sistema para protection extrema

**Model Risk Management**:
- **Out-of-Sample Validation**: Continuous walk-forward analysis
- **Model Ensemble**: Multiple models para reduce single-model risk
- **Performance Monitoring**: Continuous tracking vs expectations
- **Retraining Schedule**: Regular model updates basado en performance

---

## 4. CONCLUSIÓN

Este plan TDD completo proporciona una estructura detallada para desarrollar un bot de trading forex sofisticado capaz de lograr rendimientos anuales del 25% mientras mantiene riesgo controlado. La implementación exitosa requiere:

1. **Disciplina en Testing**: Seguir el orden de ejecución y criteria estrictos
2. **Focus en Calidad**: Priorizar reliability over complexity
3. **Risk Management**: Implement safeguards en every stage
4. **Continuous Monitoring**: Real-time performance tracking essential
5. **Adaptability**: Ready para adjust ante changing market conditions

La inversión en comprehensive testing al inicio del proyecto pagará dividendos significativos en la reliability y profitability del sistema final.

---

**Próximos Pasos**:
1. Setup inicial infrastructure (TimescaleDB en Railway + Supabase)
2. Implement tests de infrastructure y connectivity
3. Desarrollar data ingestion pipeline
4. Train y validate ML models
5. Implement risk management systems
6. Deploy y begin paper trading validation

**Autor**: MiniMax Agent  
**Fecha**: 28 de Agosto, 2025  
**Versión**: 1.0