# Gestor de Incidencias Centralizado — Nexova

> Guía de implementación para la tarea **Centralized Incident Manager / Gestor de Incidencias Centralizado** de 4Geeks. Consolida el README oficial, el briefing de Nexova, los criterios de evaluación y el estado del monorepo auditado. **Ante cualquier discrepancia, prevalecen el README y el briefing oficiales.**

## Fuentes y alcance auditados

- Tarea de 4Geeks: **Centralized Incident Manager**, cohorte **Error handling, debugging and testing**, tarea `1003161`, slug `ai-eng-centralized-incident-manager`; estado observado en la API: `PENDING`.
- README oficial: [español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-centralized-incident-manager/README.es.md) · [inglés](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-centralized-incident-manager/README.md).
- Briefing asignado a esta empresa: [Nexova — español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/centralized-incident-manager/nexova-BRIEFING.es.md).
- Monorepo de trabajo: `ai-engineering-company-project-monorepo-luis`.
- Contexto y código local relevantes: [`docs/contexts/incidents-context.es.md`](./docs/contexts/incidents-context.es.md), [`packages/incident_analyzer/`](./packages/incident_analyzer/), [`data/raw/incidents-nexova.csv`](./data/raw/incidents-nexova.csv), [`services/api/`](./services/api/), [`uis/backoffice/`](./uis/backoffice/), [`docs/DELIVERY_INCIDENTS_ANALYZER.md`](./docs/DELIVERY_INCIDENTS_ANALYZER.md).

La tarea no consiste en volver a analizar o cargar CSV manualmente desde el panel. El CSV se importa una vez mediante un seed; desde entonces, la vía normal de alta es el formulario web. El proyecto debe ampliar la plataforma/monorepo existente, no crear un repositorio ni un backend alternativo.

## Objetivo funcional

Dar al equipo de Nexova un gestor centralizado donde registrar, consultar y seguir incidencias de clientes, sedes y equipos internos. La solución debe incluir persistencia, seed del histórico, API CRUD/consulta y resumen, interfaz de registro y listado, transiciones válidas de estado y manejo de errores comprensible. Debe seguir funcionando con base vacía, errores de red/API, demoras y respuestas HTTP 500 sin exponer stack traces al usuario.

## Decisiones del briefing Nexova — usar literalmente

### Estados y transiciones

- Valores: `open`, `in_progress`, `resolved`, `discarded`.
- Transiciones permitidas: `open → in_progress`, `open → discarded`, `in_progress → resolved`, `in_progress → discarded`.
- `resolved` y `discarded` son finales. Rechazar cualquier transición no indicada con HTTP `400`.

### Orígenes

- `customer`: reporte de un cliente corporativo.
- `branch`: reporte de personal de una oficina Nexova.
- `internal`: detectado por tecnología, operaciones o dirección.

### Sedes (`branch`)

El campo es obligatorio y solo puede tomar estos valores exactos. `central` es la sede central de Valencia; **no** inventar un valor `headquarters`.

| Valor persistido | Etiqueta visible |
|---|---|
| `central` | Central — Sede Valencia |
| `valencia_operations` | Valencia — Operaciones |
| `miami_office` | Miami Office |
| `remote` | Remoto (empleado sin sede fija) |

Cuando no exista una sede concreta (por ejemplo, una incidencia interna de dirección o una queja de cliente sin sede asociada), usar `central`. No confundir `remote` con una oficina.

### Categorías

El campo debe coincidir exactamente con uno de estos valores:

| Valor | Uso |
|---|---|
| `technical_failure` | Fallo de sistemas o herramientas (ATS, HubSpot, Zendesk, infraestructura). |
| `process_error` | Error de procesos operativos: selección, onboarding, formación o facturación. |
| `client_complaint` | Queja de cliente corporativo sobre el servicio. |
| `candidate_issue` | Problema de o relacionado con un candidato. |
| `staff_issue` | Incidencia interna de RR. HH. (ausencia, conflicto, accidente, baja). |
| `sla_breach` | Incumplimiento del SLA comprometido con un cliente. |
| `data_quality` | Error o inconsistencia en datos de candidatos, clientes o informes. |
| `other` | Incidencia que no encaja en las categorías anteriores. |

El README destaca que las incidencias `sla_breach` son críticas para el equipo directivo. No se pide implementar alertas automáticas en esta entrega, pero la categoría debe quedar soportada y ser filtrable de forma natural.

## Qué debes hacer — especificación consolidada

### 1. Modelo y persistencia

Implementar `Incident` con:

- `id`: identificador único generado automáticamente.
- `title`: título breve, obligatorio.
- `description`: detalle, obligatorio.
- `category`: valor válido del briefing Nexova.
- `status`: valor válido del ciclo de vida descrito arriba.
- `origin`: `customer`, `branch` o `internal`.
- `branch`: una sede válida, obligatorio en todos los orígenes.
- `created_at`: timestamp de creación automático.
- `updated_at`: timestamp automático que se actualiza en cada modificación.

Aplicar restricciones en la capa apropiada para que campos obligatorios y enums se validen de forma consistente. Mantener persistencia con el almacenamiento y convenciones del backend actual; no añadir otra base de datos sin una razón documentada.

### 2. Seed histórico en `/scripts`

Crear `scripts/seed_incidents.py` que cargue `data/raw/incidents-nexova.csv` en el almacenamiento de incidencias:

- Validar el CSV reutilizando las reglas existentes de `packages/incident_analyzer` o extraer/reubicar lógica común en `packages/shared/` si hace falta. Evitar una segunda implementación divergente del validador.
- No insertar filas inválidas; reportar al final el total insertado, omitido/inválido y duplicado, sin imprimir información sensible.
- Asignar siempre `origin: "customer"` y `branch: "central"` (el CSV no incluye una oficina Nexova).
- La llave de idempotencia es `ticket_id`; no almacenarlo en el modelo final. Si el CSV no tuviera ese campo, usar la combinación `title + created_at`.
- Ejecutar el seed más de una vez no debe duplicar registros.
- Aplicar las siguientes transformaciones exactas antes de insertar:

| CSV | Modelo | Regla |
|---|---|---|
| `ticket_id` | — | Solo deduplicación; no almacenar. |
| `description` | `title` | Primeros 120 caracteres, recortados; descartar si queda vacío. |
| `description` | `description` | Copiar literalmente. |
| `date` | `created_at` | Parsear `YYYY-MM-DD` como medianoche UTC. |
| — | `updated_at` | Igual a `created_at` al insertar. |
| — | `origin` | Siempre `customer`. |
| — | `branch` | Siempre `central`. |

**Mapeo de estado**

| CSV | Modelo |
|---|---|
| `OPEN` | `open` |
| `CLOSED` | `resolved` |
| `DISCARDED` | `discarded` |

**Mapeo de categoría**

| CSV | Modelo |
|---|---|
| `TECHNICAL` | `technical_failure` |
| `BILLING` | `process_error` |
| `ACCESS` | `technical_failure` |
| `HR_QUERY` | `process_error` |
| `COMPLAINT` | `client_complaint` |

No inventar una categoría para registros inválidos/no mapeables: descartarlos y contarlos en el informe del seed.

### 3. API en el servicio existente (`/services`)

Añadir al backend actual estos endpoints bajo `/api/incidents`:

- `POST /api/incidents`: crear incidencia. Validar campos obligatorios y valores permitidos; devolver `400` descriptivo para datos inválidos.
- `GET /api/incidents`: listar; aceptar filtros opcionales `status`, `origin`, `branch`, `category`.
- `GET /api/incidents/{id}`: detalle; `404` si no existe.
- `PATCH /api/incidents/{id}/status`: actualizar solamente el estado, validar transición de acuerdo con la matriz anterior y actualizar `updated_at`.
- `GET /api/incidents/summary`: agregados por estado, categoría, origen y sede.

Errores y casos límite:

- Los errores de validación retornan HTTP `400` en JSON con el campo problemático y una explicación clara, sin filtrar detalles internos.
- Incidencia inexistente: `404`.
- Transición de estado inválida: `400`.
- Excepción no controlada: `500` con mensaje genérico; registrar internamente solo lo necesario, sin devolver stack trace al cliente.
- Con base vacía, endpoints de lectura responden normalmente: lista vacía y métricas con cero/colecciones vacías.
- Aplicar los filtros de forma combinable y validar sus valores.
- Mantener los endpoints y funcionalidades ya existentes (analizador CSV, autenticación, proveedores y demás); no romper regresiones.

### 4. Frontend en `/uis`

Ampliar una UI existente apropiada y conectarla al backend real. En este checkout existe el backoffice estático en `uis/backoffice/` y existe también una app Next.js distinta (`uis/talent-pipeline-tracker/`); revisar sus READMEs y contratos antes de elegir dónde se integra. No modificar el sitio público como si fuera una consola interna ni enviar estas llamadas al API externo de Tracker por accidente.

**Formulario de registro**

- Accesible desde el menú de la aplicación.
- Campos del modelo; `branch` siempre visible y requerido, con las cuatro opciones/etiquetas del briefing.
- Si `origin` es `branch`, destacar visualmente la sede para recordar el reporte desde una oficina específica.
- Validar obligatorios y enums en cliente antes del request.
- Mostrar carga y deshabilitar el botón mientras se envía.
- Mostrar errores con lenguaje de usuario, nunca stack traces/texto técnico del servidor; si hay campo identificado, ubicar el error junto a ese campo.
- En éxito, limpiar el formulario y mostrar confirmación clara.

**Listado / panel de incidencias**

- Mostrar incidencias y permitir filtros por `status`, `origin` y `branch` (el API también admite `category`).
- Mostrar estados de carga, error con acción para reintentar, vacío y resultados; nunca dejar la vista rota/en blanco ni una tabla vacía sin explicación.
- Permitir actualizar estado desde la lista respetando las transiciones del backend.
- Si falla la actualización, revertir el cambio visual optimista al estado previo y avisar al usuario.

**Panel de resumen**

- Consumir `/api/incidents/summary` y presentar totales por estado, categoría, origen y sede.
- Gestionar carga y error sin romper el resto de la pantalla.

Nexova opera en español e inglés. Si la UI elegida ya soporta ambos idiomas, mantener esa convención para formulario y mensajes.

### 5. Entrega

- Mantener el trabajo en el monorepo y organizarlo según responsabilidades: `scripts/`, `packages/shared/` cuando corresponda, `services/` y `uis/`.
- Subir una rama y abrir PR hacia `main` del repositorio del proyecto; tras aprobación, hacer merge a `main` antes de comenzar el siguiente trabajo.
- Incluir en el PR capturas de: (1) formulario con error de validación visible, (2) listado con datos cargados y (3) resumen con métricas.

## Qué vamos a evaluar — checklist de aceptación

### Modelo y seed

- [ ] El modelo tiene todos los campos requeridos, integridad y valores permitidos.
- [ ] El seed carga el histórico válido con `origin=customer` y `branch=central`.
- [ ] Se aplican exactamente los mapeos de estado, categoría, título y fecha del briefing.
- [ ] Registros inválidos/no mapeables se omiten y se reportan sin exponer datos sensibles.
- [ ] El seed es idempotente según `ticket_id`.
- [ ] Tras seed, el resumen coincide con estos valores **post-transformación**:

| Dimensión | Valor | Total |
|---|---|---:|
| Estado | `open` | 27 |
| Estado | `resolved` | 56 |
| Estado | `discarded` | 13 |
| Categoría | `technical_failure` | 49 |
| Categoría | `process_error` | 35 |
| Categoría | `client_complaint` | 12 |

Esto corresponde a 96 registros válidos del fixture. Los cuatro inválidos no se incluyen. Las categorías `candidate_issue`, `staff_issue`, `sla_breach`, `data_quality` y `other` deben ser válidas para incidencias creadas manualmente, aunque tengan conteo cero en el seed.

### Backend

- [ ] Los endpoints cumplen códigos HTTP esperados en casos correctos y de error.
- [ ] Validación JSON identifica el campo y mensaje entendible.
- [ ] Ningún endpoint expone stack trace.
- [ ] Transiciones inválidas/finales se rechazan con `400`.
- [ ] `/summary` devuelve métricas correctas incluso sin datos.
- [ ] Filtros opcionales y combinados producen resultados correctos.

### Frontend

- [ ] Formulario valida campos requeridos antes de enviar.
- [ ] Al elegir origen `branch`, sede resaltada; opciones y etiquetas coinciden con Nexova.
- [ ] Carga visible y botón deshabilitado durante el envío.
- [ ] Errores expresados en lenguaje claro y no técnico.
- [ ] Listado cubre carga, vacío, error/reintento y datos.
- [ ] Fallo al actualizar estado restaura el valor anterior y notifica.
- [ ] Fallo del resumen no rompe otras partes de la interfaz.

### Transversal y entrega

- [ ] Validador compartido del proyecto anterior se reutiliza; no duplicar reglas.
- [ ] Código queda organizado en las carpetas del monorepo.
- [ ] Pruebas cubren comportamiento feliz, validación, errores, estados vacíos y regresiones.
- [ ] PR contiene las tres capturas solicitadas.

## Matriz recomendada de pruebas (error handling, debugging y testing)

### Seed y transformaciones

- Fixture oficial: 100 filas; validar las 96 válidas y cuatro inválidas. Comprobar conteos por causa con el analizador existente, sin mostrar correos.
- Probar idempotencia ejecutando el seed dos veces; segundo intento agrega cero duplicados.
- Probar fecha UTC, título truncado a 120 caracteres y título vacío descartado.
- Probar cada mapeo de estado/categoría y valores desconocidos.
- Probar que el seed no almacene `ticket_id` ni `customer_email` en el modelo y que salida/logs no contengan PII.

### API

- `POST`: payload correcto; faltan `title`, `description`, `branch`; categoría/origen/sede/estado inválido; whitespace; verificar JSON de validación y `400`.
- `GET`: sin datos, con datos, cada filtro válido, filtro inválido y combinación de filtros.
- `GET /{id}`: id existente y no existente (`404`).
- `PATCH`: cada transición válida, cada transición inválida, estados finales, id inexistente y timestamp actualizado.
- `/summary`: conjunto vacío y dataset conocido; totales exactos de estado, categoría, origen y sede.
- Simular error interno/almacenamiento: HTTP `500` genérico, sin stack trace o detalles sensibles en response.
- Correr también la suite existente para asegurar que autenticación, usuarios/proveedores y analizador de CSV siguen operativos.

### UI / integración

- Errores de campo sin request; error API `400` mapeado a mensaje humano; fallo de red/timeout/`500` con feedback y reintento cuando proceda.
- Estado de carga y bloqueo de doble submit; confirmación y formulario limpio al crear.
- Listado cargando, vacío, error/reintento y resultados filtrados.
- Actualización de estado válida e inválida; en fallo, rollback visible.
- Resumen con datos, vacío y fallo aislado.
- Capturar las tres pantallas pedidas para el PR.

## Estado del monorepo auditado y guía de integración

- El checkout ya contiene el histórico en `data/raw/incidents-nexova.csv` y un paquete funcional de análisis/validación en `packages/incident_analyzer/`; reutilizarlo para las reglas compartidas.
- La API ya tiene `services/api/routers/incidents.py`, pero sus operaciones actuales analizan un CSV (`POST /analyze`) y exportan resultados agregados (`GET /results/export`); no asumir que eso ya implementa el nuevo CRUD.
- Ya hay UI y estilos de incidentes en `uis/backoffice/incidents.js` y `incidents.css`, orientados al analizador CSV; extender con cuidado sin borrar esa funcionalidad.
- El backend utiliza FastAPI y TinyDB en otras áreas. Revisar los patrones de almacenamiento/configuración del servicio y la guía `services/api/README.md` antes de implementar la persistencia del gestor.
- `docs/contexts/incidents-context.es.md` es el contexto del proyecto anterior (analizador de tickets), no el briefing nuevo de Nexova. Para sedes, categorías y mapeos de este proyecto, usar el briefing enlazado arriba.
- `/api/incidents/summary` debe ser una ruta específica (`/summary`), no confundirse con el endpoint previo de exportación.

## Fuera de alcance obligatorio

- Embeddings, búsqueda semántica, detección automática de duplicados y triaje por IA: el README los presenta como posibles evoluciones, no son requisito de esta entrega.
- Alertas automáticas para `sla_breach`: no solicitadas; sí debe poderse almacenar/filtrar esa categoría.
- Cargar el histórico desde el frontend: el CSV se carga por el script de seed; a partir de ahí la UI es la entrada de nuevos registros.
