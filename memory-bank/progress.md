# Progress

Última actualización: 2026-09-25

## Estado inicial observado

- Revisión documental de la etapa 1 completada para `ingenieria-ia.md`, `CONTEXT.md`, `SPEC.md` y README relevantes.
- Existe `uis/website` con landing y formulario; las rutas `/` y `/application` y sus recursos principales ya pasaron smoke test HTTP.
- Existe `uis/talent-pipeline-tracker` con especificación funcional propia.
- `uis/backoffice/` ya existe como panel estático con ruta `/`, README y estilos propios.
- `services/` contiene documentación de convenciones, pero no un backend implementado.
- La rama `feature/agent-memory-bank` estaba sincronizada con `origin` al iniciar la etapa 5; seguía presente la eliminación local de `INSTRUCCIONES_AGENTE_HITO_IA.md`.

## Trabajo completado

- Inventario documental y mapa inicial de entregables de la etapa 1.
- Creación del banco de memoria: `projectbrief.md`, `techContext.md` y este archivo.
- Etapa 3: creado `AGENTS.md` raíz, reglas de contexto y arquitectura en `.agents/rules/`, y skill de validación en `.agents/skills/validate-application-before-commit/`.
- Commits publicados en `feature/agent-memory-bank`: banco de memoria (`9a5ac91`), etapa 3 (`c52222b`), etapa 4 (`a699372`) y etapa 5 (`77f970b`).
- Etapa 4: añadido header/footer web reutilizable, navegación adaptable a móvil y límite HTML de 500 caracteres en comentarios.
- Corregido el comando de servidor: sin `-s`, el formulario se sirve en `/application`; el modo SPA redirigía a la landing.
- Corregidos los globs de Tailwind para que, ejecutado desde la raíz como indica el README, genere las utilidades del sitio y del componente compartido.
- Etapa 5: creado `uis/backoffice/` como vista interna diferenciada, con cifras aproximadas del briefing, líneas de negocio y etapas de talento de `SPEC.md`; no consume ni expone datos personales.
- Documentados en `uis/backoffice/README.md` el origen de los datos, el carácter no operativo del panel y el comando local.
- Commit de etapa 5 publicado en `feature/agent-memory-bank` (`77f970b`).
- Etapa 6: `npm run typecheck` y build Tailwind completados; JSON-LD parseado correctamente y rutas/recursos del website y backoffice comprobados por HTTP con respuesta 200.
- Smoke test del backoffice confirmó el resumen y que no renderiza campos de registros de candidatos.
- Commit de resultados de etapa 6 publicado en `feature/agent-memory-bank` (`59c3535`).
- Etapa 7: PR #3 abierta desde `feature/agent-memory-bank` hacia `main`.
- Generadas cuatro capturas con Playwright 1.50.1/Chromium para website y backoffice en 1440 × 900 y 390 × 844, en `docs/screenshots/`.
- Pruebas Playwright: website y backoffice sin overflow horizontal en 1440 y 390 px; formulario vacío mostró errores de nombre/política esperados; envío válido mostró éxito; no hubo errores JavaScript de página.
- PR #3 abierta hacia `main`: https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo-luis/pull/3.

## Decisiones

- `ingenieria-ia.md` define el alcance del hito.
- `CONTEXT.md` es la fuente para negocio y contenido; `SPEC.md` define el comportamiento del tracker.
- Mantener los entregables explícitos `uis/website` y `uis/backoffice`. Las aplicaciones existentes pueden aportar funcionalidad reutilizable, pero no eliminan automáticamente esos requisitos.
- Confirmar con Carmen Ruiz el claim «12 años de experiencia» antes de incluirlo en contenido nuevo.
- No añadir backend hasta justificar su necesidad.
- No incluir secretos ni datos personales reales de candidatos en documentación, mocks o capturas.

## Riesgos y pendientes

- Rama actual `feature/agent-memory-bank`, sincronizada con `origin` tras publicar las capturas (`8f190b3`); la anotación de PR está local.
- Permanece una eliminación local preexistente de `INSTRUCCIONES_AGENTE_HITO_IA.md`; no se incluyó en el commit y no debe descartarse sin autorización.
- La PR #3 está abierta contra `main`; su descripción incluye capturas desktop/móvil, validaciones y limitaciones.
- No se pudo inspeccionar `uis/website/assets/js/validation.js` porque Copilot lo marca como ignorado; se validó su comportamiento observable desde Chromium.
- El backoffice pasó un smoke test HTTP de `/` (200), contenido de contexto y carga del CSS; Playwright comprobó el viewport desktop/móvil sin overflow horizontal.
- Tailwind avisa que `caniuse-lite` está desactualizado; la compilación termina correctamente.
- El backoffice es estático y no declara scripts de test, lint, typecheck ni build; se validó con serving HTTP.

## Próximos pasos

1. Revisar checks/revisiones de la PR #3 y atender comentarios.
2. Entregar el enlace de la PR en el campus de 4Geeks.

## Hito 09 — Directorio de proveedores

Actualizado: 2026-10-13

- Etapa 1 completada: `base-dato-ligero.md` es la referencia vigente; `ingenieria-ia.md` era temporal y fue retirado intencionalmente.
- Etapa 2 completada: añadidos modelos Pydantic, TinyDB y `services/api/seed.py`; base local por defecto en `services/api/data/suppliers.json`, configurable con `NEXOVA_SUPPLIERS_DB_PATH` y excluida de Git.
- `uv run seed`, ejecutado desde `services/api`, insertó 15 registros en la primera ejecución y 0 en la segunda. La constante del seeder se comparó estructuralmente con los 15 registros del brief.
- Etapa 3 completada: router CRUD `/api/suppliers` con filtros combinados AND, generación server-side de `updated_at`, validación Pydantic, respuestas `404`/`422` y eliminación.
- Suite completa del API: 24 tests pasan, incluidos los tests previos de incidencias y los nuevos casos CRUD de proveedores.
- Etapa 4 completada: sección Proveedores en `uis/backoffice` con filtros, alta, cambios de tarifa/estado, feedback de API, estados y resaltado de renovaciones; actualizados README, navegación y aviso de uso local/demo.
- Verificación UI: Playwright 1.50.1 en Chromium probó escritorio 1440 × 900 y móvil 390 × 844 sin overflow, aplicó filtros y destacó una renovación sintética; alta, actualización de tarifa y suspensión pasaron contra el API real con registros de prueba eliminados. Cero errores de página.
- Etapa 5 completada: `uv run seed` dio 15 inserciones y 0 en la segunda ejecución sobre DB temporal; tras reiniciar Uvicorn, permanecieron los 15 registros con el mismo hash. Capturas añadidas a `docs/screenshots/`: seed 15/0, filtro real Swagger `200 []` y directorio filtrado desktop/móvil con fixture sintético.
- El alcance permanece local/demo; no desplegar datos comerciales del directorio.

## AUTH-01 — Autenticación y restricción de rutas

Actualizado: 2026-10-13

### Etapa 1 — Base auditada y dependencias

- Creada `feature/auth-api` desde `main` sincronizada con `origin/main`, commit base `12ef190`. Existían cambios de formato en `services/api/README.md` y `uis/backoffice/README.md`; se conservan y quedan fuera del commit de esta etapa.
- Contrastado íntegramente el README oficial en español de `ai-eng-user-authentication-api` con `autenticacion.md`, sin discrepancias funcionales. Las menciones antiguas a `ingenieria-ia.md` no requieren recrearlo: su retirada intencional ya está documentada.
- Instaladas dependencias con `uv add --project services/api "python-jose[cryptography]" "libpass[bcrypt]"`; actualizados el manifiesto principal y su lockfile, y sincronizado `requirements.txt`. Versiones probadas: `python-jose` 3.5.0, `libpass` 1.9.3 y `bcrypt` 5.0.0.
- Documentados en el README de la API los seis entregables, la matriz de endpoints/permisos, la configuración prevista, los límites de TinyDB y el procedimiento de cierre por etapa. No se crearon endpoints de auth, bases de credenciales ni restricciones todavía.
- Decisiones confirmadas: registro público `user`, primer admin mediante comando local seguro, listado de usuarios solo admin, credenciales propietario/admin, perfiles `/me` propios y login JSON/OAuth2 compatible con Swagger. Las ocho operaciones existentes serán compartidas por usuarios autenticados; el resultado de incidencias permanece global en memoria.
- Configuración futura: `NEXOVA_AUTH_DB_PATH`, `JWT_SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES`; sin valores secretos documentados. `git check-ignore services/api/data/auth.json` confirmó que la futura base está excluida. No se leyó ni modificó ningún `.env`.

### Verificación de etapa 1

- Suite basal: `uv run --locked --project services/api python -m unittest discover -s services/api/tests -v` → 24 tests satisfactorios.
- Smoke de dependencias en el mismo entorno: imports, hash bcrypt, verificación positiva/negativa de contraseña y encode/decode JWT HS256 con expiración → satisfactorio. Valores sintéticos efímeros, sin imprimir contraseña, hash, secreto ni token.
- Suite después de instalar/sincronizar dependencias: mismo comando → 24 tests satisfactorios.
- Comparación de `pyproject.toml` y `requirements.txt` con TOML y colecciones de la biblioteca estándar → declaraciones idénticas. Un primer script auxiliar falló por no disponer de `packaging`; se corrigió sin instalar dependencias adicionales y la comprobación pasó.
- `uv lock --check --project services/api` → satisfactorio; revisión estructurada del lockfile confirmó que conserva todas las versiones previas y que sus URLs no incluyen credenciales.
- Smoke HTTP con `TestClient` → `/health`, `/docs` y `/openapi.json` responden `200`; `/health` mantiene `status=ok`.
- Avisos no bloqueantes: deprecación preexistente de Starlette/TestClient sobre `httpx` y fallback de hardlinks a copia en la instalación con `uv`. No se modifican dependencias ajenas para corregirlos.
- Sin lint/typecheck/build Python declarados; no se ejecutan checks del frontend ajenos al cambio. Estos resultados no implican que la autenticación del hito ya esté implementada.

### Próximas etapas

1. Etapa 2: usuarios/perfiles TinyDB y servicios internos, bcrypt y pruebas de ciclo de vida; todavía sin endpoints nuevos.
2. Etapa 3: configuración JWT, login, dependencia, `/auth/me` y comando local de admin.
3. Etapa 4: CRUD `/users` y `/profiles/me` con autorización desde su publicación.
4. Etapa 5: proteger las ocho rutas existentes y conservar sus regresiones con tokens reales.
5. Etapa 6: suite completa, verificación manual `/docs`, evidencias sin secretos y PR hacia `main`.

La integración de autenticación en frontend queda fuera de este hito. Sus llamadas sin token fallarán a partir de la etapa 5; registrar esta limitación en la entrega.

### Etapa 2 — Usuarios, perfiles y bcrypt internos

- Implementados `auth_models.py`, `passwords.py`, `auth_storage.py` y `user_service.py`; añadidos dos archivos de tests siguiendo unittest y bases temporales. Todavía sin endpoints de usuarios/perfiles, login, JWT ni restricciones de rutas.
- User y Profile viven solo en TinyDB y separados de proveedores. User contiene email, bcrypt, estado activo, rol y creación UTC; nombre/teléfono/dirección residen en Profile. El ID deriva del doc_id de TinyDB.
- Registro público interno siempre `user`, con rechazo explícito de roles privilegiados. Enum acepta únicamente admin/manager/user. Email validado, normalizado y único; perfil creado aun sin datos opcionales; actualizaciones parciales y eliminación coordinada.
- Contraseñas hasheadas al crear/actualizar, verificadas con libpass bcrypt. Mínimo 8 caracteres, máximo 72 bytes UTF-8, sin bytes nulos ni truncamiento silencioso. Entradas/hash usan SecretStr y quedan fuera de repr/serialización; respuesta UserResponse no contiene hash.
- Escritura coordinada mediante snapshot TinyDB MemoryStorage y reemplazo del archivo después de completar la operación; bloqueo local, temporal owner-only, flush/fsync y limpieza ante fallos ordinarios. La tabla auth_metadata conserva contadores para no reutilizar IDs tras borrar/reabrir.
- Limitación documentada: un proceso/worker, sin escrituras externas simultáneas ni garantías multiworker o completas de recuperación ante caídas. El servicio de actualización es interno y privilegiado; permisos HTTP se aplicarán en la etapa 4.
- Las pruebas usaron solo datos sintéticos y directorios temporales; no se creó una base real, no se leyó ningún `.env` y no se alteraron routers, frontend ni dependencias. Cambios previos de formato en README API/backoffice conservados y excluidos del commit.

### Verificación de etapa 2

- `uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_auth_models.py -v` → 10 tests satisfactorios. El primer pase detectó email null generando AttributeError; se corrigió para devolver un error de validación y la misma prueba pasó.
- `uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_user_service.py -v` → 17 tests satisfactorios, incluidos duplicados concurrentes locales, perfil fallido, eliminación fallida y reemplazo de archivo fallido con preservación del snapshot original.
- `uv run --locked --project services/api python -m unittest discover -s services/api/tests -v` → 51 tests satisfactorios: 27 nuevos y 24 previos sin regresiones.
- Diagnósticos de los seis archivos Python nuevos → sin errores. Persiste el aviso preexistente de Starlette/TestClient sobre httpx; no se cambian dependencias ajenas para corregirlo.

Siguiente etapa: configuración JWT por entorno, login JSON/OAuth2, get_current_user, `/auth/me` y comando local seguro para el primer admin. La autorización y los endpoints CRUD se implementarán después, no se exponen servicios sin proteger.

### Etapa 3 — JWT, login y comando local de admin

- Implementados security.py, auth_dependencies.py, router auth y bootstrap_admin.py. main.py incorpora lifespan que valida entorno antes del arranque y registra solo POST `/auth/login` y GET `/auth/me`; no se adelantan CRUD de usuarios/perfiles ni restricciones operativas.
- Configuración obligatoria JWT_SECRET_KEY (mínimo 32 bytes y no vacía) y ACCESS_TOKEN_EXPIRE_MINUTES (entero positivo representable); sin claves por defecto, valores en logs ni lectura/escritura de `.env`. Cambios de configuración requieren reiniciar la API.
- Tokens HS256 con id TinyDB entero, sub equivalente, iat y exp. get_current_user requiere expiración y firma válidas y recupera usuario/estado/rol actuales de TinyDB. Usuario eliminado/inactivo, firma/algoritmo/claims inválidos o token ausente → 401 con WWW-Authenticate Bearer.
- Login JSON email/password y formulario OAuth2 username=email/password comparten verificación bcrypt y respuesta access_token/token_type. Auth/me devuelve solo email/rol/perfil vinculado. Payload inválido se responde con 422 genérico, sin eco de contraseña; contenido no soportado 415; credenciales inválidas/inactivas/inexistentes 401 genérico.
- Comando promote-admin registrado en pyproject y empaquetado junto a seed; exige base existente explícita, ID positivo y --confirm. Promueve usuario activo existente, idempotente, conserva credenciales/perfil y no imprime PII/hash/password. Debe ejecutarse con la API detenida; solo se probó con bases temporales sintéticas.
- Verificación de passwords ajustada para rechazar también Unicode no codificable sin provocar error interno. Sin dependencias nuevas ni cambios al lockfile. Los cambios de formato preexistentes de los README siguen fuera del commit.

### Verificación de etapa 3

- `uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_security.py -v` → 9 tests satisfactorios: configuración, expiración, firma/algoritmo/claims y usuario vigente.
- `uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_auth_api.py -v` → 13 tests satisfactorios: startup válido/inválido, JSON/form, Bearer, errores genéricos y OpenAPI compatible con Swagger.
- Un test levanta Uvicorn real en puerto local efímero, comprueba health/docs, auth/me sin token, login y auth/me con Bearer; cierra el proceso. Cuenta, claves, tokens y base efímeros/sintéticos, sin imprimir secretos.
- `uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_bootstrap_admin.py -v` → 7 tests satisfactorios: idempotencia, confirmación, casos ausentes/inactivos, errores de disco y comando instalado desde otro directorio.
- `uv run --locked --project services/api python -m unittest discover -s services/api/tests` → 80 tests satisfactorios, incluidos los 51 anteriores; checks focales de modelos/passwords también pasan.
- `uv lock --check --project services/api`, diagnósticos y revisión de diff → satisfactorios. Persisten avisos no bloqueantes previos Starlette/httpx y hardlink/copia uv; no se alteran dependencias ajenas.
- Verificación manual completa en navegador de registro/login/Authorize queda para etapa 6; el registro HTTP aún no existe. No se deja servidor persistente y no se creó una base real de credenciales ni se conectaron servicios externos.

Etapa 4 implementó `/users` y `/profiles/me` con autorización propietario/admin y rechazo de cambios de rol/estado no autorizados. Proveedores/incidencias siguen públicos hasta la etapa 5; el backend requiere entorno JWT válido para arrancar.

### Etapa 4 — CRUD HTTP y autorización de usuarios/perfiles

- Añadidos `UserRegistration`, separado del modelo interno `UserCreate` para que el registro público no acepte rol ni campos de servidor. `POST /users` crea `user` con su perfil inicial; errores de registro no revelan payload ni credenciales.
- Registrados routers `users.py` y `profiles.py`: endpoints `/users`, `/users/{user_id}` y `/profiles/me`. Todo salvo registro usa `get_current_user` desde su publicación.
- `GET /users` solo admin. Operaciones por ID autorizan propietario/admin antes de acceder a TinyDB; el actor no admin recibe 403 ante IDs ajenos sin revelar existencia, y admin recibe 404 para ID inexistente. El rol manager no equivale a admin.
- Owner puede leer/actualizar email/password/eliminar su cuenta; admin puede además cambiar role/is_active en PUT sobre cualquier usuario. Cambios password siguen usando hash. Duplicado email devuelve 409. Alta y baja coordinadas con el perfil.
- Perfiles solo en `/profiles/me`; admin también solo modifica su propio perfil por esta ruta. `ProfileUpdate` no acepta campos extra/user_id; omisión conserva valor y null lo limpia. `/auth/me` continúa devolviendo el perfil actual.
- Handler FastAPI sanea `RequestValidationError` de `/users` y `/users/*` a detalle genérico para evitar que payloads inválidos reflejen contraseñas, hashes u otros datos enviados; el contrato de validación de routers preexistentes no cambia.

### Verificación de etapa 4

- `uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_users_api.py -v` → 16 tests HTTP satisfactorios con usuarios sintéticos registrados por HTTP y tokens emitidos por login real.
- Casos: registro default/perfil, escalación de rol, input sensible sanitizado, duplicados 409, todas las rutas protegidas sin token 401, listado user/manager 403 y admin permitido sin hashes, ownership 403, owner actualiza credenciales, admin modifica roles/estado, perfil aislado, cascada, 404 tras autorización y schema OpenAPI.
- La primera ejecución de tests detectó dos expectativas incorrectas, no defectos del código: `too-short` tiene 9 caracteres y cumple política; ID ajeno debe ocultarse con 403 al owner, mientras que ID inexistente devuelve 404 al admin. Las expectativas se corrigieron y suite focal pasa.
- La eliminación con perfil ausente responde 404 sin borrar parcialmente el usuario.
- `uv run --locked --project services/api python -m unittest discover -s services/api/tests` → 96 tests satisfactorios (80 previos + 16), sin regresiones de incidencias/proveedores. Diagnósticos funcionales por suite y lockfile correctos.
- Se conservaron sin commit las ediciones previas de README (`services/api` y backoffice). Cambios de documentación AUTH se preparan selectivamente; no hubo PII real, secretos, DB persistente ni dependencia nueva.

Etapa 5 protegió las ocho operaciones existentes de proveedores e incidencias con `get_current_user`; los fixtures usan login/token reales y los contratos funcionales se mantienen. El frontend no se integra hasta la etapa 6.

### Etapa 5 — Protección de proveedores e incidencias

- Aplicada dependencia router-level `get_current_user` a los seis endpoints de `/api/suppliers` y los dos de `/api/incidents`. Recursos siguen compartidos entre usuarios autenticados; no se añade propietario ni matriz por rol.
- Adaptados los tests de ambos routers para crear usuarios sintéticos mediante `POST /users`, obtener Bearer por `/auth/login`, y usar `TestClient` como context manager con variables JWT y TinyDB temporales.
- Añadidas matrices de `401` con autorización ausente o token malformado para las ocho operaciones y comprobaciones OpenAPI de seguridad. `/health` sigue pública.
- Una prueba inicial encontró que varios TestClient anidados compartían `app.state.jwt_settings` y el lifespan eliminaba el atributo al cerrar el cliente interior. Se corrigió `main.py` para restaurar la configuración previa al salir de cada lifespan; las suites focales pasan después del ajuste.
- Se conservan filtros AND, creación 201, respuestas 404/422, timestamp rate/status, cambios TinyDB, validación/análisis de CSV, agregados y exportación. El resultado de incidencias sigue siendo global y en memoria.

### Verificación de etapa 5

- `uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_suppliers_api.py` → 11 tests satisfactorios, funcionalidad existente con login real y 401 ausente/inválido.
- `uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_api.py` → 8 tests satisfactorios, fixture CSV, comportamiento de incidentes y 401 ausente/inválido.
- `uv run --locked --project services/api python -m unittest discover -s services/api/tests` → 100 tests satisfactorios, incluida la cobertura completa de etapas 1–4.
- `uv lock --check --project services/api` y `git diff --check` satisfactorios; sin dependencias nuevas. Diagnósticos Pylance aún muestran imports FastAPI sin resolver porque el intérprete global `/usr/local/python/3.12.1` seleccionado no tiene los paquetes; `services/api/.venv` sí y `uv run` pasa. No se cambió configuración global del editor.
- Se conservaron fuera del commit cambios de formato previos en `services/api/README.md` y `uis/backoffice/README.md`. Solo datos sintéticos/autorizados y TinyDB temporales; no secretos, bases reales ni PII nueva.

### Etapa 6 — Aceptación y entrega

- Ejecutado el flujo contra un proceso Uvicorn real en puerto local efímero; se detuvo al finalizar. Variables JWT, TinyDBs y usuarios fueron sintéticos/temporales; no se leyó ni escribió `.env` y no se usó PII real.
- Smoke `/docs`, `/openapi.json` y `/health`; validado OpenAPI Bearer en las seis operaciones supplier y dos incidents. Registro default user/perfil, rechazo de escalación role, login JSON y OAuth2 form, `/auth/me`, `/profiles/me`, 401 por token malformado/expirado y 403 al listar como no admin.
- Con Bearer válido, smoke supplier create/list/read/rate/status/delete y análisis/export de una fila CSV sintética válida. Sin token, supplier POST/GET e incident POST/GET devuelven 401. Hash bcrypt persiste; contraseña plaintext ausente de TinyDB/respuestas; email sintético ausente del export.
- `uv run --locked --project services/api python -m unittest discover -s services/api/tests` → 100 tests satisfactorios. `uv lock --check --project services/api` y `git diff --check` satisfactorios. Aviso conocido: Pylance selecciona interpreter global sin FastAPI, mientras `services/api/.venv` y `uv run` pasan; no modificar settings globales.
- Preparar commit/push de documentación de etapa 6 con staging selectivo; preservar las ediciones de formatter anteriores en README API/backoffice. Abrir PR desde `feature/auth-api` hacia `main` con matriz de rutas y evidencia.
- El backoffice no envía Bearer todavía; su integración frontend queda como follow-up separado. Hasta entonces, llamadas a rutas protegidas responden 401.

## AUTH-02 — Frontend

### Etapa 2 — Cliente Nexova y sesión

- Rama `feature/auth-frontend`, basada en `main` limpia en `df5d034`.
- Añadidos tipos de registro, login, token, usuario actual y perfil en `uis/talent-pipeline-tracker/types/auth.ts`.
- Añadido `lib/nexova-api.ts` con origen separado `NEXT_PUBLIC_NEXOVA_API_URL`; `NEXT_PUBLIC_API_URL` permanece exclusivo para la API externa de candidatos. Solo las llamadas protegidas adjuntan `Authorization: Bearer`; solo un `401` protegido o la ausencia local de token limpia sesión y notifica navegación a `/login`.
- `NexovaSessionNavigation` escucha la expiración y usa `router.replace`; login y registro son públicos. La sesión se guarda en `localStorage` únicamente desde el navegador.
- Todavía no existen las páginas `/login`, `/register`, `/account/profile` ni el guard de las vistas privadas; pertenecen a etapas posteriores. La UI del tracker no protege los datos servidos por la API externa 4Geeks.
- `npm run lint`, `npm run build` y `git diff --check` pasan. Build advierte que Next infiere raíz Turbopack ante los lockfiles de raíz y tracker. No hay suite de tests del frontend declarada.

### Etapa 3 — Login, registro y logout

- Añadidas las rutas `/login` y `/register` con un formulario compartido, validación nativa de email/contraseña, errores accesibles y mensajes de API saneados. El formulario de registro envía los campos opcionales `name`, `phone` y `address` admitidos por la API.
- El registro ejecuta `POST /users` seguido de `POST /auth/login`; guarda `access_token` solo cuando el login también termina correctamente. Si el alta se completa pero falla el login, informa al usuario y no declara sesión.
- Añadido logout visible en la lista de candidatos: elimina el token y el manejador global navega mediante `router.replace("/login")`.
- Verificación: lint/build y diagnósticos sin errores; rutas HTTP `/login` y `/register` responden 200 y renderizan email/contraseña. Con API Uvicorn local aislada, datos de prueba efímeros y email sintético `example.com`, pasaron registro 201, login 200, `/auth/me` con Bearer 200, login inválido 401 y CORS preflight autorizado. Una primera prueba usó `.test` y recibió 422 de validación; al cambiar a `example.com` el recorrido pasó. No se usaron cuentas reales.
- No hay Playwright/Puppeteer instalado; no se automatizó interacción visual. Permanecen pendientes el guard de páginas, perfil y aceptación manual. Los dos servicios locales actuales son de desarrollo/prueba y la base auth del API se elimina al detener el proceso.

### Etapa 4 — Guard de vistas privadas

- Añadido `NexovaAuthGuard` en el layout raíz. `/login` y `/register` siguen públicas; `/`, `/candidates/*` y `/account/profile` requieren token local y validación exitosa de `GET /auth/me` antes de renderizar sus children.
- Sin token, navega a `/login`. Token rechazado limpia sesión mediante el cliente central y redirige. Fallos de red/API muestran error y botón de reintento sin borrar token; las vistas permanecen ocultas durante la comprobación.
- `npm run lint` y `npm run build` pasan. Un chequeo HTTP del HTML generado comprobó `/` y `/candidates/1` con loader y sin contenido de la vista, y `/login`/`/register` accesibles con sus formularios. El primer detector de strings incluyó el título en `<title>`; inspección puntual confirmó que no era contenido de candidatos.
- Sigue sin Playwright/Puppeteer, por lo que la navegación client-side no tuvo interacción automatizada en browser. El backend/API temporal no constituye autorización para datos de la API externa de Tracker; el guard protege la UI según el alcance acordado.

### Etapa 5 — Perfil de cuenta

- Añadida `/account/profile`, protegida por el guard global y enlazada desde la lista. Carga email, name, phone y address reales de `GET /auth/me`; muestra formulario solo después de cargar correctamente.
- La edición usa `PUT /profiles/me`, con Bearer vía el cliente común. Se añadieron estados de carga, error recuperable, guardado y confirmación; campos vacíos se envían como null para limpiarlos.
- Verificación: `npm run lint` y `npm run build` pasan, diagnósticos sin errores. Smoke sintético sobre API efímera: registro 201, `GET /auth/me` 200, `PUT /profiles/me` 200 y lectura posterior confirma persistencia. `/account/profile` sin sesión devuelve HTTP 200 con loader y no renderiza el perfil.
- La prueba usa base TinyDB temporal y usuario sintético, eliminados al detener Uvicorn. No hay Playwright/Puppeteer para interacción visual automatizada; build avisa sobre lockfiles múltiples al inferir raíz Turbopack.

### Etapa 6 — Aceptación y cierre documental

- Actualizado `autenticacion-frontend.md`: corregidos los endpoints de auth (ya presentes), los nombres de respuesta (`access_token`), la variable Nexova separada y el alcance acordado. Se anotan los límites de autorización de candidatos, la verificación ejecutada y lo que sigue pendiente; no se cambiaron `CONTEXT.md` ni `SPEC.md`.
- Actualizado el README del tracker con configuración `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_NEXOVA_API_URL`, rutas públicas/privadas, límite de seguridad y comandos de validación.
- `npm run lint`, `npm run build`, `npm run typecheck` raíz y `git diff --check` pasan. Next informa la advertencia conocida de varios lockfiles/raíz Turbopack inferida.
- Smoke final de API con usuario sintético: `/auth/me` anónimo 401, registro 201, login 200, `/auth/me` Bearer 200, `PUT /profiles/me` 200, persistencia confirmada, listado no-admin 403 y login inválido 401. Token no impreso. Bases y cuentas en el proceso temporal.
- Website estático sin cambios: `/`, `/index.html`, `/application` y `/application.html` respondieron 200 sin redirección a login. Tracker respondió 200 para `/login` y `/account/profile`; el perfil privado mostró loader sin sesión.
- No se ejecutó interacción automatizada en navegador (no hay Playwright/Puppeteer instalado). La URL de despliegue y la PR no se verificaron/abrieron. Crear PR queda pendiente de solicitud explícita; rama feature ya publicada.

## AUTH-03 — Recuperación y cambio de contraseña

### Etapa 1 — Base, contratos y control

Actualizado: 2026-10-18. **LISTO PARA REVISIÓN**, pendiente de aprobación del usuario antes de commit y push. No avanzar a etapa 2 automáticamente.

- Fuente actual: `restablecimiento-contrasena.md`; se releyó íntegramente el README oficial en español de `ai-eng-user-authentication-restore`. Coinciden rutas, expiración, uso único, proveedores y entrega; se admite token aleatorio persistido. Se mantienen intactos los criterios de aceptación.
- Al iniciar, `feature/password-reset` ya existía, limpia y sincronizada con `origin/feature/password-reset` en `65f4656`. Tras fetch, `origin/main` en `78d8678` es ancestro e incluye AUTH-01/02. Los dos commits anteriores de la feature contienen requisitos y eliminación documental; no se recreó la rama ni se restauró contenido eliminado.
- Corregido el contexto técnico de la guía: tracker ya tiene login, register, perfil, cliente Nexova separado y guard. Nuevas pantallas allí, sin modificar website/backoffice, `CONTEXT.md` o `SPEC.md`.
- Acordados siete cierres: preparación; dominio de tokens; API/Resend; cliente/guard; recovery público; cambio autenticado; aceptación real/PR. El tablero en la guía distingue En revisión de Publicada y requiere evidencia, aprobación, commit selectivo y push verificado por etapa.
- Resend seleccionado; variables previstas (aún no implementadas/configuradas): `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `NEXOVA_FRONTEND_URL`, `PASSWORD_RESET_EXPIRE_MINUTES` (default 30, rango 15–60). No se leyó ni modificó `.env*`, ni se conectó proveedor externo.
- Token opaco aleatorio de 32 bytes, digest SHA-256 persistido y consumo/cambio coordinados con almacenamiento actual single-worker. Invalidar pendientes al emitir otro o cambiar credenciales/estado/eliminar cuenta; conservar contrato JWT stateless sin nueva revocación de sesiones.
- Usuario aceptó envío en segundo plano local/demo sin cola durable: 200 significa solicitud aceptada, no entrega. Respuesta independiente de cuenta; fallo previo común es error operativo, fallo tardío del proveedor se registra saneado. Reinicios pueden perder tareas; recepción real sigue obligatoria para aceptación.
- Baseline ejecutado: `uv run --locked --project services/api python -m unittest discover -s services/api/tests` → **100 tests OK**; `npm --prefix uis/talent-pipeline-tracker run lint` y `run build` → **correctos**, incluyendo TypeScript de Next. `git diff --check` correcto. Los unit tests existentes usan datos temporales/sintéticos; no se añadió código.
- Advertencias conocidas no corregidas: Starlette/httpx y varios lockfiles/raíz Turbopack. Next build carga `.env.local` automáticamente sin inspección manual ni impresión de valores. Los enlaces nuevos tienen destino; el README API mantiene enlace histórico preexistente a `autenticacion.md`, ya eliminado, fuera de este cambio.
- La instrucción global de 4Geeks está excluida por Copilot; se siguieron instrucciones/reglas/skill de validación locales. `ingenieria-ia.md` fue retirado intencionalmente, según techContext. No se ejecutó navegador ni prueba de email: AUTH-03 todavía no existe.
- La comprobación final detectó que `services/api/.env` no estaba ignorado. Se añadieron reglas raíz `.env`, `.env.*` y excepción `!.env.example`. `git check-ignore --no-index --verbose` confirma exclusiones y excepción de plantilla API; no se leyó ni creó ningún archivo de entorno. Reglas anidadas pueden ser más estrictas y deben revisarse antes de crear una plantilla.
- Archivos propuestos para este cierre: `.gitignore`, guía de restablecimiento, README API, `memory-bank/progress.md` y `memory-bank/techContext.md`. Mensaje propuesto: `docs(auth): define AUTH-03 stages and contracts`. Sin staging, commit, push ni PR en esta etapa hasta aprobación.

### Publicación de etapa 1 y etapa 2 — Dominio interno

Actualizado: 2026-10-18. Etapa 1 aprobada/publicada en `0ac5d4f`; push verificado y árbol limpio. Etapa 2 **LISTO PARA REVISIÓN**, sin staging/commit/push ni avance a etapa 3 hasta aprobación.

- Implementados `PasswordResetRecord` y `password_reset_service.py` con `issue_password_reset_token`, `reset_password` y `change_password`. Solo capa interna; no endpoints, emails ni cambios frontend.
- Token opaco de 32 bytes aleatorios, SHA-256 persistido en `password_reset_tokens` junto a user_id/vencimiento UTC, una fila por usuario. `SecretStr` oculta token/digest de repr y serialización normal. Emisión default 30 minutos, enteros 15–60; normaliza email, no emite para cuenta desconocida/inactiva, reemplaza anteriores y limpia expirados.
- Digest comparado con `hmac.compare_digest`. Consumo, verificación de usuario activo, hash/cambio e invalidación en un único snapshot bajo lock. El cambio con contraseña actual la verifica dentro de esa misma operación, sin ventana entre verificación y escritura. Sin garantías multiworker ni nueva revocación JWT.
- Helper de invalidación en auth_storage permite a update_user y delete_user invalidar resets sin ciclos de imports ni commits separados. Password/email/desactivación/borrado invalidan solo los propios; rol/perfil preservan. Rollback de archivo también preserva enlace previo válido.
- Cuatro pruebas iniciales de atomicidad/concurrencia pasaron antes de ampliar cobertura. Suite focal final repetida: 23 tests reset + 21 user_service OK; suite backend total 127 OK (27 nuevos sobre baseline100). Pruebas de reloj controlado, caducidad exacta, límites 15/60, entradas alteradas, reemplazo/limpieza/reapertura, cuentas inactivas/borradas, dos reset y dos cambios concurrentes, aislamiento, fallos de persistencia y política UTF-8.
- Diagnósticos de los seis archivos Python sin errores. `uv lock --check --project services/api` y `git diff --check` correctos; aviso Starlette/httpx conocido. No dependencias nuevas, configuración externa, .env ni datos reales. No lint/build frontend porque no hay cambios en esa aplicación.
- Tablero de la guía registra etapa1 Publicada con SHA/push y etapa2 En revisión; criterios de endpoints/email/UI siguen sin marcar. README API separa dominio implementado de contratos HTTP/config pendientes. Mensaje propuesto: `feat(auth): add single-use password reset tokens`.

### Publicación de etapa 2 y etapa 3 — API y Resend

Actualizado: 2026-10-18. Etapa 2 aprobada/publicada en `1997bce`, push y árbol limpio verificados. Etapa 3 **LISTO PARA REVISIÓN**, sin staging/commit/push ni avance a frontend hasta aprobación.

- Router auth implementa forgot/reset/change usando el dominio de etapa 2. Nuevos esquemas `ForgotPasswordRequest`, `ResetPasswordRequest`, `ChangePasswordRequest` y `AuthActionResponse`; `SecretStr` para inputs sensibles. main.py sanea validaciones solo en nuevas rutas: token ausente/nulo/no textual en reset devuelve 400; demás payload inválido, 422 sin eco.
- Forgot valida configuración común por solicitud y acepta `BackgroundTasks`; búsqueda, emisión y envío ocurren después del cuerpo público, comprobado mediante ASGI. Existente/desconocido/inactivo reciben el mismo 200; configuración inválida o fallo al aceptar tarea, 503 común. Error posterior se registra como mensaje fijo sin traceback, destinatario o secretos; no cambia la respuesta.
- Reset valida token y cambia contraseña de forma coordinada: inválido/expirado/usado devuelve 400, contraseña inválida 422, fallo de persistencia 503 sin consumir ni cambiar. Change requiere Bearer y ID de sesión: contraseña actual incorrecta 400, autenticación inválida 401, ID extra 422, persistencia fallida 503. Revalida la cuenta y no añade revocación JWT.
- email_service usa httpx existente con POST a Resend /emails, clave en cabecera, texto plano y enlace al origen configurado. Timeout de 10 segundos por fase; redirecciones, proxy de entorno y reintentos desactivados. `EmailDeliveryError` genérico sin cuerpo crudo del proveedor. Sin envío real ni red externa en tests.
- Configuración leída por forgot, no al arrancar ni desde .env: `RESEND_API_KEY` ASCII imprimible sin espacios; `RESEND_FROM_EMAIL` email simple autorizado; `NEXOVA_FRONTEND_URL` origen HTTPS sin credenciales/ruta/query/fragment ni puerto 0 (HTTP solo en loopback); `PASSWORD_RESET_EXPIRE_MINUTES` entero 15–60, default 30. Su ausencia no rompe login ni reset/change.
- Primeros 5 tests correo y 5 HTTP pasaron; ampliación: 5 email + 23 HTTP OK y suite total 155 OK (28 nuevos sobre 127). Cubren enlace/payload, timeout/proveedor fallido, configuración, no enumeración, orden de respuesta, validación sin secretos, JWT/reset cruzados, permisos, concurrencia HTTP y rollback. Se corrigió un caso de prueba porque os.environ no permite byte nulo; se usa un control representable para validar rechazo de claves.
- Diagnósticos de 6 archivos Python sin errores; `uv lock --check` y `git diff --check` correctos. Dependencias sin cambios y aviso Starlette/httpx conocido. Sin frontend ni navegador: quedan etapas 4–7 y recepción real obligatoria con configuración autorizada. BackgroundTasks no es durable ni garantiza reintentos.
- Tablero: etapa 2 Publicada en `1997bce`, etapa 3 En revisión con 155 tests; guía/README documentan contrato actual y límites. Mensaje propuesto: `feat(auth): expose password recovery and change endpoints`.

### Publicación de etapa 3 y etapa 4 — Cliente y acceso frontend

Actualizado: 2026-10-18. Etapa 3 aprobada/publicada en `a4429d2`, push y árbol limpio verificados. Etapa 4 **LISTO PARA REVISIÓN**; no staging/commit/push ni avance a nuevas pantallas hasta aprobación.

- Añadidos tres inputs y `NexovaAuthActionResponse` en types/auth.ts, más `requestNexovaPasswordReset`, `resetNexovaPassword` y `changeNexovaPassword` al cliente Nexova. Reutilizan request<T>, origen separado y errores: recovery público sin Bearer ni efecto sobre sesión; cambio requiere Bearer, solo 401 protegido cierra sesión.
- Nueva política `lib/nexova-auth-routes.ts`, compartida por guard/listener, evita duplicar rutas públicas. Login/register/forgot/reset públicos; account/change-password explícitamente protegido junto a las vistas existentes. El listener ignora expiración en vistas públicas y conserva redirección privada.
- Sin contraseñas/tokens de reset en localStorage/URL/logs; inputs solo JSON. El reset exitoso y navegación/limpieza de sesión previa se implementarán en la futura pantalla de etapa 5, no en el SDK.
- Lint focal y completo, build con TypeScript y diagnósticos de cinco archivos correctos. Conocida advertencia de lockfiles múltiples; build/dev carga automáticamente .env.local sin inspección manual ni impresión de contenido. Documentación instalada useRouter/usePathname consultada; sin nuevas dependencias.
- Prueba en memoria del SDK y ocho rutas/listener con hooks simulados: URL, payload, Bearer, errores públicos/privados/red, sin token y cleanup correctos. Arneses deben compilar con target ES2017: ES5 por defecto altera instanceof de clases Error; se verificó y corrigió solo el arnés temporal. No se añadió framework o suite frontend persistente.
- SDK contra Uvicorn real efímero pasó solicitud genérica, reset/login/me, cambio Bearer, rechazo de actual incorrecta, contraseña anterior y reuso. Solo sender simulado, claves/cuenta/TinyDB temporales; tokens por stdin, no argumentos/logs; proceso detenido y datos limpiados. Backend no modificado ni suite global repetida.
- Next dev disponible en puerto 3000, API configurada a puerto 8000 (API efímera ya detenida). Smoke login/register/perfil HTTP 200 con formularios/loader esperados. No páginas AUTH-03 todavía ni navegador real/Resend recibido: siguen etapas 5–7.
- Tablero registra etapa 3 Publicada `a4429d2`, etapa 4 Publicada en `c0ff844`.

### Publicación de etapa 4 y etapa 5 — Pantallas públicas de recuperación

Actualizado: 2026-10-19. Etapa 4 aprobada/publicada en `c0ff844`, push y árbol limpio verificados. Etapa 5 **LISTO PARA REVISIÓN**; commit y push pendientes de aprobación del usuario.

- Implementadas las vistas públicas de recuperación en `uis/talent-pipeline-tracker/`:
  - `auth-form.tsx`: enlace visible «¿Olvidaste tu contraseña?» apuntando a `/forgot-password`, y feedback de éxito `reset=success` al redirigir tras un restablecimiento exitoso. Envuelto en `Suspense` en `/login` y `/register`.
  - `/forgot-password` (`forgot-password-form.tsx` y `page.tsx`): formulario accesible, llamada a `requestNexovaPasswordReset`, confirmación genérica no enumerativa («Si esa dirección está registrada, recibirás un enlace en breve») y desactivación de envío tras completar la solicitud.
  - `/reset-password` (`reset-password-form.tsx` y `page.tsx`): captura de `token` del query string, sanitización inmediata de la URL con `window.history.replaceState` (sin persistencia en localStorage ni historial), metadato `referrer: "no-referrer"`, validación de coincidencia de contraseñas, llamada a `resetNexovaPassword`, limpieza de sesión residual con `clearNexovaSession()` y redirección a `/login?reset=success`. Token inválido/expirado muestra error claro y enlace de retorno.
- Sin contraseñas ni tokens en URL, logs o almacenamiento local del navegador.
- Tablero: etapa 4 Publicada `c0ff844`, etapa 5 En revisión. Mensaje propuesto: `feat(auth-ui): implement password recovery screens`.
