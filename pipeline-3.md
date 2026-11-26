# Hito — Mejora del Pipeline: Subflows y Tests (Parte 3 de 3)

> Guía del proyecto recopilada y adaptada del README oficial de 4Geeks al contexto Nexova y al monorepo de Luis. Este hito amplía la Parte 2: no rehagas el pipeline desde cero; refactorízalo y conserva su funcionalidad.
>
> **Fuentes**
> - [README oficial del hito (español)](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-data-pipeline-enhancement/README.es.md)
> - [BRIEFING Nexova para Data Pipelines](https://github.com/4GeeksAcademy/ai-engineering-syllabus/tree/main/content/contexts/06-telemetry-data-pipelines/data-pipelines)
> - [Parte 1 — diseño](https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo-luis/blob/docs/data-pipeline-design/pipeline-1.md)
> - [Parte 2 — implementación resiliente](https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo-luis/blob/docs/data-pipeline-design/pipeline-2.md)

## Antes de empezar

- Este proyecto parte de la **Parte 2 completa**: `data/pipelines/pipeline.py` funcional, endpoints en `services/reporting/` y `data/pipelines/PIPELINE_DESIGN.md`.
- Revisa el BRIEFING: es la fuente de verdad para nombres/cálculo de KPIs, esquema de destino, audiencia y contrato de consulta.
- Usa la estructura existente: flows en `data/pipelines/`, transformación reutilizable en `data/process/`, tests en `tests/pipelines/` y dashboard en `uis/backoffice/`.
- Instala/usa Prefect 3 según las dependencias existentes (`uv add "prefect>=3"` si aún falta).
- Tras cambios en una rama, el flujo previsto de entrega oficial incluye PR y merge aprobado a `main` antes de basar trabajo posterior en esa rama.

## Objetivo y alcance Nexova

Refactorizar el pipeline semanal de desempeño de negocio para que sus etapas sean subflows reutilizables, cubrir las transformaciones con tests unitarios aislados, mantener la ejecución CLI existente y exponer los KPIs en un dashboard accesible para negocio.

Se conserva el contrato de la Parte 2: fuente de solo lectura `telemetry_events`; destino `reporting.weekly_office_program_performance`; agregado semanal por `office`, `programme_id` y `week_start` (lunes UTC); oficinas Valencia y Miami; monedas separadas EUR/USD. KPIs:

| KPI | Evento fuente | Definición |
|---|---|---|
| Costo de material por oficina/programa | `inbound_order_created` | Suma del campo de costo definido en el esquema/BRIEFING; no sumar `unit_cost` y `total_cost` dos veces. |
| Kits entregados | `outbound_order_created` | Conteo de eventos únicos. |
| Frecuencia de escasez | `stock_threshold_triggered` | Conteo de eventos únicos. |
| Frecuencia de variación de costo | `kit_cost_variance_detected` | Conteo de eventos únicos. |

No cambiar los KPIs, granularidad, moneda, tabla ni contrato establecidos en el BRIEFING y `PIPELINE_DESIGN.md`. Mantener intactos `telemetry_events`, `services/telemetry/analysis.py` y `GET /telemetry/report`.

## Qué debes hacer

### 1. Refactorizar en subflows Prefect

- El flow principal de `data/pipelines/pipeline.py` debe coordinar **al menos tres subflows** (`@flow`), uno por etapa:
  1. Extracción de eventos desde `telemetry_events` (y solo otras fuentes explícitamente necesarias según el diseño aprobado), en modo solo lectura.
  2. Transformación, validación, deduplicación y agregación semanal de los cuatro KPIs Nexova.
  3. Carga idempotente a `reporting.weekly_office_program_performance`.
- El flow principal coordina las fases en orden; no debe contener toda su lógica interna.
- Cada subflow debe poder ejecutarse por separado, con parámetros de entrada y resultado de salida explícitos. No compartir estado mediante variables globales.
- Los nombres de subflows, tasks y datos deben reflejar el dominio Nexova y alinearse con `PIPELINE_DESIGN.md`/BRIEFING; evitar etiquetas vagas si pueden nombrarse con precisión.
- Si existen notificaciones, exportaciones u otros pasos opcionales, se pueden separar como subflow. Invocarlos con `return_state=True`, registrar su fallo y permitir que el flujo crítico continúe.
- Preservar resiliencia de Parte 2: reintentos justificados para servicios externos, caché válida y no obsoleta, manejo explícito de errores, idempotencia por clave `(office, programme_id, week_start)` y metadatos de corrida. No introducir regresiones en el contrato.

### 2. Tests unitarios de transformación

Crear `tests/pipelines/test_pipeline.py` con tests para **al menos tres tasks de transformación** relacionadas con los KPIs del BRIEFING.

- Probar cada task aislada, usando eventos sintéticos/in-memory con la forma del esquema real.
- No depender de base de datos, APIs externas, credenciales ni red.
- Incluir un caso defensivo para input inválido/malformado (por ejemplo, dimensión obligatoria nula, tipo de costo incorrecto o estructura de evento ausente) y comprobar el comportamiento esperado: validación/rechazo controlado, sin producir agregados silenciosamente incorrectos.
- Incluir un caso con resultado esperado calculable a mano que valide al menos un KPI frente a su definición oficial.
- Considerar también duplicados por identificador estable del evento y asegurar que no inflen los conteos/sumas.
- Ejecutar: `python -m pytest tests/pipelines/test_pipeline.py`.

### 3. Mantener el CLI

- Conservar el entrypoint `if __name__ == "__main__"` existente en `data/pipelines/pipeline.py`.
- Tras el refactor, `python data/pipelines/pipeline.py` debe seguir invocando el ETL completo, coordinado por el flow principal, sin reconstruir el CLI de cero.
- Mantener documentada en `data/pipelines/PIPELINE_DESIGN.md` la frecuencia semanal prevista y el comando CLI.
- No incluir secretos en código, tests, documentación o commits.

### 4. Dashboard de negocio (obligatorio)

Construir una página funcional bajo `uis/backoffice/` (por ejemplo, ruta `/reporting`) para stakeholders de negocio, alimentada con datos reales desde el endpoint de consulta de KPIs de `services/reporting/` de la Parte 2.

- Mostrar los cuatro KPIs Nexova: costo de material, kits entregados, frecuencia de escasez y frecuencia de variación de costo.
- Usar etiquetas legibles y coherentes con el BRIEFING; mostrar el período cubierto (`week_start`) y la oficina/programa correspondiente.
- Diferenciar explícitamente EUR y USD, sin conversión ni suma entre monedas.
- Una tabla o visualización clara por KPI es suficiente; no se exige pulido visual avanzado.
- Gestionar estados de carga, respuesta vacía y error de API de forma comprensible. No usar datos simulados como si fueran resultados reales.
- No duplicar la lógica ETL en el frontend: consumir el endpoint de `services/reporting/`.

### 5. Mejoras opcionales identificadas en Parte 1

Revisa las preguntas de diseño de `data/pipelines/PIPELINE_DESIGN.md`. Solo si allí se señaló una mejora concreta pendiente (por ejemplo, alerta por ausencia de corridas, lock de concurrencia o clave de idempotencia), puedes implementarla. Documenta en `PIPELINE_DESIGN.md` qué pregunta responde y por qué se priorizó. No inventar alcance adicional para marcar esta sección.

## Qué vamos a evaluar

- [ ] El flow principal de `data/pipelines/pipeline.py` invoca al menos tres subflows (`@flow`) — extracción, transformación y carga — en lugar de concentrar toda la lógica.
- [ ] Cada subflow tiene inputs/outputs explícitos y puede ejecutarse independientemente, sin depender de variables globales.
- [ ] Los nombres y responsabilidades reflejan el vocabulario Nexova y los KPIs del BRIEFING.
- [ ] Existe `tests/pipelines/test_pipeline.py` con al menos tres tests unitarios de tasks de transformación.
- [ ] Los tests son realmente aislados: fixtures in-memory, sin base de datos viva ni APIs externas.
- [ ] Hay al menos un test de validación defensiva para datos inválidos/malformados.
- [ ] Hay al menos un test que contrasta un valor de KPI calculado a mano con la definición del BRIEFING.
- [ ] Los duplicados/eventos repetidos no inflan métricas según el identificador estable del esquema.
- [ ] `python -m pytest tests/pipelines/test_pipeline.py` pasa.
- [ ] `python data/pipelines/pipeline.py` sigue ejecutando el flujo ETL completo y se conserva el entrypoint CLI de Parte 2.
- [ ] Se mantiene idempotencia de la carga y el contrato de tabla/granularidad, sin alterar los KPIs ni la separación EUR/USD.
- [ ] `telemetry_events`, `services/telemetry/analysis.py` y `GET /telemetry/report` permanecen intactos.
- [ ] Existe un dashboard bajo `uis/backoffice/` que consume el endpoint de KPIs de `services/reporting/` y muestra los cuatro indicadores y el período.
- [ ] El dashboard es legible para stakeholders no técnicos, diferencia oficinas/programas y monedas, y maneja carga, vacío y error.

## Entrega

1. Commits de `data/pipelines/pipeline.py`, tests y dashboard bajo `uis/backoffice/`, más los cambios pertinentes a `data/pipelines/PIPELINE_DESIGN.md` si se documentan mejoras opcionales.
2. Ejecuta y comprueba:
   - `python -m pytest tests/pipelines/test_pipeline.py`
   - `python data/pipelines/pipeline.py` (con configuración de entorno válida; no exponer secretos en logs o entrega).
3. Mensaje de commit oficial: `feat: refactor business performance pipeline into subflows, add unit tests, and add reporting dashboard`.
4. Abre PR en la copia personal del monorepo, comparte su URL con el tech lead y espera aprobación antes de hacer merge a `main`.

---

**Nota de auditoría:** se consultó el README oficial Parte 3 en `ai-eng-milestone-data-pipeline-enhancement/README.es.md`. La ruta oficial pide expresamente al menos tres subflows, tests aislados para transformaciones, conservación del CLI y dashboard obligatorio. El token disponible en `.env` fue rechazado por la API de 4Geeks con HTTP 401 (`Invalid or Inactive Token`); por tanto, el contenido se obtuvo del README público oficial, no de la sesión autenticada de la cuenta.