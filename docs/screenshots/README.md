# Capturas de la entrega Nexova

Evidencia visual generada localmente con Playwright 1.50.1 y Chromium para la revisión del hito. No contiene registros de candidatos ni información personal.

- `website-desktop.png`: landing pública a 1440 × 900.
- `website-mobile.png`: landing pública a 390 × 844.
- `backoffice-desktop.png`: panel interno a 1440 × 900.
- `backoffice-mobile.png`: panel interno a 390 × 844.
- `suppliers-desktop.png`: directorio filtrado por España y portales de empleo a 1440 × 900; usa un proveedor ficticio de prueba y no datos del seed.
- `suppliers-mobile.png`: el mismo estado del directorio a 390 × 844; comprobado sin overflow horizontal.
- `supplier-filter-api.png`: respuesta real de Swagger UI para `country=Spain` y `category=background_check`; `200` con lista vacía, sin datos de proveedores.
- `supplier-seed-output.png`: salida real de dos ejecuciones de `uv run seed` en una TinyDB temporal aislada; muestra 15 inserciones y 0 duplicados.

Las capturas representan el estado de las páginas servidas localmente el 25 de septiembre de 2026. No sustituyen pruebas de validación funcional del formulario.

Las evidencias del directorio se generaron el 13 de octubre de 2026. Las capturas de UI usan un fixture sintético; el flujo de alta, actualización de tarifa y suspensión se probó contra la API real con registros temporales eliminados al terminar.
