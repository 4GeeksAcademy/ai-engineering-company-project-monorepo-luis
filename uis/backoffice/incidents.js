/**
 * Nexova Backoffice - Gestor del Analizador de Incidencias
 */

document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("incident-file-input");
  const uploadZone = document.getElementById("upload-dropzone");
  const selectedFileInfo = document.getElementById("selected-file-info");
  const selectedFileName = document.getElementById("selected-file-name");
  const btnAnalyze = document.getElementById("btn-analyze-incidents");
  const statusContainer = document.getElementById("status-container");
  const resultsPanel = document.getElementById("analysis-results");
  const btnExport = document.getElementById("btn-export-csv");

  let currentFile = null;

  // URL del API backend (por defecto localhost:8000 o el host actual)
  const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "";

  // 1. Manejo de Drag and Drop
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

  function handleFileSelected(file) {
    clearStatus();
    if (!file.name.toLowerCase().endsWith(".csv")) {
      showError("El archivo seleccionado debe ser un archivo con extensión .csv");
      currentFile = null;
      btnAnalyze.disabled = true;
      selectedFileInfo.style.display = "none";
      return;
    }

    if (file.size === 0) {
      showError("El archivo seleccionado está vacío.");
      currentFile = null;
      btnAnalyze.disabled = true;
      selectedFileInfo.style.display = "none";
      return;
    }

    currentFile = file;
    selectedFileName.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    selectedFileInfo.style.display = "flex";
    btnAnalyze.disabled = false;
  }

  // 2. Ejecución del análisis al hacer clic en "Analizar"
  btnAnalyze.addEventListener("click", async () => {
    if (!currentFile) return;

    showLoading("Analizando archivo CSV de incidencias...");
    btnAnalyze.disabled = true;
    resultsPanel.style.display = "none";

    const formData = new FormData();
    formData.append("file", currentFile);

    try {
      const response = await fetch(`${API_BASE_URL}/api/incidents/analyze`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let errMessage = "Error al procesar el archivo en el servidor.";
        try {
          const errData = await response.json();
          if (errData.detail) errMessage = errData.detail;
        } catch (_) {}
        showError(errMessage);
        btnAnalyze.disabled = false;
        return;
      }

      const data = await response.json();
      clearStatus();
      renderResults(data);
      btnAnalyze.disabled = false;
    } catch (err) {
      showError(
        "No se pudo conectar con el servidor backend (FastAPI en " +
          API_BASE_URL +
          "). Asegúrate de que el servicio esté iniciado con `uvicorn services.api.main:app --port 8000`."
      );
      btnAnalyze.disabled = false;
    }
  });

  // 3. Renderizado de resultados
  function renderResults(data) {
    document.getElementById("kpi-total").textContent = data.total_records;
    document.getElementById("kpi-valid").textContent = data.valid_records;
    document.getElementById("kpi-invalid").textContent = data.invalid_records;

    const sat = data.satisfaction || {};
    const avgScoreEl = document.getElementById("kpi-score");
    if (sat.average_score !== null && sat.average_score !== undefined) {
      avgScoreEl.textContent = `${sat.average_score.toFixed(2)} / 5.00`;
    } else {
      avgScoreEl.textContent = "N/A";
    }
    document.getElementById("kpi-score-count").textContent = `${sat.scored_tickets || 0} de ${sat.total_closed_tickets || 0} tickets cerrados con puntuación`;

    // Categorías
    const catContainer = document.getElementById("category-breakdown-list");
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

    // Estados
    const statusContainer = document.getElementById("status-breakdown-list");
    statusContainer.innerHTML = "";
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
      statusContainer.appendChild(row);
    }

    // Desglose de inválidos
    const invalidList = document.getElementById("invalid-breakdown-list");
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

    // Distribución de puntuaciones
    const scoreList = document.getElementById("score-distribution-list");
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

    resultsPanel.style.display = "block";
    resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // 4. Descarga del reporte CSV
  btnExport.addEventListener("click", async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/incidents/results/export`);
      if (!response.ok) {
        showError("No se pudo descargar el archivo CSV de exportación.");
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
      showError("Error al solicitar la exportación CSV: " + e.message);
    }
  });

  // Utilidades de feedback visual
  function showLoading(msg) {
    statusContainer.innerHTML = `
      <div class="status-alert loading" role="status" aria-live="polite">
        <div class="spinner" aria-hidden="true"></div>
        <span>${msg}</span>
      </div>
    `;
  }

  function showError(msg) {
    statusContainer.innerHTML = `
      <div class="status-alert error" role="alert" aria-live="assertive">
        <strong>Error:</strong> <span>${msg}</span>
      </div>
    `;
  }

  function clearStatus() {
    statusContainer.innerHTML = "";
  }
});
