# Progress

Última actualización: 2026-09-25

## Estado inicial observado

- Revisión documental de la etapa 1 completada para `ingenieria-ia.md`, `CONTEXT.md`, `SPEC.md` y README relevantes.
- Existe `uis/website` con landing y formulario; las rutas `/` y `/application` y sus recursos principales ya pasaron smoke test HTTP.
- Existe `uis/talent-pipeline-tracker` con especificación funcional propia.
- Pendiente: crear `uis/backoffice/`.
- `services/` contiene documentación de convenciones, pero no un backend implementado.
- Se ejecutó `git pull` con código de salida 0 según el contexto de la sesión; la rama y el estado actual del working tree no están verificados.

## Trabajo completado

- Inventario documental y mapa inicial de entregables de la etapa 1.
- Creación del banco de memoria: `projectbrief.md`, `techContext.md` y este archivo.
- Etapa 3: creado `AGENTS.md` raíz, reglas de contexto y arquitectura en `.agents/rules/`, y skill de validación en `.agents/skills/validate-application-before-commit/`.
- Commits publicados en `feature/agent-memory-bank`: banco de memoria (`9a5ac91`) y etapa 3 (`c52222b`).
- Etapa 4: añadido header/footer web reutilizable, navegación adaptable a móvil y límite HTML de 500 caracteres en comentarios.
- Corregido el comando de servidor: sin `-s`, el formulario se sirve en `/application`; el modo SPA redirigía a la landing.
- Corregidos los globs de Tailwind para que, ejecutado desde la raíz como indica el README, genere las utilidades del sitio y del componente compartido.

## Decisiones

- `ingenieria-ia.md` define el alcance del hito.
- `CONTEXT.md` es la fuente para negocio y contenido; `SPEC.md` define el comportamiento del tracker.
- Mantener los entregables explícitos `uis/website` y `uis/backoffice`. Las aplicaciones existentes pueden aportar funcionalidad reutilizable, pero no eliminan automáticamente esos requisitos.
- Confirmar con Carmen Ruiz el claim «12 años de experiencia» antes de incluirlo en contenido nuevo.
- No añadir backend hasta justificar su necesidad.
- No incluir secretos ni datos personales reales de candidatos en documentación, mocks o capturas.

## Riesgos y pendientes

- Rama actual `feature/agent-memory-bank`; los cambios de etapa 4 están locales y sin commit.
- Permanece una eliminación local preexistente de `INSTRUCCIONES_AGENTE_HITO_IA.md`; no se incluyó en el commit y no debe descartarse sin autorización.
- No se pudo inspeccionar `uis/website/assets/js/validation.js` porque Copilot lo marca como ignorado; tampoco había navegador instalado para interacción o revisión visual. Las validaciones del formulario quedan pendientes de prueba en navegador.
- Tailwind avisa que `caniuse-lite` está desactualizado; la compilación termina correctamente.
- Definir el stack, alcance de datos e integración del nuevo backoffice.

## Próximos pasos

1. Crear `uis/backoffice/` y documentar su stack/comandos.
2. Ejecutar validaciones de ambas aplicaciones e interactuar con el formulario cuando haya navegador disponible.
3. Actualizar este registro con los resultados observados.
