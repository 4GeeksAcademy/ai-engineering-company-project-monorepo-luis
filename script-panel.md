# Nexova — Analizador de incidencias: guía de implementación

Guía de trabajo para implementar el proyecto **Analizador de incidencias — Script y Panel de Control** en este monorepo. Está basada en el enunciado oficial de 4Geeks y en el contexto oficial de incidentes de Nexova. Sirve como plan de implementación y checklist de aceptación; no reemplaza `CONTEXT.md` ni autoriza a inventar campos o valores.

## Fuentes y alcance confirmado

- Enunciado oficial (español): [README.es.md — Analizador de Incidencias](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-company-incidents-file-analyzer/README.es.md)
- Enunciado oficial (inglés): [README.md — Incident Analyzer](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-company-incidents-file-analyzer/README.md)
- Contexto oficial de Nexova: [CONTEXT-nexova.es.md](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/incidents-file-analysis/CONTEXT-nexova.es.md)
- CSV de ejemplo oficial: [incidents-nexova.csv](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/incidents-file-analysis/incidents-nexova.csv)
- Cohorte verificada en la cuenta 4Geeks: **Backend development with Coding Agents**, cohorte/micro-cohorte ID `1670`, slug `spain-backend-development-with-coding-agents` (dentro de `spain-aie-pt-4`, ID `1727`).
- Tarea verificada en la cuenta: **Company Incident File Analyzer**, tipo `PROJECT`, ID `1000185`, estado `PENDING`, `associated_slug=ai-eng-company-incidents-analysis`.
- El detalle de la tarea en la API no incluye el README (descripción vacía); se auditó el README oficial del syllabus enlazado arriba y su contexto Nexova asociado. La API confirmó que la tarea pendiente pertenece a la cohorte solicitada.

Este proyecto se implementa en el monorepo de Nexova existente. No crear un repositorio nuevo ni reemplazar el contexto general de la empresa. Antes de tocar código, leer `CONTEXT.md` y los README de las carpetas afectadas. El `CONTEXT.md` presente ahora mismo en el checkout describe el hito del sitio web y no es el contexto de incidentes: incorporar el contexto correcto en su ubicación/proceso acordado o consultar la fuente oficial enlazada, sin sobrescribirlo a ciegas.

## Auditoría del enunciado: discrepancia importante

El README del proyecto especifica un CSV de **100 registros** y sus criterios de evaluación también hablan de un CSV de 100 filas. El contexto de Nexova contiene una frase que dice que el archivo de prueba tiene **1.000 filas**, pero más adelante indica **100 filas**, y sus resultados esperados suman 96 registros válidos + 4 inválidos = 100. El propio nombre y distribución del fixture también corresponden a la muestra de 100 registros.

**Criterio de implementación:** usar el fixture y las cifras esperadas expresas de 100 registros (96 válidos, 4 inválidos) como baseline. No alterar las cifras para forzar el número 1.000. Señalar la discrepancia en la documentación/PR y, si 4Geeks entrega un fixture distinto, recalcular y actualizar expectativas con evidencia antes de cambiar el contrato.

El README habla en general de 100 registros y el CONTEXT aporta los nombres concretos, las reglas, categorías y cifras que mandan para Nexova. No usar datos de ejemplo de otra compañía.

## Contexto del dominio y datos

Nexova presta outsourcing de soporte al cliente. El objetivo es analizar internamente exportaciones CSV del helpdesk para que el equipo de soporte entienda el volumen y la satisfacción sin exponer datos personales a servicios externos.

- Archivo de ejemplo: `incidents-nexova.csv` (el README lo llama también `incidents-COMPANY.csv` como marcador genérico).
- Codificación: UTF-8; separador coma; primera fila de encabezado.
- Campos exactos:
  - `ticket_id`: requerido, formato `NXV-XXXXXX`.
  - `date`: requerido, formato `YYYY-MM-DD`.
  - `client_company`: requerido, texto no vacío.
  - `category`: requerido, solo `TECHNICAL`, `BILLING`, `ACCESS`, `HR_QUERY`, `COMPLAINT`.
  - `description`: requerido, mínimo 5 caracteres.
  - `agent_id`: requerido, formato `AGT-XX`.
  - `status`: requerido, solo `OPEN`, `CLOSED`, `DISCARDED`.
  - `customer_email`: requerido y validado al menos por presencia de `@`; es dato sensible.
  - `satisfaction_score`: opcional salvo cuando `status=CLOSED`, donde es obligatorio; si existe, entero entre 1 y 5 inclusive.
- Categorías, estados y valores deben mantenerse exactamente en mayúsculas como arriba. No traducirlos en datos, API o CSV; se pueden presentar etiquetas explicativas en la UI.

### Privacidad obligatoria

`customer_email` contiene información sensible. Nunca imprimir, registrar en logs, devolver en JSON de errores, mostrar en UI ni incluir en CSV de resultados direcciones individuales. Los errores de validación deben indicar el número de fila y una categoría genérica del problema, nunca repetir el valor de la celda. No mandar el CSV a servicios de IA, APIs externas, analítica, telemetría de terceros ni herramientas de diagnóstico. Evitar guardar copias temporales; si son imprescindibles, limitar permisos, duración y acceso, y borrarlas de forma segura al terminar el proceso.

## Fase 1 — Script CLI (primero)

Implementar `scripts/analyze.py` como interfaz de línea de comandos que acepte la ruta del CSV, por ejemplo:

```bash
python scripts/analyze.py data/raw/incidents-nexova.csv
```

La ubicación final del fixture debe respetar la organización documentada del monorepo y el README del proyecto pide `scripts/` para `analyze.py` y el CSV de prueba. Evitar duplicar datasets sensibles en varios sitios. Si el repo ya establece una carpeta canónica de datos, documentar el path y actualizar el ejemplo de ejecución de manera consistente.

Requisitos del CLI:

1. Recibir la ruta como argumento, comprobar que existe y se puede leer; no codificar una ruta fija.
2. Leer CSV UTF-8 con encabezado, manejar líneas CRLF y rechazar archivo vacío, encabezados ausentes/duplicados o columnas requeridas faltantes con un mensaje claro y salida no exitosa.
3. No abortar todo el análisis ante una fila inválida. Analizar todas las filas de datos, clasificar problemas, contar registros y excluir inválidos de las métricas principales.
4. Mostrar un resumen legible con separadores y cantidades. Incluir registros totales, válidos, inválidos, desglose de errores, categoría, estado y satisfacción cerrada.
5. Al final preguntar exactamente `Export results to CSV? [y / n]` (la versión inglesa del README define esta cadena). Aceptar una respuesta afirmativa; ante `n`, terminar sin crear archivo. Si stdin no está disponible, informar cómo ejecutar en modo interactivo o proporcionar una opción CLI explícita sin cambiar el comportamiento por defecto.
6. Si se acepta, crear `results.csv` con **una fila por métrica/valor de resumen**, encabezados claros y estructura estable. No incluir emails ni contenido de las filas fuente. No sobrescribir silenciosamente un resultado existente sin advertencia.
7. Devolver código de salida distinto de cero ante errores de archivo/formato/ejecución; filas inválidas no impiden completar el análisis.

### Reglas de validez del contexto Nexova

El CONTEXT enumera estas reglas de invalidación y espera conteo por tipo:

- `client_company` vacío.
- `category` vacía o fuera del conjunto permitido.
- `description` vacía o de menos de 5 caracteres.
- `agent_id` vacío o que no cumpla `AGT-XX`.
- `customer_email` vacío o que no contenga `@` (sin mostrarlo nunca).
- Estado `CLOSED` sin `satisfaction_score`.
- `satisfaction_score` presente pero no entero o fuera de 1–5.

El CSV schema también marca `ticket_id`, `date` y `status` como requeridos y describe formatos/valores. Validar esos campos/valores para proteger las métricas y documentar errores de formato en el desglose, pero no inventar reglas que contradigan el contexto. Toda fila con uno o más errores cuenta **una sola vez** como inválida; el desglose por tipo puede contar cada regla activada, por lo que sus cantidades no necesariamente suman el total de filas inválidas. Evitar exponer el contenido de una fila inválida.

Calcular las métricas sobre **filas válidas únicamente**:

- Total de filas leídas, válidas e inválidas.
- Conteo por cada categoría válida, incluso si el conteo fuera cero.
- Conteo por cada estado válido.
- Promedio de `satisfaction_score` de tickets válidos con estado `CLOSED` y puntuación presente. Contar también cuántos tickets cerrados tienen puntuación frente al total cerrado válido. Redondear a 2 decimales para presentación/exportación; usar precisión numérica sin redondeo intermedio.
- Si no hay puntuaciones, representar el promedio como `N/A`/null, no como cero.

### Valores de aceptación del fixture Nexova (100 filas)

Estos valores deben coincidir con el contexto oficial:

- Filas totales: **100**; válidas: **96**; inválidas: **4**.
- Categorías válidas: `TECHNICAL=28`, `BILLING=18`, `ACCESS=21`, `HR_QUERY=17`, `COMPLAINT=12`.
- Estados válidos: `OPEN=27`, `CLOSED=56`, `DISCARDED=13`.
- Problemas inválidos esperados: `client_company` ausente = 1; categoría ausente/inválida = 1; email ausente/inválido = 1; `CLOSED` sin puntuación = 1.
- Puntuaciones de casos cerrados: 1=2, 2=5, 3=10, 4=22, 5=17; promedio **3.84/5.00** (215/56 antes de redondear).

No mostrar porcentajes como sustituto de los conteos; se pueden añadir como información secundaria. Si se muestran porcentajes, documentar el denominador (96 válidos) y redondeo. Las cifras anteriores deben probarse con el fixture sin imprimir datos personales.

## Diseño compartido: una lógica, dos consumidores

El README exige que script y API ejecuten la misma validación/análisis y que la lógica se extraiga a funciones o módulos compartidos. No implementar dos analizadores separados.

- Extraer lectura, validación, clasificación y agregación a funciones reutilizables en una librería interna apropiada del monorepo (preferir `packages/` o módulo compartido que siga la convención existente).
- Mantener `scripts/analyze.py` como wrapper delgado: argumentos/entrada interactiva, llamada al servicio compartido y presentación CLI.
- Hacer que el backend invoque el mismo servicio. Definir un resultado tipado/serializable que preserve conteos, errores agregados y `null` cuando no hay promedio.
- El analizador debe ser determinista y no depender del estado global, filesystem oculto ni red.
- Tener cuidado con el tamaño de producción potencialmente alto (el README menciona que podría llegar al millón de líneas): procesar en streaming/lotes cuando sea razonable y evitar cargar/copiar todo en memoria sin necesidad. El fixture pequeño sigue siendo la prueba base.

## Fase 2 — API del backoffice

Implementar dentro de `services/api` de acuerdo con el FastAPI centralizado descrito por este monorepo. Revisar primero el estado real de la carpeta y su documentación: puede que el endpoint deba incorporarse al servicio central, no crear otro microservicio.

### `POST /api/incidents/analyze`

- Aceptar CSV como `multipart/form-data`.
- Validar archivo vacío, extensión/tipo y encabezados; no confiar solo en el MIME type del navegador.
- Invocar la lógica compartida y devolver JSON con total/valid/invalid, errores agregados, conteos por categoría/estado, datos de satisfacción y average redondeado/null.
- No incluir filas originales, emails, descripciones, nombres de compañías ni detalles que identifiquen clientes.
- Devolver errores descriptivos sin PII y códigos HTTP apropiados (p. ej. 400 para archivo/formato inválido, 413 para tamaño excedido); capturar fallos sin filtrar stack traces al cliente.
- Establecer límites de tamaño/tiempo razonables y no guardar el archivo permanentemente.

### `GET /api/incidents/results/export`

- Descargar el CSV del **último análisis** según el alcance de sesión/usuario que use la plataforma; no compartir resultados de un usuario con otro.
- Si aún no hay análisis, responder con error HTTP apropiado y mensaje claro.
- Devolver `text/csv` y `Content-Disposition` de descarga.
- Exportar solo filas de métricas agregadas: nunca registros originales, emails u otra PII.
- Utilizar el mismo esquema generado por la opción de exportación del script, en la medida compatible con la API.

## Fase 3 — Panel web

Construir en `uis/backoffice` una página enlazada desde la navegación/menu existente. Seguir el stack, diseño y convenciones realmente presentes; no introducir un framework alternativo sin necesidad.

La interfaz debe permitir:

- Elegir o arrastrar un `.csv`, indicar qué formato se espera y lanzar el análisis contra el backend.
- Mostrar estados de carga, éxito y error; rechazar archivos vacíos/no CSV con mensajes entendibles.
- Mostrar total, válidos e inválidos; tabla/gráfico o lista accesible de categorías y estados; promedio y cantidad de puntuaciones de satisfacción.
- Mostrar el desglose de filas inválidas por tipo, sin valores de celdas ni PII.
- Descargar los resultados agregados del endpoint de exportación.
- Funcionar en móvil/desktop, con labels, foco visible, navegación por teclado, contraste y mensajes accesibles (`aria-live` donde corresponda). No representar datos solo por color.
- No enviar el archivo a un servicio externo, almacenar su contenido en localStorage ni incluirlo en telemetría.

## Pruebas y verificación exigidas

Añadir pruebas automatizadas para la lógica compartida, script, endpoints y, si el entorno lo permite, interacción principal de UI. Cubrir como mínimo:

1. Fixture Nexova oficial: exactitud de todos los totales/categorías/estados/errores/puntuaciones/promedio.
2. CSV válido pequeño, archivo vacío, encabezado faltante, columna faltante, columna extra y fila mal formada.
3. Cada regla de inválido individualmente y una fila que active varias reglas (inválidos únicos frente a incidencias múltiples).
4. Puntaje `0`, `6`, decimal/texto, `CLOSED` sin score y score vacío en `OPEN`/`DISCARDED`.
5. CSV con caracteres acentuados, comillas, comas dentro de texto, CRLF y líneas en blanco.
6. Promedio sin tickets cerrados puntuados; no debe dividir por cero.
7. Exportación de script/API: columnas y filas de métricas válidas; asegurar con una prueba que ningún email o texto de la fuente aparece en la salida, logs o errores.
8. API: formato multipart correcto, casos de error y descarga CSV con headers apropiados.
9. Frontend: selección/carga de archivo, presentación del resumen, errores, invalid count y descarga.

Antes de dar por listo:

- Ejecutar pruebas y comandos de lint/build disponibles en los proyectos realmente tocados.
- Ejecutar el script con el fixture Nexova y comparar automáticamente los valores esperados; no copiar/pegar PII en logs ni capturas.
- Ejecutar `git diff --check`, revisar el diff y confirmar que no se añadieron credenciales, datos personales reales ni artefactos generados.
- Documentar comandos de ejecución y pruebas en los README de `scripts/`, API y backoffice conforme a las convenciones del monorepo.

## Entrega

El enunciado oficial pide organizar la solución dentro del monorepo con:

```text
scripts/
  analyze.py
  incidents-nexova.csv (fixture de prueba, en ubicación acordada y sin duplicados)
services/
  api/ (endpoints de análisis y exportación dentro de la API del monorepo)
uis/
  backoffice/ (página de carga y resultados)
```

Subir la rama de trabajo y abrir Pull Request según el flujo solicitado por el curso. El PR debe incluir:

- Captura del resumen CLI generado con el fixture de 100 filas.
- Captura del panel con un análisis visible.
- Instrucciones para ejecutar pruebas y servicios.
- Una nota sobre la discrepancia 100/1.000 filas descrita arriba.

Las capturas no deben revelar emails, datos de clientes ni archivos fuente. Este documento solo define lo necesario para el agente; no ejecutar cambios funcionales de backend/frontend como parte de escribir estas instrucciones.
