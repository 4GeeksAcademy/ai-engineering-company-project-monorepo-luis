# Plan de telemetría de Nexova

## Alcance de esta etapa

Este documento inicia el diseño con el catálogo de eventos y el flujo de inventario. La etapa 1 define qué señales capturar y qué decisiones permiten; todavía no especifica los esquemas JSON ni la entrega stream/batch, que se completarán en las etapas siguientes. No se implementa instrumentación.

El catálogo contiene **19 eventos**: **5 obligatorios del briefing** y **14 oportunidades identificadas**, distribuidos entre inventario/negocio, autenticación, rendimiento, errores y navegación.

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

## Límites para las siguientes etapas

- Los eventos de inventario deben poder relacionarse con `office`, `product_id`, `product_category`, `programme_id`, `quantity` y `currency` cuando esos datos apliquen. En la etapa de esquemas se definirán explícitamente campos obligatorios y condicionales por evento.
- Los importes conservarán la moneda de la oficina (`EUR` en Valencia, `USD` en Miami); no se mezclarán idioma de interfaz y oficina.
- El envelope común y la representación de eventos de autenticación sin identidad conocida se definirán en la etapa 2. No se incorporarán credenciales, emails, nombres ni otros datos personales para resolver esa situación.
- Los esquemas y allowlists por evento se definirán en la etapa 2. La estrategia stream/batch, la limitación de eventos de alta frecuencia, los riesgos y las exclusiones se documentarán en la etapa 3.
- `inventory_order_abandoned` requiere una definición de cierre de flujo que distinga abandono de una sesión simplemente interrumpida; no se inferirá el abandono solo por una sesión expirada.
