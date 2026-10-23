// inventory-view.js – renders the product catalog using the central inventoryApi

/**
 * Utility to create a badge element representing stock level.
 * @param {number} stock
 * @returns {HTMLSpanElement}
 */
function createStockBadge(stock) {
  const span = document.createElement('span');
  span.classList.add('stock-badge');
  span.textContent = stock;
  if (stock <= 5) {
    span.classList.add('stock-low'); // red
  } else if (stock <= 10) {
    span.classList.add('stock-medium'); // amber
  } else {
    span.classList.add('stock-high'); // green
  }
  return span;
}

/**
 * Render the product table inside #catalog-container.
 * @param {Array} products
 */
function renderTable(products) {
  const container = document.getElementById('catalog-container');
  container.innerHTML = '';

  const table = document.createElement('table');
  table.className = 'catalog-table';
  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  const headers = ['Nombre', 'SKU', 'Categoría', 'Oficina', 'Stock', 'Acciones'];
  headers.forEach((text) => {
    const th = document.createElement('th');
    th.textContent = text;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  products.forEach((p) => {
    const tr = document.createElement('tr');
    // Nombre
    const tdName = document.createElement('td');
    tdName.textContent = p.name ?? p.product_name ?? '';
    tr.appendChild(tdName);
    // SKU
    const tdSku = document.createElement('td');
    tdSku.textContent = p.sku ?? '';
    tr.appendChild(tdSku);
    // Categoría
    const tdCat = document.createElement('td');
    tdCat.textContent = p.category ?? '';
    tr.appendChild(tdCat);
    // Oficina
    const tdOffice = document.createElement('td');
    tdOffice.textContent = p.office ?? '';
    tr.appendChild(tdOffice);
    // Stock badge
    const tdStock = document.createElement('td');
    tdStock.appendChild(createStockBadge(p.current_stock ?? 0));
    tr.appendChild(tdStock);
    // Acciones
    const tdActions = document.createElement('td');
    const btnIn = document.createElement('button');
    btnIn.type = 'button';
    btnIn.className = 'action-btn inbound-btn';
    btnIn.textContent = 'Entrada';
    btnIn.dataset.sku = p.sku;
    const btnOut = document.createElement('button');
    btnOut.type = 'button';
    btnOut.className = 'action-btn outbound-btn';
    btnOut.textContent = 'Salida';
    btnOut.dataset.sku = p.sku;
    tdActions.appendChild(btnIn);
    tdActions.appendChild(document.createTextNode(' '));
    tdActions.appendChild(btnOut);
    tr.appendChild(tdActions);

    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  container.appendChild(table);
}

/**
 * Load products from the API, apply current filters and render.
 */
async function loadAndRender() {
  const feedback = document.getElementById('catalog-feedback');
  feedback.hidden = true;
  try {
    const products = await inventoryApi.getProducts();
    // Apply filters
    const office = document.getElementById('office-filter').value;
    const category = document.getElementById('category-filter').value;
    const filtered = products.filter((p) => {
      const officeMatch = office ? p.office === office : true;
      const catMatch = category ? p.category === category : true;
      return officeMatch && catMatch;
    });
    renderTable(filtered);
  } catch (err) {
    feedback.textContent = err.message || 'Error al cargar el catálogo.';
    feedback.hidden = false;
  }
}

/**
 * Populate filter dropdowns based on distinct values from the product list.
 */
async function populateFilters() {
  try {
    const products = await inventoryApi.getProducts();
    const officeSelect = document.getElementById('office-filter');
    const categorySelect = document.getElementById('category-filter');
    const offices = [...new Set(products.map((p) => p.office).filter(Boolean))];
    const categories = [...new Set(products.map((p) => p.category).filter(Boolean))];
    offices.forEach((o) => {
      const opt = document.createElement('option');
      opt.value = o;
      opt.textContent = o;
      officeSelect.appendChild(opt);
    });
    categories.forEach((c) => {
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      categorySelect.appendChild(opt);
    });
  } catch (_) {
    // ignore – filters will stay empty if API fails; loadAndRender will show error.
  }
}

/**
 * Initialise the view – called once DOM is ready.
 */
function init() {
  document.getElementById('office-filter').addEventListener('change', loadAndRender);
  document.getElementById('category-filter').addEventListener('change', loadAndRender);
  // Delegated click handling for action buttons
  document.getElementById('catalog-container').addEventListener('click', (e) => {
    if (e.target.matches('.inbound-btn')) {
      const sku = e.target.dataset.sku;
      // TODO: open inbound form (Etapa 3). For now just alert.
      alert(`Registrar entrada para SKU ${sku}`);
    } else if (e.target.matches('.outbound-btn')) {
      const sku = e.target.dataset.sku;
      // TODO: open outbound form (Etapa 3).
      alert(`Registrar salida para SKU ${sku}`);
    }
  });
  populateFilters().finally(loadAndRender);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
