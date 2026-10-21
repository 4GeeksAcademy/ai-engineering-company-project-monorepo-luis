"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const supplierList = document.getElementById("supplier-list");
  const supplierCount = document.getElementById("supplier-count");
  const supplierFeedback = document.getElementById("supplier-feedback");
  const countryFilter = document.getElementById("supplier-country-filter");
  const categoryFilter = document.getElementById("supplier-category-filter");
  const refreshButton = document.getElementById("supplier-refresh");
  const supplierForm = document.getElementById("supplier-form");
  const countryInput = document.getElementById("supplier-country");
  const currencyInput = document.getElementById("supplier-currency");
  const apiBaseUrl = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "";

  const categoryLabels = {
    job_boards: "Portales de empleo",
    ats_software: "Software ATS",
    assessment_tools: "Evaluación",
    training_platforms: "Formación",
    payroll_and_hr_software: "Nóminas y RR. HH.",
    video_interview: "Entrevistas por vídeo",
    background_check: "Verificación de antecedentes",
    office_and_facilities: "Oficinas e instalaciones",
    it_and_software_licenses: "Licencias IT",
  };

  function setFeedback(message, isError = false) {
    supplierFeedback.textContent = message;
    supplierFeedback.classList.toggle("is-error", isError);
    supplierFeedback.hidden = !message;
    supplierFeedback.setAttribute("role", isError ? "alert" : "status");
  }

  async function getErrorMessage(response) {
    try {
      const errorData = await response.json();
      if (Array.isArray(errorData.detail)) {
        return errorData.detail
          .map((error) => `${error.loc.slice(1).join(".")}: ${error.msg}`)
          .join("; ");
      }
      if (errorData.detail) return String(errorData.detail);
    } catch (_) {
      // Sin JSON estructurado en la respuesta
    }

    if (response.status === 401 || response.status === 403) {
      return "No tienes autorización para realizar esta operación.";
    }
    if (response.status === 404) {
      return "El proveedor solicitado no fue encontrado.";
    }
    if (response.status >= 500) {
      return "El servicio no está disponible temporalmente. Inténtalo de nuevo más tarde.";
    }
    return "La solicitud no pudo completarse. Revisa los datos e intenta nuevamente.";
  }

  async function requestJson(path, options = {}) {
    let response;
    try {
      response = await fetch(`${apiBaseUrl}${path}`, {
        ...options,
        headers: {
          ...(options.body ? { "Content-Type": "application/json" } : {}),
          ...options.headers,
        },
      });
    } catch (_) {
      throw new Error("No se pudo conectar con el servidor. Comprueba tu conexión e intenta de nuevo.");
    }

    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  }

  function makeTextElement(tagName, className, text) {
    const element = document.createElement(tagName);
    if (className) element.className = className;
    element.textContent = text;
    return element;
  }

  function appendDataItem(list, label, value, extraClass = "") {
    const item = document.createElement("div");
    if (extraClass) item.className = extraClass;
    item.append(
      makeTextElement("dt", "", label),
      makeTextElement("dd", "", value),
    );
    list.appendChild(item);
  }

  function formatDate(dateValue) {
    if (!dateValue) return "Sin fecha";
    const [year, month, day] = dateValue.split("-").map(Number);
    return new Intl.DateTimeFormat("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    }).format(new Date(Date.UTC(year, month - 1, day)));
  }

  function renewsWithinSixtyDays(dateValue) {
    if (!dateValue) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const limit = new Date(today);
    limit.setDate(limit.getDate() + 60);
    const renewal = new Date(`${dateValue}T00:00:00`);
    return renewal >= today && renewal <= limit;
  }

  function renderSupplier(supplier) {
    const renewingSoon = renewsWithinSixtyDays(supplier.contract_renewal_date);
    const card = document.createElement("article");
    card.className = "supplier-card";
    if (supplier.status === "suspended") card.classList.add("is-suspended");
    if (renewingSoon) card.classList.add("is-renewing");

    const header = document.createElement("div");
    header.className = "supplier-card-heading";
    const title = document.createElement("div");
    title.className = "supplier-card-title";
    title.appendChild(makeTextElement("h3", "", supplier.name));
    title.appendChild(makeTextElement(
      "span",
      "supplier-country",
      supplier.country === "Spain" ? "España" : "Estados Unidos",
    ));
    const statusBadge = makeTextElement(
      "span",
      `supplier-status ${supplier.status === "active" ? "is-active" : "is-suspended"}`,
      supplier.status === "active" ? "Activo" : "Suspendido",
    );
    header.append(title, statusBadge);

    const categories = document.createElement("div");
    categories.className = "supplier-categories";
    supplier.categories.forEach((category) => {
      categories.appendChild(makeTextElement(
        "span",
        "supplier-category-tag",
        categoryLabels[category] || category,
      ));
    });

    const data = document.createElement("dl");
    data.className = "supplier-data";
    appendDataItem(
      data,
      "Tarifa mensual",
      new Intl.NumberFormat("es-ES", {
        style: "currency",
        currency: supplier.currency,
      }).format(supplier.monthly_rate),
    );
    appendDataItem(
      data,
      "Renovación",
      formatDate(supplier.contract_renewal_date),
      renewingSoon ? "supplier-renewal-cell" : "",
    );
    appendDataItem(data, "País", supplier.country === "Spain" ? "Spain" : "USA");
    appendDataItem(data, "Moneda", supplier.currency);

    const rateForm = document.createElement("form");
    rateForm.className = "supplier-rate-form";
    const rateLabel = document.createElement("label");
    rateLabel.textContent = "Cambiar tarifa";
    const rateInput = document.createElement("input");
    rateInput.className = "supplier-rate-input";
    rateInput.type = "number";
    rateInput.min = "0.01";
    rateInput.step = "0.01";
    rateInput.required = true;
    rateInput.value = supplier.monthly_rate;
    rateInput.setAttribute("aria-label", `Nueva tarifa mensual de ${supplier.name}`);
    rateLabel.appendChild(rateInput);
    const saveRateButton = makeTextElement("button", "supplier-button supplier-button-primary", "Guardar tarifa");
    saveRateButton.type = "submit";
    rateForm.append(rateLabel, saveRateButton);

    rateForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!rateForm.reportValidity()) return;
      saveRateButton.disabled = true;
      setFeedback("");
      try {
        await requestJson(`/api/suppliers/${supplier.id}/rate`, {
          method: "PATCH",
          body: JSON.stringify({ monthly_rate: Number(rateInput.value) }),
        });
        setFeedback(`Tarifa de ${supplier.name} actualizada.`);
        await loadSuppliers();
      } catch (error) {
        setFeedback(error.message, true);
      } finally {
        saveRateButton.disabled = false;
      }
    });

    const statusButton = makeTextElement(
      "button",
      "supplier-button supplier-button-secondary",
      supplier.status === "active" ? "Suspender" : "Activar",
    );
    statusButton.type = "button";
    statusButton.setAttribute(
      "aria-label",
      `${supplier.status === "active" ? "Suspender" : "Activar"} ${supplier.name}`,
    );

    statusButton.addEventListener("click", async () => {
      statusButton.disabled = true;
      setFeedback("");
      try {
        await requestJson(`/api/suppliers/${supplier.id}/status`, {
          method: "PATCH",
          body: JSON.stringify({
            status: supplier.status === "active" ? "suspended" : "active",
          }),
        });
        setFeedback(`${supplier.name} actualizado.`);
        await loadSuppliers();
      } catch (error) {
        setFeedback(error.message, true);
      } finally {
        statusButton.disabled = false;
      }
    });

    const controls = document.createElement("div");
    controls.className = "supplier-card-controls";
    controls.append(rateForm, statusButton);

    const details = document.createElement("details");
    details.className = "supplier-card-details";
    details.appendChild(makeTextElement("summary", "", "Detalles"));
    if (supplier.contact_email) {
      details.appendChild(makeTextElement("p", "supplier-detail-text", `Contacto: ${supplier.contact_email}`));
    }
    if (supplier.notes) {
      details.appendChild(makeTextElement("p", "supplier-detail-text", supplier.notes));
    }

    card.append(header, categories, data, controls);
    if (supplier.contact_email || supplier.notes) card.appendChild(details);
    if (renewingSoon) {
      card.appendChild(makeTextElement(
        "p",
        "supplier-renewal",
        `Renueva dentro de 60 días: ${formatDate(supplier.contract_renewal_date)}`,
      ));
    }
    return card;
  }

  async function loadSuppliers() {
    supplierList.setAttribute("aria-busy", "true");
    supplierList.replaceChildren();
    supplierCount.textContent = "Cargando proveedores…";
    const params = new URLSearchParams();
    if (countryFilter.value) params.set("country", countryFilter.value);
    if (categoryFilter.value) params.set("category", categoryFilter.value);
    const query = params.toString();

    try {
      const suppliers = await requestJson(`/api/suppliers${query ? `?${query}` : ""}`);
      supplierCount.textContent = `${suppliers.length} ${suppliers.length === 1 ? "proveedor" : "proveedores"}`;
      if (!suppliers.length) {
        supplierList.appendChild(makeTextElement("p", "supplier-empty", "No hay proveedores para estos filtros."));
        return;
      }
      suppliers.forEach((supplier) => supplierList.appendChild(renderSupplier(supplier)));
    } catch (error) {
      supplierCount.textContent = "No disponible";
      const errorWrapper = document.createElement("div");
      errorWrapper.className = "supplier-empty";
      errorWrapper.style.padding = "24px 16px";
      errorWrapper.style.textAlign = "center";
      const errorMsg = makeTextElement("p", "", "No se pudo cargar el directorio de proveedores.");
      errorMsg.style.margin = "0 0 12px 0";
      errorWrapper.appendChild(errorMsg);

      const retryBtn = makeTextElement("button", "supplier-button supplier-button-secondary", "↻ Reintentar");
      retryBtn.type = "button";
      retryBtn.addEventListener("click", () => {
        loadSuppliers();
      });
      errorWrapper.appendChild(retryBtn);

      supplierList.replaceChildren(errorWrapper);
      setFeedback(error.message, true);
    } finally {
      supplierList.setAttribute("aria-busy", "false");
    }
  }

  supplierForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!supplierForm.reportValidity()) return;
    const categories = Array.from(
      supplierForm.querySelectorAll('input[name="categories"]:checked'),
      (input) => input.value,
    );
    if (!categories.length) {
      setFeedback("Selecciona al menos una categoría.", true);
      return;
    }

    const fieldValue = (name) => supplierForm.querySelector(`[name="${name}"]`).value.trim();
    const payload = {
      name: fieldValue("name"),
      country: fieldValue("country"),
      categories,
      monthly_rate: Number(fieldValue("monthly_rate")),
      currency: fieldValue("currency"),
      status: fieldValue("status"),
    };
    const renewalDate = fieldValue("contract_renewal_date");
    const contactEmail = fieldValue("contact_email");
    const notes = fieldValue("notes");
    if (renewalDate) payload.contract_renewal_date = renewalDate;
    if (contactEmail) payload.contact_email = contactEmail;
    if (notes) payload.notes = notes;

    const submitButton = supplierForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    setFeedback("");
    try {
      await requestJson("/api/suppliers", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      supplierForm.reset();
      currencyInput.value = countryInput.value === "Spain" ? "EUR" : "USD";
      supplierForm.closest("details").open = false;
      setFeedback("Proveedor creado.");
      await loadSuppliers();
    } catch (error) {
      setFeedback(error.message, true);
    } finally {
      submitButton.disabled = false;
    }
  });

  countryInput.addEventListener("change", () => {
    currencyInput.value = countryInput.value === "Spain" ? "EUR" : "USD";
  });
  countryFilter.addEventListener("change", loadSuppliers);
  categoryFilter.addEventListener("change", loadSuppliers);
  refreshButton.addEventListener("click", loadSuppliers);

  loadSuppliers();
});
