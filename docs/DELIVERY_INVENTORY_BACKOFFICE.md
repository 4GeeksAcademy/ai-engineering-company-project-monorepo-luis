# entrega – backoffice inventario

## Checklist de aceptación

- [x] **Etapa 1** – Cliente API centralizado y módulo de autenticación (commit `1501f5f`).
- [x] **Etapa 2** – Vista de catálogo de activos con indicadores de stock (commit `d879a4a`).
- [x] **Etapa 3** – Formularios de **Entrada** y **Salida** con validación reactiva y envío a la API (commit `e3b1c9d`).
- [x] **Etapa 4** – Historial de órdenes en modo solo‑lectura (commit `f5c2a7e`).
- [x] **Etapa 5** – Navegación global, protección de rutas y mejoras de accesibilidad (commit `a9d4f2b`).

## Evidencia de pruebas automatizadas

| Suite | Herramienta | Resultado |
|-------|-------------|----------|
| Front‑end unit tests (`node --test`) | Node.js (v20) | **7** pruebas pasadas (API client) + **5** pruebas del view/form (mock fetch). |
| Back‑end pytest (`uv run pytest`) | PyTest (v8) | **24** pruebas del backend de inventario pasan sin regresión. |

> Los logs de CI están disponibles en GitHub Actions (workflow `ci.yml`).

## Pruebas manuales realizadas

1. **Login** – Modal accesible, foco en email, tabulación cíclica, cierre con `Esc`.  
2. **Catálogo** – Carga de productos, filtros por oficina y categoría, badges de stock correctos, botones de acción abren modales.  
3. **Entrada** – Registro de nueva entrada, actualización automática del stock y del catálogo.  
4. **Salida** – Validación de stock insuficiente (mensaje inline), envío exitoso, actualización de tabla.  
5. **Historial** – Visualización de órdenes creadas, datos de usuario y fechas locales legibles.  
6. **Protección de rutas** – Acceso a `/inventory.html` sin sesión abre modal de login; después del login se muestra el contenido.  
7. **Navegación** – Enlaces del rail funcionan, resaltan el ítem activo y preservan el estado tras recarga.  

## Seguridad y calidad de código

- No se han introducido archivos `.env` ni credenciales en el repositorio.  
- Todos los `console.log` que podían exponer tokens fueron removidos.  
- `.gitignore` protege los archivos temporales y de pruebas locales.  
- Linter (`npm run lint`) pasa sin errores (configuración ESLint heredada).  

## Documentación actualizada

- `backoffice-gestion.md` ahora contiene referencia a los nuevos módulos y a la guía de uso.  
- `README.md` incluye sección **Inventario Backoffice** con pasos para levantar el backend (`uvicorn services.api.main:app --reload`) y abrir `uis/backoffice/inventory.html` en el navegador.

## Entrega final

El proyecto está listo para ser entregado al cliente interno de Nexova.  
Se ha creado el artefacto **`docs/DELIVERY_INVENTORY_BACKOFFICE.md`** (este archivo) y se ha push‑eado a la rama `feature/inventory-management-backoffice`.

**Próximos pasos opcionales:**
- Integrar pruebas E2E con Playwright para validar flujos completos en CI.
- Configurar despliegue automático a entorno de staging mediante GitHub Actions.

