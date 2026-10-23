/**
 * Nexova Backoffice — Authentication UI Controller
 * 
 * Manages the accessible login dialog, topbar session status, and
 * provides route/action protection helpers (AuthUI.requireAuth).
 */
(function (global) {
  "use strict";

  let pendingAuthCallback = null;

  function getElements() {
    return {
      statusContainer: document.getElementById("auth-status-container"),
      dialog: document.getElementById("auth-dialog"),
      form: document.getElementById("auth-login-form"),
      emailInput: document.getElementById("auth-email"),
      passwordInput: document.getElementById("auth-password"),
      feedback: document.getElementById("auth-feedback"),
      submitBtn: document.getElementById("auth-submit-btn"),
      closeBtn: document.getElementById("auth-close-btn"),
      cancelBtn: document.getElementById("auth-cancel-btn"),
    };
  }

  function setFeedback(feedbackEl, message, isError = true) {
    if (!feedbackEl) return;
    if (!message) {
      feedbackEl.hidden = true;
      feedbackEl.textContent = "";
      feedbackEl.className = "auth-feedback";
      return;
    }
    feedbackEl.hidden = false;
    feedbackEl.textContent = message;
    feedbackEl.className = `auth-feedback ${isError ? "is-error" : "is-success"}`;
    feedbackEl.setAttribute("role", isError ? "alert" : "status");
  }

  function openLoginModal(callback = null) {
    pendingAuthCallback = callback;
    const { dialog, emailInput, passwordInput, feedback, submitBtn } = getElements();
    if (!dialog) return;

    setFeedback(feedback, "");
    if (passwordInput) passwordInput.value = "";
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Ingresar al sistema";
    }

    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "true");
    }

    if (emailInput) {
      emailInput.focus();
    }
  }

  function closeLoginModal() {
    const { dialog } = getElements();
    if (!dialog) return;

    if (typeof dialog.close === "function") {
      dialog.close();
    } else {
      dialog.removeAttribute("open");
    }
    pendingAuthCallback = null;
  }

  function renderAuthStatus(user) {
    const { statusContainer } = getElements();
    if (!statusContainer) return;

    statusContainer.innerHTML = "";

    if (user && global.inventoryApi && global.inventoryApi.isAuthenticated()) {
      const wrapper = document.createElement("div");
      wrapper.className = "user-session";
      wrapper.id = "user-session-badge";

      const roleBadge = document.createElement("span");
      roleBadge.className = "user-role-badge";
      roleBadge.textContent = user.role ? String(user.role).toUpperCase() : "STAFF";

      const emailSpan = document.createElement("span");
      emailSpan.className = "user-email";
      emailSpan.textContent = user.name || user.email || "Usuario autenticado";
      emailSpan.title = user.email || "";

      const logoutBtn = document.createElement("button");
      logoutBtn.type = "button";
      logoutBtn.className = "btn-auth-logout";
      logoutBtn.id = "btn-auth-logout";
      logoutBtn.textContent = "Cerrar sesión";
      logoutBtn.title = "Cerrar sesión en este equipo";
      logoutBtn.addEventListener("click", () => {
        global.inventoryApi.logout();
      });

      wrapper.appendChild(roleBadge);
      wrapper.appendChild(emailSpan);
      wrapper.appendChild(logoutBtn);
      statusContainer.appendChild(wrapper);
    } else {
      const loginBtn = document.createElement("button");
      loginBtn.type = "button";
      loginBtn.className = "btn-auth-login";
      loginBtn.id = "btn-open-login";
      loginBtn.innerHTML = '<span aria-hidden="true">🔒</span> Iniciar sesión';
      loginBtn.addEventListener("click", () => {
        openLoginModal();
      });
      statusContainer.appendChild(loginBtn);
    }
  }

  async function handleLoginSubmit(event) {
    event.preventDefault();
    const { emailInput, passwordInput, feedback, submitBtn } = getElements();
    if (!emailInput || !passwordInput || !submitBtn) return;

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
      setFeedback(feedback, "Por favor introduce tu correo y contraseña.");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Verificando credenciales...";
    setFeedback(feedback, "");

    try {
      const { user } = await global.inventoryApi.login(email, password);
      setFeedback(feedback, "Acceso concedido.", false);

      setTimeout(() => {
        const callbackToRun = pendingAuthCallback;
        closeLoginModal();
        if (typeof callbackToRun === "function") {
          callbackToRun(user);
        }
      }, 350);
    } catch (err) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Ingresar al sistema";
      setFeedback(feedback, err.message || "Error al autenticar. Verifica tus credenciales.");
    }
  }

  function requireAuth(callback) {
    if (global.inventoryApi && global.inventoryApi.isAuthenticated()) {
      if (typeof callback === "function") {
        callback(global.inventoryApi.getUser());
      }
      return true;
    }
    openLoginModal(callback);
    return false;
  }

  function init() {
    const { form, closeBtn, cancelBtn, dialog } = getElements();

    if (form) {
      form.addEventListener("submit", handleLoginSubmit);
    }

    if (closeBtn) {
      closeBtn.addEventListener("click", closeLoginModal);
    }

    if (cancelBtn) {
      cancelBtn.addEventListener("click", closeLoginModal);
    }

    if (dialog) {
      dialog.addEventListener("cancel", (e) => {
        e.preventDefault();
        closeLoginModal();
      });
    }

    // Suscribirse a cambios en el cliente API
    if (global.inventoryApi) {
      global.inventoryApi.onAuthStateChanged((user) => {
        renderAuthStatus(user);
      });

      // Renderizar estado inicial de sesión
      renderAuthStatus(global.inventoryApi.getUser());
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  global.AuthUI = {
    openLoginModal,
    closeLoginModal,
    requireAuth,
    renderAuthStatus,
  };
})(typeof window !== "undefined" ? window : globalThis);
