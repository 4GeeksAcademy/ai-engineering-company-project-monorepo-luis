# AUTH-03 — La Pieza Que Faltaba: Flujo de Restablecimiento de Contraseña

> Guía de requisitos, contexto y verificación para el proyecto de 4Geeks **«La Pieza Que Faltaba: Flujo de Restablecimiento de Contraseña»**. Reúne las instrucciones oficiales —incluidos **«Qué Debes Hacer»** y **«Qué Vamos a Evaluar»**— y las aterriza al monorepo actual. El README oficial es la fuente de verdad ante cualquier diferencia.

## Fuentes auditadas

- Tarea 4Geeks: **The Missing Piece: Password Reset Flow**, cohorte **Authentication in web applications**, tarea `1002542`, slug `ai-eng-user-authentication-restore`, estado observado `PENDING`.
- [README oficial en español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-user-authentication-restore/README.es.md).
- [README oficial en inglés](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-user-authentication-restore/README.md).
- Contexto de la API existente: [`services/api/README.md`](./services/api/README.md).
- Aplicación Next.js existente: [`uis/talent-pipeline-tracker/README.md`](./uis/talent-pipeline-tracker/README.md), [`uis/talent-pipeline-tracker/AGENTS.md`](./uis/talent-pipeline-tracker/AGENTS.md) y [`uis/talent-pipeline-tracker/lib/api.ts`](./uis/talent-pipeline-tracker/lib/api.ts).

Las dos versiones oficiales se revisaron y contienen los mismos requisitos sustanciales. Esta guía prioriza la versión en español.

## Objetivo y alcance

Completar el ciclo de vida de contraseñas sobre la autenticación existente: recuperación para quien olvidó su contraseña y cambio para quien ya tiene sesión iniciada. La entrega abarca **API, servicio real de email transaccional y frontend**; no basta con una maqueta ni con emitir un enlace sin enviarlo.

El ticket es **AUTH-03 — Recuperación y cambio de contraseña**. Debe añadirse al monorepo existente, no a un repositorio o API paralelos. El proyecto define estos endpoints y páginas:

| Capa | Ruta | Propósito |
|---|---|---|
| API | `POST /auth/forgot-password` | Solicitar un enlace de restablecimiento por email. |
| API | `POST /auth/reset-password` | Validar el token de una sola vez y guardar la contraseña nueva. |
| API | `POST /auth/change-password` | Cambiar la contraseña de un usuario autenticado. |
| Frontend | `/forgot-password` | Solicitar el enlace; respuesta genérica para evitar enumeración. |
| Frontend | `/reset-password` | Capturar el token de la URL y enviar la contraseña nueva. |
| Frontend | `/account/change-password` | Cambiar la contraseña desde una sesión autenticada. |
| Frontend | `/login` | Mostrar enlace visible «¿Olvidaste tu contraseña?». |

## Contexto del monorepo auditado

- El backend de Nexova está en `services/api/`. La autenticación AUTH-01 ya implementa usuarios/perfiles en TinyDB, login JWT y `get_current_user`; los routers existentes están en `services/api/routers/`. Extender este servicio y mantener sus patrones, configuración y pruebas.
- El router `services/api/routers/auth.py` actualmente ofrece `POST /auth/login` y `GET /auth/me`; los endpoints AUTH-03 aún no existen en el checkout auditado. No afirmar que el flujo está implementado hasta verificarlo.
- El frontend Next.js existente está en `uis/talent-pipeline-tracker/`, pero su cliente `lib/api.ts` usa por defecto `https://playground.4geeks.com/tracker/api/v1` y hoy no integra el backend de autenticación de Nexova. Antes de implementar, decidir y documentar la integración real con el frontend adecuado; no enviar las rutas de auth a la API de Tracker por accidente ni simular un backend exitoso.
- Los requisitos oficiales piden las rutas/páginas, pero no especifican explícitamente en qué aplicación del monorepo deben vivir. Revisar las instrucciones locales de la aplicación elegida y mantener el sitio público del Hito 1 ajeno a cualquier guard de autenticación.
- La API existente requiere `JWT_SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES` al arrancar; véase `services/api/README.md`. Las claves del proveedor de email y cualquier otra credencial también deben llegar desde el entorno, no desde el código.
- No hay proveedor de email elegido ni variables AUTH-03 configuradas/documentadas todavía. Elegir **Resend o SendGrid** (son los dos servicios aceptados por el README), integrar uno y documentar el nombre exacto de su variable API en `README` o `.env.example`. No se debe publicar ni commitear una API key.

## Contrato funcional de backend

### `POST /auth/forgot-password`

- Recibe `{ "email": "..." }`.
- Si la cuenta existe, crea un token de restablecimiento firmado o aleatorio, de vida corta **entre 15 y 60 minutos**, construye un enlace a `/reset-password?token=...` y manda el email mediante Resend o SendGrid.
- Devuelve **HTTP 200 tanto si el email existe como si no**. No devolver un error, campo o mensaje que revele la existencia de la cuenta.
- El email debe incluir un enlace funcional y ser legible en móvil. Plantilla HTML es opcional; el contenido del correo y el enlace no lo son.
- Deshabilitar el formulario después del envío para evitar solicitudes duplicadas. El backend debe aplicar el comportamiento de respuesta genérica también a errores de validación de cuenta no encontrada; no confundirlo con un fallo de infraestructura del proveedor.

### `POST /auth/reset-password`

- Recibe `{ "token": "...", "new_password": "..." }`.
- Comprueba la firma/integridad, expiración y que el token no se haya usado; aplica la política de contraseñas que ya tenga la API.
- Si es válido, hashea la contraseña con el mecanismo existente y actualiza la cuenta. Invalidar el token para que no se pueda volver a usar.
- Devuelve **HTTP 400** para token inválido, expirado o ya utilizado. No revelar detalles que ayuden a validar tokens.
- Redirigir desde el frontend a `/login` tras éxito; token inválido/expirado debe producir un error entendible y permitir volver a `/forgot-password`.

### `POST /auth/change-password`

- Requiere access token válido en `Authorization: Bearer <token>`.
- Recibe `{ "current_password": "...", "new_password": "..." }`.
- Verifica la contraseña actual antes de persistir la nueva, hashea la nueva con la implementación existente y no devuelve ni registra contraseñas o hashes.
- Devuelve **HTTP 400** cuando la contraseña actual no coincide.
- La operación solo afecta al usuario identificado por la sesión autenticada; no aceptar un ID de usuario arbitrario en el cuerpo.

## Requisitos de seguridad para los tokens

- El token de recuperación es distinto de la sesión normal, de alcance limitado a restablecer contraseña y de corta duración. No debe permitir autenticarse en rutas protegidas.
- La expiración debe estar entre 15 y 60 minutos. **La expiración por sí sola no impide reutilizar un JWT**: conservar estado en el servidor para hacer cumplir el uso único (por ejemplo, registro del token hasheado/usado o marca temporal de cambio de contraseña, según se adapte al diseño existente).
- Guardar tokens de reset en el servidor solo de forma segura (preferiblemente hash si se persisten); compararlos de manera segura y marcar/inutilizar el token en el cambio exitoso. Considerar solicitudes concurrentes para que el mismo token no pueda consumirse dos veces.
- No incluir API keys, tokens ni contraseñas en el repositorio, respuestas de error, logs, telemetría o capturas. No imprimir el token de reset ni guardar la contraseña en almacenamiento persistente del navegador.
- El mensaje de confirmación de «forgot password» debe ser idéntico para correo existente e inexistente para prevenir enumeración. Evitar que respuestas, latencia claramente distinta o errores de envío expongan directamente si una cuenta existe.
- El enlace contiene un secreto de un solo uso: evitar registrarlo en logs/analytics, no exponerlo a terceros mediante recursos externos/referrer y retirarlo de la URL al capturarlo si la arquitectura lo permite.

## Requisitos de frontend

### `/forgot-password`

- Formulario accesible con campo de email y validación básica.
- Llamar a `POST /auth/forgot-password` y mostrar siempre una confirmación genérica equivalente a: **«Si esa dirección está registrada, recibirás un enlace en breve»**.
- Desactivar el formulario o botón tras el envío para evitar solicitudes duplicadas.
- Manejar errores de red/servicio sin mostrar si la cuenta existe ni fingir que se envió el correo si la operación falló técnicamente.

### `/reset-password`

- Leer `token` del query string de la URL.
- Formulario con contraseña nueva y confirmación; validar que ambas coincidan antes de llamar a la API.
- Enviar `token` y `new_password` a `POST /auth/reset-password`.
- Si la operación termina correctamente, redirigir a `/login` con feedback de éxito.
- Si el token falta, es inválido o expiró, mostrar un mensaje claro y enlace para volver a `/forgot-password`.

### `/account/change-password`

- Vista autenticada con campos de contraseña actual, nueva y confirmación de la nueva.
- Validar que nueva contraseña y confirmación coinciden antes de enviar.
- Llamar a `POST /auth/change-password` con Bearer token de la sesión.
- Mostrar feedback de éxito/error. Una contraseña actual incorrecta debe representarse como error de formulario, no como éxito.

### Página `/login`

- Añadir un enlace visible **«¿Olvidaste tu contraseña?»** que apunte a `/forgot-password`.

### Accesibilidad y UX

- Etiquetas asociadas, foco y navegación por teclado, mensajes de validación vinculados a los campos y estados de carga/envío.
- No filtrar contraseñas en mensajes, consola o URL. Usar campos de tipo password y no persistir credenciales.
- No convertir fallos de red/servidor en estados de éxito. Mantener el comportamiento existente de login y otras rutas.

## Variables de entorno y email

- Elegir **Resend o SendGrid** e integrar el envío real en el backend.
- Configurar la API key por variable de entorno. Documentar el **nombre exacto** de la variable en el README de la API o en `.env.example`; el nombre concreto queda pendiente de la selección del proveedor y no debe inventarse como si ya estuviera configurado.
- Documentar remitente/requisitos de configuración que correspondan al servicio seleccionado, sin incluir claves reales.
- Asegurarse de que `.env` está excluido por Git antes de almacenar credenciales localmente. Versionar únicamente un `.env.example` con nombres de variables y valores placeholder no secretos.
- La entrega final debe indicar qué proveedor se eligió, qué variable de entorno hace falta y confirmar que se probó el flujo end-to-end.

## Qué debes hacer — checklist consolidado

### Backend

- [ ] Implementar `POST /auth/forgot-password` con payload `{ email }`.
- [ ] Para emails existentes, generar token seguro de corta duración (15–60 minutos), crear enlace `/reset-password?token=...` y enviar email real por Resend o SendGrid.
- [ ] Responder siempre `200` desde forgot-password independientemente de si la dirección está registrada; evitar enumeración.
- [ ] Implementar `POST /auth/reset-password` con `{ token, new_password }`.
- [ ] Validar token (firma/integridad, expiración y no usado); actualizar contraseña con hash existente e invalidar el token tras éxito.
- [ ] Devolver `400` para token inválido, expirado o reutilizado.
- [ ] Implementar `POST /auth/change-password` protegido por Bearer; verificar contraseña actual antes de cambiarla.
- [ ] Devolver `400` si la contraseña actual es incorrecta.
- [ ] Integrar un servicio de email transaccional elegido entre Resend y SendGrid; el correo incluye enlace legible en móvil.
- [ ] Guardar la API key del proveedor exclusivamente en entorno y documentar el nombre de la variable en README o `.env.example`.

### Frontend

- [ ] Crear `/forgot-password`, enviar email y mostrar confirmación genérica; desactivar el formulario tras el envío.
- [ ] Crear `/reset-password`, leer el token de la query URL, validar confirmación y enviar el reset a la API.
- [ ] En reset exitoso, redirigir a `/login` con mensaje de éxito.
- [ ] Ante token inválido/expirado, mostrar error claro y enlace a `/forgot-password`.
- [ ] Crear `/account/change-password` con contraseña actual, nueva y confirmación; validar coincidencia, llamar API y mostrar feedback.
- [ ] Añadir enlace «¿Olvidaste tu contraseña?» en `/login`.
- [ ] Usar las rutas del backend real de Nexova y enviar Bearer token en el cambio autenticado; no conectar accidentalmente al endpoint de Tracker ni simular la integración.

### Seguridad y entrega

- [ ] Verificar expiración (15–60 minutos) y uso único de tokens de reset.
- [ ] Verificar que las respuestas de forgot-password no permiten distinguir cuentas existentes/inexistentes.
- [ ] Confirmar que contraseñas, tokens y API keys no se guardan en código, respuestas/logs ni commits.
- [ ] Ejecutar pruebas automatizadas y flujo end-to-end completo.
- [ ] Subir la rama de feature y abrir PR contra `main` del monorepo.
- [ ] En la descripción del PR, indicar proveedor de email, variable de entorno y evidencia de prueba end-to-end.

## Qué vamos a evaluar — criterios de aceptación

- [ ] `POST /auth/forgot-password` envía un email real con el enlace si la dirección existe.
- [ ] `POST /auth/forgot-password` devuelve `200` para una dirección inexistente y no filtra información de registro.
- [ ] El token expira en la ventana configurada y no funciona después de expirar.
- [ ] `POST /auth/reset-password` cambia la contraseña e invalida el token tras éxito.
- [ ] `POST /auth/reset-password` devuelve `400` para token expirado o ya utilizado (también cubrir token inválido).
- [ ] `/forgot-password` muestra confirmación tras enviar, independientemente de si el email existe.
- [ ] `/reset-password` toma el token de la URL, envía el formulario y redirige a `/login` cuando tiene éxito.
- [ ] `/reset-password` presenta error claro y enlace a `/forgot-password` ante token inválido/expirado.
- [ ] `/login` muestra un enlace visible a «¿Olvidaste tu contraseña?».
- [ ] `/account/change-password` valida coincidencia de nueva contraseña/confirmación, llama a la API y comunica éxito/error.
- [ ] `POST /auth/change-password` requiere autenticación válida y devuelve `400` ante contraseña actual incorrecta.
- [ ] Ninguna API key está hardcodeada; los secretos se cargan desde el entorno.
- [ ] La integración envía email real a una cuenta de prueba y se demuestra el recorrido completo: solicitar → recibir enlace → restablecer → iniciar sesión con la contraseña nueva; además se verifica el cambio con sesión iniciada.

## Matriz mínima de pruebas recomendada

### Backend

- Email existente y no existente en forgot-password: ambos `200` y mensaje público equivalente; solo el caso existente genera/envía enlace.
- Email malformado, fallo del proveedor de email y errores operativos: respuesta segura, sin filtrar existencia ni secretos; documentar la política para fallos de infraestructura.
- Token válido: cambia la contraseña y permite login con la nueva; la antigua deja de autenticar.
- Token inválido, manipulado, expirado, ya consumido o ausente: rechazo con `400`; no cambia la contraseña.
- Dos intentos concurrentes con el mismo token: solo uno puede completar el cambio.
- Change-password con sesión válida y contraseña correcta: éxito; contraseña incorrecta: `400`; sin token: `401`; token inválido/expirado: `401`.
- Comprobar que hashes/contraseñas/tokens no aparecen en respuestas ni logs y que la API key no forma parte del árbol Git.

### Frontend / integración

- Solicitud de reset para email existente e inexistente: mismo feedback visible; botón desactivado al enviar.
- Enlace real de email abre `/reset-password?token=...`; contraseña confirmada permite completar y redirige al login.
- Enlace inválido/expirado/usado y query sin token producen error claro y retorno a forgot-password.
- Login muestra enlace de recuperación.
- Cambio autenticado: Bearer presente, confirmación de contraseña validada antes de llamar, feedback de éxito/error correcto.
- Revisar estados de carga, fallos de red, navegación teclado y que contraseñas no quedan en URL/localStorage/logs.

## Fuera del alcance obligatorio

El README considera opcionales: plantilla de email HTML (un email legible en móvil sí es obligatorio), rate limiting por email para limitar abuso y registro/auditoría de eventos de reset. Implementarlos solo si no comprometen los criterios obligatorios.

## Entrega

Crear la rama indicada por el README oficial (`feature/password-reset`) desde la base actualizada y abrir un PR hacia `main` del repositorio transversal. El PR debe resumir qué se implementó, nombrar el proveedor elegido, documentar la variable de entorno necesaria y confirmar explícitamente la prueba completa end-to-end.

**Estado de auditoría:** este documento captura y organiza requisitos; no implementa AUTH-03 ni sustituye las pruebas o el PR de entrega. Al comenzar la implementación, volver a revisar el README oficial, el estado de `git`, las instrucciones de las carpetas tocadas y la configuración de secretos.
