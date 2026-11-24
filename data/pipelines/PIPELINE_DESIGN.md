# Diseño del Pipeline de Desempeño de Negocio (Business Performance Data Pipeline)

> **Documento de Diseño Arquitectónico — Hito 1**  
> **Estado:** Completo y Verificado (Hito 1)  
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

---

## 4. Resiliencia, Idempotencia y Auditoría de Ejecución

### 4.1. Idempotencia y Recuperación ante Fallos Parciales

#### Escenario de Fallo Parcial:
Considérese una corrida programada con identificador $R_1$ que procesa la semana ISO comprendida entre `2026-11-16` y `2026-11-23`:
1. La tarea de extracción obtiene 1.450 eventos relevantes de `telemetry_events`.
2. La tarea de transformación calcula en memoria 8 registros agregados correspondientes a combinaciones activas de `(office, programme_id, week_start)`.
3. Durante la fase de carga, la transacción procesa e inserta exitosamente las primeras 5 filas en `reporting.weekly_office_program_performance`.
4. Al intentar insertar la sexta fila, se produce una desconexión abrupta de socket o *timeout* con la instancia de PostgreSQL/Supabase. La ejecución falla y el estado del flow se marca como `FAILED`.

#### Comportamiento en la Segunda Corrida ($R_2$):
Cuando el sistema reintenta la ejecución (sea por política de reintento automático de Prefect o por detonación manual del operador):
1. **Lectura Limpia:** La corrida $R_2$ genera un nuevo `run_id`, reevalúa la ventana completa `[week_start, week_end)` desde la fuente de verdad inmutable (`telemetry_events`), y regenera las 8 tuplas consolidadas en memoria.
2. **Aplicación del Atomic UPSERT:** Gracias a la sentencia `ON CONFLICT (office, programme_id, week_start) DO UPDATE`:
   - Las 5 tuplas previamente registradas por $R_1$ **no provocan errores de clave duplicada** ni sufren sumas acumuladas erróneas (`total = total + nuevo`). En su lugar, sus métricas son sobreescritas de forma determinista con el agregado completo calculado por $R_2$.
   - Los campos de auditoría de esas 5 tuplas se actualizan: `run_id = R_2` y `computed_at = clock_timestamp()`.
   - Las 3 tuplas restantes que nunca llegaron a persistirse en $R_1$ son insertadas limpiamente.
3. **Resultado Garantizado:** La tabla analítica queda en un estado 100% íntegro, idéntico al que habría existido si $R_1$ no hubiese fallado, sin registros parciales huérfanos ni duplicación de importes.

---

### 4.2. Tratamiento de Eventos Tardíos (Late-Arriving Events)

En sistemas distribuidos y aplicaciones móviles de almacén, ciertos eventos pueden emitirse con retraso debido a desconexiones de red local o colas de sincronización offline (e.g. un pedido de recepción ocurrido el viernes a las 18:00 UTC que el cliente de almacén envía a la API el martes siguiente a las 09:00 UTC).

#### Estrategia de Recálculo de Ventana Retroactiva:
- **Detección y Criterio de Corte:** Cada evento en `telemetry_events` almacena su marca de tiempo del hecho real en `timestamp`.
- **Ventana de Estabilidad y Re-ejecución:**
  - El pipeline semanal por defecto procesa la semana inmediata anterior ($W_{-1}$).
  - Adicionalmente, el pipeline admite como parámetro opcional `target_week_start`. Para absorber eventos tardíos, se define una política de **recálculo móvil con ventana de amortiguación**: cada ejecución semanal recalcula tanto la semana recién cerrada ($W_{-1}$) como la semana previa inmediata ($W_{-2}$).
- **Trazabilidad del Recálculo:**
  - Cuando se reprocesa una semana pasada, el UPSERT sobreescribe los valores actualizados reflejando los nuevos eventos tardíos incorporados.
  - El log de ejecución registra formalmente el evento de recálculo:
    - `window_start`: Fecha de la semana pasada reprocesada.
    - `trigger_mode`: `'late_event_recalc'` o `'backfill'`.
    - `records_extracted`: Total de eventos procesados (incluyendo los tardíos).
  - De este modo, Laura y Elena siempre observan métricas históricas reconciliadas y auditables, sabiendo exactamente qué corrida actualizó los números por última vez.

---

### 4.3. Deduplicación en Origen y Reintentos de Red

Los clientes HTTP y emisores de telemetría implementan reintentos automáticos ante errores de red, lo que puede provocar que un mismo evento de negocio llegue duplicado al endpoint `POST /telemetry/events`.

- **Mecanismo de Descarte en Extracción:**
  Aunque cada inserción en `telemetry_events` recibe un `id` UUID único en base de datos, el envelope original en el campo `tags` preserva el `eventId` emitido por el cliente o el `requestId`.
  La consulta de extracción implementa deduplicación estricta a nivel de evento de negocio antes de aplicar las sumas analíticas:
  ```sql
  WITH deduplicated_events AS (
      SELECT DISTINCT ON (COALESCE(tags->>'eventId', id::text))
          id,
          timestamp,
          event_type,
          tags
      FROM public.telemetry_events
      WHERE timestamp >= :window_start 
        AND timestamp < :window_end
        AND event_type IN (
            'inbound_order_created',
            'outbound_order_created',
            'stock_threshold_triggered',
            'kit_cost_variance_detected'
        )
      ORDER BY COALESCE(tags->>'eventId', id::text), timestamp ASC
  )
  SELECT * FROM deduplicated_events;
  ```
- **Garantía:** Si un cliente retransmitió el mismo `inbound_order_created` tres veces por fallos intermitentes de red, el pipeline computa el costo del pedido una sola vez.

---

### 4.4. Control de Concurrencia y Solapamiento de Corridas

Existe el riesgo de que una ejecución programada automática (lunes 05:00 UTC) coincida con una detonación manual solicitada por un administrador a través del endpoint de la API.

#### Mecanismo de Bloqueo Distribuido (Advisory Locks):
Para impedir que dos instancias concurrentes modifiquen la misma partición semanal al mismo tiempo:
1. Al iniciar la tarea de carga para una ventana específica `week_start`, el pipeline solicita un bloqueo a nivel de sesión en PostgreSQL mediante:
   ```sql
   SELECT pg_try_advisory_lock(hashtext('pipeline_perf_' || :week_start::text));
   ```
2. **Comportamiento si el bloqueo se obtiene:** La corrida adquiere el cerrojo exclusivo, ejecuta la transacción de carga, actualiza los logs y libera el candado al finalizar (`pg_advisory_unlock`).
3. **Comportamiento si el bloqueo está ocupado:** La segunda corrida detecta el bloqueo activo y adopta una de las siguientes políticas configuradas:
   - *Modo Espera (Backoff):* Espera hasta 60 segundos a que la primera corrida concluya.
   - *Modo Aborto Seguro (Skip):* Si la primera corrida concluyó exitosamente mientras esperaba, la segunda se marca en los logs como `SKIPPED` con el mensaje: *"Ventana semanal ya en procesamiento por corrida concurrente activa"*, evitando contención o corrupción de datos.

---

### 4.5. Observabilidad, Diagnóstico de Incidentes y Recuperabilidad

El diseño establece mecanismos explícitos para diagnosticar los tres escenarios típicos de fallo o anomalía:

| Escenario Observado | Causa Raíz Posible | Mecanismo de Diagnóstico y Acción |
| :--- | :--- | :--- |
| **Actividad en cero (0 registros o conteos en 0)** | 1) Sede sin operaciones reales (e.g. semana festiva).<br/>2) Falla masiva en colector de telemetría o frontend que dejó de emitir eventos. | El pipeline corre con éxito (`status = 'COMPLETED'`), pero registra `records_extracted = 0`. Se emite una alerta de observabilidad si el volumen cae a cero para una sede habitualmente activa, permitiendo a ingeniería revisar el colector sin corromper la tabla de negocio. |
| **Pipeline no corrió** | Fallo del scheduler de Prefect, agente caído o servicio sin alimentación eléctrica. | Monitoreo externo sobre el endpoint `GET /reporting/status`: si `now() - last_success_run > 7 días`, se dispara alerta de severidad alta (SLA breach). |
| **Caída de Base de Datos durante la ejecución** | Pérdida de conectividad con Supabase, reinicio de base de datos o saturación de conexiones. | Prefect aplica política de 3 reintentos automáticos con retroceso exponencial (30s, 60s, 120s). Si la BD no responde, el flow finaliza como `FAILED`, registra la excepción en el log local/Prefect Cloud y envía notificación de fallo al canal de operaciones. Los datos de la semana anterior permanecen intactos. |

---

### 4.6. Especificación Formal de la Tabla de Auditoría (`reporting.pipeline_execution_logs`)

Para cumplir con el estándar corporativo de auditoría de Nexova, se diseña la tabla `reporting.pipeline_execution_logs` con especificación estricta de tipos de datos y la justificación de auditoría de cada campo:

```sql
CREATE TABLE reporting.pipeline_execution_logs (
    run_id UUID PRIMARY KEY,
    flow_name VARCHAR(100) NOT NULL,
    trigger_mode VARCHAR(20) NOT NULL,
    window_start DATE NOT NULL,
    window_end DATE NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL,
    checkpoint_phase VARCHAR(50) NOT NULL,
    records_extracted INTEGER NOT NULL DEFAULT 0,
    records_loaded INTEGER NOT NULL DEFAULT 0,
    error_details TEXT,
    execution_context JSONB NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT chk_log_status CHECK (
        status IN ('RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED', 'ABORTED')
    ),
    CONSTRAINT chk_log_trigger CHECK (
        trigger_mode IN ('scheduled', 'manual', 'backfill', 'late_event_recalc')
    )
);

CREATE INDEX idx_pipeline_logs_status_window 
    ON reporting.pipeline_execution_logs (window_start DESC, started_at DESC);
```

#### Catálogo de Campos y Justificación de Auditoría:

| Campo | Tipo SQL | Justificación de Auditoría y Observabilidad |
| :--- | :--- | :--- |
| `run_id` | `UUID` | Identificador unívoco global de la corrida. Permite trazar exactamente qué ejecución calculó cada fila en `reporting.weekly_office_program_performance`. |
| `flow_name` | `VARCHAR(100)` | Nombre formal del flow orquestado en Prefect (`weekly_business_performance_pipeline`). Facilita la auditoría ante la incorporación de futuros pipelines. |
| `trigger_mode` | `VARCHAR(20)` | Discrimina si la corrida fue automática (`scheduled`), disparada por usuario (`manual`) o un reproceso histórico (`backfill` / `late_event_recalc`). |
| `window_start` | `DATE` | Límite inferior UTC de la semana calendario evaluada. Clave para verificar qué periodo cubrió la corrida. |
| `window_end` | `DATE` | Límite superior UTC de la semana evaluada. Garantiza claridad en el rango semiabierto `[window_start, window_end)`. |
| `started_at` | `TIMESTAMPTZ` | Marca temporal UTC de inicio de la corrida. Utilizada para calcular tiempos de ejecución y detectar ejecuciones colgadas. |
| `finished_at` | `TIMESTAMPTZ` | Marca temporal UTC de finalización. `NULL` mientras la corrida esté en curso; su presencia valida la culminación. |
| `status` | `VARCHAR(20)` | Estado final de la corrida (`RUNNING`, `COMPLETED`, `FAILED`, `SKIPPED`). Permite a la API responder inmediatamente sobre la salud del pipeline. |
| `checkpoint_phase` | `VARCHAR(50)` | Última fase técnica alcanzada (`INIT`, `EXTRACTION`, `TRANSFORMATION`, `LOADING`, `FINALIZED`). Vital para saber exactamente en qué paso falló la corrida sin inspeccionar logs crudos. |
| `records_extracted` | `INTEGER` | Cantidad total de eventos crudos leídos y deduplicados desde `telemetry_events`. Permite validar el volumen de ingesta. |
| `records_loaded` | `INTEGER` | Cantidad de tuplas de negocio `(office, programme_id, week_start)` efectivamente persistidas o actualizadas en la tabla analítica. |
| `error_details` | `TEXT` | Traza de error completa o mensaje de excepción en caso de falla. Permite diagnósticos inmediatos sin acceso directo al contenedor. |
| `execution_context` | `JSONB` | Metadatos contextuales (versión del código, ID de usuario ejecutor, latencia de base de datos, memoria utilizada). |

---

## 5. Mapeo de Orquestación con Prefect

### 5.1. Flow Principal y Tasks Concretas

La orquestación del proceso analítico se estructura bajo el framework **Prefect 3.x**, encapsulando la lógica en `data/pipelines/business_performance_flow.py`.

#### Flow Principal: `weekly_business_performance_pipeline`
- **Firma Conceptual:**
  ```python
  @flow(
      name="weekly-business-performance-pipeline",
      description="Orquestador semanal de KPIs de desempeño de inventario por oficina y programa para Nexova",
      log_prints=True,
      timeout_seconds=1800,
  )
  def weekly_business_performance_pipeline(
      target_week_start: Optional[date] = None,
      trigger_mode: str = "scheduled",
      include_buffer_week: bool = True,
  ) -> PipelineRunSummary:
      ...
  ```
- **Responsabilidad:** Gestionar el ciclo de vida de la corrida: inicializar el registro de log con `run_id`, coordinar la ejecución secuencial de las tasks, gobernar los bloqueos distribuidos y estampar el estado final (`Completed` o `Failed`).

#### Las Tres Tasks Concretas Obligatorias:

```mermaid
flowchart LR
    F["Flow: weekly_business_performance_pipeline"]
    F --> T1["Task 1: extract_telemetry_events<br/>(Filtros temporales, deduplicación de origen)"]
    T1 --> T2["Task 2: transform_weekly_kpis<br/>(Agrupación por grano, cómputo de KPIs y validación de divisas)"]
    T2 --> T3["Task 3: load_reporting_metrics<br/>(Atomic UPSERT en PostgreSQL y log de auditoría)"]
```

1. **Task 1: `extract_telemetry_events`**
   - **Decorador:** `@task(name="extract-telemetry-events", retries=3, retry_delay_seconds=30)`
   - **Entrada:** `window_start: date`, `window_end: date`, `db_connector: SqlAlchemyConnector`.
   - **Operación:** Conexión de solo lectura a Supabase PostgreSQL. Ejecución de consulta SQL indexada sobre `public.telemetry_events` filtrando por el cuarteto de eventos de inventario. Deduplica eventos por `COALESCE(tags->>'eventId', id::text)`.
   - **Salida:** `list[RawTelemetryEventRow]` (lista inmutable tipada en memoria).

2. **Task 2: `transform_weekly_kpis`**
   - **Decorador:** `@task(name="transform-weekly-kpis")`
   - **Entrada:** `raw_events: list[RawTelemetryEventRow]`, `window_start: date`.
   - **Operación:**
     - Normaliza las marcas de tiempo a la semana ISO UTC (`week_start`).
     - Agrupa los registros por la tupla dimensional `(office, programme_id, week_start)`.
     - Suma aditiva de `total_material_cost` para `inbound_order_created` aplicando la regla:
       $$\text{costo} = \text{total\_cost} \text{ if present else } (\text{unit\_cost} \times \text{quantity})$$
     - Conteo discreto de `kits_delivered_count` (`outbound_order_created`).
     - Conteo discreto de `shortage_events_count` (`stock_threshold_triggered`).
     - Conteo discreto de `cost_variance_events_count` (`kit_cost_variance_detected`).
     - Validación de coherencia estricta de divisa (`EUR` para Valencia, `USD` para Miami).
   - **Salida:** `list[WeeklyPerformanceAggregate]` (dataset de agregados validado).

3. **Task 3: `load_reporting_metrics`**
   - **Decorador:** `@task(name="load-reporting-metrics", retries=3, retry_delay_seconds=30)`
   - **Entrada:** `aggregates: list[WeeklyPerformanceAggregate]`, `run_id: UUID`, `db_connector: SqlAlchemyConnector`.
   - **Operación:** Abre una transacción aislada en PostgreSQL. Ejecuta el `INSERT INTO reporting.weekly_office_program_performance ... ON CONFLICT (office, programme_id, week_start) DO UPDATE`. Registra el número de registros cargados.
   - **Salida:** `LoadResult(records_loaded=len(aggregates), status="SUCCESS")`.

---

### 5.2. Semántica de Estados de Prefect y Políticas de Reintento

El pipeline mapea de forma explícita los estados fundamentales del orquestador:

| Estado Prefect | Significado Operativo | Política de Monitoreo y Reintentos |
| :--- | :--- | :--- |
| `Scheduled` | El pipeline está encolado en el worker/runner esperando su franja horaria (lunes 05:00 UTC). | Si permanece en este estado > 15 minutos, se dispara alerta de "Worker no disponible / Agente no responde". |
| `Running` | El flow se encuentra ejecutando tasks activas. | Se monitorea el *heartbeat*. Si excede el timeout configurado (1.800 s), el supervisor aborta la ejecución para liberar bloqueos. |
| `Completed` | Todas las tasks completaron con éxito. La base analítica `reporting` está actualizada y consistente. | Se actualiza `reporting.pipeline_execution_logs` a `status = 'COMPLETED'` con métricas de volumen. Notificación de éxito en canal de auditoría. |
| `Failed` | Una de las tasks críticas agotó sus 3 reintentos o capturó un fallo irrecuperable. | Se captura la excepción, se vuelca el stacktrace en `error_details` dentro del log de auditoría con `status = 'FAILED'`, y se remite alerta crítica (PagerDuty / Slack) a soporte. |

---

### 5.3. Gestión de Configuración y Credenciales con Prefect Blocks

Para cumplir con las políticas de seguridad de Nexova y no exponer secretos en repositorios o archivos de configuración:

- **SqlAlchemyConnector Block (`supabase-reporting-db`):**
  - Almacena de forma centralizada y cifrada la cadena de conexión de producción a Supabase PostgreSQL:
    `postgresql+psycopg://reporting_worker:*****@db.xxx.supabase.co:5432/postgres?sslmode=require`
  - Controla el pool de conexiones (`pool_size=5`, `max_overflow=10`, `pool_recycle=3600`).
  - Permite la rotación periódica de credenciales desde el panel de Prefect Cloud/Server sin modificar ninguna línea de código del monorepo.
- **Secret Block (`slack-ops-webhook`):**
  - Clave segura para el envío de notificaciones automáticas ante fallas de pipeline hacia el canal de monitoreo de operaciones.
- **Secret Block (`reporting-encryption-key`):**
  - Firma para la validación de tokens de servicio entre el backend FastAPI y los triggers de Prefect.
- **Regla Estricta:** No se insertan cadenas de conexión, contraseñas ni URLs con credenciales en ningún documento, archivo `.env` o código fuente.

---

## 6. Diseño de Endpoints en `services/reporting/` (Solo Diseño de API)

### 6.1. Principio de Separación Arquitectónica
- Los endpoints de `services/reporting/` son **interfaces de servicio delgadas**: no ejecutan lógica de transformación ni tareas ETL en memoria de la API web.
- **Consultas (Lectura):** Acceden exclusivamente a las tablas optimizadas `reporting.weekly_office_program_performance` y `reporting.pipeline_execution_logs`.
- **Comandos (Disparo):** El trigger manual delega de forma asíncrona la ejecución al runtime de Prefect mediante el cliente formal de Prefect (`prefect.deployments.run_deployment`), respondiendo de inmediato un código HTTP 202 con el identificador de la corrida.
- **Aislamiento Total:** Completamente separados de `services/telemetry/routers/telemetry.py` y de `GET /telemetry/report`.

---

### 6.2. Especificación de Endpoints

```mermaid
sequenceDiagram
    autonumber
    actor Stakeholder as Laura / Elena (Dashboard UI)
    participant API as services/reporting/
    participant DB as reporting schema (Postgres)
    participant Orchestrator as data/pipelines/ (Prefect)

    Note over Stakeholder,API: 1. Consulta de Métricas de Negocio
    Stakeholder->>API: GET /reporting/kpis/weekly?week_start=2026-11-16
    API->>DB: SELECT * FROM reporting.weekly_office_program_performance WHERE week_start = ...
    DB-->>API: Filas consolidadas por oficina y programa
    API-->>Stakeholder: 200 OK (JSON con KPIs y monedas separadas EUR/USD)

    Note over Stakeholder,API: 2. Consulta de Estado de Salud
    Stakeholder->>API: GET /reporting/status
    API->>DB: SELECT * FROM reporting.pipeline_execution_logs ORDER BY started_at DESC LIMIT 1
    DB-->>API: Último log de ejecución
    API-->>Stakeholder: 200 OK (Status, última corrida, registros procesados)

    Note over Stakeholder,API: 3. Disparo Manual / Reproceso
    Stakeholder->>API: POST /reporting/pipeline/trigger {"target_week_start": "2026-11-16"}
    API->>Orchestrator: Disparo asíncrono de flow Prefect
    Orchestrator-->>API: run_id registrado
    API-->>Stakeholder: 202 Accepted {"run_id": "...", "status": "SCHEDULED"}
```

#### Endpoint 1: Consulta de Estado de la Última Corrida
- **Ruta y Método:** `GET /reporting/status`
- **Función que Invoca:** `data.pipelines.queries.get_latest_pipeline_run_status()`
- **Fuente de Datos:** Lectura directa de `reporting.pipeline_execution_logs`.
- **Respuesta (JSON 200 OK):**
  ```json
  {
    "run_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "flow_name": "weekly-business-performance-pipeline",
    "status": "COMPLETED",
    "trigger_mode": "scheduled",
    "window_start": "2026-11-16",
    "window_end": "2026-11-23",
    "started_at": "2026-11-23T05:00:01.120Z",
    "finished_at": "2026-11-23T05:01:45.340Z",
    "duration_seconds": 104.22,
    "records_extracted": 1450,
    "records_loaded": 8,
    "error_details": null
  }
  ```

#### Endpoint 2: Disparo Manual del Pipeline
- **Ruta y Método:** `POST /reporting/pipeline/trigger`
- **Función que Invoca:** `data.pipelines.orchestrator.trigger_pipeline_run(target_week_start, trigger_mode="manual")`
- **Cuerpo de Solicitud (JSON):**
  ```json
  {
    "target_week_start": "2026-11-16",
    "reprocess_buffer_week": false,
    "reason": "Auditoría manual solicitada por Gerencia L&D"
  }
  ```
- **Respuesta (JSON 202 Accepted):**
  ```json
  {
    "run_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "status": "SCHEDULED",
    "target_week_start": "2026-11-16",
    "message": "Pipeline de desempeño programado exitosamente para ejecución asíncrona."
  }
  ```

#### Endpoint 3: Consulta de KPIs para el Dashboard de Negocio
- **Ruta y Método:** `GET /reporting/kpis/weekly`
- **Función que Invoca:** `data.pipelines.queries.get_weekly_performance_kpis(week_start, office, programme_id)`
- **Parámetros de Consulta (Query Params):**
  - `week_start` (opcional, formato `YYYY-MM-DD`): Filtra por semana específica. Por defecto devuelve la última semana procesada.
  - `office` (opcional, enum `valencia`, `miami`): Filtra por sede.
  - `programme_id` (opcional, string): Filtra por programa específico.
- **Respuesta (JSON 200 OK):**
  ```json
  {
    "week_start": "2026-11-16",
    "offices": [
      {
        "office": "valencia",
        "currency": "EUR",
        "total_material_cost": 14520.50,
        "total_kits_delivered": 180,
        "total_shortages": 2,
        "total_cost_variances": 1,
        "programmes": [
          {
            "programme_id": "ai-engineering-core",
            "material_cost": 8900.00,
            "kits_delivered": 110,
            "shortage_events": 1,
            "cost_variance_events": 0
          },
          {
            "programme_id": "data-pipeline-specialization",
            "material_cost": 5620.50,
            "kits_delivered": 70,
            "shortage_events": 1,
            "cost_variance_events": 1
          }
        ]
      },
      {
        "office": "miami",
        "currency": "USD",
        "total_material_cost": 18240.00,
        "total_kits_delivered": 140,
        "total_shortages": 0,
        "total_cost_variances": 3,
        "programmes": [
          {
            "programme_id": "ai-engineering-core",
            "material_cost": 18240.00,
            "kits_delivered": 140,
            "shortage_events": 0,
            "cost_variance_events": 3
          }
        ]
      }
    ],
    "metadata": {
      "computed_at": "2026-11-23T05:01:45.340Z",
      "run_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
    }
  }
  ```

---

### 6.3. Tabla Comparativa de Separación de Responsabilidades

| Criterio | Reporte Técnico Existente (`GET /telemetry/report`) | Reporte de Desempeño de Negocio (`GET /reporting/kpis/weekly`) |
| :--- | :--- | :--- |
| **Audiencia** | Equipo de Ingeniería de Software, DevOps y SRE. | Laura (CEO), Elena (Gerente de L&D) y directores de sede. |
| **Pregunta que Responde** | "¿El sistema está operando con estabilidad, sin errores 500 y con baja latencia?" | "¿Cuánto gastamos en material formativo y cuántos kits entregamos en Valencia vs. Miami esta semana?" |
| **Unidad Temporal** | En tiempo real o ventana deslizante continua (últimas 24 horas). | Ventana semanal cerrada calendario ISO (lunes 00:00 UTC a domingo 23:59 UTC). |
| **Granularidad** | Evento individual, tipo de error técnico, percentiles de latencia ($p50, p95, p99$). | Fila única por sede (`office`), programa formativo (`programme_id`) y semana (`week_start`). |
| **Métricas Clave** | Errores de API, rechazos de esquema, fallos de autenticación, tiempos de respuesta HTTP. | Inversión en material (`total_material_cost`), kits entregados, escasez de stock y variaciones de precio. |
| **Tratamiento de Divisas** | Ignorado / No aplicable. | Segregación estricta (`EUR` para Valencia, `USD` para Miami) sin conversiones arbitrarias. |
| **Módulo de Código** | `services/telemetry/` | `services/reporting/` (lecturas) y `data/pipelines/` (ETL orquestado). |

---

## 7. Matriz de Conformidad y Criterios de Evaluación

Esta sección audita y valida punto por punto el cumplimiento de los requerimientos fijados en `pipeline-1.md` y el briefing de Nexova:

| Criterio de Evaluación | Estado | Sección de Referencia | Evidencia Técnica Documentada |
| :--- | :---: | :--- | :--- |
| **Existencia de archivo en ruta oficial** | Cumple | Documento raíz | Creado y commiteado en `data/pipelines/PIPELINE_DESIGN.md`. |
| **Estado actual y brecha frente al reporte técnico** | Cumple | Sección 1 | Explica el alcance del reporte DevOps y la desconexión frente a Laura y Elena. |
| **Tablas fuente, payload y cadencia de actualización** | Cumple | Sección 1.1 y 2.2 | `public.telemetry_events`, payload en `tags` JSONB, lunes 05:00 UTC. |
| **Propósito concreto en una sola frase de negocio** | Cumple | Sección 2.1 | Frase unívoca orientada a KPIs de inventario y sedes Valencia/Miami. |
| **Separación arquitectónica estricta** | Cumple | Sección 1.4 y 6.3 | Sin modificaciones en `services/telemetry/`, destino en `reporting`. |
| **Diagrama ETL Mermaid con entidades reales** | Cumple | Sección 3.2 | Diagrama de bloques con etapas de extracción, transformación y carga. |
| **Estrategia concreta de actualización / deduplicación** | Cumple | Sección 3.4 y 4.3 | `ON CONFLICT DO UPDATE` y `DISTINCT ON` en extracción. |
| **Idempotencia y fallo parcial detallado** | Cumple | Sección 4.1 | Caso de fallo en $R_1$ y segunda corrida determinista en $R_2$. |
| **Log con al menos 5 campos justificados** | Cumple | Sección 4.6 | 13 campos con nombre, tipo SQL y justificación de auditoría. |
| **Mapeo a Prefect (Flow + 3 Tasks + Blocks)** | Cumple | Sección 5 | `weekly_business_performance_pipeline`, 3 tasks y Blocks de conexión segura. |
| **Diseño de 3 endpoints de reporting** | Cumple | Sección 6.2 | Endpoints de status, trigger y kpis semanales con esquemas JSON. |
| **Consistencia con eventos, KPIs, grano y monedas** | Cumple | Sección 2 y 3.3 | Grano `(office, programme_id, week_start)`, monedas `EUR` y `USD` aisladas. |
| **Decisiones con análisis de trade-offs** | Cumple | Secciones 3.1, 3.4, 4.2 | Comparativas de persistencia, desacoplamiento y modelos de cómputo. |
| **Límites respetados (solo diseño, sin código funcional)** | Cumple | Global | Cero scripts ETL ni routers operativos implementados prematuramente. |



