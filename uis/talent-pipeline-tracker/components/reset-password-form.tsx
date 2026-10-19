"use client";

import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  BriefcaseBusiness,
  LoaderCircle,
} from "lucide-react";

import {
  clearNexovaSession,
  NexovaApiError,
  resetNexovaPassword,
} from "@/lib/nexova-api";

export default function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [token, setToken] = useState<string | null>(null);
  const [isTokenMissing, setIsTokenMissing] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isTokenInvalid, setIsTokenInvalid] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const rawToken = searchParams.get("token")?.trim();

    if (rawToken) {
      setToken(rawToken);
      // Remove the token from the URL immediately so it is not leaked or kept in browser history
      window.history.replaceState(null, "", window.location.pathname);
    } else {
      setIsTokenMissing(true);
    }
  }, [searchParams]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!token) {
      setError("El enlace de restablecimiento no contiene un token válido o ha expirado.");
      setIsTokenInvalid(true);
      return;
    }

    if (newPassword.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setIsSubmitting(true);

    try {
      await resetNexovaPassword({
        token,
        new_password: newPassword,
      });

      // Clear any leftover access token from previous local sessions
      clearNexovaSession();

      // Redirect to login with success indicator
      router.replace("/login?reset=success");
    } catch (requestError) {
      if (requestError instanceof NexovaApiError) {
        if (requestError.status === 400) {
          setError(
            "El enlace de restablecimiento es inválido, ha expirado o ya fue utilizado.",
          );
          setIsTokenInvalid(true);
        } else if (requestError.status === 422) {
          setError("La nueva contraseña debe tener al menos 8 caracteres.");
        } else if (requestError.status >= 500) {
          setError("El servicio no está disponible ahora. Inténtalo más tarde.");
        } else {
          setError("No se pudo restablecer la contraseña. Inténtalo de nuevo.");
        }
      } else {
        setError(
          "No pudimos conectar con el servicio. Comprueba tu conexión e inténtalo de nuevo.",
        );
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
              Seguridad de acceso
            </p>
            <h2 className="mt-4 text-4xl font-semibold leading-tight">
              Crea tu nueva contraseña.
            </h2>
            <p className="mt-5 max-w-md leading-7 text-emerald-100/80">
              Una vez actualizada, podrás volver a acceder con tu cuenta de inmediato.
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
              Restablecimiento
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">
              Nueva contraseña
            </h1>
            <p className="mt-3 leading-6 text-slate-600">
              Introduce y confirma tu nueva contraseña de acceso.
            </p>

            {isTokenMissing ? (
              <div
                aria-live="polite"
                className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-950"
                role="alert"
              >
                <div className="flex items-start gap-3">
                  <AlertTriangle
                    aria-hidden="true"
                    className="mt-0.5 text-amber-700"
                    size={18}
                  />
                  <div>
                    <h2 className="text-sm font-semibold">Enlace no válido</h2>
                    <p className="mt-1 text-sm text-amber-800">
                      El enlace no incluye un token de recuperación válido o ya fue cargado previamente.
                    </p>
                    <div className="mt-4">
                      <Link
                        className="inline-flex items-center text-sm font-semibold text-emerald-800 underline-offset-4 hover:underline"
                        href="/forgot-password"
                      >
                        Solicitar un nuevo enlace
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
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
                    onChange={(event) => setNewPassword(event.target.value)}
                    required
                    type="password"
                    value={newPassword}
                  />
                  <p className="mt-2 text-xs text-slate-500">
                    Mínimo 8 caracteres.
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
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    required
                    type="password"
                    value={confirmPassword}
                  />
                </div>

                {error ? (
                  <div
                    aria-live="polite"
                    className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
                    role="alert"
                  >
                    <p>{error}</p>
                    {isTokenInvalid ? (
                      <div className="mt-3">
                        <Link
                          className="font-semibold text-emerald-800 underline-offset-4 hover:underline"
                          href="/forgot-password"
                        >
                          Solicitar un nuevo enlace
                        </Link>
                      </div>
                    ) : null}
                  </div>
                ) : null}

                <button
                  className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-emerald-800 px-4 text-sm font-semibold text-white transition hover:bg-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:cursor-wait disabled:opacity-60"
                  disabled={isSubmitting}
                  type="submit"
                >
                  {isSubmitting ? (
                    <LoaderCircle
                      aria-hidden="true"
                      className="animate-spin"
                      size={18}
                    />
                  ) : (
                    <>
                      <span>Guardar contraseña</span>
                      <ArrowRight aria-hidden="true" size={17} />
                    </>
                  )}
                </button>
              </form>
            )}

            <p className="mt-7 text-sm text-slate-600">
              ¿Quieres volver al login?{" "}
              <Link
                className="font-semibold text-emerald-800 underline-offset-4 hover:underline"
                href="/login"
              >
                Iniciar sesión
              </Link>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}

