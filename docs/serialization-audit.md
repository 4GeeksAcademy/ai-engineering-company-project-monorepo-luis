# Auditoria de serializacion del backend - Nexova

## Estado y alcance

Etapa 1: auditoria inicial y plan documentados el **2026-11-02**. No se han
implementado cambios funcionales ni certificado los contratos finales.

- Rama: `docs/auditoria-back`, siguiendo `origin/docs/auditoria-back`.
- Commit de partida: `6d3d493b60cfd5b284ff1e2af25f602c54ed26a4`.
- Arbol limpio al iniciar. API: FastAPI, version declarada `1.0.0`.
- Alcance: las **32 operaciones** de negocio/health publicadas por la aplicacion
  de [main.py](../services/api/main.py), incluidos los seis routers registrados.
- `/docs`, `/redoc` y `/openapi.json` son infraestructura de FastAPI, no operaciones
  de negocio adicionales. Los errores son respuestas de cada operacion, no rutas
  independientes.
- Fuentes: [guia local](../auditoria-back.md),
  [README oficial](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-performance-serialization/README.es.md),
  [instrucciones](../AGENTS.md), reglas de `.agents/rules/`, contexto y banco de
  memoria, README de API/backoffice y contratos de los consumidores citados abajo.
- Precedencia: README oficial vigente, contratos de negocio/consumidores y codigo,
  guia local. Las referencias historicas a hitos retirados no justifican recrearlos.
- Exclusiones: reescritura del servicio, migraciones, cambios de permisos o negocio,
  datos reales, configuracion de produccion y API externa de candidatos del tracker.

### Metodo y evidencia

Se consulto `GET /openapi.json` con `fastapi.testclient.TestClient(app)`, sin usarlo
como context manager: respuesta HTTP 200, sin ejecutar lifespan, JWT, seeds ni
dependencias de endpoints de negocio. Se uso el Python ya instalado en
`services\api\.venv\Scripts\python.exe`; no se instalaron dependencias.

El inventario se cruzo con los decoradores de `main.py` y `routers/*.py`, los
modelos, proyecciones y consumidores. Para inspeccionar `APIRoute` se combinaron
las rutas de la aplicacion y de los routers importados: la primera consulta que
solo recorria `app.routes` no encontraba las rutas incluidas en esta version de
FastAPI. La consulta corregida termino con codigo 0 y 32 operaciones.

Hallazgos verificables de OpenAPI:

- 27 operaciones declaran un modelo Pydantic explicito en el decorador.
- Dos DELETE infieren `dict[str, int | bool]` de la anotacion de retorno:
  `additionalProperties` permite enteros/booleanos, sin exigir claves concretas.
  No equivalen a una confirmacion Pydantic con `id` y `deleted` obligatorios.
- Health y analisis declaran exito JSON con `schema: {}`.
- Export declara exito `application/json` con `schema: {}`, aunque el codigo
  devuelve `Response(media_type="text/csv")`: documentacion y contenido divergen.
- No se identifico en la inspeccion un endpoint que devuelva un ORM de inventario
  sin proyeccion: el servicio construye esquemas antes de responder. Esto no
  certifica ausencia de filtraciones en ejecucion.

No se probaron respuestas de negocio ni Swagger interactivo, suite backend,
lint/build o UI en esta etapa documental. El aviso Starlette/httpx observado no
impidio consultar OpenAPI y no se cambio ninguna dependencia para resolverlo.

## Convenciones del inventario

- **YA** = ya serializado (equivalente a la clasificacion inicial de la guia):
  modelo explicito adecuado segun evidencia estatica; verificacion final pendiente.
- **PARCIAL** = contrato existente que requiere decision, ajuste o evidencia
  adicional de consumidor.
- **SIN** = falta un contrato de salida explicito con campos definidos.
- **SIN/CSV** = excepcion no JSON todavia mal documentada.
- Estado final **P** = pendiente de implementacion/verificacion; no es aprobacion.
- En las tablas, las formas objetivo son propuestas para la etapa indicada,
  no cambios ya aplicados. Una ruta sin consumidor UI identificado mantiene su
  contrato compatible; Swagger y tests existentes siguen siendo consumidores.

### Catalogo de formas actuales y objetivo

Los campos enumerados son nombres de contrato, nunca valores reales. `[]` indica
lista; nullable no equivale a campo omitido. Preservar esta distincion al implementar.

| Alias | Forma actual y fuente | Forma objetivo y justificacion |
|---|---|---|
| H | Dict: `status`, `service` en `main.py`. | Modelo pequeno con ambas claves obligatorias; mismo JSON y HTTP 200. |
| T | `TokenResponse`: `access_token`, `token_type`. | Mantener token publico de acceso y tipo bearer; necesarios para login, sin email. No confundir este token intencional con tokens internos de recuperacion. |
| A | `AuthActionResponse`: `message`. | Mantener confirmacion; forgot generico para ambos casos, sin email ni token de recuperacion. |
| U | `UserResponse`: `id`, `email`, `is_active`, `role`, `created_at`. | Mantener detalle/actualizacion compatible. Justificar email/rol/estado por gestion autorizada; no reutilizar para registro publico. Evaluar listado por separado. |
| R | Registro usa U, incluido email. | Propuesta: confirmacion `message` sin email ni campos de credenciales. El formulario descarta el cuerpo y hace login con su input; ajustar tipo del cliente junto al contrato. |
| P | `ProfileResponse`: `name`, `phone`, `address`, `id`, `user_id`. | Mantener contacto y semantica nullable; justificar IDs o retirarlos coordinadamente de modelos/tipos tras trazar el perfil completo. No eliminarlos solo por ser relaciones. |
| M | `AuthMeResponse`: `email`, `role`, `profile` (P). | Mantener email propio, rol y proyeccion anidada del perfil; nunca incluir `UserRecord` ni hash. |
| D | Dict: `id`, `deleted`. | Confirmacion explicita con ID positivo y `deleted` verdadero; mantener HTTP 200 y ambos campos, sin cambiar a 204. |
| I | `IncidentRecord`: `title`, `description`, `category`, `origin`, `branch`, `id`, `status`, `created_at`, `updated_at`. | Mantener detalle; para listado conservar los campos usados y evaluar `updated_at`, no quitar descripcion que la tabla muestra. |
| S | `IncidentSummary`: `total`, `by_status`, `by_category`, `by_origin`, `by_branch`. | Conservar agregados y dimensiones, incluidos ceros/base vacia. Sin registros individuales. |
| X | `IncidentAnalysisResult.to_dict()`: `total_records`, `valid_records`, `invalid_records`, `category_counts`, `status_counts`, `invalid_breakdown`, `satisfaction`, `errors_count`. | Modelo completo de agregados; `satisfaction` contiene `scored_tickets`, `total_closed_tickets`, `average_score` nullable y `score_distribution`. No publicar `row_errors` ni filas originales. |
| C | CSV del exportador: columnas `metric,value`. | CSV documentado como texto, attachment `results.csv`; mantener categorias/estados, contadores, satisfaccion y razones invalidas. Promedio sin puntuaciones: `N/A`; con puntuaciones: dos decimales. |
| B | `AssetRead`: `name`, `sku`, `category`, `office`, `id`, `current_stock`. | Mantener: tabla/filtros y acciones necesitan todos estos campos; stock calculado, no editable. |
| E | `AssetEntryRead`: `id`, `asset_id`, `quantity`, `supplier`, `office`, `created_at`, `user_uuid`. | Mantener proyeccion explicita y revisar campos necesarios para confirmacion; autor server-managed. No eliminarlo globalmente: el historial lo muestra. |
| O | `AssetExitRead`: `id`, `asset_id`, `quantity`, `exit_type`, `assigned_to` nullable, `office`, `created_at`, `user_uuid`. | Mantener asignacion/consumo y revisar confirmacion; `assigned_to` tiene uso funcional, no debe eliminarse sin alternativa. |
| L | `OrderItemRead`: `id`, `movement_type`, `asset_id`, `asset_name`, `asset_sku`, `quantity`, `office`, `supplier` nullable, `exit_type` nullable, `assigned_to` nullable, `created_at`, `user_uuid`. | Proyeccion plana; conservar nombres canonicos de API y alinear consumidor. Justificar IDs de movimiento/activo y autor; no anidar objetos ORM completos. |
| F | `SupplierRecord`: `name`, `country`, `categories`, `monthly_rate`, `currency`, `status`, `contract_renewal_date` nullable, `contact_email` nullable, `notes` nullable, `id`, `updated_at`. | Conservar detalle; listado utiliza contacto/notas ademas de campos comerciales. Evaluar solo campos realmente sobrantes, como timestamp no renderizado, sin duplicar esquemas identicos. |

Fuentes de modelos: [auth_models.py](../services/api/auth_models.py),
[incident_models.py](../services/api/incident_models.py),
[schemas.py](../services/api/schemas.py),
[supplier_models.py](../services/api/supplier_models.py),
[analizador](../packages/incident_analyzer/models.py) y
[exportador](../packages/incident_analyzer/exporter.py).

## Inventario completo de operaciones

Cada fila remite a una forma del catalogo: este contiene la lista actual y el
objetivo. La columna origen describe el dato proyectado, no una autorizacion para
publicar todas las columnas almacenadas. "Modelo" significa `response_model`
explicito; los DELETE solo tienen inferencia generica.

### Autenticacion, usuarios y perfiles - 12 operaciones

Evidencia: routers [auth](../services/api/routers/auth.py),
[users](../services/api/routers/users.py), [profiles](../services/api/routers/profiles.py),
[cliente tracker](../uis/talent-pipeline-tracker/lib/nexova-api.ts),
[tipos](../uis/talent-pipeline-tracker/types/auth.ts) y
[formulario](../uis/talent-pipeline-tracker/components/auth-form.tsx).

| # | Metodo y ruta / proposito | Entrada | Salida actual / origen | Consumidor y objetivo | Inicial | Etapa / final |
|---|---|---|---|---|---|---|
| 1 | `POST /auth/login`: iniciar sesion | `LoginRequest`; JSON u OAuth2 form | Modelo T, 200; JWT creado desde usuario TinyDB | Tracker y cliente backoffice: T; ambos formatos y credenciales invalidas deben conservarse | YA | 2 / P |
| 2 | `GET /auth/me`: identidad propia | Bearer; sin body | Modelo M, 200; usuario/perfil TinyDB | Tracker y backoffice: M; email propio permitido, perfil anidado intencional | PARCIAL | 2 / P |
| 3 | `POST /auth/forgot-password`: solicitar recuperacion | `ForgotPasswordRequest` | Modelo A, 200; confirmacion/background task | Cliente tracker: A; mismo mensaje exista o no usuario | YA | 2 / P |
| 4 | `POST /auth/reset-password`: restablecer | `ResetPasswordRequest` | Modelo A, 200; servicio de recuperacion TinyDB | Cliente tracker: A; no repetir token ni nueva clave | YA | 2 / P |
| 5 | `POST /auth/change-password`: cambiar clave propia | `ChangePasswordRequest`, Bearer | Modelo A, 200; servicio de credenciales TinyDB | Cliente tracker: A; no incluir email/credenciales | YA | 2 / P |
| 6 | `POST /users`: registro publico | `UserRegistration` | Modelo U, 201; usuario/perfil creados en TinyDB | Formulario tracker descarta respuesta; U debe pasar a R y cambiar tipo de retorno del cliente | PARCIAL | 2 / P |
| 7 | `GET /users`: listado admin | Bearer; sin body | Modelo U[], 200; proyecciones TinyDB | Sin UI identificada; Swagger/tests. Justificar campos para admin, no reducir sin caso de uso | PARCIAL | 2 / P |
| 8 | `GET /users/{user_id}`: detalle propietario/admin | Path, Bearer | Modelo U, 200; proyeccion TinyDB | Swagger/tests; mantener U autorizado, sin hash | YA | 2 / P |
| 9 | `PUT /users/{user_id}`: actualizar usuario | `UserUpdate`, path, Bearer | Modelo U, 200; proyeccion TinyDB | Swagger/tests; mantener U y autorizacion admin para rol/estado | YA | 2 / P |
| 10 | `DELETE /users/{user_id}`: borrar usuario/perfil | Path, Bearer | Dict D, 200; confirmacion del servicio | Swagger/tests; fijar D con modelo, no 204 | SIN | 3 / P |
| 11 | `GET /profiles/me`: perfil propio | Bearer; sin body | Modelo P, 200; proyeccion TinyDB | Cliente tracker: P; decision explicita sobre IDs pendientes | PARCIAL | 2 / P |
| 12 | `PUT /profiles/me`: actualizar contacto | `ProfileUpdate`, Bearer | Modelo P, 200; proyeccion TinyDB | Cliente tracker: P; conservar campos omitidos frente a null | PARCIAL | 2 / P |

### Incidentes y analisis - 7 operaciones

Evidencia: [router](../services/api/routers/incidents.py),
[consumidor](../uis/backoffice/incidents.js), analizador/exportador del catalogo.

| # | Metodo y ruta / proposito | Entrada | Salida actual / origen | Consumidor y objetivo | Inicial | Etapa / final |
|---|---|---|---|---|---|---|
| 13 | `GET /api/incidents/summary`: resumen | Sin body | Modelo S, 200; agregacion TinyDB | Dashboard: S; todas las dimensiones y total | YA | 5 / P |
| 14 | `POST /api/incidents`: crear | `IncidentCreate` | Modelo I, 201; documento TinyDB proyectado | Formulario backoffice: I; conservar alta y campos server-managed | YA | 5 / P |
| 15 | `GET /api/incidents`: listar/filtrar | Query `status`, `origin`, `branch`, `category` | Modelo I[], 200; documentos TinyDB proyectados | Tabla usa ID, titulo, descripcion, dimensiones, estado, fecha; evaluar solo campos restantes | PARCIAL | 5 / P |
| 16 | `GET /api/incidents/{id}`: detalle | Path | Modelo I, 200; documento TinyDB proyectado | Sin detalle UI identificado; Swagger/tests: I | YA | 5 / P |
| 17 | `PATCH /api/incidents/{id}/status`: transicion | `IncidentStatusUpdate`, path | Modelo I, 200; documento actualizado | Selector backoffice; revisar necesidad de I completo sin romper contrato existente | PARCIAL | 5 / P |
| 18 | `POST /api/incidents/analyze`: analizar CSV | Multipart, `UploadFile` campo `file` | Dict X, 200; dataclass del analizador | Dashboard CSV: X completo tipado, no `row_errors` ni PII | SIN | 4 / P |
| 19 | `GET /api/incidents/results/export`: descargar | Sin body | `Response` C, 200; ultimo agregado global en memoria | Descarga backoffice: C, no JSON; documentar errores y media type real | SIN/CSV | 4 / P |

### Inventario - 6 operaciones

Evidencia: [router](../services/api/routers/inventory.py),
[servicio](../services/api/inventory_service.py),
[cliente](../uis/backoffice/inventory-api.js),
[catalogo](../uis/backoffice/inventory-view.js),
[historial](../uis/backoffice/order-history.js).

| # | Metodo y ruta / proposito | Entrada | Salida actual / origen | Consumidor y objetivo | Inicial | Etapa / final |
|---|---|---|---|---|---|---|
| 20 | `GET /inventory/products`: catalogo | Sin body | Modelo B[], 200; SQLModel + calculo stock | Tabla, filtros y selector de activos: B[] ya ligero | YA | 7 / P |
| 21 | `POST /inventory/products`: crear activo | `AssetCreate`, Bearer | Modelo B, 201; SQLModel proyectado | Swagger/tests; B, stock calculado inicial y SKU unico | YA | 7 / P |
| 22 | `GET /inventory/products/{id}`: detalle | Path | Modelo B, 200; SQLModel + stock | Cliente backoffice/Swagger: B; no cargar movimientos anidados | YA | 7 / P |
| 23 | `POST /inventory/orders/inbound`: entrada | `AssetEntryCreate`, Bearer | Modelo E, 201; SQLModel proyectado | Formulario movimientos: revisar E y confirmacion, autor derivado del usuario | PARCIAL | 7 / P |
| 24 | `POST /inventory/orders/outbound`: salida | `AssetExitCreate`, Bearer | Modelo O, 201; SQLModel proyectado | Formulario movimientos: revisar O; asignacion/consumo y stock preservados | PARCIAL | 7 / P |
| 25 | `GET /inventory/orders`: historial | Sin body | Modelo L[], 200; proyeccion plana SQLModel | Historial usa autor/destino; espera alias distintos para tipo/nombre/SKU: alinear con L | PARCIAL | 7 / P |

### Proveedores - 6 operaciones

Evidencia: [router](../services/api/routers/suppliers.py) y
[consumidor](../uis/backoffice/suppliers.js).

| # | Metodo y ruta / proposito | Entrada | Salida actual / origen | Consumidor y objetivo | Inicial | Etapa / final |
|---|---|---|---|---|---|---|
| 26 | `POST /api/suppliers`: crear | `SupplierCreate` | Modelo F, 201; documento TinyDB proyectado | Formulario backoffice; F, ID/timestamp server-managed | YA | 6 / P |
| 27 | `GET /api/suppliers`: listado/filtros | Query `country`, `category` | Modelo F[], 200; documentos TinyDB proyectados | Tarjetas usan contacto/notas; evaluar `updated_at`, no excluir contacto sin alternativa | PARCIAL | 6 / P |
| 28 | `GET /api/suppliers/{supplier_id}`: detalle | Path | Modelo F, 200; documento TinyDB proyectado | Swagger/tests; F compatible, datos comerciales solo en alcance local/demo | YA | 6 / P |
| 29 | `PATCH /api/suppliers/{supplier_id}/rate`: tarifa | `SupplierRateUpdate`, path | Modelo F, 200; documento actualizado | Backoffice descarta cuerpo y recarga; valorar proyeccion menor o justificar F compatible | PARCIAL | 6 / P |
| 30 | `PATCH /api/suppliers/{supplier_id}/status`: estado | `SupplierStatusUpdate`, path | Modelo F, 200; documento actualizado | Backoffice descarta cuerpo y recarga; conservar semantica del timestamp | PARCIAL | 6 / P |
| 31 | `DELETE /api/suppliers/{supplier_id}`: borrar | Path | Dict D, 200; confirmacion TinyDB | No hay accion UI; Swagger/tests: D explicito, no 204 | SIN | 3 / P |

### Salud - 1 operacion

| # | Metodo y ruta / proposito | Entrada | Salida actual / origen | Consumidor y objetivo | Inicial | Etapa / final |
|---|---|---|---|---|---|---|
| 32 | `GET /health`: estado del servicio | Sin body | Dict H, 200; constantes | Smoke checks/Swagger: H estable y tipado | SIN | 3 / P |

Clasificacion inicial de este inventario: **14 YA, 13 PARCIAL, 4 SIN y 1 SIN/CSV**.
Las clasificaciones se actualizaron con consumidores y OpenAPI, no copiando la
tabla preliminar de la guia. Las 32 verificaciones finales siguen pendientes.

## Hallazgos, causas, impacto y decisiones

| ID | Causa / evidencia | Impacto | Mejora propuesta / etapa |
|---|---|---|---|
| F01 | Health/analisis retornan dict sin esquema explicito; DELETE infieren diccionario generico | OpenAPI no fija las claves esperadas; cambios accidentales de shape no quedan controlados por un modelo de campos | Modelos H/D/X explicitos, preservando respuestas/codigos; etapas 3 y 4 |
| F02 | Registro comparte U con gestion autorizada | Reenvia email, contrario al criterio oficial de registro; tipo del cliente liga casos distintos | R especifico y tipo del cliente actualizado; etapa 2 |
| F03 | Export usa `Response`, pero OpenAPI anuncia JSON | Clientes/documentacion no conocen el CSV ni su estructura real | Declarar `text/csv`, esquema texto/columnas y errores; etapa 4 |
| F04 | Listados reutilizan detalle sin decision escrita | Posible over-fetching; no hay medicion de bytes ni prueba de que todos los campos sobren | Inventariar campos efectivamente usados; separar solo con reduccion real, etapas 2/5/6 |
| F05 | Modelos P y movimientos incluyen IDs de relaciones/autor | IDs no justificados pueden revelar estructura innecesaria, pero quitarlos puede romper tipos/UI | Documentar uso y proyeccion; preservar autor del historial y decidir IDs restantes; etapas 2/7 |
| F06 | Historial lee `type`, `product_name`/`name`, `sku`; API publica `movement_type`, `asset_name`, `asset_sku`; `getOrders()` no adapta | Divergencia estatica del contrato: tipo/nombre/SKU pueden mostrarse vacios o incorrectos | Consumidor debe leer nombres canonicos de L; probar historial en etapa 7, sin renombrar API por comodidad |
| F07 | El handler de validacion cambia errores de incidentes a 400 y sanea errores de auth, mientras OpenAPI agrega 422 generico | Documentacion de errores puede no reflejar codigos/shape reales | Documentar respuestas por operacion y validar errores relevantes al trabajar cada familia |

Estos son hallazgos de contratos, no vulnerabilidades explotables confirmadas.
No se inspeccionaron datos reales ni se midieron tamanos/rendimiento.

### Relaciones, privacidad y compatibilidad

- Auth: separar almacenamiento `UserRecord` de U/R/M. No publicar hash, digest ni
  tokens de recuperacion. T contiene exclusivamente el token publico necesario.
- Registro/login/forgot/reset: no reenviar email. M puede incluir email propio.
  No imponer la misma restriccion indiscriminadamente al listado admin o al
  contacto de proveedores; justificar permisos/caso de uso.
- Perfil: M anida una proyeccion de contacto, no el documento completo. IDs de P
  requieren decision documentada; mantener contratos actuales hasta resolverla.
- Inventario: `asset_id` identifica el activo; L aplana nombre/SKU. `user_uuid`
  se genera actualmente como `str(current_user.id)`, no como un UUID real.
  Mantener la politica de acceso existente: GET de inventario publicos y escrituras
  autenticadas. Esta auditoria no autoriza cambiar permisos.
- Incidentes: descripcion libre puede contener PII, pero no se inspeccionaron
  valores para afirmarlo. La UI la muestra; no eliminar ni enmascarar sin decision.
  X/C solo agregados; resultado CSV global en memoria preservado, sin cambiar
  propiedad, almacenamiento o ciclo de vida.
- Proveedores: contacto y notas aparecen en tarjetas. Datos comerciales en
  local/demo; no crear un listado reducido que deje esas tarjetas incompletas.
- Mantener arrays vacios, null/omitido, filtros, transiciones y respuestas
  completas existentes salvo ajuste justificado y coordinado con clientes/tests.

### Entradas y errores a preservar/verificar

Los POST/PUT/PATCH JSON ya tienen modelos de entrada distintos de los de salida.
Los esquemas de escritura usan `extra="forbid"`; verificarlo contra requests en
sus etapas, no deducir validacion HTTP solo de la definicion. Analisis es multipart,
no debe convertirse a JSON para aparentar cumplir el requisito.

- Registro: solo email/password/contacto inicial; rol siempre `user`.
- Usuario: email/password editables por propietario/admin; rol/estado solo admin.
  IDs, hashes y timestamps no son entradas. `UserUpdate` rechaza null explicito.
- Perfil: actualizacion parcial; diferenciar omitido de null intencional.
- Incidentes: creacion acepta estado inicial segun regla actual; transicion recibe
  solo `status`. ID y timestamps server-managed. No cambiar el ciclo de vida.
- Inventario: stock/autor/ID/fecha server-managed; entrada y salida tienen
  modelos separados. `asset_id` es referencia escribible necesaria.
- Proveedores: ID/timestamp server-managed; tarifa y estado con modelos separados.

Errores actuales segun codigo (no ejecutados contra endpoints de negocio):

| Familia | Contratos que deben conservarse y comprobarse |
|---|---|
| Comunes | 500 generico sin stack trace; errores HTTP con `detail`. 401 en rutas autenticadas y cabecera Bearer donde corresponda |
| Auth | Login 401/415/422; me 401/404; forgot 422/503; reset 400/422/503; change 400/401/422/503. Mensajes de validacion saneados sin copiar inputs |
| Usuarios/perfiles | 401/403/404, 409 email duplicado, 422 de entrada; usuarios usan `{"detail": "Invalid user request"}`. Perfil preserva errores saneados y contacto nullable |
| Incidentes CRUD | 400 filtros/payload/transicion, 404 recurso, 500 almacenamiento; validacion puede incluir `detail` y `errors` con `field`/`message`, no 422 generico |
| Analisis/export | 400 formato/vacio/analisis, 413 limite 25 MiB, 401, 500; export 404 sin resultado. Validacion multipart de incidentes pasa por handler 400 |
| Inventario | 400 SKU duplicado/stock insuficiente, 404 activo, 422 validacion; escrituras 401; mantener errores de dominio |
| Proveedores | 401, 404, 422 entrada/filtros y 500 almacenamiento. Cambio de estado no actualiza el timestamp de tarifa |

### Decision pendiente sobre CSV

El README oficial pide literalmente `response_model` en cada endpoint y no
explica exportaciones no JSON. La guia local propone una excepcion tecnica:
documentar el CSV real en OpenAPI, sin fingir JSON ni aplicar un modelo Pydantic
al texto. Implementar esa documentacion en etapa 4 y **confirmar con el instructor
su aceptacion antes de declarar cumplida la entrega**. No marcar CSV aprobado
solo por escribir esta justificacion.

## Tablero de trabajo y publicacion

| Etapa | Alcance / condicion de cierre | Dependencias | Estado | Commit previsto / evidencia |
|---|---|---|---|---|
| 1 | Inventario, campos, consumidores, decisiones y plan; guia/memoria actualizadas | Ninguna | Completada (alcance documental) | `docs: establish serialization audit baseline`; OpenAPI 200, 32 operaciones; commit/push se verifican al publicar |
| 2 | Auth/usuarios/perfiles y tipo cliente registro; contratos/errores/permisos verificados | 1 | Pendiente | `feat(api): refine auth and user response contracts` |
| 3 | H y ambos D explicitos; codigos/shape compatibles | 1, 2 | Pendiente | `feat(api): type health and deletion responses` |
| 4 | X completo y C documentado; contenido/errores comprobados | 1, 3 | Pendiente | `feat(api): define analysis and CSV export contracts` |
| 5 | CRUD/resumen incidentes y campos de tabla justificados | 1, 4 | Pendiente | `feat(api): audit incident serialization contracts` |
| 6 | Proveedores sin romper tarjetas ni actualizaciones | 1, 5 | Pendiente | `feat(api): refine supplier serialization contracts` |
| 7 | Inventario/relaciones y alineacion del historial | 1, 6 | Pendiente | `feat(api): refine inventory serialization contracts` |
| 8 | Cobertura OpenAPI, suite completa, Swagger/UI y auditoria final/PR | 2, 3, 4, 5, 6, 7 | Pendiente | `docs: finalize serialization audit and verification` |

Las dependencias adicionales fijan el orden de trabajo acordado, no implican que
todos los modelos de una familia dependan tecnicamente de otra. Si una etapa solo
necesita justificacion y ninguna modificacion funcional, su commit sera `docs:`,
no se crearan cambios artificiales para conservar un mensaje `feat:`.

### Cierre obligatorio por etapa

1. Implementar solo el alcance actual. Si una decision cambia negocio/permisos,
   detener esa parte y consultar; no cambiar codigo para cerrar una casilla.
2. Ejecutar pruebas focalizadas existentes; actualizar contratos/tests afectados
   al implementar segun el alcance autorizado. Sin nueva suite/framework.
3. Actualizar este documento con estado original, cambios, evidencia y pendientes;
   actualizar memoria/README si cambia comportamiento o estado.
4. Revisar diff/staging, `git diff --check`, secretos/archivos generados y cambios ajenos.
5. Un commit y push por etapa cerrada; verificar hash local/remoto y arbol limpio.
   No se escribira el hash de un commit dentro de si mismo: la etapa siguiente
   registra el hash publicado anterior; `git log` conserva la trazabilidad inmediata.
6. Reportar cierre y detenerse hasta autorizacion de la siguiente etapa.

## Verificacion final pendiente

- [ ] Las 32 operaciones tienen contrato explicito adecuado; confirmar recuento
  nuevamente si cambia la superficie.
- [ ] Requests/respuestas y errores relevantes probados; campos sensibles ausentes.
- [ ] Listados y relaciones justificados frente al consumidor, no por intuicion.
- [ ] Todos los tests previos pasan y los contratos modificados quedan cubiertos.
- [ ] Al menos tres endpoints probados manualmente en `/docs`: flujo auth, listado
  y operacion modificada; registrar metodo/ruta, shape, fecha y resultado sin secretos.
- [ ] Export real CSV comprobado (media type, attachment, columnas y errores).
- [ ] Excepcion CSV aceptada para entrega o criterio pendiente explicitado.
- [ ] Consumidores afectados siguen funcionando, incluido historial inventario.
- [ ] Estados finales actualizados con evidencia, no solo presencia de un modelo.
- [ ] PR contra `main`: `feat: serialization audit and implementation`;
  URL compartida al instructor. No abrir PR final durante etapa 1.

Comando de suite completa para **etapa 8**, desde la raiz:

```powershell
uv run --locked --project services\api python -m unittest discover -s services\api\tests -v
```

No se ejecuta repetidamente la suite completa por cada cambio. Para etapas
intermedias se seleccionan modulos de tests relevantes con el runner existente.
No hay lint/typecheck/build Python propios declarados; si se modifican tipos del
tracker, usar sus checks existentes, no ejecutar checks frontend ajenos.

### Registro de evidencia

| Evidencia | Estado al cerrar la documentacion de etapa 1 |
|---|---|
| Base / fecha | `6d3d493b60cfd5b284ff1e2af25f602c54ed26a4`, 2026-11-02 |
| OpenAPI | TestClient sin lifespan, GET 200; 32 operaciones contrastadas con routers |
| Contratos actuales | 27 modelos explicitos; 2 DELETE inferidos; health/analisis sin esquema fijo; CSV documentado incorrectamente como JSON |
| Consumidores | Registro tracker descarta respuesta; tarjetas proveedores usan contacto/notas; incidentes usan descripcion; historial usa autor y alias divergentes |
| Validacion documental | Inventario numerado 1-32 coincide exactamente con OpenAPI; recuentos de clasificacion y enlaces locales comprobados; referencias desde guia/memoria/README y columnas de login verificadas |
| Pruebas de negocio / suite completa | No ejecutadas; pendientes de etapas de implementacion/cierre |
| Swagger interactivo / UI | No ejecutados; pendientes |
| Datos / dependencias | Sin datos reales, seeds, lectura de `.env*` ni instalaciones |
| Implementacion / PR | Etapas 2-8 pendientes; PR no abierta |
| Commit/push de etapa 1 | Verificacion al publicar; consultar `git log` y cierre de etapa, registrar hash en etapa 2 |
