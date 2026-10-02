# Instrucciones para agentes

## Lectura obligatoria al comenzar

Antes de implementar o modificar archivos:

1. Leer `ingenieria-ia.md` para conocer el alcance y los criterios de aceptación del hito.
2. Leer `CONTEXT.md` y `memory-bank/projectbrief.md` para el dominio y las restricciones de Nexova.
3. Leer `memory-bank/techContext.md` y `memory-bank/progress.md` para la arquitectura, los comandos y el estado conocido.
4. Leer el README de cada carpeta que se vaya a modificar y revisar los `AGENTS.md` o reglas aplicables a esa ruta. Si se trabaja en el tracker, leer también `SPEC.md` y respetar `uis/talent-pipeline-tracker/AGENTS.md`.
5. Revisar `git status --short --branch` y el diff existente. No asumir que la rama o el árbol de trabajo están limpios.

Las reglas de `.agents/rules/` con alcance aplicable también forman parte de las instrucciones de la tarea. El banco de memoria resume fuentes: no las reemplaza.

## Fuentes de verdad

- `ingenieria-ia.md` define los entregables y la aceptación del hito.
- `CONTEXT.md` define el negocio, la marca y los requisitos de la web pública.
- `SPEC.md` define los requisitos funcionales y la API del tracker.
- Los README y `package.json` de cada aplicación definen su configuración y comandos reales.
- Si hay contradicciones entre fuentes, detener el cambio afectado, señalar la diferencia y pedir aclaración; no inventar una resolución.

## Arquitectura del monorepo

- Interfaces: `uis/`. La web pública vive en `uis/website`; la aplicación interna requerida vive en `uis/backoffice`.
- La aplicación `uis/talent-pipeline-tracker` gestiona el flujo detallado de candidatos; no asumir que reemplaza el entregable `uis/backoffice`.
- APIs y workers: `services/`. No crear un backend si las necesidades pueden cubrirse de forma documentada sin él.
- Datos y pipelines: `data/`; agentes de producto: `agents/`; skills de producto: `skills/`; reglas y skills para agentes de desarrollo: `.agents/`.
- Antes de crear una subcarpeta, leer su README y seguir las convenciones locales.

## Validación

Ejecutar solo las comprobaciones disponibles y pertinentes a los archivos modificados. Revisar los scripts del `package.json` y el README de la aplicación; no inventar scripts ni declarar exitosos checks que no se ejecutaron.

Comandos actualmente documentados:

- Raíz: `npm run typecheck` y `npm run demo`.
- Website: compilar Tailwind según `uis/website/README.es.md`; ejecutar `npx --yes serve uis/website -l 5500` (usar otro puerto si está ocupado) y comprobar `/`, `/index.html`, `/application` y `/application.html`. No usar el modo SPA `-s`: hace que `/application` devuelva la landing.
- Tracker: desde `uis/talent-pipeline-tracker/`, ejecutar `npm run lint` y `npm run build`. Consultar esa carpeta para las instrucciones específicas de Next.js.
- Backoffice: seguir su README y scripts una vez que se cree; documentar cualquier check no disponible.

## Cambios que requieren confirmación explícita

Pedir confirmación antes de:

- Cambiar el briefing de negocio en `CONTEXT.md` o los requisitos funcionales en `SPEC.md`.
- Leer, modificar o versionar secretos, credenciales o archivos `.env*`.
- Usar, almacenar o publicar datos personales reales de candidatos.
- Eliminar o renombrar aplicaciones, datos o documentación existente fuera del alcance acordado.
- Conectar sistemas externos, bases de datos reales o servicios de producción sin configuración y autorización documentadas.
- Crear commits, hacer push o abrir una Pull Request, salvo que el usuario lo haya pedido expresamente para esos cambios.

## Cuándo detenerse y pedir aclaración

Detener el trabajo afectado si las fuentes de negocio o requisitos se contradicen, faltan datos necesarios para decidir el comportamiento, la implementación requiere datos personales o credenciales reales, la ruta o arquitectura solicitada no está clara, o una validación revela un riesgo que no se puede resolver sin ampliar el alcance. Informar qué falta y qué decisión concreta se necesita.

## Flujo obligatorio antes de cada commit

1. Revisar el diff y confirmar que solo contiene cambios del objetivo autorizado.
2. Ejecutar tests y comprobaciones pertinentes disponibles.
3. Ejecutar lint, typecheck y/o build de las aplicaciones afectadas.
4. Actualizar `memory-bank/` y la documentación si cambió el comportamiento, la arquitectura o el estado del proyecto.
5. Revisar secretos, archivos generados y configuración sensible sin imprimir valores secretos.
6. Revisar `git status`, preparar un mensaje descriptivo y confirmar qué archivos entrarán en el commit.
