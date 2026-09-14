"use client";

import { X, Save, UserRound } from "lucide-react";
import { useState } from "react";

import { createCandidate, editCandidate } from "@/lib/api";
import type { Candidate, CandidateInput } from "@/types";

type Mode = "create" | "edit";

type CandidateFormValues = {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string;
  cv_url: string;
  experience_years: string;
};

const defaultValues: CandidateFormValues = {
  full_name: "",
  email: "",
  phone: "",
  position: "",
  linkedin_url: "",
  cv_url: "",
  experience_years: "",
};

function toPayload(values: CandidateFormValues): CandidateInput {
  return {
    full_name: values.full_name.trim(),
    email: values.email.trim(),
    phone: values.phone.trim(),
    position: values.position.trim(),
    linkedin_url: values.linkedin_url.trim() || undefined,
    cv_url: values.cv_url.trim() || undefined,
    experience_years: Number(values.experience_years),
  };
}

function getInitialValues(candidate?: Candidate | Partial<Candidate>) {
  if (!candidate) return defaultValues;

  return {
    full_name: candidate.full_name ?? "",
    email: candidate.email ?? "",
    phone: candidate.phone ?? "",
    position: candidate.position ?? "",
    linkedin_url: candidate.linkedin_url ?? "",
    cv_url: candidate.cv_url ?? "",
    experience_years: String(candidate.experience_years ?? ""),
  };
}

export default function CandidateForm({
  mode,
  candidate,
  onClose,
  onSaved,
}: {
  mode: Mode;
  candidate?: Candidate | Partial<Candidate>;
  onClose: () => void;
  onSaved: (candidate: Candidate) => void;
}) {
  const [values, setValues] = useState<CandidateFormValues>(() =>
    getInitialValues(candidate),
  );
  const [errors, setErrors] = useState<Partial<Record<keyof CandidateFormValues, string>>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function updateField(field: keyof CandidateFormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
    setSubmitError(null);
  }

  function validate() {
    const nextErrors: Partial<Record<keyof CandidateFormValues, string>> = {};

    if (!values.full_name.trim()) {
      nextErrors.full_name = "El nombre completo es obligatorio.";
    }
    if (!values.email.trim()) {
      nextErrors.email = "El email es obligatorio.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) {
      nextErrors.email = "Introduce un email válido.";
    }
    if (!values.phone.trim()) {
      nextErrors.phone = "El teléfono es obligatorio.";
    }
    if (!values.position.trim()) {
      nextErrors.position = "La posición es obligatoria.";
    }
    if (!values.experience_years.trim()) {
      nextErrors.experience_years = "La experiencia es obligatoria.";
    } else if (Number(values.experience_years) < 0) {
      nextErrors.experience_years = "La experiencia no puede ser negativa.";
    }

    if (values.linkedin_url.trim() && !/^https?:\/\//i.test(values.linkedin_url.trim())) {
      nextErrors.linkedin_url = "La URL de LinkedIn debe empezar por http(s).";
    }
    if (values.cv_url.trim() && !/^https?:\/\//i.test(values.cv_url.trim())) {
      nextErrors.cv_url = "La URL del CV debe empezar por http(s).";
    }

    return nextErrors;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors = validate();
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      setSubmitError("Completa los campos obligatorios y corrige los errores del formulario.");
      return;
    }

    setSaving(true);
    setSubmitError(null);

    try {
      const payload = toPayload(values);
      const savedCandidate =
        mode === "create"
          ? await createCandidate(payload)
          : await editCandidate(candidate?.id ?? "", payload);

      onSaved(savedCandidate);
      onClose();
    } catch (error) {
      setSubmitError(
        error instanceof Error
          ? error.message
          : "No se pudo guardar el candidato.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
              <UserRound size={18} />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                {mode === "create" ? "Nuevo candidato" : "Editar candidato"}
              </h2>
              <p className="text-sm text-slate-500">
                {mode === "create" ? "Registra un nuevo perfil" : "Actualiza los datos del candidato"}
              </p>
            </div>
          </div>
          <button
            aria-label="Cerrar formulario"
            className="rounded-lg border border-slate-200 p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
            onClick={onClose}
            type="button"
          >
            <X size={18} />
          </button>
        </div>

        <form className="space-y-5 p-5 sm:p-6" onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              error={errors.full_name}
              label="Nombre completo"
              onChange={(value) => updateField("full_name", value)}
              placeholder="Ej. Marta Sánchez"
              required
              value={values.full_name}
            />
            <Field
              error={errors.email}
              label="Email"
              onChange={(value) => updateField("email", value)}
              placeholder="marta@ejemplo.com"
              required
              type="email"
              value={values.email}
            />
            <Field
              error={errors.phone}
              label="Teléfono"
              onChange={(value) => updateField("phone", value)}
              placeholder="+34 600 123 456"
              required
              value={values.phone}
            />
            <Field
              error={errors.position}
              label="Posición"
              onChange={(value) => updateField("position", value)}
              placeholder="Jefa/e de Gabinete"
              required
              value={values.position}
            />
            <Field
              error={errors.linkedin_url}
              label="LinkedIn"
              onChange={(value) => updateField("linkedin_url", value)}
              placeholder="https://linkedin.com/in/..."
              value={values.linkedin_url}
            />
            <Field
              error={errors.cv_url}
              label="CV"
              onChange={(value) => updateField("cv_url", value)}
              placeholder="https://.../cv.pdf"
              value={values.cv_url}
            />
            <Field
              error={errors.experience_years}
              label="Años de experiencia"
              onChange={(value) => updateField("experience_years", value)}
              min={0}
              placeholder="5"
              required
              type="number"
              value={values.experience_years}
            />
          </div>

          {submitError ? (
            <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {submitError}
            </div>
          ) : null}

          <div className="flex flex-col-reverse gap-3 border-t border-slate-200 pt-4 sm:flex-row sm:justify-end">
            <button
              className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
              onClick={onClose}
              type="button"
            >
              Cancelar
            </button>
            <button
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-emerald-300"
              disabled={saving}
              type="submit"
            >
              <Save size={16} />
              {saving ? "Guardando..." : mode === "create" ? "Crear candidato" : "Guardar cambios"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  required = false,
  error,
  min,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  required?: boolean;
  error?: string;
  min?: number;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">
        {label}
        {required ? <span className="text-red-500"> *</span> : null}
      </span>
      <input
        className="h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"
        min={min}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type={type}
        value={value}
      />
      {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
    </label>
  );
}
