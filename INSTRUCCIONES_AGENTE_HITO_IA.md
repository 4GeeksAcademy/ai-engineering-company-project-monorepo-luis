# Instrucciones para el agente — Hito: Ingeniería impulsada por IA

## 1. Contexto del proyecto

Este documento contiene las instrucciones operativas para trabajar en la entrega de 4Geeks Academy:

- **Cohorte:** Working with AI coding agents
- **Cohorte ID:** `1615`
- **Proyecto:** Hito — Ingeniería impulsada por IA
- **Título en 4Geeks:** `Milestone 4 — AI-driven Engineering`
- **Tarea:** `991590`
- **Slug:** `ai-eng-ai-driven-engineering`
- **Estado actual:** pendiente
- **Repositorio base:** https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo

La entrega debe hacerse sobre un fork o repositorio propio basado en el monorepo de la empresa. No crees un repositorio vacío ni trabajes en un proyecto independiente del monorepo.

La referencia oficial del enunciado es:

- Español: https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-ai-driven-engineering/README.es.md
- Inglés: https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-ai-driven-engineering/README.md
- Plantilla: https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo

---

## 2. Objetivo principal

Preparar el monorepo de la empresa para que sea mantenible y **AI-ready** antes de seguir incorporando funcionalidades.

La entrega debe demostrar que el repositorio tiene:

1. Contexto persistente de negocio y técnico.
2. Reglas claras para cualquier agente de coding.
3. Al menos una skill reutilizable y verificable.
4. Una web corporativa pública alineada con la empresa elegida.
5. Una aplicación interna de backoffice con contenido relevante para esa empresa.
6. Una estructura de monorepo coherente y respetada.

No construyas una solución genérica: todas las decisiones deben estar alineadas con el `CONTEXT.md` real de la empresa asignada.

---

## 3. Primer paso obligatorio: identificar la empresa

Antes de escribir código:

1. Lee el `CONTEXT.md` de la raíz.
2. Comprueba que no sea el placeholder de la plantilla.
3. Identifica la empresa, su dominio, usuarios, procesos, restricciones y hoja de ruta.
4. Si `CONTEXT.md` sigue siendo un placeholder o no permite saber qué empresa se está construyendo, detente y solicita el briefing correcto antes de crear una interfaz específica.
5. No inventes la identidad, los procesos ni los datos de negocio de la empresa.

El banco de memoria, las reglas, la skill, la web pública y el backoffice deben derivarse de ese contexto.

---

## 4. Archivos que debes leer antes de modificar nada

En este orden:

1. `README.md` y `README.es.md` de la raíz.
2. `CONTEXT.md`.
3. El `README.md` de cada carpeta del monorepo que vayas a utilizar.
4. `AGENTS.md`, si ya existe.
5. Las reglas existentes en `.agents/rules/`, si existen.
6. Las skills existentes en `.agents/skills/`, si existen.
7. Los archivos de `memory-bank/`, si existen.
8. El estado actual de Git con `git status`.

No asumas que la documentación describe exactamente el estado actual. Comprueba el código y los archivos existentes antes de editar.

---

## 5. Estructura del monorepo

Respeta la separación de responsabilidades de la plantilla:

```text
CONTEXT.md
AGENTS.md
memory-bank/
.agents/
├── rules/
└── skills/
uis/
├── website/
└── backoffice/
services/
data/
agents/
skills/
mcps/
packages/
shared/
docs/
infra/
scripts/
internal/
```

Reglas de ubicación:

- Todo lo que el usuario ve y usa va en `uis/`.
- Los servicios backend y APIs van en `services/`.
- Los datos, pipelines y conjuntos de evaluación van en `data/`.
- Los agentes de producto van en `agents/`.
- Las capacidades reutilizables de producto van en `skills/`.
- Las reglas para el agente de desarrollo van en `.agents/`, no en `agents/` ni en `skills/`.
- La documentación transversal va en `docs/`.
- No vuelvas a colocar aplicaciones, servicios o documentación específica en la raíz si existe una carpeta adecuada.

Antes de crear una carpeta, lee su `README.md`.

---

## 6. Banco de memoria obligatorio

Crea `memory-bank/` en la raíz con, como mínimo:

```text
memory-bank/
├── projectbrief.md
├── techContext.md
└── progress.md
```

### `projectbrief.md`

Debe documentar, basándose en `CONTEXT.md`:

- qué empresa se está construyendo;
- qué problema resuelve;
- usuarios y actores principales;
- objetivos del producto;
- procesos de negocio relevantes;
- alcance actual y fuera de alcance;
- restricciones funcionales y de negocio.

### `techContext.md`

Debe documentar:

- stack utilizado;
- estructura del monorepo;
- decisiones de arquitectura;
- límites entre website, backoffice y servicios;
- convenciones de configuración;
- estrategia de datos y APIs;
- restricciones técnicas;
- comandos para ejecutar y validar el proyecto.

### `progress.md`

Debe indicar:

- estado inicial observado;
- trabajo completado;
- decisiones tomadas;
- problemas o riesgos conocidos;
- próximos pasos;
- fecha o referencia de la última actualización.

Actualiza `progress.md` cada vez que cambie de forma relevante la arquitectura o el estado del proyecto.

---

## 7. `AGENTS.md` obligatorio

Crea o actualiza `AGENTS.md` en la raíz. Debe indicar claramente:

- qué archivos debe leer el agente al comienzo de cada sesión;
- que debe consultar `CONTEXT.md` y `memory-bank/` antes de implementar;
- el flujo obligatorio antes de cada commit;
- cómo ejecutar las validaciones;
- qué carpetas o archivos no puede modificar sin confirmación explícita;
- cuándo debe detenerse y pedir aclaraciones.

El flujo previo a cada commit debe contener al menos cuatro pasos ordenados. Como mínimo:

1. Revisar el diff y confirmar que los cambios pertenecen a la tarea.
2. Ejecutar los tests o comprobaciones pertinentes.
3. Ejecutar build, lint o typecheck de las aplicaciones afectadas.
4. Actualizar el banco de memoria y la documentación si cambió el comportamiento.
5. Comprobar secretos, archivos generados y configuración sensible.
6. Revisar `git status` y preparar un commit descriptivo.

---

## 8. Reglas en `.agents/`

Crea `.agents/rules/` y documenta al menos una regla con alcance explícito.

Se recomienda crear:

```text
.agents/rules/
├── company-context.md
├── monorepo-architecture.md
├── ui-and-service-conventions.md
└── validation-and-delivery.md
```

Cada regla debe indicar su alcance, por ejemplo:

- **Siempre activa:** aplica a todo el repositorio.
- **Por patrón:** aplica a archivos concretos, como `uis/website/**` o `services/**`.
- **Bajo demanda:** el agente la consulta para una tarea específica.

Las reglas deben ser específicas del contexto de la empresa. No copies instrucciones genéricas sin adaptarlas.

---

## 9. Skill de agente obligatoria

Implementa al menos una skill en:

```text
.agents/skills/<nombre-de-la-skill>/SKILL.md
```

La skill debe capturar una tarea recurrente real del proyecto y tener un único objetivo.

Ejemplos válidos:

- validar una aplicación antes de crear un commit;
- añadir una nueva pantalla de backoffice siguiendo el dominio de la empresa;
- actualizar un dato o flujo de negocio en el servicio central;
- revisar que una feature respeta `CONTEXT.md` y el banco de memoria.

Cada `SKILL.md` debe incluir:

1. Nombre y objetivo único.
2. Cuándo usarla.
3. Inputs necesarios.
4. Archivos que debe inspeccionar.
5. Pasos ordenados.
6. Restricciones y errores comunes.
7. Criterios de aceptación explícitos y verificables.
8. Comandos de validación.
9. Resultado esperado.

No confundas esta carpeta con `skills/` de producto. `.agents/skills/` configura al agente de desarrollo; `skills/` contiene capacidades de la aplicación empresarial.

---

## 10. Aplicación pública: `uis/website`

Crea o completa `uis/website` respetando la estructura de la plantilla.

Requisitos:

- La ruta `/` debe renderizar una web corporativa completa.
- La identidad visual, el texto y las funcionalidades deben derivarse de `CONTEXT.md`.
- Usa componentes reutilizables.
- Mantén una estructura clara de layout, páginas y componentes.
- Incluye estados vacíos o de error cuando corresponda.
- Mantén accesibilidad básica: HTML semántico, labels, foco visible y contraste razonable.
- No uses contenido ficticio que contradiga el briefing de la empresa.
- La aplicación debe arrancar con el comando de desarrollo definido por la plantilla o por su propio README.

La web debe parecer una primera versión real de la empresa, no una pantalla de prueba sin relación con el dominio.

---

## 11. Aplicación interna: `uis/backoffice`

Crea `uis/backoffice` con:

- layout propio;
- ruta `/` accesible;
- estructura visual diferenciada de `uis/website`;
- contenido visible y relevante para la empresa;
- al menos un dato, proceso, indicador o flujo tomado de `CONTEXT.md`;
- estados de carga, vacío y error si consume datos;
- componentes reutilizables y una organización mantenible.

No basta con imprimir información en la consola. El contenido relevante debe aparecer en pantalla.

Si el backoffice usa datos mock, documenta claramente:

- qué representan;
- de dónde salen;
- qué parte es provisional;
- cómo se sustituirían por datos reales.

---

## 12. Servicios y APIs

Cualquier backend debe vivir bajo `/services`, siguiendo las instrucciones de esa carpeta.

Reglas:

- Prioriza un servicio centralizado antes que microservicios innecesarios.
- Define contratos claros para endpoints y modelos.
- Valida entradas y errores de forma legible.
- Mantén separadas rutas, dominio y acceso a datos cuando el tamaño lo justifique.
- Añade tests para lógica y endpoints relevantes.
- No conectes servicios externos ni bases de datos reales sin documentarlo y sin una configuración segura.
- No incluyas claves, tokens, contraseñas ni secretos en el código.

---

## 13. Reglas de implementación

- No sobrescribas cambios existentes sin revisarlos.
- No borres carpetas o archivos de la plantilla sin comprobar sus instrucciones.
- No introduzcas dependencias innecesarias.
- Reutiliza componentes, tipos y utilidades existentes.
- Evita duplicar lógica entre website, backoffice y servicios.
- Mantén la configuración sensible fuera del repositorio.
- Usa nombres consistentes y descriptivos.
- Documenta decisiones no obvias en `memory-bank/` o `docs/`.
- Si el contexto de negocio contradice una idea de implementación, prevalece `CONTEXT.md`.
- Si falta información necesaria para una decisión de negocio, detente y pregunta; no inventes.

---

## 14. Validación obligatoria

Antes de terminar, ejecuta las validaciones disponibles para cada aplicación modificada:

1. Instalación o comprobación de dependencias.
2. Tests unitarios y de integración.
3. Lint.
4. Typecheck.
5. Build de producción.
6. Arranque local de las aplicaciones.
7. Comprobación manual de:
   - `uis/website` en `/`;
   - `uis/backoffice` en `/`;
   - contenido alineado con `CONTEXT.md`;
   - ausencia de errores visibles en consola.

Si una validación no puede ejecutarse, explica el motivo exacto. No la marques como correcta por suposición.

---

## 15. Entrega en Git

La rama de trabajo debe llamarse:

```text
feature/agent-memory-bank
```

Antes del commit final:

1. Ejecuta el flujo definido en `AGENTS.md`.
2. Revisa `git diff` y `git status`.
3. Comprueba que no haya secretos ni archivos generados innecesarios.
4. Confirma que el banco de memoria está actualizado.
5. Crea un commit descriptivo.
6. Abre una Pull Request contra `main` de tu fork.

La descripción de la Pull Request debe incluir:

- resumen de cambios;
- empresa y contexto utilizado;
- captura de `uis/website` funcionando;
- captura de `uis/backoffice` con contenido relevante visible;
- enlace directo a `AGENTS.md`;
- validaciones ejecutadas y sus resultados;
- limitaciones o tareas pendientes.

No entregues solo archivos de configuración sin demostrar que las dos interfaces funcionan.

---

## 16. Informe final del agente

Al finalizar, responde con:

1. Empresa y contexto utilizado.
2. Archivos creados o modificados.
3. Banco de memoria creado o actualizado.
4. Reglas añadidas en `.agents/rules/`.
5. Skills añadidas en `.agents/skills/`.
6. Estado de `uis/website` y `uis/backoffice`.
7. Servicios creados o modificados.
8. Validaciones ejecutadas y resultado de cada una.
9. Rama, commit y Pull Request.
10. Bloqueos o decisiones pendientes.

No afirmes que el proyecto está terminado si falta la web pública, el backoffice, el contexto de empresa o alguna validación crítica.
