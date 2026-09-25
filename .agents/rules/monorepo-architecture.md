# Arquitectura del monorepo

**Alcance:** Por patrón: `uis/**`, `services/**`, `agents/**`, `skills/**`, `packages/**` y `.agents/**`.

## Reglas

- Mantener las aplicaciones visibles bajo `uis/`, APIs y workers bajo `services/`, agentes de producto bajo `agents/` y capacidades de producto bajo `skills/`.
- La configuración para agentes de desarrollo va en `.agents/`; no confundirla con agentes o skills de producto.
- Mantener el sitio público en `uis/website` y crear el backoffice solicitado en `uis/backoffice`. No asumir que `uis/talent-pipeline-tracker` satisface por sí solo el entregable de backoffice.
- Reutilizar componentes, contratos y datos existentes cuando sea adecuado; evitar duplicar gestión detallada de candidatos entre el tracker y el backoffice.
- Antes de añadir una aplicación, servicio o subcarpeta, leer su README y documentar propósito, stack y forma de ejecución.
- No añadir backend ni microservicios por defecto. Si se necesita lógica de servidor, usar `services/` y seguir su README.
- No mover ni borrar proyectos existentes para resolver una diferencia de arquitectura sin confirmación explícita.
