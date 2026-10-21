# Capturas de la entrega Nexova

Evidencia visual generada localmente para la revisión del proyecto. No contiene registros de candidatos ni información personal.

- `website-desktop.png`: landing pública a 1440 × 900.
- `website-mobile.png`: landing pública a 390 × 844.
- `backoffice-desktop.png`: panel interno a 1440 × 900.
- `backoffice-mobile.png`: panel interno a 390 × 844.
- `suppliers-desktop.png`: directorio filtrado por España y portales de empleo a 1440 × 900; usa un proveedor ficticio de prueba y no datos del seed.
- `suppliers-mobile.png`: el mismo estado del directorio a 390 × 844; comprobado sin overflow horizontal.
- `supplier-filter-api.png`: respuesta real de Swagger UI para `country=Spain` y `category=background_check`; `200` con lista vacía, sin datos de proveedores.
- `supplier-seed-output.png`: salida real de dos ejecuciones de `uv run seed` en una TinyDB temporal aislada; muestra 15 inserciones y 0 duplicados.

### Gestor Centralizado de Incidencias (Entrega Oficial)

- `incident-form-validation.png`: formulario de registro en `uis/backoffice` mostrando errores de validación en cliente (campos obligatorios y mensajes legibles).
- `incident-list.png`: listado de incidencias con datos históricos del seed cargados, barra de filtros combinables y controles de ciclo de vida con transiciones válidas.
- `incident-summary.png`: panel de resumen de métricas operativas (`/api/incidents/summary`) con totales exactos por estado, categoría, origen y sede.
