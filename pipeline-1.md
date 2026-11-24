# Hito — Diseño de un Pipeline de Desempeño de Negocio (Parte 1 de 3)

> Instrucciones del proyecto recopiladas del README oficial de 4Geeks. Este archivo resume qué debes hacer y qué se evaluará, adaptándolo al contexto Nexova del `CONTEXT.md` del monorepo.
>
> Fuentes oficiales:
> - [README del hito (español)](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-data-pipeline-design/README.es.md)
> - [BRIEFING Nexova para Data Pipelines](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/06-telemetry-data-pipelines/data-pipelines/nexova-BRIEFING.es.md)

## Objetivo

Diseñar —sin implementar todavía el código de orquestación— un pipeline de datos nuevo que convierta la telemetría existente en cifras de desempeño de negocio para stakeholders no técnicos. El documento de diseño que pide el README oficial es `data/pipelines/PIPELINE_DESIGN.md` y debe quedar commiteado en este monorepo.

El pipeline es adicional al reporte técnico existente: `telemetry_events` es fuente de lectura, nunca destino. No se debe modificar `services/telemetry/analysis.py` ni `GET /telemetry/report`. Cualquier campo aditivo requerido en el payload de eventos obligatorios es una extensión permitida de captura, no una reescritura del reporte.

## Contexto Nexova: necesidad de negocio y KPIs

Según el BRIEFING Nexova, Laura (CEO) y Elena (Gerente de L&D) necesitan un **Reporte Semanal de Desempeño por Oficina y Programa**, listo el lunes por la mañana, que compare inversión y entrega de material de formación entre Valencia y Miami.

El diseño debe calcular y poder auditar estos KPIs:

1. **Costo de material por oficina/programa:** suma de los costos de `inbound_order_created` durante la semana.
2. **Kits entregados:** conteo de `outbound_order_created`.
3. **Frecuencia de escasez:** conteo de `stock_threshold_triggered`.
4. **Frecuencia de variación de costo:** conteo de `kit_cost_variance_detected`.

Eventos fuente obligatorios en `telemetry_events`:

- `inbound_order_created` → costo de material. Nexova requiere que el evento tenga costo (`unit_cost` o `total_cost` en `properties`); si el esquema actual no lo tiene, proponer agregarlo de forma aditiva.
- `outbound_order_created` → kits entregados.
- `stock_threshold_triggered` → eventos de escasez.
- `kit_cost_variance_detected` → variaciones anómalas de costo.

Grano de agregación: una fila por `office` (`valencia` o `miami`), `programme_id` y semana ISO (`week_start`, lunes en UTC). Mantener las monedas separadas (EUR para Valencia, USD para Miami); no convertir ni sumar monedas en este hito.

Destino exacto especificado por el BRIEFING: `reporting.weekly_office_program_performance`, con unicidad por `(office, programme_id, week_start)`. Campos de KPI: `total_material_cost`, `kits_delivered_count`, `shortage_events_count`, `cost_variance_events_count`, `currency`, además de dimensiones y `computed_at`.

## Qué debes hacer

### 1. Analizar el estado actual

- Documentar una sección **Estado Actual** en `data/pipelines/PIPELINE_DESIGN.md`.
- Describir los eventos de telemetría ya capturados, dónde se almacenan y qué responde el reporte técnico actual para ingeniería.
- Identificar la brecha: el reporte técnico (volumen de eventos, errores, latencia) no ofrece el consolidado semanal de inversión/entrega de material por oficina y programa que necesitan Laura y Elena.
- Aclarar cómo el pipeline nuevo responde esa pregunta de negocio sin reemplazar el reporte técnico.

### 2. Diseñar el pipeline

- Definir el propósito en una sola frase concreta que nombre el reporte semanal, audiencia/cadencia, KPIs y eventos obligatorios que los alimentan.
- Especificar fuentes y formato de extracción: `telemetry_events`, forma del envelope/payload y frecuencia de actualización; mencionar tablas de dominio adicionales únicamente si el contexto real las exige.
- Incluir un diagrama Mermaid o de texto con etapas separadas de extracción, transformación y carga, usando entidades y nombres reales de Nexova.
- Explicar cómo se manejan registros actualizados en lugar de insertados: estrategia concreta de deduplicación/upsert y claves relevantes.
- Usar como destino `reporting.weekly_office_program_performance` (nombre exacto), con esquema dedicado `reporting`; no escribir agregados a `telemetry_events`.
- Diseñar el acceso desde un módulo nuevo `services/reporting/`, separado de `services/telemetry/`.

### 3. Definir resiliencia, idempotencia y auditoría

- Explicar exactamente qué sucede si la carga falla parcialmente y se reintenta: cómo evitar duplicados y corrupción usando la clave única `(office, programme_id, week_start)` y upsert/recalculo de la partición semanal.
- Cubrir eventos tardíos mediante recálculo de la ventana semanal afectada, manteniendo trazabilidad de la corrida que la recalcula.
- Especificar un log de ejecución con al menos cinco campos, cada uno con nombre, tipo y motivo; incluir como mínimo inicio/fin, estado, conteos procesados y error. Considerar `run_id`, checkpoint/fase y ventana procesada para observabilidad y recuperación.
- Describir observabilidad y recuperabilidad: cómo distinguir actividad cero de una falla de captura o de un pipeline que no corrió; cómo retomar tras una caída de base de datos; cómo trazar eventos y corrida.
- Considerar duplicados de origen y transmisión reintentada, corridas concurrentes (programada y manual) y control de solapamiento.

### 4. Mapear el diseño a Prefect

- Identificar un flow principal con nombre y al menos tres tasks concretas: extracción, transformación y carga.
- Indicar estados relevantes: `Running`, `Completed` y `Failed`, y qué significan para monitoreo/reintentos.
- Describir qué configuración/credenciales se gestionarían mediante Prefect Blocks (por ejemplo, conexión segura a Supabase; no poner secretos en el documento).
- La Parte 1 no requiere subflows: estos se profundizan en la Parte 3.

### 5. Diseñar endpoints (solo diseño)

Esbozar en `services/reporting/` los tres endpoints de negocio y para cada uno indicar qué flow/función de `data/pipelines/` llamaría:

- Consulta de estado de la última corrida.
- Disparo manual del pipeline.
- Consulta de KPIs para el dashboard futuro, filtrable por semana y con la salida por oficina/programa.

Toda lógica ETL permanece en `data/pipelines/`; los endpoints no deben contenerla. Mantener estos endpoints separados del reporte de telemetría y de `GET /telemetry/report`.

## Qué vamos a evaluar

- [ ] Existe `data/pipelines/PIPELINE_DESIGN.md`, legible y en Markdown, commiteado en el monorepo.
- [ ] Incluye **Estado Actual** y explica claramente la brecha de negocio frente al reporte técnico.
- [ ] Especifica tablas/eventos fuente, forma del payload y cadencia de actualización.
- [ ] El propósito es una frase concreta con el entregable y KPIs del BRIEFING Nexova; no KPIs genéricos/técnicos.
- [ ] Respeta la separación: no modificar `services/telemetry/analysis.py` ni `GET /telemetry/report`; no usar `telemetry_events` como destino; nuevos resultados en tablas `reporting` y exposición por `services/reporting/`.
- [ ] El diagrama muestra claramente extracción, transformación y carga con nombres reales de entidades/tablas.
- [ ] La estrategia de actualizaciones/deduplicación describe un mecanismo concreto, no una intención genérica.
- [ ] La idempotencia detalla el escenario de fallo parcial y la segunda corrida.
- [ ] El log especifica al menos cinco campos con tipo y justificación de auditoría.
- [ ] Mapea un flow Prefect y al menos tres tasks con nombres concretos, además de estados y Blocks pertinentes.
- [ ] Define los tres endpoints en `services/reporting/` (estado, ejecución manual y KPIs) e indica qué funciones/flows importan.
- [ ] Es consistente con los eventos, KPIs, dimensiones, grano, tabla exacta y monedas descritos por el BRIEFING de Nexova.
- [ ] Las decisiones explican sus trade-offs; no basta con enumerar tecnologías o buenas prácticas.

## Límites y entrega

- **Esta parte es diseño, no implementación:** no escribir todavía código de orquestación, scripts ETL ni endpoints funcionales.
- No ampliar el alcance con eventos o KPIs que el BRIEFING no exige.
- Entrega principal: `data/pipelines/PIPELINE_DESIGN.md` en el monorepo.
- Mensaje de commit requerido: `feat: add business performance pipeline design document`.
- Subir los cambios a la copia del monorepo y compartir la URL de GitHub con el tech lead.
