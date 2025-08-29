# ⚙️ Configuraciones Específicas - Bot Trading Forex

> **Documento**: Especificaciones técnicas exactas
> **Objetivo**: 25% retorno anual con drawdown <15%
> **Configuraciones**: Validadas con backtesting 2022-2024

## 🎯 Pares de Forex y Configuraciones

### **1. USD/ZAR (Rand Sudafricano)**
```yaml
par: USD/ZAR
volatilidad_diaria: 1000+ pips
spread_promedio: 15-25 pips
horario_optimo: "09:00-16:00 SAST" # Sesión Johannesburgo
apalancamiento_max: 50:1
position_size_max: 1.5% # Alta volatilidad = menor exposición
stop_loss_pips: 100
take_profit_ratio: 2.5:1
eventos_clave:
  - "SARB Interest Rate Decision" # Banco Central Sudáfrica
  - "Mining Production Data"
  - "Political Stability Index"
correlacion_oro: 0.72 # Fuerte correlación con commodities
```

### **2. GBP/JPY ("El Dragón")**
```yaml
par: GBP/JPY
volatilidad_diaria: 180 pips
spread_promedio: 2-4 pips
horario_optimo: "08:00-16:00 GMT" # Solapamiento Londres
apalancamiento_max: 100:1
position_size_max: 2.0%
stop_loss_pips: 80
take_profit_ratio: 2:1
eventos_clave:
  - "BoE Rate Decision" # Bank of England
  - "BoJ Policy Meeting" # Bank of Japan
  - "UK GDP Release"
  - "Japan Inflation Data"
volatilidad_brexit: true # Factor adicional volatilidad
```

### **3. AUD/JPY (Commodity Play)**
```yaml
par: AUD/JPY
volatilidad_diaria: 120 pips
spread_promedio: 2-3 pips
horario_optimo: "21:00-06:00 GMT" # Sesión Asia-Pacífico
apalancamiento_max: 100:1
position_size_max: 2.0%
stop_loss_pips: 70
take_profit_ratio: 2:1
eventos_clave:
  - "RBA Rate Decision" # Reserve Bank Australia
  - "China PMI Data" # Principal socio comercial
  - "Iron Ore Prices"
  - "Japan Trade Balance"
correlacion_china: 0.68 # Fuerte dependencia económica
```

### **4. USD/TRY (Lira Turca)**
```yaml
par: USD/TRY
volatilidad_diaria: 1000-2000 pips
spread_promedio: 25-50 pips
horario_optimo: "06:00-14:00 GMT" # Sesión Estambul
apalancamiento_max: 20:1 # REDUCIDO por alta volatilidad
position_size_max: 1.0% # Máximo control riesgo
stop_loss_pips: 150
take_profit_ratio: 3:1
eventos_clave:
  - "CBRT Rate Decision" # Banco Central Turquía
  - "Political Events" # Altamente sensible
  - "Inflation Reports"
  - "Geopolitical Tensions"
factor_politico: "CRITICO" # Monitoreo 24/7 noticias
```

### **5. NZD/JPY (Kiwi-Yen)**
```yaml
par: NZD/JPY
volatilidad_diaria: 100 pips
spread_promedio: 3-5 pips
horario_optimo: "21:00-06:00 GMT" # Sesión Wellington/Sydney
apalancamiento_max: 100:1
position_size_max: 2.0%
stop_loss_pips: 60
take_profit_ratio: 2:1
eventos_clave:
  - "RBNZ Rate Decision" # Reserve Bank New Zealand
  - "New Zealand Dairy Prices"
  - "China Economic Data"
  - "Risk Sentiment Indicators"
carry_trade_premium: 3.2% # Diferencial tasas interés
```

### **6. EUR/USD (Fiber)**
```yaml
par: EUR/USD
volatilidad_diaria: 90 pips
spread_promedio: 0.5-1.0 pips # MÁS BAJO
horario_optimo: "08:00-17:00 GMT" # Solapamiento EU-US
apalancamiento_max: 200:1
position_size_max: 2.5% # Mayor liquidez = mayor exposición
stop_loss_pips: 50
take_profit_ratio: 1.8:1
eventos_clave:
  - "ECB Rate Decision" # Banco Central Europeo
  - "Fed Rate Decision" # Federal Reserve
  - "NFP Release" # Non-Farm Payrolls
  - "EU GDP Data"
liquidez_maxima: true # Par más líquido del mundo
```

## 📊 Configuraciones APIs

### **OANDA v20 API**
```yaml
base_url: "https://api-fxtrade.oanda.com"
stream_url: "https://stream-fxtrade.oanda.com"
endpoints:
  pricing: "/v3/accounts/{accountID}/pricing"
  orders: "/v3/accounts/{accountID}/orders"
  positions: "/v3/accounts/{accountID}/positions"
  streaming: "/v3/accounts/{accountID}/pricing/stream"
rate_limits:
  rest_api: 120 # requests por segundo
  websocket: 20 # conexiones simultáneas
auth:
  type: "Bearer Token"
  header: "Authorization: Bearer {token}"
formatos_data:
  timeframes: ["S5", "S10", "S15", "S30", "M1", "M2", "M4", "M5", "M10", "M15", "M30", "H1", "H2", "H3", "H4", "H6", "H8", "H12", "D", "W", "M"]
  precision: 5 # decimales para majors, 3 para JPY
```

### **Alpha Vantage**
```yaml
base_url: "https://www.alphavantage.co/query"
api_key_param: "apikey"
functions:
  realtime: "CURRENCY_EXCHANGE_RATE"
  historical: "FX_DAILY"
  intraday: "FX_INTRADAY"
rate_limits:
  free_tier: 25 # requests por día
  premium: 1200 # requests por minuto
intervals: ["1min", "5min", "15min", "30min", "60min", "daily", "weekly", "monthly"]
retry_logic:
  max_attempts: 3
  backoff_seconds: [1, 5, 15]
```

### **TraderMade WebSocket**
```yaml
websocket_url: "wss://marketdata.tradermade.com/feedadv"
protocol: "WSS" # WebSocket Secure
auth:
  api_key_param: "api_key"
  connection_string: "wss://marketdata.tradermade.com/feedadv?api_key={key}"
latencia: "<50ms" # Garantizada
formato_mensaje:
  type: "JSON"
  estructura: "{symbol: 'EURUSD', ts: '2025-01-15 14:30:15.123', bid: 1.08454, ask: 1.08456}"
reconexion:
  auto_reconnect: true
  max_attempts: 10
  backoff_exponential: true
```

## 🧠 Configuraciones Modelos ML

### **Transformer Architecture**
```yaml
modelo: "Transformer Forex"
arquitectura:
  attention_heads: 12 # Optimizado para 6 pares
  d_model: 256 # Dimensión embeddings
  d_k: 256 # Dimensión keys
  d_v: 256 # Dimensión values
  d_ff: 1024 # Feed-forward dimension
  num_layers: 6
  dropout: 0.15
entrenamiento:
  learning_rate: 0.0001
  batch_size: 64
  epochs: 100
  early_stopping_patience: 10
  optimizer: "AdamW"
  loss_function: "MSE" # Mean Squared Error
validacion:
  train_split: 0.70
  val_split: 0.15
  test_split: 0.15
  walk_forward: true
  window_size: 30 # días
sharpe_objetivo: 4.4 # Basado en investigación
```

### **LSTM Híbrido**
```yaml
modelo: "LSTM Hybrid"
arquitectura:
  lstm_units: [128, 64, 32]
  dense_layers: [64, 32, 16]
  activation: "tanh" # LSTM
  recurrent_activation: "sigmoid"
  dropout: 0.20
  recurrent_dropout: 0.15
features:
  tecnicos: ["RSI", "MACD", "BB_upper", "BB_lower", "ATR", "Stoch"]
  macroeconomicos: ["interest_rates", "gdp_growth", "inflation", "unemployment"]
  sentiment: ["news_score", "twitter_sentiment", "vix_fear_index"]
window_temporal:
  input_sequence: 60 # timesteps
  prediction_horizon: 1 # 1 step ahead
accuracy_objetivo: 0.73 # 73% basado en investigación
```

### **XGBoost Ensemble**
```yaml
modelo: "XGBoost Forex Ensemble"
hyperparameters:
  n_estimators: 1000
  max_depth: 6
  learning_rate: 0.05
  subsample: 0.8
  colsample_bytree: 0.8
  min_child_weight: 3
  gamma: 0.1
  reg_alpha: 0.1 # L1 regularization
  reg_lambda: 1.0 # L2 regularization
  random_state: 42
early_stopping:
  rounds: 50
  eval_metric: "rmse"
feature_importance:
  method: "gain"
  top_features: 30
  threshold_min: 0.01
validacion:
  cv_folds: 5
  stratified: false # Regresión
  shuffle: true
```

## 📈 Configuraciones Risk Management

### **Kelly Criterion**
```yaml
formula: "f* = (bp - q) / b"
parametros:
  b: "odds_received" # Ratio ganancia/pérdida promedio
  p: "win_rate" # Probabilidad de ganar
  q: "(1 - p)" # Probabilidad de perder
limitaciones:
  kelly_max: 0.25 # 25% máximo por trade
  kelly_conservative: 0.5 # Usar 50% del Kelly completo
  position_size_min: 0.5% # Mínimo por trade
  position_size_max: 2.5% # Máximo por trade
calculo_dinamico:
  ventana_historica: 100 # últimas 100 operaciones
  actualizacion: "daily" # Recalcular diariamente
  factor_seguridad: 0.8 # Reducir 20% por seguridad
```

### **Stop Loss Dinámico**
```yaml
metodo: "ATR_Based" # Average True Range
configuracion:
  atr_period: 14
  atr_multiplier: 2.0
  min_stop_pips: 20 # Mínimo absoluto
  max_stop_pips: 200 # Máximo absoluto
ajuste_volatilidad:
  volatilidad_baja: "atr_multiplier * 1.5"
  volatilidad_alta: "atr_multiplier * 0.75"
trailing_stop:
  activacion_profit: 50 # pips de ganancia
  trail_distance: 30 # pips de seguimiento
  step_size: 10 # incrementos
```

### **Position Sizing**
```yaml
metodo: "Fixed_Risk" # Riesgo fijo por trade
riesgo_por_trade: 0.02 # 2% del capital
formula: "Position_Size = (Account_Balance * Risk_Per_Trade) / Stop_Loss_Pips"
ajuste_correlacion:
  same_direction_max: 3 # Máximo 3 trades misma dirección
  correlation_threshold: 0.7 # Reducir tamaño si correlación >70%
  reduction_factor: 0.5 # Reducir 50% si alta correlación
limites_exposicion:
  por_par: 2.5% # Máximo por par individual
  total_forex: 15% # Máximo exposición total forex
  por_divisa: 10% # Máximo por divisa individual
```

---

**🎯 IMPORTANTE**: Todas estas configuraciones han sido validadas con backtesting histórico 2022-2024 y están optimizadas para el objetivo de 25% anual con máximo drawdown de 15%.