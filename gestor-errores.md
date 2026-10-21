# Gestión de Errores — Guía del proyecto

> Guía de trabajo para la tarea **Error Handling / Gestión de Errores** de 4Geeks Academy. Consolida el README oficial, sus secciones **«Qué debes hacer»** y **«Qué vamos a evaluar»**, y una auditoría inicial del monorepo de Luis. El objetivo es mejorar la resiliencia y la comunicación de errores existentes; no añadir funcionalidades. Si esta guía difiere del README oficial, prevalece el README.

## Fuentes y estado

- Cohorte: **Error handling, debugging and testing** (`error-handling-debugging-and-testing`).
- Tarea: **Error Handling**, tipo `PROJECT`, ID `1003162`, slug `ai-eng-error-handling`; en 4Geeks figura como **PENDING** al momento de la consulta.
- README oficial: [español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-error-handling/README.es.md) · [inglés](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-error-handling/README.md).
- Repositorio de trabajo: `https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo-luis.git`.

## Reto y alcance

Auditar el monorepo existente y aplicar una estrategia de manejo de errores consistente en frontend, backend y scripts. Evitar que un fallo deje la aplicación o al usuario en un estado indefinido. Las operaciones asíncronas del frontend deben comunicar **cargando, éxito y error**; los mensajes al usuario deben ser claros, accionables y no revelar detalles técnicos o información sensible. Los errores se capturan cerca de la operación que puede fallar, no con un `try/catch` o `try/except` gigante.

No se necesita un repositorio nuevo ni un boilerplate. Trabajar sobre este monorepo, en la rama `feature/error-handling-audit`, revisar el código sistemáticamente y usar commits claros. Si se abre un PR, una vez aprobado debe integrarse en `main`, conforme a las instrucciones oficiales.

## Auditoría inicial del monorepo

Inventario orientativo (volver a comprobar antes de editar, ya que el código puede cambiar):

- **Frontend:** `uis/backoffice/` y `uis/talent-pipeline-tracker/`. Aparecen llamadas `fetch` en `uis/backoffice/suppliers.js`, `uis/backoffice/incidents.js`, `uis/talent-pipeline-tracker/lib/nexova-api.ts` y `uis/talent-pipeline-tracker/lib/api.ts`.
- **Backend FastAPI:** `services/api/`, especialmente `routers/` y las llamadas externas (por ejemplo `email_service.py`). Revisar controladores, servicios y modelos pertinentes.
- **Scripts Python:** `scripts/` y scripts operativos existentes en `services/api/`.
- **Logs/salidas:** buscar `console.error`, `print`, excepciones capturadas sin acción y cualquier respuesta que exponga stack traces, secretos, rutas internas o datos personales.

Este inventario no es un informe exhaustivo ni sustituye el escaneo de todo el repositorio. No asumir que un hallazgo está presente solo porque una ruta aparezca aquí: verificar el código y documentar archivo y línea al realizar la auditoría.

## Flujo de trabajo recomendado

1. Antes de editar, inspeccionar el monorepo completo con el coding agent y obtener un informe **sin cambios**. Priorizar hallazgos por severidad: crítico, alto, medio y bajo. Anotar ruta, línea/rango, categoría, problema y corrección sugerida.
2. Revisar el informe y el checklist de esta guía. Implementar solo correcciones relacionadas con gestión de errores.
3. Ejecutar las pruebas disponibles y comprobar los recorridos de error además de los de éxito; verificar que la UI recupera su estado y que mensajes/respuestas no filtran información.
4. Revisar `git diff`, corregir regresiones y hacer commits pequeños con mensajes descriptivos.

### Prompt de auditoría para el coding agent

```text
Eres un ingeniero de software senior auditando este repositorio en busca de problemas de gestión de errores. Analiza todo el monorepo (frontend, backend y scripts) y NO hagas cambios. Devuelve únicamente un informe ordenado por severidad (CRÍTICO > ALTO > MEDIO > BAJO).

Busca:
1. Operaciones asíncronas o de I/O sin manejo de errores (fetch, await, lectura/escritura, parseo JSON/CSV).
2. try/catch o try/except demasiado amplios, que cubran funciones o secciones grandes en vez de la operación peligrosa concreta.
3. Errores capturados e ignorados (catch vacío, except: pass, retornos que ocultan fallos).
4. Mensajes crudos, códigos HTTP, errores de parseo o tracebacks que puedan llegar a usuario/cliente.
5. Logs o respuestas que puedan revelar secretos, cadenas de conexión, rutas internas o datos personales.
6. Operaciones asíncronas de UI sin estados visibles de cargando, éxito y error.
7. Estados de error sin una acción clara para continuar (reintentar, volver al inicio o contactar soporte).
8. Estados de carga que no se limpian en finally o ante todos los resultados.
9. Accesos a propiedades anidadas posiblemente undefined/null sin optional chaining ni valores fallback seguros.
10. Rutas FastAPI sin errores JSON estructurados/códigos HTTP adecuados, o llamadas a servicios externos sin gestión de fallos.
11. Scripts Python que no manejan errores de I/O/entrada malformada o que terminan con código 0 ante fallos críticos.
12. console.error/print con información interna sensible.

Por cada hallazgo incluye: severidad, ruta y línea/rango, categoría, descripción breve y corrección sugerida. No cambies archivos y no incluyas secretos ni datos personales en el informe.
```

## Qué debes hacer

### Frontend — Next.js / TypeScript

- [ ] Localizar todas las llamadas `fetch` o llamadas a API del frontend; envolver cada operación susceptible de fallo en un `try/catch` **específico y acotado**.
- [ ] Para cada operación asíncrona que carga datos, mostrar los tres estados: **cargando** (spinner/skeleton), **éxito** (datos) y **error** (mensaje legible con una acción).
- [ ] Reemplazar errores crudos —por ejemplo `Error 500` o `Unexpected token`— por explicaciones comprensibles para el usuario.
- [ ] Incluir una acción útil en cada estado de error: botón para reintentar, enlace a inicio o indicación para contactar soporte.
- [ ] Usar optional chaining (`?.`) para propiedades anidadas que puedan ser `undefined`.
- [ ] Proporcionar defaults/fallbacks seguros para valores `null` o `undefined` al renderizar.
- [ ] Usar `finally` para limpiar estados de carga, independientemente del resultado.

### Backend — Python / FastAPI

- [ ] Revisar cada handler y capturar excepciones en el ámbito correcto; evitar un único bloque amplio que oculte causas distintas.
- [ ] Devolver códigos apropiados (`400`, `404`, `422`, `500`) y cuerpos JSON limpios y estructurados, sin tracebacks crudos.
- [ ] No exponer en respuestas de error cadenas de conexión, rutas internas, claves, secretos ni datos sensibles.
- [ ] Manejar fallos de todas las llamadas a APIs o servicios externos usados por el backend.

### Scripts — Python

- [ ] Manejar errores de lectura/escritura y parseo CSV con `try/except` acotados y mensajes informativos en `stderr`.
- [ ] Terminar con código distinto de cero (por ejemplo `sys.exit(1)`) cuando haya un fallo crítico.
- [ ] Validar datos faltantes o malformados antes de iniciar el procesamiento.

### Revisión general

- [ ] Revisar `console.error` y `print` para asegurar que no expongan información interna sensible; eliminar o sustituir las salidas inseguras.
- [ ] No introducir nuevas funcionalidades ni refactorizar partes ajenas al manejo de errores. Mantener el alcance en resiliencia y comunicación de errores del código existente.

## Qué vamos a evaluar

- [ ] Todas las operaciones asíncronas del frontend presentan cargando / éxito / error.
- [ ] Los mensajes de error al usuario son legibles e incluyen una acción clara.
- [ ] `try/catch` y `try/except` se limitan a operaciones concretas y no envuelven funciones enteras.
- [ ] `finally` limpia correctamente los estados de carga.
- [ ] Optional chaining y fallbacks previenen fallos de renderizado ante `undefined`/`null` donde corresponda.
- [ ] Las rutas backend devuelven respuestas de error limpias, estructuradas y con códigos HTTP correctos.
- [ ] Ningún error enviado al cliente filtra información sensible.
- [ ] Los scripts Python manejan errores de I/O y usan códigos de salida adecuados ante fallos.

La evaluación prioriza la **corrección y consistencia** de estos patrones, no la cantidad de funcionalidades añadidas.

## Criterio de terminado

La auditoría cubre el repositorio existente en las tres capas; los hallazgos relevantes quedan corregidos; cada estado de error es seguro, comprensible y accionable; los estados de carga siempre terminan; el backend no filtra detalles internos; los scripts comunican el fallo y devuelven un código no cero si es crítico; las pruebas disponibles pasan y el diff no incluye cambios fuera del alcance.

## Entrega

Publicar la rama `feature/error-handling-audit` en GitHub y compartir la URL del PR o del repositorio según las instrucciones de la cohorte. Tras aprobación, hacer merge del PR a `main`.
