// inventory-form.js – inbound/outbound movement dialogs for inventory-forms.html

// Must match OfficeType in services/api/schemas.py
const OFFICES = ['Valencia', 'Miami'];

let currentAssetId = null;
let formVersion = 0;
let supplierLoad = 0;

function getParts(mode) {
  const dialog = document.getElementById(`${mode}-dialog`);
  const form = document.getElementById(`${mode}-form`);
  return {
    dialog,
    form,
    feedback: form.querySelector('.form-feedback'),
    submit: form.querySelector('.form-submit'),
  };
}

function fillOffices(select, selected) {
  select.innerHTML = '<option value="">Selecciona</option>';
  OFFICES.forEach((office) => {
    const opt = document.createElement('option');
    opt.value = office;
    opt.textContent = office;
    select.appendChild(opt);
  });
  select.value = OFFICES.includes(selected) ? selected : '';
}

function showFeedback(feedback, message, type) {
  feedback.textContent = message;
  feedback.dataset.type = type;
  feedback.hidden = false;
}

function syncAssignedField() {
  const isAllocation = document.getElementById('outbound-type').value === 'allocation';
  const input = document.getElementById('outbound-assigned');
  input.required = isAllocation;
  input.disabled = !isAllocation;
  input.hidden = !isAllocation;
  document.getElementById('outbound-assigned-label').hidden = !isAllocation;
  if (!isAllocation) input.value = '';
}

function syncSupplierFields() {
  const selected = document.getElementById('inbound-supplier-id').selectedOptions[0];
  const supplier = document.getElementById('inbound-supplier');
  const cost = document.getElementById('inbound-unit-cost');
  const hasSupplier = Boolean(selected?.value);
  if (hasSupplier) supplier.value = selected.textContent;
  supplier.readOnly = hasSupplier;
  cost.disabled = !hasSupplier;
  cost.required = hasSupplier;
  if (!hasSupplier) cost.value = '';
}

async function loadSuppliers() {
  const load = ++supplierLoad;
  const { dialog, feedback } = getParts('inbound');
  const select = document.getElementById('inbound-supplier-id');
  select.options.length = 1;
  syncSupplierFields();
  if (load !== supplierLoad || !dialog.open || !inventoryApi.isAuthenticated()) return;
  try {
    const suppliers = await inventoryApi.request('/api/suppliers', { method: 'GET' });
    if (!dialog.open || !inventoryApi.isAuthenticated()) return;
    for (const supplier of suppliers) {
      const option = document.createElement('option');
      option.value = String(supplier.id);
      option.textContent = supplier.name;
      select.appendChild(option);
    }
  } catch {
    if (load === supplierLoad && dialog.open) {
      showFeedback(feedback, 'No se pudo cargar el directorio. La entrada sin coste sigue disponible.', 'info');
    }
  }
}

function openForm({ mode, assetId, sku, office }) {
  const { dialog, form, feedback } = getParts(mode);
  formVersion++;
  form.reset();
  feedback.hidden = true;
  currentAssetId = assetId;
  document.getElementById(`${mode}-sku`).value = sku ?? '';
  fillOffices(document.getElementById(`${mode}-office`), office);
  if (mode === 'outbound') syncAssignedField();
  dialog.showModal();
  if (mode === 'inbound') void loadSuppliers();
  document.getElementById(`${mode}-quantity`).focus();
}

function buildPayload(mode) {
  const quantity = Number(document.getElementById(`${mode}-quantity`).value);
  const office = document.getElementById(`${mode}-office`).value;
  if (mode === 'inbound') {
    const supplierId = document.getElementById('inbound-supplier-id').value;
    return {
      asset_id: currentAssetId,
      quantity,
      supplier: document.getElementById('inbound-supplier').value.trim(),
      office,
      ...(supplierId ? {
        supplier_id: Number(supplierId),
        unit_cost_cents: Math.round(document.getElementById('inbound-unit-cost').valueAsNumber * 100),
      } : {}),
    };
  }
  if (mode === 'direct') return { quantity, office };
  const exitType = document.getElementById('outbound-type').value;
  const recipientType = document.getElementById('outbound-recipient').value;
  return {
    asset_id: currentAssetId,
    quantity,
    exit_type: exitType,
    assigned_to: exitType === 'allocation'
      ? document.getElementById('outbound-assigned').value.trim()
      : null,
    office,
    ...(recipientType ? { recipient_type: recipientType } : {}),
  };
}

async function handleSubmit(mode, event) {
  event.preventDefault();
  const { dialog, form, feedback, submit } = getParts(mode);
  if (!form.reportValidity()) return;
  const version = formVersion;

  const send = async () => {
    if (version !== formVersion || !dialog.open || submit.disabled) return;
    submit.disabled = true;
    showFeedback(feedback, 'Guardando…', 'info');
    try {
      const payload = buildPayload(mode);
      if (mode === 'inbound') {
        await inventoryApi.createInboundOrder(payload);
      } else if (mode === 'outbound') {
        await inventoryApi.createOutboundOrder(payload);
      } else {
        await inventoryApi.rejectDirectStockEdit(currentAssetId, payload);
        showFeedback(feedback, 'Respuesta inesperada al solicitar el cambio directo.', 'error');
        return;
      }
      dialog.close();
      document.dispatchEvent(new CustomEvent('inventory:changed'));
    } catch (err) {
      showFeedback(feedback, err.message || 'No se pudo registrar el movimiento.', 'error');
    } finally {
      submit.disabled = false;
    }
  };

  // Movements require a session; open the login modal first if needed.
  if (window.AuthUI && typeof window.AuthUI.requireAuth === 'function') {
    window.AuthUI.requireAuth(send);
  } else {
    send();
  }
}

function trackCancellation(mode) {
  const { dialog, submit } = getParts(mode);
  if (!dialog.open || submit.disabled || mode === 'direct') return;
  const office = document.getElementById(`${mode}-office`).value;
  if (!OFFICES.includes(office)) return;
  const quantity = document.getElementById(`${mode}-quantity`).valueAsNumber;
  const cost = mode === 'inbound' ? document.getElementById('inbound-unit-cost') : null;
  window.Telemetry?.track('inventory_order_abandoned', {
    office: office.toLowerCase(),
    currency: office === 'Valencia' ? 'EUR' : 'USD',
    order_type: mode,
    last_step: cost && !cost.disabled && cost.value ? 'cost_entry'
      : Number.isSafeInteger(quantity) ? 'quantity_entry' : 'product_selection',
    abandonment_trigger: 'explicit_cancel',
    ...(Number.isSafeInteger(currentAssetId) && currentAssetId > 0 ? { product_id: String(currentAssetId) } : {}),
    ...(Number.isSafeInteger(quantity) ? { quantity } : {}),
  });
}

function init() {
  ['inbound', 'outbound', 'direct'].forEach((mode) => {
    const { dialog, form } = getParts(mode);
    if (!dialog || !form) return;
    form.addEventListener('submit', (e) => handleSubmit(mode, e));
    form.querySelector('[data-action="close"]').addEventListener('click', () => {
      trackCancellation(mode);
      dialog.close();
    });
    dialog.addEventListener('cancel', () => trackCancellation(mode));
  });
  document.getElementById('outbound-type')?.addEventListener('change', syncAssignedField);
  document.getElementById('inbound-supplier-id')?.addEventListener('change', syncSupplierFields);
  inventoryApi.onAuthStateChanged(() => { void loadSuppliers(); });
  document.addEventListener('inventory:open-form', (e) => openForm(e.detail));
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
