# Diseño del Pipeline de Desempeño de Negocio (Business Performance Data Pipeline)

> **Documento de Diseño Arquitectónico — Hito 1**  
> **Estado:** En progreso (Etapas 1 y 2 completadas)  
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

---

## 3. Arquitectura del Pipeline y Modelo de Datos (ETL)

### 3.1. Fuentes de Extracción y Formato de Datos
- **Fuente Principal:** Tabla PostgreSQL `public.telemetry_events` (alojada en Supabase).
- **Criterio de Extracción Temporal:** Filtrado indexado por partición semanal:
  $$\text{timestamp} \ge \text{week\_start} \quad \text{AND} \quad \text{timestamp} < \text{week\_start} + 7\,\text{días}$$
  donde `week_start` representa el lunes a las 00:00:00 UTC de la semana a procesar.
- **Filtro Taxonómico de Eventos:**
  ```sql
  event_type IN (
      'inbound_order_created',
      'outbound_order_created',
      'stock_threshold_triggered',
      'kit_cost_variance_detected'
  )
  ```
- **Envelope y Extracción de Dimensiones:**
  Los atributos analíticos se leen directamente del campo semiestructurado `tags` (JSONB):
  - `office`: Cadena (`valencia` o `miami`).
  - `programme_id`: Identificador del programa (e.g. `ml-ops-track`).
  - `currency`: Validación estricta (`EUR` si `valencia`, `USD` si `miami`).
  - Valores de métricas (`unit_cost`, `total_cost`, `quantity`).
- **Análisis de Tablas de Dominio Adicionales (Trade-off de Desacoplamiento):**
  Se evalúa si es necesario unir (*JOIN*) con tablas del sistema transaccional de inventario (`items`, `orders`, `suppliers`).
  - **Decisión Arquitectónica:** **No se consultan tablas de dominio transaccionales en este pipeline.**
  - **Justificación:** Los eventos de telemetría de Nexova fueron diseñados como "eventos enriquecidos autocontenidos" (*self-contained fat events*). Incluyen `office`, `programme_id`, `product_category`, `currency` y `costs`. Consultar la base de datos operacional transaccional (SQLite `inventory.db`) crearía un acoplamiento indeseado de infraestructura, riesgo de bloqueo transaccional (*table locks*) y degradación de rendimiento de la API en horas de operación. La telemetría ofrece una fuente inmutable desacoplada óptima para la analítica.

---

### 3.2. Diagrama de Flujo de Datos (Arquitectura ETL)

```mermaid
flowchart TD
    subgraph S1["1. Origen de Datos (Solo Lectura)"]
        TE[("telemetry_events<br/>(Supabase PostgreSQL)")<br/>• timestamp (TIMESTAMPTZ)<br/>• event_type (VARCHAR)<br/>• tags (JSONB)]
    end

    subgraph S2["2. Pipeline Orquestado (data/pipelines/)"]
        direction TB
        E["Task: extract_telemetry_events<br/>Filtro: [week_start, week_end)<br/>Eventos de inventario requeridos"]
        T["Task: transform_weekly_kpis<br/>• Normalizar semana ISO (lunes 00:00 UTC)<br/>• Agrupar por (office, programme_id, week_start)<br/>• Sumar total_material_cost<br/>• Contar kits_delivered_count<br/>• Contar shortage_events_count<br/>• Contar cost_variance_events_count<br/>• Preservar currency nativa"]
        L["Task: load_reporting_metrics<br/>UPSERT transaccional idempotente en lote"]
        
        E -->|Dataset crudo validado| T
        T -->|Filas agregadas por grano| L
    end

    subgraph S3["3. Capa de Persistencia Analítica (reporting)"]
        DEST[("reporting.weekly_office_program_performance<br/>Clave única: (office, programme_id, week_start)<br/>• total_material_cost<br/>• kits_delivered_count<br/>• shortage_events_count<br/>• cost_variance_events_count<br/>• currency / computed_at / run_id")]
        AUDIT[("reporting.pipeline_execution_logs<br/>Trazabilidad de corridas y auditoría")]
    end

    subgraph S4["4. Capa de Servicios y Exposición (services/reporting/)"]
        EP1["GET /reporting/status<br/>(Última corrida / salud)"]
        EP2["POST /reporting/pipeline/trigger<br/>(Disparo manual / reproceso)"]
        EP3["GET /reporting/kpis/weekly<br/>(Dashboard Laura & Elena)"]
    end

    TE -->|Lectura SQL indexada| E
    L -->|ON CONFLICT DO UPDATE| DEST
    L -.->|Log de ejecución / métricas| AUDIT
    DEST -->|Consultas de agregados sin ETL| EP3
    AUDIT -->|Consulta de estado| EP1
    EP2 -->|Invoca ejecución en| E
```

---

### 3.3. Esquema y Modelo de Destino (`reporting.weekly_office_program_performance`)

Para garantizar aislamiento físico y de permisos, los datos de desempeño residirán en un esquema PostgreSQL dedicado denominado `reporting`.

#### Definición DDL Formal:
```sql
CREATE SCHEMA IF NOT EXISTS reporting;

CREATE TABLE reporting.weekly_office_program_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    office VARCHAR(20) NOT NULL,
    programme_id VARCHAR(100) NOT NULL,
    week_start DATE NOT NULL,
    total_material_cost NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    kits_delivered_count INTEGER NOT NULL DEFAULT 0,
    shortage_events_count INTEGER NOT NULL DEFAULT 0,
    cost_variance_events_count INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    run_id UUID NOT NULL,

    -- Restricciones de Dominio y Consistencia
    CONSTRAINT chk_office CHECK (office IN ('valencia', 'miami')),
    CONSTRAINT chk_currency CHECK (
        (office = 'valencia' AND currency = 'EUR') OR
        (office = 'miami' AND currency = 'USD')
    ),
    CONSTRAINT chk_non_negative_cost CHECK (total_material_cost >= 0),
    CONSTRAINT chk_non_negative_counts CHECK (
        kits_delivered_count >= 0 AND
        shortage_events_count >= 0 AND
        cost_variance_events_count >= 0
    ),

    -- Clave Natural de Unicidad (Garantía de Grano)
    CONSTRAINT uq_weekly_office_programme UNIQUE (office, programme_id, week_start)
);

-- Índices Analíticos para Consumo del Dashboard
CREATE INDEX idx_weekly_perf_query 
    ON reporting.weekly_office_program_performance (week_start DESC, office, programme_id);

CREATE INDEX idx_weekly_perf_run 
    ON reporting.weekly_office_program_performance (run_id);
```

#### Diccionario de Datos:
- `id`: Clave subrogada única de registro.
- `office`: Oficina física responsable (`valencia` o `miami`).
- `programme_id`: Identificador de programa formativo asignado.
- `week_start`: Fecha de inicio de la semana ISO (siempre lunes, UTC).
- `total_material_cost`: Inversión total en compras (`inbound_order_created`) en la moneda de la sede.
- `kits_delivered_count`: Volumen de entregas a participantes (`outbound_order_created`).
- `shortage_events_count`: Incidentes de caída bajo stock mínimo (`stock_threshold_triggered`).
- `cost_variance_events_count`: Anomalías de costo detectadas (`kit_cost_variance_detected`).
- `currency`: Moneda obligatoria según sede (`EUR` o `USD`).
- `computed_at`: Marca temporal exacta del cálculo analítico.
- `run_id`: Identificador de la corrida del pipeline orquestador para auditoría completa.

---

### 3.4. Estrategia de Actualizaciones, Deduplicación y UPSERT

En procesamiento de datos analíticos, la ejecución semanal puede coincidir con reprocesamientos manuales o actualizaciones retroactivas.

#### Mecanismo de Actualización Idempotente (UPSERT):
En lugar de fallar por violación de clave primaria o insertar registros duplicados, la carga utiliza la cláusula `ON CONFLICT` de PostgreSQL sobre la restricción natural única `(office, programme_id, week_start)`:

```sql
INSERT INTO reporting.weekly_office_program_performance (
    office,
    programme_id,
    week_start,
    total_material_cost,
    kits_delivered_count,
    shortage_events_count,
    cost_variance_events_count,
    currency,
    computed_at,
    run_id
) VALUES (
    :office,
    :programme_id,
    :week_start,
    :total_material_cost,
    :kits_delivered_count,
    :shortage_events_count,
    :cost_variance_events_count,
    :currency,
    clock_timestamp(),
    :run_id
)
ON CONFLICT (office, programme_id, week_start)
DO UPDATE SET
    total_material_cost = EXCLUDED.total_material_cost,
    kits_delivered_count = EXCLUDED.kits_delivered_count,
    shortage_events_count = EXCLUDED.shortage_events_count,
    cost_variance_events_count = EXCLUDED.cost_variance_events_count,
    currency = EXCLUDED.currency,
    computed_at = EXCLUDED.computed_at,
    run_id = EXCLUDED.run_id;
```

#### Análisis de Trade-Offs de la Estrategia de Carga:
| Estrategia | Ventajas | Desventajas | Decisión |
| :--- | :--- | :--- | :--- |
| **Append-Only (Sin restricción)** | Inserción ultra rápida sin comprobación de índices. | Produce duplicados de negocio en reintentos o reprocesos; falsea totales en sumas. | **Descartada**. Inviable para KPIs auditables. |
| **Delete Partition + Insert (`DELETE WHERE week_start = :w`)** | Garantiza que no queden programas huérfanos que hayan desaparecido. | Crea una ventana temporal de lectura vacía (*dirty read*) si el dashboard consulta en medio de la transacción; bloqueo más agresivo. | **Descartada** para la carga normal por fila/lote. |
| **Atomic UPSERT (`ON CONFLICT DO UPDATE`)** | **Idempotencia total**, lecturas concurrentes sin ventanas vacías, actualiza métricas y preserva el `run_id` más reciente de forma atómica. | Requiere mantener un índice de unicidad y un mínimo sobrecosto de resolución de conflictos. | **Seleccionada**. Máxima resiliencia y consistencia para consultas en vivo. |

---

### 3.5. Aislamiento Modular: `services/reporting/`

Para mantener la separación arquitectónica exigida por Nexova:
- El módulo de ingeniería y observabilidad técnica permanece confinado en `services/telemetry/`.
- El nuevo consumo de analítica de negocio se establece en `services/reporting/`.
- La orquestación y transformación residen exclusivamente en `data/pipelines/`. Los servicios en `services/reporting/` únicamente consultan la tabla `reporting.weekly_office_program_performance` y la tabla de logs de ejecución, actuando como capa de servicio ligera sin lógica ETL acoplada.
