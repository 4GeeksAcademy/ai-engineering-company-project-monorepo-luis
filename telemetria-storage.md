# Telemetría de Nexova — Almacenamiento

> Guía de trabajo para **Application Telemetry — Telemetría de tu compañía – Almacenamiento**. Recoge los requisitos del README oficial y los adapta al monorepo actual de Nexova. El alcance de esta entrega es el backend y Supabase: **no cambiar el frontend ni el contrato de captura**.
>
> **README oficial (español):** [Telemetría de tu compañía – Almacenamiento](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-telemetry-storage/README.es.md)
> **Etapa anterior:** [`telemetria-front.md`](telemetria-front.md)
> **Contrato de eventos:** [`docs/telemetry/event-schemas.json`](docs/telemetry/event-schemas.json)
> **Plan y privacidad:** [`docs/telemetry/telemetry-plan.md`](docs/telemetry/telemetry-plan.md)
> **Backend:** [`services/api/README.md`](services/api/README.md), [`services/api/telemetry.py`](services/api/telemetry.py), [`services/api/routers/telemetry.py`](services/api/routers/telemetry.py)
>
> **Prerrequisito:** el `TelemetryService` debe estar enviando lotes al endpoint existente y recibiendo HTTP 200. La rama `docs/telemetry-front` contiene el stub y el modelo `TelemetryEvent` de la etapa previa. Antes de implementar, verifica el commit/PR de captura y confirma que el contrato desplegado coincide con `event-schemas.json`.
>
> **Acceso 4Geeks:** el token disponible para esta sesión devolvió HTTP 401; por tanto, no se pudo validar el estado de la cuenta en la plataforma. Este documento se basa en el README oficial público en español, leído completo, y en los artefactos de la etapa anterior del monorepo. No compartas ni subas tokens; si el token se publicó en un chat, revócalo y sustitúyelo.

---

## 🎯 Reto y límites

Los eventos de frontend ya llegan al stub, que valida el contrato y los descarta. Convierte ese receptor en un endpoint real que:

1. Reutilice el `TelemetryEvent` de la fase anterior como contrato sin modificarlo.
2. Valide cada evento individualmente, rechazando solo los inválidos.
3. Persista todos los válidos de un lote en `telemetry_events` de Supabase mediante **una operación bulk y una transacción**.
4. Devuelva exactamente cuántos eventos recibió, almacenó y rechazó.

El cambio es del lado servidor. La URL HTTP y el formato `{ "events": [...] }` se mantienen; el frontend no cambia ni una línea. No se crean eventos nuevos, no se altera el schema aprobado ni se escribe un sistema analítico adicional.

### Situación concreta del monorepo

- El backend FastAPI vive en `services/api/`; la app se registra desde `services/api/main.py` y el endpoint previo está en `services/api/routers/telemetry.py`.
- `services/api/telemetry.py` ya define `TelemetryEvent`, `TelemetryBatch`, validación contra el registry y configuración de `TELEMETRY_ENDPOINT`. El endpoint actual acepta el lote tipado completo, registra solo metadatos controlados y **no persiste**.
- El backend ya tiene una integración SQLModel/SQLAlchemy para inventario, con fallback local SQLite si no hay configuración de base de datos. **No permitas que el nuevo almacenamiento de telemetría caiga silenciosamente en SQLite local cuando el criterio pide Supabase.** Confirma el destino de base de datos y el mecanismo de conexión antes de implementar o demostrar persistencia.
- El proyecto no debe asumir que existe una tabla de Supabase, una URL de PostgreSQL, una clave de servicio ni datos reales. Las credenciales deben ser backend-only, suministradas por configuración segura y nunca incluirse en el repo, navegador, capturas, logs o documentación.
- El productor de los eventos de esta etapa es el backoffice. Para los eventos de prueba usa identificadores opacos sintéticos; no uses proveedores/contactos, empleados, candidatos, clientes ni destinatarios reales.

### Criterios que prevalecen

- El README oficial especifica el contrato de almacenamiento y aceptación parcial.
- `TelemetryEvent` y `event-schemas.json` son la fuente para validar eventos; el registro define allowlists exactos por evento.
- `telemetry-plan.md` define dimensiones de Nexova y privacidad: oficinas `valencia`/`miami`, moneda `EUR`/`USD`, identificadores opacos y ninguna PII.
- Si Supabase no está configurado o los contratos existentes discrepan, no inventes credenciales, esquema ni comportamiento: documenta el bloqueo y pide la configuración/decisión necesaria.

---

## 🌱 Antes de empezar

1. Revisa `git status --short --branch`, el diff y la rama de captura; no sobrescribas cambios ajenos. Comprueba que el cambio de frontend previo ya está publicado/integrado según el flujo de trabajo acordado.
2. Lee el README de `services/` y `services/api/`, las instrucciones `AGENTS.md`, las reglas aplicables en `.agents/rules/`, y los archivos `telemetria-front.md`, `telemetry-plan.md`, `event-schemas.json`, `services/api/telemetry.py`, router, configuración de DB y tests.
3. Verifica que el stub recibe lotes válidos y que su respuesta es HTTP 200 antes de sustituir su comportamiento. No uses el endpoint de telemetría de producción para pruebas.
4. Confirma por un canal seguro el entorno Supabase local/de prueba autorizado, el destino de conexión y quién lo administra. No abras ni imprimas `.env*` ni credenciales sin autorización explícita. No hace falta una clave Supabase para crear la guía; sí hace falta un entorno de prueba seguro para persistencia E2E.
5. Revisa cómo se inicializa actualmente SQLModel y evita crear accidentalmente `telemetry_events` en el SQLite de fallback o modificar tablas de inventario/auth.
6. Implementa en este orden: **tabla/migración → persistencia bulk → validación parcial y endpoint → pruebas → verificación E2E**. Mantén Supabase fuera del camino de arranque si no está disponible, salvo que la configuración de este proyecto documente explícitamente otro requisito.

---

## 💻 Qué debes hacer

### Fase 1 — Tabla `telemetry_events` en Supabase

Crea la tabla en el proyecto Supabase autorizado (y versiona la migración SQL reproducible en la ruta de migraciones establecida por el repo; si no existe convención, documenta y acuerda una antes de crear una carpeta nueva).

Debe contener estas ocho columnas:

| Columna | Tipo / restricción | Uso |
|---|---|---|
| `id` | `uuid PRIMARY KEY DEFAULT gen_random_uuid()` | ID único del registro en la tabla. |
| `timestamp` | `timestamptz NOT NULL` | Timestamp del evento, tomado de `event.timestamp`. |
| `service` | `text NOT NULL` | Origen; para eventos producidos por esta app, valor controlado `backoffice`. |
| `event_type` | `text NOT NULL` | Tipo aprobado `entidad_acción`, tomado de `event.event_type`. |
| `level` | `text DEFAULT 'info'` | Severidad controlada `info`, `warn` o `error`, derivada del tipo de evento con reglas explícitas. |
| `value` | `numeric NULL` | Medida numérica opcional; `NULL` si no hay una correspondencia de negocio inequívoca. |
| `message` | `text NULL` | Resumen controlado opcional; mantener `NULL` antes que copiar texto arbitrario del evento. |
| `tags` | `jsonb NOT NULL DEFAULT '{}'` | `event.properties`, después de validar el allowlist de ese tipo. |

Añade los tres índices requeridos:

- B-tree en `timestamp`.
- B-tree en `event_type`.
- GIN en `tags` para consultas JSONB.

Los eventos son hechos inmutables y append-only. No implementes rutas ni lógica de `UPDATE`/`DELETE`. La tabla no es CRUD.

#### Seguridad de Supabase

- Conecta desde FastAPI usando configuración del servidor y un rol/credencial backend-only con permisos mínimos necesarios. Nunca uses `service_role`, password de PostgreSQL o URL con credenciales en frontend, documentación versionada, logs o evidencia.
- Protege la tabla para que no sea públicamente legible/escribible; aplica grants/RLS según el modo de conexión elegido. Las migraciones deben ejecutarse con un rol autorizado, no con la credencial del cliente.
- Si no existe un Supabase autorizado para desarrollo, no inventes una URL ni uses datos reales: prepara la migración y tests aislados y deja la verificación real como bloqueo explícito.

### Mapeo del evento a la fila

Implementa y documenta una sola función de mapeo, con estas reglas:

| Columna | Origen/regla |
|---|---|
| `id` | Lo genera la base de datos según el default declarado. |
| `timestamp` | `TelemetryEvent.timestamp`, convertido a datetime timezone-aware solo si el driver/ORM lo requiere; conserva el instante UTC correctamente. |
| `service` | Constante controlada `backoffice` para los lotes del frontend actual. No aceptar un valor arbitrario del cliente. |
| `event_type` | `TelemetryEvent.event_type`, ya validado contra los 19 eventos del registry. |
| `level` | Mapa explícito y probado de tipos a `info`/`warn`/`error`; default `info`. No derivar de texto libre ni guardar mensaje de excepción crudo. |
| `value` | Opcional. Solo mapear una propiedad numérica si su significado y unidad son inequívocos y están documentados para ese `event_type`; de lo contrario `NULL`. No mezclar cantidades, costes, duración ni monedas en una métrica genérica sin etiqueta/unidad consultable. |
| `message` | `NULL` por defecto. Si se necesita, usar una descripción estática/controlada por `event_type`; nunca copiar mensajes de error, texto libre, formularios, payloads o identificadores personales. |
| `tags` | Copia de `event.properties`, después de validación Pydantic y del allowlist exacto; preserva las dimensiones analíticas de Nexova. No añadir datos fuera del contrato. |

El README oficial permite incluir metadatos del envelope dentro de `tags` solo si el plan lo requiere y se documenta consistentemente. En la versión vigente del plan, `tags` representa `properties`; no cambies silenciosamente esa semántica ni agregues claves extra. Si se decide almacenar `eventId` en la tabla para idempotencia, trata eso como una decisión de esquema documentada/revisada primero: la tabla exigida no tiene columna `eventId` y el proyecto no define una política de deduplicación.

No uses `message` para serializar `properties`. La estructura indexable y su privacidad pertenecen a `tags`.

### Fase 2 — Sustituir el stub por endpoint de persistencia real

Conserva `POST /telemetry/events`, el body `{ "events": [...] }`, el envelope y el `TelemetryEvent` previamente aprobado. El endpoint final debe devolver HTTP 200 y JSON:

```json
{"received": 3, "stored": 2, "rejected": 1}
```

Reglas para el manejo parcial:

1. **No declares el body completo como `TelemetryBatch` con `events: list[TelemetryEvent]` en la firma del endpoint.** FastAPI/Pydantic lo validaría antes de ejecutar el handler y un solo item inválido produciría 422 para todo el lote.
2. Acepta el contenedor externamente como JSON parseable con un arreglo `events` sin validar anticipadamente sus items como `TelemetryEvent`. Rechaza con 4xx genérico/sanitizado un contenedor malformado, si falta `events` o si no es arreglo. Conserva y documenta un límite razonable al tamaño del lote; el contrato anterior admite hasta 500.
3. Dentro del handler recorre cada valor y ejecuta `TelemetryEvent.model_validate(raw)` (o la forma equivalente de Pydantic instalada) dentro de `try/except ValidationError`. No cambies el modelo existente para lograr validación parcial.
4. Los válidos se acumulan en memoria para el bulk insert. Los inválidos incrementan `rejected`; el bucle continúa. No devuelvas al cliente los detalles de validación, valores, claves erróneas ni PII.
5. Inserta todos los válidos en **una sola operación bulk dentro de una transacción**. No hagas un `INSERT`/commit por evento. Si no hay válidos, no abras una operación de escritura.
6. Responde `{received: N, stored: M, rejected: R}`: `N` cantidad de items del arreglo; `M` cantidad efectivamente persistida; `R` items no conformes. Un lote vacío válido devuelve `200 {"received":0,"stored":0,"rejected":0}`. Si falla la base de datos, revierte el lote válido completo y responde un error genérico no-2xx; no finjas éxito parcial.
7. Asegura que el cliente `TelemetryService` actual sigue funcionando: revisa su comportamiento, que solo necesita status HTTP, y no cambies URL, formato, nombres de campos ni frontend.

Mantén la respuesta compatible con el servicio actual. No envíes en el JSON de respuesta mensajes de base de datos, query SQL, eventos, IDs o datos de validación.

#### Registro y privacidad

- Registra únicamente contadores (`received`, `stored`, `rejected`) y nombres `event_type` que hayan sido validados y pertenezcan al catálogo controlado.
- No registres bodies, `tags`, `eventId`, `sessionId`, `userId`, `requestId`, email, nombres, direcciones IP, cabeceras `Authorization`, credenciales o mensajes de validación que reflejen inputs.
- Las propiedades string siguen pudiendo contener PII aunque el tipo/allowlist sea válido. La validación del esquema no es un detector de PII: los productores deben mandar IDs opacos y valores controlados.
- Los fallos de persistencia deben producir logs saneados; no imprimir URL de conexión ni secretos.

### Fase 3 — Pruebas

Añade o adapta pruebas en `services/api/tests/` con el framework y convenciones existentes. Usa base temporal/de prueba, fixtures sintéticos y mocks para el almacenamiento; no escribas contra producción desde tests automatizados.

Casos mínimos:

- [ ] Evento válido de negocio persistido con `timestamp`, `service`, `event_type`, `level`, `value`, `message` y `tags` esperados.
- [ ] Evento técnico válido y propiedades permitidas preservadas en `tags`.
- [ ] Lote mixto: válido + inválido; HTTP 200 y conteos correctos, se guarda solo el válido.
- [ ] Varios eventos válidos se envían al almacenamiento en una sola operación bulk/una transacción, no en N inserts.
- [ ] Evento con campo de envelope extra, tipo desconocido, propiedad fuera del allowlist, propiedad requerida ausente o tipo/enum inválido: se rechaza individualmente y no filtra el valor ni el error detallado en response/logs.
- [ ] Contenedor sin `events`, `events` no-arreglo, JSON inválido y lote sobre el límite: error genérico/sanitizado según política documentada; no se modifica ninguna fila.
- [ ] Arreglo vacío: respuesta `200` con ceros; sin llamada de escritura.
- [ ] Fallo de DB/bulk insert: rollback íntegro y respuesta no-2xx genérica; no deja una parte del lote almacenada.
- [ ] Los `event_type` de log son únicamente nombres verificados/controlados; no se registran cuerpos, tags, IDs ni tokens.
- [ ] La aplicación sigue arrancando según la configuración documentada y el almacenamiento de telemetría no altera las tablas/datos del inventario, auth, proveedores o incidencias.

La respuesta para cada item inválido debe evitar reflejar la entrada. Pydantic ya usa errores ocultando inputs, pero el handler debe capturar y convertir las fallas de cada evento en contadores sin serializar `ValidationError.errors()` al response o log.

### Fase 4 — Verificación end-to-end y evidencia

Con API conectada a un proyecto Supabase **de prueba autorizado** y el frontend de la etapa previa sin cambios:

1. Inicia el backoffice y backend localmente con configuración segura. Confirma que el endpoint URL es el mismo y que la persistencia seleccionada es Supabase, no el SQLite fallback.
2. Desde el backoffice crea al menos una entrada y una salida de inventario, y genera un evento técnico (por ejemplo, login fallido de prueba). Usa solo datos sintéticos/opacos y un entorno aislado.
3. Consulta la tabla `telemetry_events` desde el dashboard/SQL Editor autorizado. Comprueba al menos cinco filas reales del flujo de prueba y los valores de `event_type`, `timestamp`, `service` y `tags`.
4. Envía un lote controlado que mezcle eventos válidos e inválidos. Conserva el JSON de respuesta con `received`, `stored` y `rejected`, y confirma en la base que solo se persistieron los válidos.
5. Comprueba que se realiza un bulk insert por lote y que ninguna operación funcional del backoffice falla si TelemetryService reintenta o el receptor no está disponible.
6. Captura evidencia sanitizada de la tabla con al menos cinco eventos, incluyendo uno de negocio y uno técnico. Oculta proyecto/URLs con secretos, tokens, claves, connection strings, email, nombres y cualquier dato real. Nunca captures cabeceras sensibles.

Si la configuración Supabase segura no está disponible, no simules una prueba real de DB ni marques la fase E2E aprobada: reporta exactamente qué falta y completa mientras tanto tests unitarios/integración aislados con motor temporal.

---

## ✅ Qué vamos a evaluar

- [ ] Existe `telemetry_events` en Supabase con **ocho columnas**, conforme a la tabla descrita; tiene índice por `timestamp`, índice por `event_type` e índice GIN por `tags`.
- [ ] Los eventos son inmutables: no existe flujo de `UPDATE` o `DELETE` para telemetría.
- [ ] `POST /telemetry/events` hace bulk insert y responde `{ "received": N, "stored": M, "rejected": R }`.
- [ ] Los eventos inválidos se rechazan individualmente sin cancelar el lote: se usa `TelemetryEvent.model_validate(...)` item por item dentro del handler, no un body tipado como `list[TelemetryEvent]` que devuelva 422 por todo el request.
- [ ] `TelemetryEvent` y su contrato Pydantic/schema de la fase anterior se reutilizan sin modificaciones.
- [ ] El frontend no cambió ninguna línea; la sustitución stub → almacenamiento real es transparente y la URL/body se mantienen.
- [ ] Los eventos de negocio y técnicos están almacenados con `event_type`, `timestamp` y `tags` correctamente mapeados.
- [ ] `tags` conserva las propiedades permitidas y dimensiones específicas del briefing de Nexova, sin añadir propiedades fuera del allowlist.
- [ ] Cada lote de eventos válidos se inserta en una sola operación bulk, no mediante una consulta/commit por evento.
- [ ] El mapeo de severidad, `value`, `message` y `service` es consistente, controlado y no filtra datos sensibles.
- [ ] Se probaron un lote mixto válido/inválido y rollback ante fallo de almacenamiento; los conteos reflejan el resultado real.
- [ ] Se incluye evidencia E2E sanitizada con al menos cinco eventos (mínimo uno técnico y uno de negocio), y evidencia de la respuesta JSON para lote mixto.
- [ ] No se exponen secretos Supabase ni se altera autenticación, datos personales o comportamiento funcional del backoffice.

---

## 📦 Entrega

1. Mantén los cambios en esta copia del monorepo; no crees otro repositorio.
2. El cambio de código corresponde a `services/` y la migración de base de datos. **No modifiques `uis/backoffice/` ni `uis/talent-pipeline-tracker/`.**
3. Abre un Pull Request contra `main` con el título exacto: **`feat: telemetry event storage`**.
4. Incluye en la descripción del PR:
   - Captura sanitizada de `telemetry_events` en Supabase con al menos cinco filas reales de prueba: eventos técnicos y de negocio.
   - JSON de respuesta de un lote mixto que muestre `received`, `stored` y `rejected`.
   - Confirmación explícita: **el frontend no cambió**.
   - Comandos de tests ejecutados y resultados reales, decisión de mapeo `service`/`level`/`value`/`message`, migración/índices y limitaciones conocidas.
5. No integres el PR en `main` hasta aprobación. Si hay observaciones, corregirlas antes de cerrar la fase.

---

## 🧭 Checklist de cierre para el agente

- [ ] Se leyó README oficial completo, especialmente «Qué Necesitas Hacer» y «Qué Vamos a Evaluar».
- [ ] Se contrastó el cambio con el contrato de 19 eventos y el allowlist de Nexova.
- [ ] La tabla/migración e índices son reproducibles y no dependen de pasos manuales no documentados.
- [ ] Se valida cada item sin bloquear el resto del lote; errores/cuerpos se mantienen privados.
- [ ] Persistencia bulk y atomicidad están comprobadas mediante tests.
- [ ] Se verificó que el frontend sigue intacto y funciona contra la misma ruta.
- [ ] Se ejecutaron pruebas pertinentes de API y `git diff --check`; no se declararon validaciones no ejecutadas.
- [ ] El entorno de prueba Supabase fue autorizado y no es producción; evidencia sanitizada revisada.
- [ ] `git status` y diff confirman que solo se incluyen archivos del objetivo. No hay secretos, datos reales, DBs locales ni archivos generados.
- [ ] PR creada con el título requerido y sin merge prematuro.

> **Límite de esta guía:** describe instrucciones y criterios, no afirma que Supabase esté configurado ni que la persistencia E2E se haya ejecutado. La autenticación 4Geeks no pudo verificarse porque el token de sesión respondió 401; la fuente oficial pública sí se consultó correctamente.
