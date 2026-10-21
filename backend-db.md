# Hito 5 — Backend: Gestión de Inventario con ORM y Doble Base de Datos

> Guía consolidada de implementación para el hito **Milestone 5 — Backend: Inventory Management with ORM & Dual Database** de 4Geeks Academy. Incluye el README oficial y el briefing específico de **Nexova**, la empresa elegida en este monorepo. Deben respetarse tanto **«Qué debes hacer»** como **«Qué vamos a evaluar»**. Si esta guía difiere de las fuentes oficiales, prevalecen el README y el briefing.

## Fuentes y estado de 4Geeks

- Cohorte: **Managing relational databases with FastAPI** (`managing-relational-databases-with-fastapi`), ID `1689`.
- Proyecto: **Milestone 5 — Backend: Inventory Management with ORM & Dual Database**, tarea `1014109`, slug `ai-eng-milestone-backend-development`, tipo `PROJECT`; estado observado en 4Geeks: **PENDING**.
- README oficial: [español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-backend-development/README.es.md) · [inglés](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-backend-development/README.md).
- Briefing Nexova: [nexova-BRIEFING.es.md](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/05-backend-development/nexova-BRIEFING.es.md).
- Monorepo del proyecto: `https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo-luis.git`.

## Reto y decisión arquitectónica

Extender el backend FastAPI existente del monorepo para crear una API centralizada de inventario. **No crear un repositorio ni un servicio FastAPI paralelo.** La autenticación y los usuarios siguen en la base TinyDB existente; los activos y movimientos de inventario se almacenan en Supabase/PostgreSQL y se acceden mediante **SQLModel**. La API mantiene ambas conexiones simultáneamente y enruta cada operación al almacén correspondiente.

La regla fundamental del negocio: el stock no se modifica directamente. Se calcula a partir del historial de movimientos; una entrada lo incrementa y una salida lo reduce. Cada movimiento debe identificar al usuario autenticado que lo registró.

### Auditoría del monorepo antes de empezar

En la rama principal inspeccionada existe un backend FastAPI en `services/api/`, autenticación TinyDB ya implementada y documentación de dependencias con `uv`. La API tiene rutas existentes de auth, usuarios, perfiles, proveedores e incidencias. A la inspección, no existían todavía la conexión SQLModel/Supabase ni el router de inventario.

El README de 4Geeks muestra una estructura genérica `services/{main.py,database.py,models.py,schemas.py,routers/inventory.py}`. En este monorepo, conserva el backend ya existente y organiza el hito bajo `services/api/` (por ejemplo `services/api/database.py`, `services/api/models.py`, `services/api/schemas.py`, `services/api/routers/inventory.py`) sin duplicar `main.py` o la autenticación. Antes de programar, inspecciona las rutas y convenciones actuales y ajusta la estructura sin romper los endpoints vigentes.

## Prerrequisitos y entorno

- [ ] Leer este documento y el briefing Nexova completo antes de definir tablas o endpoints.
- [ ] Confirmar que FastAPI y la autenticación TinyDB del proyecto anterior funcionan; si no, terminar esa capa primero.
- [ ] Añadir con `uv` las dependencias del hito (`sqlmodel` y `psycopg2-binary`) al proyecto que mantiene `services/api/pyproject.toml` y actualizar `uv.lock`/`requirements.txt` según las convenciones existentes. No usar SQLAlchemy directamente: el ORM requerido es SQLModel.
- [ ] Crear/configurar un proyecto Supabase de desarrollo y usar **Connect → Direct → Transaction pooler → URI** para obtener la cadena PostgreSQL recomendada.
- [ ] Guardar la cadena como `DATABASE_URL` en un `.env` local, excluido por `.gitignore`. No poner contraseñas, tokens ni cadenas de conexión en Python, docs públicos, commits o logs.
- [ ] Mantener intacta la configuración TinyDB de autenticación. No migrar ni replicar usuarios en Supabase.
- [ ] No aplicar `SQLModel.metadata.create_all()` contra una base compartida/de producción. `create_all()` es aceptable para el entorno de desarrollo del ejercicio; los entornos reales deben evolucionar mediante migraciones versionadas (por ejemplo Alembic).

## Entidades Nexova — nombres exactos del briefing

Usar estos nombres exactos en modelos, schemas y respuestas; no sustituirlos por `Product`, `InboundOrder` u `OutboundOrder` genéricos.

### `Asset` — activo

| Campo | Tipo | Reglas |
|---|---|---|
| `id` | entero, PK | Autoincremental. |
| `name` | string | Nombre descriptivo del activo. |
| `sku` | string | Código único del activo. |
| `category` | string | `hardware`, `peripherals`, `office_supplies` o `training_materials`. |
| `office` | string | `Valencia` o `Miami`. |
| `current_stock` | entero calculado | Solo en schema de respuesta; nunca columna persistida ni campo editable. |

### `AssetEntry` — entrada de activos

| Campo | Tipo | Reglas |
|---|---|---|
| `id` | entero, PK | Autoincremental. |
| `asset_id` | entero, FK → `Asset.id` | La FK debe imponerse en PostgreSQL. |
| `quantity` | entero | Unidades recibidas; validar como positivo. |
| `supplier` | string | Proveedor/vendedor. |
| `office` | string | Oficina receptora: `Valencia` o `Miami`. |
| `created_at` | datetime | Se establece automáticamente. |
| `user_uuid` | string | Identidad del usuario TinyDB que registró la entrada; no FK a una tabla clonada. |

### `AssetExit` — salida/asignación/consumo

| Campo | Tipo | Reglas |
|---|---|---|
| `id` | entero, PK | Autoincremental. |
| `asset_id` | entero, FK → `Asset.id` | La FK debe imponerse en PostgreSQL. |
| `quantity` | entero | Unidades asignadas/consumidas; validar como positivo. |
| `exit_type` | string | `allocation` o `consumption`. |
| `assigned_to` | string nullable | Obligatorio si `exit_type=allocation`; debe ser `null` si `exit_type=consumption`. |
| `office` | string | Oficina de la salida: `Valencia` o `Miami`. |
| `created_at` | datetime | Se establece automáticamente. |
| `user_uuid` | string | Identidad del usuario TinyDB que registró la salida; no FK a usuarios Supabase. |

**Identidad local del monorepo:** la implementación TinyDB existente obtiene la identidad de usuario como un `id` entero (doc_id), no como un UUID nativo. El campo de movimiento debe ser string, como exige el briefing; preservar la identidad autenticada existente, convirtiendo ese ID a su representación decimal (`str(user.id)`) si el sistema no tiene UUID. No inventar un UUID distinto ni añadir una tabla de usuarios a Supabase. Si cambia la identidad del sistema antes de implementar, adaptar esta decisión al contrato real y documentarlo.

## Doble conexión de base de datos

- [ ] Crear o extender el módulo de conexión (p. ej. `services/api/database.py`) conservando el cliente TinyDB existente para usuarios/auth y creando un `engine` SQLModel para Supabase a partir de `DATABASE_URL`.
- [ ] Asegurar que TinyDB solo gestione autenticación/usuarios y que `Asset`, `AssetEntry` y `AssetExit` se lean/escriban en PostgreSQL vía SQLModel.
- [ ] Definir `get_db` como dependencia FastAPI que cree/yield/ cierre una `Session` de SQLModel por petición, inyectada con `Depends()`. No guardar una sesión de request en variable global.
- [ ] Inicializar el esquema de desarrollo al inicio de la aplicación con `SQLModel.metadata.create_all(engine)` (y cargar los modelos para que estén registrados en metadata antes de crear tablas).
- [ ] Integrar el router en el `main.py` existente, preservando el lifespan y routers actuales.
- [ ] Configurar el driver/URL de acuerdo con el formato de conexión de SQLModel y el driver instalado, manteniendo los secretos fuera del repo.

## Modelos ORM y schemas separados

- [ ] Definir `Asset`, `AssetEntry`, `AssetExit` como modelos de tabla SQLModel (`table=True`) en un módulo ORM, con claves primarias, tipos, restricciones e índices necesarios.
- [ ] Definir relaciones FK de entradas/salidas hacia `Asset`; no crear FK hacia usuarios de TinyDB.
- [ ] Definir schemas Pydantic de request/response independientes en `schemas.py`; no reutilizar los objetos tabla como contrato de entrada/salida.
- [ ] El schema de respuesta de `Asset` incluye `current_stock`, calculado al consultar.
- [ ] Prohibir que el cliente envíe `id`, `created_at`, `user_uuid` del creador o `current_stock` en solicitudes de creación. El servidor establece identidad/fechas y calcula stock.
- [ ] Incluir `office` en el modelo y en los schemas pertinentes de respuesta; validar que `category`, oficina, `exit_type` y cantidades son valores válidos.
- [ ] Ningún endpoint debe devolver un objeto ORM directamente: serializar a un schema de respuesta.

## Router y contrato de endpoints

Crear un `APIRouter` dedicado con `prefix="/inventory"`, etiquetarlo apropiadamente e incluirlo en la app FastAPI existente.

| Método | Ruta | Comportamiento requerido |
|---|---|---|
| `GET` | `/inventory/products` | Lista activos con `current_stock` derivado. |
| `POST` | `/inventory/products` | Crea un activo; requiere autenticación. El stock inicial es cero. |
| `GET` | `/inventory/products/{id}` | Devuelve activo y stock actual; `404` si no existe. |
| `POST` | `/inventory/orders/inbound` | Registra una `AssetEntry`; requiere autenticación y atribuye usuario del token. |
| `POST` | `/inventory/orders/outbound` | Registra una `AssetExit`; requiere autenticación, valida asignación/consumo y stock. |
| `GET` | `/inventory/orders` | Lista entradas y salidas con los datos del activo y `user_uuid`. |

Las escrituras (crear activo y registrar entrada/salida) deben estar protegidas por la dependencia de autenticación TinyDB existente. Para los GET, el briefing Nexova no fija requisito de autenticación; definir la política consistente con el contrato existente del monorepo y documentarla, sin debilitar la autenticación en rutas de escritura.

## Reglas de negocio obligatorias

- [ ] **Stock derivado:** para un activo `a` en oficina `o`, calcular `current_stock = SUM(AssetEntry.quantity) − SUM(AssetExit.quantity)` filtrando ambas agregaciones por `asset_id=a.id` y `office=o`. El stock es por oficina porque Nexova opera en Valencia y Miami y `office` aparece en los dos tipos de movimiento. No mezclar inventario de oficinas distintas ni sumar movimientos de otro activo.
- [ ] **Sin columna editable de stock:** no almacenar `current_stock` en la tabla `Asset`; un nuevo activo empieza con stock cero.
- [ ] **Control de salida:** antes de insertar una salida, calcular existencias del activo y oficina solicitados. Si `quantity > available`, no persistir ningún registro y devolver HTTP `400` con el texto exacto: `Insufficient stock for asset '{name}'. Available: {available}, requested: {quantity}.`.
- [ ] Validar cantidad de entrada y salida como mayor que cero; evitar movimientos que no representan stock.
- [ ] **Tipos de salida y destinatario:** aceptar solo `allocation` o `consumption`; `assigned_to` debe tener valor en `allocation` y ser nulo en `consumption`. Rechazar incoherencias en request/schema antes de escribir.
- [ ] Guardar automáticamente `created_at` y `user_uuid` desde el usuario autenticado, no desde valores confiados del payload.
- [ ] El `office` del movimiento debe pertenecer a los valores exactos `Valencia`/`Miami`; validar relaciones coherentes con el activo y aplicar el cálculo neto por oficina.
- [ ] Usar consultas agregadas/relaciones cargadas eficientemente. Evitar el problema N+1 al listar órdenes y luego consultar el activo una vez por orden; usar joins/consultas agrupadas o carga anticipada apropiada.
- [ ] Manejar transacciones/errores de persistencia de forma que una salida rechazada no deje escrituras parciales. Para concurrencia real, documentar la limitación de la comprobación de stock y usar bloqueo/transacción apropiada si el entorno/driver lo permite.

## Datos semilla Nexova

Crear datos de desarrollo y no incorporarlos a la base compartida de producción. El briefing pide **mínimo 6 activos, 4 entradas y 3 salidas**.

### Activos mínimos (usar estos registros)

| name | sku | category | office |
|---|---|---|---|
| Portátil 14" Business | `NXV-IT-001` | `hardware` | Valencia |
| Portátil 14" Business | `NXV-IT-002` | `hardware` | Miami |
| Ratón ergonómico | `NXV-PER-001` | `peripherals` | Valencia |
| Hub USB-C | `NXV-PER-002` | `peripherals` | Miami |
| Resma de papel A4 | `NXV-OFF-001` | `office_supplies` | Valencia |
| Cuaderno de formación en liderazgo | `NXV-TRN-001` | `training_materials` | Valencia |

### Entradas y salidas mínimas

- [ ] Insertar al menos 4 `AssetEntry`: al menos dos entregas para `NXV-IT-001` con cantidades diferentes (el briefing da como ejemplo 10 y 5) y al menos una entrega para otros dos activos. Usar proveedores de ejemplo como `TechDistrib Valencia S.L.` y `Office Depot Miami`.
- [ ] Insertar al menos 3 `AssetExit`; incluir al menos una `allocation` con `assigned_to` informado y una `consumption` con `assigned_to=null`. Las cantidades deben caber en entradas del mismo activo **y oficina**.
- [ ] Asignar `user_uuid` coherente con usuarios TinyDB del entorno demo (representación string de la identidad real existente).
- [ ] Calcular los netos seed con entradas menos salidas por activo/oficina; verificar que `GET /inventory/products` los devuelve correctamente.
- [ ] Hacer el seed repetible/idempotente o controlar claramente la carga para que reinicializaciones de desarrollo no dupliquen movimientos ni inflen el stock.

El briefing no especifica cantidades exactas para cada registro semilla restante. Elegir valores coherentes y documentar el neto real, sin presentar cantidades de ejemplo como si fueran obligatorias.

## Qué debes hacer — checklist consolidado

### Configuración

- [ ] Configurar Supabase/PostgreSQL por `DATABASE_URL` en `.env` local e ignorado por Git.
- [ ] Inicializar simultáneamente TinyDB y SQLModel; implementar `get_db` como sesión por request vía `Depends()`.

### ORM, schemas y API

- [ ] Modelos SQLModel de `Asset`, `AssetEntry`, `AssetExit`, con FK correctas y campos Nexova exactos.
- [ ] Schemas Pydantic separados, incluyendo `current_stock` calculado en la respuesta del activo.
- [ ] Router `APIRouter(prefix="/inventory")` integrado a la aplicación existente y los seis endpoints implementados.
- [ ] Aplicar autenticación a escrituras, registrar identidad del usuario y validar reglas de stock, oficina y destinatario.
- [ ] Evitar N+1 al listar órdenes; evitar devolver directamente instancias ORM.
- [ ] Crear al menos 6 activos, 4 entradas y 3 salidas del briefing en entorno de desarrollo y probar el neto.

### Integración y seguridad

- [ ] Probar que auth continúa usando TinyDB y los datos de inventario usan PostgreSQL/Supabase.
- [ ] Verificar claves foráneas reales en la base de datos y fallo limpio ante IDs de activo inexistentes.
- [ ] Probar la salida superior al stock: HTTP 400, texto exacto y ningún movimiento persistido.
- [ ] Verificar `.env` ignorado y que ningún secreto/connection string aparezca en el diff, tests, logs o documentación comprometida.
- [ ] Ejecutar pruebas y pruebas manuales de endpoints, revisar diff y confirmar que los endpoints anteriores del servicio siguen funcionando.

## Qué vamos a evaluar

- [ ] Existen y se usan correctamente dos conexiones: TinyDB para autenticación/usuarios; Supabase con SQLModel para todo el inventario.
- [ ] Todos los endpoints quedan agrupados bajo `/inventory` en un `APIRouter` dedicado.
- [ ] `AssetEntry` y `AssetExit` tienen FK de base de datos hacia `Asset`.
- [ ] `current_stock` se deriva de movimientos; ningún endpoint permite editar directamente el stock.
- [ ] Los cálculos respetan oficina y activo; no hay mezcla de stock entre Valencia y Miami.
- [ ] La salida que excede stock devuelve HTTP 400 con el mensaje prescrito y se rechaza antes de persistir.
- [ ] Cada movimiento guarda el `user_uuid` del creador autenticado; no existe réplica de usuarios en Supabase.
- [ ] `models.py` (ORM) y `schemas.py` (Pydantic request/response) son archivos/clases separados; las rutas no exponen objetos ORM directamente.
- [ ] La sesión SQLModel se inyecta por petición con `Depends()`; no existe una sesión global de request.
- [ ] Los secretos de conexión están en `.env`, y `.env` está cubierto por `.gitignore`.
- [ ] Los nombres de entidades/campos respetan Nexova: `Asset`, `AssetEntry`, `AssetExit`, `asset_id`, `office`, `supplier`, `exit_type`, `assigned_to`.
- [ ] Están presentes los datos semilla requeridos y el endpoint de activos refleja el stock neto esperado.
- [ ] Los movimientos de listado incluyen información del activo sin patrón N+1 evidente.

## Pruebas de aceptación recomendadas

- [ ] App inicia con ambas conexiones configuradas; auth sigue verificando usuarios desde TinyDB y las tablas SQLModel se crean en el Supabase de desarrollo.
- [ ] `POST /inventory/products` crea un activo en stock cero; rechaza SKU duplicado o payload con `current_stock`/campos gestionados por servidor.
- [ ] `GET /inventory/products` y `GET /inventory/products/{id}` calculan stocks por activo y oficina; un ID inexistente da `404`.
- [ ] Crear entrada con autenticación persiste en Supabase y asigna usuario/fecha desde servidor; sin token no permite escribir.
- [ ] Registrar salida `allocation` sin `assigned_to` falla; registrar `consumption` con destinatario falla; tipos desconocidos y cantidades no positivas fallan.
- [ ] Salida dentro del saldo permite persistir; salida por encima del stock devuelve 400 con el mensaje Nexova exacto y no crea registro.
- [ ] Una salida en Miami no consume stock de Valencia (y viceversa); un activo distinto tampoco afecta el saldo.
- [ ] `GET /inventory/orders` devuelve órdenes relacionadas con su activo evitando una consulta individual por fila.
- [ ] Los datos seed satisfacen mínimos y netos esperados; volver a ejecutar seed no duplica movimientos.
- [ ] Ejecutar la suite existente completa y añadir pruebas unitarias/API con almacenamiento/configuración aislados; documentar comandos y resultados reales.

## Entrega

Subir los cambios del backend al fork/monorepo existente, verificar que `.env` no se rastrea y enviar el enlace del repositorio en la plataforma del estudiante. Esta guía es la especificación de trabajo; no constituye por sí misma la implementación ni la aprobación del hito.
