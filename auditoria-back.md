# Auditoría de Serialización del Backend — Nexova

Guía de trabajo para el proyecto **Backend Serialization Audit / Auditoría de Serialización del Backend** de 4Geeks Academy, cohorte **Architecture optimization**. Reúne el README oficial —incluidas íntegramente sus intenciones de **«Qué debes hacer»** y **«Qué vamos a evaluar»**— y una primera inspección estática del backend del monorepo.

> **Precedencia:** README oficial vigente de 4Geeks → código y consumidores actuales del monorepo → esta guía. Esta guía aporta contexto y un plan: no sustituye los entregables exigidos (`docs/serialization-audit.md`) ni declara que la implementación o las pruebas ya estén hechas. Revalidar cualquier observación contra el checkout sobre el que se trabaje.

## Fuentes y alcance

- Cohorte: **Architecture optimization**, ID `1709`, slug `architecture-optimization`.
- Proyecto de 4Geeks: **Backend Serialization Audit / Auditoría de Serialización del Backend**, tarea `1020099`, slug `ai-eng-backend-serialization`; estado consultado: `PENDING`.
- README oficial: [Español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-performance-serialization/README.es.md) · [English](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-performance-serialization/README.md).
- API declarada en el asset oficial: [descripción del proyecto](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-performance-serialization/README.es.md).
- Monorepo de trabajo: [ai-engineering-company-project-monorepo-luis](https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo-luis).
- Aplicación auditada: `services/api/`, servicio FastAPI. Routers registrados en `services/api/main.py`: incidents, suppliers, auth, users, profiles e inventory. El endpoint `/health` se declara directamente en `main.py`.

## Objetivo y reglas de diseño

Inspeccionar **cada endpoint** de la API, describir qué forma devuelve hoy, quién la consume y qué debería devolver; clasificarlo; implementar esquemas Pydantic explícitos de respuesta en toda la superficie; separar los modelos de entrada de los de salida cuando corresponda; verificar que los contratos no exponen datos internos y que las funcionalidades siguen trabajando.

No reescribir el servicio ni devolver el ORM/documento de almacenamiento sin una proyección explícita. Diseñar el payload desde las necesidades del cliente, no desde todas las columnas disponibles. Para listados, preferir esquemas ligeros; para relaciones, elegir y justificar una representación plana, un ID o un objeto anidado. Mantener los contratos de error y códigos HTTP existentes salvo que un cambio sea necesario, justificado y probado.

### Clasificación requerida por endpoint

- **✅ Ya serializado:** tiene `response_model` explícito y adecuado para sus consumidores; el esquema incluye solo los campos intencionales.
- **⚠️ Parcialmente serializado:** hay un modelo, pero el payload es excesivo/incompleto, la forma no satisface al consumidor, falta un esquema de entrada separado o no queda claro/seguro el contrato.
- **❌ Sin serializar:** no hay `response_model` explícito o se devuelve ORM/dict sin contrato de salida declarado.

La clasificación inicial de abajo es una **revisión estática preliminar** del checkout de `origin/main`, no sustituye recorrer consumidores, ejecutar la API y probar sus respuestas. Cambiarla cuando haya evidencia.

## Inventario preliminar de endpoints

Los routers usan estos prefijos en `main.py`. Confirmar la lista final con OpenAPI (`/openapi.json`) en la versión auditada; incluir rutas adicionales, métodos y rutas de error si aparecen.

| Método y ruta | Propósito | Estado estático inicial | Observación que se debe validar |
|---|---|---|---|
| `GET /health` | Estado del servicio | ❌ | Devuelve un dict con `status` y `service`, sin `response_model`. Definir un esquema pequeño estable. |
| `POST /auth/login` | Inicio de sesión; token Bearer | ✅ | Tiene `TokenResponse`. Comprobar en ejecución ambos modos de entrada soportados (JSON/OAuth2) y que ninguna credencial se filtra. |
| `GET /auth/me` | Identidad y perfil del usuario autenticado | ✅ | Tiene `AuthMeResponse`; el email del propio llamante sí está permitido por el README. Revisar proyección del perfil y campos necesarios en UI. |
| `POST /auth/forgot-password` | Solicitar restablecimiento | ✅ | Tiene `AuthActionResponse`; verificar mensaje genérico, sin revelar si el email existe ni repetirlo en la respuesta. |
| `POST /auth/reset-password` | Cambiar contraseña con token de recuperación | ✅ | Tiene `AuthActionResponse`; el token y contraseña nueva no deben aparecer en la salida ni logs. |
| `POST /auth/change-password` | Cambio de contraseña autenticado | ✅ | Tiene `AuthActionResponse`; comprobar que no devuelve email ni datos de credenciales. |
| `POST /users` | Registro de usuario | ⚠️ | Tiene `UserResponse`, que incluye email. El criterio oficial exige que la ruta de registro no reenvíe email: confirmar si aplica a esta ruta y adaptar el contrato, manteniendo clara la diferencia con `GET /auth/me`. Nunca exponer `hashed_password`. |
| `GET /users` | Listado de usuarios (admin) | ⚠️ | Tiene `list[UserResponse]`; inspeccionar consumo. Evitar over-fetching en el listado y comprobar que no haya contraseña/hash ni campos de perfil innecesarios. |
| `GET /users/{user_id}` | Obtener usuario | ✅* | Tiene `UserResponse`; verificar la política de campos frente al consumidor. `*` solo marcar ✅ final tras pruebas. |
| `PUT /users/{user_id}` | Actualizar credenciales/estado permitido | ✅* | Tiene `UserResponse` e input `UserUpdate`; verificar separación, campos autorizados y respuesta segura. |
| `DELETE /users/{user_id}` | Eliminar usuario y perfil ligado | ❌ | No declara `response_model`; retorna `{"id": ..., "deleted": true}`. Añadir un modelo de confirmación explícito o, si se elige `204`, documentar y probarlo coherentemente. |
| `GET /profiles/me` | Obtener el perfil propio | ✅* | Tiene `ProfileResponse`; contiene `user_id`. Confirmar si el cliente lo necesita o si basta una forma plana con los campos de perfil. |
| `PUT /profiles/me` | Actualizar perfil propio | ✅* | Tiene `ProfileResponse` e input `ProfileUpdate`; comprobar semántica de campos omitidos/null y minimizar identificadores internos innecesarios. |
| `GET /api/incidents/summary` | Métricas agregadas por dimensión | ✅ | Tiene `IncidentSummary`; verificar las claves/métricas que realmente consumen los dashboards. |
| `POST /api/incidents` | Crear incidente | ✅ | Tiene `IncidentRecord`; input `IncidentCreate` separado. Confirmar filtrado/PII y que `id`, `created_at`, `updated_at` sean server-managed. |
| `GET /api/incidents` | Listar incidentes con filtros | ⚠️ | Tiene `list[IncidentRecord]`; comprobar campos usados por la tabla. Puede ser necesario un esquema de fila más liviano que el de detalle. Considerar descripción con datos personales: no exponer más de lo necesario. |
| `GET /api/incidents/{id}` | Obtener un incidente | ✅* | Tiene `IncidentRecord`; verificar acceso, PII y forma frente al detalle UI. |
| `PATCH /api/incidents/{id}/status` | Transición de estado | ✅ | Tiene `IncidentRecord` e input `IncidentStatusUpdate`; revisar si la respuesta completa es necesaria para una operación que actualiza un campo. |
| `POST /api/incidents/analyze` | Analizar CSV y devolver métricas agregadas | ❌ | No declara `response_model`; devuelve `analysis_result.to_dict()`. Añadir esquema Pydantic que describa todos los campos agregados y excluya PII, validándolo contra casos reales de análisis. |
| `GET /api/incidents/results/export` | Descargar CSV de métricas agregadas | ❌* | Devuelve `Response` de `text/csv` y no tiene `response_model`. Un CSV no debe fingirse como JSON: declarar/documentar explícitamente media type, forma/columnas y respuestas de error en OpenAPI; resolver el requisito de contrato explícito de forma compatible con `Response` y probar el contenido. |
| `GET /inventory/products` | Listar activos con stock calculado | ✅* | Tiene `List[AssetRead]`; comprobar si es suficiente para la tabla y que no serialice relaciones ORM adicionales. |
| `POST /inventory/products` | Crear activo | ✅ | Tiene `AssetRead`; input `AssetCreate` separado y `extra="forbid"`. Verificar que campos calculados/server-managed no se acepten en input. |
| `GET /inventory/products/{id}` | Detalle de activo | ✅* | Tiene `AssetRead`; confirmar que el payload sea el mínimo útil para detalle. |
| `POST /inventory/orders/inbound` | Registrar entrada de inventario | ⚠️ | Tiene `AssetEntryRead` e input `AssetEntryCreate`. La salida incluye `user_uuid`: confirmar si la UI necesita este identificador interno o debe eliminarse/representarse de otro modo. |
| `POST /inventory/orders/outbound` | Registrar salida/asignación/consumo | ⚠️ | Tiene `AssetExitRead` e input separado. Revisar `user_uuid` y `assigned_to` según permisos y lo que muestra la UI. |
| `GET /inventory/orders` | Listar movimientos | ⚠️ | Tiene `List[OrderItemRead]`; campos `user_uuid`, nombre y SKU de activo, destinatario/proveedor. Trazar consumidor y justificar cada campo; mantener la proyección ligera para lista. |
| `POST /api/suppliers` | Crear proveedor | ⚠️ | Tiene `SupplierRecord`, input `SupplierCreate` separado. Revisar si notas/contacto son necesarios para todos los consumidores y las restricciones de visibilidad. |
| `GET /api/suppliers` | Listar proveedores con filtros | ⚠️ | Usa `list[SupplierRecord]`, igual que el detalle; evaluar `SupplierListItem` más ligero. Evitar cargar notas/contacto si el listado no los usa. |
| `GET /api/suppliers/{supplier_id}` | Obtener proveedor | ✅* | Tiene `SupplierRecord`; revisar campos de contacto/notas según consumidor y privacidad. |
| `PATCH /api/suppliers/{supplier_id}/rate` | Actualizar tarifa | ✅ | Tiene `SupplierRecord` e input `SupplierRateUpdate` separado; comprobar si se necesita devolver el registro completo tras un cambio puntual. |
| `PATCH /api/suppliers/{supplier_id}/status` | Actualizar estado | ✅ | Tiene `SupplierRecord` e input `SupplierStatusUpdate`; comprobar si se necesita devolver el registro completo. |
| `DELETE /api/suppliers/{supplier_id}` | Eliminar proveedor | ❌ | No declara `response_model`; retorna `{"id": ..., "deleted": true}`. Definir modelo de confirmación explícito o respuesta 204 documentada y probada. |

**Nota de conteo:** la tabla enumera 32 operaciones del código inspeccionado (incluye endpoints CSV). Confirmar el inventario real con OpenAPI y con las rutas montadas cuando se ejecute el proyecto; si el conteo cambia, documentar por qué.

## Hallazgos estáticos iniciales a comprobar

1. **Cuatro endpoints sin contrato Pydantic explícito:** `GET /health`, `POST /api/incidents/analyze` y las dos rutas DELETE (`/users/{user_id}`, `/api/suppliers/{supplier_id}`) no llevan `response_model`. La ruta de análisis tiene una forma de dict creada por el analizador; DELETE retorna un dict de confirmación. Convertirlas en contratos explícitos y añadir pruebas de shape.
2. **Respuesta no JSON del export:** `GET /api/incidents/results/export` retorna CSV mediante `Response`. Mantener `text/csv`; documentar el esquema/columnas y errores en OpenAPI, sin serializar falsamente el CSV como objeto JSON.
3. **Listados reutilizan modelos de detalle:** `GET /users`, `/api/incidents`, `/inventory/products` y `/api/suppliers` devuelven listas de esquemas de recurso. Comprobar los consumidores del frontend y evaluar esquemas separados de listado cuando reduzcan campos, sin crear abstracciones duplicadas si los payloads realmente son iguales.
4. **Identificadores internos en modelos de inventario:** `AssetEntryRead`, `AssetExitRead` y `OrderItemRead` exponen `user_uuid`. Determinar si es una clave interna necesaria para el consumidor; si no, excluirla del contrato público. Verificar también el destino y la sensibilidad de `assigned_to`.
5. **Registro y proyección de usuarios:** `UserResponse` incluye `email`; revisar criterio oficial para `POST /users` (registro) y diseñar una respuesta de creación segura. `GET /auth/me` puede devolver el email del llamante autenticado. Mantener modelos distintos si los casos de uso difieren.
6. **Consumo y PII en incidentes:** el esquema de incidente contiene `description`; inspeccionar UI y requisitos de acceso para decidir si los listados deben reducir o enmascarar contenido, sin afirmar que la descripción contiene PII sin comprobar datos/esquemas.
7. **Proveedores:** `SupplierRecord` hereda los campos de `SupplierCreate`, potencialmente incluye `contact_email` y `notes`. Rastrear los consumidores y separar `SupplierListItem` del detalle si el listado no requiere esa información.

Los puntos de esta sección son observaciones de código/hipótesis, **no mediciones de tamaño ni vulnerabilidades confirmadas**. No imprimir ni incluir contraseñas, hashes, tokens, datos reales de usuarios o información confidencial de proveedores en el documento, fixtures, capturas o salida de pruebas.

## Qué debes hacer

### Fase 1 — Auditoría

- [ ] Leer estas instrucciones, `AGENTS.md` y reglas aplicables, `CONTEXT.md`, `memory-bank/projectbrief.md`, `memory-bank/techContext.md`, `memory-bank/progress.md` y `services/api/README.md`. Leer README de consumidores pertinentes (website/backoffice) y los contratos funcionales aplicables; consultar `SPEC.md` si una ruta afecta al tracker.
- [ ] Inspeccionar rama, estado y diff; no sobrescribir trabajo existente. Trabajar en una rama dedicada; el README oficial propone `feature/serialization-audit`.
- [ ] Confirmar la aplicación FastAPI y los routers activos desde `services/api/main.py`; obtener el inventario final desde `/openapi.json` y contrastarlo con decoradores y métodos, no fiarse de un listado previo.
- [ ] Para cada operación, registrar método, ruta, propósito, consumidor, forma actual, uso de `response_model`, origen de datos, clasificación ✅/⚠️/❌ y evidencia. Distinguir Pydantic, dict ad hoc, objeto ORM/documento y `Response` no JSON.
- [ ] Trazar campos requeridos siguiendo el frontend/consumidor o el cliente real; distinguir campos que el modelo almacena de los que la API debe publicar.
- [ ] Empezar por autenticación/usuarios. No exponer nunca contraseñas ni hashes. En registro/login/forgot/reset, no devolver email en el cuerpo; `GET /auth/me` sí puede devolver el email del llamante autenticado.
- [ ] Registrar auditoría inicial en `docs/serialization-audit.md`, con endpoint por endpoint, los campos actuales, estado y, para cada problema, explicación de causa, riesgo/impacto, forma objetivo del payload y mejora propuesta.
- [ ] Documentar decisiones de relaciones: objeto anidado, ID relacionado o proyección plana. Para listados, justificar campos y no reutilizar el modelo de detalle por comodidad si da lugar a over-fetching.

### Fase 2 — Implementación

- [ ] Crear/ajustar esquemas Pydantic de respuesta para cada endpoint ❌ o ⚠️ y declarar `response_model` explícito en cada ruta aplicable. El entregable mínimo es cero endpoints que devuelvan objetos ORM sin control y cero respuestas JSON sin contrato explícito.
- [ ] Para operaciones CSV/binarias/texto (`Response`), declarar con claridad content type, estructura/columnas y respuestas en OpenAPI y documentar la excepción técnica: no presentar el contenido CSV como JSON ni dejar su contrato indeterminado.
- [ ] Definir esquemas de entrada separados para POST/PUT/PATCH, aceptando solo los campos que el cliente puede cambiar. No reutilizar el modelo de salida como input; prohibir campos extra/server-managed, como IDs, timestamps, hashes, tokens, roles o permisos no editables desde esa operación.
- [ ] Diseñar modelos específicos de listados cuando sus consumidores necesiten menos campos o una forma más plana que el detalle. Aplicar la reducción con evidencia del cliente, no por intuición.
- [ ] Excluir campos sensibles/internos: credenciales, tokens, hashes, claves foráneas sin uso, datos de auditoría o campos no requeridos. No hacer echo de email en registro/login/forgot/reset; preservar la posibilidad de email en `/auth/me` para su propio usuario.
- [ ] Actualizar modelos y lógica de análisis para definir de manera completa el resultado de `POST /api/incidents/analyze`, y verificar que no incluya filas originales ni datos personales.
- [ ] Mantener intencional y explícito el contrato CSV de `/api/incidents/results/export`, incluyendo éxito y errores relevantes.
- [ ] No modificar requisitos de negocio, el comportamiento del frontend ni la persistencia más allá de lo necesario para los contratos acordados. Si hay contradicción entre fuentes o falta decisión funcional, detener esa parte y pedir aclaración.

### Fase 3 — Verificación

- [ ] Ejecutar la suite existente completa del backend tras los cambios. En el repo, el comando documentado es `uv run --locked --project services/api python -m unittest discover -s services/api/tests -v` desde la raíz.
- [ ] Añadir/actualizar tests para cada contrato: campos presentes/ausentes, validación de entrada, `response_model`, errores y protección de secretos; incluir listados y respuestas vacías si aplican.
- [ ] Probar manualmente **al menos tres endpoints** desde FastAPI `/docs` y verificar el shape real contra los esquemas declarados. Incluir un flujo de autenticación sin revelar datos sensibles y al menos un listado; documentar los endpoints probados.
- [ ] Para la respuesta de exportación, comprobar manualmente que `Content-Type` y contenido siguen siendo CSV y que la documentación OpenAPI refleja correctamente el resultado.
- [ ] Consultar `/openapi.json` y comprobar cobertura del inventario completo; cada endpoint debe tener contrato de respuesta explícito, incluyendo excepciones no-JSON correctamente documentadas.
- [ ] Actualizar `docs/serialization-audit.md`: registrar estado original y cambio por endpoint, y marcar ✅ solo tras implementación y pruebas exitosas. Si una ruta queda pendiente o hay una excepción, dejarla claramente identificada; no declarar la tarea completa.
- [ ] Verificar que la aplicación y los consumidores continúan funcionando y que no hay regresiones. Ejecutar solo lint/typecheck/build existentes y pertinentes; no inventar checks ni afirmar que corrieron si no se ejecutaron.
- [ ] Antes de cada commit, revisar diff/staging para excluir secretos, bases de datos, datos personales, archivos generados y cambios ajenos. Seguir además el flujo del repo para commits y memoria/documentación.

## Qué vamos a evaluar

Criterios de aceptación derivados del README oficial; marcar como cumplidos únicamente con evidencia:

- [ ] **Cada endpoint** de la aplicación tiene `response_model` explícito, o su contrato no-JSON queda explícito y comprobable en OpenAPI cuando técnicamente no corresponde un modelo JSON.
- [ ] Los esquemas Pydantic de entrada y salida existen donde corresponde y no se reutilizan de forma que permitan escribir campos no autorizados.
- [ ] Los endpoints de listado exponen únicamente los campos que necesita su consumidor; no hay anidamiento ni over-fetching injustificado.
- [ ] Ningún esquema de respuesta expone hashes de contraseña o tokens internos. Registro, login, forgot/reset no reenvían email; `/auth/me` puede devolver el email del usuario autenticado.
- [ ] `docs/serialization-audit.md` existe, enumera todos los endpoints y deja constancia de su estado original, clasificación y cambios aplicados; explica objetivo y justificación de cada payload.
- [ ] Las relaciones tienen una decisión explícita (objeto anidado/ID/proyección plana) documentada y consistente con el consumidor.
- [ ] Todos los tests previos pasan; los nuevos tests validan los contratos, campos sensibles, requests y respuestas.
- [ ] Se probaron manualmente al menos tres endpoints en `/docs`, y la respuesta observada coincide con el esquema.
- [ ] La aplicación sigue funcionando tras los cambios y no hay regresiones.
- [ ] La calidad de la auditoría escrita es suficiente por sí misma: una implementación sin inventario y justificación documentados no aprueba el entregable.

## Entregables y entrega

- Este archivo, `auditoria-back.md`, es una **guía contextual** y no reemplaza los siguientes entregables oficiales:
  - `docs/serialization-audit.md`: auditoría completa endpoint por endpoint, estado inicial, clasificación y estado final/cambios.
  - Esquemas Pydantic de entrada/salida y `response_model` explícitos donde corresponda.
  - Tests y evidencia de verificación de `/docs`, OpenAPI, contratos y suite completa.
- Subir una rama a GitHub y abrir un Pull Request contra `main` con el título **`feat: serialization audit and implementation`**, siguiendo el README oficial. Compartir el enlace del PR según las instrucciones del instructor.
- No declarar lista la implementación mientras queden endpoints sin contrato explícito, criterios pendientes o pruebas no ejecutadas.

## Registro de evidencia (completar durante la ejecución)

- Rama/base y commit de partida: _pendiente_
- Fecha y versión/commit del inventario de rutas: _pendiente_
- Número final de operaciones/métodos en OpenAPI: _pendiente_
- Endpoint(s) probados manualmente en `/docs`: _pendiente_
- Comando y resultado de suite backend: _pendiente_
- Campos sensibles revisados y evidencia: _pendiente_
- Endpoints con excepción no-JSON y su documentación: _pendiente_
- Commit(s) y PR: _pendiente_
- Limitaciones o criterios no satisfechos: _pendiente_
