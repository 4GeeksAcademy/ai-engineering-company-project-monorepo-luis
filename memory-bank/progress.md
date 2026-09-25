# Progress

Última actualización: 2026-09-25

## Estado inicial observado

- Revisión documental de la etapa 1 completada para `ingenieria-ia.md`, `CONTEXT.md`, `SPEC.md` y README relevantes.
- Existe `uis/website` con landing y formulario; falta verificarla en ejecución contra todos los criterios del hito.
- Existe `uis/talent-pipeline-tracker` con especificación funcional propia.
- Pendientes al iniciar: `uis/backoffice/`, `AGENTS.md` raíz, `.agents/rules/` y `.agents/skills/`.
- `services/` contiene documentación de convenciones, pero no un backend implementado.
- Se ejecutó `git pull` con código de salida 0 según el contexto de la sesión; la rama y el estado actual del working tree no están verificados.

## Trabajo completado

- Inventario documental y mapa inicial de entregables de la etapa 1.
- Creación del banco de memoria: `projectbrief.md`, `techContext.md` y este archivo.

## Decisiones

- `ingenieria-ia.md` define el alcance del hito.
- `CONTEXT.md` es la fuente para negocio y contenido; `SPEC.md` define el comportamiento del tracker.
- Mantener los entregables explícitos `uis/website` y `uis/backoffice`. Las aplicaciones existentes pueden aportar funcionalidad reutilizable, pero no eliminan automáticamente esos requisitos.
- Confirmar con Carmen Ruiz el claim «12 años de experiencia» antes de incluirlo en contenido nuevo.
- No añadir backend hasta justificar su necesidad.
- No incluir secretos ni datos personales reales de candidatos en documentación, mocks o capturas.

## Riesgos y pendientes

- Verificar rama y cambios locales con `git status --short --branch` antes de modificar otros archivos.
- Confirmar durante la implementación que la ruta `/` del sitio público funciona, además de las páginas documentadas en su README.
- Definir el stack, alcance de datos e integración del nuevo backoffice.
- Ejecutar y documentar las validaciones disponibles; no marcar como correcto ningún check que no se haya ejecutado.

## Próximos pasos

1. Crear o actualizar `AGENTS.md` en la raíz con el flujo y límites definidos en `ingenieria-ia.md`.
2. Añadir reglas con alcance declarado en `.agents/rules/` y una skill de objetivo único en `.agents/skills/`.
3. Verificar/completar `uis/website` y crear `uis/backoffice/`.
4. Ejecutar validaciones y actualizar este registro con resultados observados.
