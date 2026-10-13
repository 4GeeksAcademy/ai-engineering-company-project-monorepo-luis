# Nexova Backoffice

Panel interno de referencia para el contexto de negocio y las etapas del proceso de talento. Se mantiene separado del sitio público y del tracker de candidatos.

## Alcance de datos

- Las cifras aproximadas de plantilla y facturación y las líneas de negocio se transcriben de `CONTEXT.md`.
- Los nombres de las etapas se toman de `SPEC.md`.
- El directorio de proveedores consulta la API de operaciones; el resto de las cifras del panel sigue siendo contexto del proyecto y no una vista en tiempo real.
- El panel no consulta la API del tracker ni muestra registros personales de candidatos.
- El directorio muestra información comercial interna (tarifas, contactos y notas). Mantener API y panel en local/demo; no hay autenticación y CORS no la sustituye.

## Ejecutar localmente

Desde la raíz del monorepo:

```bash
npx --yes serve uis/backoffice -l 5502
```

Abrir http://localhost:5502. No usar el modo SPA; la app estática debe servir `index.html` en `/`.

## Analizador de incidencias (Outsourcing Helpdesk)

El panel incorpora una sección interactiva para cargar exportaciones CSV del servicio de helpdesk de Nexova (`/api/incidents/analyze`).

- **Carga de archivos**: Selector o drag & drop para archivos `.csv`.
- **Métricas visuales**: Visualización de total de registros, válidos, incompletos/inválidos, promedio de satisfacción con desglose de estrellas y distribución por categoría y estado.
- **Privacidad estricta**: Cero almacenamiento o renderizado de emails o datos sensibles de clientes en pantalla o consola.
- **Exportación**: Descarga directa de `results.csv` estructurado mediante el endpoint `/api/incidents/results/export`.

### Requisitos para el analizador

Asegúrate de que la API backend esté ejecutándose:
```bash
uvicorn services.api.main:app --port 8000
```

## Directorio de proveedores

La sección **Proveedores** consume `/api/suppliers` de la API local de FastAPI.

- Consulta todos los proveedores y aplica filtros de país y categoría sin recargar la página.
- Permite crear proveedores, actualizar tarifas y activar/suspender registros.
- Muestra errores de validación de la API y destaca renovaciones dentro de los próximos 60 días.
- Los datos semilla tienen fechas de renovación históricas; la vista no las modifica.
- El borrado está disponible en la API, pero no se ofrece como acción del backoffice.

Para cargar los datos iniciales, ejecutar desde `services/api/`:

```bash
uv run seed
```

## Validación

- Abrir `/` y comprobar la carga del panel.
- Revisar navegación interna, enlace al sitio público y enlace al tracker.
- Verificar que el directorio carga desde `/api/suppliers`; probar filtros conjuntos, alta, tarifa y cambio de estado con la API local iniciada.
- Comprobar la sección "Analizador de incidencias" cargando `data/raw/incidents-nexova.csv`.
- Comprobar el layout en viewport amplio y móvil, foco visible y contenido con zoom.
- Confirmar que el panel no renderiza nombres, correos, teléfonos ni otros datos personales.

No hay scripts propios de test, lint, typecheck o build porque esta app es estática y no añade un toolchain independiente.

