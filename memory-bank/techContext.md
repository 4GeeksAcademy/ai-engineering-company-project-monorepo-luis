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

Actualizado: 2026-10-13; etapas 1 y 2 completadas, JWT y endpoints de autenticación todavía sin implementar.

- Rama de trabajo: `feature/auth-api`, creada desde `main` en `12ef190`. Plan de seis etapas y matriz de acceso en `services/api/README.md`; cada etapa cierra con pruebas, documentación, commit y push, y el PR final apunta a `main`.
- Dependencias instaladas con `uv add --project services/api "python-jose[cryptography]" "libpass[bcrypt]"`. Versiones resueltas: `python-jose` 3.5.0, `libpass` 1.9.3, `bcrypt` 5.0.0. Mantener coherentes `pyproject.toml`, `uv.lock` y `requirements.txt`; el import bcrypt sigue siendo `from passlib.hash import bcrypt`.
- Usuarios y perfiles implementados exclusivamente en TinyDB mediante `auth_models.py`, `auth_storage.py`, `passwords.py` y `user_service.py`, separados de proveedores. Ruta por defecto `services/api/data/auth.json`, configurable mediante `NEXOVA_AUTH_DB_PATH`; la carpeta ya está ignorada. Ninguna base real de auth se creó durante esta etapa.
- Variables previstas para JWT, aún no consumidas: `JWT_SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES`. Sin secretos por defecto ni valores en documentación; configuración por entorno, algoritmo HS256 fijo y expiración positiva finita.
- Registro público solo con rol `user`; primer admin mediante comando local seguro. Listado de usuarios solo admin; credenciales propietario/admin; perfiles `/me` del usuario autenticado. Roles admitidos: `admin`, `manager`, `user`.
- Login previsto en `/auth/login`: JSON email/password y formulario OAuth2 con email como username. Dependencia `get_current_user` verificará token y estado vigente del usuario; `401` para autenticación inválida y `403` para falta de permiso.
- Se protegerán las seis operaciones de proveedores y las dos de incidencias. Ambos módulos permanecen compartidos entre usuarios autenticados; el último resultado de incidencias sigue siendo global en memoria. No se implementará propiedad por usuario para estos recursos.
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
