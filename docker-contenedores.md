# Contenedorización del Monorepo de la Empresa

> Guía de auditoría e implementación para el proyecto **Company Monorepo Containerization** de 4Geeks Academy (cohorte *Container applications with Docker*). Consolida el README oficial en español, sus secciones **«Lo que debes hacer»** y **«Lo que evaluaremos»**, y una revisión inicial del repositorio de Luis. La especificación oficial prevalece ante cualquier diferencia.

- **Tarea 4Geeks:** `Company Monorepo Containerization` (ID `1008338`; asset `ai-eng-company-monorepo-container`).
- **README oficial:** [español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-container-project/README.es.md) · [inglés](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-container-project/README.md).
- **Repositorio de trabajo:** [ai-engineering-company-project-monorepo-luis](https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo-luis).
- **Fecha de la auditoría del checkout:** 23 de octubre de 2026.

## Objetivo y alcance

El objetivo es que el monorepo tenga un entorno de desarrollo reproducible y versionado, que un miembro nuevo del equipo pueda iniciar desde la raíz con `docker compose up`, sin instalar/configurar manualmente runtimes o dependencias. Se pide contenerizar las dos interfaces indicadas (`/uis/website` y `/uis/backoffice`) en **un solo contenedor UI**, además del backend FastAPI en un contenedor separado, con recarga en caliente y comunicación por la red de Compose. También es requisito desplegar el stack en el VPS existente del proyecto; que funcione solo en local **no** completa la tarea.

El proyecto no solicita crear un monorepo nuevo. Trabaja en este fork y conserva sus carpetas y servicios existentes. No confundas este hito con los contenedores de desarrollo de `.devcontainer/`: el entregable requiere Dockerfiles, ignores y Compose propios.

## Auditoría inicial del repositorio

La estructura encontrada no coincide completamente con algunas suposiciones del README oficial. Antes de codificar, verifica el estado actual de los archivos y resuelve esta diferencia de forma explícita:

- `uis/website/` contiene una web estática (`index.html`, `application.html`, `assets/`); no tiene `package.json` ni es una aplicación Next.js.
- `uis/backoffice/` contiene HTML, CSS y JavaScript estáticos; tampoco tiene `package.json` ni es una aplicación Next.js.
- Sí existe una app Next.js en `uis/talent-pipeline-tracker/` con su propio `package.json` y scripts `dev`/`build`/`start`.
- La API FastAPI está en `services/api/`, con `main.py`, `requirements.txt` y `uv.lock`; no en la raíz de `services/`.
- El `.gitignore` de la raíz ya ignora `.env`, `.env.*` y artefactos Python/Node. Confirma este comportamiento en la rama de trabajo y comprueba que no haya secretos previamente versionados.

El README de 4Geeks pide instalar las dependencias de `/uis/website` y `/uis/backoffice` y ejecutar **dos Next.js** en 3000 y 3001 desde `uis/start.sh`. En el checkout auditado no existen esos dos proyectos Next.js. No inventes scripts o manifiestos inexistentes ni presentes el tracker como si fuera esas dos interfaces: documenta la discrepancia, identifica con el tech lead/4Geeks si el objetivo es adaptar las interfaces actuales o si el repositorio esperado ha cambiado, y ajusta la solución manteniendo el criterio funcional de un único servicio UI para las interfaces solicitadas. No cambies el alcance sin dejar constancia y sin comprobar los criterios oficiales vigentes.

## Qué debes hacer

### 1. Preparar el entorno y revisar el monorepo

- [ ] Usar Docker Desktop, o Docker Engine y Docker Compose CLI v2, instalado y en ejecución.
- [ ] Trabajar en el fork indicado por el curso, desde la raíz de este repositorio.
- [ ] Revisar la estructura real de `uis/` y `services/`, los README de esas carpetas y la configuración/variables necesarias de las apps.
- [ ] Resolver y dejar documentada la diferencia de stack descrita arriba antes de decidir los comandos de arranque.
- [ ] Confirmar acceso SSH al VPS existente, pero no incluir claves, contraseñas, tokens, IP privada ni otros secretos en archivos versionados o en esta guía.
- [ ] Crear el `.env` privado de la raíz antes de completar Compose. Mantener nombres y valores requeridos por las aplicaciones; no agregar credenciales de ejemplo que parezcan reales.

### 2. Servicio UI: `uis/Dockerfile`, `uis/start.sh`, `uis/.dockerignore`

- [ ] Crear `uis/Dockerfile` basado en una imagen oficial de Node basada en Alpine.
- [ ] Instalar por separado las dependencias de las dos interfaces pedidas (`uis/website` y `uis/backoffice`) según su stack real. En el checkout auditado son estáticas, así que no ejecutar `npm install` ni `next dev` en carpetas donde no existe `package.json`.
- [ ] Proveer `uis/start.sh` como comando de inicio predeterminado del Dockerfile y hacer que el contenedor UI sirva las dos interfaces solicitadas en puertos separados: website en `3000`, backoffice en `3001`. Asegurar que los procesos permanecen en primer plano, que ambos fallos se propagan y que el script es ejecutable.
- [ ] Si se confirma que el requisito de 4Geeks se refiere a dos apps Next.js, iniciar cada una en modo desarrollo con hot reload. Si se acuerda servir las interfaces HTML estáticas actuales, escoger y documentar un servidor de desarrollo adecuado que mantenga los mismos puertos/criterios de acceso; no etiquetar ese resultado como dos apps Next.js.
- [ ] Crear `uis/.dockerignore`, excluyendo como mínimo `node_modules`, `.next`, `.env*` y `*.log`. Añadir artefactos locales pertinentes sin excluir código fuente ni archivos necesarios para la imagen.

### 3. Backend: `services/Dockerfile` y `services/.dockerignore`

- [ ] Crear `services/Dockerfile` basado en una imagen oficial de Python.
- [ ] Instalar `uv` en la imagen y las dependencias con el comando requerido `uv pip install -r requirements.txt`.
- [ ] Tener presente que el archivo real está en `services/api/requirements.txt`. Ajustar el contexto/build o la ubicación de Dockerfile para que la instalación use ese archivo, sin cambiarlo de sitio inadvertidamente.
- [ ] Ejecutar Uvicorn contra el módulo real `services.api.main:app`, escuchando en `0.0.0.0:8000`, con `--reload` habilitado para desarrollo. La app también inicializa la base de datos y carga configuración al arrancar.
- [ ] Crear `services/.dockerignore`, excluyendo como mínimo `__pycache__`, `*.pyc`, `.env*`, `tests/` y `*.log`. Verificar el contexto: desde `services/`, el directorio `api/tests/` no debe copiarse a la imagen de desarrollo si se excluye con ese patrón.
- [ ] Revisar almacenamiento persistente y rutas de datos. En particular, no perder datos locales necesarios al recrear contenedores; no incluir bases de datos locales con datos reales en Git.

### 4. Orquestación: `docker-compose.yml` en la raíz

- [ ] Definir dos servicios, uno UI (build desde `./uis`) y uno backend (build desde `./services`).
- [ ] En el UI, montar el código fuente de las interfaces como bind mount y arrancar ambas aplicaciones con sus comandos de desarrollo/hot reload según el stack confirmado.
- [ ] En el backend, montar el código fuente de `services/` como bind mount y arrancar Uvicorn con `--reload`.
- [ ] Publicar los puertos requeridos: `3000` y `3001` para las interfaces y `8000` para FastAPI, con puertos de contenedor y host explícitos.
- [ ] Conectar ambos servicios a una red Docker con nombre explícito. En conexiones **entre contenedores**, el host de la API debe ser el nombre de servicio de Compose (por ejemplo `backend`) y el puerto interno `8000`; no `localhost`, `127.0.0.1` ni una IP fijada.
- [ ] Tener en cuenta el límite entre redes: el navegador del usuario no puede resolver el DNS interno de Compose. Si el frontend llama a la API desde el navegador, configurar una URL accesible desde el navegador o un proxy/ruta de backend, en vez de pasarle una URL `http://backend:8000` que solo es resoluble dentro de Docker.
- [ ] Cargar configuración mediante variables de entorno desde `.env` raíz; no fijar secretos en YAML/Dockerfile ni duplicar valores sensibles en el código.
- [ ] Mantener `.env` fuera de Git. El `.gitignore` raíz existente ya contiene reglas para `.env` y `.env.*`; verificarlo en la rama y no quitar la excepción/las reglas inadvertidamente. Se puede versionar un `.env.example` sin valores secretos si hace falta documentar las variables.
- [ ] Evitar montar el directorio del host sobre las dependencias instaladas dentro de la imagen de modo que las oculte. Para Node (y, si aplica, otros paquetes), usar volúmenes nombrados o una configuración equivalente.
- [ ] Validar el YAML/Compose y comprobar los logs y la conectividad entre servicios, no solo que el comando termine sin error.

### 5. Despliegue obligatorio al VPS

- [ ] Después de validar Compose local, desplegar el monorepo en **el VPS existente** del proyecto y dejar el stack alcanzable allí.
- [ ] Proveer en el VPS los valores de producción de forma segura, fuera de Git. No copiar el `.env` local al repositorio ni publicar credenciales.
- [ ] Verificar que los contenedores UI y backend están en ejecución y que las interfaces y API necesarias responden desde la ubicación prevista.
- [ ] Conservar evidencia verificable de despliegue (por ejemplo salida de `docker compose ps` obtenida en el VPS, URL accesible o captura), sin filtrar secretos.
- [ ] El README oficial exige modo desarrollo y hot reload para el entorno local. Para el VPS, separar claramente configuración de desarrollo y de producción: no exponer innecesariamente el servidor de desarrollo ni `--reload` a Internet; documentar cómo se cumple el despliegue y qué comandos/configuración de producción se usan, manteniendo los criterios publicados por 4Geeks.

### 6. Rama y entrega

- [ ] Hacer commit y push de los archivos de contenedorización a una rama del repositorio del proyecto.
- [ ] Abrir un Pull Request hacia `main` y, una vez aprobado, integrarlo según el flujo del equipo; el README oficial indica expresamente hacer merge del PR aprobado.
- [ ] Incluir en la descripción del PR una captura o salida de contenedores locales (`docker compose ps` o `docker compose up`).
- [ ] Incluir evidencia de que el stack está desplegado y corriendo en el VPS (salida de Compose por SSH, URL o captura).
- [ ] Compartir el enlace del PR con el tech lead para el sign-off.

## Qué vamos a evaluar

Usa esta lista como matriz de aceptación; no marques un criterio como logrado sin evidencia reproducible:

- [ ] `docker compose up` desde la raíz inicia toda la plataforma sin errores ni configuración manual adicional.
- [ ] Los cambios de código del host aparecen en el navegador sin reconstruir las imágenes: bind mounts y recarga en caliente funcionan en ambos servicios.
- [ ] Un único contenedor UI inicia las dos interfaces en puertos distintos (`3000` y `3001`). El estado real del repositorio y cualquier desviación acordada respecto a “dos Next.js” están documentados con precisión.
- [ ] El servicio FastAPI se inicia en su contenedor con Uvicorn y `--reload` en desarrollo.
- [ ] Las conexiones internas entre servicios usan el nombre del servicio Docker, no `localhost` ni IPs hardcodeadas; las URLs usadas por navegadores son accesibles desde el host del navegador.
- [ ] No hay secretos, API keys ni contraseñas hardcodeadas en Dockerfiles ni en `docker-compose.yml`.
- [ ] `.env` está ignorado por Git y no se añadió al commit/historial. Existe un ejemplo sin secretos si se documentan variables.
- [ ] Hay `.dockerignore` tanto en `uis/` como en `services/`, que incluyen todas las exclusiones mínimas pedidas.
- [ ] El monorepo está desplegado y en funcionamiento en el VPS existente; la entrega aporta evidencia de producción y no solo ejecución local.
- [ ] Se abrió el PR a `main`, con evidencia local y VPS, y se integró tras la aprobación del tech lead.

## Comprobación sugerida

Desde la raíz, una vez implementada la configuración:

```bash
# Revisar Compose antes de arrancar
 docker compose config

# Levantar servicios
 docker compose up --build

# En otra terminal: estado y logs
 docker compose ps
 docker compose logs --tail=100

# Comprobar API desde el host
 curl --fail http://localhost:8000/health
```

Para comprobar hot reload, modifica temporalmente un archivo de cada servicio y verifica el refresco/reinicio correspondiente sin reconstruir. Para verificar el DNS interno, prueba una petición **desde un contenedor hacia el servicio backend usando el nombre de servicio**. Para el VPS, ejecutar las comprobaciones desde el entorno remoto y registrar evidencia no sensible.

## Riesgos y decisiones pendientes de confirmar

1. **Desajuste de frontend:** la consigna declara dos apps Next.js; el checkout contiene interfaces estáticas y una sola app Next.js (`talent-pipeline-tracker`). Acordar el alcance técnico antes de dar por superada la comprobación de “ambas apps Next.js”.
2. **Ubicación backend:** la instrucción genérica presupone `/services/requirements.txt`; el archivo que existe es `/services/api/requirements.txt`. Ajustar Dockerfile/contexto a la ubicación efectiva.
3. **Desarrollo vs. producción:** `--reload` y Next `dev` son requisitos de desarrollo; el VPS también es obligatorio, pero no se deben confundir las prácticas de desarrollo con una configuración de producción expuesta. Documentar configuración y seguridad del despliegue.
4. **Alcance:** no reemplazar el monorepo ni rehacer las aplicaciones para satisfacer Docker; contenerizar las apps existentes y resolver discrepancias con el responsable del proyecto.

> Esta guía es un documento de trabajo auditado, no evidencia de que la contenedorización, las pruebas, el PR o el despliegue al VPS ya se hayan completado. La entrega final deberá reflejar lo que efectivamente se implemente y verifique.
