const form = document.getElementById("form-registro-talento");
const mensajeExito = document.getElementById("mensaje-exito");

const fields = {
  nombre: document.getElementById("nombre-completo"),
  email: document.getElementById("email"),
  telefono: document.getElementById("telefono"),
  pais: document.getElementById("pais"),
  experiencia: document.getElementById("experiencia"),
  sector: document.getElementById("sector"),
  ingles: document.getElementById("ingles"),
  linkedin: document.getElementById("linkedin"),
  comentarios: document.getElementById("comentarios"),
  contador: document.getElementById("comentarios-contador"),
  politica: document.getElementById("politica")
};

const radiosDisponibilidad = form ? Array.from(form.querySelectorAll('input[name="disponibilidad"]')) : [];

const errorNodes = {
  nombre: document.getElementById("error-nombre-completo"),
  email: document.getElementById("error-email"),
  telefono: document.getElementById("error-telefono"),
  pais: document.getElementById("error-pais"),
  experiencia: document.getElementById("error-experiencia"),
  sector: document.getElementById("error-sector"),
  ingles: document.getElementById("error-ingles"),
  disponibilidad: document.getElementById("error-disponibilidad"),
  linkedin: document.getElementById("error-linkedin"),
  comentarios: document.getElementById("error-comentarios"),
  politica: document.getElementById("error-politica")
};

const mensajes = {
  nombre: "El nombre debe contener al menos nombre y apellido",
  email: "Ingresa un email válido (ejemplo: nombre@empresa.com)",
  telefono: "El teléfono debe incluir código de país (ejemplo: +34 612 345 678)",
  pais: "Selecciona tu país de residencia",
  experiencia: "Los años de experiencia deben estar entre 0 y 50",
  sector: "Selecciona el sector de tu interés",
  ingles: "Indica tu nivel de inglés",
  disponibilidad: "Selecciona tu disponibilidad",
  linkedin: "Si incluyes LinkedIn, debe ser una URL válida",
  politica: "Debes aceptar la política de tratamiento de datos para continuar"
};

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const phoneRegex = /^\+\d{1,4}(?:\s\d{1,4}){1,5}$/;

function setError(key, input, message) {
  const node = errorNodes[key];
  if (!node) return;

  node.textContent = message;
  node.classList.remove("hidden");

  if (input) {
    input.setAttribute("aria-invalid", "true");
    input.classList.add("border-rose-400", "focus-visible:ring-rose-300");
  }
}

function clearError(key, input) {
  const node = errorNodes[key];
  if (!node) return;

  node.textContent = "";
  node.classList.add("hidden");

  if (input) {
    input.removeAttribute("aria-invalid");
    input.classList.remove("border-rose-400", "focus-visible:ring-rose-300");
  }
}

function getDisponibilidadSeleccionada() {
  return form ? form.querySelector('input[name="disponibilidad"]:checked') : null;
}

function validateNombre() {
  const value = fields.nombre ? fields.nombre.value.trim() : "";
  const words = value.split(/\s+/).filter(Boolean);
  if (words.length < 2) {
    setError("nombre", fields.nombre, mensajes.nombre);
    return false;
  }
  clearError("nombre", fields.nombre);
  return true;
}

function validateEmail() {
  const value = fields.email ? fields.email.value.trim() : "";
  if (!emailRegex.test(value)) {
    setError("email", fields.email, mensajes.email);
    return false;
  }
  clearError("email", fields.email);
  return true;
}

function validateTelefono() {
  const value = fields.telefono ? fields.telefono.value.trim() : "";
  if (!phoneRegex.test(value)) {
    setError("telefono", fields.telefono, mensajes.telefono);
    return false;
  }
  clearError("telefono", fields.telefono);
  return true;
}

function validatePais() {
  const value = fields.pais ? fields.pais.value : "";
  if (!value) {
    setError("pais", fields.pais, mensajes.pais);
    return false;
  }
  clearError("pais", fields.pais);
  return true;
}

function validateExperiencia() {
  const raw = fields.experiencia ? fields.experiencia.value.trim() : "";
  const num = Number(raw);
  if (raw === "" || Number.isNaN(num) || num < 0 || num > 50) {
    setError("experiencia", fields.experiencia, mensajes.experiencia);
    return false;
  }
  clearError("experiencia", fields.experiencia);
  return true;
}

function validateSector() {
  const value = fields.sector ? fields.sector.value : "";
  if (!value) {
    setError("sector", fields.sector, mensajes.sector);
    return false;
  }
  clearError("sector", fields.sector);
  return true;
}

function validateIngles() {
  const value = fields.ingles ? fields.ingles.value : "";
  if (!value) {
    setError("ingles", fields.ingles, mensajes.ingles);
    return false;
  }
  clearError("ingles", fields.ingles);
  return true;
}

function validateDisponibilidad() {
  const selected = getDisponibilidadSeleccionada();
  if (!selected) {
    setError("disponibilidad", null, mensajes.disponibilidad);
    return false;
  }
  clearError("disponibilidad", null);
  return true;
}

function validateLinkedin() {
  const value = fields.linkedin ? fields.linkedin.value.trim() : "";
  if (!value) {
    clearError("linkedin", fields.linkedin);
    return true;
  }

  let valid = false;
  try {
    const parsed = new URL(value);
    valid = parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    valid = false;
  }

  if (!valid) {
    setError("linkedin", fields.linkedin, mensajes.linkedin);
    return false;
  }
  clearError("linkedin", fields.linkedin);
  return true;
}

function updateComentariosCounter() {
  if (!fields.comentarios || !fields.contador) return;

  const len = fields.comentarios.value.length;
  const remaining = 500 - len;
  fields.contador.textContent = `${len}/500`;

  if (len > 500) {
    setError("comentarios", fields.comentarios, `Los comentarios no pueden exceder 500 caracteres (quedan ${remaining})`);
    return false;
  }

  clearError("comentarios", fields.comentarios);
  return true;
}

function validatePolitica() {
  if (!fields.politica || !fields.politica.checked) {
    setError("politica", fields.politica, mensajes.politica);
    return false;
  }
  clearError("politica", fields.politica);
  return true;
}

function validateAll() {
  return [
    validateNombre(),
    validateEmail(),
    validateTelefono(),
    validatePais(),
    validateExperiencia(),
    validateSector(),
    validateIngles(),
    validateDisponibilidad(),
    validateLinkedin(),
    updateComentariosCounter(),
    validatePolitica()
  ].every(Boolean);
}

function clearAllErrors() {
  clearError("nombre", fields.nombre);
  clearError("email", fields.email);
  clearError("telefono", fields.telefono);
  clearError("pais", fields.pais);
  clearError("experiencia", fields.experiencia);
  clearError("sector", fields.sector);
  clearError("ingles", fields.ingles);
  clearError("disponibilidad", null);
  clearError("linkedin", fields.linkedin);
  clearError("comentarios", fields.comentarios);
  clearError("politica", fields.politica);
}

function focusFirstError() {
  const firstInvalid = form ? form.querySelector('[aria-invalid="true"]') : null;
  if (firstInvalid) {
    firstInvalid.focus();
    return;
  }

  if (errorNodes.disponibilidad && !errorNodes.disponibilidad.classList.contains("hidden")) {
    const firstRadio = form ? form.querySelector('input[name="disponibilidad"]') : null;
    if (firstRadio) firstRadio.focus();
  }
}

if (form) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();

    const valid = validateAll();
    if (!valid) {
      if (mensajeExito) mensajeExito.classList.add("hidden");
      focusFirstError();
      return;
    }

    form.classList.add("hidden");
    if (mensajeExito) {
      mensajeExito.classList.remove("hidden");
      mensajeExito.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });

  form.addEventListener("reset", () => {
    window.setTimeout(() => {
      clearAllErrors();
      if (mensajeExito) mensajeExito.classList.add("hidden");
      form.classList.remove("hidden");
      updateComentariosCounter();
    }, 0);
  });
}

if (fields.nombre) {
  fields.nombre.addEventListener("input", validateNombre);
  fields.nombre.addEventListener("blur", validateNombre);
}
if (fields.email) {
  fields.email.addEventListener("input", validateEmail);
  fields.email.addEventListener("blur", validateEmail);
}
if (fields.telefono) {
  fields.telefono.addEventListener("input", validateTelefono);
  fields.telefono.addEventListener("blur", validateTelefono);
}
if (fields.pais) {
  fields.pais.addEventListener("change", validatePais);
  fields.pais.addEventListener("blur", validatePais);
}
if (fields.experiencia) {
  fields.experiencia.addEventListener("input", validateExperiencia);
  fields.experiencia.addEventListener("blur", validateExperiencia);
}
if (fields.sector) {
  fields.sector.addEventListener("change", validateSector);
  fields.sector.addEventListener("blur", validateSector);
}
if (fields.ingles) {
  fields.ingles.addEventListener("change", validateIngles);
  fields.ingles.addEventListener("blur", validateIngles);
}
if (fields.linkedin) {
  fields.linkedin.addEventListener("input", validateLinkedin);
  fields.linkedin.addEventListener("blur", validateLinkedin);
}
if (fields.comentarios) {
  fields.comentarios.addEventListener("input", updateComentariosCounter);
  fields.comentarios.addEventListener("blur", updateComentariosCounter);
  updateComentariosCounter();
}
if (fields.politica) {
  fields.politica.addEventListener("change", validatePolitica);
}

radiosDisponibilidad.forEach((radio) => {
  radio.addEventListener("change", validateDisponibilidad);
  radio.addEventListener("blur", validateDisponibilidad);
});
