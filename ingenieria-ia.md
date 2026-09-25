# Ingeniería impulsada por IA — Guía de ejecución y auditoría

> Documento preparado a partir de la tarea **Milestone 4 — AI-driven Engineering** de 4Geeks Academy, cohorte **Working with AI coding agents**.
>
> **Auditoría realizada:** 23 de septiembre de 2026.

## 1. Identificación de la tarea

- **Cohorte:** Working with AI coding agents
- **Cohorte ID:** `1615`
- **Tarea:** Milestone 4 — AI-driven Engineering
- **Tarea ID:** `991590`
- **Estado en 4Geeks:** `PENDING`
- **Slug:** `ai-eng-ai-driven-engineering`
- **Repositorio base:** [ai-engineering-company-project-monorepo](https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo)
- **README oficial en español:** [README.es.md](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-ai-driven-engineering/README.es.md)
- **README oficial en inglés:** [README.md](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-ai-driven-engineering/README.md)

## 2. Objetivo del hito

Preparar el monorepo de la empresa para que sea **coherente, mantenible y AI-ready** antes de continuar incorporando funcionalidades.

El repositorio debe demostrar que cuenta con:

1. Contexto de negocio y técnico persistente.
2. Reglas claras para cualquier agente de coding.
3. Al menos una skill reutilizable, con criterios verificables.
4. Una web corporativa pública alineada con la empresa.
5. Una aplicación interna de backoffice con contenido relevante para la empresa.
6. Una estructura de monorepo respetada, sin duplicación innecesaria.

### Restricción principal

El trabajo debe hacerse sobre un fork o copia propia del monorepo oficial. **No se debe crear un repositorio vacío ni un proyecto independiente.**

Repositorio local auditado:

```text
ai-engineering-company-project-monorepo-luis/
```

## 3. Contexto de negocio auditado

El `CONTEXT.md` existente describe a **Nexova**, una consultora de recursos humanos y adquisición de talento fundada en 2011, con sede en Valencia y expansión en Miami.

Sus líneas de negocio son:

- Headhunting ejecutivo y de mandos medios.
- Outsourcing de equipos de atención al cliente para empresas tecnológicas.
- Formación corporativa en soft skills y liderazgo.

El problema de negocio indicado es la modernización del sitio web corporativo y la captura estructurada de candidatos, sustituyendo el flujo desordenado de CVs enviados por email.

### Stakeholder

- **Carmen Ruiz**, Head of Marketing.

### Implicación para este hito

Toda la infraestructura de agentes, la web pública y el backoffice deben derivarse de este contexto. No se debe inventar otra empresa, identidad, proceso o conjunto de datos.

## 4. Auditoría del estado actual

### Hallazgos confirmados

- El repositorio local está limpio en la rama `main`.
- El README de la plantilla está disponible en español e inglés.
- La plantilla define claramente la separación entre `uis/`, `services/`, `data/`, `agents/`, `skills/`, `mcps/`, `workflows/`, `packages/`, `shared/`, `docs/`, `infra/`, `scripts/` e `internal/`.
- El `CONTEXT.md` existe y contiene información concreta de Nexova.
- El contexto actualmente está titulado **“Hito 1: Sitio Web Público de tu Empresa”**, aunque este trabajo corresponde al Hito 4. Hay que conservarlo como fuente de negocio, pero completar el contexto técnico del nuevo hito en `memory-bank/techContext.md`.
- La tarea de 4Geeks no incluye una descripción adicional en la respuesta de la API; el alcance se obtiene del README oficial del syllabus.

### Riesgo que debe corregirse antes de implementar

El README oficial exige que el `CONTEXT.md` sea el briefing de la empresa asignada y no el placeholder de la plantilla. Hay que verificar que el documento de Nexova sea efectivamente el briefing vigente y que no sea necesario sustituirlo por una versión más completa de `00-general-contexts`.

Si no se puede confirmar la empresa asignada o el contexto contiene contradicciones, hay que detener la implementación específica y pedir el briefing correcto. No se deben crear interfaces genéricas para cubrir la duda.

## 5. Qué debes hacer

## 5.1 Crear el banco de memoria

Crear en la raíz del monorepo:

```text
memory-bank/
├── projectbrief.md
├── techContext.md
└── progress.md
```

### `memory-bank/projectbrief.md`

Debe documentar, basándose en `CONTEXT.md`:

- Qué empresa se está construyendo.
- Qué problema de negocio resuelve.
- Usuarios y actores principales.
- Objetivos del producto.
- Procesos de negocio relevantes.
- Alcance actual y funcionalidades fuera de alcance.
- Restricciones funcionales y de negocio.

### `memory-bank/techContext.md`

Debe documentar:

- Stack tecnológico utilizado.
- Estructura del monorepo.
- Decisiones de arquitectura.
- Separación entre website, backoffice y servicios.
- Convenciones de configuración.
- Estrategia de datos y APIs.
- Restricciones técnicas.
- Comandos para ejecutar y validar cada aplicación.

### `memory-bank/progress.md`

Debe registrar:

- Estado inicial observado.
- Trabajo completado.
- Decisiones tomadas.
- Problemas y riesgos conocidos.
- Próximos pasos.
- Fecha o referencia de la última actualización.

Actualizarlo cada vez que cambie de forma relevante la arquitectura o el estado del proyecto.

## 5.2 Crear `AGENTS.md`

Crear o actualizar `AGENTS.md` en la raíz del monorepo. Debe especificar:

- Qué archivos debe leer el agente al comenzar cada sesión.
- Que debe consultar `CONTEXT.md` y `memory-bank/` antes de implementar.
- El flujo obligatorio antes de cada commit.
- Cómo ejecutar las validaciones.
- Qué carpetas o archivos no puede modificar sin confirmación explícita.
- Cuándo debe detenerse y pedir aclaraciones.

El flujo previo a cada commit debe tener al menos cuatro pasos ordenados y explícitos. Se recomienda incluir todos estos:

1. Revisar el diff y confirmar que los cambios pertenecen a la tarea.
2. Ejecutar tests y comprobaciones pertinentes.
3. Ejecutar lint, typecheck o build de las aplicaciones afectadas.
4. Actualizar el banco de memoria y la documentación si cambió el comportamiento.
5. Revisar secretos, archivos generados y configuración sensible.
6. Revisar `git status` y preparar un commit descriptivo.

## 5.3 Crear reglas en `.agents/`

Crear al menos una regla en `.agents/rules/` y declarar explícitamente su alcance:

- **Siempre activa:** aplica a todo el repositorio.
- **Por patrón:** aplica a rutas concretas, por ejemplo `uis/website/**` o `services/**`.
- **Bajo demanda:** el agente la consulta para una tarea específica.

Las reglas deben adaptarse a Nexova y a la arquitectura real. No deben ser instrucciones genéricas copiadas sin contexto.

Se recomienda crear:

```text
.agents/rules/
├── company-context.md
├── monorepo-architecture.md
├── ui-and-service-conventions.md
└── validation-and-delivery.md
```

## 5.4 Implementar al menos una skill de agente

Crear una skill en:

```text
.agents/skills/<nombre-de-la-skill>/SKILL.md
```

La skill debe representar una tarea recurrente real del proyecto y tener **un único objetivo**.

Debe incluir como mínimo:

1. Nombre y objetivo único.
2. Cuándo utilizarla.
3. Inputs necesarios.
4. Archivos que debe inspeccionar.
5. Pasos ordenados.
6. Restricciones y errores comunes.
7. Criterios de aceptación explícitos y verificables.
8. Comandos de validación.
9. Resultado esperado.

Ejemplos de objetivos válidos:

- Validar una aplicación antes de crear un commit.
- Añadir una pantalla de backoffice alineada con el dominio de Nexova.
- Revisar que una feature respeta `CONTEXT.md` y el banco de memoria.

No confundir esta ubicación con `skills/` del producto. `.agents/skills/` configura el agente de desarrollo; `skills/` contiene capacidades de producto para módulos posteriores.

## 5.5 Inicializar la aplicación pública

Crear o completar `uis/website` respetando la estructura y el README de la plantilla.

Requisitos mínimos:

- La ruta `/` debe renderizar una web corporativa completa.
- El contenido debe estar alineado con Nexova y `CONTEXT.md`.
- Debe utilizar componentes reutilizables.
- La identidad visual y los textos deben ser coherentes con la empresa.
- Debe incluir estados vacíos o de error cuando corresponda.
- Debe mantener accesibilidad básica: HTML semántico, labels, foco visible y contraste razonable.
- Debe arrancar con el comando de desarrollo documentado.

La web no puede ser una pantalla de prueba genérica.

## 5.6 Inicializar la aplicación interna

Crear `uis/backoffice` con:

- Layout propio.
- Ruta `/` accesible.
- Estructura visual diferenciada del website.
- Contenido visible y relevante para Nexova.
- Al menos un dato, proceso, indicador o flujo tomado de `CONTEXT.md` visible en pantalla.
- Estados de carga, vacío y error si consume datos.
- Componentes reutilizables y organización mantenible.

Si se utilizan datos mock, documentar:

- Qué representan.
- De dónde salen.
- Qué parte es provisional.
- Cómo se sustituirían por datos reales.

No basta con imprimir la información en consola.

## 5.7 Servicios y APIs

Cualquier backend debe vivir bajo `/services` y seguir el README de esa carpeta.

Reglas:

- Priorizar un servicio centralizado antes que microservicios innecesarios.
- Definir contratos claros para endpoints y modelos.
- Validar entradas y errores de forma legible.
- Separar rutas, dominio y acceso a datos cuando el tamaño lo justifique.
- Añadir tests para lógica y endpoints relevantes.
- No conectar servicios externos o bases de datos reales sin documentarlo y sin configuración segura.
- No incluir claves, tokens, contraseñas ni secretos en el código.

## 5.8 Mantener la arquitectura del monorepo

Usar estas ubicaciones como guía:

| Tipo de trabajo | Ubicación |
|---|---|
| Interfaces y aplicaciones visibles | `uis/` |
| APIs y servicios backend | `services/` |
| Datos, pipelines y evaluación | `data/` |
| Agentes de producto | `agents/` |
| Capacidades reutilizables de producto | `skills/` |
| Servidores MCP | `mcps/` |
| Automatizaciones | `workflows/` |
| Código compartido versionable | `packages/` |
| Esquemas, plantillas y assets compartidos | `shared/` |
| Documentación transversal | `docs/` |
| Infraestructura y despliegue | `infra/` |
| Scripts puntuales | `scripts/` |
| Herramientas internas estructuradas | `internal/` |

Antes de crear una carpeta nueva, leer el `README.md` de esa carpeta.

## 6. Qué vamos a evaluar

La entrega debe cumplir todos estos criterios:

### Infraestructura de agentes

- [ ] El banco de memoria contiene contexto de negocio **y** contexto técnico.
- [ ] Existe `memory-bank/projectbrief.md` con el negocio, objetivos y problema.
- [ ] Existe `memory-bank/techContext.md` con stack, arquitectura y restricciones.
- [ ] Existe `memory-bank/progress.md` con estado y próximos pasos.
- [ ] `AGENTS.md` indica qué leer al inicio de cada sesión.
- [ ] `AGENTS.md` contiene un flujo previo al commit con al menos cuatro pasos ordenados.
- [ ] `AGENTS.md` especifica qué archivos o carpetas requieren confirmación antes de modificarse.
- [ ] `.agents/` contiene al menos una regla con alcance explícito.
- [ ] La skill tiene un objetivo único.
- [ ] La skill documenta sus inputs.
- [ ] La skill tiene criterios de aceptación verificables.

### Aplicaciones

- [ ] `uis/website` existe y arranca sin errores con su comando de desarrollo.
- [ ] `uis/website` expone una ruta `/` funcional.
- [ ] La ruta `/` muestra una web corporativa completa.
- [ ] La web pública está alineada con `CONTEXT.md` de Nexova.
- [ ] La web usa componentes reutilizables y estilos coherentes.
- [ ] `uis/backoffice` existe.
- [ ] `uis/backoffice` tiene un layout propio, separado del website.
- [ ] `uis/backoffice` expone una ruta `/` funcional.
- [ ] El backoffice muestra en pantalla contenido relevante de Nexova.
- [ ] Las aplicaciones no dependen de contenido ficticio que contradiga el briefing.

### Arquitectura y calidad

- [ ] El código respeta las convenciones de carpetas del monorepo.
- [ ] No hay duplicación innecesaria entre website, backoffice y servicios.
- [ ] Los servicios backend, si existen, están bajo `/services`.
- [ ] No hay secretos en el repositorio.
- [ ] Las validaciones disponibles se han ejecutado y documentado.

## 7. Validación obligatoria antes de terminar

Para cada aplicación modificada, ejecutar las validaciones disponibles:

1. Instalar o comprobar dependencias.
2. Ejecutar tests unitarios y de integración.
3. Ejecutar lint.
4. Ejecutar typecheck.
5. Ejecutar build de producción.
6. Arrancar localmente la aplicación.
7. Comprobar manualmente `/` en `uis/website`.
8. Comprobar manualmente `/` en `uis/backoffice`.
9. Confirmar que el contenido está alineado con `CONTEXT.md`.
10. Confirmar que no hay errores visibles en consola.

Si una validación no puede ejecutarse, documentar el motivo exacto. No marcarla como correcta por suposición.

## 8. Entrega en Git

La rama final debe llamarse:

```text
feature/agent-memory-bank
```

Antes del commit final:

1. Ejecutar el flujo definido en `AGENTS.md`.
2. Revisar `git diff` y `git status`.
3. Comprobar que no hay secretos ni archivos generados innecesarios.
4. Confirmar que `memory-bank/` está actualizado.
5. Crear un commit descriptivo.
6. Abrir una Pull Request hacia `main` del fork.

La descripción de la Pull Request debe incluir:

- Resumen de cambios.
- Empresa y contexto utilizado.
- Captura de la web pública funcionando.
- Captura del backoffice con contenido relevante visible.
- Enlace directo a `AGENTS.md`.
- Validaciones ejecutadas y sus resultados.
- Limitaciones o tareas pendientes.

Finalmente, entregar el enlace de la Pull Request en el campus de 4Geeks.

## 9. Informe final que debe poder producir el agente

Al finalizar, el informe debe incluir:

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

No declarar el proyecto terminado si falta la web pública, el backoffice, el contexto de empresa o una validación crítica.

## 10. Fuentes auditadas

- README oficial del hito en español: `ai-eng-milestone-ai-driven-engineering/README.es.md`, consultado desde el repositorio oficial de `4GeeksAcademy/ai-engineering-syllabus`.
- README oficial del hito en inglés: `ai-eng-milestone-ai-driven-engineering/README.md`.
- README de la plantilla local: `ai-engineering-company-project-monorepo-luis/README.es.md`.
- Contexto local de empresa: `ai-engineering-company-project-monorepo-luis/CONTEXT.md`.
- Registro de tarea de 4Geeks: cohorte `1615`, tarea `991590`.
