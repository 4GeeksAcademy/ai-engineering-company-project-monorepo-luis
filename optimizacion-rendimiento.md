# Optimización de rendimiento: Caching

> Instrucciones del proyecto de 4Geeks Academy para el monorepo transversal. Este documento reúne el reto, las tareas y los criterios de evaluación del README oficial en español.
>
> **Fuente oficial:** [README.es.md — ai-eng-performance-caching](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-performance-caching/README.es.md)

---

## 🎯 El reto

Trabaja sobre **tu copia del monorepo** de la empresa seleccionada al inicio del curso; no crees un repositorio nuevo.

La plataforma de la empresa está creciendo: hay más usuarios, más llamadas a la API e interacciones de interfaz más complejas. La telemetría indica que algunos endpoints reciben decenas de peticiones por minuto con consultas idénticas y que ciertos componentes se renderizan más de lo necesario.

Antes del próximo sprint, el equipo debe analizar la aplicación existente, encontrar oportunidades de caching de mayor impacto e implementarlas. El objetivo **no** es cachear todo, sino decidir de forma deliberada y justificada qué cachear, en qué capa y durante cuánto tiempo.

El resultado incluye código funcional y un informe técnico estructurado. El informe debe explicar el razonamiento detrás de las decisiones para que el equipo pueda entenderlas y mantenerlas.

## 🧠 Conocimientos y guía complementaria

### Cuándo conviene aplicar caching

Evalúa estos dos ejes antes de cachear:

- **Coste de cálculo frente al coste de almacenamiento:** determina si recalcular o volver a consultar un dato cuesta más que conservar una copia. Por ejemplo, una consulta de 400 ms que se ejecuta 200 veces por minuto puede justificar caching; una consulta de 2 ms cuyos datos cambian cada 10 segundos probablemente no.
- **Frescura frente a rendimiento:** un dato cacheado puede estar desactualizado. Un listado de productos podría tolerar un TTL de 60 segundos; un saldo bancario, no. Documenta explícitamente el equilibrio entre velocidad y consistencia en cada decisión.

### Técnicas en el frontend

- **Lazy Loading:** difiere la carga de componentes o datos hasta que sean necesarios. Puede reducir el bundle inicial y el tiempo hasta la interactividad. Es útil para componentes pesados que aparecen fuera del viewport inicial o solo en determinados flujos.
- **`useMemo`:** memoriza valores calculados costosos dentro de un componente y los recalcula únicamente cuando cambian sus dependencias. Úsalo cuando el cálculo sea genuinamente costoso; la memoización prematura añade complejidad sin beneficio.

### Alternativas de caching en el backend

En FastAPI se puede empezar con una caché **en proceso** (por ejemplo, un diccionario con TTL o un decorador) o usar una caché externa como **Redis**, si el stack lo soporta. Para cada endpoint, analiza si su respuesta depende de datos que cambian con frecuencia y si el cálculo representa un coste real. Las agregaciones de muchas filas, llamadas a servicios externos y filtros complejos suelen ser mejores candidatos.

### Disciplina con el TTL

Todo dato cacheado debe expirar. Sin TTL, los datos obsoletos pueden permanecer indefinidamente. Elige el TTL según la frecuencia con que cambian los datos subyacentes, no por comodidad.

### Identificar candidatos con evidencia

Antes de implementar caching, mide las peticiones. La guía propone agregar temporalmente a `main.py` un middleware de timing sin dependencias:

```python
import time
import logging
from fastapi import Request

logger = logging.getLogger("api.timing")

@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000  # ms

    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} | {duration:.1f}ms"
    )
    return response
```

Ejemplo de salida:

```text
GET /users → 200 | 312.4ms
POST /orders → 201 | 48.2ms
GET /products → 200 | 891.7ms
```

Interpreta los logs teniendo en cuenta:

| Señal | Qué permite evaluar | ¿Puede ser candidato? |
|---|---|---|
| Latencia consistentemente alta (>100–200 ms) | Coste de la operación | Sí, si se repite |
| Muchas llamadas a la misma ruta en poco tiempo | Frecuencia | Sí, si las respuestas son iguales |
| Misma ruta, estado y tiempos similares en lecturas | Estabilidad de los datos | Sí, con un TTL adecuado |

Una lectura lenta que se repite en ráfagas con los mismos parámetros (por ejemplo, `GET /products?category=electronics`) puede ser buena candidata. Una escritura `POST` o un `GET` cuya respuesta dependa de cada usuario no debe ir a una caché compartida; para datos privados, la clave tendría que estar acotada al usuario autenticado.

**Procedimiento sugerido:**

1. Navega por el frontend o repite peticiones con la misma URL y los mismos parámetros.
2. Prioriza rutas que combinen un volumen alto de llamadas con latencia elevada.
3. Registra en `CACHING_REPORT.md` el tiempo medido antes del cambio y el beneficio esperado o medido después.

### Carga de datos realista

Con pocas filas, casi todos los endpoints pueden parecer rápidos. Antes de sacar conclusiones del middleware, aumenta en local el volumen de las tablas que alimentan las lecturas más costosas (catálogo, pedidos, usuarios con relaciones, etc.).

- Pide al agente de código un seeder apropiado al stack (Alembic, Prisma, comando de gestión de Django, etc.) o un script SQL; revísalo antes de ejecutarlo.
- Prioriza datos variados, coherentes y con claves foráneas válidas: nombres, categorías, fechas, precios y relaciones. Evita cientos de filas idénticas de prueba.
- Vuelve a medir después de cargar los datos. En `CACHING_REPORT.md`, anota el volumen aproximado de filas antes y después, y cómo cambió la latencia de los endpoints seleccionados.

En el frontend, usa **React DevTools Profiler** para detectar componentes que se renderizan sin cambios reales en sus props. Usa la pestaña **Network** para localizar código JavaScript pesado que solo se necesita al entrar en otra ruta o flujo.

> **Importante:** no cachees todo lo que parezca lento. Mide y prioriza los casos en los que coste × frecuencia × estabilidad justifican el intercambio entre frescura y rendimiento.

---

## 🌱 Cómo iniciar el proyecto

Este proyecto continúa sobre el monorepo transversal existente; **no** hay que crear ni forkar otro repositorio.

1. Abre el monorepo en Codespaces o clónalo localmente.
2. Crea una rama de trabajo: `git switch -c feature/caching-optimisation`.
3. Comprueba que el frontend y el backend funcionan correctamente antes de cambiar código.

---

## 💻 Qué debes hacer

### Análisis y optimización del frontend

- [ ] Revisa la aplicación Next.js e identifica al menos **dos componentes o rutas** que sean buenos candidatos para Lazy Loading.
- [ ] Documenta para cada candidato por qué está justificado diferir su carga.
- [ ] Implementa Lazy Loading para esos componentes o rutas con `next/dynamic` o `React.lazy`.
- [ ] Revisa los componentes e identifica al menos **una oportunidad de `useMemo`** para un valor calculado no trivial, con un array de dependencias bien definido.
- [ ] Implementa esa optimización con `useMemo`. No lo apliques a cálculos triviales.

### Análisis y optimización del backend

- [ ] Enumera todos los endpoints de la aplicación FastAPI.
- [ ] Para cada endpoint, evalúa: **(a)** coste de la operación, **(b)** frecuencia de llamadas y **(c)** frecuencia con que cambian los datos subyacentes.
- [ ] Identifica al menos **dos endpoints** que cumplan los criterios de coste, frecuencia y estabilidad para caching.
- [ ] Implementa caching en esos endpoints. Se permite un diccionario en memoria con lógica de TTL, `functools.lru_cache` cuando corresponda o Redis si el stack lo soporta.
- [ ] Implementa la **invalidación de caché**: cuando cambien los datos subyacentes (por ejemplo, por una operación de escritura), limpia o marca como obsoletos los valores cacheados relevantes.

> **Seguridad:** no caches en una clave compartida respuestas con datos personalizados, de sesión o sensibles. Si corresponde cachear esos datos, acota la clave al usuario autenticado para impedir fugas entre usuarios.

### Informe técnico

- [ ] Añade al monorepo un informe llamado `CACHING_REPORT.md` (o equivalente) que incluya estas secciones:
  - **Decisiones en el frontend:** qué componentes se cargan de forma diferida y por qué; qué valores se memoizan y cuál es el beneficio medido o estimado.
  - **Decisiones en el backend:** para cada endpoint cacheado, coste de la operación, frecuencia estimada de llamadas, TTL elegido y estrategia de invalidación.
  - **Intercambios reconocidos:** al menos una explicación explícita del intercambio frescura/rendimiento, indicando el TTL elegido y por qué la posible desactualización es aceptable para ese caso de uso.
  - **Qué no se cacheó y por qué:** al menos un endpoint o componente que se consideró y se descartó, con su justificación.

---

## ✅ Qué vamos a evaluar

- [ ] Al menos **dos componentes o rutas** implementan Lazy Loading y tienen una justificación documentada.
- [ ] Al menos **un `useMemo`** se aplica a un valor calculado no trivial y tiene un array de dependencias correcto.
- [ ] Al menos **dos endpoints del backend** están cacheados con expiración basada en TTL.
- [ ] La invalidación de caché está implementada: se limpian los valores cacheados cuando cambian los datos subyacentes.
- [ ] Ningún dato privado o de sesión se almacena en una clave de caché compartida.
- [ ] El informe `CACHING_REPORT.md` está presente y cubre todas las secciones requeridas.
- [ ] Las decisiones del informe son específicas y justificadas; no basta con decir «se cacheó porque es lento».
- [ ] Se discute explícitamente al menos un intercambio entre frescura y rendimiento.

> La evaluación se centra en la calidad de las decisiones y la corrección de la implementación, no en la cantidad de componentes o endpoints cacheados. Se prefieren pocas decisiones bien justificadas a muchas decisiones sin justificación.

---

## 📦 Cómo entregar

Sube la rama a GitHub y abre un Pull Request hacia `main` en el repositorio del monorepo transversal. Comparte el enlace del PR según las instrucciones del instructor.

> Si el PR es aprobado, intégralo en `main`. De lo contrario, la funcionalidad no se despliega y la siguiente rama parte de código desactualizado, lo que puede generar conflictos de merge.
