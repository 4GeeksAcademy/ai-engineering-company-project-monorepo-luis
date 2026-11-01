/**
 * Nexova Backoffice — Componente Compartido Reutilizable de Navegación (Web Component)
 * 
 * Centraliza la estructura del rail lateral de navegación para evitar duplicación
 * de código entre las vistas operativas (Dashboard, Catálogo, Movimientos e Historial).
 * Gestiona de forma accesible los enlaces activos (aria-current="page") y el contraste.
 */
class BackofficeRail extends HTMLElement {
  connectedCallback() {
    const current = this.getAttribute('current') || 'resumen';

    const navSections = [
      {
        heading: 'ESPACIO DE TRABAJO',
        items: [
          { id: 'resumen', index: '01', label: 'Resumen', href: './#resumen' },
          { id: 'talento', index: '02', label: 'Proceso de talento', href: './#talento' },
          { id: 'servicios', index: '03', label: 'Líneas de negocio', href: './#servicios' },
          { id: 'ubicaciones', index: '04', label: 'Ubicaciones', href: './#ubicaciones' },
          { id: 'proveedores', index: '05', label: 'Proveedores', href: './#proveedores' },
          { id: 'incidencias', index: '06', label: 'Incidencias', href: './#incidencias' },
        ],
      },
      {
        heading: 'INVENTARIO',
        items: [
          { id: 'catalogo', index: '07', label: 'Catálogo', href: './inventory.html' },
          { id: 'movimientos', index: '08', label: 'Movimientos', href: './inventory-forms.html' },
          { id: 'historial', index: '09', label: 'Historial', href: './order-history.html' },
        ],
      },
    ];

    let navMarkup = '';
    for (const sec of navSections) {
      navMarkup += `<p class="nav-heading">${sec.heading}</p>`;
      for (const item of sec.items) {
        const isCurrent = item.id === current;
        const currentClass = isCurrent ? ' is-current' : '';
        const currentAttr = isCurrent ? ' aria-current="page"' : '';
        navMarkup += `
          <a class="nav-link${currentClass}" href="${item.href}"${currentAttr}>
            <span class="nav-index">${item.index}</span>
            ${item.label}
          </a>`;
      }
    }

    this.innerHTML = `
      <aside class="rail" aria-label="Navegación del backoffice">
        <a class="brand" href="./" aria-label="Nexova PEOPLE OPERATIONS, resumen del backoffice">
          <span class="brand-mark" aria-hidden="true">N</span>
          <span class="brand-name">Nexova<span>PEOPLE OPERATIONS</span></span>
        </a>

        <nav class="primary-nav" aria-label="Principal">
          ${navMarkup}
        </nav>

        <div class="rail-footer">
          <span class="rail-status"><span aria-hidden="true"></span> Entorno local</span>
          <p>Directorio comercial<br />Solo demo/local</p>
        </div>
      </aside>
    `;
  }
}

if (!customElements.get('backoffice-rail')) {
  customElements.define('backoffice-rail', BackofficeRail);
}
