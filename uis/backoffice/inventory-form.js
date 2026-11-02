// inventory-form.js – inbound/outbound movement dialogs for inventory-forms.html

// Must match OfficeType in services/api/schemas.py
const OFFICES = ['Valencia', 'Miami'];

let currentAssetId = null;

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

function openForm({ mode, assetId, sku, office }) {
  const { dialog, form, feedback } = getParts(mode);
  form.reset();
  feedback.hidden = true;
  currentAssetId = assetId;
  document.getElementById(`${mode}-sku`).value = sku ?? '';
  fillOffices(document.getElementById(`${mode}-office`), office);
  if (mode === 'outbound') syncAssignedField();
  dialog.showModal();
  document.getElementById(`${mode}-quantity`).focus();
}

function buildPayload(mode) {
  const quantity = Number(document.getElementById(`${mode}-quantity`).value);
  const office = document.getElementById(`${mode}-office`).value;
  if (mode === 'inbound') {
    return {
      asset_id: currentAssetId,
      quantity,
      supplier: document.getElementById('inbound-supplier').value.trim(),
      office,
    };
  }
  const exitType = document.getElementById('outbound-type').value;
  return {
    asset_id: currentAssetId,
    quantity,
    exit_type: exitType,
    assigned_to: exitType === 'allocation'
      ? document.getElementById('outbound-assigned').value.trim()
      : null,
    office,
  };
}

async function handleSubmit(mode, event) {
  event.preventDefault();
  const { dialog, form, feedback, submit } = getParts(mode);
  if (!form.reportValidity()) return;

  const send = async () => {
    submit.disabled = true;
    showFeedback(feedback, 'Guardando…', 'info');
    try {
      const payload = buildPayload(mode);
      if (mode === 'inbound') {
        await inventoryApi.createInboundOrder(payload);
      } else {
        await inventoryApi.createOutboundOrder(payload);
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

function init() {
  ['inbound', 'outbound'].forEach((mode) => {
    const { dialog, form } = getParts(mode);
    if (!dialog || !form) return;
    form.addEventListener('submit', (e) => handleSubmit(mode, e));
    form.querySelector('[data-action="close"]').addEventListener('click', () => dialog.close());
  });
  document.getElementById('outbound-type')?.addEventListener('change', syncAssignedField);
  document.addEventListener('inventory:open-form', (e) => openForm(e.detail));
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
