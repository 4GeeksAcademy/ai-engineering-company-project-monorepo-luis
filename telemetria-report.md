# Telemetría de Nexova — Reporte técnico

> Guía de trabajo para **Application Telemetry — Telemetría de tu compañía – Reporte técnico**. Traduce al monorepo los requisitos oficiales del README y los criterios de evaluación. El resultado es un reporte técnico/operacional para ingeniería, no un tablero de negocio.
>
> **README oficial (español):** [Telemetría de tu compañía – Reporte técnico](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-telemetry-report/README.es.md)
> **Etapa de almacenamiento:** [`telemetria-storage.md`](telemetria-storage.md)
> **Captura y taxonomía:** [`telemetria-front.md`](telemetria-front.md), [`docs/telemetry/telemetry-plan.md`](docs/telemetry/telemetry-plan.md) y [`docs/telemetry/event-schemas.json`](docs/telemetry/event-schemas.json)
> **API y persistencia vigentes:** [`services/api/README.md`](services/api/README.md), [`services/api/telemetry_storage.py`](services/api/telemetry_storage.py), [`services/api/migrations/001_telemetry_events.sql`](services/api/migrations/001_telemetry_events.sql)
>
> **Prerrequisito de datos:** antes de analizar, la tabla `telemetry_events` debe contener al menos **20 eventos reales de prueba** generados desde el backoffice, con variedad de tipos e incluyendo al menos un evento técnico (por ejemplo, error o login fallido) además de eventos de negocio. Sin esos datos no se puede hacer el análisis solicitado. Usa un entorno de prueba autorizado y no incluyas datos personales.
>
> **Acceso 4Geeks:** se intentó autenticar usando `TOKEN_4GEEKS` del `.env` durante esta sesión; el endpoint de usuario devolvió HTTP 401 (`Invalid or Inactive Token`). El README oficial público en español sí se pudo consultar completo. No guardar el token en este documento; renueva la credencial de forma segura y no la vuelvas a compartir en texto.

---

## 🎯 Reto

Construye, dentro del backend del monorepo de Nexova, un pipeline Python/Pandas que transforma eventos guardados en métricas técnicas y un endpoint `GET /telemetry/report` que las entrega como JSON. Las métricas deben ayudar al equipo de ingeniería a entender:

- volumen y tipos de eventos en el tiempo;
- tasa de errores y grupos donde ocurren;
- latencia/rendimiento de las operaciones, si hay eventos medidos;
- señales operativas relevantes del catálogo aprobado.

**No incluir métricas de ventas, conversión, ingresos, productividad comercial o resultados de negocio.** Ese análisis pertenece al hito posterior de Data Pipelines. Datos crudos no son un reporte: cada métrica debe tener una dimensión temporal u operacional que permita interpretar el comportamiento del sistema.

### Reglas innegociables

- Las funciones de análisis viven en un módulo separado del endpoint. El endpoint no carga ni transforma eventos inline.
- Cada métrica recibe el mismo `start_date` y `end_date`, calculados una vez por request.
- Filtra `timestamp` y `event_type` en SQL, antes de traer datos. No cargues toda la tabla en Pandas.
- Convierte timestamps con `pd.to_datetime(..., utc=True)` antes de cualquier agrupación temporal.
- Usa operaciones vectorizadas de Pandas (`groupby`, `agg`, `count`, `sum`, `mean`); no loops para calcular métricas.
- El endpoint cachea el resultado 60 segundos por combinación de fechas. No recalcules el pipeline en cada request.
- Preserva la privacidad y los allowlists: analiza propiedades técnicas permitidas; nunca incluyas PII, tokens, cuerpos o mensajes crudos.

---

## 🌱 Contexto del repositorio y fuentes de verdad

- `services/api/` es la API FastAPI actual. La tabla persistente `telemetry_events` se creó en `services/api/migrations/001_telemetry_events.sql`; la conexión aislada de telemetría y el almacenamiento están en `services/api/telemetry_storage.py`. La integración exige Supabase/PostgreSQL; el fallback SQLite de inventario no debe usarse para el reporte.
- El monorepo todavía no tiene una carpeta de servicio `services/telemetry/`. El README oficial pide crear `services/telemetry/analysis.py`; antes de crearla revisa `services/README.es.md` y `services/api/README.md`, confirma el estado de `services/` y ubica el módulo donde se encuentra la query SQL y la sesión de almacenamiento de telemetría. Documenta cómo se conectan las funciones del pipeline a dicho almacenamiento. No dupliques credenciales ni configuración.
- El backend está acoplado a Supabase/PostgreSQL para leer los eventos persistidos. No simules datos reales con ejemplos inventados ni consultes Supabase de producción sin autorización explícita.
- El contrato del evento contiene 19 tipos y `tags` guarda `properties` aprobadas. Las dimensiones disponibles relevantes al reporte incluyen `route_group`, `http_method`, `status_code`, `duration_ms`, `error_code`, `page_id`, `auth_method`, `failure_code` y las dimensiones de inventario. Confirma tipo y significado exacto en `event-schemas.json` antes de usar una propiedad.
- Las funciones de reporte deben preguntar por salud/rendimiento del sistema. No convertir métricas de consumo de productos, órdenes o costes en análisis de negocio, aunque esos eventos existan en la misma tabla.

### Qué hacer si no hay datos suficientes

Comprueba el conteo y variedad del dataset en la base de prueba autorizada. Si hay menos de 20 filas, si faltan eventos técnicos o no hay propiedades de latencia válidas, detente antes de afirmar que las métricas están verificadas. Solicita generar eventos sintéticos desde el backoffice o registra el límite. Puedes desarrollar las funciones con fixtures sintéticos aislados, pero no presentes esos fixtures como filas reales ni como evidencia E2E.

---

## 🔁 Orden obligatorio de cualquier métrica

```text
cargar (SQL) → refinar (Pandas) → convertir tipos → agrupar → agregar → servir
```

1. **Cargar (SQL):** seleccionar solo columnas necesarias (por ejemplo `timestamp`, `event_type`, `level`, `tags`) y filtrar rango temporal y tipos de evento en SQL. Usa `timestamp >= start_date AND timestamp < end_date` en UTC, inicio inclusivo y fin exclusivo.
2. **Refinar (Pandas):** convertir `tags` JSONB a estructura tabular y extraer la dimensión operacional requerida. Quitar filas con dimensión nula; aplicar filtros adicionales por fila solo en Pandas.
3. **Convertir tipos:** `df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)`. Derivar el día UTC (`df['date'] = df['timestamp'].dt.date`) después de esa conversión. No agrupar timestamps string.
4. **Agrupar:** agrupar por dimensión relevante como fecha, tipo, `route_group` o código de error.
5. **Agregar:** aplicar `.count()`, `.sum()` o `.mean()`/otra agregación vectorizada con unidad claramente documentada.
6. **Servir:** devolver `reset_index().to_dict(orient='records')`; asegurar que fechas, enteros y valores nulos sean serializables a JSON.

El rango de fechas se resuelve una sola vez en el endpoint. Las funciones no vuelven a introducir el default de siete días ni a filtrar una segunda vez la ventana en Python.

### Ubicación de filtros

| Filtro/operación | Capa obligatoria | Reglas |
|---|---|---|
| `start_date`/`end_date` sobre `timestamp` | SQL | `>= start_date` y `< end_date`, ambos timezone-aware UTC. |
| Uno o varios `event_type` | SQL | `=` para uno o `IN (...)` para tipos de una razón/ratio; incluir numerador y denominador en la misma consulta. |
| Dimensiones de `tags` (p. ej. `route_group`) | Pandas | Extraer después de la carga; descartar null y agrupar por todos los valores presentes. No prefiltres a un único valor. |
| Flags derivados (p. ej. evento de error) | Pandas | Derivarlos después de cargar los tipos necesarios; computar tasas con numerador/denominador bien definidos. |
| Predicados opcionales sobre `tags` | Pandas por defecto | Push-down JSONB→SQL es optimización no obligatoria; si se usa, conserva equivalencia y cobertura de tipos. |

---

## 💻 Qué debes hacer

### Fase 1 — Pipeline de métricas en Pandas

Crea `services/telemetry/analysis.py` con **al menos tres funciones de métrica independientes**. Cada una debe aceptar `start_date` y `end_date`, consultar solo los datos pertinentes en Supabase/PostgreSQL y devolver una lista de diccionarios JSON-serializables.

Métricas mínimas sugeridas, a adaptar al catálogo real:

1. **Volumen de eventos por día y tipo** — pregunta técnica: qué señales recibe el sistema y cómo cambia el volumen a lo largo del tiempo. Usa los tipos de evento aprobados; no sumes órdenes/cantidades/costes como métrica comercial.
2. **Tasa de errores por tipo y/o día** — define explícitamente qué tipos o niveles son errores según el mapeo del almacenamiento actual; filtra los tipos de numerador y denominador en una sola query SQL cuando el ratio lo requiera. Reporta numerador, denominador y tasa para que el valor sea interpretable.
3. **Latencia operacional por día y grupo de ruta** — si hay `api_latency_recorded` con `duration_ms`, agrupa duración por fecha y `route_group`, e informa una medida (media y/o percentil) con unidad `ms`. Si el catálogo/dataset real carece de latencia, sustituye por otra señal técnica válida del catálogo, sin inventar propiedades.

Para cada función:

- [ ] Es pura/repetible respecto a sus argumentos y datos consultados: mismas entradas y mismo snapshot producen igual resultado. Sin escritura ni mutación del estado compartido.
- [ ] Acepta `start_date`, `end_date` como datetimes timezone-aware UTC; valida la precondición en una capa acordada y documenta límites invalidos (`start_date >= end_date`, naive datetime).
- [ ] Filtra rango temporal con inicio inclusivo y fin exclusivo y `event_type` en SQL, cargando solo las columnas necesarias.
- [ ] Extrae de `tags` solo las propiedades documentadas en el schema y necesarias para esa métrica.
- [ ] Convierte `timestamp` con `pd.to_datetime(..., utc=True)` antes de agrupar por día/tiempo.
- [ ] Usa Pandas vectorizado y `groupby`/agregaciones, nunca loops para implementar el cálculo de la métrica.
- [ ] Devuelve una lista de dicts JSON-serializable (sin objetos `Timestamp`, `NaN`/`Infinity` ni tipos NumPy incompatibles si el serializador no los maneja).
- [ ] No filtra identificadores de usuario/sesión/evento, supplier/product/person IDs, datos personales ni mensajes crudos en la respuesta.

El módulo puede delegar la lectura SQL en el repositorio/servicio de persistencia ya existente; no acoples Pandas a una URL de conexión escrita en código ni crees una segunda configuración Supabase. Mantén las consultas parametrizadas.

#### Manejo de rangos y resultados vacíos

- La API acepta ISO 8601 con zona horaria; normaliza a UTC antes de pasar al pipeline.
- Un rango sin eventos debe producir listas vacías o métricas vacías claramente definidas, no un error ni un valor global engañoso.
- Para ratio con denominador cero: define/documenta si `rate` es `null` y conserva conteos 0; no dividas por cero ni presentes un porcentaje inventado.
- No interpolar valores de fechas o tipos en SQL. Usa parámetros/SQLAlchemy expressions.

### Fase 2 — Endpoint `GET /telemetry/report`

Añade un router/endpoint FastAPI que use el pipeline aparte y exponga `GET /telemetry/report`.

Query params:

- `start_date`: ISO 8601 opcional.
- `end_date`: ISO 8601 opcional.
- Si falta una sola fecha, define una política consistente: recomendado, aceptar rangos explícitos solo cuando ambas estén presentes, o derivar la faltante de forma documentada. El comportamiento default es obligatorio cuando no se proporciona ninguna: ventana de últimos 7 días, `end_date = now` UTC y `start_date = end_date - 7 días`.
- Resuelve ambas fechas **una única vez por request** y pásalas a cada función; el rango sigue siendo inicio inclusivo/fin exclusivo.
- Rechaza datetimes inválidos, sin timezone o rango vacío/invertido con un error 4xx claro y sin detalles internos.

Estructura mínima de respuesta:

```json
{
  "period": {
    "from": "2026-11-11T00:00:00Z",
    "to": "2026-11-18T00:00:00Z"
  },
  "metrics": {
    "events_per_day": [],
    "error_rate_by_type": [],
    "latency_by_route_group": []
  }
}
```

Los nombres de claves métricas pueden adaptarse al catálogo, pero el esquema raíz `period` + `metrics` y las dimensiones claras deben mantenerse. No devuelvas una cifra sin periodo ni agregaciones sin etiquetas/unidades.

#### Caché

- El endpoint no ejecuta las queries y agregaciones nuevamente en cada request: añade cache en memoria con **TTL 60 segundos**.
- La clave de cache incluye el rango UTC normalizado (`start_date`, `end_date`) y cualquier filtro que pueda cambiar el resultado. Rangos equivalentes con distinto offset, una vez normalizados, pueden compartir clave.
- Misma clave dentro de TTL: responde el resultado cacheado sin volver a invocar el pipeline.
- Expirado o clave distinta: recalcula y refresca cache.
- Asegura copia/serialización apropiada para no permitir que una modificación del objeto de response corrompa el cache. Mantén el mecanismo acotado y thread-safe si la API atiende requests concurrentes.
- Los defaults temporales generan una clave diferente al avanzar `now`; documenta que el cache aplica a la ventana concreta normalizada.
- Usa la cache existente del repo si encaja, configurándola con TTL 60; si no, un cache local sencillo para este reporte es aceptable. No añadas dependencia grande para esta función.

El handler debe hacer únicamente validación/autorización si aplica, cálculo del periodo, lookup/cache y ensamblaje del resultado. No debe consultar directamente la tabla ni usar Pandas dentro del endpoint.

### Métricas técnicas válidas y límites

Adapta las tres métricas al catálogo que de verdad existe:

- `events_per_day`: volumen agrupado por `date` y `event_type`; responder a frecuencia/tendencias operacionales.
- `error_rate_by_type`: tasa basada en reglas existentes (`level` o tipos de fallo) y agrupación por tipo/día. Explica en el código/documentación qué clasifica como error; no supongas `level='error'` si mapeo previo no lo garantiza.
- `latency_by_route_group`: usar `api_latency_recorded`, `duration_ms` y `route_group` si hay eventos almacenados. No calcular latencia desde timestamps de eventos distintos.
- Alternativa a latencia faltante: conteo de fallos API por día y `route_group` o fallos de autenticación por día, siempre que sean tipos/campos aprobados y la pregunta sea técnica.

No incluyas análisis comercial/financiero ni ranking de productos/programas por consumo. Los identificadores de dimensión sensibles no se devuelven a menos que sean grupos controlados necesarios; evita usuario/sesión y dimensiones no técnicas.

### Actividad adicional — Métrica de autenticación

Si la instrumentación previa incluye `auth_login_failed` y `auth_login_succeeded`, añade una cuarta función para la **tasa diaria de fallos de acceso**:

```text
auth_failure_rate = login_failed / (login_failed + login_succeeded)
```

Requisitos:

- Carga ambos tipos en una única query SQL con `IN (...)`, no dos lecturas ni consultas dentro de un loop.
- Agrupa por día UTC en Pandas y devuelve, como mínimo, fallos, intentos totales y tasa.
- Si el denominador es 0, la tasa debe ser `null` (o política equivalente explícita) sin división por cero.
- Incluye la métrica en `metrics.auth_failure_rate`.
- No incluye ni calcula por usuario, email, IP, nombre, token o sesión.

### Actividad adicional — Dashboard visual simple

Opcionalmente añade una vista mínima, por ejemplo ruta estática `/telemetry`, en `uis/backoffice/` que consuma `GET /telemetry/report` y muestre un gráfico sencillo o tablas HTML para las métricas operacionales.

- Mostrar el periodo `from`/`to` presentado.
- Mostrar solo las métricas técnicas del endpoint; no crear KPIs de negocio.
- Reutilizar dependencias disponibles, o usar tablas HTML simples; no sumar una librería pesada por un gráfico básico.
- Proveer estado de carga/error/vacío de forma legible.
- Si la config/allowlist del repo prohíbe modificar frontend en la fase, prioriza los entregables backend y solicita/justifica la excepción antes de tocar `uis/backoffice/`.

---

## ✅ Qué vamos a evaluar

- [ ] Existe `services/telemetry/analysis.py` con al menos tres funciones de métricas independientes.
- [ ] Cada función sigue el orden `cargar (SQL) → refinar (Pandas) → convertir tipos → agrupar → agregar`.
- [ ] `timestamp` se convierte con `pd.to_datetime(..., utc=True)` antes de todo `groupby()` temporal.
- [ ] Los filtros `start_date`/`end_date` (`>=` / `<`) y tipos de evento se aplican en SQL; no se carga la tabla completa para filtrar en Python.
- [ ] No hay loops usados para calcular métricas; se usan operaciones vectorizadas de Pandas.
- [ ] Todas las funciones reciben el periodo resuelto por el endpoint, son independientes/repetibles y devuelven lista de dicts serializable a JSON.
- [ ] `GET /telemetry/report` acepta `start_date` y `end_date` ISO 8601 opcionales y usa UTC/últimos 7 días por defecto.
- [ ] El periodo se calcula una vez por request y se pasa a todas las funciones.
- [ ] El endpoint devuelve `{ "period": {...}, "metrics": {...} }`, con métricas temporalmente/operacionalmente agrupadas.
- [ ] Hay cache in-memory de TTL 60 segundos; un request repetido con igual rango dentro del TTL no recalcula el pipeline.
- [ ] Las métricas responden preguntas técnicas/operacionales (volumen, error, latencia/disponibilidad), no ventas, conversión o ingresos.
- [ ] Se manejan rangos inválidos, datos vacíos, zonas horarias y denominadores cero sin resultados engañosos.
- [ ] No se exponen PII, secretos, mensajes crudos ni identificadores de usuarios/sesiones.
- [ ] (Adicional) Si existen eventos de login, `auth_failure_rate` usa ambos tipos en una query SQL y agrupa la razón por día.
- [ ] (Adicional) Si se implementa dashboard, muestra el periodo y las mismas métricas operacionales del reporte.

---

## 🧪 Pruebas y aceptación técnica

Añade pruebas focalizadas siguiendo las convenciones actuales de `services/api/tests/` y el paquete instalado en `services/api/`. Como mínimo:

- [ ] Una prueba por función de métrica confirma filtros SQL (tipos y límites de fecha), transformación Pandas y forma serializable.
- [ ] Pruebas detectan que timestamps timezone-aware/string se interpretan en UTC y que una muestra que cruza medianoche cae en el día correcto.
- [ ] Pruebas para límites inclusivo/exclusivo: evento exactamente en `start_date` sí se incluye; exactamente en `end_date` no.
- [ ] Resultado vacío y propiedad de `tags` ausente/null no produce excepción, grupo `NaN` ni PII.
- [ ] Error rate y tasa de auth verifican numerador/denominador, grupos y denominator-zero.
- [ ] Rangos inválidos, naive datetime, offsets distintos y normalización UTC tienen resultado definido.
- [ ] Endpoint default usa los últimos 7 días UTC; params explícitos y periodo devuelto coinciden; cada métrica recibe el mismo periodo.
- [ ] Endpoint con la misma clave de cache hace una sola ejecución del pipeline dentro de TTL; al expirar o cambiar fechas, recalcula.
- [ ] Respuesta final se puede serializar con el JSON encoder de FastAPI; no incluye `NaN`, `Timestamp`, identificadores personales ni propiedades fuera del alcance.
- [ ] Pruebas usan datos sintéticos/fixtures y dependencias DB inyectables o un motor temporal; no consultan ni escriben contra producción.

No indiques que un test verifica consulta SQL si en realidad solo sustituye el DataFrame: comprueba las expresiones/llamada de repositorio o integra con una DB temporal compatible y documenta el alcance.

### Evidencia del endpoint

Incluye en el PR una muestra sanitizada del JSON generado a partir de datos reales de la tabla de prueba, por ejemplo:

```json
{
  "period": {"from": "<ISO UTC>", "to": "<ISO UTC>"},
  "metrics": {
    "events_per_day": [{"date": "<UTC date>", "event_type": "api_request_failed", "count": 2}],
    "error_rate_by_type": [{"event_type": "api_request_failed", "errors": 2, "total": 8, "rate": 0.25}],
    "latency_by_route_group": [{"date": "<UTC date>", "route_group": "inventory_read", "mean_duration_ms": 120.0}]
  }
}
```

Este JSON es solo una plantilla; sustituirlo por resultado observado. No presentar valores sintéticos como si fueran resultados reales.

---

## 🔐 Datos y seguridad

- Reporte de solo lectura: no modificar/limpiar filas en `telemetry_events`.
- No exponer connection strings, credenciales de Supabase, claves de servicio ni errores SQL en el endpoint.
- Las consultas son parametrizadas y limitadas a periodo/tipos relevantes.
- Evita dimensiones con datos seudónimos que identifiquen personas: `userId`, `sessionId`, `requestId`, IDs de negocio y cualquier llave sensible no son parte de la respuesta técnica de esta entrega.
- No devolver `tags` crudos, payloads, emails, nombres, IPs, rutas URL, textos de error, trazas o mensajes.
- `tags.route_group` y enums controlados son adecuados para agregación operacional; valida que los valores pertenezcan al catálogo.
- Mantén el endpoint protegido conforme al despliegue del API; no expongas el reporte o la DB de Supabase públicamente sin una decisión explícita de seguridad.

---

## 📦 Entrega

1. Mantén los cambios en esta copia del monorepo, no crees un repo nuevo.
2. Entregables backend: pipeline Python en `services/telemetry/analysis.py` y `GET /telemetry/report` registrado en el backend `services/`. Documenta la conexión con la persistencia Supabase ya existente.
3. Abre un Pull Request contra `main` con el título exacto: **`feat: telemetry report endpoint`**.
4. En la descripción del PR incluye:
   - Nombre de cada métrica y pregunta técnica/operacional que contesta.
   - Un ejemplo de JSON producido por el endpoint con datos reales de prueba.
   - Confirmación del periodo por defecto y del TTL de cache de 60 segundos.
   - Si se incluyeron `auth_failure_rate` y/o dashboard visual.
   - Pruebas ejecutadas y resultado real, limitaciones conocidas y confirmación de privacidad.
5. No integres el PR a `main` hasta que haya sido revisado/aprobado.

---

## 🧭 Checklist de cierre

- [ ] Se leyó completo el README oficial, en especial **«Qué Necesitas Hacer»** y **«Qué Vamos a Evaluar»**.
- [ ] Se validó que existan al menos 20 eventos de prueba variados en Supabase antes de aceptar métricas reales.
- [ ] El análisis usa timestamps UTC ya convertidos, filtros SQL parametrizados y DataFrame acotado.
- [ ] Se implementaron 3 o más funciones de métricas técnicas, separadas del endpoint.
- [ ] No hay loops en cálculo; todas las respuestas son arrays JSON-serializables.
- [ ] Endpoint acepta/normaliza periodo y usa siete días por defecto.
- [ ] Caché de 60 segundos demostrada sin repetir queries en la misma ventana.
- [ ] Se probaron métricas con datos vacíos, límites de fecha, timezone y cache hit/miss/expiry.
- [ ] No se mezcló reporte técnico con reporte de negocio ni se filtraron PII/secretos.
- [ ] JSON de evidencia proviene de datos reales de prueba y fue revisado/sanitizado.
- [ ] El diff contiene solo archivos autorizados y se ejecutaron validaciones documentadas.
- [ ] PR abierto con título exacto; no se hizo merge prematuro.

> **Límite de esta guía:** documenta el alcance e instrucciones, no afirma que ya existan 20 eventos en Supabase ni que el pipeline, endpoint, caché o dashboard estén implementados. La API de 4Geeks no autenticó el token del `.env` (HTTP 401); el README oficial del syllabus sí se consultó y se usa como fuente de requisitos.
