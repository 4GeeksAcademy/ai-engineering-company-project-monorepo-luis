# Nexova Backoffice

## Entrega de captura de telemetria — etapa 6

PR a `main`: **`feat: telemetry event capture`**. No hacer merge antes de la
revision. El receptor temporal valida y cuenta eventos; **no los persiste**.

| Eventos | Emisor |
| --- | --- |
| Obligatorios: `inbound_order_created`, `outbound_order_created`, `stock_threshold_triggered`, `direct_stock_edit_rejected`, `kit_cost_variance_detected` | Cliente de inventario, a partir de las confirmaciones de FastAPI. |
| `page_load_recorded`, `frontend_uncaught_error`, `backoffice_section_viewed` | `telemetry-technical.js`. |
| `auth_login_succeeded`, `auth_login_failed`, `api_latency_recorded`, `api_request_failed` | Cliente API y autenticacion central. |
| `inventory_order_abandoned` | Formulario de movimientos, solo cancelacion explicita. |

El servicio central envia hasta 20 eventos cada 10 s o al llegar al umbral,
intenta Beacon al ocultar/salir y usa `fetch` con `keepalive` como alternativa.
Hace hasta tres reintentos (1/2/4 s). Configurar `window.__TELEMETRY_ENDPOINT__`
y, para navegacion, `window.__TELEMETRY_OFFICE__` en
[`telemetry-config.js`](./telemetry-config.js). Entrega best effort: un
reintento conserva el ID, pero el stub no deduplica. No hay Web Vitals.

### Evidencia de red sanitizada (2026-11-18)

Chromium y FastAPI en loopback, en origenes distintos, SQLite en memoria y
cuenta sintetica aislada. El receptor no se simulo; la unica intercepcion de
red abortaba POST de telemetria para comprobar el fallo y la recuperacion.

| Caso | Resultado observado |
| --- | --- |
| Temporizador | `POST /telemetry/events` → HTTP 200, `{"received":2}`. |
| Umbral de 20 | `POST /telemetry/events` → HTTP 200, `{"received":20}`, 20 IDs distintos. |
| `pagehide` sintetico | El envio de cierre llego a FastAPI: HTTP 200, `{"received":1}`. |
| Primer intento abortado | Reintento a los 1.036 s, mismo body, HTTP 200; no dos lotes aceptados en este escenario. |
| Receptor bloqueado | Registro e inicio de sesion, entrada de 2 unidades, consulta de stock (2) y cierre de sesion operativos. |

El lote de 20 tenia los campos `eventId`, `timestamp`, `sessionId`, `userId`,
`event_type`, `schemaVersion`, `requestId` y `properties`. Se comprobo que esa
peticion no incluia `Authorization` ni `Cookie`. El extracto y su captura
sanitizada omiten los valores de los eventos y los identificadores. No se
repitieron en navegador todos los escenarios de inventario de la etapa 3.

```powershell
node --test uis\backoffice\tests\test_telemetry.mjs uis\backoffice\tests\test_inventory_api.mjs
node uis\backoffice\generate-telemetry-contract.mjs --check
$env:DATABASE_URL = 'sqlite://'
uv run --locked --project services\api python -m pytest services\api\tests\test_telemetry_api.py services\api\tests\test_inventory_api.py services\api\tests\test_inventory_service.py services\api\tests\test_security.py -q
```

Node: 19 pasan y el contrato generado coincide. FastAPI: 64 pasan y falla
`test_get_products_empty` (`KeyError: '500'` en OpenAPI, discrepancia ya
identificada en la rama base). No se cambio el contrato ajeno a telemetria.
Los tiempos completos de backoff, fallback y presupuesto de envio se
comprobaron con las pruebas Node.

## Oportunidades de telemetria — etapa 5

| Evento | Punto de captura |
| --- | --- |
| `auth_login_succeeded` | Cliente de autenticacion central, una vez establecida la sesion. |
| `auth_login_failed` | Intento rechazado por la API o fallo de transporte durante login; siempre anonimo, con codigo controlado. Emite el primero y resume repeticiones por metodo y codigo tras 60 s. |
| `api_latency_recorded` | Cliente API central: tiempo hasta recibir las cabeceras o fallar. Muestreo determinista por ID del 10% de exitos debajo de 1.000 ms; 100% de lentas y fallidas. |
| `api_request_failed` | Cliente API central: primer fallo y resumen de repeticiones tras 60 s, por grupo de ruta, metodo, estado y codigo. No cubre peticiones fuera del cliente central ni el colector. |
| `inventory_order_abandoned` | Boton Cancelar o Escape en una orden abierta, sin envio activo. No se infiere abandono de una recarga, expiracion o cierre de pagina. |

No se envian URLs, consultas, credenciales, cuerpos ni errores crudos. Los
resumenes se mantienen en memoria y pueden perderse al cerrar el documento.

Exclusiones acordadas: `auth_session_expired` (401 no distingue expiracion),
`inventory_item_viewed` (sin vista de detalle), `inventory_threshold_acknowledged`
(sin accion de reconocimiento), `inventory_search_performed` (los filtros
pueden mezclar oficinas), `inventory_order_validation_failed` (sin captura
unificada por codigo aprobado) y `backoffice_flow_abandoned` (no se duplica la
cancelacion y no hay otro flujo priorizado). No se amplia el esquema para Web
Vitals.

## Telemetria tecnica — etapa 4

- `page_load_recorded` usa Navigation Timing al terminar la carga. Si el
  navegador no ofrece la medicion, no envia un cero inventado.
- `frontend_uncaught_error` captura errores de ventana y promesas rechazadas
  sin manejar. El fingerprint SHA-256 se calcula solo con una firma controlada:
  script local permitido y posicion, o una categoria generica. No lee mensajes,
  stacks ni motivos de rechazo. Por documento, envia la primera ocurrencia y
  resume las repetidas al cerrar 60 segundos; limita a 64 grupos simultaneos.
- `backoffice_section_viewed` requiere `window.__TELEMETRY_OFFICE__` en
  [telemetry-config.js](./telemetry-config.js): `valencia` o `miami`, solo cuando
  el despliegue corresponde a una oficina. En un despliegue compartido, dejar
  vacio para omitir navegacion sin afectar a errores y rendimiento.
  Resumen mapea a `dashboard`, Catalogo y Movimientos a `inventory`, e Historial
  a `reports`. Enlaces internos al mismo resumen y recargas no cuentan como
  cambios de seccion. La deduplicacion entre paginas usa `sessionStorage`.

## Telemetria de inventario — etapa 3

Con el receptor frontend habilitado y `INVENTORY_TELEMETRY_CATALOG` configurado
en la [API](../../services/api/README.md), en Movimientos:

- **Entrada:** selecciona un proveedor del directorio y registra el coste
  unitario en la moneda de la oficina. Se mide la entrada confirmada y, cuando
  corresponda, la variacion frente al ultimo coste confirmado comparable.
- **Salida:** indica una categoria de destinatario si aplica para medir la
  entrega. Un cruce del minimo configurado se mide independientemente de que
  la salida tenga categoria de destinatario.
- **Cambio directo:** envia una solicitud de ajuste con cantidad firmada.
  La API la rechaza y el stock permanece intacto. Abrir o cancelar el
  formulario no emite el evento.

Los cinco eventos se encolan solo a partir de las confirmaciones de la API.
El cliente central procesa cada tipo una vez por respuesta y pasa el UUID
`X-Request-ID` al servicio para correlacionar el envelope. Los formularios no
envian telemetria directamente. No se incluyen nombres de proveedor,
destinatarios ni campos libres. Sin datos aprobados, no se completa el evento
con valores inventados. Las operaciones legacy siguen disponibles.

## Telemetria — etapa 2

El servicio central expone solo `window.Telemetry.track(eventType, properties)`.
Retorna `true` si encola el evento y `false` si esta desactivado o lo rechaza;
no retorna una promesa ni garantiza entrega. Esta etapa carga el servicio en
las cuatro paginas, pero **todavia no instrumenta operaciones de negocio,
autenticacion, errores ni navegacion**.

### Configuracion estatica

Antes de cargar el servicio, el despliegue configura
`window.__TELEMETRY_ENDPOINT__` en `telemetry-config.js` (o en un script anterior).
Ejemplo publico, solo para datos sinteticos locales:

```js
window.__TELEMETRY_ENDPOINT__ = "http://127.0.0.1:8000/telemetry/events";
```

Es el equivalente de configuracion de ejecucion para este sitio estatico:
no usa Next.js, variables de proceso en el browser ni secretos. La version
incluida tiene endpoint vacio: no encola, no crea temporizadores y muestra
una advertencia controlada. Cambiar la configuracion requiere recargar.
La URL puede ser relativa al documento o HTTP(S) absoluta, nunca con
credenciales, query o fragmento. El receptor debe admitir el origen del panel
por CORS. No se usa el cliente autenticado `inventoryApi.request` para enviarla.

Los envios `fetch` usan `credentials: "omit"` y no incluyen Authorization.
**`sendBeacon` no permite omitir las cookies automaticas del navegador**:
usar un receptor/origen sin cookies ni credenciales HTTP, tambien en pruebas;
no configurar un colector compartido con sesiones personales.

### Contrato y sesion

- El contrato estatico `telemetry-contract.js` se genera desde
  `docs/telemetry/event-schemas.json`; no mantener otro catalogo a mano.
  Regenerar tras cambios aprobados del contrato:

  ```powershell
  node uis\backoffice\generate-telemetry-contract.mjs
  node uis\backoffice\generate-telemetry-contract.mjs --check
  ```

- `track()` comprueba allowlist, obligatoriedad, tipos, enums, limites,
  elementos de arrays y correspondencia oficina/moneda. Rechaza propiedades
  extra; no corrige ni completa datos de negocio inventados.
- Crea el envelope de ocho campos y serializa una instantanea al encolar:
  UUID para `eventId`, hora ISO de creacion y `schemaVersion: "1.0"`.
- Genera un UUID opaco de sesion al reconocer una sesion autenticada, lo
  conserva por pestaña en `sessionStorage` y lo rota en login; logout/401 lo
  elimina mediante el observador central existente. Sin almacenamiento
  disponible conserva solo la sesion en memoria, sin impedir autenticacion.
- `userId` usa exclusivamente `String(profile.user_id)` cuando es un entero
  interno positivo seguro; nunca email/nombre ni contenido del token.
  Sin usuario/sesion conocidos, sus campos correspondientes son `null`.
  Son identificadores seudonimos sensibles, no datos anonimizados.
- `requestId` usa el UUID de respuesta para las confirmaciones de inventario
  instrumentadas; si no hay uno valido, el servicio genera un UUID por evento.
- Requiere `crypto.randomUUID` (contexto seguro, incluido localhost); si falta,
  rechaza captura con advertencia sin afectar al backoffice.

### Transporte y limites

- Cola solo en memoria: hasta 500 eventos incluidos los que estan en vuelo;
  al llenarse rechaza los nuevos. No guarda eventos en storage ni en perfiles.
- Envia hasta 20 eventos cada 10 segundos o al alcanzar 20 pendientes.
  Los lotes pueden contener menos eventos por temporizador/cierre o tamano.
  Cada evento admite hasta 8 KiB serializados; cada body, hasta 60 KiB.
- Solo un lote activo. Ante fallo HTTP/red o timeout de 5 segundos hace hasta
  tres reintentos adicionales, a 1/2/4 segundos; conserva body, IDs y timestamp.
  Descarta el lote agotado y continua. Las advertencias usan codigos fijos
  una vez por codigo y documento, sin cuerpos, errores crudos ni identificadores.
- `visibilitychange` a oculto y `pagehide` intentan `sendBeacon`; si falta,
  lanza excepcion o retorna false, usan `fetch` con `keepalive` sin bloquear.
  No duplican un lote cuyo fetch sigue en vuelo.
- Limita el total intentado mientras esta oculta a 60 KiB para respetar el
  presupuesto del navegador. Lo que no cabe espera en memoria a que vuelva a
  estar visible; se pierde si el documento se destruye.
- Entrega **best effort**, no exactamente una vez: Beacon true solo confirma
  que el navegador acepto el envio. Un timeout/respuesta perdida puede causar
  reentrega; el stub no deduplica ni persiste. Evitar duplicados de negocio y
  correlacionar respuestas queda para las etapas de instrumentacion.

### Verificacion de etapa 2 — 2026-11-16

```powershell
node --test uis\backoffice\tests\test_telemetry.mjs uis\backoffice\tests\test_inventory_api.mjs
node uis\backoffice\generate-telemetry-contract.mjs --check
node --check uis\backoffice\telemetry.js
node --check uis\backoffice\telemetry-config.js
```

Pasan 19 pruebas: 12 del servicio y siete existentes. Reloj/transporte simulados
comprueban 10 s/20 eventos, envelope, sesion, allowlists de los 19 eventos,
1/2/4 s, limite de cola, timeout, Beacon/fallback, concurrencia, presupuesto de
bytes y funcionamiento sin configuracion/storage/UUID.

Navegador local: pagina de inventario carga el servicio; 20 llamadas sinteticas
producen un lote con ocho campos por evento y respuesta `received: 20`, sin
excepciones de pagina tras recarga controlada. API y receptor **simulados por
Playwright**, no verificacion extremo a extremo con FastAPI. La apertura inicial
sin API mostro el error de conexion esperado del inventario; la recarga uso
respuestas sinteticas. En las cuatro paginas se comprobo tambien la carga de
`track()`, el rechazo de un evento desconocido y abrir/cerrar el dialogo de login,
sin excepciones de pagina. Evidencia con API real y flujos completos sigue pendiente.

Panel interno de referencia para el contexto de negocio y las etapas del proceso de talento. Se mantiene separado del sitio público y del tracker de candidatos.

## Alcance de datos

- Las cifras aproximadas de plantilla y facturación y las líneas de negocio se transcriben de `CONTEXT.md`.
- Los nombres de las etapas se toman de `SPEC.md`.
- El directorio de proveedores consulta la API de operaciones; el resto de las cifras del panel sigue siendo contexto del proyecto y no una vista en tiempo real.
- El panel no consulta la API del tracker ni muestra registros personales de candidatos.
- El directorio muestra información comercial interna (tarifas, contactos y notas)
  y requiere sesión Nexova. Mantener API y panel en local/demo; CORS no sustituye
  la autenticación. El historial de inventario conserva su acceso público existente.

## Ejecutar localmente

Desde la raíz del monorepo:

```bash
npx --yes serve uis/backoffice -l 5502
```

Abrir http://localhost:5502. No usar el modo SPA; la app estática debe servir `index.html` en `/`.

## Analizador de incidencias (Outsourcing Helpdesk)

El panel incorpora una sección interactiva para cargar exportaciones CSV del servicio de helpdesk de Nexova (`/api/incidents/analyze`).

- **Carga de archivos**: Selector o drag & drop para archivos `.csv`.
- **Métricas visuales**: Visualización de total de registros, válidos, incompletos/inválidos, promedio de satisfacción con desglose de estrellas y distribución por categoría y estado.
- **Privacidad estricta**: Cero almacenamiento o renderizado de emails o datos sensibles de clientes en pantalla o consola.
- **Exportación**: Descarga directa de `results.csv` estructurado mediante el endpoint `/api/incidents/results/export`.

### Requisitos para el analizador

Asegúrate de que la API backend esté ejecutándose:
```bash
uvicorn services.api.main:app --port 8000
```

## Directorio de proveedores

La sección **Proveedores** consume `/api/suppliers` de la API local de FastAPI.

- Consulta todos los proveedores y aplica filtros de país y categoría sin recargar la página.
- Permite crear proveedores, actualizar tarifas y activar/suspender registros.
- Muestra errores de validación de la API y destaca renovaciones dentro de los próximos 60 días.
- Los datos semilla tienen fechas de renovación históricas; la vista no las modifica.
- El borrado está disponible en la API, pero no se ofrece como acción del backoffice.

Para cargar los datos iniciales, ejecutar desde `services/api/`:

```bash
uv run seed
```

## Inventario e historial

Proveedores y analisis/exportacion CSV reutilizan `inventoryApi.request` para
enviar la sesion Bearer y tratar errores/expiracion. El directorio se recarga al
iniciar sesion y retira sus tarjetas al cerrar; respuestas antiguas de filtros
no duplican filas. El cliente admite `responseType: "blob"` para CSV, sin cambiar
el tratamiento JSON de errores. FormData conserva el boundary del navegador.

Verificacion final 2026-11-05: siete tests Node pasan; navegador local con
datos sinteticos comprobo tarjetas/filtros/tarifa/estado/login/logout, historial,
tabla/resumen de incidencias y analisis/export CSV. Se verificaron Blob y enlace
`results.csv`, no un archivo guardado por el navegador integrado.

- El catalogo consume los seis campos de `AssetRead` en `/inventory/products`;
  los formularios registran entradas/salidas con el cliente centralizado.
- El historial en `order-history.html` consume `/inventory/orders` sin adaptar
  nombres: `movement_type` para Entrada/Salida, `asset_name` y `asset_sku` para
  el activo; cantidad, oficina, proveedor o destino, fecha y autor.
- `supplier` es null en salidas; `assigned_to` es null en consumo. El autor
  `user_uuid` es el ID del usuario autenticado convertido a string, no un UUID.
  IDs de entrada/salida pueden coincidir: su identidad incluye `movement_type`.
- Se conservan permisos existentes: lecturas publicas y escrituras autenticadas.
  Mantener el uso local/demo y datos sinteticos; no cargar destinos personales
  reales ni interpretar esta auditoria como autorizacion para publicar el historial.

Comprobacion automatica existente desde la raiz:

```bash
node --test uis/backoffice/tests/test_inventory_api.mjs
node --check uis/backoffice/order-history.js
```

La prueba del cliente comprueba tambien el renderizado del historial con un DOM
minimo y movimientos sinteticos de entrada/asignacion/consumo. No sustituye una
revision visual en navegador.

## Validación

- Abrir `/` y comprobar la carga del panel.
- Revisar navegación interna, enlace al sitio público y enlace al tracker.
- Verificar que el directorio carga desde `/api/suppliers`; probar filtros conjuntos, alta, tarifa y cambio de estado con la API local iniciada.
- Comprobar la sección "Analizador de incidencias" cargando `data/raw/incidents-nexova.csv`.
- Comprobar el layout en viewport amplio y móvil, foco visible y contenido con zoom.
- Confirmar que el panel no renderiza nombres, correos, teléfonos ni otros datos personales.

No hay scripts propios de lint, typecheck o build porque esta app es estática y
no añade un toolchain independiente. Las pruebas existentes del cliente se
ejecutan directamente con el runner integrado de Node indicado arriba.
