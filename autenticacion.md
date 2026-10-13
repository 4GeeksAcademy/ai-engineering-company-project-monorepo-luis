# Hito — Autenticación y restricción de rutas en FastAPI

> Documento de contexto y auditoría del proyecto 4Geeks **«Asegurando la API: Autenticación y Restricción de Rutas en FastAPI»**. Reúne los requisitos para implementar la entrega en el monorepo existente de Nexova. Es una guía de trabajo; el README oficial es la fuente de verdad ante cualquier discrepancia.

## Fuentes auditadas

- Tarea 4Geeks: **Securing the API: Authentication and Route Restriction in FastAPI** (`ai-eng-user-authentication-api`), cohorte **Authentication in web applications**; tarea pendiente.
- [README oficial en español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-user-authentication-api/README.es.md).
- [README oficial en inglés](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-user-authentication-api/README.md).
- [Contexto de Nexova](./CONTEXT.md) y guías locales del monorepo, incluido [`services/README.md`](./services/README.md).

Las versiones española e inglesa del README contienen los mismos requisitos sustanciales. Este documento prioriza la versión española para facilitar la implementación.

## Objetivo y alcance

La API existente de Nexova debe incorporar autenticación JWT stateless y autorización por propietario para proteger información y operaciones sensibles. Este hito **extiende el backend del proyecto transversal existente**: no crear un repositorio ni una API paralelos. Una vez aplicada la protección, algunas llamadas del frontend podrían dejar de funcionar hasta que este envíe el token; el README indica que eso es esperado en esta etapa.

El ticket de referencia es **AUTH-01 — Implementar autenticación y protección de rutas**. Incluye:

- CRUD de usuarios para credenciales (email y contraseña), en `/users`.
- Perfiles separados, relacionados uno a uno con usuarios, en `/profiles`.
- Login con emisión de JWT firmado, en `/auth`.
- Dependencia reutilizable `get_current_user` que valida el token y recupera al usuario.
- Protección de las rutas sensibles existentes y autorización con respuestas HTTP correctas.

## Ubicación e integración en el monorepo

- Trabajar sobre la API FastAPI que ya existe bajo `services/`; leer primero su README local y revisar la estructura real, routers, almacenamiento y pruebas.
- Seguir los patrones actuales del backend y sumar los módulos/rutas al servicio existente, sin duplicar la aplicación ni reemplazar funcionalidades previas.
- El README fuente pide crear la rama `feature/auth-api` y abrir un PR contra `main` del repositorio transversal. Para este documento de contexto no se ha creado esa rama.
- Dependencias indicadas por el README, instaladas con `uv` (no `pip install` ni `pipenv`):

  ```bash
  uv add "python-jose[cryptography]" "libpass[bcrypt]"
  ```

  `libpass` es el fork drop-in indicado para el hash bcrypt; el import de Python sigue siendo `from passlib.hash import bcrypt`.

## Requisitos funcionales: usuarios

### Modelo y almacenamiento

Guardar `User` **solo en TinyDB**, con al menos:

- `id` (identificador TinyDB)
- `email`
- `hashed_password`
- `is_active`
- `role`
- `created_at`

No guardar `name`, teléfono, dirección ni otros datos de contacto en `User`. Nunca persistir contraseñas en texto plano.

El rol solo puede ser `admin`, `manager` o `user`; validar con `Enum` o validador. Los registros nuevos deben tomar `user` por defecto. Rechazar valores de rol que no estén permitidos.

### Servicio y endpoints `/users`

Implementar una capa de servicio con operaciones para crear, buscar por ID, buscar por email, actualizar y eliminar usuarios. Exponer:

| Método y ruta | Comportamiento y acceso |
|---|---|
| `POST /users` | Registro público; hashear la contraseña antes de guardar. Acepta opcionalmente `name`, `phone`, `address` del perfil inicial y crea el perfil vinculado en la misma operación. Rol por defecto `user`. |
| `GET /users` | Listar usuarios; requiere autenticación. No exponer hashes de contraseña en respuestas. |
| `GET /users/{id}` | Obtener usuario; requiere autenticación. Aplicar autorización según reglas de propiedad/admin. |
| `PUT /users/{id}` | Actualizar credenciales como email; modificar rol solo si quien llama es admin. Solo el propio usuario o un admin puede actualizar. Protegido. |
| `DELETE /users/{id}` | Eliminar usuario; protegido y autorizado. Eliminar también el perfil vinculado. |

Separar esquemas de entrada/salida para evitar asignaciones de campos no permitidos y no filtrar `hashed_password` en la API.

## Requisitos funcionales: perfiles

Crear `Profile` en **TinyDB**, con relación uno a uno a `User` mediante `user_id`, y al menos estos campos: `id`, `user_id`, `name`, `phone`, `address`.

| Método y ruta | Comportamiento y acceso |
|---|---|
| `GET /profiles/me` | Requiere autenticación; devuelve el perfil asociado al usuario autenticado. |
| `PUT /profiles/me` | Requiere autenticación; actualiza `name`, `phone`, `address`. Solo el propietario puede modificar su perfil. |

Mantener los datos personales/contacto en `Profile`, no en `User`. El registro puede crear ambos de forma coordinada para no dejar un usuario sin el perfil inicial esperado.

## Requisitos funcionales: autenticación JWT

### Endpoints

- `POST /auth/login`: recibe `email` y `password`, verifica el hash y devuelve un access token JWT firmado.
- `GET /auth/me`: requiere autenticación y devuelve el email, rol y perfil vinculado (nombre y datos de contacto).

### Token y dependencia

- Usar `OAuth2PasswordBearer` de FastAPI para extraer `Authorization: Bearer <token>`.
- Firmar y decodificar tokens con `python-jose`.
- Incluir como mínimo el identificador `id` del usuario TinyDB en los claims JWT; el resto de módulos lo referencia como `user_uuid` cuando corresponda.
- Configurar una expiración finita mediante variable de entorno, por ejemplo `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Leer el secreto de firma desde `.env`/entorno; nunca hardcodearlo ni versionarlo.
- Implementar `get_current_user`: extraer token, validar firma y expiración, recuperar usuario vigente desde TinyDB y lanzar `HTTPException` con `401` si token, usuario o validación fallan.
- No usar cookies ni autenticación basada en sesiones: el requisito es JWT stateless.

## Hash y tratamiento de contraseñas

- Usar `libpass[bcrypt]` y esquema `bcrypt` para hash y verificación.
- Hashear al registrar y al cambiar una contraseña; verificar el hash durante el login.
- Nunca guardar, comparar ni devolver una contraseña en texto plano.
- No incluir hashes en respuestas, logs ni mensajes de error.

## Restricción y autorización de rutas

Aplicar `get_current_user` a cada ruta que no sea pública. Como mínimo:

1. Proteger todos los endpoints de `/users` excepto `POST /users`.
2. Proteger `GET /auth/me` y las rutas `/profiles/me`.
3. Proteger **al menos otras cinco rutas ya existentes**, fuera de `/users` y `/auth`, que expongan o modifiquen información sensible.
4. Para recursos de otros usuarios, comprobar explícitamente propiedad/permisos: devolver `403 Forbidden` cuando el usuario autenticado no sea propietario y no tenga autorización de admin.
5. Mantener `401 Unauthorized` para solicitudes sin autenticación válida (incluidos tokens ausentes, malformados, expirados o inválidos).

Antes de elegir las cinco rutas, inventariar los routers existentes en el backend. Registrar en el PR/documentación cuáles se protegieron y confirmar que una llamada con token válido conserva su comportamiento funcional.

> El README no exige aplicar una matriz de permisos por rol a cada ruta; sí exige restringir la actualización de rol a admins y hacer cumplir la propiedad (propietario/admin) en operaciones pertinentes.

## Persistencia: restricción crítica

- `User` y `Profile` viven **solo en TinyDB**, ahora y después de incorporar Supabase.
- No crear tablas `User`/`Profile` en PostgreSQL, Supabase o SQLModel.
- Si inventario u otros módulos PostgreSQL necesitan referirse a una persona, almacenar únicamente el ID TinyDB en el campo `user_uuid`.
- Mantener consistente la clave/representación del ID de TinyDB en claims JWT y referencias cruzadas.

## Pruebas y verificación manual

Verificar el flujo desde FastAPI `/docs`:

1. Registrar usuario en `POST /users`.
2. Iniciar sesión en `POST /auth/login` y obtener el token.
3. Autorizar el token como Bearer y llamar una ruta protegida, incluida `/auth/me` o `/profiles/me`.
4. Comprobar que una ruta protegida sin token devuelve `401`.
5. Comprobar que tokens expirados o malformados devuelven `401`.
6. Comprobar que un usuario no puede leer/modificar el perfil o credenciales de otro: debe obtener `403`, no un `401` engañoso.
7. Probar roles inválidos y confirmar que el alta por defecto asigna `user`.
8. Confirmar que contraseñas se persisten solo como hash y que los modelos de respuesta no exponen el hash.
9. Probar CRUD, eliminación en cascada lógica del perfil, y errores de usuario/email inexistente o duplicado.
10. Probar con token válido las cinco o más rutas preexistentes protegidas y comprobar que no hay regresiones.
11. Verificar que secreto y expiración se cargan del entorno, y que no se han añadido secretos al repositorio.

Conviene automatizar estas comprobaciones con tests del backend, además de la verificación manual requerida.

## Qué debes hacer — checklist consolidado

- [ ] Extender la API existente de Nexova; no crear repo/API nueva.
- [ ] Instalar dependencias declaradas con `uv`.
- [ ] Implementar `User` en TinyDB y CRUD completo bajo `/users`.
- [ ] Implementar validación del rol (`admin`, `manager`, `user`) y default `user`.
- [ ] Implementar hash bcrypt y verificación segura de contraseña.
- [ ] Implementar `Profile` en TinyDB, uno a uno con usuario, separado de credenciales.
- [ ] Crear perfil inicial al registrar usuario y eliminarlo al borrar usuario.
- [ ] Implementar login JWT en `/auth/login` y endpoint protegido `/auth/me`.
- [ ] Crear `get_current_user` con `OAuth2PasswordBearer` y `python-jose`.
- [ ] Leer secreto y expiración desde variables de entorno.
- [ ] Implementar `/profiles/me` GET/PUT con autorización del propietario.
- [ ] Proteger rutas `/users` indicadas, `/auth/me`, perfiles y cinco o más rutas sensibles preexistentes.
- [ ] Responder `401` ante autenticación inválida y `403` ante falta de autorización/propiedad.
- [ ] Mantener usuarios y perfiles exclusivamente en TinyDB, incluso al añadirse Supabase.
- [ ] Verificar flujo completo, errores de autenticación/autorización y ausencia de regresiones.
- [ ] Crear PR hacia `main` con resumen de rutas protegidas y cómo se verificaron.

## Qué vamos a evaluar — criterios de aceptación

- [ ] CRUD de usuarios completo y accesible vía API.
- [ ] Cada usuario tiene un perfil vinculado; nombre, teléfono y dirección residen en `Profile`, no `User`.
- [ ] Solo se aceptan roles `admin`, `manager`, `user`; nuevos usuarios usan `user` por defecto.
- [ ] Contraseñas hasheadas al crear/actualizar y verificadas correctamente en login; texto plano nunca se persiste.
- [ ] Login devuelve JWT válido y firmado.
- [ ] `get_current_user` decodifica el token y determina correctamente al usuario.
- [ ] Rutas protegidas devuelven `401` sin token válido.
- [ ] Acceso o modificación de perfil/credenciales de otro usuario devuelve `403 Forbidden`.
- [ ] Secreto de firma y expiración proceden de variables de entorno, no están hardcodeados.
- [ ] Rutas de auth bajo `/auth`, usuarios bajo `/users`, perfiles bajo `/profiles`.
- [ ] Al menos cinco rutas existentes fuera de `/users` y `/auth` requieren token válido.
- [ ] `User` y `Profile` siguen almacenándose en TinyDB tras incorporar Supabase; no hay tablas de usuario en PostgreSQL.
- [ ] Rutas preexistentes protegidas funcionan con token válido, sin regresiones.

## Entrega

Según el README de 4Geeks, subir la rama de la feature y abrir un pull request contra `main` del repositorio transversal. La descripción del PR debe resumir qué rutas se protegieron y cómo se verificó el comportamiento. Este archivo documenta los requisitos del proyecto; no sustituye la implementación ni el PR de entrega.
