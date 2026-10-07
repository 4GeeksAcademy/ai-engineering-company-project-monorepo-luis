# Nexova — Analizador de Incidencias: Informe de Entrega y Documentación

Este documento resume la implementación del proyecto **Analizador de Incidencias — Script y Panel de Control** en el monorepo de Nexova, cumpliendo con los criterios de evaluación de 4Geeks Academy.

---

## 1. Arquitectura y Componentes Desarrollados

Siguiendo el principio de diseño *"Una lógica, dos consumidores"*:

1. **Librería Compartida (`packages/incident_analyzer/`)**:
   - `models.py`: Modelos de datos (`IncidentAnalysisResult`, `SatisfactionStats`, `RowError`).
   - `validator.py`: Validador de esquemas y reglas de negocio. **Garantía absoluta de privacidad**: jamás se registran, exponen ni exportan direcciones de correo individuales (`customer_email`).
   - `analyzer.py`: Motor determinista en streaming para procesamiento de grandes volúmenes con bajo consumo de memoria.
   - `exporter.py`: Generador de `results.csv` con estructura agregada (una métrica por fila).
2. **Interfaz de Línea de Comandos (`scripts/analyze.py`)**:
   - Script CLI con argumentos configurables (`--export`, `--no-export`, `-o`).
   - Salida en consola formateada con separadores y porcentajes.
   - Soporte nativo para codificación UTF-8 en consolas Windows (`cp1252`).
3. **Servicio Backend API (`services/api/`)**:
   - Aplicación central en FastAPI con middleware CORS.
   - `POST /api/incidents/analyze`: Análisis multipart de CSV con control de tamaño y validación de tipos.
   - `GET /api/incidents/results/export`: Descarga de `results.csv` correspondiente al último análisis.
   - `GET /health`: Endpoint de estado de salud.
4. **Panel Web (`uis/backoffice/`)**:
   - Pestaña "05 Incidencias" en el menú de navegación del backoffice.
   - Drag & drop de archivos CSV con validación en cliente.
   - Renderizado reactivo y accesible de métricas (KPIs, categorías, estados, satisfacción y motivos de descarte).
   - Botón directo para descargar el resumen `results.csv`.

---

## 2. Nota sobre la Discrepancia del Dataset (100 vs. 1.000 filas)

- **Contexto**: El enunciado general menciona en una línea un archivo de 1.000 filas. Sin embargo, el fixture provisto para Nexova (`incidents-nexova.csv`), las métricas esperadas y los criterios de evaluación corresponden a una muestra mensual de **100 registros** (96 válidos y 4 inválidos).
- **Criterio aplicado**: Se tomó el fixture oficial de 100 filas como baseline determinista para todas las pruebas y validaciones. Si en el futuro 4Geeks proporciona un conjunto de datos ampliado de 1.000 filas, la arquitectura en streaming de `packages/incident_analyzer` lo procesará sin requerir cambios de código.

---

## 3. Salida de Consola con el Fixture Oficial (Evidencia CLI)

Ejecución de `python scripts/analyze.py data/raw/incidents-nexova.csv`:

```text
============================================================
  NEXOVA — SUPPORT TICKET ANALYSIS
  Source file: incidents-nexova.csv
============================================================

TOTAL RECORDS IN FILE .......... 100
  ├─ Valid records ................ 96
  └─ Invalid / incomplete .......... 4

INVALID RECORDS BREAKDOWN
  ├─ Missing client_company ............. 1
  ├─ Invalid or missing category ........ 1
  ├─ Invalid or missing email ........... 1
  └─ Closed ticket, no score ............ 1

BREAKDOWN BY CATEGORY (valid records)
  ├─ TECHNICAL .......................... 28  (29.2%)
  ├─ BILLING ............................ 18  (18.8%)
  ├─ ACCESS ............................. 21  (21.9%)
  ├─ HR_QUERY ........................... 17  (17.7%)
  └─ COMPLAINT .......................... 12  (12.5%)

BREAKDOWN BY STATUS (valid records)
  ├─ OPEN ............................... 27  (28.1%)
  ├─ CLOSED ............................. 56  (58.3%)
  └─ DISCARDED .......................... 13  (13.5%)

SATISFACTION INDEX (closed tickets)
  Scored tickets: 56 of 56
  Average score: 3.84 / 5.00
  ├─ Score 1 (Very dissatisfied) ........  2
  ├─ Score 2 (Dissatisfied) .............  5
  ├─ Score 3 (Neutral) .................. 10
  ├─ Score 4 (Satisfied) ................ 22
  └─ Score 5 (Very satisfied) ........... 17

============================================================
Export results to CSV? [y / n]:
```

---

## 4. Instrucciones para Ejecución Local

### Ejecutar la API Backend (FastAPI):
```bash
uvicorn services.api.main:app --reload --port 8000
```
- Documentación interactiva Swagger: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

### Ejecutar el Panel Web (Backoffice):
Desde la raíz del monorepo:
```bash
npx --yes serve uis/backoffice -l 5502
```
- Abrir en el navegador: http://localhost:5502
- Navegar a la sección **05 Incidencias** y cargar `data/raw/incidents-nexova.csv`.

---

## 5. Ejecución de Pruebas Automatizadas

```bash
# Pruebas del motor compartido y del script CLI
python -m unittest discover -s packages/incident_analyzer/tests -v

# Pruebas de integración de la API
python -m unittest discover -s services/api/tests -v
```

**Resultado actual**: 15 pruebas pasando exitosamente (0 fallos, 0 errores).

---

## 6. Auditoría de Seguridad y Privacidad

- [x] Ningún correo electrónico (`customer_email`) se imprime en consola o logs.
- [x] Ningún correo electrónico se incluye en la respuesta JSON de análisis o de error.
- [x] Ningún correo electrónico o dato personal se incluye en el archivo `results.csv`.
- [x] No se envían datos a APIs externas, servicios de IA ni telemetría de terceros.
- [x] `results.csv` y archivos temporales están incluidos en `.gitignore`.
