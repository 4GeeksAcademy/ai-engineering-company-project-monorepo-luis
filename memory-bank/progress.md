# Progress

Última actualización: 2026-09-25

## Estado inicial observado

- Revisión documental de la etapa 1 completada para `ingenieria-ia.md`, `CONTEXT.md`, `SPEC.md` y README relevantes.
- Existe `uis/website` con landing y formulario; las rutas `/` y `/application` y sus recursos principales ya pasaron smoke test HTTP.
- Existe `uis/talent-pipeline-tracker` con especificación funcional propia.
- `uis/backoffice/` ya existe como panel estático con ruta `/`, README y estilos propios.
- `services/` contiene documentación de convenciones, pero no un backend implementado.
- La rama `feature/agent-memory-bank` estaba sincronizada con `origin` al iniciar la etapa 5; seguía presente la eliminación local de `INSTRUCCIONES_AGENTE_HITO_IA.md`.

## Trabajo completado

- Inventario documental y mapa inicial de entregables de la etapa 1.
- Creación del banco de memoria: `projectbrief.md`, `techContext.md` y este archivo.
- Etapa 3: creado `AGENTS.md` raíz, reglas de contexto y arquitectura en `.agents/rules/`, y skill de validación en `.agents/skills/validate-application-before-commit/`.
- Commits publicados en `feature/agent-memory-bank`: banco de memoria (`9a5ac91`), etapa 3 (`c52222b`), etapa 4 (`a699372`) y etapa 5 (`77f970b`).
- Etapa 4: añadido header/footer web reutilizable, navegación adaptable a móvil y límite HTML de 500 caracteres en comentarios.
- Corregido el comando de servidor: sin `-s`, el formulario se sirve en `/application`; el modo SPA redirigía a la landing.
- Corregidos los globs de Tailwind para que, ejecutado desde la raíz como indica el README, genere las utilidades del sitio y del componente compartido.
- Etapa 5: creado `uis/backoffice/` como vista interna diferenciada, con cifras aproximadas del briefing, líneas de negocio y etapas de talento de `SPEC.md`; no consume ni expone datos personales.
- Documentados en `uis/backoffice/README.md` el origen de los datos, el carácter no operativo del panel y el comando local.
- Commit de etapa 5 publicado en `feature/agent-memory-bank` (`77f970b`).
- Etapa 6: `npm run typecheck` y build Tailwind completados; JSON-LD parseado correctamente y rutas/recursos del website y backoffice comprobados por HTTP con respuesta 200.
- Smoke test del backoffice confirmó el resumen y que no renderiza campos de registros de candidatos.
- Commit de resultados de etapa 6 publicado en `feature/agent-memory-bank` (`59c3535`).
- Etapa 7: confirmado que `feature/agent-memory-bank` está publicada contra `main` y que no existe una PR abierta para esa rama.
- Generadas cuatro capturas con Playwright 1.50.1/Chromium para website y backoffice en 1440 × 900 y 390 × 844, en `docs/screenshots/`.
- Pruebas Playwright: website y backoffice sin overflow horizontal en 1440 y 390 px; formulario vacío mostró errores de nombre/política esperados; envío válido mostró éxito; no hubo errores JavaScript de página.

## Decisiones

- `ingenieria-ia.md` define el alcance del hito.
- `CONTEXT.md` es la fuente para negocio y contenido; `SPEC.md` define el comportamiento del tracker.
- Mantener los entregables explícitos `uis/website` y `uis/backoffice`. Las aplicaciones existentes pueden aportar funcionalidad reutilizable, pero no eliminan automáticamente esos requisitos.
- Confirmar con Carmen Ruiz el claim «12 años de experiencia» antes de incluirlo en contenido nuevo.
- No añadir backend hasta justificar su necesidad.
- No incluir secretos ni datos personales reales de candidatos en documentación, mocks o capturas.

## Riesgos y pendientes

- Rama actual `feature/agent-memory-bank`, sincronizada con `origin` tras publicar el commit de etapa 6 (`59c3535`).
- Permanece una eliminación local preexistente de `INSTRUCCIONES_AGENTE_HITO_IA.md`; no se incluyó en el commit y no debe descartarse sin autorización.
- La PR aún no se ha creado; las capturas están generadas localmente y deben revisarse e incluirse en el commit de entrega.
- No se pudo inspeccionar `uis/website/assets/js/validation.js` porque Copilot lo marca como ignorado; se validó su comportamiento observable desde Chromium.
- El backoffice pasó un smoke test HTTP de `/` (200), contenido de contexto y carga del CSS; Playwright comprobó el viewport desktop/móvil sin overflow horizontal.
- Tailwind avisa que `caniuse-lite` está desactualizado; la compilación termina correctamente.
- El backoffice es estático y no declara scripts de test, lint, typecheck ni build; se validó con serving HTTP.

## Próximos pasos

1. Revisar el diff, estado Git, capturas, secretos y archivos generados antes de la entrega.
2. Crear la PR a `main` con las capturas y resultados de validación; entregar su enlace en el campus.
