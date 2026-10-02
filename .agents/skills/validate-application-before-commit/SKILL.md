# Skill: Validar una aplicación antes del commit

## Objetivo único

Determinar y reportar si los cambios de una aplicación tienen las validaciones pertinentes ejecutadas y están listos para proponerse para un commit. Esta skill no crea commits, no hace push ni abre Pull Requests.

## Cuándo utilizarla

Antes de proponer un commit que incluya cambios en una aplicación de `uis/` o en un servicio de `services/`.

## Inputs necesarios

- Ruta de la aplicación o servicio modificado.
- Lista o diff de los archivos del cambio.
- Objetivo del cambio y criterios de aceptación relevantes.

Si alguno falta, deducirlo del diff y de `ingenieria-ia.md`; si el objetivo o el alcance siguen ambiguos, informar el bloqueo en vez de asumir.

## Archivos que debe inspeccionar

1. `AGENTS.md` de raíz y cualquier instrucción local aplicable.
2. `ingenieria-ia.md`, `CONTEXT.md` y los archivos pertinentes de `memory-bank/`.
3. README, `package.json` y configuración de la aplicación afectada.
4. `SPEC.md` y `uis/talent-pipeline-tracker/AGENTS.md` si el cambio afecta al tracker.
5. El diff y el estado de Git; no leer ni imprimir archivos de secretos como `.env.local`.

## Pasos

1. Relacionar el cambio con sus criterios de aceptación y verificar que se limita al alcance autorizado.
2. Identificar los comandos reales en el README y `package.json` de la aplicación; no inventar scripts.
3. Ejecutar tests disponibles y luego lint, typecheck y build pertinentes al cambio.
4. Arrancar la aplicación cuando sea posible y comprobar las rutas y estados afectados, incluyendo errores visibles en consola.
5. Revisar el diff, cambios generados, secretos y datos personales sin revelar valores sensibles.
6. Informar el resultado de cada comprobación y las limitaciones; no marcar como correcto un check no ejecutado.

## Restricciones

- No crear commit, hacer push ni abrir PR.
- No incluir PII real de candidatos, credenciales ni secretos en logs, fixtures o capturas.
- No alterar datos, configuración o infraestructura real para hacer pasar una validación.
- Si falta un comando o una dependencia, registrar el motivo y continuar solo con comprobaciones seguras disponibles.

## Comandos conocidos

Ejecutar únicamente los que apliquen a los archivos modificados:

- Raíz: `npm run typecheck`.
- `uis/website`: compilar Tailwind con el comando de `uis/website/README.es.md`; servir con `npx --yes serve uis/website -l 5500` (o un puerto disponible), sin modo SPA `-s`, y probar `/`, `/index.html`, `/application` y `/application.html`.
- `uis/talent-pipeline-tracker`: desde su carpeta, `npm run lint` y `npm run build`. No hay scripts propios de test ni typecheck declarados.
- `uis/backoffice` u otros servicios: consultar primero el README y `package.json` correspondientes; si aún no existen, documentar que no aplica.

## Criterios de aceptación

- Se ejecutaron y reportaron los comandos disponibles que aplican, o se indicó el motivo específico por el que alguno no se pudo ejecutar.
- La aplicación arranca y las rutas afectadas funcionan cuando el entorno permite probarlas.
- Los requisitos de negocio, estados de interfaz y estructura del monorepo se respetan.
- El diff no contiene archivos ajenos, secretos ni datos personales reales.
- El resultado termina con uno de estos estados: `LISTO PARA REVISIÓN`, `NO LISTO` o `BLOQUEADO`, con evidencia breve.

## Resultado esperado

Un informe breve con archivos/rutas comprobados, comandos y resultados, defectos pendientes y estado final. No realizar la operación Git.
