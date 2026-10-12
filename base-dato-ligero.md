# Hito 09 — API de Proveedores con Almacenamiento Ligero

> Documento de contexto y auditoría del proyecto 4Geeks **«Almacenar datos en bases de datos ligeras — Directorio de Proveedores»**. Su objetivo es dejar reunidos los requisitos antes de implementar. No reemplaza los README fuente ni el contexto de Nexova.

## Fuentes auditadas

- Tarea de 4Geeks: **Supplier Directory — Lightweight Storage API** (`ai-eng-supplier-directory`), proyecto pendiente.
- README del proyecto en español: [README.es.md](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-supplier-directory/README.es.md).
- README en inglés: [README.md](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-supplier-directory/README.md).
- Contexto de negocio Nexova: [CONTEXT-nexova.es.md](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/supplier-directory/CONTEXT-nexova.es.md).

La versión española e inglesa del README contienen esencialmente los mismos requisitos. El contexto Nexova es la fuente de verdad para el esquema exacto, categorías, estados y datos del seeder.

## Auditoría: objetivo y arquitectura

Nexova necesita reemplazar su hoja de cálculo de proveedores por un directorio oficial, persistente y accesible mediante API. El backend requerido es **FastAPI + TinyDB + Pydantic**. TinyDB es una solución ligera para esta etapa; se contempla migrar a PostgreSQL más adelante, cuando exista un ORM.

La implementación debe ubicarse en el monorepo existente, no en un repositorio nuevo:

- Backend: `/services/api`.
- Interfaz de gestión: el README la llama `/uis/backoffice`.
- El esquema de entrega muestra `uis/application/app/suppliers/` para la página de proveedores.

### Discrepancia del README que hay que resolver al implementar

Hay dos rutas distintas para el frontend: la sección de trabajo indica `/uis/backoffice`, pero el árbol de entrega muestra `uis/application/app/suppliers/`. Además, las convenciones del monorepo de este repositorio asignan las interfaces a `uis/` y describen `uis/backoffice` como la aplicación interna. Antes de crear la página, inspeccionar la estructura real y los READMEs locales, y mantener la integración con la aplicación existente; no crear una segunda aplicación por asumir que una de las rutas es correcta.

El README dice que no hay código inicial para este proyecto, pero el repositorio objetivo es un monorepo ya existente. Esto debe interpretarse como que el nuevo módulo de proveedores no tiene starter específico, no como permiso para recrear o sustituir el monorepo.

## Contexto de negocio

Nexova es una consultora de recursos humanos y adquisición de talento con sede en Valencia y oficina en Miami. El equipo de compras/operaciones necesita mantener una única fuente de verdad para proveedores de servicios recurrentes: portales de empleo, software ATS, evaluación, formación, nóminas/RR. HH., entrevistas por vídeo, verificación de antecedentes, instalaciones y licencias IT.

El stakeholder funcional del directorio es Patricia Solís, HR Manager; el tech lead es Sergio Molina, CTO. Los datos actuales están en una hoja de cálculo, con versiones distribuidas y sin trazabilidad clara.

## Modelo de datos requerido

Cada proveedor debe representar estos campos:

| Campo | Tipo y reglas |
|---|---|
| `name` | `string`, obligatorio. Nombre comercial. |
| `country` | `string`, obligatorio: exactamente `Spain` o `USA`. |
| `categories` | Lista obligatoria de strings; al menos una categoría válida. |
| `monthly_rate` | Número (`float`) obligatorio, estrictamente mayor que cero. |
| `currency` | Obligatoria: `EUR` para `Spain`, `USD` para `USA`. Rechazar combinaciones inconsistentes. |
| `updated_at` | Fecha/hora generada por el sistema; refleja la última actualización de tarifa, no es un valor controlado por el cliente. |
| `status` | Obligatorio: `active` o `suspended`, sin otros valores. |
| `contract_renewal_date` | Opcional, fecha como texto `YYYY-MM-DD`. |
| `contact_email` | Email del account manager, opcional. |
| `notes` | Observaciones internas, opcional. |

Categorías permitidas, respetando exactamente los identificadores:

- `job_boards`
- `ats_software`
- `assessment_tools`
- `training_platforms`
- `payroll_and_hr_software`
- `video_interview`
- `background_check`
- `office_and_facilities`
- `it_and_software_licenses`

Estados válidos: `active`, `suspended`.

Validar la entrada con Pydantic antes de escribir en TinyDB. Separar modelos de entrada y respuesta cuando corresponda, para impedir que el cliente fije `updated_at` o el ID interno.

## Datos iniciales exactos del seeder

`seed.py` debe insertar estos 15 proveedores de forma idempotente. No inventar, omitir ni renombrar campos/categorías. Los campos opcionales que no aparecen en un elemento deben permanecer ausentes o tener el tratamiento de opcional definido por el modelo.

```python
SUPPLIERS_SEED = [
    {
        "name": "LinkedIn Talent Solutions",
        "country": "Spain",
        "categories": ["job_boards"],
        "monthly_rate": 1200.0,
        "currency": "EUR",
        "status": "active",
        "contract_renewal_date": "2025-03-31",
        "contact_email": "account@linkedin.com",
        "notes": "Licencia corporativa para publicación de ofertas y búsqueda de candidatos."
    },
    {
        "name": "InfoJobs Premium",
        "country": "Spain",
        "categories": ["job_boards"],
        "monthly_rate": 490.0,
        "currency": "EUR",
        "status": "active",
        "contract_renewal_date": "2025-06-30",
        "contact_email": "empresas@infojobs.net"
    },
    {
        "name": "Indeed Sponsored",
        "country": "USA",
        "categories": ["job_boards"],
        "monthly_rate": 850.0,
        "currency": "USD",
        "status": "active",
        "contact_email": "sales@indeed.com",
        "notes": "Campañas de pago por clic para perfiles de customer support en Miami."
    },
    {
        "name": "Workable",
        "country": "Spain",
        "categories": ["ats_software"],
        "monthly_rate": 299.0,
        "currency": "EUR",
        "status": "active",
        "contract_renewal_date": "2025-09-15",
        "contact_email": "support@workable.com",
        "notes": "ATS principal para el equipo de selección de Valencia."
    },
    {
        "name": "Greenhouse",
        "country": "USA",
        "categories": ["ats_software"],
        "monthly_rate": 620.0,
        "currency": "USD",
        "status": "suspended",
        "contact_email": "accounts@greenhouse.io",
        "notes": "Suspendido tras no renovar. Sergio está evaluando si migrar todo a Workable."
    },
    {
        "name": "Thomas International",
        "country": "Spain",
        "categories": ["assessment_tools"],
        "monthly_rate": 380.0,
        "currency": "EUR",
        "status": "active",
        "contract_renewal_date": "2025-12-01",
        "contact_email": "clientes@thomas.es",
        "notes": "Tests de personalidad y aptitud para procesos de mandos intermedios."
    },
    {
        "name": "HireVue",
        "country": "USA",
        "categories": ["video_interview"],
        "monthly_rate": 540.0,
        "currency": "USD",
        "status": "active",
        "contract_renewal_date": "2025-08-31",
        "contact_email": "support@hirevue.com"
    },
    {
        "name": "Udemy Business",
        "country": "Spain",
        "categories": ["training_platforms"],
        "monthly_rate": 420.0,
        "currency": "EUR",
        "status": "active",
        "contract_renewal_date": "2026-01-15",
        "contact_email": "business@udemy.com",
        "notes": "Licencias para el equipo interno. Gestionado por Elena Vargas."
    },
    {
        "name": "Coursera for Teams",
        "country": "USA",
        "categories": ["training_platforms"],
        "monthly_rate": 399.0,
        "currency": "USD",
        "status": "suspended",
        "contact_email": "teams@coursera.com",
        "notes": "Suspendido por bajo uso. Revisar antes de Q4."
    },
    {
        "name": "Sage HR",
        "country": "Spain",
        "categories": ["payroll_and_hr_software"],
        "monthly_rate": 310.0,
        "currency": "EUR",
        "status": "active",
        "contract_renewal_date": "2025-10-01",
        "contact_email": "soporte@sage.com",
        "notes": "Software de nóminas y gestión de personal para la sede de Valencia."
    },
    {
        "name": "Gusto",
        "country": "USA",
        "categories": ["payroll_and_hr_software"],
        "monthly_rate": 280.0,
        "currency": "USD",
        "status": "active",
        "contact_email": "support@gusto.com",
        "notes": "Gestión de nóminas para los empleados de la oficina de Miami."
    },
    {
        "name": "Checkr",
        "country": "USA",
        "categories": ["background_check"],
        "monthly_rate": 195.0,
        "currency": "USD",
        "status": "active",
        "contract_renewal_date": "2025-11-30",
        "contact_email": "sales@checkr.com"
    },
    {
        "name": "Microsoft 365 Business",
        "country": "Spain",
        "categories": ["it_and_software_licenses"],
        "monthly_rate": 760.0,
        "currency": "EUR",
        "status": "active",
        "contact_email": "enterprise@microsoft.com",
        "notes": "Licencias para toda la plantilla de Valencia y Miami."
    },
    {
        "name": "Regus Valencia",
        "country": "Spain",
        "categories": ["office_and_facilities"],
        "monthly_rate": 2400.0,
        "currency": "EUR",
        "status": "active",
        "contract_renewal_date": "2025-07-01",
        "contact_email": "valencia@regus.com",
        "notes": "Alquiler de la oficina principal en Valencia. Incluye sala de reuniones."
    },
    {
        "name": "WeWork Miami",
        "country": "USA",
        "categories": ["office_and_facilities"],
        "monthly_rate": 3100.0,
        "currency": "USD",
        "status": "active",
        "contract_renewal_date": "2025-09-30",
        "contact_email": "miami@wework.com"
    }
]
```

> Nota: las fechas de renovación de los datos semilla son las que publica el contexto del proyecto, aunque varias ya quedan en el pasado. No actualizarlas silenciosamente. La regla visual del README habla de renovaciones dentro de los próximos 60 días; con datos históricos no habrá renovaciones próximas según la fecha actual salvo que el contexto se actualice expresamente.

## Requisitos funcionales del backend

- `POST /suppliers`: crear proveedor; respuesta con registro completo e ID TinyDB; entradas inválidas → `422`.
- `GET /suppliers`: devolver todos; aceptar filtros opcionales `country` y `category`; ambos filtros deben poder aplicarse conjuntamente de manera coherente.
- `GET /suppliers/{id}`: detalle por ID; inexistente → `404`.
- `PATCH /suppliers/{id}/rate`: actualizar `monthly_rate` (> 0), registrar `updated_at` automáticamente; inexistente → `404`.
- `PATCH /suppliers/{id}/status`: permitir solo `active` o `suspended`; inválido → `422`; inexistente → `404`.
- `DELETE /suppliers/{id}`: eliminar del directorio; inexistente → `404`.

La suspensión no equivale a borrado: los proveedores suspendidos permanecen en el directorio para preservar el historial comercial. Las solicitudes válidas deben responder con códigos de éxito `200`/`201`, según operación.

## Seeder y persistencia

- Crear `services/api/seed.py` y una inicialización TinyDB documentada.
- Debe poder ejecutarse con `uv run seed` sin editar el código para cada ejecución.
- Insertar los 15 datos semilla exactamente una vez: comprobar duplicados antes de insertar; una segunda ejecución no debe duplicar registros.
- Informar en consola cuántos registros se insertaron (y, si es útil, cuántos ya existían).
- Verificar que TinyDB conserva los datos tras reiniciar la API.

## Requisitos funcionales del frontend

La interfaz debe mostrar el directorio consumiendo la API y los campos principales: nombre, país, categorías, tarifa mensual, moneda y estado.

- Filtrar por país y categoría sin recargar la página.
- Formulario para alta de proveedor; validar requeridos y mostrar errores devueltos por la API.
- Permitir cambiar tarifa y reflejar la respuesta de la API en la lista.
- Permitir activar/suspender cada proveedor desde un control visible.
- Diferenciar visualmente `active` y `suspended`.
- Destacar proveedores cuya renovación esté dentro de los próximos 60 días.

## Criterios de aceptación y evidencias de entrega

La evaluación debe demostrar:

1. El modelo coincide exactamente con el contexto; status, país/categorías, moneda y tarifa se validan antes de llegar a TinyDB.
2. `updated_at` lo genera el sistema y se actualiza con cambios de tarifa.
3. `uv run seed` funciona, carga los proveedores iniciales, es idempotente e informa el recuento.
4. La persistencia sobrevive a reiniciar el servidor.
5. Los filtros por país/categoría y las operaciones CRUD cumplen los códigos HTTP esperados.
6. La UI consume la API, filtra, permite crear/cambiar tarifa/cambiar estado y diferencia estados.
7. El código sigue la arquitectura del monorepo: backend dentro de `services/` e interfaz en `uis/` siguiendo las convenciones reales locales.

El README pide que el Pull Request de entrega incluya:

- Captura de la salida de `uv run seed`.
- Captura de respuesta de al menos un endpoint de filtro (Swagger UI o cliente HTTP).
- Captura del directorio web con al menos un filtro aplicado.

## Lista de comprobación previa a implementar

- [ ] Leer reglas y documentación actualizadas del monorepo, y revisar el estado de Git antes de editar.
- [ ] Confirmar la ruta de frontend adecuada debido a la discrepancia `uis/backoffice` vs. `uis/application/app/suppliers/` en el README.
- [ ] Confirmar cómo se expone el comando `uv run seed` con la configuración de proyecto que exista; no añadir scripts no usados/documentados.
- [ ] Mantener los nombres exactos del modelo, categorías, estados y valores semilla.
- [ ] Probar validaciones negativas (tarifa ≤ 0, categorías/estados inválidos, país/moneda inconsistente).
- [ ] Probar repetición del seeder, persistencia tras reinicio y respuestas `404`/`422`.
- [ ] No almacenar credenciales o tokens en el repositorio.
