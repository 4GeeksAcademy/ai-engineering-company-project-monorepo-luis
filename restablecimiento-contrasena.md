# AUTH-03 — La Pieza Que Faltaba: Flujo de Restablecimiento de Contraseña

> Guía de requisitos, contexto y verificación para el proyecto de 4Geeks **«La Pieza Que Faltaba: Flujo de Restablecimiento de Contraseña»**. Reúne las instrucciones oficiales —incluidos **«Qué Debes Hacer»** y **«Qué Vamos a Evaluar»**— y las aterriza al monorepo actual. El README oficial es la fuente de verdad ante cualquier diferencia.

## Fuentes auditadas

- Tarea 4Geeks: **The Missing Piece: Password Reset Flow**, cohorte **Authentication in web applications**, tarea `1002542`, slug `ai-eng-user-authentication-restore`, estado observado `PENDING`.
- [README oficial en español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-user-authentication-restore/README.es.md).
- [README oficial en inglés](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-user-authentication-restore/README.md).
- Contexto de la API existente: [`services/api/README.md`](./services/api/README.md).
- Aplicación Next.js existente: [`uis/talent-pipeline-tracker/README.md`](./uis/talent-pipeline-tracker/README.md), [`uis/talent-pipeline-tracker/AGENTS.md`](./uis/talent-pipeline-tracker/AGENTS.md) y cliente de autenticación [`uis/talent-pipeline-tracker/lib/nexova-api.ts`](./uis/talent-pipeline-tracker/lib/nexova-api.ts).

Las dos versiones oficiales se revisaron y contienen los mismos requisitos sustanciales. Esta guía prioriza la versión en español.

Revisión de etapa 1, 2026-10-18: se volvió a consultar íntegramente el README oficial en español. Los endpoints, páginas, proveedores admitidos, expiración, uso único y entrega coinciden con esta guía. La cadena aleatoria persistida es una alternativa admitida al JWT firmado. No se modifican los criterios de aceptación.

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
- El router `services/api/routers/auth.py` conserva login/me y, desde la etapa 3, implementa `POST /auth/forgot-password`, `POST /auth/reset-password` y `POST /auth/change-password`. Sus contratos se verificaron con datos sintéticos y correo simulado; no equivalen todavía a un flujo frontend ni a recepción real de Resend.
- AUTH-02 ya integra el backend Nexova en `uis/talent-pipeline-tracker/`: existen `/login`, `/register`, `/account/profile`, gestión de sesión y guard. El cliente `lib/nexova-api.ts` utiliza `NEXT_PUBLIC_NEXOVA_API_URL`; `lib/api.ts` y `NEXT_PUBLIC_API_URL` siguen dedicados a la API externa de candidatos. Añadir AUTH-03 al cliente Nexova, nunca a la API de Tracker.
- Las nuevas páginas vivirán en esa aplicación Next.js, reutilizando login, sesión y patrones de formularios. Desde la etapa 4, guard y listener comparten una política que protege `/account/change-password` y mantiene públicas `/forgot-password` y `/reset-password`, sin redirigirlas por eventos de una sesión anterior expirada. Las páginas se crearán en etapas 5–6; el sitio público y el backoffice no se modifican.
- La API existente requiere `JWT_SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES` al arrancar; véase `services/api/README.md`. Las claves del proveedor de email y cualquier otra credencial también deben llegar desde el entorno, no desde el código.
- El proveedor elegido es **Resend** y su cliente HTTP está integrado. `RESEND_API_KEY` y las demás variables de recuperación se leen del entorno al aceptar una solicitud forgot-password; su configuración y validación se documentan en el README de la API. No se configuraron credenciales reales ni se probó recepción; no se lee/modifica `.env*` ni se conecta Resend sin autorización específica.

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

- Integrar **Resend**, seleccionado entre los dos proveedores admitidos.
- Configurar la API key exclusivamente mediante `RESEND_API_KEY` en el entorno del backend. Su nombre y las demás variables implementadas se documentan en el [README de la API](./services/api/README.md#auth-03-password-recovery-plan); el entorno sintético de los tests no equivale a configurar o probar credenciales reales.
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

## Plan de trabajo por etapas

### Base y decisiones de implementación

- El 2026-10-18, `feature/password-reset` ya existe y parte de `origin/main` en `78d8678`, que incorpora AUTH-02. Su HEAD inicial es `65f4656`, con los requisitos y una eliminación documental anteriores a esta etapa. Tras `git fetch origin`, la rama contiene la base remota y el árbol inicial está limpio. No recrear la rama ni restaurar documentos eliminados.
- Extender exclusivamente la API existente y la autenticación del tracker. Mantener los contratos de login, registro, perfiles, proveedores e incidencias; no modificar `CONTEXT.md`, `SPEC.md` ni la web pública.
- Emitir un token opaco con `secrets.token_urlsafe(32)`, persistir solo su digest SHA-256 y estado mínimo asociado al usuario y vencimiento, y comparar de forma segura. Duración por defecto: 30 minutos, configurable únicamente entre 15 y 60. No usar un access token como token de recuperación.
- Una nueva emisión invalida los enlaces anteriores del usuario. Restablecer la contraseña y consumir los tokens pendientes debe ser una única operación dentro de `open_auth_database`, sin escrituras parciales. Probar dos consumos concurrentes: solo uno puede tener éxito. El bloqueo existente solo garantiza coordinación en un proceso/worker; no ampliar a producción multiworker.
- Invalidar resets pendientes también ante cambios de contraseña/email, desactivación o eliminación mediante las operaciones existentes. Conservar el contrato JWT actual: el cambio de contraseña no revoca automáticamente los access tokens emitidos; la revocación general de sesiones queda fuera de alcance.
- Reutilizar bcrypt y su política actual: mínimo 8 caracteres, máximo 72 bytes UTF-8 y sin bytes nulos ni truncamiento. Sanear errores de validación de las nuevas rutas para no reflejar contraseñas o tokens.

### Política de correo acordada

Para el alcance local/demo se acepta envío en segundo plano, sin cola durable ni garantía de reintentos. Un `200` confirma la aceptación de la solicitud, no la recepción del correo. Buscar la cuenta, emitir el token y enviar el email fuera del camino de respuesta evita que la espera de Resend dependa públicamente de si existe la cuenta. No mantener el bloqueo de TinyDB durante llamadas de red.

Para emails sintácticamente válidos, existentes o no, el cuerpo y estado públicos serán iguales. Email malformado recibirá validación genérica sin eco de datos. Si falta configuración o no se puede aceptar la tarea, se devolverá un fallo operativo común, independiente de la cuenta; la UI no mostrará éxito ante ese rechazo o un fallo de red. Los fallos posteriores de Resend se registrarán sin secretos ni datos personales, sin informar al solicitante si la cuenta existe ni afirmar que el correo fue enviado. Un reinicio puede perder tareas pendientes y requerir otra solicitud. La aceptación final exige igualmente comprobar un email real recibido.

### Tablero de control

Estados: **Pendiente**, **En curso**, **En revisión**, **Publicada** o **Bloqueada**. Una etapa solo queda Publicada tras verificar el push. No rellenar SHA o evidencia antes de ejecutar la operación correspondiente.

| Etapa | Entregable y criterio de cierre | Estado | Evidencia | Commit | Push |
|---|---|---|---|---|---|
| 1. Base, contratos y control | Contrastar README oficial, Git y AUTH-02; actualizar esta guía, configuración prevista y memoria; ejecutar baseline. | Publicada | 2026-10-18: baseline y revisión correctos; publicación aprobada y verificada. | `0ac5d4f` | Verificado; rama sincronizada |
| 2. Dominio seguro | Tokens hasheados, expiración, invalidación y cambio coordinado; pruebas de uso único, concurrencia y fallo de persistencia. | Publicada | 2026-10-18: 127 tests OK; publicación aprobada y verificada. | `1997bce` | Verificado; rama sincronizada |
| 3. API y Resend | Tres endpoints y cliente Resend integrados; pruebas HTTP y de transporte simulado, errores seguros y regresiones backend. | Publicada | 2026-10-18: 155 tests OK; publicación aprobada y verificada. Sin correo real todavía. | `a4429d2` | Verificado; rama sincronizada |
| 4. Cliente y acceso frontend | Tipos y métodos en cliente Nexova; recovery público y cambio protegido; navegación de sesión, lint y build. | En revisión | 2026-10-18: lint/build, diagnósticos, SDK simulado y contra Uvicorn real, smoke HTTP correctos. | Pendiente de aprobación | Pendiente |
| 5. Recuperación pública | Forgot/reset, enlace desde login, confirmación y errores accesibles; token solo en memoria y URL limpiada; verificación en navegador. | Pendiente | Pendiente | Pendiente | Pendiente |
| 6. Cambio autenticado | Página y acceso desde perfil, Bearer, verificación de contraseña actual, confirmación y feedback; pruebas de éxito y errores. | Pendiente | Pendiente | Pendiente | Pendiente |
| 7. Aceptación y entrega | Recepción real de Resend, recorrido completo y regresiones; evidencias saneadas y documentación; PR a `main` previa autorización. | Pendiente | Pendiente | Pendiente | Pendiente |

### Validaciones y evidencias esperadas

- **Etapa 1:** suite backend y lint/build del tracker para conocer el punto de partida; revisar enlaces documentales y `git diff --check`. No confundir baseline con pruebas de AUTH-03, aún inexistente.
- **Etapas 2–3:** unittest con cuentas sintéticas, bases temporales y reloj controlado, sin esperas artificiales. Cubrir token inválido, faltante, expirado, consumido, concurrente y rechazo cruzado JWT/reset; cambio autorizado/401/contraseña incorrecta 400; respuestas genéricas, proveedor fallido y ausencia de secretos. No llamar Resend real en unit tests.
- **Etapas 4–6:** `npm run lint` y `npm run build` desde el tracker, más pruebas dirigidas de llamadas y navegación en navegador contra Nexova. Comprobar móvil/escritorio, teclado, etiquetas, foco, estados de carga y errores de red. No existe script de tests frontend declarado; registrar si la prueba es manual o automatizada.
- **Etapa 5:** quitar el token de la URL tras capturarlo y no persistirlo; recargar la URL limpia requiere reabrir el enlace. Aplicar política de referrer y evitar recursos externos/analytics en reset. La limpieza posterior no elimina la petición inicial: revisar logs de servidor/proxy y no capturar URLs secretas en trazas o screenshots.
- **Etapa 7:** solicitar, recibir el email real, abrir el enlace, restablecer, iniciar sesión con la nueva y rechazar la antigua; rechazar reutilización y probar cambio autenticado. Verificar expiración con reloj controlado sin reducir el TTL permitido. Si no se recibe correo, la aceptación queda Bloqueada, no completada.
- Comandos y configuración: [README API](./services/api/README.md#auth-03-password-recovery-plan) y [README tracker](./uis/talent-pipeline-tracker/README.md#validation). No ejecutar checks de aplicaciones ajenas ni inventar scripts.

### Cierre obligatorio por etapa

1. Completar solo el alcance de la etapa, ejecutar sus comprobaciones y registrar resultados reales y limitaciones.
2. Actualizar README y banco de memoria, revisar el diff y archivos sensibles/generados sin imprimir secretos; conservar cualquier cambio ajeno.
3. Presentar archivos y mensaje propuesto al usuario con estado **LISTO PARA REVISIÓN**, **NO LISTO** o **BLOQUEADO**. Esperar aprobación explícita antes de commit y push.
4. Con aprobación, usar staging selectivo, revisar el diff preparado, crear un commit descriptivo y hacer push a la misma `feature/password-reset`. Registrar SHA y resultado remoto antes de pasar a Publicada. No hacer force-push ni merge a `main`.
5. La PR final y la configuración de secretos/servicios externos requieren autorización propia. No avanzar automáticamente a la siguiente etapa.

Mensajes previstos: `docs(auth): define AUTH-03 stages and contracts`, `feat(auth): add single-use password reset tokens`, `feat(auth): expose password recovery and change endpoints`, `feat(auth-ui): add password API client and route access`, `feat(auth-ui): implement password recovery screens`, `feat(auth-ui): add authenticated password change` y `test(auth): verify password lifecycle end to end`.

### Registro de etapa 1 — 2026-10-18

- **LISTO PARA REVISIÓN:** solo documentación y contratos; commit y push pendientes de aprobación. Ningún endpoint o formulario AUTH-03 implementado y ninguna prueba de email real realizada.
- `git fetch origin` y revisión de historial: `origin/main` en `78d8678` es ancestro de HEAD `65f4656`; la rama ya contiene AUTH-01 y AUTH-02. Se conserva la rama existente y sus dos commits previos. El árbol estaba limpio al iniciar.
- `uv run --locked --project services/api python -m unittest discover -s services/api/tests`: **100 tests OK**. Advertencia preexistente de Starlette sobre httpx; sin cambios de dependencias.
- `npm run lint` y `npm run build`, ejecutados mediante `npm --prefix uis/talent-pipeline-tracker`: **correctos**, con comprobación TypeScript integrada en build. Rutas generadas: login, register y perfil existentes; todavía no hay páginas AUTH-03.
- Next.js mantiene la advertencia de raíz Turbopack inferida por varios lockfiles y carga automáticamente `.env.local` durante build. No se inspeccionó ni modificó su contenido ni se imprimieron sus valores.
- `git diff --check`: correcto. Los enlaces documentales nuevos tienen destino; sigue una referencia histórica preexistente a `autenticacion.md` en el README de la API, documento ya eliminado y fuera del alcance de esta etapa.
- La revisión de exclusiones detectó que `services/api/.env` no estaba ignorado. Se añadieron `.env` y `.env.*` al `.gitignore` raíz, con excepción para `.env.example`. `git check-ignore --no-index --verbose` confirmó las exclusiones y la excepción de la plantilla API, sin abrir ni crear archivos de entorno. La base de auth y el entorno local del tracker ya estaban ignorados.
- La instrucción global de 4Geeks no pudo leerse por exclusión de Copilot; se aplicaron `AGENTS.md`, reglas y skill de validación del repositorio. La retirada intencional de `ingenieria-ia.md` ya está documentada en el banco de memoria; no se recreó.
- No se modificó código, configuración de ejecución, dependencias ni el briefing; además de documentación, solo cambió la exclusión preventiva de Git. No se configuraron credenciales ni se conectó Resend. Las pruebas de navegador y la aceptación end-to-end pertenecen a las etapas funcionales posteriores.

### Registro de etapa 2 — 2026-10-18

- **LISTO PARA REVISIÓN:** capa interna implementada; no hay endpoints AUTH-03, envío de correo ni cambios frontend. Commit y push de esta etapa pendientes de aprobación. La etapa 1 se publicó con aprobación en `0ac5d4f` y quedó sincronizada con su remoto.
- `password_reset_service.py` ofrece `issue_password_reset_token`, `reset_password` y `change_password`. `PasswordResetRecord` valida identidad y vencimiento con zona horaria; su digest usa `SecretStr` y queda fuera de repr/serialización normal.
- Emisión para email normalizado y usuario activo; desconocido/inactivo devuelve `None`. Lifetime explícito entero de 15–60 minutos, default 30, todavía sin leer entorno. Token de 32 bytes aleatorios; solo digest SHA-256, `user_id` y vencimiento UTC persisten en la tabla opcional `password_reset_tokens` de la base auth existente. Una fila por usuario reemplaza el enlace anterior y la emisión limpia registros vencidos.
- Consumo con comparación `hmac.compare_digest`, verificación de cuenta vigente/activa y expiración estricta. Hash de contraseña, actualización e invalidación se completan en un solo snapshot. La verificación de contraseña actual en `change_password` también ocurre bajo el mismo bloqueo, evitando aceptar dos cambios con la contraseña antigua.
- `update_user` invalida resets al recibir password/email o desactivación, y `delete_user` los elimina junto a cuenta/perfil. No se invalidan por edición de perfil/rol ni se afecta a otro usuario. Cualquier fallo de commit conserva contraseña y token previos; no hay nueva garantía multiworker ni revocación de JWTs.
- Pruebas focales ejecutadas y repetidas tras el último ajuste: **23 reset + 21 usuarios OK**. Incluyen expiración exacta/reapertura, tokens alterados, límites de duración y contraseña UTF-8, reemplazo/limpieza, cuentas borradas/inactivas, concurrencia de reset y cambio autenticado, aislamiento y fallos de persistencia en emisión/reset/cambio/actualización/borrado.
- Suite backend completa: **127 tests OK**, frente a 100 de baseline. `uv lock --check --project services/api`, diagnósticos de los seis archivos Python y `git diff --check` correctos. Persiste solo el aviso conocido de Starlette/httpx; no hay dependencias nuevas ni checks frontend pertinentes a esta etapa.
- Datos y bases exclusivamente sintéticos/temporales. Sin `.env*`, secretos reales, Resend ni cambios en routers. Las respuestas HTTP, el saneamiento de nuevos payloads y la integración email pertenecen a la etapa 3; sus criterios de aceptación siguen sin marcar.

### Registro de etapa 3 — 2026-10-18

- **LISTO PARA REVISIÓN:** endpoints y cliente Resend implementados; commit y push pendientes de aprobación. La etapa 2 fue aprobada y publicada en `1997bce`, con push verificado antes de comenzar esta etapa.
- `POST /auth/forgot-password`: valida email y configuración común, acepta una tarea `BackgroundTasks` y devuelve el mismo `200` y mensaje para cuentas existentes/desconocidas/inactivas. La búsqueda, emisión y llamada de correo ocurren después de enviar el cuerpo público, comprobado con una prueba ASGI. Un fallo previo de configuración/aceptación devuelve `503` común; un fallo posterior se registra sin datos sensibles ni traceback, sin convertirlo en señal pública de existencia.
- `POST /auth/reset-password`: JSON con token y contraseña nueva; token inválido, faltante, nulo, expirado o consumido devuelve `400` genérico. La política de contraseña se valida antes de mutar; resto de payload inválido/malformado devuelve `422` saneado. Persiste/invalida usando el servicio de etapa 2; fallo operativo de persistencia devuelve `503`, conserva el token y no cambia la contraseña.
- `POST /auth/change-password`: requiere Bearer, deriva ID de `get_current_user` y revalida la cuenta al cambiar. Contraseña actual incorrecta `400`; credencial ausente/inválida/expirada o cuenta ya inexistente/inactiva `401`; IDs extra rechazados `422`; fallo operativo `503`. Solo modifica al usuario de la sesión.
- Esquemas `ForgotPasswordRequest`, `ResetPasswordRequest`, `ChangePasswordRequest` y `AuthActionResponse`; inputs sensibles con `SecretStr`. El handler sanea únicamente las nuevas rutas, conservando contratos previos de login/users y operaciones.
- `email_service.py` usa httpx ya disponible: `POST https://api.resend.com/emails`, API key exclusivamente en cabecera, enlace de origen confiable, texto plano legible, timeout de 10 segundos por fase, sin redirecciones, proxy de entorno ni reintentos. No registra destinatario, mensaje, URL de reset, tokens, contraseñas, claves o errores crudos del proveedor.
- Configuración validada por solicitud forgot-password, sin lectura de `.env`: key no vacía ASCII imprimible sin espacios, remitente email simple autorizado, origen HTTPS sin credenciales/ruta/query/fragment (HTTP solo loopback) y expiración entera 15–60/default30. Si falta o es inválida, forgot responde `503` para cualquier cuenta; login y el resto de API siguen operativos. Reset y cambio no dependen de Resend configurado.
- Pruebas focales: **5 email + 23 HTTP OK**, con remitentes/destinatarios sintéticos, TinyDB temporal y `httpx.MockTransport` o sender inyectado; ninguna conexión real. Incluyen payload/link, límites/config, fallos proveedor/timeout, orden ASGI, no enumeración, validación sin eco, JWT/reset no intercambiables, autorización y concurrencia HTTP con un solo éxito.
- Suite backend completa: **155 tests OK**, `uv lock --check --project services/api`, diagnósticos de seis archivos Python y `git diff --check` correctos. Sin dependencias nuevas ni cambios frontend; no procede lint/build del tracker. El aviso Starlette/httpx conocido permanece.
- Los criterios de email recibido, pantallas y flujo completo siguen pendientes. BackgroundTasks no es cola durable: reinicios pueden perder solicitudes y los errores posteriores no se notifican al solicitante. La entrega final requerirá configuración autorizada y recepción real en la etapa 7.

### Registro de etapa 4 — 2026-10-18

- **LISTO PARA REVISIÓN:** tipos, métodos del cliente y acceso a rutas preparados. Sin nuevas pantallas, cambios backend, dependencias, staging, commit ni push de esta etapa. La etapa 3 se publicó con aprobación en `a4429d2` y quedó sincronizada antes de empezar.
- Añadidos inputs `NexovaForgotPasswordInput`, `NexovaResetPasswordInput`, `NexovaChangePasswordInput` y respuesta `NexovaAuthActionResponse`. Métodos `requestNexovaPasswordReset`, `resetNexovaPassword` y `changeNexovaPassword` reutilizan `request<T>` y el origen Nexova separado; forgot/reset públicos sin Bearer, cambio con Bearer.
- `lib/nexova-auth-routes.ts` centraliza la política compartida por guard y listener: login/register/forgot/reset públicos; cambio de contraseña protegido junto a vistas privadas existentes. Un evento de expiración en una vista pública no la abandona; un 401 protegido conserva el cierre/redirección anterior.
- No se persisten contraseñas ni tokens de reset; payloads solo JSON. Errores públicos no borran sesión, fallos de red/403/5xx tampoco. Sin token, el cambio falla localmente antes del fetch. El reset público no realiza todavía navegación ni limpia la sesión previa: corresponde a la pantalla de etapa 5.
- `npm run lint` y `npm run build` del tracker: **correctos**, incluido TypeScript de build; diagnósticos de cinco archivos sin errores y `git diff --check` correcto. Next conserva advertencia de múltiples lockfiles y carga automática del entorno local sin inspección ni impresión de valores.
- Prueba dirigida en memoria del SDK: URL, JSON, Bearer, matriz de errores y almacenamiento correctos. Comprobados ocho paths y listener/cleanup con hooks simulados; no constituye interacción real en navegador. El arnés inicial usó por defecto ES5 y alteró `instanceof Error`; la prueba discriminante confirmó que el target ES2017 del proyecto lo conserva. Se corrigió solo el arnés, sin cambiar código de producción por ese motivo.
- Recorrido SDK → Uvicorn real efímero: forgot para cuenta existente/desconocida con mismo feedback, reset, login, auth/me, contraseña actual incorrecta, cambio autenticado, login nuevo y rechazo de anterior/reuso **correctos**. Sender simulado, cuenta/secretos/base temporales; tokens transmitidos por stdin sin logs. Servidor API detenido y datos eliminados.
- Next dev iniciado en `http://localhost:3000` para esta sesión, apuntando al API habitual de puerto 8000; el API efímero anterior ya no está activo. Smoke HTTP: `/login`, `/register` y `/account/profile` responden 200 con formularios/loader esperados. No hay páginas AUTH-03 nuevas todavía; la suite backend no se repitió porque su código no cambió.
- El cliente Resend y los endpoints permanecen como en etapa 3; no se leyó/modificó `.env*` manualmente ni se enviaron emails reales. UI, interacción de navegador y recepción real siguen pendientes de etapas 5–7.

**Estado de auditoría:** etapas 1–3 publicadas y 4 en revisión. Cliente AUTH-03 y política de acceso integrados, pero todavía sin pantallas de recuperación/cambio, recepción real de email, aceptación end-to-end o PR.
