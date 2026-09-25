# Tech Context

## Fuentes de verdad

- `ingenieria-ia.md`: alcance, ubicaciones y criterios de aceptación de este hito.
- `CONTEXT.md`: negocio de Nexova y requisitos del sitio público y formulario.
- `SPEC.md`: requisitos funcionales y API del tracker de candidatos.
- README y `package.json` de cada aplicación: estructura y comandos disponibles.
- Este archivo resume esas fuentes; si hay discrepancias, consultar la fuente original.

## Estructura actual relevante

- `uis/website/`: sitio público estático existente, con `index.html`, `application.html` y estilos Tailwind.
- `uis/talent-pipeline-tracker/`: aplicación Next.js existente para gestión detallada de candidatos.
- `uis/backoffice/`: aplicación interna requerida por el hito; pendiente de crear.
- `services/`: documentación de convenciones; no hay un servicio backend implementado actualmente.
- `memory-bank/`: contexto persistente para el proyecto.
- `.agents/`: reglas y skills para agentes de desarrollo; pendiente de crear.
- Existe `uis/talent-pipeline-tracker/AGENTS.md`; no sustituye el `AGENTS.md` raíz requerido.

## Stack y datos

- Sitio público: HTML estático, Tailwind CSS 3.4.17 y componentes web nativos compartidos para header/footer en `uis/website/shared-components.js`.
- Tracker de candidatos: Next.js App Router, React, TypeScript y Tailwind CSS 4.
- El tracker consume `https://playground.4geeks.com/tracker/api/v1`; revisar `SPEC.md` para rutas, modelos y comportamiento.
- La tecnología e integración de datos del nuevo backoffice quedan por decidir al implementarlo. Reutilizar la API del tracker solo si cubre los requisitos del backoffice.
- No crear un backend por defecto. Si se necesita, debe vivir bajo `services/` y seguir sus convenciones.

## Comandos declarados

Desde la raíz:

- `npm run typecheck`
- `npm run demo`

Sitio público, desde la raíz:

- Compilar Tailwind: `npx --yes tailwindcss@3.4.17 -c uis/website/tailwind.config.cjs -i uis/website/assets/css/input.css -o uis/website/assets/css/styles.css --minify`
- Servir: `npx --yes serve uis/website -l 5500` (usar otro puerto si 5500 está ocupado). Ejecutar desde la raíz; no usar `-s`, porque el fallback SPA sirve la landing para `/application`.
- Verificar `/`, `/index.html`, `/application` y `/application.html`; `serve` redirige las páginas `.html` a sus rutas limpias.

Tracker, desde `uis/talent-pipeline-tracker/`:

- `npm run dev`
- `npm run lint`
- `npm run build`
- `npm run start`
- No declara scripts propios para tests ni typecheck.

Los comandos están documentados, pero aún no se han ejecutado como parte de esta auditoría. Añadir aquí los comandos del backoffice cuando se seleccione e implemente su stack.

## Restricciones técnicas y de datos

- Respetar las ubicaciones del monorepo y leer el README de cada carpeta antes de añadir una aplicación o servicio.
- No leer, imprimir ni versionar secretos de `uis/talent-pipeline-tracker/.env.local`.
- No almacenar PII real de candidatos en este banco de memoria, mocks o capturas.
- Documentar mocks, APIs externas, estados de carga/error y limitaciones de datos.
- La documentación es un resumen operativo; no reemplaza las especificaciones ni los contratos originales.
