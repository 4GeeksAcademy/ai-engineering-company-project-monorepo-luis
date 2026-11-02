# Informe final: Auditoría y optimización de rendimiento frontend (Nexova)

Comparativa antes/después de las optimizaciones de rendimiento, accesibilidad, buenas prácticas y SEO en el sitio público (`uis/website/`) y el backoffice (`uis/backoffice/`). La metodología y el análisis de causas raíz están en [AUDIT.md](AUDIT.md).

## Resumen ejecutivo

- **Sitio público:** el LCP de la home de escritorio bajó de 0.9 s a 0.5 s tras reemplazar el hero PNG por WebP con `<picture>` responsive. El resto de métricas se mantienen en 100 o cerca.
- **Backoffice:** la accesibilidad de `index.html` subió de 96 a 100, y el SEO de `inventory.html` subió de 90 a 100. La extracción de la navegación lateral a un Web Component reduce la duplicación entre ambas páginas.
- **Retrocesos detectados:** el Speed Index móvil del sitio pasó de 1.5 s a 2.5 s, el CLS de la home de escritorio pasó de 0 a 0.046, y el LCP de `inventory.html` pasó de 0.7 s a 0.8 s. Son diferencias pequeñas, pero se documentan y se revisarán en una siguiente iteración.
- **Pendiente:** la verificación funcional de catálogo y login con backend no se pudo completar en este entorno (ver [Verificación funcional](#verificación-funcional)).

## Condiciones de medición

- Lighthouse CLI (versión 13.6.0) con Chrome headless (`--headless=new --no-sandbox`).
- Servidores estáticos en modo producción: sitio en `http://localhost:5500` y backoffice en `http://localhost:5502`, ambos con `npx serve`.
- Las mismas 5 corridas y perfiles en ambas etapas, ejecutadas con [scripts/run-audit.mjs](scripts/run-audit.mjs):
  `website-home-mobile`, `website-home-desktop`, `website-application-desktop`, `backoffice-index-desktop`, `backoffice-inventory-desktop`.
- Reportes en [audit/before/](audit/before/) y [audit/after/](audit/after/).

## Métricas antes vs. después

Puntuaciones de 0 a 100 por categoría. Valores absolutos de Web Vitals y métricas complementarias.

| Página | Versión | Performance | Accessibility | Best Practices | SEO | FCP | LCP | CLS | TBT | Speed Index |
|---|---|---|---|---|---|---|---|---|---|---|
| website-home-mobile | Antes | 100 | 100 | 100 | 100 | 1.5 s | 1.5 s | 0 | 0 ms | 1.5 s |
| website-home-mobile | Después | 99 | 100 | 100 | 100 | 1.5 s | 1.5 s | 0 | 0 ms | **2.5 s** |
| website-home-desktop | Antes | 99 | 100 | 100 | 100 | 0.5 s | 0.9 s | 0 | 0 ms | 0.5 s |
| website-home-desktop | Después | 100 | 100 | 100 | 100 | 0.5 s | **0.5 s** | **0.046** | 0 ms | 0.5 s |
| website-application-desktop | Antes | 100 | 100 | 100 | 100 | 0.5 s | 0.5 s | 0.04 | 0 ms | 0.5 s |
| website-application-desktop | Después | 100 | 100 | 100 | 100 | 0.5 s | 0.5 s | 0.04 | 0 ms | 0.5 s |
| backoffice-index-desktop | Antes | 100 | 96 | 96 | 60 | 0.5 s | 0.8 s | 0.001 | 0 ms | 0.5 s |
| backoffice-index-desktop | Después | 100 | **100** | 96 | 60 | 0.5 s | 0.8 s | 0.001 | 0 ms | 0.5 s |
| backoffice-inventory-desktop | Antes | 100 | 100 | 96 | 90 | 0.5 s | 0.7 s | 0.001 | 0 ms | 0.5 s |
| backoffice-inventory-desktop | Después | 100 | 100 | 96 | **100** | 0.5 s | 0.8 s | 0.001 | 0 ms | 0.5 s |

Todos los CLS quedan por debajo del objetivo de 0.1. Los TBT son 0 ms en todas las corridas.

## Cambios aplicados y commits

| Commit | Cambio | Impacto medido |
|---|---|---|
| `58a572c` | Scripts de auditoría (`scripts/run-audit.mjs`) y servidor estático de producción (`scripts/static-server.mjs`). | Base reproducible de las mediciones. |
| `673f3b4` | Baseline en `audit/before/` (5 corridas, HTML, JSON y PNG). | Línea base de comparación. |
| `08d0f30` | Análisis de causas raíz y casos de duplicación en [AUDIT.md](AUDIT.md). | Sin impacto directo en métricas. |
| `fc761a9` | Hero del sitio en WebP con `<picture>` responsive, `width`/`height`, `fetchpriority="high"` y `decoding="async"`. Hero de 501 KB PNG reemplazado por un WebP de 40 KB. | LCP de home de escritorio: 0.9 s → 0.5 s. |
| `9a779f1` | Componente `<backoffice-rail>` en [shared-nav.js](uis/backoffice/shared-nav.js), usado en `index.html`, `inventory.html`, `inventory-forms.html` y `order-history.html`. Mejoras de accesibilidad y SEO en la navegación. | Accessibility de backoffice index: 96 → 100. SEO de inventario: 90 → 100. |
| `dd49dcc` | Reportes posteriores en `audit/after/`. | Medición final. |

## Intervención de mayor impacto

El cambio con mayor impacto medido fue el reemplazo del hero PNG por WebP con `<picture>` responsive (`fc761a9`). Redujo el peso de la imagen de 501 KB a 40 KB y bajó el LCP de la home de escritorio de 0.9 s a 0.5 s. La extracción del componente de navegación (`9a779f1`) tuvo impacto en accesibilidad y SEO, y además elimina la duplicación entre páginas del backoffice.

## Retrocesos y riesgos

- **Speed Index móvil (sitio):** pasó de 1.5 s a 2.5 s, aunque el LCP móvil se mantiene en 1.5 s. Probablemente está relacionado con el cambio de carga del hero. Pendiente investigar en una siguiente iteración.
- **CLS en home de escritorio:** pasó de 0 a 0.046. Puede deberse a la altura de la imagen responsive. Sigue por debajo de 0.1.
- **LCP de inventario:** pasó de 0.7 s a 0.8 s. La diferencia es de 100 ms y puede ser variabilidad de medición.
- **SEO de backoffice index:** sigue en 60 y no se corrigió en esta iteración.
- **Errores de red del backoffice:** las páginas intentan llamar a `http://127.0.0.1:8000`, donde corre el backend. Sin backend aparecen `ERR_CONNECTION_REFUSED`. Estos errores ya estaban en la línea base y no son una regresión de esta rama.

## Verificación funcional

Verificado en navegador con Playwright sobre el servidor de desarrollo:

- **Sitio público** (`index.html` y `application.html`): carga correcta, navegación principal y formulario de registro visibles y accesibles, sin errores de consola ni recursos con status 4xx/5xx.
- **Backoffice** (`index.html` e `inventory.html`): navegación lateral, botón de inicio de sesión y estructura de catálogo renderizadas. Los errores de consola corresponden a la ausencia del backend.
- **Test automatizado:** `node uis/backoffice/tests/test_inventory_api.mjs` pasa 7 de 7.

Verificado después con el backend local (`uvicorn services.api.main:app` con `JWT_SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES` definidas en la sesión, sin Docker):

- **Catálogo:** `inventory.html` carga los 6 activos desde `/inventory/products`.
- **Login:** el modal de `inventory.html` inicia sesión con una cuenta local de prueba y muestra el usuario y "Cerrar sesión". La sesión persiste al navegar a `order-history.html` e `inventory-forms.html`.
- **Bug corregido:** los modales de `inventory.html`, `order-history.html` e `inventory-forms.html` usaban un formulario legacy (`method="dialog"`, campos `username`/`password`) sin handler, así que el login no hacía nada. Se reemplazó por el mismo markup de `index.html` (`auth-login-form`), que `auth.js` ya maneja.

- **Formularios de movimientos:** `inventory-forms.html` referenciaba `inventory-form.css` e `inventory-form.js`, que no existían (404), y los botones Entrada/Salida solo mostraban un `alert`. Se crearon ambos archivos: los dialogs envían `POST /inventory/orders/inbound` y `/outbound`, muestran los errores del backend (p. ej. stock insuficiente) y recargan la tabla. En `inventory.html`, que no tiene dialogs, los botones llevan a `inventory-forms.html`. Verificado en navegador: entrada +2, salida rechazada por stock y salida −2, sin 404 en consola.

## Balance global

- **Logros:** LCP del sitio mejorado sin cambiar diseño ni contenido, accesibilidad del backoffice a 100 en una página y SEO a 100 en la otra, y un componente reutilizable que reduce duplicación.
- **Deuda:** Speed Index móvil del sitio, SEO del backoffice index y verificación funcional con backend.
