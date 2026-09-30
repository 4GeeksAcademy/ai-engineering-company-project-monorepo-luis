# Propuesta de Arquitectura de Backend — Nexova

- **Proyecto:** Backend development with Coding Agents — *Backend Architecture Proposal*
- **Cohorte:** Backend development with Coding Agents (`1670`)
- **Estado:** propuesta inicial; no se implementa backend en este hito
- **Fuentes de negocio:** [`CONTEXT.md`](../CONTEXT.md), [`SPEC.md`](../SPEC.md)
- **Fecha:** 2026-09-30

## 1. Resumen y objetivo

Propongo construir el backend de Nexova como un **monolito modular con arquitectura en capas**, usando FastAPI y una API HTTP versionada. La aplicación sería un único servicio desplegable, con módulos separados por dominio y límites claros entre transporte HTTP, lógica de negocio y persistencia.

La primera responsabilidad del backend sería recibir y gestionar de forma estructurada las solicitudes de profesionales interesados en oportunidades, y dar soporte al flujo interno de revisión y seguimiento de candidatos. El sitio público, el tracker de talento y el backoffice serían clientes independientes de esa API. La propuesta no implica que esas interfaces existentes ya estén conectadas a ella.

La decisión prioriza claridad, seguridad de datos y facilidad de evolución. No recomiendo comenzar con microservicios: las tres líneas de negocio de Nexova no justifican por sí solas desplegar y operar varios servicios antes de conocer sus necesidades de escala e independencia.

## 2. Contexto de negocio y alcance inicial

Nexova es una consultora de recursos humanos y adquisición de talento fundada en 2011, con sede en Valencia y oficina en Miami, aproximadamente 120 empleados y clientes de tecnología, retail y servicios financieros. Sus líneas de negocio son headhunting ejecutivo, outsourcing de atención al cliente y formación corporativa. El problema descrito en `CONTEXT.md` es la recepción desestructurada de perfiles profesionales por correo genérico y la necesidad de una experiencia web moderna para captar talento.

### Alcance propuesto para el primer backend

- Recibir solicitudes de profesionales desde el formulario público, validarlas y registrar su consentimiento de tratamiento de datos.
- Permitir a personal autorizado consultar y gestionar candidatos, su etapa/estado y notas internas.
- Exponer una API coherente para el sitio público y las herramientas internas.
- Mantener separadas las solicitudes públicas, los datos internos de selección y los futuros procesos comerciales.

### Fuera de alcance de esta propuesta

- Implementar endpoints, base de datos, autenticación o despliegue ahora: este entregable es documentación, no código funcional.
- Crear microservicios para cada línea de negocio.
- Diseñar un CRM completo, portal de clientes, gestión de nóminas o contratación.
- Aceptar propuestas comerciales de empresas mediante el formulario de candidatos. El `CONTEXT.md` indica que las consultas de empresas se dirigen a contacto@nexova.com; un futuro formulario de leads B2B requeriría alcance y requisitos propios.
- Migrar automáticamente datos desde la API de demostración del tracker (`SPEC.md`). Antes de sustituirla habrá que validar el contrato y decidir cómo preservar los datos existentes.

## 3. Patrón arquitectónico

### Monolito modular y arquitectura en capas

El servicio se implementaría como una aplicación FastAPI única, organizada por dominios funcionales. Dentro de cada dominio se separarían las responsabilidades principales:

1. **Presentación / API:** routers FastAPI, parsing de requests, autenticación/autorización y códigos HTTP.
2. **Esquemas de entrada y salida:** modelos Pydantic para validar y serializar el contrato HTTP; no se reutilizan como modelos de persistencia por comodidad.
3. **Aplicación / servicios:** casos de uso y reglas del negocio (registrar solicitud, mover un candidato de etapa, añadir una nota).
4. **Dominio:** entidades, estados válidos y reglas que no dependen de FastAPI ni de la base de datos.
5. **Persistencia:** repositorios y modelos de base de datos; la lógica de consultas queda fuera de los routers.

Los límites por dominio evitan una separación artificial por tipo de archivo global —por ejemplo, un único archivo con todos los modelos o todas las rutas— y permiten que el equipo encuentre juntos los componentes de una capacidad. Las capas evitan que las rutas acumulen validación, consultas SQL y reglas de negocio.

### Por qué encaja con Nexova

- El problema inicial es un flujo de captación y revisión de candidatos, no un conjunto de productos autónomos que necesiten despliegues independientes.
- Las capacidades de headhunting, outsourcing y formación comparten información de clientes, personal y procesos de talento. Un servicio inicial permite reutilizar identidad, permisos y convenciones sin llamadas de red entre servicios propios.
- El tamaño y facturación descritos no permiten inferir cargas extremas ni equipos autónomos por dominio. Diseñar microservicios ahora añadiría operación, observabilidad, despliegues y consistencia distribuida sin una necesidad acreditada.
- Un monolito modular permite separar más adelante un módulo si aparece una razón medible —escala propia, ciclo de despliegue independiente, frontera de datos o equipo responsable— sin fingir que esa separación ya es necesaria.

## 4. Estructura propuesta

Ubicación conforme al monorepo: `services/nexova-api/`. Es una estructura objetivo ilustrativa; no se crean aquí los archivos ni se da por instalada ninguna dependencia.

```text
services/
├── README.md
├── README.es.md
└── nexova-api/
    ├── README.md
    ├── pyproject.toml
    ├── .env.example
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                 # crear FastAPI, incluir routers y middleware
    │   ├── config.py               # settings tipados desde entorno
    │   ├── api/
    │   │   ├── router.py           # agrega los routers de /api/v1
    │   │   ├── dependencies.py     # dependencias HTTP compartidas
    │   │   └── v1/
    │   │       ├── public.py       # rutas públicas permitidas
    │   │       ├── applications.py
    │   │       ├── candidates.py
    │   │       ├── notes.py
    │   │       └── health.py
    │   ├── domains/
    │   │   ├── applications/
    │   │   │   ├── schemas.py
    │   │   │   ├── service.py
    │   │   │   ├── repository.py
    │   │   │   └── models.py
    │   │   ├── candidates/
    │   │   │   ├── schemas.py
    │   │   │   ├── service.py
    │   │   │   ├── repository.py
    │   │   │   └── models.py
    │   │   ├── notes/
    │   │   └── users/              # identidad/roles del personal interno
    │   ├── db/
    │   │   ├── session.py
    │   │   └── base.py
    │   └── security/
    │       ├── authentication.py
    │       └── permissions.py
    └── tests/
        ├── api/
        └── domains/
```

La estructura puede empezar más pequeña. Por ejemplo, `applications` y `candidates` podrían compartir una tabla o caso de uso durante el prototipo si las reglas son simples, pero sus contratos y responsabilidades deben seguir siendo comprensibles. No se deben crear capas vacías solo para completar el árbol.

### Criterio de separación de dominios

- **Applications (solicitudes):** entrada pública, validación, consentimiento, confirmación y estado de recepción. Es el límite de confianza entre internet y los datos internos.
- **Candidates (candidatos):** perfil normalizado y flujo interno de selección; estados y etapas válidos, filtros y cambios auditables.
- **Notes (notas):** comentarios internos asociados a un candidato, accesibles únicamente a usuarios autorizados.
- **Users / security:** cuentas internas, roles y permisos; no se confunden con los profesionales que envían el formulario.
- **Clientes / leads B2B:** posible dominio futuro para ventas de servicios. Se deja fuera del primer alcance porque el contexto dirige esas consultas al correo y no define aún un proceso digital de clientes.

Debe decidirse durante el diseño del esquema si una persona puede tener varias solicitudes a lo largo del tiempo. La opción preferida es distinguir el perfil de candidato de cada solicitud a una oportunidad, para preservar historial y consentimiento por envío; si el primer alcance solo captura un registro sin vacantes, se puede iniciar con una relación más simple y documentar la migración antes de añadir postulaciones múltiples.

## 5. Organización de routers y endpoints

Los routers se agrupan por recurso y dominio usando `APIRouter`, con un prefijo común `/api/v1`. Las rutas públicas se separan de las internas y no se ofrece acceso público a búsquedas, notas o perfiles completos.

| Dominio | Endpoint propuesto | Acceso | Uso |
|---|---|---|---|
| Salud | `GET /health` | Operativo | Comprobar que el proceso responde; no exponer secretos ni información interna. |
| Solicitudes públicas | `POST /api/v1/public/applications` | Público, validado y protegido contra abuso | Registrar los campos definidos en `CONTEXT.md`, validar formato y guardar consentimiento. Responder con confirmación y un identificador no sensible. |
| Solicitudes | `GET /api/v1/applications` | Personal autorizado | Listar y filtrar solicitudes para revisión; paginación obligatoria. |
| Solicitudes | `GET /api/v1/applications/{application_id}` | Personal autorizado | Ver detalle según permisos. |
| Candidatos | `GET /api/v1/candidates` | Personal autorizado | Buscar/listar perfiles con filtros de etapa y estado y paginación. |
| Candidatos | `GET /api/v1/candidates/{candidate_id}` | Personal autorizado | Ver perfil y datos necesarios para selección. |
| Candidatos | `PATCH /api/v1/candidates/{candidate_id}` | Personal autorizado | Cambios parciales controlados, especialmente etapa/estado. Validar transiciones válidas. |
| Notas | `GET /api/v1/candidates/{candidate_id}/notes` | Personal autorizado | Consultar notas internas de ese perfil. |
| Notas | `POST /api/v1/candidates/{candidate_id}/notes` | Personal autorizado | Añadir nota con autor y fecha. |
| Notas | `DELETE /api/v1/candidates/{candidate_id}/notes/{note_id}` | Personal autorizado con permiso | Borrar según una política explícita; registrar auditoría o conservar evento de eliminación. |

Los routers se mantendrán delgados: validan el request, requieren permisos, llaman al caso de uso correspondiente y transforman el resultado a una respuesta HTTP. La lógica de etapas, consentimiento y transiciones no debe duplicarse en cada endpoint.

### Contrato y convenciones HTTP

- Mantener versión en el prefijo (`/api/v1`) para evolucionar contratos sin romper de forma silenciosa las interfaces.
- Usar nombres de recursos estables, JSON consistente, validación de entrada y respuestas de error previsibles.
- Usar `201 Created` al registrar recursos, `200 OK` para consultas/cambios con cuerpo, `204 No Content` cuando corresponda, `400/422` para entrada inválida, `401/403` para autenticación/permisos y `404` para recursos inexistentes.
- Paginar las listas de candidatos y solicitudes; no descargar todo el historial al navegador.
- No retornar campos internos, credenciales, notas ni datos personales en endpoints públicos.

## 6. Convenciones de FastAPI que fundamentan la propuesta

La documentación oficial de FastAPI sobre [aplicaciones grandes y múltiples archivos](https://fastapi.tiangolo.com/tutorial/bigger-applications/) muestra cómo separar módulos Python, crear `APIRouter` por conjunto de rutas e incluirlos en la aplicación principal. También explica el uso de prefijos, tags y dependencias comunes de router. De ahí se propone un `main.py` de composición y routers por dominio en vez de un único archivo con todas las operaciones.

FastAPI usa modelos de datos y type hints para validar, documentar y serializar requests y responses. Por ello se separan esquemas HTTP (`schemas.py`) de los modelos persistidos (`models.py`) y de los casos de uso; cada representación cumple una finalidad distinta y evita filtrar accidentalmente campos de base de datos.

La configuración se concentra en `config.py` y se alimenta de variables de entorno tipadas. La guía oficial de [Settings y variables de entorno](https://fastapi.tiangolo.com/advanced/settings/) explica el patrón de leer configuración externa y validarla con Pydantic Settings. Así, URL de base de datos, orígenes CORS, modo de ejecución y secretos no se incrustan en el código ni se versionan en `.env`.

Estas convenciones son una base, no una obligación de crear módulos sin necesidad. La estructura deberá crecer con el dominio y conservar una ruta clara desde endpoint → caso de uso → persistencia.

## 7. Frontend y backend como sistemas separados

### Repositorio, despliegue y comunicación

El proyecto ya organiza las interfaces en `uis/` y reserva `services/` para las APIs. Mantener ambas partes en este monorepo da al equipo una fuente común para el contexto de Nexova y permite revisar cambios coordinados; no obliga a desplegarlas como una sola aplicación. Website, tracker, backoffice y API pueden construirse y publicarse por separado.

El frontend se comunica con el backend por HTTPS mediante requests JSON a una URL configurable, por ejemplo `NEXT_PUBLIC_API_URL` en el tracker y una configuración equivalente para el sitio estático. Los nombres concretos deben documentarse en cada aplicación. Las variables `NEXT_PUBLIC_*` son visibles para el navegador: solo contienen configuración pública como una URL, nunca credenciales o secretos. La API obtiene sus secretos exclusivamente del entorno del servidor.

En desarrollo y producción, cada interfaz debe apuntar al host correcto de la API. Los contratos compartidos (campos, tipos, errores) deben documentarse y evolucionar junto a las aplicaciones; una interfaz no debe llamar directamente a la base de datos.

### CORS

Si la página y la API usan distintos esquemas, dominios o puertos, el navegador aplica CORS. FastAPI documenta el uso de `CORSMiddleware` y recomienda especificar los orígenes permitidos; la guía señala que `*` no sirve para solicitudes con credenciales. Por tanto:

- Configurar una lista explícita de orígenes de desarrollo y dominios reales de website/backoffice; mantenerla en configuración de servidor por entorno.
- Permitir solo métodos y cabeceras necesarios. Activar credenciales únicamente si la estrategia de sesión las requiere y entonces enumerar explícitamente los orígenes.
- No usar `allow_origins=["*"]` en producción como atajo.
- Probar preflight `OPTIONS` y peticiones reales desde cada interfaz desplegada.

Referencia: [FastAPI — CORS](https://fastapi.tiangolo.com/tutorial/cors/) y [MDN — CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS).

## 8. Datos, privacidad y seguridad

El formulario recoge nombre, email, teléfono, país, experiencia, sector, inglés, disponibilidad, LinkedIn opcional, comentarios y aceptación de política. Son datos personales; algunos comentarios o CVs pueden incluir información adicional no necesaria.

- Recoger solo los datos acordados y limitar longitud/tipo de cada campo; no solicitar ni inferir datos sensibles.
- Guardar el consentimiento con marca temporal y versión de la política aceptada. Definir con el responsable de privacidad el propósito, retención, acceso, eliminación y tratamiento de solicitudes de derechos antes de producción.
- Nexova opera en España y Miami. La arquitectura debe registrar ubicación y flujos de datos y someter transferencias internacionales y obligaciones aplicables a revisión legal/privacidad; esta propuesta no sustituye asesoría legal.
- Separar rutas públicas de las internas. Aplicar autenticación y autorización por rol al personal, con principio de mínimo privilegio; nunca hacer público el listado de candidatos ni las notas.
- Usar HTTPS, almacenar hashes de contraseñas si se gestionan credenciales localmente, no registrar tokens ni payloads completos con PII en logs y auditar accesos/cambios relevantes.
- Proteger el endpoint público contra spam y abuso con límites de frecuencia y controles proporcionados; no confiar solo en validación JavaScript del navegador.
- No guardar secretos, tokens o datos reales de candidatos en Git, ejemplos, capturas o logs. Mantener `.env.example` sin valores sensibles y configurar secretos en el entorno de despliegue.

## 9. Persistencia y consistencia

Para el flujo de candidatos, una base de datos relacional es una opción inicial razonable: solicitudes, candidatos, usuarios internos, notas y cambios de etapa tienen relaciones y restricciones que conviene expresar explícitamente. La tecnología y el proveedor no se fijan en esta propuesta; se elegirán al definir el entorno de despliegue, las necesidades de backup y recuperación y el volumen real.

Las escrituras críticas —alta de solicitud, actualización de etapa y creación de nota— deben validar reglas antes de persistir y realizarse de forma atómica. La tabla o registro de historial de etapas debe conservar quién hizo el cambio, cuándo y el estado anterior/nuevo. Los repositorios encapsulan consultas para que FastAPI y las reglas de dominio no dependan de detalles de SQL.

El tracker actual documentado en `SPEC.md` apunta a `playground.4geeks.com/tracker/api/v1`. Es un contrato externo/de demostración, no evidencia de un backend propio de Nexova. Antes de conectarlo al futuro servicio habrá que revisar sus modelos, campos, autenticación y migración; no se deben mezclar ambas fuentes como si fueran una única base confiable.

## 10. Riesgos y puntos de atención

1. **Routers monolíticos con lógica de negocio y SQL:** dificultan probar reglas, generan duplicación y hacen arriesgados los cambios de etapas. Mitigación: routers delgados, servicios/casos de uso y repositorios por dominio.
2. **Separación prematura en microservicios:** añade llamadas de red, despliegues y problemas de consistencia para un flujo que todavía puede vivir en una aplicación única. Mitigación: monolito modular y extracción solo ante una necesidad de escala u organización demostrable.
3. **Exposición de PII o acceso excesivo:** listar candidatos o notas sin autorización, registrar payloads en logs o usar CORS abierto puede filtrar información. Mitigación: autenticación y permisos de servidor, minimización, revisión de logs, CORS explícito y pruebas negativas.
4. **Confundir candidato con solicitud:** sobrescribir el perfil en cada nueva oportunidad puede borrar historial y consentimiento. Mitigación: definir la cardinalidad perfil–solicitud antes de implementar y guardar estados/consentimientos asociados al evento correcto.
5. **Desalineación entre frontends y contrato API:** distintas interfaces pueden esperar nombres, errores o etapas diferentes, mientras que el tracker usa hoy una API de playground. Mitigación: documentar el contrato y versión, revisar cambios coordinados y planificar integración/migración explícita.
6. **Retención y transferencias transfronterizas sin política:** recopilar CVs/datos desde España y EE. UU. sin límites claros aumenta el riesgo de cumplimiento. Mitigación: acordar finalidad, retención, acceso y transferencias con responsables legales/privacidad antes de producción.
7. **Mezcla de solicitudes comerciales y de empleo:** puede enviar datos a un flujo equivocado y confundir a usuarios. Mitigación: mantener el formulario de talento para candidatos y tratar leads empresariales como un proceso separado, solo si se aprueba su alcance.

## 11. Decisiones pendientes antes de implementar

- Definir identidad/autenticación del personal y roles concretos (reclutador, responsable, administrador).
- Acordar si el primer alcance maneja solo registros de talento o también oportunidades/postulaciones múltiples.
- Confirmar política de privacidad, retención, eliminación y tratamiento en España/EE. UU.
- Elegir motor y proveedor de base de datos según el despliegue aprobado, backup y recuperación.
- Definir dominios/orígenes de producción para website, tracker, backoffice y API.
- Especificar cómo migrar o dejar atrás los datos del tracker de demostración.

## 12. Fuentes

- Requisitos del entregable: [4Geeks — Propuesta de Arquitectura de Backend (español)](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-architectural-proposal/README.es.md).
- Contexto de negocio: [`CONTEXT.md`](../CONTEXT.md).
- Convenciones del monorepo: [`services/README.es.md`](../services/README.es.md), [`SPEC.md`](../SPEC.md), [`memory-bank/techContext.md`](../memory-bank/techContext.md).
- FastAPI, estructura de aplicaciones grandes: [Bigger Applications — Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/).
- FastAPI, configuración: [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/).
- FastAPI, solicitudes cross-origin: [CORS](https://fastapi.tiangolo.com/tutorial/cors/).
- MDN, referencia general: [Cross-Origin Resource Sharing (CORS)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS).
