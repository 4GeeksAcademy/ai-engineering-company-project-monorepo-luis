# Diseño del Pipeline de Desempeño de Negocio (Business Performance Data Pipeline)

> **Documento de Diseño Arquitectónico — Hito 1**  
> **Estado:** En progreso (Etapa 1: Estado Actual, Brecha de Negocio y Propósito)  
> **Destino en Monorepo:** `data/pipelines/PIPELINE_DESIGN.md`  
> **Contexto Organizacional:** Nexova Inc. — División de Operaciones, Logística y Capacitación (L&D)

---

## 1. Estado Actual y Diagnóstico Técnico

### 1.1. Arquitectura Actual de Telemetría y Almacenamiento
En la infraestructura actual de Nexova, la ingesta de telemetría está desacoplada de la base transaccional de inventario (`inventory.db` SQLite) mediante una capa de persistencia en PostgreSQL / Supabase gestionada por `services/api/telemetry_storage.py` y expuesta a través del endpoint `POST /telemetry/events` (`services/api/routers/telemetry.py`).

Los eventos entrantes son validados frente al registro estricto `docs/telemetry/event-schemas.json` y se persisten de manera atómica y en lote (*bulk*) dentro de la tabla append-only `telemetry_events`:

| Columna | Tipo de Dato | Rol Arquitectónico |
| :--- | :--- | :--- |
| `id` | `UUID` (PK) | Identificador único del evento generado por `gen_random_uuid()`. |
| `timestamp` | `TIMESTAMPTZ` | Marca temporal UTC en la que ocurrió el evento en el cliente o servicio. |
| `service` | `VARCHAR` | Servicio de origen controlado (`backoffice`, etc.). |
| `event_type` | `VARCHAR` | Identificador taxonómico validado del catálogo. |
| `level` | `VARCHAR` | Severidad operativa (`info`, `warn`, `error`). |
| `value` | `NUMERIC` | Métrica numérica directa opcional (e.g. latencia `duration_ms`). |
| `message` | `VARCHAR` | Siempre `NULL` para prevenir fugas de texto no estructurado o PII. |
| `tags` | `JSONB` | Propiedades validadas del evento (dimensiones de negocio y cantidades). |

### 1.2. Alcance del Reporte Técnico Existente y sus Límites
El módulo de reporte técnico actual (`services/telemetry/analysis.py` y `GET /telemetry/report`) está concebido exclusivamente para el equipo de **Ingeniería y DevOps**. Su función se limita a métricas de salud técnica de la plataforma:
- Conteo y volumen de eventos procesados, almacenados y rechazados por tipo.
- Frecuencia y ratios de errores técnicos (`api_request_failed`, `frontend_uncaught_error`, `auth_login_failed`).
- Latencias de red y tiempos de carga de página (`api_latency_recorded`, `page_load_recorded`).
- Estado de disponibilidad de los componentes de software.

### 1.3. Identificación de la Brecha de Negocio
Existe una desconexión crítica entre los datos disponibles en la telemetría y la información requerida para la toma de decisiones de negocio:
- **La necesidad no resuelta:** Laura (CEO) y Elena (Gerente de L&D) requieren evaluar la eficiencia de la formación interna y el abastecimiento de equipos entre sedes. Necesitan saber con exactitud cuánto capital se está comprometiendo en materiales formativos por programa, cuántos kits llegan a manos de los participantes, y con qué frecuencia las operaciones sufren desabastecimiento o sobrecostos en **Valencia vs. Miami**.
- **La brecha técnica:** El reporte técnico actual no realiza agregaciones temporales de negocio (semanales ISO), ignora el cruce dimensional por oficina y programa (`programme_id`), no totaliza costos monetarios, ni discrimina transacciones logísticas (`inbound_order_created` vs. `outbound_order_created`). Para un stakeholder no técnico, una lista de errores 500 y latencias en milisegundos no responde si la operación en Miami está desbordando el presupuesto o si Valencia se está quedando sin kits de certificación.

### 1.4. Separación Arquitectónica Estricta
El nuevo pipeline de datos para desempeño de negocio se diseña como una capa analítica **adicional e independiente**, respetando rigurosamente las siguientes fronteras:
1. **`telemetry_events` es fuente de solo lectura:** El nuevo pipeline extrae registros pero **nunca** escribe datos agregados ni estados de ejecución en `telemetry_events`.
2. **Inmutabilidad de la telemetría técnica:** No se modifica `services/telemetry/analysis.py` ni el contrato de `GET /telemetry/report`.
3. **Aislamiento de consumo:** Los futuros endpoints de negocio residirán en un módulo independiente `services/reporting/`, completamente desacoplado de `services/telemetry/`.

---

## 2. Propósito del Pipeline y Especificación de KPIs

### 2.1. Declaración de Propósito
> **Propósito:** Consolidar semanalmente los eventos de telemetría de inventario en métricas auditables de desempeño de negocio —costo de material (`inbound_order_created`), kits entregados (`outbound_order_created`), frecuencia de escasez (`stock_threshold_triggered`) y variaciones anómalas de costo (`kit_cost_variance_detected`)— para proveer a Laura (CEO) y Elena (Gerente de L&D) un reporte comparativo entre las sedes de Valencia y Miami disponible cada lunes por la mañana en UTC.

### 2.2. Audiencia, Cadencia y Grano Dimensional
- **Audiencia Principal:** Laura (CEO) y Elena (Gerente de Aprendizaje y Desarrollo / L&D).
- **Cadencia de Ejecución:** Semanal, programada para ejecutarse automáticamente los **lunes a primera hora (05:00 UTC)** para procesar la semana calendario ISO recién culminada.
- **Grano de Agregación:** Una fila única por la tupla:
  $$\text{Grano} = (\text{office}, \text{programme\_id}, \text{week\_start})$$
  donde:
  - `office`: Sede operativa (`valencia` o `miami`).
  - `programme_id`: Identificador del programa formativo (e.g. `data-eng-q4`, `ai-core-2026`).
  - `week_start`: Fecha de inicio de la semana ISO (lunes a las 00:00:00 UTC).

### 2.3. Tratamiento de Divisas
- **Aislamiento estricto de moneda:** Cada sede opera con su divisa local:
  - **Valencia:** Euro (`EUR`).
  - **Miami:** Dólar estadounidense (`USD`).
- **Regla del Hito 1:** No se realiza conversión cambiaria ni consolidación entre divisas distintas. Las cifras financieras de Valencia permanecen en `EUR` y las de Miami en `USD`, manteniendo la columna `currency` asociada a la oficina.

### 2.4. Eventos Fuente Obligatorios y Extensión Aditiva del Esquema
El pipeline se nutre de cuatro eventos de telemetría de negocio registrados en `telemetry_events`:

| Evento de Telemetría | KPI de Negocio que Alimenta | Mecanismo de Agregación |
| :--- | :--- | :--- |
| `inbound_order_created` | **Costo total de material** (`total_material_cost`) | Suma del costo financiero de los pedidos de entrada en la semana. |
| `outbound_order_created` | **Kits formativos entregados** (`kits_delivered_count`) | Conteo de órdenes de salida completadas para alumnos/consultores. |
| `stock_threshold_triggered`| **Frecuencia de escasez** (`shortage_events_count`) | Conteo de alertas donde el stock cayó por debajo del mínimo seguro. |
| `kit_cost_variance_detected`| **Frecuencia de variación de costo** (`cost_variance_events_count`) | Conteo de anomalías de precio unitario frente al histórico. |

#### Auditoría del Payload de `inbound_order_created`:
Para el cálculo del KPI de costo de material, el payload en `tags` debe contener información de coste. La auditoría del catálogo formal (`docs/telemetry/event-schemas.json`) revela:
- El esquema actual ya especifica de forma nativa `unit_cost` (número requerido $\ge 0$), `quantity` (entero requerido $\ge 1$), `currency` (`EUR` o `USD`), y un campo aditivo opcional `total_cost` (número $\ge 0$).
- **Regla de Extracción Aditiva:**
  $$\text{Costo de Línea} = \begin{cases} \text{tags}\to\text{'total\_cost'} & \text{si existe y no es nulo} \\ (\text{tags}\to\text{'unit\_cost'}) \times (\text{tags}\to\text{'quantity'}) & \text{en caso contrario} \end{cases}$$
  Cualquier enriquecimiento futuro de este payload se gestiona bajo el principio de **extensión aditiva** (campos opcionales compatibles hacia atrás), sin romper el contrato del colector ni modificar el reporte técnico.
