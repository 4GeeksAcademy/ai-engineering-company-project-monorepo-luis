# Hito 5 — Backoffice: Interfaz de Gestión de Inventario

Guía de auditoría e implementación para el proyecto **Milestone 5 — Backoffice: Inventory Management Interface** de 4Geeks Academy. Consolida el README oficial con el contexto de Nexova y el estado observado en este monorepo. Incluye explícitamente los apartados **«Qué debes hacer»** y **«Qué vamos a evaluar»**.

> **Orden de precedencia:** README oficial vigente de 4Geeks → briefing Nexova y contrato real de la API → convenciones y arquitectura actuales del monorepo. Esta guía no reemplaza esas fuentes. Si las fuentes o el código discrepan, detener el cambio afectado y resolver la discrepancia antes de inventar contratos o reemplazar arquitectura.

## Fuentes y estado de la tarea

- Cohorte: **Managing relational databases with FastAPI**, ID `1689`, slug `managing-relational-databases-with-fastapi`.
- Proyecto: **Milestone 5 — Backoffice: Inventory Management Interface**, tarea `1014110`, slug `ai-eng-inventory-management-backoffice`, tipo `PROJECT`.
- Estado consultado en 4Geeks el **2026-10-22**: **PENDING**.
- README oficial: [español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-inventory-management-backoffice/README.es.md) · [inglés](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-inventory-management-backoffice/README.md).
- Briefing Nexova de backend: [nexova-BRIEFING.es.md](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/05-backend-development/nexova-BRIEFING.es.md).
- Hito backend relacionado: tarea `1014109`, **Milestone 5 — Backend: Inventory Management with ORM & Dual Database**.
- Monorepo existente (no crear otro repositorio): <https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo-luis>.
- Guía local del hito backend: [`backend-db.md`](./backend-db.md).

## Reto

Añadir al backoffice existente de Nexova las vistas operativas para que el personal autenticado pueda consultar activos y stock, registrar entradas, registrar salidas/consumos y revisar el historial de movimientos. La interfaz debe consumir la API real de inventario del hito de backend; no basta con datos de ejemplo, mock o estado local para simular persistencia.

Prioridades de esta herramienta interna: claridad, rapidez, accesibilidad, estados de carga y errores comprensibles. Dos requisitos fáciles de pasar por alto y obligatorios son:

1. En el formulario de salida, mostrar el stock actual del activo seleccionado **antes del envío** y actualizarlo al cambiar la selección.
2. Mostrar de forma visible y legible los errores `400` de la API, en especial stock insuficiente. No imprimir el JSON en bruto ni fallar silenciosamente.

## Auditoría previa del monorepo — discrepancias que resolver

La inspección del repo y el código local muestra diferencias importantes respecto al supuesto del README oficial. Resolverlas antes de iniciar implementación funcional:

1. **Stack del backoffice:** el README oficial dice que `uis/backoffice` es una aplicación **Next.js** existente. En este monorepo, al auditarlo el 2026-10-22, `uis/backoffice/` contiene `index.html`, CSS y JavaScript estáticos; no hay `package.json`, estructura de rutas Next ni pantalla de login. Su README prescribe `npx --yes serve uis/backoffice -l 5502`.
2. **Inventario backend:** al revisar inicialmente la copia local no aparecían los endpoints `/inventory`; mientras se preparaba esta guía, la rama remota avanzó con los commits `7261edc`, `07e8cc1`, `ab134d7`, `5124248` y `d1560b1`. Tras sincronizarla, la versión publicada ya contiene modelos/servicio, `routers/inventory.py`, su registro en `main.py` y tests. El estado real de la rama al publicar esta guía sí incluye la API; verificar los schemas, configuración y OpenAPI actuales antes de implementar el frontend.
3. **Autenticación frontend:** FastAPI tiene login y autenticación Bearer existentes (`/auth/login`, `get_current_user`), pero la UI estática auditada no tiene patrón de login ni protección de rutas. La política oficial requiere login en las cuatro vistas.
4. **Contrato exacto:** el README usa términos genéricos “products”, pero el backend sincronizado implementa los nombres Nexova `Asset`, `AssetEntry` y `AssetExit`. Antes de integrar, contrastar respuestas/esquemas reales de OpenAPI y briefing; no renombrar ni inventar campos.

**Decisión de arquitectura pendiente:** confirmar cómo se alineará la app estática actual con el requisito oficial de Next.js y con la autenticación, sin crear un segundo backoffice ni sustituir funcionalidades ajenas al hito. El `AGENTS.md` raíz ordena detenerse y pedir aclaración si la arquitectura o las fuentes se contradicen. Esta guía conserva la ubicación `uis/backoffice/` y prohíbe crear una app paralela; la conversión/migración de stack no debe darse por aprobada por el mero hecho de escribir estas instrucciones.

**Precondición del frontend:** arrancar el backend con la configuración local requerida y confirmar en `/openapi.json` que los endpoints `/inventory` están accesibles y sus schemas coinciden con los formularios. La rama sincronizada ya implementa estos endpoints. No codificar contra mocks como si fueran API real. Los endpoints de lectura también deben confirmarse en OpenAPI para saber si exigen token; las cuatro páginas sí requieren sesión según el brief.

## Configuración y reglas de seguridad

- Trabajar dentro de `uis/backoffice/` siguiendo la decisión de arquitectura aprobada y el README de esa carpeta.
- Instalar dependencias solo según el stack acordado. El README oficial sugiere `npm install` por asumir Next.js; no ejecutar ese flujo sobre la app estática existente sin resolver la discrepancia.
- Configurar la URL base de la API como `NEXT_PUBLIC_INVENTORY_API_URL=http://localhost:8000` únicamente si la solución aprobada realmente es Next.js y el entorno local lo requiere. En otro stack, usar el mecanismo de configuración correspondiente, documentado y sin incrustar entornos de producción.
- `.env.local` y `.env*` están ignorados por el `.gitignore` raíz, excepto `.env.example`. Verificar con Git que ningún archivo de entorno se versiona.
- La URL base no es un secreto, pero los JWT sí: nunca incluir tokens en código, documentación, logs, capturas ni commits. No enviar una URL pública a producción sin revisar su configuración CORS/autenticación.
- Leer el token de la sesión/autenticación ya aprobada; no duplicar el login ni crear un segundo formato de sesión. Las llamadas a endpoints protegidos incluyen `Authorization: Bearer <token>`.
- No guardar ni mostrar datos personales reales. El `user_uuid` del historial es el identificador de autor exigido por el contrato; no revelar otros datos del usuario.
- La autenticación de interfaz mejora la experiencia, pero no reemplaza la autorización del backend. CORS no es autenticación.

## Vocabulario y entidades Nexova

Usar nombres y campos de dominio del briefing y de la API real. El contrato del hito backend documenta:

- **`Asset`**: activo de inventario. Campos de negocio `name`, `sku`, `category`, `office`; el stock actual se expone como `current_stock` calculado. No tratar el stock como editable.
- **`AssetEntry`**: entrada/entrega recibida: `asset_id`, `quantity`, `supplier`, `office`, `created_at`, `user_uuid`.
- **`AssetExit`**: salida: `asset_id`, `quantity`, `exit_type` (`allocation` o `consumption`), `assigned_to` según el tipo, `office`, `created_at`, `user_uuid`.
- Las oficinas del briefing son `Valencia` y `Miami`; categorías válidas: `hardware`, `peripherals`, `office_supplies`, `training_materials`.
- En la API, las rutas oficiales del hito se llaman `/inventory/products` y `/inventory/orders/...`. Mantener esas rutas públicas si OpenAPI las confirma, pero presentar el vocabulario Nexova correcto en etiquetas/formularios; no introducir entidades genéricas `Product`/`InboundOrder` como contrato de dominio.
- El stock es neto por activo y oficina (`AssetEntry` menos `AssetExit`). Mostrar la oficina y el saldo que devuelve la API; no sumar silenciosamente oficinas diferentes.

## Requisitos funcionales

### 1. Módulo central de integración API

- [ ] Crear un módulo dedicado (por ejemplo `lib/inventory.ts` si el stack acordado es TypeScript) que encapsule todas las llamadas a `/inventory`.
- [ ] Ningún componente/vista debe llamar a `fetch` directamente; la UI consume funciones tipadas del módulo.
- [ ] Centralizar URL base, Bearer token, serialización, parseo de respuestas y errores.
- [ ] En respuestas no exitosas `4xx`/`5xx`, extraer el mensaje del cuerpo (FastAPI suele usar `detail`) y convertirlo en un error legible y seguro; admitir `detail` string u objeto/lista sin mostrar JSON crudo.
- [ ] Tratar errores de red, respuesta vacía y datos malformados; limpiar/renovar datos de sesión solo según el patrón de auth existente.
- [ ] No registrar el token ni el cuerpo completo de una respuesta potencialmente sensible en consola.

### 2. Vista de activos — `/backoffice/inventory/products`

- [ ] Obtener y mostrar activos desde `GET /inventory/products` (datos reales).
- [ ] Mostrar `name`, `sku`, `category`, `office` y `current_stock` según el contrato confirmado.
- [ ] Añadir indicadores visuales de stock adecuado/bajo, además del color (texto/icono para accesibilidad).
- [ ] Elegir umbrales de UX, documentarlos en un comentario junto a su definición y mantenerlos coherentes. Propuesta inicial si Nexova no define umbrales: stock bajo `current_stock <= 5`; alerta intermedia `6–10`; adecuado `>10`. Estos umbrales solo clasifican la vista; no cambian reglas ni datos del backend.
- [ ] Incluir en cada fila enlaces/botones claros para registrar entrada o salida del activo, pasando su selección de forma segura y sin solicitar al usuario escribir un ID en bruto.
- [ ] Cubrir estados de carga, error con reintento y lista vacía.

### 3. Formulario de entrada — `/backoffice/inventory/orders/inbound`

- [ ] Cargar activos y enviar la entrada a `POST /inventory/orders/inbound`.
- [ ] El selector muestra nombres de activos (y SKU/oficina cuando haga falta distinguir duplicados); nunca requiere que se escriba el ID manualmente.
- [ ] Capturar campos que realmente requiera el API de `AssetEntry`, como activo, cantidad, proveedor y oficina. Confirmar obligatorios y formato en OpenAPI antes de cerrar el formulario.
- [ ] Validar cantidad positiva y selección válida en cliente para mejorar UX; backend sigue siendo autoridad.
- [ ] Enviar el Bearer token si el endpoint está protegido; atribución de usuario/fecha la gestiona el backend, no confiar en campos de autor enviados por el formulario.
- [ ] En éxito, limpiar el formulario y mostrar confirmación visible; actualizar/refrescar el stock afectado.
- [ ] En `400`, `500`, error de red o validación, preservar los datos útiles y mostrar el mensaje legible junto al formulario/campo aplicable.

### 4. Formulario de salida — `/backoffice/inventory/orders/outbound`

- [ ] Cargar activos y enviar a `POST /inventory/orders/outbound`.
- [ ] Al seleccionar un activo, obtener y mostrar reactivamente su `current_stock` actual antes de introducir cantidad. Volver a obtenerlo si cambia activo u oficina, si el contrato permite seleccionar oficina distinta.
- [ ] Mostrar contexto inequívoco de activo, oficina y stock disponible.
- [ ] Si la cantidad supera el saldo mostrado, advertir inline antes del envío y deshabilitar el envío si corresponde. Es una salvaguarda de UX: la API vuelve a validar para cubrir datos obsoletos/concurrencia.
- [ ] Respetar `exit_type` (`allocation`/`consumption`) y la regla de `assigned_to`: requerido para asignación, vacío/nulo para consumo. Evitar enviar incoherencias.
- [ ] Manejar específicamente HTTP `400` de stock insuficiente; mostrar el mensaje devuelto por API junto al campo cantidad, escapado como texto y no como HTML.
- [ ] En otros fallos `4xx`/`5xx` o red, presentar un mensaje visible y accionable sin perder datos.
- [ ] En éxito, confirmar, limpiar el formulario y refrescar el saldo.

### 5. Historial de órdenes — `/backoffice/inventory/orders`

- [ ] Obtener movimientos reales desde `GET /inventory/orders`.
- [ ] Mostrar por fila: nombre del activo, cantidad, tipo entrada/salida, fecha de creación y `user_uuid` creador; añadir oficina y SKU cuando estén disponibles y sean útiles para desambiguar.
- [ ] Distinguir entrada y salida con etiqueta/icono/color y texto accesible.
- [ ] Vista estrictamente de solo lectura: sin acciones para editar o borrar.
- [ ] Resolver carga, error/reintento, historial vacío y formato de fecha local legible sin asumir zona horaria incorrecta.
- [ ] Si el API devuelve solo IDs, resolver nombres de forma eficiente o usar la representación relacionada del backend; evitar una petición por fila/patrón N+1.

### 6. Protección de rutas y navegación

- [ ] Las cuatro vistas (productos, entrada, salida e historial) requieren autenticación.
- [ ] Usuario sin sesión válida: redirigir al login existente y conservar, si el patrón actual lo permite, la ruta destino para continuar tras autenticarse.
- [ ] No mostrar contenido privado brevemente antes de comprobar sesión (evitar flash de contenido); gestionar carga de sesión.
- [ ] Usar la misma fuente de verdad/patrón de auth existente. La auditoría actual no encontró login en `uis/backoffice`; resolver la discrepancia antes de inventar uno.
- [ ] Añadir enlaces de navegación a las vistas sin romper las secciones de resumen, proveedores e incidencias existentes.

### 7. Usabilidad y accesibilidad de herramienta interna

- [ ] Formularios con etiquetas asociadas, validación anunciada, foco visible, navegación por teclado y errores vinculados al campo.
- [ ] Confirmaciones/errores anunciados mediante región apropiada (`aria-live`) y no solo por color.
- [ ] Diseñar para uso operativo: formularios cortos, valores claros, botones distinguibles y confirmaciones de acciones.
- [ ] Comprobar viewport móvil y escritorio, zoom y contraste.

## Qué debes hacer — checklist consolidado

### Antes de programar

- [ ] Leer este archivo, `AGENTS.md`, `uis/backoffice/README.md`, briefing Nexova y README oficial del hito.
- [ ] Revisar `git status --short --branch` y diff actual; no asumir una rama ni un árbol limpio.
- [ ] Resolver la incompatibilidad documentada entre README oficial (Next.js), app existente (estática) y login ausente en frontend. El backend de inventario sí está presente en la rama sincronizada; validar su contrato/runtime en OpenAPI.
- [ ] Verificar `/openapi.json` de la API local y confirmar rutas, schemas, auth de cada endpoint y errores antes de construir formularios.

### Implementación

- [ ] Crear capa centralizada de API, sin `fetch` en componentes.
- [ ] Implementar las cuatro vistas/rutas funcionales bajo el backoffice existente.
- [ ] Mostrar activos/stock real con indicadores visibles y umbrales documentados.
- [ ] Implementar formularios de entradas y salidas con selectores por nombre, validaciones y confirmación.
- [ ] Mostrar stock reactivo antes de salida, advertencia cliente si se supera y error de API `400` inline.
- [ ] Implementar historial completo de solo lectura con nombre, cantidad, tipo, fecha y `user_uuid`.
- [ ] Proteger las cuatro vistas y enviar Bearer token a rutas API protegidas.
- [ ] Mantener términos/campos Nexova coherentes con briefing y API; no editar directamente `current_stock`.
- [ ] Gestionar carga, éxito, ausencia de datos, fallos HTTP y fallos de red.
- [ ] No romper funcionalidades existentes del backoffice.

### Validación, seguridad y entrega

- [ ] Probar los flujos con backend local y datos sintéticos/autorizados; nada de datos personales reales.
- [ ] Probar acceso anónimo a las cuatro vistas y redirección a login; probar solicitudes API con/sin token según OpenAPI.
- [ ] Probar entrada aceptada y rechazada; salida dentro del saldo, superior al saldo y error `400`; cambio de selección refresca el stock.
- [ ] Probar historial con entradas y salidas, nombres de activo y autor.
- [ ] Revisar estados responsive, accesibilidad básica y consola sin errores ni tokens.
- [ ] Confirmar `.env.local`/secretos excluidos; revisar diff y que no haya valores sensibles.
- [ ] Ejecutar solo tests/lint/build disponibles para la app realmente existente; documentar comandos y resultados reales, no declarar checks no ejecutados.
- [ ] Entregar cambios en el fork/repositorio existente y registrar el enlace en 4Geeks según el flujo de entrega.

## Qué vamos a evaluar — matriz de aceptación

| Criterio de 4Geeks | Evidencia de aceptación esperada |
|---|---|
| Existe un módulo dedicado de integración API, sin `fetch` en componentes. | Búsqueda/revisión de código: las llamadas `/inventory` salen del módulo común. |
| Las llamadas protegidas incluyen `Authorization` con el token actual. | Prueba de red/API con sesión válida; token ausente no se suplanta ni se registra. |
| Productos cargan datos reales y muestran `current_stock` con indicadores. | Vista obtiene `/inventory/products`, muestra stock y etiquetas accesibles; umbrales documentados en comentario. |
| El formulario inbound envía bien y siempre da confirmación o error legible. | Prueba de éxito, `4xx`/`5xx` y red; nunca error silencioso. |
| El formulario outbound muestra stock actual antes de enviar y reacciona a selección. | Elegir distintos activos/oficinas actualiza saldo visible antes de cantidad/envío. |
| Outbound advierte cuando la cantidad supera el saldo. | Aviso cliente visible antes del submit, conservando validación servidor. |
| `400` de salida muestra el mensaje legible de API. | Error inline junto a cantidad, no JSON crudo/consola únicamente. |
| Historial muestra órdenes distinguiendo entrada/salida, activo, cantidad, fecha y `user_uuid`. | Tabla/lista de solo lectura con todos los campos requeridos y nombres correctos. |
| Las cuatro vistas redirigen usuarios no autenticados al login. | Prueba individual de cada ruta y ausencia de flash de datos privados. |
| Etiquetas y nombres respetan el briefing Nexova. | UI usa entidades/campos aprobados; stock no editable y oficina correctamente representada. |
| El producto final consume la API real y maneja fallos correctamente. | Validación end-to-end en entorno local con backend operativo y resultados documentados. |

## Pruebas de aceptación sugeridas

1. **Productos:** sesión válida; aparecen activos y `current_stock`; indicador coincide con umbrales por oficina; error recuperable si backend falla.
2. **Autenticación:** abrir directamente cada una de las cuatro rutas sin sesión; redirige al login. Repetir con token expirado/inválido y comprobar manejo consistente.
3. **Entrada:** selector por nombre; cantidad/proveedor/oficina válidos; envío exitoso limpia y confirma; respuesta de error se muestra y preserva los campos corregibles.
4. **Salida:** seleccionar un activo y observar stock antes de introducir cantidad; cambiar activo/oficina y observar actualización. Cantidad superior muestra advertencia cliente; si el API devuelve `400`, mensaje aparece inline; salida válida refresca stock.
5. **Historial:** comprobar movimientos de ambos tipos, activo, cantidad, fecha y autor; sin controles de edición/borrado.
6. **Errores:** `401`, `404`, `422`, `500`, desconexión y respuesta no JSON no rompen la UI ni imprimen estructuras crudas.
7. **Seguridad:** `.env.local` y JWT no rastreados; no hay token en consola, URL, captura o diff.
8. **Regresión:** las vistas existentes del backoffice (resumen, proveedores e incidencias) siguen funcionando.

## Entrega

- Publicar en el **monorepo/fork existente**, no crear un repositorio nuevo.
- Verificar que ningún `.env*` local, token, clave ni dato privado se incluyó.
- Compartir el enlace del fork en la plataforma del estudiante.
- Esta guía es documentación de trabajo; no constituye por sí sola la implementación ni la aprobación del hito.
