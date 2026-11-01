# Auditoría de Rendimiento Frontend — Nexova

Documento de auditoría inicial para el proyecto **Frontend Performance Audit / Auditoría de Rendimiento Frontend** de 4Geeks Academy (cohorte *Architecture optimization*, tarea `1008341`, slug `ai-eng-performance-web-vitals`).

---

## 1. Registro de Condiciones del Entorno y Metodología

Para garantizar reproducibilidad y evitar ruido o variaciones de desarrollo (HMR, dev-servers), las pruebas se ejecutaron sobre las aplicaciones servidas en **modo producción** estático:

- **Fecha de medición inicial:** 1 de Noviembre de 2026.
- **Entorno de ejecución:** Windows 10/11 x64, Node.js `v24.18.0`.
- **Motor de auditoría:** Google Lighthouse CLI `v13.6.0`.
- **Navegador:** Google Chrome `v145.0` (`--headless=new --no-sandbox`).
- **Servidores de producción locales:**
  - Servidor estático Node.js de producción dedicado ([`scripts/static-server.mjs`](./scripts/static-server.mjs)) con cabeceras HTTP de producción (`Cache-Control: public, max-age=0, must-revalidate` y MIME types estrictos).
  - **Website corporativo:** `http://localhost:5500` (mapeado a `uis/website/`).
  - **Backoffice de talento y operaciones:** `http://localhost:5502` (mapeado a `uis/backoffice/`).
- **Pipeline automatizado de auditoría:** [`scripts/run-audit.mjs`](./scripts/run-audit.mjs).
- **Evidencias generadas:** Informes `.report.html`, `.report.json` y capturas de pantalla de alta resolución `.png` versionadas en [`audit/before/`](./audit/before/).

---

## 2. Resultados de la Línea Base (Medición Inicial)

A continuación se presentan los resultados numéricos oficiales consolidados de las 5 configuraciones evaluadas:

### 2.1. Puntuaciones Lighthouse (0 – 100)

| Aplicación / Vista | Ruta evaluada | Viewport / Preset | Performance | Accessibility | Best Practices | SEO |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Website (Home)** | `http://localhost:5500/index.html` | Móvil (Mobile) | **100** | **100** | **100** | **100** |
| **Website (Home)** | `http://localhost:5500/index.html` | Escritorio (Desktop) | **99** | **100** | **100** | **100** |
| **Website (Application)** | `http://localhost:5500/application.html` | Escritorio (Desktop) | **100** | **100** | **100** | **100** |
| **Backoffice (Index / Dashboard)** | `http://localhost:5502/index.html` | Escritorio (Desktop) | **100** | **96** | **96** | **60** |
| **Backoffice (Inventario / Catálogo)** | `http://localhost:5502/inventory.html` | Escritorio (Desktop) | **100** | **100** | **96** | **90** |

---

### 2.2. Métricas Clave de Core Web Vitals y Rendimiento

| Aplicación / Vista | Viewport | FCP (First Contentful Paint) | LCP (Largest Contentful Paint) | CLS (Cumulative Layout Shift) | TBT (Total Blocking Time) | Speed Index |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Website (Home)** | Mobile | 1.5 s | 1.5 s | 0.000 | 0 ms | 1.5 s |
| **Website (Home)** | Desktop | 0.5 s | 0.9 s | 0.000 | 0 ms | 0.5 s |
| **Website (Application)** | Desktop | 0.5 s | 0.5 s | 0.040 | 0 ms | 0.5 s |
| **Backoffice (Index)** | Desktop | 0.5 s | 0.8 s | 0.001 | 0 ms | 0.5 s |
| **Backoffice (Inventory)** | Desktop | 0.5 s | 0.7 s | 0.001 | 0 ms | 0.5 s |

---

## 3. Diagnóstico Técnico y Análisis de Causa Raíz

A pesar de las puntuaciones iniciales elevadas proporcionadas por la naturaleza estática del código, las auditorías de Lighthouse revelaron oportunidades y diagnósticos de impacto real en la experiencia de usuario y eficiencia de red:

### 3.1. Oportunidad Crítica de Optimización de Imágenes (Website Hero)
- **Ubicación:** `uis/website/assets/img/nexova_hero_image_1784574586596.png` en `uis/website/index.html`.
- **Diagnóstico Lighthouse:** `[image-delivery-insight] Improve image delivery`.
- **Ahorro potencial medido:** **459 KiB** en escritorio y **433 KiB** en móvil.
- **Causa raíz:** La imagen hero se distribuye en formato PNG sin compresión con un peso de **501.3 KiB**. A pesar de contar con atributos `fetchpriority="high"` y `decoding="async"`, el navegador se ve obligado a descargar medio megabyte sobre conexiones móviles y perfiles de red lentos, lo cual eleva el coste de transferencia e incrementa el LCP.
- **Impacto:** Alto en redes móviles 3G/4G con pérdida de paquetes o alta latencia.
- **Plan de corrección:** Convertir la imagen a formatos modernos y altamente comprimidos (**WebP** y **AVIF**) manteniendo fidelidad visual, sirviendo una etiqueta `<picture>` responsiva con `<source type="image/webp">` y fallback retrocompatible al PNG optimizado.

### 3.2. Bloqueo de Renderizado por Fuentes Externas (Render-Blocking Resources)
- **Ubicación:** `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@...&display=swap" />` tanto en `uis/website/index.html` como en `uis/backoffice/index.html`.
- **Diagnóstico Lighthouse:** `[render-blocking-insight] Render-blocking requests`.
- **Ahorro potencial medido:** Hasta **750 ms** en móvil y **270 ms** en escritorio.
- **Causa raíz:** Las fuentes externas de Google Fonts dependen de una cadena de resolución DNS y negociación TLS contra dominios de terceros (`fonts.googleapis.com` y `fonts.gstatic.com`). Aunque existe `rel="preconnect"`, el stylesheet externo de Google Fonts bloquea el renderizado inicial del árbol DOM.
- **Plan de corrección:** Reorganizar la prioridad de carga, verificar la inclusión de `display=swap` y optimizar la precarga de la tipografía crítica.

### 3.3. Accesibilidad en Backoffice (`uis/backoffice/index.html`)
- **Ubicación:** `uis/backoffice/index.html` (score de Accesibilidad: **96**).
- **Diagnóstico Lighthouse:**
  - `[color-contrast]`: Ciertos textos secundarios (etiquetas en `eyebrow`, subtítulos en gris) presentan un ratio de contraste inferior a 4.5:1 exigido por WCAG 2.1 AA.
  - `[label-content-name-mismatch]`: Ciertos botones interactivos no exponen un nombre accesible idéntico al texto visible.
- **Plan de corrección:** Ajustar variables CSS de color para garantizar ratios ≥ 4.5:1 en modo claro y asegurar nombres accesibles explícitos con `aria-label` descriptivos.

### 3.4. SEO y Metadatos de Navegación
- **Ubicación:** `uis/backoffice/inventory.html` (score SEO: **90**) e `index.html` (score SEO: **60**).
- **Diagnóstico Lighthouse:**
  - En `inventory.html`, falta la etiqueta `<meta name="description">`.
  - En `index.html`, la puntuación reducida de 60 se debe a la etiqueta intencionada `<meta name="robots" content="noindex, nofollow" />`.
- **Justificación de aplicabilidad:** Para una intranet y panel operativo privado, la directiva `noindex, nofollow` es una **buena práctica de seguridad y privacidad**. El score 60 no representa una degradación técnica, sino el comportamiento esperado de una aplicación no indexable. Se subsanará la meta descripción en `inventory.html`.

---

## 4. Análisis de Duplicación de Código y Candidatos a Refactorización

En cumplimiento con la especificación de 4Geeks Academy y la guía de auditoría, se examinó la arquitectura del repositorio para identificar redundancias estructurales y proponer abstracciones funcionales reutilizables.

### Caso 1: Rail de Navegación y Shell de la Aplicación en Backoffice
- **Archivos y ubicaciones observadas:**
  - `uis/backoffice/index.html` (líneas 27–104)
  - `uis/backoffice/inventory.html` (líneas 18–20: marcado con comentario placeholder `<!-- Re‑use the same rail navigation as index.html (omitted for brevity) -->`)
  - `uis/backoffice/inventory-forms.html`
  - `uis/backoffice/order-history.html`
- **Problema de duplicación:**
  Cada página del backoffice repite (o en el caso de `inventory.html`, omitió por placeholder) más de 80 líneas de marcado HTML idéntico correspondiente al rail de navegación lateral (`<aside class="rail">`), los enlaces a las 9 secciones, el footer de estado local y la cabecera `<header class="topbar">`.
- **Riesgo:**
  Inconsistencia funcional y visual. Cuando se añade una nueva vista (como Catálogo o Historial), los enlaces deben replicarse manualmente en cada archivo HTML. Cualquier omisión genera navegación rota entre páginas.
- **Propuesta de extracción reutilizable:**
  Crear un Web Component vanilla estandarizado `<backoffice-nav current-page="..."></backoffice-nav>` o un script modular compartido [`uis/backoffice/shared-nav.js`](./uis/backoffice/shared-nav.js) que inyecte de forma reactiva y accesible el rail completo, gestione la clase `is-current` y el atributo `aria-current="page"`, y centralice la barra de estado de autenticación.
- **Riesgo y mitigación:**
  Evitar el parpadeo de contenido no estilizado (FOUC) aplicando dimensiones CSS reservadas para el rail (`width: 260px`).

---

### Caso 2: Capa Cliente HTTP y Parseo Centralizado de Errores de API
- **Archivos y ubicaciones observadas:**
  - `uis/backoffice/suppliers.js` (líneas 10–55)
  - `uis/backoffice/incidents.js` (líneas 20–80)
  - `uis/backoffice/inventory-api.js` (líneas 1–340)
- **Problema de duplicación:**
  Tanto `suppliers.js` como `incidents.js` implementan su propia lógica dispersa de resolución de URL base (`http://localhost:8000` hardcoded o deducido), construcción de headers `Authorization: Bearer`, manejo de estados de carga y formateo artesanal de errores 4xx/5xx de FastAPI (`detail` en arrays u objetos). Paralelamente, `inventory-api.js` implementó una clase completa `InventoryApiClient` con manejo sanitizado de `ApiError`.
- **Riesgo:**
  Tratamiento heterogéneo de errores (unos muestran JSON crudo si la API devuelve una estructura Pydantic inesperada, otros alertan en consola o fallan silenciosamente sin refrescar tokens ni manejar 401).
- **Propuesta de extracción reutilizable:**
  Estandarizar un helper o módulo compartido de utilidades cliente (o extender `inventory-api.js` como cliente común del backoffice) para que todas las llamadas de operaciones consuman el mismo interceptor de tokens y el mismo formateador seguro de mensajes de error.

---

## 5. Plan de Intervenciones Dirigidas (Etapas 3 y 4)

1. **Sitio Público (`uis/website/`)**:
   - Generar formato WebP comprimido de alta fidelidad para `nexova_hero_image_1784574586596.png` reduciendo el peso de ~501 KB a < 70 KB (>85% de reducción de bytes transferidos).
   - Actualizar `uis/website/index.html` con `<picture>` para soportar WebP manteniendo fallback PNG.
   - Optimizar directivas de fuentes y enlaces de precarga.
2. **Backoffice (`uis/backoffice/`)**:
   - Implementar e integrar el componente compartido de navegación [`uis/backoffice/shared-nav.js`](./uis/backoffice/shared-nav.js) en `index.html` e `inventory.html`.
   - Corregir el contraste en elementos de texto y asegurar nombres accesibles en botones.
   - Añadir la meta descripción en `inventory.html`.
3. **Validación**:
   - Re-auditar en la Etapa 5 bajo idénticas condiciones para registrar la mejora medible en `audit/after/` y consolidar el `REPORT.md`.
