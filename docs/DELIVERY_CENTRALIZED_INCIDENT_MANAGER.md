# Nexova — Gestor de Incidencias Centralizado: Informe de Entrega y Documentación

Este documento certifica y documenta la implementación completa del proyecto **Centralized Incident Manager / Gestor de Incidencias Centralizado** en el monorepo de Nexova, cumpliendo al 100% con los criterios de evaluación de 4Geeks Academy y las especificaciones exactas del briefing de Nexova.

---

## 1. Arquitectura y Componentes Desarrollados

El desarrollo amplía la plataforma existente del monorepo sin romper ninguna funcionalidad previa:

1. **Modelos de Dominio y Validaciones (`services/api/incident_models.py`)**:
   - Definición de enums estrictos:
     - `IncidentStatus`: `open`, `in_progress`, `resolved`, `discarded`.
     - `IncidentOrigin`: `customer`, `branch`, `internal`.
     - `IncidentBranch`: `central` (Central — Sede Valencia), `valencia_operations` (Valencia — Operaciones), `miami_office` (Miami Office), `remote` (Remoto). *Se rechaza el valor `headquarters` conforme al briefing*.
     - `IncidentCategory`: `technical_failure`, `process_error`, `client_complaint`, `candidate_issue`, `staff_issue`, `sla_breach`, `data_quality`, `other`.
   - Reglas de transición de ciclo de vida (`validate_status_transition`):
     - Transiciones permitidas: `open → in_progress`, `open → discarded`, `in_progress → resolved`, `in_progress → discarded`.
     - Estados terminales: `resolved` y `discarded` son finales.
     - Cualquier otra transición es rechazada con HTTP `400`.
   - Modelos Pydantic V2 (`IncidentCreate`, `IncidentStatusUpdate`, `IncidentRecord`, `IncidentSummary`) con validación de cadenas en blanco y configuración `extra="forbid"`.

2. **Capa de Almacenamiento Persistente (`services/api/incident_storage.py`)**:
   - Persistencia local en TinyDB (`data/incidents.json`), configurable mediante la variable de entorno `NEXOVA_INCIDENTS_DB_PATH`.
   - Control de concurrencia seguro mediante `threading.RLock`.

3. **Script de Seed Histórico Idempotente (`scripts/seed_incidents.py`)**:
   - Importa el dataset histórico de `data/raw/incidents-nexova.csv`.
   - Reutiliza el validador oficial `validate_row` de `packages.incident_analyzer.validator`.
   - Mapeos exactos aplicados:
     - Estado: `OPEN → open`, `CLOSED → resolved`, `DISCARDED → discarded`.
     - Categoría: `TECHNICAL` y `ACCESS → technical_failure`, `BILLING` y `HR_QUERY → process_error`, `COMPLAINT → client_complaint`.
     - Sede fija: `branch = "central"`.
     - Origen fijo: `origin = "customer"`.
     - Título: primeros 120 caracteres de `description` recortados.
     - Fecha: parseo a medianoche UTC (`YYYY-MM-DDT00:00:00Z`).
   - Idempotencia garantizada por `ticket_id` (mediante tabla de seguimiento `_seed_history`) sin almacenar `ticket_id` ni PII en la colección de incidencias.

4. **API Backend FastAPI (`services/api/routers/incidents.py` & `main.py`)**:
   - `POST /api/incidents`: Creación con respuesta `201 Created` o `400 Bad Request` en caso de validación fallida.
   - `GET /api/incidents`: Listado con soporte para filtros combinables (`status`, `origin`, `branch`, `category`) y validación de parámetros (HTTP `400` ante valores desconocidos). Retorna `[]` si no hay registros.
   - `GET /api/incidents/{id}`: Detalle de incidencia por ID o `404 Not Found`.
   - `PATCH /api/incidents/{id}/status`: Actualización de estado auditada con validación de ciclo de vida (HTTP `400` ante transiciones inválidas o estados finales) y actualización de `updated_at`.
   - `GET /api/incidents/summary`: Agregados numéricos en tiempo real por estado, categoría, origen y sede. Soporta base vacía retornando ceros.
   - Manejo seguro de errores: Validación JSON clara con campo afectado (`400`); excepciones no controladas devuelven `500` con mensaje genérico sin filtrar stack traces.
   - Endpoints heredados del analizador (`/api/incidents/analyze` y `/api/incidents/results/export`) preservados con autenticación Bearer intacta.

5. **Panel Frontend Backoffice (`uis/backoffice/`)**:
   - Integrado en `uis/backoffice/index.html` bajo la navegación `#incidencias`.
   - Formulario de alta con validación previa en cliente, bloqueo de submit durante carga y **destaque visual automático de la sede cuando el origen sea `branch`**.
   - Listado reactivo con filtros combinados, estados de carga, vacío, error con botón para **reintentar**, y selectores de ciclo de vida con **rollback optimista** en caso de rechazo del servidor.
   - Panel de resumen de métricas operativas con tarjetas KPI y barras de desglose consumiendo `/api/incidents/summary`.
   - Sección del analizador CSV conservada en bloque plegable para mantener la herramienta previa de helpdesk.

---

## 2. Validación de Criterios de Aceptación

| Requisito | Estado | Evidencia |
|---|---|---|
| Modelo `Incident` con todos los campos y restricciones | Cumplido | `services/api/incident_models.py` |
| Seed histórico con 96 válidas y 4 omitidas | Cumplido | `services/api/tests/test_incident_seed.py` |
| Conteo post-seed: Open=27, Resolved=56, Discarded=13 | Cumplido | `test_seed_distribution_matches_briefing_exact_counts` |
| Conteo categorías: Tech=49, Process=35, Complaint=12 | Cumplido | Verificado contra `data/raw/incidents-nexova.csv` |
| Idempotencia del seed (segunda ejecución = 0 duplicados) | Cumplido | `test_seed_is_strictly_idempotent` |
| Sin almacenamiento ni fuga de PII (`ticket_id`, emails) | Cumplido | `test_no_pii_or_ticket_id_in_stored_records` |
| Endpoints REST con códigos HTTP correctos (201, 200, 400, 404, 500) | Cumplido | `services/api/tests/test_incidents_crud_api.py` |
| Validación de errores en formato JSON amigable (HTTP 400) | Cumplido | `sanitize_auth_validation_errors` en `main.py` |
| Transiciones inválidas o estados finales rechazados con 400 | Cumplido | `test_status_transitions_invalid_and_terminal` |
| `/summary` responde con datos y con base vacía | Cumplido | `test_summary_empty_database` y `test_summary_with_seed_data` |
| Destaque visual de sede en UI cuando `origin === 'branch'` | Cumplido | `uis/backoffice/incidents.js` y `incidents.css` |
| Rollback optimista en UI ante fallo de actualización | Cumplido | Implementado en `select-status-transition` listener |
| Tres capturas obligatorias para el PR | Cumplido | En `docs/screenshots/` generadas con Playwright |

---

## 3. Evidencia de Ejecución del Seed

Salida de `python scripts/seed_incidents.py`:

```text
============================================================
  NEXOVA — INCIDENT HISTORICAL SEED REPORT
============================================================
  Source file:          data/raw/incidents-nexova.csv
  Total processed:      100
  Inserted:             96
  Skipped (invalid):    4
  Duplicates omitted:   0
============================================================
```

Segunda ejecución (prueba de idempotencia):

```text
============================================================
  NEXOVA — INCIDENT HISTORICAL SEED REPORT
============================================================
  Source file:          data/raw/incidents-nexova.csv
  Total processed:      100
  Inserted:             0
  Skipped (invalid):    4
  Duplicates omitted:   96
============================================================
```

---

## 4. Evidencia de Pruebas Automatizadas

Ejecución de la suite completa de pruebas:

```bash
python -m unittest discover -s packages/incident_analyzer/tests
python -m unittest services/api/tests/test_api.py services/api/tests/test_incident_models.py services/api/tests/test_incident_seed.py services/api/tests/test_incidents_crud_api.py services/api/tests/test_suppliers_api.py
```

Resultado:
- `packages/incident_analyzer/tests`: **9/9 tests OK**.
- `services/api/tests`: **48/48 tests OK** (incluyendo modelos, seed, CRUD, transiciones, proveedores y autenticación).
- **Total: 57 tests ejecutados y pasando (0 fallos, 0 errores, 0 regresiones)**.

---

## 5. Capturas de Pantalla Generadas para la PR

Las capturas requeridas se encuentran ubicadas en `docs/screenshots/`:
1. `incident-form-validation.png`: Formulario con error de validación visible por campos requeridos y mensaje claro.
2. `incident-list.png`: Listado con datos cargados, filtros reactivos y selectores de ciclo de vida.
3. `incident-summary.png`: Panel de resumen con métricas operativas por estado, categoría, origen y sede.
