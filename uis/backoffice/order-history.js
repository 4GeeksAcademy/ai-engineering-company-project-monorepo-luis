// order-history.js – renders a read‑only table of inventory orders (inbound & outbound)

/**
 * Map order type to a human readable label.
 * @param {string} type – e.g., "inbound" or "outbound"
 */
function formatType(type) {
  if (!type) return '';
  return type === 'inbound' ? 'Entrada' : type === 'outbound' ? 'Salida' : type;
}

/**
 * Render the orders table.
 * @param {Array} orders
 */
function renderTable(orders) {
  const container = document.getElementById('history-container');
  container.innerHTML = '';

  const table = document.createElement('table');
  table.className = 'catalog-table'; // reuse catalog table style
  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  const headers = [
    'Tipo',
    'Activo',
    'SKU',
    'Cantidad',
    'Oficina',
    'Detalle', // proveedor o asignado
    'Fecha',
    'Autor'
  ];
  headers.forEach((h) => {
    const th = document.createElement('th');
    th.textContent = h;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  orders.forEach((o) => {
    const tr = document.createElement('tr');
    // Tipo
    const tdType = document.createElement('td');
    tdType.textContent = formatType(o.movement_type);
    tr.appendChild(tdType);
    // Activo (nombre)
    const tdName = document.createElement('td');
    tdName.textContent = o.asset_name ?? '';
    tr.appendChild(tdName);
    // SKU
    const tdSku = document.createElement('td');
    tdSku.textContent = o.asset_sku ?? '';
    tr.appendChild(tdSku);
    // Cantidad
    const tdQty = document.createElement('td');
    tdQty.textContent = o.quantity ?? '';
    tr.appendChild(tdQty);
    // Oficina
    const tdOffice = document.createElement('td');
    tdOffice.textContent = o.office ?? '';
    tr.appendChild(tdOffice);
    // Detalle (proveedor o asignado)
    const tdDetail = document.createElement('td');
    if (o.movement_type === 'inbound') {
      tdDetail.textContent = o.supplier ?? '';
    } else {
      tdDetail.textContent = o.assigned_to ?? '';
    }
    tr.appendChild(tdDetail);
    // Fecha
    const tdDate = document.createElement('td');
    const date = o.created_at ? new Date(o.created_at) : null;
    tdDate.textContent = date ? date.toLocaleString() : '';
    tr.appendChild(tdDate);
    // Autor
    const tdUser = document.createElement('td');
    tdUser.textContent = o.user_uuid ?? '';
    tr.appendChild(tdUser);

    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  container.appendChild(table);
}

/**
 * Load orders from the API and render.
 */
async function loadAndRender() {
  const feedback = document.getElementById('history-feedback');
  feedback.hidden = true;
  try {
    const orders = await inventoryApi.getOrders(); // expects array
    renderTable(orders);
  } catch (err) {
    feedback.textContent = err.message || 'Error al cargar el historial de órdenes.';
    feedback.hidden = false;
  }
}

// Init on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', loadAndRender);
} else {
  loadAndRender();
}
