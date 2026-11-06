# Informe de línea base: optimización de rendimiento

Fecha de la auditoría: 2026-11-06
Rama: `feature/caching-optimisation`

## Alcance y límites

El frontend Next.js identificado en el monorepo es `uis/talent-pipeline-tracker`.
Sus registros de candidatos proceden de una API externa; la API FastAPI local de
`services/api` es un servicio distinto. La caché de FastAPI no aceleraría las
peticiones a esa API externa.

No hay telemetría de tráfico real disponible. Las frecuencias que aparecen abajo
son patrones de uso esperados, no tasas medidas. Las repeticiones del benchmark
sirven para comparar el coste local de las lecturas, no para demostrar cuántas
veces se invocan en el uso real.

## Método y mediciones del backend

Se usó `FastAPI TestClient` con cinco peticiones de calentamiento y 40 peticiones
GET secuenciales por endpoint, sin caché. Los datos se generaron para esta prueba
en archivos TinyDB y SQLite temporales, eliminados al terminar; no se leyeron ni
modificaron las bases locales del proyecto ni se usaron datos reales.

| Endpoint | Datos sintéticos | Mediana | p95 | Respuesta |
|---|---:|---:|---:|---:|
| `GET /api/incidents/summary` | 5.000 incidentes | 17,590 ms | 18,729 ms | 413 B |
| `GET /inventory/products` | 300 productos, 5.000 entradas y 5.000 salidas | 13,829 ms | 14,852 ms | 36.563 B |

Son tiempos de aplicación en proceso, no tiempos de red ni de producción. En el
resumen de incidentes, el máximo observado fue 70,289 ms frente a una mediana de
17,590 ms; la variación refuerza que una medición local pequeña no es un SLA.
Ninguno de los dos endpoints supera en esta prueba el umbral orientativo de
100–200 ms. Su candidatura se basa en que repiten agregaciones de lectura y
pueden volver a solicitarse durante la consulta de una pantalla, pero el volumen
real de esas solicitudes aún debe confirmarse.

## Inventario y evaluación de los 32 endpoints FastAPI

La frecuencia real es desconocida en todos los endpoints. «Lectura recurrente»
indica solo una expectativa de uso de interfaz; las escrituras suelen responder
a una acción puntual. Los costes son cualitativos, salvo donde se indica una
medición.

| Método y ruta | Coste / patrón y cambios de datos | Evaluación inicial |
|---|---|---|
| `GET /api/incidents/summary` | Escanea y agrega todos los incidentes; lectura potencialmente repetida. Cambia al crear o cambiar el estado de un incidente. | Candidata provisional: 17,590 ms mediana con 5.000 registros; invalidez al crear o actualizar estado. |
| `POST /api/incidents` | Inserta un incidente por acción; modifica el resumen y el listado. | No cachear; escritura e invalidación del resumen/listado. |
| `GET /api/incidents` | Lee y filtra todos los registros; puede repetirse al consultar la pantalla. Cambia con creación o cambio de estado. | No cachear de forma compartida: devuelve registros completos y su clasificación de privacidad debe confirmarse. |
| `GET /api/incidents/{id}` | Lectura puntual por ID; cambia al actualizar el estado. | Coste presumiblemente bajo; no priorizar sin medición y clasificación de acceso. |
| `PATCH /api/incidents/{id}/status` | Escritura puntual; cambia el detalle, el listado y el resumen. | No cachear; invalida las lecturas relacionadas después de una actualización correcta. |
| `POST /api/incidents/analyze` | Procesa un CSV y genera agregados; operación por acción, potencialmente costosa. Cambia el resultado global del último análisis. | No cachear POST; el CSV/resultados requieren tratamiento independiente. |
| `GET /api/incidents/results/export` | Lee y serializa el resultado del último análisis; cambia tras otro análisis. Requiere autenticación. | No priorizar: resultado mutable y global, descarga bajo demanda. |
| `POST /auth/login` | Verifica credenciales y genera una sesión/token; depende de la identidad. | Nunca cachear una respuesta compartida. |
| `GET /auth/me` | Lee la identidad y perfil de la sesión actual. | Nunca cachear entre usuarios; dato personalizado. |
| `POST /auth/forgot-password` | Inicia recuperación y puede enviar correo; depende de la cuenta. | No cachear; efecto externo y flujo por usuario. |
| `POST /auth/reset-password` | Cambia credenciales usando un token de recuperación. | No cachear; mutación sensible. |
| `POST /auth/change-password` | Verifica y cambia la contraseña de la sesión actual. | No cachear; mutación sensible. |
| `GET /inventory/products` | Lista productos y agrega entradas/salidas para calcular stock. Lectura potencialmente repetida; cambia al crear producto o movimiento. | Candidata provisional: 13,829 ms mediana con 300 productos y 10.000 movimientos; invalidar tras alta de producto y entradas/salidas. |
| `POST /inventory/products` | Inserta un producto por acción. | No cachear; invalida el listado de productos tras éxito. |
| `GET /inventory/products/{id}` | Busca un producto y calcula su stock con agregaciones; cambia con cualquier movimiento de ese producto. | No priorizar sin medición; cualquier caché requeriría invalidación por movimientos. |
| `POST /inventory/orders/inbound` | Inserta una entrada y cambia el stock/listado de movimientos. | No cachear; invalida productos y movimientos tras éxito. |
| `POST /inventory/orders/outbound` | Valida stock e inserta una salida; cambia el stock/listado de movimientos. | No cachear; invalida productos y movimientos tras éxito. |
| `GET /inventory/orders` | Lee, relaciona y ordena todos los movimientos; el volumen y coste pueden crecer. Incluye `user_uuid` y `assigned_to`. | No usar caché compartida: contiene identificadores/asignaciones internas; además falta medir su coste. |
| `POST /api/suppliers` | Inserta un proveedor por acción. | No cachear; escritura. |
| `GET /api/suppliers` | Lee y filtra el directorio TinyDB; lectura potencialmente repetida. Cambia con altas, tarifas, estado o borrados. Requiere autenticación. | No priorizar: no hay evidencia de volumen/coste; datos comerciales y de contacto, no compartir entre usuarios. |
| `GET /api/suppliers/{supplier_id}` | Lectura puntual de un proveedor; cambia con ediciones o borrado. Requiere autenticación. | No priorizar; revisar clasificación y acceso antes de cualquier caché. |
| `PATCH /api/suppliers/{supplier_id}/rate` | Actualiza tarifa y fecha por acción. | No cachear; escritura. |
| `PATCH /api/suppliers/{supplier_id}/status` | Actualiza estado por acción. | No cachear; escritura. |
| `DELETE /api/suppliers/{supplier_id}` | Borra un proveedor por acción. | No cachear; escritura. |
| `POST /users` | Registra una cuenta. | No cachear; escritura de identidad. |
| `GET /users` | Lista cuentas y requiere permisos de administrador. | No cachear de forma compartida; datos personales y acceso privilegiado. |
| `GET /users/{user_id}` | Lee una cuenta con autorización de propietario o administrador. | No cachear de forma compartida; dato personal y acceso por usuario. |
| `PUT /users/{user_id}` | Actualiza una cuenta con autorización de propietario o administrador. | No cachear; escritura de identidad. |
| `DELETE /users/{user_id}` | Borra una cuenta con autorización de propietario o administrador. | No cachear; escritura de identidad. |
| `GET /profiles/me` | Lee el perfil de la sesión actual. | Nunca cachear entre usuarios; dato personalizado. |
| `PUT /profiles/me` | Actualiza el perfil de la sesión actual. | No cachear; escritura personalizada. |
| `GET /health` | Devuelve un estado constante, sin consulta costosa. | No aporta un beneficio material de caché. |

### Hipótesis iniciales de la etapa 1

1. `GET /api/incidents/summary`: el agregado hace un recorrido completo por los
   incidentes. Hipótesis inicial: TTL de hasta 30 s; invalidar después de crear
   un incidente o modificar su estado. Validar que el panel realmente repite
   esta lectura y que ese retraso es aceptable.
2. `GET /inventory/products`: calcula stock con agregaciones de movimientos.
   Hipótesis inicial: TTL de hasta 15 s; invalidar después de crear un producto
   o registrar una entrada/salida. Confirmar que la frecuencia justifica la
   caché y que el equipo acepta ese límite de frescura.

Los TTL eran hipótesis para evaluar: la medición sin caché no probaba alto
tráfico ni una mejora perceptible.

## Etapa 2 — caché del backend

Se implementó `services/api/response_cache.py`, una caché en proceso con TTL
basada en reloj monotónico. Devuelve copias de los valores para que una respuesta
no pueda alterar el objeto guardado. Las claves de resumen incluyen la ruta de
la base TinyDB y las claves de productos identifican el engine SQLModel; ninguna
clave depende de credenciales, sesión o usuario.

| Endpoint | TTL | Invalidación después de una escritura correcta |
|---|---:|---|
| `GET /api/incidents/summary` | 30 s | `POST /api/incidents` y `PATCH /api/incidents/{id}/status` |
| `GET /inventory/products` | 15 s | `POST /inventory/products`, `POST /inventory/orders/inbound` y `POST /inventory/orders/outbound` |

Son datos agregados/internos compartidos por diseño en estas rutas, no respuestas
de sesión. La lectura puede quedar obsoleta como máximo hasta el TTL si otra
instancia, un script o una escritura directa a la base modifica los datos sin
pasar por estas rutas. Esta caché en proceso no se comparte entre workers o
instancias; si el despliegue escala horizontalmente, habrá que sustituirla por
una caché compartida o una estrategia de invalidación distribuida.

### Comparación local de latencia

Se repitió el benchmark con los mismos volúmenes de datos sintéticos de la línea
base. Se midieron 40 lecturas sin caché después de cinco calentamientos en la
línea base, y 40 lecturas con caché caliente después de una solicitud que llenó
la caché en la medición posterior. Tiempos de `FastAPI TestClient`, en proceso;
no son datos de producción.

| Endpoint | Mediana sin caché | p95 sin caché | Mediana con caché caliente | p95 con caché caliente |
|---|---:|---:|---:|---:|
| `GET /api/incidents/summary` | 17,590 ms | 18,729 ms | 1,272 ms | 1,927 ms |
| `GET /inventory/products` | 13,829 ms | 14,852 ms | 3,491 ms | 4,399 ms |

En esta prueba, la mediana caliente bajó aproximadamente un 92,8 % para el
resumen y un 74,8 % para el listado de productos. Es una comparación entre dos
ejecuciones locales, sensible al entorno y sin latencia de red; no demuestra la
frecuencia real de las llamadas ni permite prometer la misma mejora en
producción.

### Verificación de etapa

- Pasaron 23 pruebas preexistentes: `test_incidents_crud_api.py` y
  `test_inventory_api.py`.
- Una comprobación local con datos sintéticos confirmó reutilización, copia
  defensiva, expiración e invalidación al crear/cambiar incidentes, crear
  productos y registrar movimientos de entrada/salida.
- `compileall` para los tres módulos Python modificados y `git diff --check`
  pasaron. TestClient emitió la advertencia conocida de deprecación de
  `httpx`; no afecta el resultado de las pruebas.

## Revisión inicial del frontend

No se encontró uso de `useMemo`, `next/dynamic` ni `React.lazy` en el tracker.
La revisión de código da dos usos candidatos para diferir el mismo formulario
compartido:

| Ruta | Componente | Evidencia y oportunidad |
|---|---|---|
| `/` | `CandidateForm` en el flujo de alta | El formulario solo se muestra al abrir el alta, pero actualmente se importa desde el componente de lista. Su archivo fuente ocupa 10.134 B. |
| `/candidates/[id]` | `CandidateForm` en el flujo de edición | Solo se muestra al activar la edición, pero se importa al cargar el detalle. Diferir el módulo puede evitar cargar el formulario en ambas rutas hasta que se solicite. |

El formulario condicional se carga con `next/dynamic` tanto en la ruta de alta
(`/`) como en la de edición (`/candidates/[id]`); ambas muestran un estado de
carga mientras se descarga el módulo. El componente solo se necesita cuando el
usuario abre uno de esos formularios. Su archivo fuente ocupa 10.134 B. Esta es
una medida del código fuente, no del chunk emitido ni de bytes transferidos.

La lista memoiza con `useMemo` los elementos de filas de escritorio y tarjetas
móviles, con `[candidates]` como dependencia. La transformación construye dos
representaciones completas de la lista; estados de carga, error y apertura del
formulario no cambian esos datos. Así se evita recrear los elementos durante
esos renders. No se aplicó memoización a cálculos triviales. Sin React Profiler y
una lista de tamaño representativo, el beneficio de renderizado sigue siendo
cualitativo, no medido.

Las mediciones de 16.482 B para `candidate-list.tsx` y 17.305 B para la página de
detalle son tamaños de archivos fuente, no tamaños de transferencia. No se pudo
obtener un perfil de React ni tamaños de red fiables durante esta etapa.

## Etapa 4 — informe y aceptación

Se integran en este informe el inventario de la API, las decisiones de frontend,
las invalidaciones, los TTL, los intercambios de frescura y las comparaciones de
latencia del backend con datos sintéticos. No se cachean respuestas de sesión,
perfiles, cuentas ni movimientos internos.

Validaciones frontend ejecutadas tras las optimizaciones:

- `tsc --noEmit`: pasó.
- ESLint enfocado en `app/candidate-list.tsx` y `app/candidates/[id]/page.tsx`:
  pasó.
- `npm run build`: bloqueado por la misma resolución local de Next.js observada
  en la línea base. Webpack intenta resolver
  `./C:/Users/el_me/AppData/Local/nexova-build-cache/tracker-810d7d052aad/node_modules/next/dist/client/next.js`
  y `app-next.js`, que no encuentra. La instalación local contiene un enlace de
  `node_modules/next` hacia una ruta diferente (`E:\Users\...`). No se cambió la
  instalación ni la configuración para ocultar el error.
- El lint global sigue teniendo el error preexistente de
  `components/reset-password-form.tsx:35` (`react-hooks/set-state-in-effect`);
  las dos rutas modificadas pasan el lint dirigido.

Por el fallo de build no se pudieron confirmar los chunks de producción ni
medir bytes transferidos para el lazy loading. El informe y el código cubren los
requisitos de implementación, pero la aceptación del build y la medición visual
del frontend quedan condicionadas a reparar la resolución de Next.js y repetir
la validación en un entorno correcto.

## Validaciones backend y pendientes generales

- React DevTools Profiler y Network quedan pendientes: obtener un perfil con
  una lista sintética representativa, verificar el coste real de renders y medir
  chunks transferidos.
- La suite FastAPI pasó: 244 pruebas, 2 omitidas y 105 subtests. TestClient
  emitió una advertencia de deprecación de `httpx`; las pruebas terminaron bien.
- `compileall` para los módulos backend modificados y `git diff --check` pasaron.

## Siguiente comprobación

Resolver la instalación/ruta de Next.js y volver a ejecutar build; después,
medir los chunks y el render con React Profiler/Network usando datos sintéticos.
Si se obtiene telemetría local por ruta, reevaluar los TTL según frecuencia y
frescura. No cachear respuestas de autenticación, perfil, usuarios ni
movimientos con identificadores/asignaciones personales.
