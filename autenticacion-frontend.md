# AUTH-02 — Conectando el Candado: Flujos de Autenticación en el Frontend

> Documento de requisitos y contexto para implementar el proyecto 4Geeks **“Conectando el Candado: Flujos de Autenticación en el Frontend”** en el monorepo existente de Nexova. Resume las instrucciones oficiales, especialmente **“Qué debes hacer”** y **“Qué vamos a evaluar”**, y las aterriza a la estructura actual del repositorio. El README oficial prevalece si este resumen difiere de él.

## Fuentes auditadas

- Tarea 4Geeks: **Connecting the Lock: Authentication Flows in the Frontend**, cohorte **Authentication in web applications**, tarea `1002541`, slug `ai-eng-user-authentication-flows`.
- [README oficial en español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-user-authentication-flows/README.es.md).
- [README oficial en inglés](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-user-authentication-flows/README.md).
- Contexto local: [`uis/README.es.md`](./uis/README.es.md), [`uis/website/README.es.md`](./uis/website/README.es.md), [`uis/talent-pipeline-tracker/README.md`](./uis/talent-pipeline-tracker/README.md), [`services/api/README.md`](./services/api/README.md).

## Objetivo y alcance

La API del hito anterior exige un JWT en sus rutas protegidas. Este proyecto completa el flujo en el cliente: registro, inicio y cierre de sesión, perfil de cuenta, envío del token a la API y protección de las vistas privadas.

- Continuar en **este monorepo**; no crear una aplicación de autenticación o un repositorio aparte.
- Integrar los flujos en las aplicaciones Next.js existentes.
- Proteger las vistas que requieran sesión en todas esas aplicaciones, **excepto el website público del Hito 1**, que debe seguir siendo completamente público y sin redirecciones ni comprobaciones de autenticación.
- Token JWT en `localStorage`; enviar en cada llamada protegida como `Authorization: Bearer <token>`.
- Al cerrar sesión o ante una respuesta `401` de una llamada protegida, eliminar el token y redirigir a `/login`.
- El frontend deberá funcionar de extremo a extremo con la API real, no limitarse a una interfaz simulada.

## Contexto del monorepo auditado

- La aplicación Next.js identificada está en [`uis/talent-pipeline-tracker/`](./uis/talent-pipeline-tracker/), con App Router bajo `app/` y cliente HTTP en [`lib/api.ts`](./uis/talent-pipeline-tracker/lib/api.ts). Ahí se integran login, registro, perfil y protección de vistas si es una aplicación que requiere autenticación.
- El sitio público de Nexova está en [`uis/website/`](./uis/website/); es un sitio estático y debe permanecer público, sin guard de sesión.
- El cliente HTTP existente usa `NEXT_PUBLIC_API_URL` con un valor por defecto de la API pública de Tracker. Antes de conectar autenticación, configurar la URL adecuada para la API Nexova según el entorno; no dejar que las rutas de auth se envíen a la API de Tracker.
- La API de Nexova sí implementa `POST /users`, `POST /auth/login`, `GET /auth/me` y `GET/PUT /profiles/me` en `services/api`. El login devuelve `access_token` y `token_type`; `/auth/me` devuelve `email`, `role` y `profile`. Para ejecución real, la API necesita `JWT_SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES` válidos.
- El tracker usa `NEXT_PUBLIC_API_URL` para `https://playground.4geeks.com/tracker/api/v1`. La autenticación Nexova usa por separado `NEXT_PUBLIC_NEXOVA_API_URL` (por ejemplo, la raíz de la API local); no reemplazar la URL de Tracker ni añadir `/api` a la base de Nexova.
- El README propone la rama `feature/auth-frontend` (o continuar en la rama de trabajo). La entrega de implementación se hace mediante PR hacia `main`.

## Estado de implementación — 2026-10-15

- Flujos implementados en `uis/talent-pipeline-tracker`: `/login`, `/register`, `/account/profile`; registro `POST /users` seguido de login; almacenamiento en `localStorage`; logout; manejo centralizado de `401`; y guard cliente para `/`, `/candidates/*` y `/account/profile`.
- El website estático `uis/website/` no se modificó ni depende de autenticación. El backoffice estático queda fuera del alcance acordado.
- El guard protege la visualización de la UI del tracker, pero los datos de candidatos siguen proviniendo de la API externa de 4Geeks y no están protegidos por el JWT Nexova. No considerar ese guard una frontera de autorización de datos.
- Comprobaciones ejecutadas: `npm run lint`, `npm run build`; smoke HTTP de registro/login, credenciales inválidas, `/auth/me`, `PUT /profiles/me`, persistencia del perfil y CORS en API local aislada con datos sintéticos; rutas frontend y guard SSR sin sesión. La base de prueba es temporal y se elimina al detener Uvicorn.
- Pendiente antes de declarar aceptación manual completa: probar en navegador los flujos UI con la API configurada para el entorno de ejecución, los estados de `403`/`5xx` y el logout desde la UI. No se automatizó navegador porque no hay Playwright/Puppeteer instalado. La URL real de despliegue y la PR contra `main` aún no se verificaron/abrieron.

## Contrato esperado con la API

Usar el contrato del proyecto y la implementación real del hito API anterior. Confirmar la forma exacta de las respuestas (en particular el nombre del campo del JWT) con OpenAPI/Swagger; no asumir nombres de propiedades que la API no devuelva.

| Método y ruta | Uso en frontend | Autenticación |
|---|---|---|
| `POST /users` | Crear usuario durante el registro; enviar credenciales y los campos de perfil opcionales soportados por la API. | Pública |
| `POST /auth/login` | Enviar email y contraseña; obtener el access token. | Pública |
| `GET /auth/me` | Cargar email y perfil del usuario actual. | Bearer token |
| `GET /profiles/me` | Consultar perfil si la UI/API lo requiere; el README del proyecto pide cargar la vista con `GET /auth/me`. | Bearer token |
| `PUT /profiles/me` | Actualizar `name`, `phone` y `address`. | Bearer token |

Durante el registro, la secuencia indicada es `POST /users` y, si tiene éxito, `POST /auth/login` con las mismas credenciales; almacenar el token devuelto solo después del login exitoso. Si cualquiera de las peticiones falla, mostrar un error útil y no mostrar al usuario como autenticado.

## Requisitos de implementación

### 1. Vistas de autenticación

- [ ] `/login`: formulario de email y contraseña.
  - Si el login tiene éxito, guardar el token en `localStorage` y redirigir a la vista principal autenticada.
  - Si falla, presentar un mensaje de error claro; no filtrar detalles internos ni credenciales.
- [ ] `/register`: formulario de creación de cuenta.
  - Enviar `POST /users`, incluyendo campos opcionales de perfil disponibles en la API.
  - Tras el registro exitoso, iniciar sesión con `POST /auth/login`, guardar el JWT y redirigir.
  - Si la validación o una petición falla, mostrar errores a nivel de campo cuando corresponda.
- No almacenar la contraseña ni incluirla en URLs, logs o almacenamiento persistente.

### 2. Perfil de cuenta

- [ ] `/account/profile`: vista autenticada con email y campos `name`, `phone`, `address` desde `GET /auth/me`.
- [ ] Permitir actualizar los campos editables mediante `PUT /profiles/me`, adjuntando el Bearer token.
- [ ] Mostrar estados de carga, errores de API y confirmación de guardado; no presentar datos inventados si falla la petición.

### 3. Protección de rutas

- [ ] Inventariar las vistas de cada aplicación Next.js y decidir cuáles requieren sesión.
- [ ] Proteger todas las vistas privadas con guard de layout en cliente o hook compartido. Si no hay token en `localStorage`, redirigir a `/login`.
- [ ] El middleware de Next.js se ejecuta en servidor y no puede leer `localStorage`; **no usarlo para esta verificación**, salvo que además exista una cookie deliberada y legible por middleware. El contrato de este proyecto indica `localStorage`.
- [ ] Evitar mostrar contenido privado durante la comprobación inicial del token (estado de carga/guard).
- [ ] Mantener intacto `uis/website/`: sin control de token, redirect al login ni dependencia de endpoints autenticados.

### 4. Ciclo de vida del token y cliente API

- [ ] Tras login o registro, persistir el access token en `localStorage`.
- [ ] En **cada** llamada protegida, leer el token y enviar `Authorization: Bearer <token>`.
- [ ] Centralizar esta lógica en el cliente API/helper de la aplicación para reducir errores y evitar duplicación. Revisar el `request()` actual de `uis/talent-pipeline-tracker/lib/api.ts`, que hoy no adjunta token ni trata globalmente los `401`.
- [ ] En logout: borrar token, limpiar estado de usuario en memoria y redirigir a `/login`.
- [ ] Si cualquier llamada protegida devuelve `401`: borrar token, limpiar estado autenticado y redirigir a `/login`.
- [ ] No redirigir ante cualquier error indiscriminadamente: un `403`, fallo de red o error `5xx` no equivale a sesión expirada; mostrar el error correspondiente.
- [ ] Restringir el acceso a `localStorage` al cliente (por ejemplo, dentro de efectos o helpers llamados desde componentes cliente), para evitar errores de renderizado en servidor.

## Qué debes hacer — checklist consolidado

- [ ] Confirmar que la API del hito previo está ejecutándose y es accesible desde la aplicación frontend.
- [ ] Configurar el endpoint base de API Nexova mediante el entorno correspondiente (`NEXT_PUBLIC_API_URL` o configuración existente); no reutilizar accidentalmente la URL de Tracker.
- [ ] Implementar `/login`: formulario, llamada de API, almacenamiento del JWT, redirección y mensaje de error.
- [ ] Implementar `/register`: formulario, `POST /users`, después `POST /auth/login`, almacenamiento del JWT y errores de validación por campo.
- [ ] Implementar `/account/profile`: email y datos de perfil desde `GET /auth/me`; edición por `PUT /profiles/me` con Bearer token.
- [ ] Identificar vistas privadas en las aplicaciones Next.js y protegerlas con un guard/hook en cliente.
- [ ] Excluir completamente el website público del guard y de los redirects de autenticación.
- [ ] Guardar el token al autenticar y adjuntarlo a cada petición protegida mediante `Authorization: Bearer <token>`.
- [ ] Implementar logout borrando el token y redirigiendo a `/login`.
- [ ] Ante un `401` de cualquier llamada protegida, limpiar sesión y redirigir a `/login`.
- [ ] Verificar flujos exitosos y fallidos, el comportamiento del token y la accesibilidad básica de formularios/mensajes.
- [ ] Abrir PR contra `main`, describiendo las vistas protegidas y confirmando que el website público no fue afectado.

## Qué vamos a evaluar — criterios de aceptación

- [ ] Los formularios de login y registro funcionan end-to-end; tras autenticación exitosa, el token se almacena.
- [ ] Las vistas protegidas redirigen a `/login` cuando no existe un token válido en el almacenamiento.
- [ ] El website público del Hito 1 sigue funcionando sin comprobaciones de autenticación.
- [ ] La vista de perfil muestra el email de `User` y el nombre/datos de contacto del `Profile` vinculado, y actualiza el perfil mediante `PUT /profiles/me`.
- [ ] El logout elimina el token y redirige correctamente.
- [ ] Una respuesta `401` de cualquier llamada protegida limpia la sesión y redirige a `/login`.

## Plan de verificación manual

1. Arrancar la API Nexova y la aplicación Next.js con configuración de entorno correcta.
2. Sin token, visitar una vista privada y confirmar redirect a `/login`; comprobar que el website de `uis/website/` sigue cargando sin redirect.
3. Registrar una cuenta nueva; confirmar petición a `POST /users` seguida de `POST /auth/login`, token guardado y navegación a vista autenticada.
4. Cerrar sesión, iniciar sesión con credenciales válidas y comprobar que se guarda el token y el login redirige correctamente.
5. Inspeccionar una llamada protegida en la pestaña de red: cabecera `Authorization: Bearer …` presente; confirmar que nunca se incluye la contraseña en la cabecera ni en URL.
6. Abrir `/account/profile`: verificar email y los campos de perfil obtenidos de `GET /auth/me`; actualizar datos y confirmar `PUT /profiles/me` con Bearer token y persistencia tras recarga.
7. Simular un `401` de un endpoint protegido: verificar que se borra el token y se redirige a `/login`.
8. Probar errores de login/registro y de red/API: mensajes claros, sin falso estado autenticado ni pérdida silenciosa de datos.
9. Probar logout: token ausente en `localStorage`, navegación a `/login` y denegación de acceso posterior a vistas privadas.
10. Confirmar que una respuesta distinta de `401` (por ejemplo `403` o `5xx`) no se trata erróneamente como logout automático.

## Entrega

Subir la rama de implementación y abrir un pull request contra `main` del monorepo. La descripción debe especificar **qué vistas están protegidas** y confirmar explícitamente que **el website público no fue afectado**. Este archivo documenta requisitos y verificación; no sustituye la implementación ni el PR de entrega.
