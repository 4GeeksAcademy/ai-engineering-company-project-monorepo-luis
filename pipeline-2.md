# Hito — Pipeline de Desempeño de Negocio Resiliente (Parte 2 de 3)

> Guía de trabajo resumida y adaptada del README oficial de 4Geeks y del diseño de Nexova de la Parte 1. Esta parte implementa el diseño aprobado; no reemplaza la telemetría técnica.
>
> Fuentes oficiales:
> - [README del hito (español)](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-data-pipeline-build/README.es.md)
> - [BRIEFING Nexova para Data Pipelines](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/06-telemetry-data-pipelines/data-pipelines/nexova-BRIEFING.es.md)
> - [Diseño de la Parte 1 en este repo](https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo-luis/blob/docs/data-pipeline-design/pipeline-1.md)

## Objetivo

Implementar el pipeline de `data/pipelines/PIPELINE_DESIGN.md` para que lea eventos de `telemetry_events` y genere los KPIs de negocio semanales de Nexova en `reporting.weekly_office_program_performance`, con resiliencia ante fallos parciales, reintentos, ejecución CLI e interfaces separadas en `services/reporting/`.

## Contrato de negocio Nexova

**Audiencia:** Laura (CEO) y Elena (Gerente de L&D). **Entrega:** reporte semanal, actualizado el lunes por la mañana, por oficina y programa.

| KPI | Evento fuente | Cálculo |
|---|---|---|
| Costo de material por oficina/programa | `inbound_order_created` | Suma de `unit_cost` o `total_cost` en `properties` durante la semana. Validar cuál campo representa el importe agregado para evitar sumar dos veces. |
| Kits entregados | `outbound_order_created` | Conteo de eventos únicos. |
| Frecuencia de escasez | `stock_threshold_triggered` | Conteo de eventos únicos. |
| Frecuencia de variación de costo | `kit_cost_variance_detected` | Conteo de eventos únicos. |

Grano: una fila por `office` (`valencia` o `miami`), `programme_id` y semana ISO (`week_start`, lunes UTC). Monedas sin conversión: EUR en Valencia, USD en Miami. Destino exacto: `reporting.weekly_office_program_performance`, con unicidad `(office, programme_id, week_start)` y campos `total_material_cost`, `kits_delivered_count`, `shortage_events_count`, `cost_variance_events_count`, `currency` y `computed_at`.

## Qué debes hacer

### 1. Implementar flows y tasks Prefect

- Crear `data/pipelines/pipeline.py` con un flow principal que coordine al menos tres tasks independientes, con entradas y salidas explícitas:
  - extracción de los cuatro tipos de eventos desde `telemetry_events` en modo solo lectura;
  - transformación/validación y agregación semanal por oficina y programa;
  - carga idempotente a `reporting.weekly_office_program_performance`.
- Mantener nombres de funciones, campos y entidades alineados con `PIPELINE_DESIGN.md` y el BRIEFING Nexova.
- Incluir al menos un paso opcional/no crítico (por ejemplo, notificación o snapshot de validación) invocado con `return_state=True`; si falla, registrar el fallo y permitir que el ETL principal continúe.
- Configurar `retries` y `retry_delay_seconds` en cada task que llame servicios externos (base de datos/API). Justificar en comentarios el número y la demora elegidos; no reintentar errores permanentes de validación como si fueran fallos transitorios.
- Configurar caché en al menos una transformación con `cache_key_fn` y `cache_expiration`; la clave debe incorporar ventana y versión/identidad de los datos de entrada para no reutilizar resultados obsoletos.
- Manejar explícitamente al menos un fallo con `return_state=True`, distinguiendo pasos críticos (extracción/carga: abortar o marcar corrida fallida) de pasos secundarios opcionales (registrar y continuar).

### 2. Idempotencia, auditoría y recuperación

- Deduplicar eventos por el identificador estable del envelope (`eventId` si ese es el nombre real del esquema); la recepción repetida del mismo evento no debe inflar métricas. Si la captura aún no impone unicidad, señalar/implementar el upsert por ID en la capa de ingesta sin cambiar el endpoint de reporte técnico.
- La carga debe apoyarse en la clave única `(office, programme_id, week_start)` y usar upsert/reemplazo determinista de agregados. Si una corrida carga algunas filas y cae, reejecutar la ventana completa debe dejar exactamente los valores de una corrida limpia, nunca duplicarlos.
- Recalcular semanas afectadas por eventos tardíos, preservando `run_id` y ventana para rastrear qué corrida corrigió el agregado.
- Registrar por corrida, como mínimo: `run_id`, `started_at`, `finished_at`, `status`, `source_rows_read`, `rows_written`, `window_start`/`window_end`, `phase` o checkpoint y `error_message`. Conservar timestamps UTC y counts para distinguir cero actividad de extracción vacía/fallida o pipeline no ejecutado.
- Ante caída de base de datos, persistir estado/checkpoint de fase y reintentar operaciones transitorias; tras agotar reintentos marcar `Failed` con error y permitir relanzar la ventana de forma idempotente.
- Evitar carreras entre horario y disparo manual mediante lock por ventana (o mecanismo equivalente) y `run_id` distinto por intento; documentar cómo se libera/vence un lock abandonado.

### 3. Ejecución desde CLI

- Mantener un entrypoint `if __name__ == "__main__"` que invoque el flow completo desde `data/pipelines/pipeline.py`.
- Documentar el comando `python data/pipelines/pipeline.py` y la frecuencia semanal prevista (lunes por la mañana). Configuración sensible por variables de entorno/Prefect Blocks; nunca incluir secretos en código, documentos o commits.
- Verificar con Prefect 3 instalado (`uv add "prefect>=3"` según el README oficial), respetando las convenciones y dependencias ya presentes en el repo.

### 4. Endpoints de reporting

En un módulo nuevo `services/reporting/`, separado del módulo de telemetría, implementar tres endpoints, siguiendo autenticación y formato de respuesta existentes:

1. `GET /reporting/pipeline-runs/latest`: devuelve estado y metadata de la última corrida (`run_id`, inicio/fin, conteos, ventana, error si aplica).
2. `POST /reporting/pipeline-runs`: dispara el flow manualmente; no duplica ETL dentro del endpoint y responde con identificador/estado de la corrida.
3. `GET /reporting/weekly-office-program-performance?week_start=YYYY-MM-DD`: devuelve filas de KPIs para la semana solicitada o, por defecto, la última semana calculada; contrato de respuesta Nexova:

```json
{
  "week_start": "2026-07-13",
  "entries": [
    {
      "office": "valencia",
      "programme_id": "b2b-sales",
      "total_material_cost": 1240.50,
      "kits_delivered_count": 18,
      "shortage_events_count": 1,
      "cost_variance_events_count": 0,
      "currency": "EUR"
    }
  ]
}
```

Las rutas llaman/importan funciones de `data/pipelines/` para orquestación/consulta según corresponda. No colocar lógica ETL en `services/`.

## Límites

- No modificar `services/telemetry/analysis.py`, `GET /telemetry/report` ni usar `telemetry_events` como destino. Solo lectura de telemetría.
- No mezclar EUR y USD ni introducir KPIs/eventos fuera del alcance Nexova.
- Respetar `data/pipelines/PIPELINE_DESIGN.md` como especificación aprobada; si hay discrepancias, corregir diseño/código para mantener consistencia.
- La Parte 2 implementa flows/tasks; la extracción en subflows, tests de transformación y dashboard corresponden a la Parte 3.

## Qué vamos a evaluar

- [ ] Existe `data/pipelines/pipeline.py` y contiene al menos un flow con tres o más tasks.
- [ ] Las tasks de extracción, transformación y carga son independientes y tienen inputs/outputs explícitos.
- [ ] Una task opcional usa `return_state=True`; su fallo se registra y no interrumpe el camino crítico.
- [ ] Al menos una task maneja explícitamente un fallo mediante `return_state=True`.
- [ ] Las tasks con servicios externos tienen `retries > 0` y `retry_delay_seconds`, con comentario que justifica la política.
- [ ] Una task de transformación define `cache_key_fn` y `cache_expiration`, con clave ligada a ventana/datos para evitar resultados obsoletos.
- [ ] Correr dos veces el mismo rango deja resultados idénticos y sin duplicados, apoyándose en la clave única `(office, programme_id, week_start)`.
- [ ] Duplicados/reintentos de transmisión no cuentan un evento dos veces; eventos tardíos producen recálculo trazable de la semana correspondiente.
- [ ] Cada corrida registra metadata estructurada de inicio, fin, estado, conteos y errores, más identificador/ventana/checkpoint suficiente para auditoría y recuperación.
- [ ] `python data/pipelines/pipeline.py` ejecuta el ETL completo desde CLI.
- [ ] La carga escribe en `reporting.weekly_office_program_performance`; `telemetry_events` y `services/telemetry/analysis.py` permanecen intactos.
- [ ] Existe endpoint de última corrida en `services/reporting/` con metadata de estado.
- [ ] Existe endpoint de disparo manual que delega al flow sin duplicar ETL.
- [ ] Existe endpoint de consulta de KPIs por semana y su respuesta coincide con el contrato del BRIEFING Nexova.
- [ ] Los cuatro KPIs, granularidad, oficinas, programas y monedas coinciden con el BRIEFING; no se suman monedas ni se añaden métricas ajenas.
- [ ] `data/pipelines/PIPELINE_DESIGN.md` y la implementación son consistentes; no se altera el reporte técnico.

## Entrega

1. Commit de implementación con el mensaje requerido: `feat: implement resilient business performance pipeline`.
2. Subir los cambios a la copia personal del monorepo y compartir el enlace con el tech lead.
3. La guía oficial señala que esta entrega implementa el diseño de Parte 1; para la Parte 3 se reutilizará `pipeline.py` y se añadirá el refactor en subflows, tests y dashboard.
