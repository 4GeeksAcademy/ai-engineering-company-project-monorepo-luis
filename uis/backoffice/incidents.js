/**
 * Nexova Backoffice - Gestor Centralizado de Incidencias & Analizador CSV
 */

"use strict";

document.addEventListener("DOMContentLoaded", () => {
  // Backend API URL (localhost:8000 en local o relativo)
  const API_BASE_URL =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
      ? "http://127.0.0.1:8000"
      : "";

  // =========================================================================
  // Diccionarios de etiquetas legibles (Nexova Briefing)
  // =========================================================================

  const CATEGORY_LABELS = {
    technical_failure: "Fallo de sistemas / herramientas",
    process_error: "Error de procesos operativos",
    client_complaint: "Queja de cliente corporativo",
    candidate_issue: "Problema de candidato",
    staff_issue: "Incidencia interna de RR. HH.",
    sla_breach: "Incumplimiento de SLA",
    data_quality: "Error o inconsistencia de datos",
    other: "Otra incidencia",
  };

  const STATUS_LABELS = {
    open: "Abierta",
    in_progress: "En progreso",
    resolved: "Resuelta",
    discarded: "Descartada",
  };

  const ORIGIN_LABELS = {
    customer: "Cliente corporativo",
    branch: "Sede Nexova",
    internal: "Interno",
  };

  const BRANCH_LABELS = {
    central: "Central — Sede Valencia",
    valencia_operations: "Valencia — Operaciones",
    miami_office: "Miami Office",
    remote: "Remoto (empleado sin sede fija)",
  };

  // Matriz de transiciones permitidas según el briefing
  const ALLOWED_NEXT_STATUSES = {
    open: ["in_progress", "discarded"],
    in_progress: ["resolved", "discarded"],
    resolved: [],
    discarded: [],
  };

  // =========================================================================
  // SECCIÓN 1: FORMULARIO DE REGISTRO DE INCIDENCIAS
  // =========================================================================

  const createForm = document.getElementById("incident-create-form");
  const titleInput = document.getElementById("inc-title");
  const descriptionInput = document.getElementById("inc-description");
  const categorySelect = document.getElementById("inc-category");
  const originSelect = document.getElementById("inc-origin");
  const branchSelect = document.getElementById("inc-branch");
  const branchWrapper = document.getElementById("branch-field-wrapper");
  const branchHint = document.getElementById("branch-hint");
  const formFeedback = document.getElementById("create-form-feedback");
  const btnSubmit = document.getElementById("btn-submit-incident");
  const btnSubmitText = document.getElementById("btn-submit-text");

  // Destaque visual obligatorio para Sede cuando origin === 'branch'
  function updateBranchHighlight() {
    if (originSelect && branchWrapper) {
      const isBranchOrigin = originSelect.value === "branch";
      branchWrapper.classList.toggle("is-highlighted", isBranchOrigin);
      if (branchHint) {
        branchHint.style.display = isBranchOrigin ? "block" : "none";
      }
    }
  }

  if (originSelect) {
    originSelect.addEventListener("change", updateBranchHighlight);
    updateBranchHighlight();
  }

  function clearFormErrors() {
    document.querySelectorAll(".field-error").forEach((el) => {
      el.textContent = "";
    });
    if (formFeedback) {
      formFeedback.style.display = "none";
      formFeedback.className = "status-alert";
      formFeedback.textContent = "";
    }
  }

  function showFieldError(fieldId, message) {
    const errorEl = document.getElementById(`err-${fieldId}`);
    if (errorEl) {
      errorEl.textContent = message;
    }
  }

  function validateCreateForm() {
    clearFormErrors();
    let isValid = true;

    const title = titleInput.value.trim();
    if (!title) {
      showFieldError("title", "El título es obligatorio y no puede estar vacío.");
      isValid = false;
    } else if (title.length > 120) {
      showFieldError("title", "El título no puede exceder 120 caracteres.");
      isValid = false;
    }

    const description = descriptionInput.value.trim();
    if (!description) {
      showFieldError("description", "La descripción detallada es obligatoria.");
      isValid = false;
    }

    if (!categorySelect.value) {
      showFieldError("category", "Debes seleccionar una categoría válida.");
      isValid = false;
    }

    if (!originSelect.value) {
      showFieldError("origin", "Debes seleccionar un origen para el reporte.");
      isValid = false;
    }

    if (!branchSelect.value) {
      showFieldError("branch", "La sede es obligatoria para todos los orígenes.");
      isValid = false;
    }

    return isValid;
  }

  if (createForm) {
    createForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      if (!validateCreateForm()) {
        formFeedback.className = "status-alert error";
        formFeedback.textContent = "Por favor, corrige los campos marcados antes de continuar.";
        formFeedback.style.display = "block";
        return;
      }

      // Preparar payload
      const payload = {
        title: titleInput.value.trim(),
        description: descriptionInput.value.trim(),
        category: categorySelect.value,
        origin: originSelect.value,
        branch: branchSelect.value,
      };

      // Estado de carga y bloqueo del botón
      btnSubmit.disabled = true;
      btnSubmitText.textContent = "Guardando incidencia...";
      formFeedback.style.display = "none";

      try {
        const response = await fetch(`${API_BASE_URL}/api/incidents`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          let errorMsg = "No se pudo registrar la incidencia. Intenta nuevamente.";
          try {
            const errData = await response.json();
            if (errData.errors && Array.isArray(errData.errors)) {
              errData.errors.forEach((err) => {
                showFieldError(err.field, err.message);
              });
              errorMsg = errData.detail || "Verifica los datos ingresados.";
            } else if (errData.detail) {
              errorMsg = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
            }
          } catch (_) {}

          formFeedback.className = "status-alert error";
          formFeedback.textContent = errorMsg;
          formFeedback.style.display = "block";
          return;
        }

        const newIncident = await response.json();
        createForm.reset();
        updateBranchHighlight();
        clearFormErrors();

        formFeedback.className = "status-alert success";
        formFeedback.textContent = `✓ Incidencia #${newIncident.id} registrada con éxito.`;
        formFeedback.style.display = "block";

        // Actualizar lista y resumen automáticamente
        loadIncidentsList();
        loadIncidentsSummary();
      } catch (err) {
        formFeedback.className = "status-alert error";
        formFeedback.textContent =
          "No se pudo conectar con el servidor. Verifica tu conexión e intenta nuevamente.";
        formFeedback.style.display = "block";
      } finally {
        btnSubmit.disabled = false;
        btnSubmitText.textContent = "Guardar incidencia";
      }
    });

    createForm.addEventListener("reset", () => {
      setTimeout(() => {
        clearFormErrors();
        updateBranchHighlight();
      }, 0);
    });
  }

  // =========================================================================
  // SECCIÓN 2: LISTADO Y FILTRADO DE INCIDENCIAS
  // =========================================================================

  const incidentsContainer = document.getElementById("incidents-container");
  const filterStatus = document.getElementById("filter-status");
  const filterOrigin = document.getElementById("filter-origin");
  const filterBranch = document.getElementById("filter-branch");
  const filterCategory = document.getElementById("filter-category");
  const btnRefreshList = document.getElementById("btn-refresh-list");
  const listActionFeedback = document.getElementById("list-action-feedback");

  function showListFeedback(message, type = "success") {
    if (!listActionFeedback) return;
    listActionFeedback.className = `status-alert ${type}`;
    listActionFeedback.textContent = message;
    listActionFeedback.style.display = "block";
    setTimeout(() => {
      if (listActionFeedback.textContent === message) {
        listActionFeedback.style.display = "none";
      }
    }, 4500);
  }

  async function loadIncidentsList() {
    if (!incidentsContainer) return;

    incidentsContainer.innerHTML = `
      <div class="status-alert loading" role="status">
        <div class="spinner" aria-hidden="true"></div>
        <span>Cargando incidencias...</span>
      </div>
    `;

    const params = new URLSearchParams();
    if (filterStatus && filterStatus.value) params.set("status", filterStatus.value);
    if (filterOrigin && filterOrigin.value) params.set("origin", filterOrigin.value);
    if (filterBranch && filterBranch.value) params.set("branch", filterBranch.value);
    if (filterCategory && filterCategory.value) params.set("category", filterCategory.value);

    const queryString = params.toString() ? `?${params.toString()}` : "";

    try {
      const response = await fetch(`${API_BASE_URL}/api/incidents${queryString}`);
      if (!response.ok) {
        throw new Error("No se pudo obtener el listado de incidencias del servidor.");
      }

      const incidents = await response.json();
      renderIncidentsTable(incidents);
    } catch (err) {
      incidentsContainer.innerHTML = `
        <div class="error-state" role="alert">
          <p><strong>Error al cargar las incidencias:</strong> ${err.message}</p>
          <button type="button" class="btn btn-secondary btn-sm" id="btn-retry-incidents" style="margin-top: 10px;">
            <span>↻ Reintentar</span>
          </button>
        </div>
      `;
      const retryBtn = document.getElementById("btn-retry-incidents");
      if (retryBtn) {
        retryBtn.addEventListener("click", loadIncidentsList);
      }
    }
  }

  function renderIncidentsTable(incidents) {
    if (!incidentsContainer) return;

    if (!Array.isArray(incidents) || incidents.length === 0) {
      incidentsContainer.innerHTML = `
        <div class="empty-state">
          <p>No se encontraron incidencias registradas con los filtros seleccionados.</p>
        </div>
      `;
      return;
    }

    let rowsHtml = "";
    incidents.forEach((inc) => {
      const catLabel = CATEGORY_LABELS[inc.category] || inc.category;
      const originLabel = ORIGIN_LABELS[inc.origin] || inc.origin;
      const branchLabel = BRANCH_LABELS[inc.branch] || inc.branch;
      const statusLabel = STATUS_LABELS[inc.status] || inc.status;

      // Selector de transición de estado
      const allowedNext = ALLOWED_NEXT_STATUSES[inc.status] || [];
      const isTerminal = allowedNext.length === 0;

      let statusControlHtml = "";
      if (isTerminal) {
        statusControlHtml = `<span class="badge badge-${inc.status}">${statusLabel}</span>`;
      } else {
        let optionsHtml = `<option value="${inc.status}" selected>${statusLabel} (actual)</option>`;
        allowedNext.forEach((nextSt) => {
          optionsHtml += `<option value="${nextSt}">→ Cambiar a: ${STATUS_LABELS[nextSt]}</option>`;
        });
        statusControlHtml = `
          <select class="select-status-transition" data-incident-id="${inc.id}" data-current-status="${inc.status}" aria-label="Cambiar estado de incidencia ${inc.id}">
            ${optionsHtml}
          </select>
        `;
      }

      const dateStr = inc.created_at ? inc.created_at.split("T")[0] : "—";

      rowsHtml += `
        <tr id="incident-row-${inc.id}">
          <td><strong>#${inc.id}</strong></td>
          <td class="inc-title-cell">
            <span class="inc-title-text">${escapeHtml(inc.title)}</span>
            <span class="inc-desc-text" title="${escapeHtml(inc.description)}">${escapeHtml(inc.description)}</span>
          </td>
          <td><span class="badge badge-cat">${catLabel}</span></td>
          <td><small>${originLabel}</small></td>
          <td><small>${branchLabel}</small></td>
          <td><small>${dateStr}</small></td>
          <td>${statusControlHtml}</td>
        </tr>
      `;
    });

    incidentsContainer.innerHTML = `
      <div class="incidents-table-wrapper">
        <table class="incidents-table">
          <thead>
            <tr>
              <th scope="col">ID</th>
              <th scope="col">Incidencia</th>
              <th scope="col">Categoría</th>
              <th scope="col">Origen</th>
              <th scope="col">Sede</th>
              <th scope="col">Fecha</th>
              <th scope="col">Ciclo de vida</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;

    // Asignar listeners a los selects de transición con rollback optimista
    document.querySelectorAll(".select-status-transition").forEach((select) => {
      select.addEventListener("change", async (e) => {
        const incidentId = select.dataset.incidentId;
        const previousStatus = select.dataset.currentStatus;
        const newStatus = select.value;

        if (newStatus === previousStatus) return;

        // Actualización optimista: bloquear select durante request
        select.disabled = true;

        try {
          const response = await fetch(`${API_BASE_URL}/api/incidents/${incidentId}/status`, {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ status: newStatus }),
          });

          if (!response.ok) {
            let errorMsg = `No se pudo cambiar el estado a '${STATUS_LABELS[newStatus] || newStatus}'.`;
            try {
              const errData = await response.json();
              if (errData.detail) errorMsg = errData.detail;
            } catch (_) {}
            throw new Error(errorMsg);
          }

          const updatedIncident = await response.json();
          select.dataset.currentStatus = updatedIncident.status;

          showListFeedback(`✓ Incidencia #${incidentId} actualizada a '${STATUS_LABELS[newStatus]}'`, "success");

          // Si el nuevo estado es terminal o cambia las transiciones posibles, refrescar la lista
          loadIncidentsList();
          loadIncidentsSummary();
        } catch (err) {
          // ROLLBACK OPTIMISTA: Revertir al estado anterior y avisar al usuario
          select.value = previousStatus;
          showListFeedback(`⚠️ Rollback: ${err.message}`, "error");
        } finally {
          select.disabled = false;
        }
      });
    });
  }

  // Listeners de filtros
  [filterStatus, filterOrigin, filterBranch, filterCategory].forEach((filterEl) => {
    if (filterEl) {
      filterEl.addEventListener("change", loadIncidentsList);
    }
  });

  if (btnRefreshList) {
    btnRefreshList.addEventListener("click", loadIncidentsList);
  }

  // =========================================================================
  // SECCIÓN 3: PANEL DE RESUMEN DE MÉTRICAS (/api/incidents/summary)
  // =========================================================================

  const sumTotal = document.getElementById("sum-total");
  const sumOpen = document.getElementById("sum-open");
  const sumInProgress = document.getElementById("sum-in-progress");
  const sumResolved = document.getElementById("sum-resolved");
  const sumDiscarded = document.getElementById("sum-discarded");
  const summaryByCategory = document.getElementById("summary-by-category");
  const summaryByBranchOrigin = document.getElementById("summary-by-branch-origin");
  const summaryFeedback = document.getElementById("summary-feedback");
  const btnRefreshSummary = document.getElementById("btn-refresh-summary");
  const incidentManagerBadge = document.getElementById("incident-manager-badge");

  async function loadIncidentsSummary() {
    if (summaryFeedback) {
      summaryFeedback.className = "status-alert loading";
      summaryFeedback.innerHTML = `
        <div class="spinner" aria-hidden="true"></div>
        <span>Cargando métricas...</span>
      `;
      summaryFeedback.style.display = "flex";
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/incidents/summary`);
      if (!response.ok) {
        throw new Error("No se pudo obtener el resumen de métricas.");
      }

      const summary = await response.json();
      renderSummaryData(summary);
      if (summaryFeedback) summaryFeedback.style.display = "none";
    } catch (err) {
      // Manejar error de forma aislada sin romper el resto de la interfaz
      if (summaryFeedback) {
        summaryFeedback.className = "status-alert error";
        summaryFeedback.innerHTML = `
          <span>Error al cargar métricas: No se pudo conectar con el servidor.</span>
          <button type="button" class="btn btn-secondary btn-sm" id="btn-retry-summary" style="margin-left: 10px;">↻ Reintentar</button>
        `;
        summaryFeedback.style.display = "flex";
        const retry = document.getElementById("btn-retry-summary");
        if (retry) retry.addEventListener("click", loadIncidentsSummary);
      }
    }
  }

  function renderSummaryData(summary) {
    const total = summary.total || 0;
    if (sumTotal) sumTotal.textContent = total;
    if (incidentManagerBadge) incidentManagerBadge.textContent = `${total} INCIDENCIAS`;

    const byStatus = summary.by_status || {};
    if (sumOpen) sumOpen.textContent = byStatus.open || 0;
    if (sumInProgress) sumInProgress.textContent = byStatus.in_progress || 0;
    if (sumResolved) sumResolved.textContent = byStatus.resolved || 0;
    if (sumDiscarded) sumDiscarded.textContent = byStatus.discarded || 0;

    // Desglose por categoría
    if (summaryByCategory) {
      summaryByCategory.innerHTML = "";
      const byCat = summary.by_category || {};
      const catEntries = Object.entries(byCat);
      if (catEntries.length === 0 || total === 0) {
        summaryByCategory.innerHTML = "<p class='upload-help'>Sin datos registrados aún.</p>";
      } else {
        catEntries.forEach(([catKey, count]) => {
          const pct = total > 0 ? ((count / total) * 100).toFixed(1) : "0.0";
          const label = CATEGORY_LABELS[catKey] || catKey;
          const row = document.createElement("div");
          row.className = "stat-row";
          row.innerHTML = `
            <span class="stat-name">${label}</span>
            <div class="stat-meta">
              <div class="stat-bar-container" aria-hidden="true">
                <div class="stat-bar-fill" style="width: ${pct}%"></div>
              </div>
              <span class="stat-badge">${count} (${pct}%)</span>
            </div>
          `;
          summaryByCategory.appendChild(row);
        });
      }
    }

    // Desglose por Sede y Origen
    if (summaryByBranchOrigin) {
      summaryByBranchOrigin.innerHTML = "";
      const byBranch = summary.by_branch || {};
      const byOrigin = summary.by_origin || {};

      let branchHtml = "<h4 style='font-size: 12px; margin: 0 0 8px; color: var(--muted); text-transform: uppercase;'>Por Sede</h4>";
      Object.entries(byBranch).forEach(([brKey, count]) => {
        const pct = total > 0 ? ((count / total) * 100).toFixed(1) : "0.0";
        const label = BRANCH_LABELS[brKey] || brKey;
        branchHtml += `
          <div class="stat-row">
            <span class="stat-name">${label}</span>
            <div class="stat-meta">
              <div class="stat-bar-container" aria-hidden="true">
                <div class="stat-bar-fill" style="width: ${pct}%"></div>
              </div>
              <span class="stat-badge">${count}</span>
            </div>
          </div>
        `;
      });

      let originHtml = "<h4 style='font-size: 12px; margin: 16px 0 8px; color: var(--muted); text-transform: uppercase;'>Por Origen</h4>";
      Object.entries(byOrigin).forEach(([orKey, count]) => {
        const pct = total > 0 ? ((count / total) * 100).toFixed(1) : "0.0";
        const label = ORIGIN_LABELS[orKey] || orKey;
        originHtml += `
          <div class="stat-row">
            <span class="stat-name">${label}</span>
            <div class="stat-meta">
              <div class="stat-bar-container" aria-hidden="true">
                <div class="stat-bar-fill" style="width: ${pct}%"></div>
              </div>
              <span class="stat-badge">${count}</span>
            </div>
          </div>
        `;
      });

      summaryByBranchOrigin.innerHTML = branchHtml + originHtml;
    }
  }

  if (btnRefreshSummary) {
    btnRefreshSummary.addEventListener("click", loadIncidentsSummary);
  }

  // Inicialización de datos del gestor centralizado
  loadIncidentsSummary();
  loadIncidentsList();

  // =========================================================================
  // SECCIÓN 4: ANALIZADOR HISTÓRICO CSV (Outsourcing Helpdesk) — Conservado
  // =========================================================================

  const fileInput = document.getElementById("incident-file-input");
  const uploadZone = document.getElementById("upload-dropzone");
  const selectedFileInfo = document.getElementById("selected-file-info");
  const selectedFileName = document.getElementById("selected-file-name");
  const btnAnalyze = document.getElementById("btn-analyze-incidents");
  const statusContainer = document.getElementById("status-container");
  const resultsPanel = document.getElementById("analysis-results");
  const btnExport = document.getElementById("btn-export-csv");

  let currentFile = null;

  if (uploadZone && fileInput) {
    ["dragenter", "dragover"].forEach((eventName) => {
      uploadZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadZone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      uploadZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadZone.classList.remove("dragover");
      });
    });

    uploadZone.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        handleFileSelected(files[0]);
      }
    });

    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        handleFileSelected(e.target.files[0]);
      }
    });
  }

  function handleFileSelected(file) {
    clearCsvStatus();
    if (!file.name.toLowerCase().endsWith(".csv")) {
      showCsvError("El archivo seleccionado debe ser un archivo con extensión .csv");
      currentFile = null;
      if (btnAnalyze) btnAnalyze.disabled = true;
      if (selectedFileInfo) selectedFileInfo.style.display = "none";
      return;
    }

    if (file.size === 0) {
      showCsvError("El archivo seleccionado está vacío.");
      currentFile = null;
      if (btnAnalyze) btnAnalyze.disabled = true;
      if (selectedFileInfo) selectedFileInfo.style.display = "none";
      return;
    }

    currentFile = file;
    if (selectedFileName) {
      selectedFileName.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    }
    if (selectedFileInfo) selectedFileInfo.style.display = "flex";
    if (btnAnalyze) btnAnalyze.disabled = false;
  }

  if (btnAnalyze) {
    btnAnalyze.addEventListener("click", async () => {
      if (!currentFile) return;

      showCsvLoading("Analizando archivo CSV de incidencias...");
      btnAnalyze.disabled = true;
      if (resultsPanel) resultsPanel.style.display = "none";

      const formData = new FormData();
      formData.append("file", currentFile);

      try {
        const response = await fetch(`${API_BASE_URL}/api/incidents/analyze`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          let errMessage = "No se pudo procesar el archivo en el servidor.";
          try {
            const errData = await response.json();
            if (errData.detail) errMessage = errData.detail;
          } catch (_) {}
          showCsvError(errMessage);
          return;
        }

        const data = await response.json();
        clearCsvStatus();
        renderCsvResults(data);
      } catch (err) {
        showCsvError(
          "No se pudo conectar con el servidor. Comprueba tu conexión e intenta de nuevo."
        );
      } finally {
        btnAnalyze.disabled = false;
      }
    });
  }

  function renderCsvResults(data) {
    const kpiTotal = document.getElementById("kpi-total");
    const kpiValid = document.getElementById("kpi-valid");
    const kpiInvalid = document.getElementById("kpi-invalid");
    if (kpiTotal) kpiTotal.textContent = data.total_records;
    if (kpiValid) kpiValid.textContent = data.valid_records;
    if (kpiInvalid) kpiInvalid.textContent = data.invalid_records;

    const sat = data.satisfaction || {};
    const avgScoreEl = document.getElementById("kpi-score");
    if (avgScoreEl) {
      if (sat.average_score !== null && sat.average_score !== undefined) {
        avgScoreEl.textContent = `${sat.average_score.toFixed(2)} / 5.00`;
      } else {
        avgScoreEl.textContent = "N/A";
      }
    }
    const scoreCountEl = document.getElementById("kpi-score-count");
    if (scoreCountEl) {
      scoreCountEl.textContent = `${sat.scored_tickets || 0} de ${sat.total_closed_tickets || 0} tickets cerrados con puntuación`;
    }

    // Categorías del CSV
    const catContainer = document.getElementById("category-breakdown-list");
    if (catContainer) {
      catContainer.innerHTML = "";
      const totalValid = data.valid_records || 1;
      for (const [cat, count] of Object.entries(data.category_counts || {})) {
        const pct = ((count / totalValid) * 100).toFixed(1);
        const row = document.createElement("div");
        row.className = "stat-row";
        row.innerHTML = `
          <span class="stat-name">${cat}</span>
          <div class="stat-meta">
            <div class="stat-bar-container" aria-hidden="true">
              <div class="stat-bar-fill" style="width: ${pct}%"></div>
            </div>
            <span class="stat-badge">${count} (${pct}%)</span>
          </div>
        `;
        catContainer.appendChild(row);
      }
    }

    // Estados del CSV
    const statusContainerEl = document.getElementById("status-breakdown-list");
    if (statusContainerEl) {
      statusContainerEl.innerHTML = "";
      const totalValid = data.valid_records || 1;
      for (const [st, count] of Object.entries(data.status_counts || {})) {
        const pct = ((count / totalValid) * 100).toFixed(1);
        const row = document.createElement("div");
        row.className = "stat-row";
        row.innerHTML = `
          <span class="stat-name">${st}</span>
          <div class="stat-meta">
            <div class="stat-bar-container" aria-hidden="true">
              <div class="stat-bar-fill" style="width: ${pct}%"></div>
            </div>
            <span class="stat-badge">${count} (${pct}%)</span>
          </div>
        `;
        statusContainerEl.appendChild(row);
      }
    }

    // Desglose de inválidos del CSV
    const invalidList = document.getElementById("invalid-breakdown-list");
    if (invalidList) {
      invalidList.innerHTML = "";
      const invalidItems = Object.entries(data.invalid_breakdown || {});
      if (invalidItems.length === 0) {
        invalidList.innerHTML = "<li><span>Todos los registros fueron validados correctamente.</span></li>";
      } else {
        for (const [reason, count] of invalidItems) {
          const li = document.createElement("li");
          li.innerHTML = `<span>${reason}</span><strong>${count}</strong>`;
          invalidList.appendChild(li);
        }
      }
    }

    // Puntuaciones
    const scoreList = document.getElementById("score-distribution-list");
    if (scoreList) {
      scoreList.innerHTML = "";
      const dist = sat.score_distribution || {};
      const scoreLabels = {
        1: "1 - Muy insatisfecho",
        2: "2 - Insatisfecho",
        3: "3 - Neutral",
        4: "4 - Satisfecho",
        5: "5 - Muy satisfecho",
      };
      for (let s = 1; s <= 5; s++) {
        const count = dist[s] || 0;
        const closedCount = sat.scored_tickets || 1;
        const pct = ((count / closedCount) * 100).toFixed(1);
        const row = document.createElement("div");
        row.className = "stat-row";
        row.innerHTML = `
          <span class="stat-name">${scoreLabels[s]}</span>
          <div class="stat-meta">
            <div class="stat-bar-container" aria-hidden="true">
              <div class="stat-bar-fill" style="width: ${pct}%"></div>
            </div>
            <span class="stat-badge">${count}</span>
          </div>
        `;
        scoreList.appendChild(row);
      }
    }

    if (resultsPanel) {
      resultsPanel.style.display = "block";
      resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // Exportar CSV
  if (btnExport) {
    btnExport.addEventListener("click", async () => {
      btnExport.disabled = true;
      try {
        const response = await fetch(`${API_BASE_URL}/api/incidents/results/export`);
        if (!response.ok) {
          showCsvError("No se pudo descargar el archivo CSV de exportación.");
          return;
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "results.csv";
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
      } catch (e) {
        showCsvError("No se pudo completar la exportación del archivo CSV. Comprueba tu conexión e intenta de nuevo.");
      } finally {
        btnExport.disabled = false;
      }
    });
  }

  function showCsvLoading(msg) {
    if (!statusContainer) return;
    statusContainer.innerHTML = `
      <div class="status-alert loading" role="status" aria-live="polite">
        <div class="spinner" aria-hidden="true"></div>
        <span>${msg}</span>
      </div>
    `;
  }

  function showCsvError(msg) {
    if (!statusContainer) return;
    statusContainer.innerHTML = `
      <div class="status-alert error" role="alert" aria-live="assertive">
        <strong>Error:</strong> <span>${msg}</span>
      </div>
    `;
  }

  function clearCsvStatus() {
    if (statusContainer) statusContainer.innerHTML = "";
  }

  // Utilidad de escape XSS para renderizado seguro
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
