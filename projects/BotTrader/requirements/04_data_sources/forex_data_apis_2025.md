# APIs de Datos Forex en Tiempo Real - Guía Completa 2025

## Resumen Ejecutivo

Esta guía proporciona documentación detallada sobre las principales APIs para datos de forex en tiempo real disponibles en 2025. La investigación cubre endpoints específicos, métodos de autenticación, límites de rate, costos y capacidades de WebSocket para cada proveedor. Las APIs analizadas incluyen soluciones tanto para desarrolladores individuales como para aplicaciones empresariales.

## 1. OANDA v20 API

### 1.1 Información General
La OANDA v20 REST API proporciona acceso al motor de trading v20 con capacidades de datos en tiempo real, información histórica desde 2005, y funcionalidades completas de trading[1].

### 1.2 Endpoints Específicos

#### Endpoints Principales
- **Base URL (Live)**: `https://api-fxtrade.oanda.com`
- **Base URL (Practice)**: `https://api-fxpractice.oanda.com`
- **Formato de contenido**: `application/json`

#### Endpoints de Datos de Mercado
- **Precios en Tiempo Real**: `/v3/pricing/prices`
  - Proporciona cotizaciones en tiempo real para pares comerciables 24 horas al día
  - Parámetros: account_id, instruments
- **Datos Históricos**: `/v3/pricing/historical`
  - Acceso a precios históricos desde 2005
- **Streaming de Precios**: Via WebSocket API
  - URL Base Streaming: `https://stream-fxtrade.oanda.com`

### 1.3 Autenticación
- **Método**: Personal Access Token
- **Generación**: Portal de Gestión de Cuentas (AMP) → "My Services" → "Manage API Access"
- **Compatibilidad**: Válido para API legacy y v20
- **Header requerido**: `Authorization: Bearer <access_token>`

### 1.4 Límites de Rate y Restricciones

| Tipo | Límite | Alcance |
|------|--------|---------|
| REST API | 120 solicitudes/segundo | Por IP |
| Streaming API | 20 conexiones activas | Por IP |
| Nuevas conexiones | 2 conexiones/segundo | Por IP |
| Exceso de solicitudes | HTTP 429 error | - |

### 1.5 Capacidades de Streaming/WebSocket
- **Streaming en tiempo real** disponible para precios y eventos
- **Formato**: JSON estándar
- **Conexiones simultáneas**: Máximo 20 por IP
- **Protocolos soportados**: WebSocket nativo

### 1.6 Costos y Requisitos
- **Requisito principal**: Cuenta de trading OANDA v20
- **Cuenta demo**: Disponible gratuitamente
- **Restricciones geográficas**: No disponible para OANDA Global Markets y OANDA TMS BROKERS S.A.

## 2. Alpha Vantage Forex API

### 2.1 Información General
Alpha Vantage ofrece datos financieros incluyendo forex, acciones, opciones y criptomonedas, con más de 60 indicadores técnicos y económicos[11].

### 2.2 Endpoints Forex Específicos
- **Base URL**: `https://www.alphavantage.co/query`
- **Función FX_DAILY**: Tasas de cambio diarias
- **Función FX_INTRADAY**: Datos intradía con intervalos de 1min, 5min, 15min, 30min, 60min
- **Función CURRENCY_EXCHANGE_RATE**: Tasa de cambio en tiempo real

### 2.3 Sistema de Claves API
- **Obtención**: Registro gratuito en `https://www.alphavantage.co/support/#api-key`
- **Parámetro**: `apikey=YOUR_API_KEY`
- **Formato de respuesta**: JSON y CSV

### 2.4 Límites y Costos

| Plan | Precio/Mes | Solicitudes/Día | Características |
|------|------------|-----------------|------------------|
| Gratuito | $0 | 25 | Funcionalidades básicas |
| Premium | Variable | Ilimitado | Funciones premium, mayor rate limit |

### 2.5 Frecuencias Disponibles
- **Tiempo real**: Tasas actuales de cambio
- **Intradía**: 1, 5, 15, 30, 60 minutos
- **Diario**: Datos diarios históricos
- **Semanal/Mensual**: Agregaciones de largo plazo

### 2.6 Cobertura de Divisas
- Cobertura global con pares principales y menores
- Asociación con NASDAQ como proveedor de datos licenciado
- Acceso a mercados globales

## 3. Interactive Brokers API (TWS)

### 3.1 Información General
La API de Interactive Brokers proporciona acceso programático al Trader Workstation (TWS) e IB Gateway para trading automatizado y datos de mercado[9,10].

### 3.2 Configuración y Autenticación

#### Requisitos de Cuenta
- **Cuenta fondeada**: Requerida para datos en vivo
- **Permisos de datos**: Deben estar habilitados
- **Suscripciones de mercado**: Activas y pagadas
- **Cuentas demo**: Compatibles para pruebas

#### Configuración Técnica
| Componente | TWS (Live) | TWS (Paper) | IB Gateway (Live) | IB Gateway (Paper) |
|------------|------------|-------------|-------------------|-------------------|
| Puerto Socket | 7496 | 7497 | 4001 | 4002 |

#### Configuraciones Esenciales
- **Enable ActiveX and Socket Clients**: Debe estar marcado
- **Read-Only**: Desmarcar para envío de órdenes
- **Socket Port**: Debe coincidir con cliente API

### 3.3 Endpoints para Datos Forex
- **Datos en tiempo real**: Via sockets
- **Datos históricos**: Solicitudes históricas
- **Streaming**: Suscripciones a datos en vivo
- **Ejecución de órdenes**: Endpoints de trading

### 3.4 Capacidades de Tiempo Real
- **Latencia**: Sub-segundo para ejecución
- **Instrumentos soportados**: Todos los pares forex disponibles en IB
- **Streaming**: Nativo via socket connections
- **Backtesting y Live**: Ambos soportados

### 3.5 Costos
- **API**: Gratuita con cuenta
- **Datos de mercado**: Tarifas separadas según suscripciones
- **Trading**: Comisiones estándar de IB
- **Sin comisiones**: API no disponible para cuentas de trading gratuito

### 3.6 Herramientas Disponibles
1. **Script Python Open Source**: Disponible en GitHub
2. **IBridgePy**: Herramienta simplificada con curso gratuito de 3 horas

## 4. APIs Alternativas

### 4.1 XE Currency Data API

#### Especificaciones[3]
- **Divisas soportadas**: 220+ divisas mundiales, metales preciosos, criptomonedas
- **Frecuencia de actualización**: Cada 60 segundos
- **SDKs disponibles**: Java, NodeJS, PHP, Python
- **Fuentes**: Más de 100 fuentes globales

#### Planes de Precios
| Plan | Solicitudes/Mes | Frecuencias Incluidas |
|------|----------------|-----------------------|
| Lite | 10,000 | Diaria |
| Intermediate | 50,000 | Por hora, Diaria |
| Prime | 150,000 | Cada 15 min, Por hora, Diaria |
| Enterprise | Personalizado | En vivo (60s), Cada 15 min, Por hora, Diaria |

#### Características Técnicas
- **Prueba gratuita**: 7 días
- **Conteo de solicitudes**: Cada par cuenta como una solicitud
- **Tiempo de respuesta**: Milisegundos
- **Compatibilidad**: Microsoft Dynamics, SAP, Oracle, Sage

### 4.2 Fixer.io API

#### Especificaciones[4]
- **Divisas soportadas**: 170 monedas mundiales
- **Datos históricos**: Desde 1999
- **Fuentes**: Más de 15 fuentes de datos
- **Precisión**: 6 decimales en la mayoría de tasas

#### Endpoints Disponibles
1. **Supported Symbols** (`/symbols`): Lista de divisas disponibles
2. **Latest Rates** (`/latest`): Tasas en tiempo real
3. **Historical Rates** (`/YYYY-MM-DD`): Datos históricos
4. **Convert** (`/convert`): Conversión de divisas
5. **Time-Series** (`/timeseries`): Series temporales (máx. 365 días)
6. **Fluctuation** (`/fluctuation`): Análisis de fluctuaciones

#### Planes y Precios
| Plan | Precio/Mes | Llamadas/Mes | Frecuencia Actualización | Costo Exceso/Llamada |
|------|------------|--------------|--------------------------|---------------------|
| Basic | $14.99 | 10,000 | 60 minutos | $0.002998 |
| Professional | $59.99 | 100,000 | 10 minutos | $0.0011998 |
| Professional Plus | $99.99 | 500,000 | 60 segundos | $0.00039996 |

#### Características Técnicas
- **Base URL**: `https://data.fixer.io/api/`
- **Autenticación**: Clave API en parámetro `access_key`
- **Formato**: JSON estándar
- **Cifrado**: HTTPS SSL de 256 bits
- **Soporte CORS**: Sí
- **JSONP**: Sí
- **HTTP ETags**: Sí

### 4.3 CurrencyLayer API

#### Especificaciones[5]
- **Divisas soportadas**: 168 divisas mundiales y metales preciosos
- **Datos históricos**: Desde 1999
- **Precisión**: 6 decimales
- **Uptime API**: ~99.9% (últimos 12 meses)

#### Planes y Precios
| Plan | Precio/Mes | Precio Anual | Solicitudes/Mes | Actualizaciones | Costo Exceso |
|------|------------|--------------|----------------|-----------------|---------------|
| Gratis | $0 | $0 | 100 | Diarias | - |
| Starter | $9.99 | $8.99 | 2,500 | Por hora | $0.007992 |
| Basic | $14.99 | $13.99 | 10,000 | Por hora | $0.002998 |
| Professional | $59.99 | $52.99 | 100,000 | 10 minutos | $0.0011998 |
| Business Plus | $99.99 | $84.99 | 500,000 | 60 segundos | $0.00039996 |

#### Características Técnicas
- **Método de pago**: Tarjeta de crédito, transferencia bancaria (empresarial)
- **Notificaciones**: 75%, 90%, 100% del uso mensual
- **Soporte**: Platinum para planes de pago

### 4.4 TraderMade API

#### Especificaciones WebSocket[6]
- **Protocolos**: WSS (WebSocket), SocketIO v2
- **URL WebSocket**: `wss://marketdata.tradermade.com/feedadv`
- **URL SocketIO**: `https://marketdata.tradermade.com`
- **Pares soportados**: 60+ pares de divisas, CFDs globales
- **Formatos**: JSON, CSV, SSV

#### Autenticación
- **Método**: API Key (`userKey`)
- **WebSocket**: Incluir en conexión inicial: `{"userKey":"API_KEY", "symbol":"EURUSD,GBPUSD"}`
- **SocketIO**: Emitir evento 'login' con userKey

#### Formato de Datos
- **JSON**: `{symbol, ts (timestamp), bid, ask, mid}`
- **SSV/CSV**: Valores separados por espacios/comas
- **SocketIO**: `'symbol bid ask mid date time'`

#### Eventos WebSocket/SocketIO
- **WebSocket**: on open, on message, on disconnect
- **SocketIO**: login, handshake, symbolSub, subResponse, price, disconnect

### 4.5 Polygon.io Forex API

#### Especificaciones[7]
- **Acceso**: API REST, WebSocket streams, archivos planos
- **Horario**: 24/5 (24 horas, 5 días semana)
- **Normalización**: UTC (Coordinated Universal Time)
- **Fuentes**: Bancos globales, instituciones financieras, market makers

#### Capacidades
- **Tiempo real**: Cotizaciones en vivo
- **Históricos**: Datos históricos completos
- **Referencia**: Información de referencia de divisas
- **Análisis técnico**: Construcción de agregados personalizados
- **Integración**: APIs para algoritmos de trading y dashboards

## 5. Conexiones WebSocket Específicas

### 5.1 Comparativa de Capacidades WebSocket

| API | Soporte WebSocket | Protocolos | Latencia | Conexiones Simultáneas |
|-----|-------------------|------------|----------|------------------------|
| OANDA v20 | ✅ Nativo | WebSocket | <50ms | 20 por IP |
| Alpha Vantage | ❌ | REST únicamente | N/A | N/A |
| Interactive Brokers | ✅ Socket nativo | TCP Sockets | Sub-segundo | Según cuenta |
| XE Currency | ❌ | REST únicamente | Milisegundos | N/A |
| Fixer.io | ❌ | REST con polling | 60s-10min-1min | N/A |
| CurrencyLayer | ❌ | REST con polling | 60s-10min-1min | N/A |
| TraderMade | ✅ Completo | WSS, SocketIO v2 | <50ms | Sin límite especificado |
| Polygon.io | ✅ Completo | WebSocket | Variable | Sin límite especificado |

### 5.2 Implementaciones WebSocket Recomendadas

#### Para Baja Latencia y Alto Volumen
1. **TraderMade**: Protocolo WSS con soporte completo
2. **OANDA v20**: WebSocket nativo con límites claros
3. **Polygon.io**: Streaming completo con infraestructura robusta

#### Para Desarrollo Sencillo
1. **TraderMade SocketIO**: Simplifica la conexión
2. **Interactive Brokers**: Documentación extensa y herramientas

## 6. Análisis Comparativo de Costos y Límites

### 6.1 Tabla Comparativa de Costos

| API | Plan Básico | Solicitudes/Mes | Características Principales |
|-----|-------------|----------------|----------------------------|
| OANDA v20 | Cuenta trading | Ilimitado* | Streaming nativo, datos desde 2005 |
| Alpha Vantage | Gratis | 750 (25/día) | Indicadores técnicos incluidos |
| Interactive Brokers | Cuenta + suscripciones | Ilimitado* | Trading completo, múltiples instrumentos |
| XE Currency | Plan Lite | 10,000 | 220+ divisas, actualizaciones diarias |
| Fixer.io | $14.99 | 10,000 | 170 divisas, datos desde 1999 |
| CurrencyLayer | $9.99 | 2,500 | 168 divisas, actualizaciones por hora |
| TraderMade | Consultar | Variable | WebSocket nativo, baja latencia |
| Polygon.io | Plan gratuito limitado | Variable | REST + WebSocket, datos completos |

*Sujeto a límites de rate por segundo/minuto

### 6.2 Recomendaciones por Uso

#### Desarrollo y Prototipos
- **Alpha Vantage**: Mejor opción gratuita (25 calls/día)
- **CurrencyLayer Starter**: Económico para desarrollo ($9.99/mes)

#### Aplicaciones de Producción Media
- **Fixer.io Professional**: Buena relación precio-funcionalidad ($59.99/mes)
- **XE Currency Intermediate**: Confiable y establecido (50K/mes)

#### Aplicaciones Empresariales/Tiempo Real
- **OANDA v20**: Para trading real y máxima precisión
- **Interactive Brokers**: Para portafolios completos multi-instrumento
- **TraderMade**: Para streaming de alta frecuencia

#### Trading Algorítmico
- **OANDA v20**: Capacidades completas de trading
- **Interactive Brokers**: Ecosistema robusto con herramientas
- **Polygon.io**: Para análisis de datos avanzado

### 6.3 Limitaciones Importantes

#### Alpha Vantage
- Solo 25 solicitudes/día en plan gratuito
- No hay WebSocket streaming nativo

#### Fixer.io/CurrencyLayer
- Sin WebSocket, requiere polling
- Actualizaciones limitadas según plan

#### Interactive Brokers
- Requiere cuenta fondeada para datos en vivo
- Costos adicionales por suscripciones de datos

#### XE Currency
- Precios no públicos, requiere contacto comercial
- Sin capacidades WebSocket

## 7. Consideraciones Técnicas

### 7.1 Factores de Selección

#### Para Tiempo Real Crítico
1. **Latencia**: TraderMade, OANDA v20, Polygon.io
2. **Confiabilidad**: OANDA (99.9%+), Interactive Brokers
3. **Cobertura**: XE Currency (220+ pares), OANDA

#### Para Desarrollo Ágil
1. **Facilidad de uso**: Alpha Vantage, Fixer.io
2. **Documentación**: Interactive Brokers, OANDA
3. **SDKs**: XE Currency (4 lenguajes)

#### Para Escala Empresarial
1. **Volumen**: Interactive Brokers, OANDA v20
2. **Soporte**: XE Currency Platinum, CurrencyLayer Business
3. **SLAs**: OANDA, Interactive Brokers

### 7.2 Mejores Prácticas

#### Implementación WebSocket
- Implementar reconexión automática
- Manejar límites de rate apropiadamente
- Usar compresión cuando esté disponible
- Monitorear latencia y pérdida de paquetes

#### Gestión de APIs REST
- Implementar caching inteligente
- Respetar límites de rate estrictos
- Usar HTTP ETags cuando esté disponible
- Implementar circuit breakers para fallas

## Conclusión

La selección de la API de datos forex apropiada depende de factores específicos como volumen de datos, requisitos de latencia, presupuesto y capacidades técnicas. Para aplicaciones que requieren datos en tiempo real con baja latencia, OANDA v20, TraderMade y Interactive Brokers son las opciones más robustas. Para desarrollo y aplicaciones de menor escala, Alpha Vantage, Fixer.io y CurrencyLayer ofrecen soluciones costo-efectivas con buena funcionalidad.

---

## Referencias

[1] [OANDA v20 REST API - Guía de Desarrollo](https://developer.oanda.com/rest-live-v20/development-guide/)
[2] [Alpha Vantage Premium API Key](https://www.alphavantage.co/premium/)
[3] [XE Currency Data API - Packages, Pricing and Payment](https://help.xe.com/hc/en-gb/articles/4414092026769-Currency-Data-API-packages-pricing-and-payment)
[4] [Fixer.io API Documentation](https://fixer.io/documentation)
[5] [CurrencyLayer Pricing](https://currencylayer.com/pricing)
[6] [TraderMade WebSocket Streaming Data API](https://tradermade.com/docs/streaming-data-api)
[7] [Polygon.io Forex REST API Overview](https://polygon.io/docs/rest/forex/overview)
[8] [OANDA v20 REST API - Introduction](https://developer.oanda.com/rest-live-v20/introduction/)
[9] [Installing & Configuring TWS for the API](https://www.interactivebrokers.com/campus/trading-lessons/installing-configuring-tws-for-the-api/)
[10] [Setup to Trade Forex Algorithmically Using the Interactive Brokers API](https://www.interactivebrokers.com/campus/ibkr-quant-news/a-setup-to-trade-forex-algorithmically-using-the-interactive-brokers-api/)
[11] [Alpha Vantage: Free Stock APIs in JSON & Excel](https://www.alphavantage.co/)

---
*Documento generado el 28 de agosto de 2025 por MiniMax Agent*
