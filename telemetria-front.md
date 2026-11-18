# Telemetría de Nexova — Captura en el frontend

> Instrucciones del proyecto de 4Geeks Academy para la siguiente fase de Application Telemetry. Este documento adapta los requisitos oficiales al monorepo y al backoffice actual de Nexova.
>
> **Proyecto oficial:** [Telemetría de tu compañía – Captura en el frontend (README en español)](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-telemetry-capture/README.es.md)
> **Briefing de Nexova:** [briefings de telemetría de 4Geeks](https://github.com/4GeeksAcademy/ai-engineering-syllabus/tree/main/content/contexts/06-telemetry-data-pipelines/telemetry)
> **Contrato previo obligatorio:** [`docs/telemetry/telemetry-plan.md`](docs/telemetry/telemetry-plan.md) y [`docs/telemetry/event-schemas.json`](docs/telemetry/event-schemas.json).
>
> **Prerrequisito:** la Fase 1 debe estar aprobada antes de implementar. El plan define 19 eventos (5 obligatorios del briefing y 14 oportunidades identificadas), sus allowlists, el envelope, privacidad, categorización y estrategia de entrega. Ese contrato prevalece sobre nombres o ejemplos genéricos del README oficial.

---

## 🎯 Reto

Implementa la captura de telemetría del backoffice de Nexova. Cada evento debe generarse cuando ocurre su transición real, pasar por una única función `track()`, acumularse en una cola en memoria y enviarse al backend en lotes. No envíes un request por evento.

También se implementará un receptor temporal en FastAPI para comprobar el formato y el flujo. El stub valida el envelope y responde `200`, pero **no persiste eventos**: la persistencia real pertenece a la fase posterior.

El frontend actual de este monorepo está en `uis/backoffice/` y es una aplicación estática JavaScript/HTML (no presupongas Next.js ni crees otro frontend). El backend FastAPI está en `services/api/`. Integra la solución con esa estructura y conserva el comportamiento existente del backoffice.

### Reglas de arquitectura

- La llamada pública de instrumentación es `track(eventType, properties)`. Ningún componente o módulo funcional debe llamar `fetch`/`axios` para telemetría directamente.
- Captura la hora del evento al crearlo, no al vaciar la cola.
- El frontend usa la URL configurable del receptor; no hardcodees una URL dentro de componentes. El README de 4Geeks nombra `NEXT_PUBLIC_TELEMETRY_ENDPOINT`; como el backoffice de este repo no usa Next.js, documenta y usa una configuración equivalente compatible con el despliegue estático, o adapta el mecanismo sin exponer secretos. El browser no debe recibir credenciales privadas.
- El backend declara `TELEMETRY_ENDPOINT` en la configuración de entorno requerida por el proyecto, aunque el stub no redirija ni persista tráfico.
- No mezcles datos de uso con el perfil o los datos persistentes de empleados.
- Mantén las propiedades exactamente dentro del allowlist del evento en `event-schemas.json`. No inventes claves ni uses los ejemplos genéricos del README en lugar del contrato de Nexova.

---

## 🌱 Cómo empezar

1. Confirma que los entregables aprobados existen en `docs/telemetry/` y léelos completos. Consulta también el briefing de Nexova enlazado en el plan.
2. Revisa la organización actual: `uis/backoffice/` (HTML/JS y autenticación/inventario) y `services/api/` (FastAPI, routers, configuración y pruebas). Lee los README de ambas áreas antes de editar.
3. Revisa cómo la API representa entradas/salidas, rechazos y validaciones. Los eventos que describen una decisión del servidor deben corresponder al resultado confirmado por el servidor y no duplicarse por reintentos o por la respuesta y un listener del mismo flujo.
4. Define cómo se suministrará la URL configurable a la aplicación estática y configura `TELEMETRY_ENDPOINT` para el backend siguiendo sus convenciones de configuración. No leas, imprimas ni agregues secretos del `.env` al repositorio.
5. Implementa en este orden: **stub FastAPI → TelemetryService → instrumentación → verificación de extremo a extremo**. No instrumentes componentes antes de tener una función `track()` funcional.
6. Prueba con datos sintéticos/locales; no envíes datos de candidatos, clientes, consultores o personal real a un servicio de telemetría.

---

## 💻 Qué debes hacer

### Fase 1 — Endpoint stub en FastAPI

El endpoint es provisional y sirve para comprobar el contrato de transporte. No añadas almacenamiento ni cambies el comportamiento funcional de inventario.

- [ ] Crea un router propio en `services/api/` con `POST /telemetry/events`.
- [ ] Acepta un objeto con forma `{ "events": [...] }` y define modelos Pydantic para el lote y `TelemetryEvent`.
- [ ] `TelemetryEvent` incluye los ocho campos del envelope aprobado: `eventId`, `timestamp`, `sessionId`, `userId`, `event_type`, `schemaVersion`, `requestId` y `properties`.
- [ ] Valida los tipos y restricciones básicas del envelope conforme a `event-schemas.json`; rechaza campos desconocidos del envelope. Comprueba que `event_type` pertenezca al catálogo aprobado. Cuando sea razonable, valida también las propiedades con el allowlist específico del tipo de evento; nunca aceptes ni registres datos fuera del contrato.
- [ ] Registra solo la cantidad de eventos y sus valores controlados de `event_type`; no registres cuerpos completos, tokens, PII, texto libre ni cabeceras sensibles.
- [ ] Devuelve `200 OK` con `{ "received": N }`, donde `N` es el número de eventos aceptados. No escribe en base de datos.
- [ ] Declara/lee la variable de entorno backend `TELEMETRY_ENDPOINT` según la configuración de esta API, aunque el stub no la utilice para reenviar eventos.
- [ ] Añade pruebas del endpoint para lote válido, lote vacío (según la política que definas y documentes), envelope inválido, evento desconocido y propiedad fuera del allowlist. No expongas mensajes de validación que reproduzcan PII.

### Fase 2 — TelemetryService en el frontend

Crea un servicio central, por ejemplo `uis/backoffice/telemetry.js`, siguiendo el estilo de módulos existente. Si eliges otra ubicación, documenta la decisión y mantén una única API pública.

- [ ] **Cola local:** agrega eventos a una cola en memoria; no hagas una petición HTTP individual por evento.
- [ ] **Batch + temporizador:** envía el lote cada 10 segundos o cuando alcance 20 eventos, lo que ocurra primero. El body tiene la forma `{ "events": [...] }`.
- [ ] **Flush al ocultar/cerrar:** usa `visibilitychange` y `navigator.sendBeacon` cuando la página pase a estar oculta, enviando los eventos pendientes de forma asíncrona. Si `sendBeacon` no está disponible o rechaza el envío, aplica un fallback seguro sin bloquear la salida de la página.
- [ ] **Reintentos:** ante fallos de red o respuestas no exitosas, reintenta hasta 3 veces con backoff exponencial. Al agotar reintentos descarta el lote; la telemetría no debe bloquear el backoffice. Evita duplicar eventos al reintentar y limita memoria/colas pendientes.
- [ ] **Única función:** expón `track(eventType, properties)` y canaliza por ella toda la instrumentación. Ningún módulo de UI hace `fetch`/`axios` de telemetría.
- [ ] **Envelope automático:** `track()` completa `eventId` (UUID), `timestamp` ISO 8601, `sessionId`, `userId`, `schemaVersion` (`1.0`) y `requestId`; los componentes solo aportan el tipo de evento y sus propiedades aprobadas. Reutiliza un `sessionId` opaco de la sesión de autenticación según el contrato; no uses email/nombre como ID. Si no hay sesión o usuario conocido, representa esos valores como `null`, de acuerdo con el esquema.
- [ ] `requestId` debe correlacionar el evento con la operación frontend/backend cuando exista un identificador de solicitud; si no existe, genera un identificador opaco. No introduzcas PII en este campo.
- [ ] Respeta el contrato custom de `event-schemas.json`: sus `properties` contienen la lista completa permitida de cada evento, y `required`/tipos/enums deben comprobarse conforme a la descripción del archivo. No asumas que ese registro es un único JSON Schema draft-07.
- [ ] El servicio debe tolerar que el entorno no tenga endpoint configurado, el navegador no soporte `sendBeacon` o el backend no esté disponible, sin interrumpir la navegación, autenticación ni operaciones.

### Fase 3 — Instrumentación técnica y de negocio

Instrumenta todas las métricas obligatorias del briefing y el piso técnico transversal. Prioriza además oportunidades de categorías distintas, de acuerdo con el tiempo disponible y el código existente.

#### Eventos obligatorios (los cinco)

- [ ] `inbound_order_created`: cuando una entrada de proveedor se confirme correctamente.
- [ ] `outbound_order_created`: cuando una entrega de material/kit/certificado se confirme correctamente.
- [ ] `stock_threshold_triggered`: cuando la disponibilidad cruce el umbral mínimo configurado.
- [ ] `direct_stock_edit_rejected`: cuando el sistema rechace un cambio directo no trazable de existencias.
- [ ] `kit_cost_variance_detected`: cuando se confirme que el costo unitario excede el umbral histórico configurado.

Emite cada evento solo en el momento correcto, después de recibir confirmación autoritativa del resultado. Si el umbral o la variación de costo se detectan únicamente en backend, devuelve al cliente la información necesaria para que el frontend pueda registrar el evento aprobado, o diseña una emisión única del lado servidor y documenta cómo evita una doble captura. No infieras un éxito a partir del clic en el botón ni conviertas una operación fallida en un evento de orden creada.

#### Piso técnico transversal

- [ ] **Errores no capturados del frontend:** captura `window.onerror`, `unhandledrejection` y/o boundaries equivalentes; sanitiza el error y usa `frontend_uncaught_error` con `error_fingerprint` no reversible y `page_id` controlado. No envíes mensaje crudo ni stack trace.
- [ ] **Rendimiento:** implementa al menos una medición (`api_latency_recorded` o `page_load_recorded`) de acuerdo con el schema. Agrupa rutas en `route_group` y mide duración; no incluyas URL con query, payload ni respuesta.
- [ ] **Navegación:** instrumenta `backoffice_section_viewed` en las secciones principales del backoffice y solo cuando haya un cambio real de sección, no en cada re-render.
- [ ] Implementa las restantes oportunidades de negocio/técnicas priorizadas del plan, cubriendo autenticación, inventario/negocio, rendimiento, errores y navegación cuando existan puntos reales de captura. Entre ellas pueden estar `inventory_order_validation_failed`, `auth_login_failed`, `auth_session_expired`, `api_request_failed` y `backoffice_flow_abandoned`.
- [ ] Para eventos de autenticación, instrumenta en el módulo/hook central de autenticación, no página por página. Un fallo debe usar una razón controlada, por ejemplo `invalid_credentials`, `session_expired` o `network_error` según aplique, y nunca incluir el email, nombre, contraseña, token o valor introducido.
- [ ] Cumple los allowlists de `event-schemas.json`; en particular, usa códigos de error y enum controlados, identificadores opacos de producto/programa y dimensiones de oficina/moneda según el plan. No envíes campos extras “por si acaso”.
- [ ] Comprueba que la captura está desacoplada del éxito de la operación de negocio: una caída del receptor de telemetría no debe impedir guardar una orden, mostrar un error funcional ni iniciar/cerrar sesión.

#### Actividad adicional — Web Vitals

- [ ] Si la arquitectura del backoffice lo permite sin incorporar un framework o dependencia desproporcionada, registra Web Vitals (por ejemplo, LCP/CLS/INP equivalentes) como eventos permitidos del contrato. Si se necesita extender el catálogo, actualiza primero plan y schema con revisión; no añadas propiedades no aprobadas. Incluye únicamente un `page_id`/ruta controlada y métricas numéricas no personales.

### Fase 4 — Verificación y evidencia

- [ ] Ejecuta las pruebas del backend y frontend relevantes, más las pruebas nuevas del servicio/endpoint. No afirmes checks que no hayas ejecutado.
- [ ] Inicia la API y el backoffice localmente con configuración de prueba y valores sintéticos.
- [ ] Verifica en DevTools → Network que salen lotes (no requests unitarios), en el formato `{ "events": [...] }`, con los ocho campos del envelope y `properties` permitidas; confirma respuesta `200` y `{ "received": N }`.
- [ ] Comprueba temporizador de 10 segundos, umbral de 20 eventos, `visibilitychange`/`sendBeacon`, retries/backoff y ausencia de duplicados en una prueba controlada.
- [ ] Prueba que fallos del endpoint no interrumpen flujos normales y que no se envían PII, secretos ni mensajes crudos.
- [ ] Añade evidencia sanitizada de Network en la entrega. La captura no debe mostrar tokens, cookies, email, nombres, datos de candidatos, variables secretas ni solicitudes con payload real.

---

## ✅ Qué vamos a evaluar

- [ ] Existe `POST /telemetry/events`; acepta `{ "events": [...] }`, valida eventos y devuelve `{ "received": N }` con HTTP 200 en caso válido.
- [ ] El modelo Pydantic `TelemetryEvent` incluye los ocho campos del envelope definido en la Fase 1 y conserva compatibilidad con `schemaVersion` y propiedades aprobadas.
- [ ] El stub no persiste datos y registra solo cantidad y `event_type` controlados, sin PII.
- [ ] La URL del endpoint de frontend se configura por entorno/configuración de ejecución y no está hardcodeada. En este repo estático se explica el mecanismo equivalente al `NEXT_PUBLIC_TELEMETRY_ENDPOINT` indicado por 4Geeks.
- [ ] El backend define/lee `TELEMETRY_ENDPOINT` desde su configuración de entorno.
- [ ] `TelemetryService` implementa cola en memoria, batch + debounce/temporizador (10 s / 20 eventos), flush con `navigator.sendBeacon`, fallback y hasta 3 retries con backoff exponencial.
- [ ] `track()` genera automáticamente `eventId`, `timestamp`, `sessionId`, `userId`, `schemaVersion` y `requestId`; quien llama no proporciona el envelope manualmente.
- [ ] No hay llamadas directas a `fetch`/`axios` para telemetría fuera del servicio central.
- [ ] Están instrumentados los cinco eventos obligatorios de Nexova en el instante correcto y sin duplicados.
- [ ] Está instrumentado el piso transversal: errores no capturados, al menos una métrica de rendimiento y navegación en las secciones principales.
- [ ] Los eventos y propiedades coinciden con el plan/schema aprobados, incluyendo sus allowlists, categorías, valores y datos condicionales.
- [ ] No se capturan PII ni secretos: email, nombre, contraseña, token, dirección IP, payloads, texto libre, URL completa, mensaje/stack crudos.
- [ ] La caída de telemetría no bloquea operaciones funcionales del backoffice.
- [ ] La pestaña Network demuestra lotes correctos y respuesta `200`; pruebas y evidencia son reproducibles y están sanitizadas.

---

## 🔐 Privacidad y seguridad

- Los eventos son append-only y distintos del perfil/registro persistente del usuario.
- Los valores personales no se necesitan para tomar las decisiones del plan. No registres destinatarios nominales; usa solo `recipient_type` y referencias opacas del negocio permitidas.
- `userId`, `sessionId`, `product_id`, `programme_id` y `supplier_ref` son identificadores seudónimos y deben protegerse como datos sensibles: no incluirlos en logs de depuración ni en capturas compartidas.
- No envíes `Authorization`, cookies, tokens, contraseñas, emails, nombres, formularios, cuerpos de requests, texto de búsquedas, stacks, ni datos reales de empleados/candidatos/clientes/consultores.
- No modifiques ni añadas secretos a archivos versionados. Configura solo valores locales de prueba no sensibles y conserva las reglas de ignore del repo.
- Los fallos de telemetría no deben exponer detalles internos al usuario ni fallar la operación funcional que los originó.

---

## 📦 Entrega

1. Mantén los cambios en esta copia del monorepo; no crees otro repositorio.
2. Incluye el endpoint FastAPI en `services/api/` y el servicio/instrumentación en `uis/backoffice/`, además de pruebas y documentación de configuración necesarias.
3. Abre un Pull Request dirigido a `main` con el título exacto: **`feat: telemetry event capture`**.
4. En la descripción del PR incluye:
   - Lista de eventos instrumentados, indicando cuáles son los cinco obligatorios y cuáles son oportunidades identificadas.
   - Componente, módulo o hook que genera cada evento.
   - Resumen de cola/batching, `sendBeacon`, reintentos y configuración del endpoint.
   - Captura de DevTools mostrando un lote llegando al stub con respuesta `200`, sanitizada.
   - Si se implementó Web Vitals y/o eventos de autenticación.
   - Comandos de pruebas ejecutados y resultados reales, limitaciones conocidas y confirmación explícita de que el stub no persiste datos.
5. No integres el PR en `main` hasta que sea aprobado. Si no se aprueba, corrige las observaciones antes de dar por cerrada la fase.

---

## Referencia del contrato aprobado

El registry aprobado incluye 19 eventos:

- **Obligatorios BRIEFING (5):** `inbound_order_created`, `outbound_order_created`, `stock_threshold_triggered`, `direct_stock_edit_rejected`, `kit_cost_variance_detected`.
- **Oportunidades (14):** `inventory_item_viewed`, `inventory_order_validation_failed`, `inventory_order_abandoned`, `inventory_threshold_acknowledged`, `inventory_search_performed`, `auth_login_failed`, `auth_session_expired`, `auth_login_succeeded`, `api_latency_recorded`, `page_load_recorded`, `api_request_failed`, `frontend_uncaught_error`, `backoffice_section_viewed`, `backoffice_flow_abandoned`.

Los tipos y propiedades completos, incluidos tipos de dato, obligatoriedad y allowlist, están en [`docs/telemetry/event-schemas.json`](docs/telemetry/event-schemas.json). El plan aprobado explica hipótesis, decisiones, flujo, privacidad, riesgos, exclusiones y batch/stream en [`docs/telemetry/telemetry-plan.md`](docs/telemetry/telemetry-plan.md).
