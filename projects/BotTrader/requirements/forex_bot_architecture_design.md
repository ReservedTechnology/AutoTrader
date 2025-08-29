# Diseño de Arquitectura: Bot de Trading Forex Institucional v1.0

## Resumen Ejecutivo

Este documento presenta el diseño arquitectónico de un bot de trading forex de grado institucional, concebido para operar sobre la infraestructura de Supabase y Railway. El diseño integra estrategias de inteligencia artificial de vanguardia, validadas en los mercados de China, Wall Street y estudios académicos globales, con un enfoque pragmático adaptado a las capacidades del stack tecnológico seleccionado.

La arquitectura se define como un **Sistema de Trading de Frecuencia Media (MFT)**, operando en un rango de latencia de 100-500ms. Si bien no es apto para High-Frequency Trading (HFT), el sistema incorpora la lógica, la sofisticación y la robustez de las estrategias institucionales. Los componentes clave incluyen un motor de ingesta de datos en tiempo real, un módulo de generación de señales basado en un ensamble de modelos de Deep Learning (TCNs, Transformers) y Reinforcement Learning, un motor de ejecución algorítmica (VWAP, IS) y un sistema de gestión de riesgo multicapa en tiempo real.

La distribución de componentes optimiza el uso de Supabase para la persistencia de datos (TimescaleDB), la autenticación y el despliegue de funciones de análisis no críticas, mientras que Railway se utiliza para orquestar los microservicios que componen el núcleo del bot. El diseño es modular y escalable, previendo una futura migración de los componentes más sensibles a la latencia a una infraestructura dedicada (co-location) para evolucionar hacia capacidades de HFT.

**Características Clave del Diseño:**
- **Plataforma:** Supabase y Railway.
- **Tipo de Sistema:** Trading de Frecuencia Media (MFT) con Lógica Institucional.
- **Latencia Esperada:** 100-500ms.
- **Estrategias IA:** Ensamble de TCN, Transformers, A3C Reinforcement Learning, y XGBoost.
- **Gestión de Riesgo:** VaR dinámico, límites de drawdown, y circuit breakers a nivel de estrategia.
- **Ejecución:** Algoritmos VWAP e Implementation Shortfall adaptados.
- **Datos:** Conectividad a APIs institucionales (Interactive Brokers, LMAX) y procesamiento de datos alternativos (sentimiento de noticias).

---

## 1. Arquitectura del Sistema

La arquitectura está diseñada bajo un enfoque de microservicios, priorizando la modularidad, la resiliencia y la escalabilidad dentro de las limitaciones del entorno Supabase/Railway.

### 1.1. Componentes Core del Bot

El sistema se descompone en cuatro microservicios principales, cada uno desplegado como un contenedor independiente en Railway y comunicados a través de una API interna y colas de mensajes (utilizando Redis o un servicio similar).

1.  **Data Ingestion Engine (Motor de Ingesta de Datos):**
    *   **Responsabilidad:** Conectarse a las APIs de los brokers (p. ej., Interactive Brokers, LMAX) y proveedores de datos (p. ej., Alpha Vantage) para recibir datos de mercado en tiempo real (ticks, cotizaciones L1/L2) y datos fundamentales.
    *   **Tecnología:** Contenedor Python/Go en Railway utilizando conexiones WebSocket persistentes.
    *   **Flujo:** Recibe los datos, los normaliza a un formato canónico interno y los publica en un stream de Redis (para consumo en tiempo real por otros servicios) y los persiste de forma asíncrona en la base de datos de Supabase (TimescaleDB) para análisis histórico.

2.  **Signal Generation Engine (Motor de Generación de Señales):**
    *   **Responsabilidad:** Procesar los datos de mercado en tiempo real y generar señales de trading (COMPRAR, VENDER, MANTENER). Este es el "cerebro" del bot.
    *   **Tecnología:** Contenedor Python en Railway con librerías de ML (PyTorch, TensorFlow, Scikit-learn). Se comunica con el pipeline de ML.
    *   **Flujo:** Consume datos del stream de Redis. Ejecuta el ensamble de modelos de predicción (TCN, Transformer, etc.) y el modelo de RL (A3C) para determinar la acción óptima. La señal resultante, junto con un nivel de confianza, se envía al motor de gestión de riesgo.

3.  **Risk Management Engine (Motor de Gestión de Riesgo):**
    *   **Responsabilidad:** Evaluar cada señal de trading propuesta contra un conjunto de reglas de riesgo predefinidas y el estado actual del portafolio.
    *   **Tecnología:** Contenedor Python/Go en Railway.
    *   **Flujo:** Recibe la señal del *Signal Engine*. Verifica:
        *   Límites de exposición por activo y totales.
        *   Drawdown máximo del día/semana.
        *   Cálculos de VaR (Value at Risk) dinámicos.
        *   Correlación de la nueva posición con el portafolio existente.
        *   Si la señal es aprobada, la enriquece con parámetros de riesgo (p. ej., tamaño de la posición calculado según el modelo de Kelly Criterion o similar) y la pasa al *Execution Engine*. Si es rechazada, la descarta y registra el motivo.

4.  **Execution Engine (Motor de Ejecución):**
    *   **Responsabilidad:** Ejecutar la orden en el mercado de la manera más eficiente posible, minimizando el *slippage* y el impacto en el mercado.
    *   **Tecnología:** Contenedor Python/Go en Railway, manteniendo una conexión directa y de baja latencia con la API del broker.
    *   **Flujo:** Recibe la orden aprobada del *Risk Engine*. Implementa algoritmos de ejecución institucionales como:
        *   **VWAP (Volume-Weighted Average Price):** Para órdenes grandes que no son urgentes, dividiéndolas a lo largo del día según el perfil de volumen.
        *   **Implementation Shortfall (IS):** Para un balance óptimo entre el riesgo de mercado y el costo de impacto.
        *   **SOR (Smart Order Routing):** Lógica para enrutar la orden al broker/venue que ofrezca la mejor liquidez en ese momento (si se usan múltiples brokers).

### 1.2. Distribución Optimizada entre Supabase y Railway

La distribución de cargas de trabajo aprovecha las fortalezas de cada plataforma:

**Railway (Computación y Lógica en Tiempo Real):**
*   **Microservicios Core:** Los cuatro motores (Ingesta, Señales, Riesgo, Ejecución) se ejecutan como servicios persistentes en Railway para garantizar la continuidad operativa. Se recomienda usar **Railway Metal** para obtener el mejor rendimiento posible dentro de la plataforma.
*   **Cache y Colas de Mensajes:** Se despliega una instancia de Redis en Railway para la comunicación de alta velocidad y baja latencia entre los microservicios.
*   **Pipelines de ML (Offline):** Los procesos de re-entrenamiento y walk-forward optimization se ejecutan como tareas programadas o bajo demanda en contenedores de Railway, aprovechando su escalabilidad para cargas de trabajo pesadas.

**Supabase (Persistencia, Datos, y Servicios de Soporte):**
*   **Base de Datos Principal:** Se utiliza Supabase con la extensión **TimescaleDB** para almacenar todos los datos de mercado históricos (ticks, barras de precios), datos alternativos, transacciones, y logs del sistema. Su optimización para series temporales es ideal para backtesting y análisis.
*   **Autenticación y Gestión de Usuarios:** Supabase Auth gestiona el acceso seguro al dashboard de control.
*   **API de Datos Históricos:** Supabase PostgREST genera automáticamente una API RESTful sobre la base de datos, que es utilizada por el dashboard y por los pipelines de ML para obtener datos de entrenamiento.
*   **Edge Functions (Funciones no críticas):** Se usan para tareas asíncronas de bajo impacto, como la generación de reportes diarios, notificaciones a través de webhooks, o la ingesta de datos alternativos de baja frecuencia (p. ej., noticias económicas de APIs REST). Se evita su uso para cualquier parte del flujo de trading en tiempo real debido a su alta latencia y cold starts.
*   **Almacenamiento de Modelos:** Los artefactos de los modelos de ML entrenados (pesos, etc.) se almacenan en Supabase Storage para ser accedidos por el *Signal Generation Engine*.

### 1.3. Pipelines de ML para Predicción y Adaptación Continua

El sistema implementa un pipeline de MLOps robusto para garantizar que los modelos se mantengan relevantes.

*   **Entrenamiento y Validación (Offline):**
    1.  **Disparador:** Se ejecuta semanalmente o mensualmente (o al detectar *concept drift*).
    2.  **Extracción de Datos:** Un script en Railway extrae los datos más recientes de TimescaleDB en Supabase.
    3.  **Feature Engineering:** Se aplican las técnicas de ingeniería de características (indicadores técnicos, microestructura, correlaciones).
    4.  **Validación Cruzada:** Se utiliza **Combinatorial Purged Cross-Validation (CPCV)** para evaluar los modelos, evitando el data leakage.
    5.  **Entrenamiento:** Se re-entrenan los modelos del ensamble (TCN, Transformer, XGBoost).
    6.  **Registro:** El modelo con mejor performance en la validación se versiona y guarda en Supabase Storage, junto con sus métricas de rendimiento.

*   **Adaptación Continua (Online):**
    1.  **Detección de Concept Drift:** El *Signal Generation Engine* monitorea continuamente la performance de sus predicciones. Utiliza el framework **Proceed** o **SAEM**, que compara la distribución de los datos recientes con los datos de entrenamiento para detectar cambios de régimen en el mercado.
    2.  **Mecanismo de Alerta:** Si se detecta una deriva significativa (p. ej., el error de predicción aumenta un 20% sobre la media móvil), se dispara una alerta y, opcionalmente, se activa automáticamente el pipeline de re-entrenamiento.
    3.  **Ajuste Dinámico del Ensamble:** El sistema puede ajustar dinámicamente los pesos de los modelos en el ensamble en tiempo real, dando más importancia a los que han tenido mejor rendimiento en las últimas horas.

### 1.4. Sistema de Gestión de Riesgo Multi-capa

El riesgo se gestiona en tres niveles para máxima seguridad:

1.  **Riesgo Pre-Trade (Nivel de Orden):** Realizado por el *Risk Management Engine* antes de que cualquier orden llegue al mercado. Incluye límites de tamaño de posición, exposición máxima y verificación de liquidez.
2.  **Riesgo En-Vuelo (Nivel de Estrategia):** Monitoreo en tiempo real del rendimiento de la estrategia. Si el drawdown de la estrategia activa supera un umbral (p. ej., 2% en un día), un **circuit breaker** puede pausar automáticamente la generación de nuevas señales o poner todas las posiciones en modo "solo cierre".
3.  **Riesgo de Portafolio (Nivel Global):** Un proceso en segundo plano calcula métricas de riesgo del portafolio completo (Sharpe Ratio, Sortino Ratio, VaR del portafolio). Si el riesgo global excede los límites definidos, se pueden activar alertas a los operadores o reducir el apalancamiento general del sistema.

### 1.5. Protocolos de Failover y Recuperación

*   **Redundancia de Servicios:** Railway permite desplegar múltiples instancias de cada microservicio core. Si una instancia falla, el tráfico se redirige a otra.
*   **Persistencia de Estado:** El estado crítico (posiciones abiertas, órdenes activas) se mantiene tanto en la memoria del servicio correspondiente como en la base de datos de Supabase. En caso de un reinicio, el servicio puede recuperar su estado desde la base de datos.
*   **Conexión de Broker:** El *Execution Engine* implementa una lógica de reconexión automática y robusta a la API del broker con reintentos exponenciales.
*   **Heartbeats:** Cada microservicio emite un "latido" a un servicio de monitoreo. Si un latido se pierde, el sistema de orquestación intentará reiniciar el servicio automáticamente.
*   **Respaldo de Base de Datos:** Supabase gestiona respaldos automáticos y puntuales de la base de datos PostgreSQL, permitiendo la recuperación ante un desastre.

---

## 2. Estrategias de IA Integradas

El motor de generación de señales es un sistema híbrido y adaptativo que combina las estrategias más efectivas identificadas en la investigación. El enfoque se basa en un **ensamble de modelos ponderado dinámicamente**, donde la decisión final es una combinación de las predicciones de varios modelos especializados, con pesos ajustados según su rendimiento reciente y el régimen de mercado actual.

### 2.1. Implementación de Técnicas Chinas Exitosas

*   **Reinforcement Learning Multi-Agente (A3C):**
    *   **Concepto:** Se implementa una versión simplificada del framework Asynchronous Advantage Actor-Critic (A3C). En lugar de múltiples *workers* asíncronos para diferentes divisas, se utiliza un modelo A3C como **meta-aprendiz (meta-learner)**. 
    *   **Función:** El modelo A3C no predice el precio, sino que **aprende la política óptima para combinar las señales** del ensamble de modelos predictivos. Su espacio de acción es decidir el peso que se le da a cada modelo del ensamble (TCN, Transformer, etc.) en cada instante de tiempo, y el tamaño óptimo de la posición, para maximizar el Sharpe Ratio.
    *   **Entrada:** Las señales de los modelos predictivos, la volatilidad actual, y el estado del portafolio.
    *   **Recompensa:** Se utiliza una función de recompensa basada en el Sharpe Ratio o el Profit Factor para incentivar rendimientos ajustados por riesgo.

*   **Ensemble Methods (Stacking y OW-XGBoost):**
    *   **Stacking:** El ensamble principal de modelos predictivos se basa en una arquitectura de *stacking*. 
        *   **Nivel 0 (Modelos Base):** Incluye un modelo TCN, un Transformer (con Time2Vec embeddings), y un modelo OW-XGBoost.
        *   **Nivel 1 (Meta-Modelo):** Una regresión lineal simple o una red neuronal pequeña que toma las predicciones de los modelos base como entrada para producir la predicción final. El modelo A3C actúa sobre este nivel para ajustar los pesos.
    *   **OW-XGBoost (Optimal Weights XGBoost):** Se incluye un modelo XGBoost que utiliza "fusing labels" para balancear múltiples objetivos (retorno, drawdown, Sharpe ratio) en una sola predicción, aportando una visión de riesgo-recompensa al ensamble.

### 2.2. Algoritmos Institucionales de Wall Street

*   **Generación de Alpha con Datos Alternativos:**
    *   **Análisis de Sentimiento:** Un microservicio auxiliar (desplegado como Supabase Edge Function de ejecución periódica) ingiere noticias financieras de fuentes RSS o APIs de noticias. Utiliza un modelo **FinBERT** pre-entrenado para clasificar el sentimiento (positivo, negativo, neutral).
    *   **Integración:** El sentimiento agregado (p. ej., media móvil del sentimiento de las últimas 24h) se convierte en una característica de entrada adicional para los modelos de predicción del *Signal Engine*. Esto permite a los modelos capturar cambios en el sentimiento del mercado que preceden a movimientos de precios.

*   **Ejecución Algorítmica (VWAP, IS):** Estos no son modelos predictivos, sino **estrategias de ejecución** implementadas en el *Execution Engine* como se detalló en la Sección 1.

### 2.3. ML Avanzado para Forex

*   **Temporal Convolutional Networks (TCNs):** Constituye el principal modelo predictivo para series temporales dentro del ensamble. Su arquitectura (convoluciones causales, dilatadas y conexiones residuales) le permite capturar patrones a corto y largo plazo de forma computacionalmente eficiente. Se basa en arquitecturas probadas como la del **ATCGAN** (sin la parte generativa para simplificar).
*   **Transformers con Time Embeddings:** Se utiliza un modelo Transformer (encoder-only) con embeddings **Time2Vec** como segundo pilar del ensamble. Es particularmente efectivo para capturar las relaciones complejas entre un gran número de características (más de 1000, incluyendo indicadores técnicos, de sentimiento y correlaciones).

### 2.4. Sistemas de Adaptación Online y Continuous Learning

*   **Framework de Adaptación Proactiva (Proceed):** El sistema monitorea el *concept drift* de forma continua. Cada hora, un proceso evalúa la diferencia estadística (p. ej., usando la distancia de Kullback-Leibler) entre la distribución de las características de los datos de las últimas 24 horas y las de la semana anterior. Si la distancia supera un umbral, se activa una alerta.
*   **Smart Adaptive Ensemble Model (SAEM):** La ponderación de los modelos en el ensamble es dinámica. El modelo A3C ajusta los pesos, pero además, si un modelo base muestra un rendimiento consistentemente bajo durante un período (detectado por el mecanismo ADWIN), su peso se reduce drásticamente o se le excluye temporalmente del ensamble hasta el próximo re-entrenamiento.
*   **Validación Robusta (Walk-Forward Optimization):** El pipeline de re-entrenamiento no utiliza un simple backtest, sino un protocolo de **Walk-Forward Analysis**. Los datos se dividen en ventanas consecutivas de entrenamiento y prueba (p. ej., 12 meses de entrenamiento, 3 meses de prueba), y el proceso se repite desplazando la ventana. Esto asegura que la estrategia es robusta y adaptable a través de diferentes condiciones de mercado. Para la validación dentro de cada ventana de entrenamiento, se usa **Purged K-Fold CV**.

---

## 3. Gestión de Datos y Conectividad

La gestión de datos es la columna vertebral del sistema, asegurando un flujo de información limpio, rápido y confiable desde los mercados hasta los modelos.

### 3.1. Integración con APIs de Brokers Recomendadas

*   **Conexión Primaria (Ejecución): Interactive Brokers (IBKR):**
    *   **API:** Se utiliza la **API TWS o la Web API de IBKR** a través de una conexión WebSocket persistente para la ejecución de órdenes y la recepción de datos de mercado en tiempo real. Esto garantiza la menor latencia posible para el componente más crítico.
    *   **Ventajas:** Acceso a liquidez profunda, ejecución fiable y cumplimiento normativo.

*   **Conexión Secundaria (Datos y Liquidez): LMAX Exchange / Saxo Bank:**
    *   **API:** Se puede establecer una conexión adicional a LMAX o Saxo para obtener un feed de datos redundante y comparar precios, mejorando la lógica del Smart Order Routing.
    *   **Ventajas:** Proporcionan feeds de datos de alta calidad y permiten diversificar la dependencia de un solo broker.

*   **Datos Históricos para Backtesting: OANDA:**
    *   **API:** Se utiliza la API REST v20 de OANDA para descargar grandes volúmenes de datos históricos (hasta 20 años), que son la base para el entrenamiento inicial de los modelos y el backtesting extensivo.

### 3.2. Streaming de Datos en Tiempo Real con WebSockets

*   **Data Ingestion Engine:** Este servicio mantiene las conexiones WebSocket con los brokers. Está diseñado para ser altamente concurrente, manejando múltiples streams (uno por cada par de divisas monitoreado) en paralelo.
*   **Protocolo Interno:** Los datos recibidos se normalizan a un formato JSON estándar (protobuf como optimización futura) antes de ser publicados en el stream de Redis. Este formato incluye el timestamp con precisión de nanosegundos (si el broker lo provee), el par de divisas, el precio de bid/ask, y el volumen.
*   **Manejo de Desconexiones:** El motor implementa una lógica de `heartbeat` y reconexión automática para asegurar que la conexión de streaming sea robusta 24/7.

### 3.3. Almacenamiento Optimizado de Datos de Mercado

*   **Plataforma:** PostgreSQL con la extensión **TimescaleDB** en Supabase.
*   **Esquema de Hypertables:** Los datos de ticks y las barras de precios (OHLCV) se almacenan en `hypertables` de TimescaleDB, particionadas automáticamente por tiempo (p. ej., en bloques de 1 día).
*   **Compresión:** TimescaleDB se configura para comprimir automáticamente los bloques de datos antiguos (p. ej., después de 7 días), reduciendo los costos de almacenamiento en un 90% o más sin afectar el rendimiento de las consultas, ya que el trading en tiempo real opera sobre datos recientes no comprimidos.
*   **Índices:** Se crean índices compuestos en `(timestamp, symbol)` para acelerar las consultas tanto para el backtesting como para la carga de datos en el dashboard.

### 3.4. Procesamiento de Alternative Data

*   **Fuente:** Noticias financieras de APIs como NewsAPI, o feeds especializados.
*   **Ingesta:** Una **Supabase Edge Function** se ejecuta cada 15 minutos. Llama a la API de noticias, busca artículos relevantes para los pares de divisas monitoreados, y los inserta en una tabla `news_articles` en la base de datos.
*   **Procesamiento:** Otra función (o un trigger en la base de datos) se activa cuando se inserta un nuevo artículo. Esta función ejecuta el modelo **FinBERT** para el análisis de sentimiento y actualiza la fila con el score de sentimiento.
*   **Agregación:** El *Signal Engine* consulta una vista materializada que provee el score de sentimiento promedio y ponderado por volumen de noticias para cada par de divisas en diferentes ventanas de tiempo (1h, 24h, 7d).

---

## 4. Sistema de Ejecución

El Sistema de Ejecución traduce las decisiones de alto nivel del bot en acciones concretas en el mercado, con un enfoque en la eficiencia y la minimización de costos.

### 4.1. Smart Order Routing (SOR) Adaptado

*   **Lógica:** Aunque el sistema puede comenzar con un solo broker, el *Execution Engine* está diseñado para soportar múltiples conexiones. Antes de enviar una orden, el SOR consulta los precios actuales de los brokers conectados.
*   **Criterios de Decisión:** La decisión de enrutamiento se basa en una función de costo simple: `Costo = Precio + Latencia_Estimada_Fee`. La orden se envía al broker con el menor costo. En este entorno de MFT, el `Precio` es el factor dominante.
*   **Fragmentación:** Para órdenes grandes, el SOR puede decidir fragmentar la orden y enviarla a múltiples brokers simultáneamente para reducir el impacto en el mercado.

### 4.2. Algoritmos Anti-Gaming y Ejecución Stealth

*   **Randomización:** Para evitar ser detectado por algoritmos predatorios, el *Execution Engine* introduce una pequeña aleatoriedad en el tamaño y el tiempo de las sub-órdenes (dentro de los algoritmos VWAP/IS). Por ejemplo, en lugar de enviar 10 lotes cada 5 minutos, podría enviar 9.8 lotes a los 4 minutos y 50 segundos, y 10.2 lotes a los 5 minutos y 10 segundos.
*   **Órdenes Iceberg:** Cuando la API del broker lo permite, el motor utiliza órdenes tipo Iceberg, mostrando solo una pequeña porción del tamaño total de la orden en el libro de órdenes para ocultar la intención real.

### 4.3. Transaction Cost Analysis (TCA) Integrado

*   **Registro de Datos:** Por cada orden "padre" (p. ej., "Vender 100 lotes de EUR/USD"), el sistema registra el precio de mercado en el momento de la decisión (*arrival price*). Por cada ejecución "hijo", registra el precio y volumen ejecutado.
*   **Cálculo Post-Trade:** Un proceso asíncrono (Supabase Edge Function) se ejecuta periódicamente para calcular las métricas de TCA para todas las órdenes completadas. Las métricas clave incluyen:
    *   **Implementation Shortfall:** La diferencia entre el *arrival price* y el precio promedio de ejecución.
    *   **Slippage:** La diferencia entre el precio esperado de una ejecución y el precio real.
*   **Bucle de Retroalimentación:** Los resultados del TCA se almacenan y se utilizan como una característica de entrada para el *Risk Management Engine* y el *Execution Engine*. Por ejemplo, si el slippage para un par de divisas aumenta en condiciones de alta volatilidad, el sistema puede optar por reducir el tamaño de las órdenes o utilizar algoritmos de ejecución más pasivos.

### 4.4. Portfolio Optimization en Tiempo Real

*   **Optimización de Posiciones:** El sistema no solo decide qué operar, sino también **cuánto**. El tamaño de cada posición se determina dinámicamente utilizando una versión modificada del **Kelly Criterion**, que considera la probabilidad de éxito de la señal (proporcionada por el *Signal Engine*) y el ratio de ganancia/pérdida histórico de la estrategia.
*   **Gestión de Correlación:** El *Risk Management Engine* mantiene una matriz de correlación de los retornos de los pares de divisas en el portafolio. Antes de aprobar una nueva orden, verifica si la nueva posición aumentaría la correlación total del portafolio por encima de un umbral predefinido. Si es así, puede reducir el tamaño de la posición o rechazarla para mantener la diversificación.

---

## 5. Interfaz y Monitoreo

Se desarrollará un dashboard web para el monitoreo y control en tiempo real del bot. Esta interfaz será una aplicación de página única (SPA) construida con un framework moderno (p. ej., React, Vue.js) que se comunica con la infraestructura a través de una API segura y streams de WebSocket.

### 5.1. Dashboard de Control en Tiempo Real

*   **Tecnología:** Aplicación web estática alojada en Vercel/Netlify o directamente desde Railway. Se conecta a Supabase para obtener datos y recibir actualizaciones en tiempo real.
*   **Componentes Clave del Dashboard:**
    1.  **Vista General del Portafolio:** Muestra el P/L (Profit/Loss) total en tiempo real, el drawdown actual, el valor neto de los activos (NAV), y la exposición por divisa.
    2.  **Estado de los Servicios:** Un panel que muestra el estado (Online/Offline/Error) de cada uno de los cuatro microservicios core, basado en los `heartbeats` que emiten.
    3.  **Posiciones Abiertas:** Una tabla detallada con todas las posiciones actuales, incluyendo par de divisas, tamaño, precio de entrada, P/L actual, y stop loss/take profit si aplica.
    4.  **Historial de Órdenes:** Un registro de todas las órdenes ejecutadas, con detalles del TCA (slippage, shortfall).
    5.  **Log de Señales:** Un feed en tiempo real de las señales generadas por el *Signal Engine* y las decisiones tomadas por el *Risk Management Engine* (Aprobada/Rechazada y el motivo).
    6.  **Controles Manuales:**
        *   **Botón de Pánico (Kill Switch):** Un botón que pausa inmediatamente toda nueva actividad de trading y, opcionalmente, cierra todas las posiciones abiertas al precio de mercado.
        *   **Ajuste de Riesgo:** Controles para ajustar parámetros de riesgo globales, como el máximo drawdown permitido o la exposición total.

### 5.2. Sistema de Alertas y Métricas de Performance

*   **Tecnología:** Las alertas se gestionan a través de Supabase Edge Functions que se activan por eventos en la base de datos (triggers) o por llamadas de los microservicios. Las notificaciones se pueden enviar a través de servicios como Slack, Telegram o por correo electrónico.
*   **Alertas Críticas:**
    *   **Fallo de un Servicio:** Si un microservicio deja de enviar su `heartbeat`.
    *   **Errores de Ejecución:** Si una orden es rechazada repetidamente por el broker.
    *   **Límite de Drawdown Alcanzado:** Si el drawdown diario/semanal supera el umbral.
    *   **Detección de Concept Drift:** Cuando el sistema detecta un cambio de régimen en el mercado.
*   **Reportes de Performance:** Una función programada genera un reporte diario/semanal en PDF con las métricas clave de rendimiento: Sharpe Ratio, Sortino Ratio, Profit Factor, tasa de acierto, P/L promedio, etc.

### 5.3. Protocolos de Testing y Validación

*   **Entorno de Staging/Paper Trading:** Se debe configurar una réplica completa de la arquitectura que se conecte a la cuenta de paper trading del broker (p. ej., la cuenta demo de OANDA o IBKR). Esto permite probar nuevas estrategias y actualizaciones de software sin arriesgar capital real.
*   **Backtesting Riguroso:** Antes de desplegar una nueva estrategia, debe pasar por el framework de **Walk-Forward Optimization** descrito en la sección 2.4. Solo las estrategias que demuestren ser robustas y rentables en la simulación se promueven al entorno de paper trading.
*   **Pruebas Unitarias y de Integración:** Cada microservicio debe tener su propio conjunto de pruebas unitarias. Además, se deben implementar pruebas de integración que verifiquen el flujo completo, desde la recepción de un tick de datos hasta la ejecución de una orden.

---

## 6. Especificaciones Técnicas

### 6.1. Esquemas de Base de Datos (PostgreSQL/TimescaleDB en Supabase)

Se definen los esquemas principales para las tablas en la base de datos.

**Tabla de Ticks (Hypertable):**
```sql
CREATE TABLE ticks (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    bid NUMERIC NOT NULL,
    ask NUMERIC NOT NULL
);
SELECT create_hypertable('ticks', 'time');
CREATE INDEX ON ticks (symbol, time DESC);
```

**Tabla de Órdenes:**
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    symbol TEXT NOT NULL,
    action TEXT NOT NULL, -- 'BUY' or 'SELL'
    quantity NUMERIC NOT NULL,
    status TEXT NOT NULL, -- 'PENDING', 'APPROVED', 'EXECUTED', 'REJECTED'
    signal_id UUID REFERENCES signals(id),
    -- Detalles de ejecución
    executed_at TIMESTAMPTZ,
    avg_fill_price NUMERIC,
    -- Métricas de TCA
    arrival_price NUMERIC,
    slippage_bps NUMERIC
);
```

**Tabla de Señales:**
```sql
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    symbol TEXT NOT NULL,
    decision TEXT NOT NULL, -- 'LONG', 'SHORT', 'HOLD'
    confidence FLOAT NOT NULL, -- Confianza del modelo (0 a 1)
    source_model TEXT NOT NULL, -- Qué modelo/ensamble la generó
    -- Contexto de la señal
    metadata JSONB -- Features importantes, sentimiento, etc.
);
```

### 6.2. APIs y Endpoints Necesarios

Se define una API interna (usando REST o gRPC) para la comunicación entre los servicios desplegados en Railway.

*   `/signal` [POST]: Usado por el Signal Engine para enviar una nueva señal al Risk Engine.
    *   Body: `{ "symbol": "EUR/USD", "decision": "LONG", "confidence": 0.85, ... }`
*   `/order` [POST]: Usado por el Risk Engine para enviar una orden aprobada al Execution Engine.
    *   Body: `{ "symbol": "EUR/USD", "action": "BUY", "quantity": 10000, "type": "VWAP", ... }`
*   `/risk/check` [POST]: Endpoint para validaciones de riesgo ad-hoc.

La API de cara al usuario (para el dashboard) es proporcionada automáticamente por Supabase PostgREST, ofreciendo acceso CRUD seguro a las tablas de la base de datos.

### 6.3. Algoritmos Específicos de Ejecución

*   **VWAP (Implementación Simplificada):**
    1.  Obtener el perfil de volumen histórico del día anterior para el activo.
    2.  Dividir la orden total en `N` sub-órdenes, donde el tamaño de cada sub-orden es proporcional al volumen esperado en ese intervalo de tiempo.
    3.  Ejecutar cada sub-orden como una orden a mercado o limitada en el intervalo correspondiente.

*   **Implementation Shortfall (IS) (Implementación Simplificada):**
    1.  Definir un horizonte de tiempo para la ejecución (p. ej., 60 minutos).
    2.  Definir un nivel de agresividad (p. ej., de 1 a 10).
    3.  El algoritmo participa más agresivamente (envía órdenes más grandes y frecuentes) al principio del horizonte y cuando el mercado se mueve a favor de la orden. La agresividad se reduce si el mercado se mueve en contra.

### 6.4. Métricas de Performance y KPIs

Los KPIs se calculan y almacenan diariamente para monitorear la salud del sistema.

| Métrica | Descripción | Objetivo Mínimo | Objetivo Ideal |
| :--- | :--- | :--- | :--- |
| **Sharpe Ratio (Anualizado)** | Retorno ajustado por riesgo | > 1.0 | > 2.0 |
| **Sortino Ratio (Anualizado)** | Retorno ajustado por riesgo de caída | > 1.5 | > 3.0 |
| **Máximo Drawdown** | Mayor pérdida desde un pico | < 10% | < 5% |
| **Profit Factor** | Ganancia Bruta / Pérdida Bruta | > 1.5 | > 2.5 |
| **Tasa de Acierto (%)** | % de trades ganadores | > 55% | > 65% |
| **Slippage Promedio (bps)** | Costo de ejecución promedio | < 0.5 bps | < 0.2 bps |

---

## 7. Fuentes

Este diseño se basa en la inteligencia y los datos recopilados de las siguientes fuentes primarias y secundarias:

*   [1] [IBKR Trading API Solutions](https://www.interactivebrokers.com/en/trading/ib-api.php) - Interactive Brokers
*   [2] [Rate Limiting - Saxo Bank OpenAPI](https://www.developer.saxo/openapi/learn/rate-limiting) - Saxo Bank
*   [3] [cTrader Open API](https://openapi.ctrader.com/) - Spotware (cTrader)
*   [4] [OANDA REST API v20 Introduction](https://developer.oanda.com/rest-live-v20/introduction/) - OANDA
*   [5] [Best Forex Brokers with Trading APIs for 2025](https://www.forexbrokers.com/guides/best-api-brokers) - ForexBrokers.com
*   [6] [Best API for Forex Market in 2025: A Comprehensive Guide](https://fcsapi.com/blog/best-api-for-forex-market-in-2025-a-comprehensive-guide/) - FCS API
*   [7] [Alpha Vantage Premium API Key](https://www.alphavantage.co/premium/) - Alpha Vantage
*   [8] [Powerful cloud forex trading API for MetaTrader](https://metaapi.cloud/) - MetaApi
*   [9] [Low Latency Metatrader API](https://www.mtsocketapi.com/) - MTsocketAPI
*   [10] [Introducing New & Improved FIX API for Real-Time Market](https://tradermade.com/blog/introducing-improved-fix-api) - TraderMade
*   [11] [Machine Learning for Market Microstructure and High Frequency Trading](https://www.cis.upenn.edu/~mkearns/papers/KearnsNevmyvakaHFTRiskBooks.pdf) - University of Pennsylvania
*   [12] [FX TCA Transaction Cost Analysis Whitepaper](https://www.lmax.com/documents/LMAXExchange-FX-TCA-Transaction-Cost-Analysis-Whitepaper.pdf) - LMAX Exchange
*   [13] [MiFIR Review Final Report on CTPs and DRSPs](https://www.esma.europa.eu/sites/default/files/2024-12/ESMA74-2134169708-7768_-_MiFIR_review_-_Final_Report_on_CTPs_and_DRSPs.pdf) - ESMA
*   [14] [HFT Architecture: Designing Systems for Hemang Dave](https://www.linkedin.com/pulse/high-frequency-trading-hft-architecture-designing-systems-hemang-dave-txjjf) - LinkedIn
*   [15] [Kernel Bypass Techniques in Linux for High-Frequency Trading](https://lambdafunc.medium.com/kernel-bypass-techniques-in-linux-for-high-frequency-trading-a-deep-dive-de347ccd5407) - Medium
*   [16] [In Pursuit of Ultra-Low Latency: FPGA in High-Frequency Trading](https://www.velvetech.com/blog/fpga-in-high-frequency-trading/) - Velvetech
*   [17] [Latency Arbitrage Glossary](https://questdb.com/glossary/latency-arbitrage/) - QuestDB
*   [18] [High Frequency Trading Infrastructure](https://dysnix.com/blog/high-frequency-trading-infrastructure) - Dysnix
*   [19] [Off-the-Shelf Neural Network Architectures for Forex Time Series Prediction come at a Cost](https://arxiv.org/abs/2405.10679) - arXiv
*   [20] [Temporal Convolutional Networks for Financial Time Series Forecasting: A Survey](https://www.researchgate.net/publication/392102503_Temporal_Convolutional_Networks_for_Financial_Time_Series_Forecasting_A_Survey) - ResearchGate
*   [21] [Enhancing Trading Performance Through Sentiment Analysis](https://arxiv.org/html/2507.09739v1) - arXiv
*   [22] [Backtest overfitting in the machine learning era: A comparison of out-of-sample testing techniques](https://www.sciencedirect.com/science/article/abs/pii/S0950705124011110) - Knowledge-Based Systems
*   [23] [Stock price prediction with attentive temporal convolution based generative adversarial network](https://www.sciencedirect.com/science/article/pii/S2590005625000013) - Neurocomputing
*   [24] [Application of Wavenet to financial times series prediction](https://bora.uib.no/bora-xmlui/handle/11250/3144546) - University of Bergen
*   [25] [The Future of Backtesting: A Deep Dive into Walk Forward Analysis](https://www.interactivebrokers.com/campus/ibkr-quant-news/the-future-of-backtesting-a-deep-dive-into-walk-forward-analysis/) - Interactive Brokers
*   [26] [Cross Validation in Finance: Purging, Embargoing, Combination](https://www.interactivebrokers.com/campus/ibkr-quant-news/cross-validation-in-finance-purging-embargoing-combination/) - Interactive Brokers
*   [27] [Feature Engineering in Trading: Turning Data into Insights](https://www.luxalgo.com/blog/feature-engineering-in-trading-turning-data-into-insights/) - LuxAlgo
*   [28] [A Deep Reinforcement Learning Approach for Trading Optimization in the Forex Market with Multi-Agent Asynchronous Distribution](https://arxiv.org/abs/2405.19982) - arXiv
*   [29] [A comparative study of ensemble learning algorithms for high-frequency trading](https://www.sciencedirect.com/science/article/pii/S2468227624001066) - ScienceDirect
*   [30] [Fx-spot predictions with state-of-the-art transformer and time embeddings](https://www.sciencedirect.com/science/article/pii/S0957417424004032) - ScienceDirect
*   [31] [A-Share Quantitative Investment Strategy for Multiple Objectives Driven by Machine Learning and Deep Learning](https://dl.acm.org/doi/10.1145/3745238.3745386) - ACM Digital Library
*   [32] [An Efficient deep learning model to Predict Stock Price Movement in High Frequency Trading Using Limit Order Book](https://arxiv.org/abs/2505.22678) - arXiv
*   [33] [Deep Reinforcement Learning for Optimizing Order Book Imbalance-Based High-Frequency Trading Strategies](https://www.researchgate.net/publication/391292844_Deep_Reinforcement_Learning_for_Optimizing_Order_Book_Imbalance-Based_High-Frequency_Trading_Strategies) - ResearchGate
*   [34] [Predicting Chinese stock market using XGBoost multi-objective optimization with optimal weighting](https://pmc.ncbi.nlm.nih.gov/articles/PMC10936758/) - PMC/NCBI
*   [35] [A Self-Rewarding Mechanism in Deep Reinforcement Learning for Financial Trading](https://www.mdpi.com/2227-7390/12/24/4020) - MDPI Mathematics
*   [36] [Proactive Model Adaptation Against Concept Drift for Online Time Series Forecasting](https://arxiv.org/abs/2412.08435) - arXiv
*   [37] [Smart adaptive ensemble model for multiclass imbalanced concept drift data streams](https://www.nature.com/articles/s41598-025-05122-w) - Nature Scientific Reports
*   [38] [2024 China Fintech Academic Annual Conference Held in Shanghai](https://www.acem.sjtu.edu.cn/en/news/82904.html) - Shanghai Jiao Tong University ACEM
*   [39] [Intelligent approach to detecting online fraudulent trading with concept drift adaptation](https://www.nature.com/articles/s41598-025-01223-8) - Nature Scientific Reports
*   [40] [Deep learning for algorithmic trading: A systematic review of financial applications](https://www.sciencedirect.com/science/article/pii/S2590005625000177) - ScienceDirect
*   [41] [Deep Learning for VWAP Execution in Crypto Markets](https://arxiv.org/pdf/2502.13722.pdf) - arXiv
*   [42] [Hedge Fund Use of AI Report 2024](https://www.hsgac.senate.gov/wp-content/uploads/2024.06.11-Hedge-Fund-Use-of-AI-Report.pdf) - U.S. Senate
*   [43] [Implementation Shortfall - One Objective, Many Algorithms](https://www.cis.upenn.edu/~mkearns/finread/impshort.pdf) - University of Pennsylvania
*   [44] [Portfolio Allocation and Asset Management Algorithms 2023-2024](http://www.thierry-roncalli.com/download/AM-Lectures.pdf) - Thierry Roncalli
*   [45] [Real-time Risk Management in Algorithmic Trading](https://theaiquant.medium.com/real-time-risk-management-in-algorithmic-trading-strategies-for-mitigating-exposure-0a940b5e924b) - Medium
*   [46] [Market Making Trading Strategies for 2024](https://bookmap.com/blog/the-secrets-of-market-making-liquidity-strategies-every-trader-must-know) - Bookmap
*   [47] [Alternative Data for Algorithmic Trading: What Works?](https://www.luxalgo.com/blog/alternative-data-for-algorithmic-trading-what-works/) - LuxAlgo
*   [48] [Advanced Order Flow Trading: Spotting Hidden Liquidity & Iceberg Orders](https://bookmap.com/blog/advanced-order-flow-trading-spotting-hidden-liquidity-iceberg-orders) - Bookmap
*   [49] [Most Sophisticated Institutional Trading Algorithms](https://www.win-algo.com/index.php/blog/32-most-sophisticated-institutional-trading-algorithms-for-market-making-order-execution-and-trading) - Win-Algo
