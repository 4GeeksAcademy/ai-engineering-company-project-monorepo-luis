# Carpeta `scripts`

Esta carpeta contiene **scripts auxiliares** del monorepo: automatizaciones de desarrollo, utilidades de mantenimiento, tareas repetitivas (setup, lint, migraciones, generación de datos, etc.) y tooling interno.

- **Propósito principal**: agrupar herramientas de soporte que no pertenecen a una app/agente/pipeline específico, pero facilitan el trabajo del equipo.
- **Recomendación**: documenta cada script (qué hace, parámetros, requisitos, ejemplos de uso) y procura que sean reproducibles (y seguros) en distintos entornos.

## `analyze.py` — Analizador de Incidencias

Herramienta de consola para analizar exportaciones CSV del servicio de helpdesk de Nexova. Calcula métricas de volumen, registros válidos/inválidos, distribución por categoría y puntuaciones de satisfacción sin exponer datos personales (PII).

### Uso

```bash
# Ejecutar análisis con el fixture oficial
python scripts/analyze.py data/raw/incidents-nexova.csv

# O desde dentro del directorio scripts/
cd scripts
python analyze.py incidents-nexova.csv
```

### Opciones
- `--export`: Exporta automáticamente el resumen a `results.csv` sin preguntar de forma interactiva.
- `--no-export`: Omite la exportación sin preguntar.
- `-o <ruta>`, `--output <ruta>`: Especifica la ruta destino para el archivo CSV de exportación.

### Pruebas

```bash
python -m unittest discover -s packages/incident_analyzer/tests -v
```
