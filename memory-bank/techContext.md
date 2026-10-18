# Tech Context

## Fuentes de verdad

- `autenticacion.md`: guía del hito AUTH-01; el README oficial de 4Geeks enlazado allí prevalece ante discrepancias. Las referencias temporales `ingenieria-ia.md` y `base-dato-ligero.md` fueron retiradas al completar su función; el directorio de proveedores existente se documenta en el README de la API.
- `CONTEXT.md`: negocio de Nexova y requisitos del sitio público y formulario.
- `SPEC.md`: requisitos funcionales y API del tracker de candidatos.
- README y `package.json` de cada aplicación: estructura y comandos disponibles.
- Este archivo resume esas fuentes; si hay discrepancias, consultar la fuente original.

## Estructura actual relevante

- `uis/website/`: sitio público estático existente, con `index.html`, `application.html` y estilos Tailwind.
- `uis/backoffice/`: panel interno estático con contexto, etapas, analizador de incidencias y directorio de proveedores conectado al API local.
- `uis/talent-pipeline-tracker/`: aplicación Next.js existente para gestión detallada de candidatos.
- `services/api/`: API FastAPI para incidencias y directorio de proveedores; proveedores usa modelos Pydantic, TinyDB y rutas CRUD bajo `/api/suppliers`.
- `memory-bank/`: contexto persistente para el proyecto.
- `.agents/`: reglas y skills para agentes de desarrollo; pendiente de crear.
- Existe `uis/talent-pipeline-tracker/AGENTS.md`; no sustituye el `AGENTS.md` raíz requerido.

## Stack y datos

- Sitio público: HTML estático, Tailwind CSS 3.4.17 y componentes web nativos compartidos para header/footer en `uis/website/shared-components.js`.
- Tracker de candidatos: Next.js App Router, React, TypeScript y Tailwind CSS 4.
- El tracker consume `https://playground.4geeks.com/tracker/api/v1`; revisar `SPEC.md` para rutas, modelos y comportamiento.
- El directorio de proveedores guarda TinyDB en `services/api/data/suppliers.json` por defecto, o en `NEXOVA_SUPPLIERS_DB_PATH` si se configura. El archivo local de datos está excluido de Git.
- El comando idempotente `uv run seed` se ejecuta desde `services/api`; la API y sus datos comerciales permanecen en alcance local/demo.
- La tecnología e integración de datos del nuevo backoffice quedan por decidir al implementarlo. Reutilizar la API del tracker solo si cubre los requisitos del backoffice.
- No crear un backend por defecto. Si se necesita, debe vivir bajo `services/` y seguir sus convenciones.

## Comandos declarados

Desde la raíz:

- `npm run typecheck`
- `npm run demo`

Sitio público, desde la raíz:

- Compilar Tailwind: `npx --yes tailwindcss@3.4.17 -c uis/website/tailwind.config.cjs -i uis/website/assets/css/input.css -o uis/website/assets/css/styles.css --minify`
- Servir: `npx --yes serve uis/website -l 5500` (usar otro puerto si 5500 está ocupado). Ejecutar desde la raíz; no usar `-s`, porque el fallback SPA sirve la landing para `/application`.
- Verificar `/`, `/index.html`, `/application` y `/application.html`; `serve` redirige las páginas `.html` a sus rutas limpias.

Tracker, desde `uis/talent-pipeline-tracker/`:

- `npm run dev`
- `npm run lint`
- `npm run build`
- `npm run start`
- No declara scripts propios para tests ni typecheck.

Backoffice estático, desde la raíz:

- Servir: `npx --yes serve uis/backoffice -l 5502`.
- No tiene scripts propios de test, lint, typecheck o build.

API de proveedores, desde `services/api/`:

- `uv run seed`
- Desde la raíz, suite Python: `uv run --project services/api python -m unittest discover -s services/api/tests -v`

Los comandos de compilación y serving del website se ejecutaron. El backoffice se validó sirviéndolo y con smoke test HTTP; los checks del tracker y de raíz no se ejecutaron en esta etapa.

## Restricciones técnicas y de datos

- Respetar las ubicaciones del monorepo y leer el README de cada carpeta antes de añadir una aplicación o servicio.
- No leer, imprimir ni versionar secretos de `uis/talent-pipeline-tracker/.env.local`.
- No almacenar PII real de candidatos en este banco de memoria, mocks o capturas.
- Documentar mocks, APIs externas, estados de carga/error y limitaciones de datos.
- La documentación es un resumen operativo; no reemplaza las especificaciones ni los contratos originales.

## AUTH-01 — Preparación de autenticación

Actualizado: 2026-10-14; etapas 1–6 completadas. Auth, CRUD de usuarios/perfiles y protección de rutas operativas implementados; aceptación final verificada y PR de entrega en curso.

- Rama de trabajo: `feature/auth-api`, creada desde `main` en `12ef190`. Plan de seis etapas y matriz de acceso en `services/api/README.md`; cada etapa cierra con pruebas, documentación, commit y push, y el PR final apunta a `main`.
- Dependencias instaladas con `uv add --project services/api "python-jose[cryptography]" "libpass[bcrypt]"`. Versiones resueltas: `python-jose` 3.5.0, `libpass` 1.9.3, `bcrypt` 5.0.0. Mantener coherentes `pyproject.toml`, `uv.lock` y `requirements.txt`; el import bcrypt sigue siendo `from passlib.hash import bcrypt`.
- Usuarios y perfiles implementados exclusivamente en TinyDB mediante `auth_models.py`, `auth_storage.py`, `passwords.py` y `user_service.py`, separados de proveedores. Ruta por defecto `services/api/data/auth.json`, configurable mediante `NEXOVA_AUTH_DB_PATH`; la carpeta ya está ignorada. Ninguna base real de auth se creó durante esta etapa.
- Variables JWT obligatorias validadas en el lifespan: `JWT_SECRET_KEY` (no vacía, al menos 32 bytes UTF-8) y `ACCESS_TOKEN_EXPIRE_MINUTES` (entero positivo con expiración representable). Sin secretos por defecto ni valores en documentación; HS256 fijo. Cambios de entorno requieren reiniciar; sin configuración válida no arranca la API.
- Registro público HTTP solo permite los campos email/password/contacto inicial y siempre asigna `user`; `role` extra se rechaza con 422 genérico. Primer admin mediante comando local seguro. Listado de usuarios solo admin; credenciales propietario/admin; `role`/`is_active` modificables solo por admin; perfiles `/me` del usuario autenticado. Roles admitidos: `admin`, `manager`, `user`.
- Login implementado en `/auth/login`: JSON email/password y formulario OAuth2 con email como username, compatible con Swagger. `get_current_user` valida firma/exp/id y recupera estado/rol vigente desde TinyDB; `401` con Bearer challenge para autenticación inválida. `/auth/me` devuelve email/rol/perfil. Endpoints `/users` y `/profiles/me` implementan propiedad/admin y `403` para usuarios sin permiso.
- Las seis operaciones de proveedores y dos de incidencias requieren `get_current_user` mediante dependencias a nivel de router. Ambos módulos permanecen compartidos entre usuarios autenticados; el último resultado de incidencias sigue siendo global en memoria. Sin propiedad por usuario.
- Sin cambios frontend en este hito; después de proteger las rutas, el backoffice sin Bearer dejará de funcionar temporalmente. No añadir Supabase, cookies, sesiones, refresh tokens ni despliegue.
- Verificación de etapa 1: 24 tests antes/después y smoke bcrypt/JWT satisfactorios. Comando reproducible desde raíz: `uv run --locked --project services/api python -m unittest discover -s services/api/tests -v`. No hay lint/typecheck/build Python declarados; no ejecutar checks frontend ajenos.

### Capa interna de etapa 2

- Operaciones: `create_user`, `get_user_by_id`, `get_user_by_email`, `list_users`, `update_user`, `delete_user`, `get_profile_by_user_id`, `update_profile`. Errores de dominio, todavía sin HTTP: `DuplicateEmailError`, `UserNotFoundError`, `ProfileNotFoundError`, `RegistrationRoleError`.
- Registro siempre `user`; perfil creado incluso sin contacto y eliminado junto al usuario. Email validado/normalizado, unicidad bajo bloqueo en proceso. `update_user` permite cambios privilegiados internos; el router futuro debe aplicar permisos propietario/admin antes de llamarlo.
- `UserCreate` y `UserUpdate` usan `SecretStr` para contraseña; `UserRecord` oculta su hash en repr/serialización y `UserResponse` no lo contiene. El almacenamiento solo persiste bcrypt, nunca password. Política: mínimo 8 caracteres, máximo 72 bytes UTF-8, sin bytes nulos ni truncamiento.
- Las escrituras trabajan en un snapshot TinyDB en memoria bajo `RLock`; solo se reemplaza el archivo al completar la operación, con temporal en el mismo directorio, flush/fsync y limpieza ante fallos ordinarios. Las lecturas no reescriben archivos existentes.
- Tabla TinyDB adicional `auth_metadata` con contadores persistentes para no reutilizar IDs borrados; IDs de usuario/perfil son los doc_id, no UUID nuevos. Sin datos de contacto/credenciales en metadata.
- Alcance de persistencia: un proceso/worker, sin modificación concurrente mediante comando admin externo. No hay transacciones multiworker ni garantías completas ante caídas/pérdida de energía. Reset/restauración de DB requerirá invalidar los tokens/clave de firma cuando existan.
- Verificación: `test_auth_models.py` (10 tests), `test_user_service.py` (17 tests), suite total (51 tests) satisfactorios, con bases temporales sintéticas y fallos inyectados. Sin cambios en `main.py`, routers, manifiestos ni frontend en etapa 2.

### JWT y bootstrap de etapa 3

- Módulos `security.py`, `auth_dependencies.py`, `routers/auth.py` y `bootstrap_admin.py`; esquemas LoginRequest, TokenResponse y AuthMeResponse en auth_models. Token con id entero, sub equivalente, iat y exp; no incorpora rol/hash/contacto. El secreto se oculta en repr de settings y no se crean archivos `.env`.
- OAuth2PasswordBearer(tokenUrl=/auth/login, auto_error=False), validación HS256/exp obligatorio, id positivo estricto (no bool/string) y sub coherente si aparece. Usuario inexistente/eliminado/inactivo y tokens inválidos → 401. JSON/form inválidos → 422 genérico sin eco de credenciales; tipo de contenido no soportado → 415.
- Comando instalado `uv run --locked --project services/api promote-admin --database <ruta> --user-id <id> --confirm`: promueve usuario activo existente, requiere ruta explícita/confirmación, idempotente, no acepta contraseñas ni imprime email/hash. API detenida, sin proceso externo concurrente; usar solo datos autorizados. Registrado como bootstrap_admin:main, py-modules incluye seed y bootstrap_admin.
- JWT stateless sin refresh/logout de servidor. Cambio de contraseña no revoca automáticamente tokens anteriores; expiración, eliminación/desactivación y cambio de clave controlan su validez. Configuración por entorno cargada al arranque; no se ha implementado lectura de `.env`.
- Verificación de etapa 3: 9 tests security, 13 auth_api (incluido Uvicorn real en puerto efímero), 7 bootstrap_admin; 80 tests totales. Todos pasan, lockfile coherente sin cambios ni dependencias nuevas, diagnósticos sin errores. La prueba del servidor termina su proceso.
- Registro HTTP y `/users`/`profiles/me` siguen pendientes; no se modifica frontend ni se protegen aún proveedores/incidencias. El arranque local previo ahora requiere las dos variables JWT. Verificación manual completa en navegador queda para etapa 6.

### CRUD y autorización de etapa 4

- Routers `routers/users.py` y `routers/profiles.py`, registrados en `main.py`: `POST/GET /users`, `GET/PUT/DELETE /users/{user_id}`, `GET/PUT /profiles/me`. No existe ruta de perfil por ID.
- `UserRegistration` es distinto del esquema interno `UserCreate`: no expone `role`, estado, ID/hash ni otros campos servidor. Registro siempre crea role=user y perfil inicial. Roles privilegiados nunca pasan por la superficie pública.
- Todas las rutas salvo `POST /users` usan `get_current_user`. `GET /users` exige admin; GET/PUT/DELETE por id autorizan propietario/admin antes de consultar, por lo que usuarios ajenos reciben 403 y un ID desconocido solo da 404 al actor autorizado. Manager no es admin.
- PUT usuario propietario puede email/password; únicamente admin puede enviar role/is_active. `model_fields_set` diferencia campo ausente de valor, y modelos de update rechazan null explícito. Cambios password se hashean. Emails duplicados →409; usuario/perfil inexistente →404; auth ausente/inválida →401 Bearer.
- `ProfileUpdate` limita cambios a name/phone/address; omitted preserva y null limpia; siempre se usa el id autenticado. La eliminación user conserva cascada lógica user/profile coordinada.
- Handler de `RequestValidationError` sanea respuestas para paths `/users` y `/users/*` en 422 genérico, previniendo eco de passwords y hashes. La validación de otros routers conserva su contrato actual.
- Verificación: `test_users_api.py` (16 tests) y suite total (96 tests) satisfactorias con autenticación real por login y registros sintéticos aislados. Incluye autorización, rol admin/manager, seguridad contra escalación, secretos, OpenAPI, duplicados, 401/403/404/409/422 y cascada sin borrado parcial si falta perfil. Sin cambios en rutas supplier/incidents, aún públicas hasta etapa 5.

### Protección operativa de etapa 5

- `routers/suppliers.py` y `routers/incidents.py` aplican `Depends(get_current_user)` al router completo: 6+2 operaciones protegidas. OpenAPI refleja OAuth2 Bearer en cada operación; `/health`, `/docs` y `/openapi.json` siguen públicos.
- Los recursos no son por propietario y no añaden permisos por rol: cualquier usuario activo autenticado conserva el comportamiento funcional existente.
- Tests existentes de supplier/incidents ahora usan `POST /users` y `POST /auth/login` con cuenta sintética y TinyDB temporal; el TestClient se inicia con contextmanager tras inyectar env JWT. Se valida cada endpoint con token válido (contrato anterior intacto) y se añaden matrices de 401 para ausencia/token malformed. Fixture de análisis CSV existente permanece igual.
- Al usar un TestClient autenticado y otro anónimo anidados, ambos comparten FastAPI `app.state`. El lifespan ahora restaura el valor previo de `jwt_settings` y elimina la clave únicamente si no existía al entrar, evitando doble eliminación en tests/uso anidado.
- Verificación: supplier 11 tests, incidents 8 tests y suite total 100 tests, además `uv lock --check`/`git diff --check`. Sin dependencias nuevas. Pylance seleccionado global `/usr/local/python/3.12.1` aún emite imports no resueltos; entorno real de servicio `services/api/.venv` contiene FastAPI/Uvicorn, suites `uv run` pasan. No se modifica configuración VS Code.

### Aceptación y entrega de etapa 6

- Proceso Uvicorn real y efímero comprobó `/docs`, OpenAPI, registro+perfil, rechazo role escalation, JSON/OAuth login, `/auth/me`, `/profiles/me`, 401 inválido/expirado y 403 listado user. Puerto aleatorio socket-activated; proceso, TinyDBs, secreto y usuario temporales se destruyeron al terminar.
- En live smoke con credenciales Bearer pasaron las seis rutas supplier y ambas incident con CSV de una fila totalmente sintética; sin token se verificaron 401 en endpoints protegidos. OpenAPI lista los ocho schemas Security. Respuesta/TinyDB no exponen password/hash; TinyDB contiene bcrypt; export no contiene email.
- Suite backend 100, `uv lock --check` y `git diff --check` correctos. La prueba de interacción se efectuó mediante llamadas HTTP contra `/docs`/OpenAPI y el OAuth2 form; no se integró UI del backoffice. Todo coincide con limitación explícita de frontend pendiente.
- PR final hacia `main` desde `feature/auth-api`, con resumen de rutas/permisos y pruebas, conforme al flujo aprobado.

## AUTH-02 actual y preparación AUTH-03

Actualizado: 2026-10-18. Este apartado actualiza el punto de partida; los apartados AUTH-01 anteriores describen su evolución histórica.

- AUTH-02 ya está en `origin/main` (`78d8678`): el tracker implementa `/login`, `/register`, `/account/profile`, sesión local, Bearer, guard y navegación por expiración. `lib/nexova-api.ts` utiliza `NEXT_PUBLIC_NEXOVA_API_URL`; `lib/api.ts` y `NEXT_PUBLIC_API_URL` siguen separados para candidatos externos. El guard de UI no autoriza datos servidos por esa API externa.
- AUTH-03 se prepara en la rama existente `feature/password-reset`, HEAD inicial `65f4656`, con main remoto como ancestro y árbol inicialmente limpio. La fuente del nuevo hito es `restablecimiento-contrasena.md`, contrastada con README oficial español el 2026-10-18. Sus siete etapas y evidencias viven en esa guía.
- Solo etapa 1 documental realizada y En revisión. No hay endpoints forgot/reset/change ni nuevas páginas aún. Guard actual protege explícitamente perfil dentro de account; deberá incorporar change-password y permitir recovery sin redirecciones por sesión vieja.
- Reutilizar API FastAPI/TinyDB existente, `open_auth_database`, bcrypt y cliente Nexova. Token previsto: `secrets.token_urlsafe(32)`, solo digest SHA-256 persistido, comparación segura, default 30 minutos (15–60 permitidos), consumo y actualización en un snapshot bajo el bloqueo single-worker. Sin nueva base ni revocación de access JWTs.
- Resend seleccionado; contrato futuro de entorno: `RESEND_API_KEY` secreta backend-only, `RESEND_FROM_EMAIL` remitente autorizado, `NEXOVA_FRONTEND_URL` origen confiable y `PASSWORD_RESET_EXPIRE_MINUTES` opcional. Ninguna de estas variables se lee todavía por la implementación; no confundir documentación con configuración. JWT actual permanece obligatorio.
- Envío acordado en segundo plano local/demo: respuesta genérica confirma aceptación, no entrega; no cola durable/reintentos garantizados. Fallo previo común independiente de email; fallo tardío del proveedor sin exposición pública ni datos sensibles. No mantener lock de TinyDB durante envío. Prueba final exige recepción real con autorización de configuración/conexión y buzón de prueba; nunca PII real de candidatos.
- Baseline actual: 100 tests backend OK, lint/build tracker OK y diff sin errores de formato. Next verifica TypeScript en build. Persisten avisos Starlette/httpx y Turbopack por lockfiles múltiples. Build carga automáticamente configuración local, sin lectura manual/modificación ni impresión de valores.
- Se corrigió una brecha preventiva de Git: `.env` y `.env.*` se ignoran ahora desde raíz, con excepción `.env.example`, comprobada para la API sin leer ni crear archivos. Las reglas propias del tracker pueden ser más estrictas; comprobar ruta exacta antes de crear plantillas. No modificar secretos sin autorización.
- Revisar y aprobar cada cierre antes de staging/commit/push; no avanzar automáticamente. Solo documentación y exclusiones Git en etapa 1: no se alteran website, backoffice, CONTEXT/SPEC, dependencias o código. No hay pruebas E2E AUTH-03 todavía.

### AUTH-03 etapa 2 — Dominio implementado

- Etapa1 publicada en `0ac5d4f`, push confirmado. Etapa2 En revisión al 2026-10-18; no endpoints/password email/settings nuevos aún. La configuración documentada sigue prevista, no se carga hasta etapa3.
- Nuevo `password_reset_service.py`: emisión por email normalizado (`None` si desconocido/inactivo), reset con token y cambio interno con contraseña actual. Entradas sensibles usan SecretStr; error genérico `InvalidPasswordResetTokenError`, mismatch actual `CurrentPasswordMismatchError` y cuenta ausente/inactiva en cambio `UserNotFoundError`.
- `PasswordResetRecord` en auth_models valida user_id positivo y vencimiento con zona normalizado UTC; digest oculto de repr/model_dump. Tabla TinyDB opcional `password_reset_tokens`, doc_id=user_id; solo digest SHA-256/user_id/expires_at. Emisión token_urlsafe(32), default30, lifetime entero15–60, reemplaza previo y elimina registros vencidos.
- `reset_password` compara con hmac.compare_digest y coordina validación/hash/actualización/remoción en un solo open_auth_database. `change_password` verifica actual bajo el mismo lock. Helper `invalidate_password_reset_tokens(database, user_id)` trabaja en el snapshot suministrado, no abre otro; user_service lo llama al cambiar password/email/desactivar/borrar, no rol/perfil.
- Atomicidad solo dentro del proceso/worker existente; fallo de commit conserva contraseña/token y limpia temporal. Sin cola, email, cambios de routers o revocación de access JWT. El futuro router debe sacar user_id de get_current_user.
- Verificación: 23 tests reset, 21 user_service, 127 totales backend OK; focales repetidos tras último ajuste. Diagnósticos de seis archivos, lockfile y formato diff correctos, dependencias sin cambio. Datos sintéticos/temporales y reloj controlado, sin sleeps. Ninguna prueba frontend/Resend/E2E en esta etapa interna.

### AUTH-03 etapa 3 — Endpoints y correo integrado

- Etapa 2 aprobada/publicada en `1997bce`; etapa 3 En revisión al 2026-10-18. Existen POST `/auth/forgot-password`, `/auth/reset-password` y `/auth/change-password` en el router auth. Frontend y recepción real de correo pendientes.
- Forgot acepta email normalizado, valida configuración y acepta `BackgroundTasks` antes del 200 genérico. Búsqueda, emisión y envío después del cuerpo ASGI; configuración inválida o aceptación fallida devuelve 503 común. Fallo posterior: log fijo sin exc_info, PII o tokens; no cola durable ni reintentos garantizados.
- `get_password_reset_settings` lee entorno en cada forgot y captura settings inmutables para la tarea. API arranca sin Resend; forgot devuelve 503 si configuración incompleta/inválida. JWT startup no cambia; reset/change no dependen del proveedor. API no carga .env automáticamente.
- `email_service.py`: `PasswordResetSettings` oculta key SecretStr en repr; `load_password_reset_settings` y `send_password_reset_email`. Key ASCII imprimible sin espacios, remitente EmailStr simple, origen AnyHttpUrl HTTPS sin credenciales/ruta/query/fragment/puerto 0, HTTP loopback permitido; TTL 15–60/default 30. httpx existente hace POST a Resend /emails, texto plano y link con urlencode, timeout de 10 segundos por fase, sin redirects/trust_env/retries. Fallos HTTP y no-2xx devuelven `EmailDeliveryError` saneado.
- Esquemas sensibles usan SecretStr. Handler main sanea 422 sin input en nuevas rutas; error del campo token en reset devuelve 400. Reset inválido/vencido/usado 400, actual incorrecta en change 400, auth 401 con challenge, ID extra 422, persistencia 503 sin parcialidad. ID siempre de get_current_user; sin revocación access JWT.
- Tests: 5 email con MockTransport, 23 HTTP con sender inyectado (orden ASGI y consumo concurrente incluidos), 155 totales backend OK. Diagnósticos de 6 archivos, lockfile y diff correctos. Sin dependencias nuevas, secretos reales, navegador o frontend. Resend real y recepción siguen como requisito de etapa 7 con autorización separada.
