"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, KeyRound, LoaderCircle } from "lucide-react";

import {
  changeNexovaPassword,
  NexovaApiError,
} from "@/lib/nexova-api";

export default function AccountChangePassword() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(false);

    if (newPassword.length < 8) {
      setError("La nueva contraseña debe tener al menos 8 caracteres.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("La nueva contraseña y su confirmación no coinciden.");
      return;
    }

    if (currentPassword === newPassword) {
      setError("La nueva contraseña debe ser distinta de la contraseña actual.");
      return;
    }

    setIsSubmitting(true);

    try {
      await changeNexovaPassword({
        current_password: currentPassword,
        new_password: newPassword,
      });

      setSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (requestError) {
      if (requestError instanceof NexovaApiError) {
        if (requestError.status === 400) {
          setError("La contraseña actual no es correcta.");
        } else if (requestError.status === 422) {
          setError("La nueva contraseña no cumple con los requisitos de seguridad.");
        } else if (requestError.status >= 500) {
          setError("El servicio no está disponible ahora. Inténtalo más tarde.");
        } else {
          setError(requestError.message || "No se pudo actualizar la contraseña.");
        }
      } else {
        setError("No pudimos conectar con el servicio. Comprueba tu conexión e inténtalo de nuevo.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f6f7f2] px-5 py-8 text-slate-950 sm:px-8 lg:px-10 lg:py-12">
      <div className="mx-auto w-full max-w-7xl">
        <div className="flex items-center gap-4">
          <Link
            className="inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-emerald-800 hover:text-emerald-950 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-800"
            href="/account/profile"
          >
            <ArrowLeft aria-hidden="true" size={17} />
            Volver al perfil
          </Link>
          <span className="text-slate-300">·</span>
          <Link
            className="inline-flex min-h-10 items-center text-sm font-semibold text-slate-600 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-800"
            href="/"
          >
            Pipeline
          </Link>
        </div>

        <header className="mt-8 border-b border-slate-200 pb-7">
          <p className="text-sm font-semibold uppercase text-emerald-800">
            Seguridad de cuenta
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
            Cambiar contraseña
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            Actualiza la clave de acceso de tu sesión actual. Necesitarás introducir tu contraseña vigente.
          </p>
        </header>

        <section className="mt-8 max-w-2xl rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
          {success ? (
            <div
              aria-live="polite"
              className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-950"
              role="status"
            >
              <div className="flex items-start gap-3">
                <CheckCircle2
                  aria-hidden="true"
                  className="mt-0.5 text-emerald-700"
                  size={18}
                />
                <div>
                  <h2 className="text-sm font-semibold">Contraseña actualizada</h2>
                  <p className="mt-1 text-sm text-emerald-800">
                    Tu contraseña ha sido modificada correctamente. Podrás utilizarla en tus próximos inicios de sesión.
                  </p>
                </div>
              </div>
            </div>
          ) : null}

          <form className="space-y-6" onSubmit={handleSubmit}>
            <div>
              <label
                className="mb-2 block text-sm font-medium"
                htmlFor="current-password"
              >
                Contraseña actual
              </label>
              <input
                autoComplete="current-password"
                className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
                id="current-password"
                onChange={(event) => {
                  setCurrentPassword(event.target.value);
                  setError(null);
                }}
                required
                type="password"
                value={currentPassword}
              />
            </div>

            <div>
              <label
                className="mb-2 block text-sm font-medium"
                htmlFor="new-password"
              >
                Nueva contraseña
              </label>
              <input
                autoComplete="new-password"
                className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
                id="new-password"
                minLength={8}
                onChange={(event) => {
                  setNewPassword(event.target.value);
                  setError(null);
                }}
                required
                type="password"
                value={newPassword}
              />
              <p className="mt-2 text-xs text-slate-500">
                Usa al menos 8 caracteres.
              </p>
            </div>

            <div>
              <label
                className="mb-2 block text-sm font-medium"
                htmlFor="confirm-password"
              >
                Confirmar nueva contraseña
              </label>
              <input
                autoComplete="new-password"
                className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
                id="confirm-password"
                minLength={8}
                onChange={(event) => {
                  setConfirmPassword(event.target.value);
                  setError(null);
                }}
                required
                type="password"
                value={confirmPassword}
              />
            </div>

            {error ? (
              <p
                aria-live="polite"
                className="rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-800"
                role="alert"
              >
                {error}
              </p>
            ) : null}

            <div className="flex items-center gap-4 pt-2">
              <button
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-emerald-800 px-5 text-sm font-semibold text-white transition hover:bg-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:cursor-wait disabled:opacity-60"
                disabled={isSubmitting}
                type="submit"
              >
                {isSubmitting ? (
                  <LoaderCircle
                    aria-hidden="true"
                    className="animate-spin"
                    size={17}
                  />
                ) : (
                  <KeyRound aria-hidden="true" size={17} />
                )}
                Actualizar contraseña
              </button>

              <Link
                className="inline-flex min-h-11 items-center justify-center rounded-lg border border-slate-300 px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
                href="/account/profile"
              >
                Cancelar
              </Link>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}

