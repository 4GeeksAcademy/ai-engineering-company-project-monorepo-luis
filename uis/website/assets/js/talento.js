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
  if (!node) {
    return;
  }

  node.textContent = message;
  node.classList.remove("hidden");

  if (input && typeof input.setAttribute === "function") {
    input.setAttribute("aria-invalid", "true");
    input.classList.add("border-rose-400", "focus-visible:ring-rose-300");
  }
}

function clearError(key, input) {
  const node = errorNodes[key];
  if (!node) {
    return;
  }

  node.textContent = "";
  node.classList.add("hidden");

  if (input && typeof input.removeAttribute === "function") {
    input.removeAttribute("aria-invalid");
    input.classList.remove("border-rose-400", "focus-visible:ring-rose-300");
  }
}

function updateComentariosCounter() {
  if (!fields.comentarios || !fields.contador) {
    return;
  }

  const len = fields.comentarios.value.length;
  const remaining = 500 - len;
  fields.contador.textContent = `${len}/500`;

  if (len > 500) {
    setError("comentarios", fields.comentarios, `Los comentarios no pueden exceder 500 caracteres (quedan ${remaining})`);
  } else {
    clearError("comentarios", fields.comentarios);
  }
}

function getDisponibilidadSeleccionada() {
  return form ? form.querySelector('input[name="disponibilidad"]:checked') : null;
}

function validateForm() {
  let isValid = true;

  const nombre = fields.nombre ? fields.nombre.value.trim() : "";
  const words = nombre.split(/\s+/).filter(Boolean);
  if (words.length < 2) {
    setError("nombre", fields.nombre, mensajes.nombre);
    isValid = false;
  } else {
    clearError("nombre", fields.nombre);
  }

  const email = fields.email ? fields.email.value.trim() : "";
  if (!emailRegex.test(email)) {
    setError("email", fields.email, mensajes.email);
    isValid = false;
  } else {
    clearError("email", fields.email);
  }

  const telefono = fields.telefono ? fields.telefono.value.trim() : "";
  if (!phoneRegex.test(telefono)) {
    setError("telefono", fields.telefono, mensajes.telefono);
    isValid = false;
  } else {
    clearError("telefono", fields.telefono);
  }

  const pais = fields.pais ? fields.pais.value : "";
  if (!pais) {
    setError("pais", fields.pais, mensajes.pais);
    isValid = false;
  } else {
    clearError("pais", fields.pais);
  }

  const experienciaRaw = fields.experiencia ? fields.experiencia.value.trim() : "";
  const experienciaNum = Number(experienciaRaw);
  if (experienciaRaw === "" || Number.isNaN(experienciaNum) || experienciaNum < 0 || experienciaNum > 50) {
    setError("experiencia", fields.experiencia, mensajes.experiencia);
    isValid = false;
  } else {
    clearError("experiencia", fields.experiencia);
  }

  const sector = fields.sector ? fields.sector.value : "";
  if (!sector) {
    setError("sector", fields.sector, mensajes.sector);
    isValid = false;
  } else {
    clearError("sector", fields.sector);
  }

  const ingles = fields.ingles ? fields.ingles.value : "";
  if (!ingles) {
    setError("ingles", fields.ingles, mensajes.ingles);
    isValid = false;
  } else {
    clearError("ingles", fields.ingles);
  }

  const disponibilidad = getDisponibilidadSeleccionada();
  if (!disponibilidad) {
    setError("disponibilidad", null, mensajes.disponibilidad);
    isValid = false;
  } else {
    clearError("disponibilidad", null);
  }

  const linkedin = fields.linkedin ? fields.linkedin.value.trim() : "";
  if (linkedin) {
    let linkedinValid = false;
    try {
      const parsed = new URL(linkedin);
      linkedinValid = parsed.protocol === "http:" || parsed.protocol === "https:";
    } catch (error) {
      linkedinValid = false;
    }

    if (!linkedinValid) {
      setError("linkedin", fields.linkedin, mensajes.linkedin);
      isValid = false;
    } else {
      clearError("linkedin", fields.linkedin);
    }
  } else {
    clearError("linkedin", fields.linkedin);
  }

  const comentariosLen = fields.comentarios ? fields.comentarios.value.length : 0;
  if (comentariosLen > 500) {
    const remaining = 500 - comentariosLen;
    setError("comentarios", fields.comentarios, `Los comentarios no pueden exceder 500 caracteres (quedan ${remaining})`);
    isValid = false;
  } else {
    clearError("comentarios", fields.comentarios);
  }

  if (!fields.politica || !fields.politica.checked) {
    setError("politica", fields.politica, mensajes.politica);
    isValid = false;
  } else {
    clearError("politica", fields.politica);
  }

  return isValid;
}

function focusFirstError() {
  const firstInvalid = form ? form.querySelector('[aria-invalid="true"]') : null;
  if (firstInvalid && typeof firstInvalid.focus === "function") {
    firstInvalid.focus();
    return;
  }

  if (errorNodes.disponibilidad && !errorNodes.disponibilidad.classList.contains("hidden")) {
    const firstRadio = form ? form.querySelector('input[name="disponibilidad"]') : null;
    if (firstRadio && typeof firstRadio.focus === "function") {
      firstRadio.focus();
    }
  }
}

if (form) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();

    updateComentariosCounter();
    const isValid = validateForm();

    if (!isValid) {
      if (mensajeExito) {
        mensajeExito.classList.add("hidden");
      }
      focusFirstError();
      return;
    }

    form.classList.add("hidden");
    if (mensajeExito) {
      mensajeExito.classList.remove("hidden");
      mensajeExito.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
}

if (fields.comentarios) {
  fields.comentarios.addEventListener("input", updateComentariosCounter);
  updateComentariosCounter();
}
