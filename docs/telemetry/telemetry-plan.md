# Plan de telemetría de Nexova

## Alcance de esta etapa

El catálogo de eventos y el flujo de inventario se definieron en la etapa 1. Esta etapa agrega el envelope común y los contratos JSON por evento; la estrategia stream/batch y sus controles operativos se completan en la etapa 3. No se implementa instrumentación.

El catálogo contiene **19 eventos**: **5 obligatorios del briefing** y **14 oportunidades identificadas**, distribuidos entre inventario/negocio, autenticación, rendimiento, errores y navegación.

## Envelope estándar

Cada evento se valida como un objeto con estos ocho campos de nivel superior, sin claves adicionales:

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `eventId` | string | Sí | UUID único por evento, generado antes de emitirlo. |
| `timestamp` | string | Sí | Fecha y hora ISO 8601 con zona horaria, por ejemplo `2026-11-11T20:00:00Z`. |
| `sessionId` | string o `null` | Sí | Identificador opaco de sesión; `null` cuando el evento ocurre antes de establecer sesión. |
| `userId` | string o `null` | Sí | Identificador interno opaco; `null` si aún no se conoce al usuario, como en un intento de acceso anónimo. No usar email ni nombre como identificador. |
| `event_type` | string | Sí | Uno de los 19 nombres de evento enumerados en este plan. |
| `schemaVersion` | string | Sí | Versión del contrato, inicialmente `1.0`. |
| `requestId` | string | Sí | Identificador de correlación opaco para enlazar frontend, backend y logs; no debe contener datos de usuario. |
| `properties` | object | Sí | Payload validado contra el allowlist del `event_type`; se rechazan propiedades no declaradas. |

`event-schemas.json` usa un formato de registro JSON personalizado, no un único JSON Schema draft-07. El documento contiene `formatVersion`, la definición común `envelope` y la lista `events`; cada evento tiene un allowlist explícito de `properties`. Para validar una instancia, se comprueba el envelope y luego `properties` contra la definición asociada al `event_type`; ambas capas rechazan campos desconocidos. Las definiciones de propiedad usan tipos y restricciones JSON Schema, además de `required` y `description` como metadatos del registro.

## Contexto y restricciones de negocio

Nexova administra material de formación y certificación, además de equipos de incorporación, en las oficinas de Valencia y Miami. Los productos pertenecen a un programa o área. Toda variación de stock debe proceder de una orden de entrada o salida trazable; no se permite editar existencias directamente.

Las señales deben permitir agregación por oficina y programa. Los importes se expresan en la moneda de la oficina (`EUR` en Valencia y `USD` en Miami), sin conversión en la telemetría. El idioma de interfaz y la oficina son dimensiones independientes. No se capturarán nombres de candidatos, clientes, consultores ni otros datos personales innecesarios.

## Flujo de inventario y puntos de instrumentación

El flujo representa el recorrido de un operador autenticado en el backoffice; los eventos describen oportunidades de medición, no cambios al comportamiento del sistema.

| Paso | Momento del flujo | Evento(s) |
|---|---|---|
| 1 | El operador inicia una sesión autenticada. | `auth_login_succeeded` (oportunidad) |
| 2 | Accede a una sección del backoffice y abre el inventario o consulta un producto. | `backoffice_section_viewed`, `inventory_item_viewed` (oportunidades) |
| 3 | Busca un producto o programa para decidir qué material gestionar. | `inventory_search_performed` (oportunidad) |
| 4 | Inicia una orden de entrada o salida y el sistema valida sus datos. | `inventory_order_validation_failed` (oportunidad) |
| 5 | Si intenta modificar el stock fuera de una orden, el sistema rechaza el cambio. | `direct_stock_edit_rejected` (obligatorio) |
| 6 | Si no completa la orden iniciada, el flujo termina sin registrar una orden. | `inventory_order_abandoned` (oportunidad), cuando pueda distinguirse de una sesión interrumpida |
| 7 | Al confirmarse una entrada o salida válida, se registra la orden trazable. | `inbound_order_created` o `outbound_order_created` (obligatorios) |
| 8 | Si la operación deja un producto por debajo de su mínimo, se activa la señal de umbral; el operador puede reconocerla. | `stock_threshold_triggered` (obligatorio), `inventory_threshold_acknowledged` (oportunidad) |

El flujo incluye más de cinco puntos y cubre explícitamente las validaciones fallidas, el rechazo de edición directa y la activación del umbral mínimo.

## Catálogo obligatorio del briefing

Cada hipótesis se vincula a una decisión concreta. Estos cinco eventos son el mínimo requerido, no el catálogo completo.

| `event_type` | Emisión | Clasificación | Hipótesis y decisión habilitada |
|---|---|---|---|
| `inbound_order_created` | Se confirma la llegada de un lote de material formativo o de incorporación de un proveedor. | Obligatorio (BRIEFING) | Capturamos `inbound_order_created` porque necesitamos saber cuánto material se compra o produce, para qué programa y con qué costo, lo que nos permite planificar la producción según la demanda esperada de matrículas. |
| `outbound_order_created` | Se confirma la entrega de un kit o certificado a un cliente, candidato, consultor o agente. | Obligatorio (BRIEFING) | Capturamos `outbound_order_created` porque necesitamos saber qué programas consumen más material y a qué ritmo, lo que nos permite anticipar la reposición antes de una ola de matrículas. |
| `stock_threshold_triggered` | El stock de un producto cae por debajo del mínimo configurado. | Obligatorio (BRIEFING) | Capturamos `stock_threshold_triggered` porque necesitamos saber con qué frecuencia cada programa se queda sin material disponible, lo que nos permite ajustar el mínimo o acelerar la reimpresión o reproducción. |
| `direct_stock_edit_rejected` | El sistema rechaza un intento de cambiar existencias fuera de una orden de entrada o salida. | Obligatorio (BRIEFING) | Capturamos `direct_stock_edit_rejected` porque necesitamos saber si el personal intenta eludir la trazabilidad, lo que nos permite reforzar la capacitación o ajustar los permisos en la oficina con más intentos. |
| `kit_cost_variance_detected` | El costo unitario de una entrada supera el umbral de variación respecto al historial del mismo material y proveedor. | Obligatorio (BRIEFING) | Capturamos `kit_cost_variance_detected` porque necesitamos detectar aumentos anómalos de precio de proveedores, lo que nos permite alertar a Elena y Laura para renegociar o buscar una alternativa. |

## Oportunidades identificadas

Se proponen catorce eventos adicionales en cinco categorías. Se conservarán en el diseño si sus propiedades pueden acotarse y su captura respeta las restricciones de privacidad.

### Inventario y negocio

| `event_type` | Emisión | Hipótesis y decisión habilitada |
|---|---|---|
| `inventory_item_viewed` | Un operador abre el detalle de un producto. | Capturamos `inventory_item_viewed` porque necesitamos saber qué productos consultan con mayor frecuencia, lo que nos permite priorizar la visibilidad de existencias y la planificación de material más consultado. |
| `inventory_order_validation_failed` | Una orden de entrada o salida no supera una validación y no puede confirmarse. | Capturamos `inventory_order_validation_failed` porque necesitamos saber qué validaciones impiden completar órdenes, lo que nos permite aclarar las reglas o mejorar el formulario y la capacitación. |
| `inventory_order_abandoned` | Se inicia una orden de entrada o salida, pero no se confirma antes de finalizar el flujo. | Capturamos `inventory_order_abandoned` porque necesitamos saber en qué tipo de orden se interrumpe el trabajo, lo que nos permite investigar fricciones operativas y reducir demoras en el registro trazable. |
| `inventory_threshold_acknowledged` | Un operador reconoce una alerta de stock bajo. | Capturamos `inventory_threshold_acknowledged` porque necesitamos saber si las alertas llegan a ser atendidas, lo que nos permite ajustar su seguimiento o escalamiento cuando se acumulan alertas sin respuesta. |
| `inventory_search_performed` | Un operador busca o filtra productos del inventario. | Capturamos `inventory_search_performed` porque necesitamos saber si los operadores encuentran el material que buscan, lo que nos permite mejorar la organización del catálogo y los filtros. No se justifica registrar texto libre de búsqueda. |

### Autenticación

| `event_type` | Emisión | Hipótesis y decisión habilitada |
|---|---|---|
| `auth_login_failed` | Un intento de inicio de sesión no se autentica, incluidas credenciales incorrectas. | Capturamos `auth_login_failed` porque necesitamos saber la frecuencia y el patrón operativo de los fallos de acceso, lo que nos permite detectar problemas de acceso y decidir si hace falta mejorar instrucciones o controles. No se registran contraseñas, emails ni nombres de usuario. |
| `auth_session_expired` | Una sesión autenticada expira y el sistema requiere volver a autenticarse. | Capturamos `auth_session_expired` porque necesitamos saber si las expiraciones interrumpen tareas del backoffice, lo que nos permite revisar la duración de sesión y reducir interrupciones sin debilitar la seguridad. |
| `auth_login_succeeded` | Un usuario completa correctamente el inicio de sesión. | Capturamos `auth_login_succeeded` porque necesitamos conocer el volumen y la distribución temporal de accesos al backoffice, lo que nos permite planificar disponibilidad y soporte en los periodos de uso. |

### Rendimiento

| `event_type` | Emisión | Hipótesis y decisión habilitada |
|---|---|---|
| `api_latency_recorded` | Se mide la duración de una solicitud a la API, de acuerdo con las rutas o grupos de operación definidos. | Capturamos `api_latency_recorded` porque necesitamos saber si las operaciones de backoffice responden dentro de niveles aceptables, lo que nos permite priorizar la optimización de las rutas que retrasan el trabajo. |
| `page_load_recorded` | Se mide el tiempo de carga de una vista del backoffice. | Capturamos `page_load_recorded` porque necesitamos saber qué vistas tardan en estar disponibles para los operadores, lo que nos permite priorizar mejoras en las pantallas que más afectan el trabajo diario. |

### Errores

| `event_type` | Emisión | Hipótesis y decisión habilitada |
|---|---|---|
| `api_request_failed` | Una solicitud de API termina en error y no completa la operación solicitada. | Capturamos `api_request_failed` porque necesitamos saber qué grupos de operaciones fallan y con qué frecuencia, lo que nos permite priorizar la corrección de fallos que bloquean el inventario o el acceso. |
| `frontend_uncaught_error` | El frontend detecta una excepción no capturada durante el uso del backoffice. | Capturamos `frontend_uncaught_error` porque necesitamos conocer los errores que interrumpen la experiencia sin ser reportados manualmente, lo que nos permite priorizar las correcciones que afectan a los operadores. |

### Navegación

| `event_type` | Emisión | Hipótesis y decisión habilitada |
|---|---|---|
| `backoffice_section_viewed` | Un operador navega a una sección del backoffice. | Capturamos `backoffice_section_viewed` porque necesitamos saber qué secciones se usan y en qué secuencia general, lo que nos permite priorizar mejoras de navegación y contenido operativo. |
| `backoffice_flow_abandoned` | Un operador inicia un flujo definido del backoffice y lo deja sin completar. | Capturamos `backoffice_flow_abandoned` porque necesitamos saber qué flujos se interrumpen con mayor frecuencia, lo que nos permite investigar pasos confusos o bloqueos operativos. La señal se limita al nombre del flujo y no reconstruye navegación individual innecesaria. |

## Estrategia de entrega

`stream` se reserva para señales que requieren detección o respuesta operativa en segundos; objetivo inicial: disponible para consumidores operativos en menos de 60 segundos. `batch` se procesa cada hora y se consolida en agregados diarios: es suficiente para analizar tendencias de consumo, uso y fricción, sin interrumpir operaciones por variaciones de un solo evento. La frecuencia es una hipótesis inicial para revisar con Operaciones antes de instrumentar.

| `event_type` | Entrega | Motivo de negocio u operación |
|---|---|---|
| `inbound_order_created` | Batch | Planificar producción según la demanda acumulada; una alerta por cada lote no cambia una decisión de segundos. |
| `outbound_order_created` | Batch | Analizar consumo por programa y ritmo de reposición en periodos, no actuar sobre cada entrega individual. |
| `stock_threshold_triggered` | Stream | La falta de material puede bloquear formación o incorporación; Operaciones necesita actuar en cuanto se cruza el mínimo. |
| `direct_stock_edit_rejected` | Stream | El rechazo indica un posible problema de trazabilidad o permisos que debe investigarse sin esperar al informe periódico. |
| `kit_cost_variance_detected` | Stream | Compras y responsables necesitan conocer el aumento anómalo al registrarse la entrada para evaluar renegociación o alternativa. |
| `inventory_item_viewed` | Batch | El interés por producto se interpreta como tendencia agregada, no como una alerta por cada consulta. |
| `inventory_order_validation_failed` | Batch | Los fallos de validación guían mejoras de formulario y capacitación al acumularse; no requieren escalar cada error de operador. |
| `inventory_order_abandoned` | Batch | La fricción se evalúa por tasas y pasos de abandono en ventanas periódicas; una interrupción individual no es accionable en tiempo real. |
| `inventory_threshold_acknowledged` | Batch | La cobertura de atención a alertas se revisa como tendencia para ajustar seguimiento; el disparo original ya viaja por stream. |
| `inventory_search_performed` | Batch | La encontrabilidad y uso de filtros se analizan de forma agregada para mejorar catálogo y navegación. |
| `auth_login_failed` | Stream | Una ráfaga de fallos puede impedir el acceso operativo y debe detectarse rápidamente; se agrupa para limitar ruido sin registrar credenciales ni identidad escrita. |
| `auth_session_expired` | Batch | La frecuencia de expiraciones informa ajustes de experiencia y política de sesión; un caso aislado no requiere intervención inmediata. |
| `auth_login_succeeded` | Batch | El volumen de accesos sirve para planificación de soporte y análisis de uso, no para alertas por cada autenticación correcta. |
| `api_latency_recorded` | Stream | La degradación de latencia puede bloquear órdenes activas; las medidas se necesitan con rapidez para detectar problemas por grupo de ruta. |
| `page_load_recorded` | Batch | Los tiempos de carga se usan para priorizar optimizaciones de vistas con datos agregados; un solo tiempo no justifica una alerta. |
| `api_request_failed` | Stream | Errores repetidos pueden impedir entradas, salidas o acceso; la primera señal se entrega pronto para iniciar diagnóstico. |
| `frontend_uncaught_error` | Stream | Una excepción no capturada puede interrumpir inmediatamente el backoffice; se necesita conocer el error para mitigar el impacto operativo. |
| `backoffice_section_viewed` | Batch | La popularidad y secuencia de secciones orientan mejoras de navegación y se analizan como patrones, no en segundos. |
| `backoffice_flow_abandoned` | Batch | Las tasas de abandono y pasos problemáticos requieren agregación para distinguir fricción recurrente de interrupciones aisladas. |

### Throttle, debounce y agregación

- **`api_latency_recorded`:** procesar en stream, con muestreo determinista del 10% de solicitudes exitosas por debajo de 1.000 ms y del 100% de las solicitudes que alcancen o superen 1.000 ms o fallen. `sample_rate` registra la probabilidad aplicada (`0.1` o `1.0`) para ponderar estimaciones; así se limita volumen sin ocultar latencias lentas ni fallos.
- **`api_request_failed`:** emitir de inmediato el primer fallo de cada combinación `route_group` + método + estado + `error_code`; durante una ventana fija de 60 segundos, acumular duplicados y emitir un resumen al cierre si los hubo. `occurrence_count` indica cuántos fallos adicionales representa el resumen y `window_seconds` vale `60`; la primera señal no se retrasa ni se pierde el total.
- **`frontend_uncaught_error`:** misma ventana de 60 segundos, agrupando solo por `error_fingerprint` sanitizado y `page_id`; mantener la primera emisión inmediata y un resumen con `occurrence_count` para duplicados. No se agrupa ni registra el texto o stack original.
- **`auth_login_failed`:** agrupar por método y código controlado de fallo durante 60 segundos. Emitir el primer intento enseguida y resumir repeticiones con `occurrence_count`/`window_seconds`; no utilizar email, nombre, IP ni credenciales como clave de agrupación.
- **`inventory_item_viewed`:** agrupar vistas por producto, oficina, programa, sesión y ventana de 5 minutos; emitir el conteo `occurrence_count` al cerrar la ventana o terminar la sesión, lo que ocurra primero. El análisis necesita demanda por producto, no una señal por cada render o apertura repetida.
- **`inventory_search_performed`:** aplicar debounce de 500 ms desde la última edición de búsqueda y emitir una sola vez cuando se complete la búsqueda o se apliquen filtros; nunca enviar texto libre. Registrar `result_count` y filtros controlados mantiene la señal de encontrabilidad sin capturar el término introducido.
- **`backoffice_section_viewed`:** emitir al cambiar realmente de sección, no en re-renderizados; no debounce de transiciones reales para preservar la secuencia de navegación.
- Para eventos de resumen, generar un `eventId` propio y conservar como `requestId` el de la primera ocurrencia que representa el resumen como ancla de correlación; no combinar request IDs. El resto de eventos de inventario se emite una vez por transición confirmada. Las repeticiones causadas por reintentos deben conservar el `eventId` original o deduplicarse por identificador estable de orden/transición antes de contabilizarse, sin duplicar movimientos de stock.

## Riesgos, privacidad y exclusiones

### Riesgos y mitigaciones

- **Identificadores seudónimos:** `userId`, `sessionId`, identificadores de producto/programa y referencias opacas de proveedor siguen siendo datos sensibles por su capacidad de vinculación. Limitar acceso por rol, restringir el uso a análisis operativo y acordar retención con el responsable de datos antes de instrumentar.
- **Alertas duplicadas o incorrectas:** asegurar emisión después de persistir la orden; deduplicar reintentos por evento/orden; comprobar el cálculo del stock después de cada entrada o salida antes de disparar un umbral.
- **Muestreo y métricas sesgadas:** conservar `sample_rate`, aplicar ponderación al calcular percentiles y contar el 100% de respuestas lentas y fallidas; revisar periódicamente que el muestreo represente las rutas utilizadas.
- **Coste y ruido de alta frecuencia:** aplicar solo las ventanas, agregaciones y muestreo declarados; conservar conteos agregados y la primera señal urgente para no borrar incidentes relevantes.
- **Comparación entre oficinas:** no sumar importes de EUR y USD como si fueran una sola moneda. Informar costos por oficina/moneda o aplicar una conversión fuera de la capa de telemetría y bajo una política financiera explícita.
- **Abandono ambiguo:** `inventory_order_abandoned` y `backoffice_flow_abandoned` se emiten únicamente por cancelación explícita o timeout definido del flujo (30 minutos sin actividad en el flujo); no inferir abandono a partir de cierre de pestaña o expiración de sesión solamente.

### Eventos y datos excluidos

- No capturar nombres, emails, teléfonos, credenciales, tokens, datos de candidatos/clientes/consultores/agentes, direcciones IP, geolocalización ni identificadores publicitarios.
- No capturar texto libre de búsquedas, rutas URL completas, parámetros de consulta, cuerpos de solicitudes/respuestas, mensajes de error crudos, trazas de stack ni contenido de formularios. Usar códigos, grupos y fingerprints sanitizados.
- No reconstruir grabaciones de sesión ni clickstreams detallados de una persona; la navegación se limita a secciones y flujos controlados, con acceso y retención acotados.
- No registrar ediciones directas de stock como cambios válidos: solo se mide su rechazo; toda variación efectiva permanece ligada a una orden trazable.
- Se descartaría un evento adicional que no habilite una decisión concreta, duplique otra señal o requiera datos personales no necesarios. El idioma de interfaz puede registrarse como dimensión independiente; nunca se usa como sustituto de oficina.

### Oportunidades consideradas y descartadas

- `inventory_search_query_entered`: descartado porque el texto libre puede contener nombres u otra información sensible; `inventory_search_performed` con filtros controlados y `result_count` basta para decidir mejoras de catálogo.
- `recipient_identity_recorded`: descartado porque el nombre o contacto del destinatario no es necesario para analizar consumo por programa; `recipient_type` y los identificadores opacos del material son suficientes.
- `api_request_payload_captured`: descartado por riesgo de capturar credenciales, datos personales o contenido de negocio, además de su alto volumen; los grupos de ruta y códigos de error permiten priorizar fallos.
- `stock_directly_changed`: descartado como evento válido porque una edición directa no debe modificar el inventario; solo se mide el rechazo mediante `direct_stock_edit_rejected`, y los cambios reales se trazan por órdenes.
- `backoffice_session_replayed`: descartado por la exposición desproporcionada de contenido e interacción individual y por su coste; las métricas agregadas y errores sanitizados cubren las decisiones definidas.

## Límites de implementación

- El contrato de `event-schemas.json` define para cada evento el allowlist explícito y la obligatoriedad de cada propiedad. Los eventos de inventario siempre incluyen `office` y la moneda derivada de la oficina (`currency`); los eventos relativos a un producto incluyen `product_id`, `product_category` y `programme_id` cuando el producto ya está seleccionado. `quantity` aplica cuando hay cantidad observada o intentada; las búsquedas sin producto seleccionado no inventan cantidad ni identificadores de producto.
- Los importes conservarán la moneda de la oficina (`EUR` en Valencia, `USD` en Miami); no se mezclarán idioma de interfaz y oficina.
- En `auth_login_failed`, `sessionId` y `userId` se incluyen como `null` cuando el intento no corresponde a una sesión ni a una identidad conocida. No se incorporarán credenciales, emails, nombres, direcciones IP, texto libre de error o contenido de solicitudes para resolver esa situación.
- `inventory_order_abandoned` y `backoffice_flow_abandoned` requieren cancelación explícita o timeout del flujo definido como 30 minutos sin actividad; no se inferirá el abandono por cierre de pestaña o expiración de sesión solamente.
