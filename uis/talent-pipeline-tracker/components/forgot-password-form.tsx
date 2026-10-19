"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import Link from "next/link";
import { ArrowRight, BriefcaseBusiness, CheckCircle2, LoaderCircle } from "lucide-react";

import {
  NexovaApiError,
  requestNexovaPasswordReset,
} from "@/lib/nexova-api";

export default function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await requestNexovaPasswordReset({ email: email.trim() });
      setIsSubmitted(true);
    } catch (requestError) {
      if (requestError instanceof NexovaApiError) {
        if (requestError.status === 422) {
          setError("Introduce una dirección de correo electrónico válida.");
        } else if (requestError.status >= 500) {
          setError("El servicio no está disponible ahora. Inténtalo más tarde.");
        } else {
          setError("No se pudo procesar la solicitud. Inténtalo más tarde.");
        }
      } else {
        setError("No pudimos conectar con el servicio. Comprueba tu conexión e inténtalo de nuevo.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f6f7f2] text-slate-950">
      <div className="mx-auto grid min-h-screen max-w-7xl lg:grid-cols-[minmax(0,1fr)_minmax(24rem,0.82fr)]">
        <aside className="hidden flex-col justify-between bg-emerald-950 px-12 py-12 text-white lg:flex">
          <div className="flex items-center gap-3 font-semibold tracking-wide">
            <span className="flex size-10 items-center justify-center rounded-lg bg-emerald-700">
              <BriefcaseBusiness aria-hidden="true" size={20} />
            </span>
            NEXOVA / TALENTO
          </div>
          <div className="max-w-lg pb-8">
            <p className="text-sm font-semibold uppercase text-emerald-300">
              Recuperación de acceso
            </p>
            <h2 className="mt-4 text-4xl font-semibold leading-tight">
              Recupera el acceso a tu espacio de talento.
            </h2>
            <p className="mt-5 max-w-md leading-7 text-emerald-100/80">
              Te enviaremos un enlace seguro de un solo uso para restablecer tu contraseña.
            </p>
          </div>
          <p className="text-sm text-emerald-100/60">Nexova · Valencia · Miami</p>
        </aside>

        <section className="flex items-center justify-center px-5 py-10 sm:px-10 lg:px-14">
          <div className="w-full max-w-md">
            <div className="mb-10 flex items-center gap-3 font-semibold tracking-wide lg:hidden">
              <span className="flex size-9 items-center justify-center rounded-lg bg-emerald-800 text-white">
                <BriefcaseBusiness aria-hidden="true" size={18} />
              </span>
              NEXOVA / TALENTO
            </div>

            <p className="text-sm font-semibold uppercase text-emerald-800">
              Recuperación de cuenta
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">
              ¿Olvidaste tu contraseña?
            </h1>
            <p className="mt-3 leading-6 text-slate-600">
              Introduce la dirección de correo asociada a tu cuenta para recibir un enlace de recuperación.
            </p>

            {isSubmitted ? (
              <div
                aria-live="polite"
                className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-950"
                role="status"
              >
                <div className="flex items-start gap-3">
                  <CheckCircle2 aria-hidden="true" className="mt-0.5 text-emerald-700" size={18} />
                  <div>
                    <h2 className="text-sm font-semibold">Solicitud enviada</h2>
                    <p className="mt-1 text-sm text-emerald-800">
                      Si esa dirección está registrada, recibirás un enlace en breve.
                    </p>
                  </div>
                </div>
              </div>
            ) : null}

            <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
              <div>
                <label className="mb-2 block text-sm font-medium" htmlFor="email">
                  Email
                </label>
                <input
                  autoComplete="email"
                  className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100 disabled:bg-slate-100 disabled:text-slate-500"
                  disabled={isSubmitting || isSubmitted}
                  id="email"
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  type="email"
                  value={email}
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

              <button
                className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-emerald-800 px-4 text-sm font-semibold text-white transition hover:bg-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isSubmitting || isSubmitted}
                type="submit"
              >
                {isSubmitting ? (
                  <LoaderCircle aria-hidden="true" className="animate-spin" size={18} />
                ) : (
                  <>
                    <span>{isSubmitted ? "Enlace solicitado" : "Enviar enlace"}</span>
                    <ArrowRight aria-hidden="true" size={17} />
                  </>
                )}
              </button>
            </form>

            <p className="mt-7 text-sm text-slate-600">
              ¿Recordaste tu contraseña?{" "}
              <Link
                className="font-semibold text-emerald-800 underline-offset-4 hover:underline"
                href="/login"
              >
                Inicia sesión
              </Link>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}

