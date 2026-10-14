"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, BriefcaseBusiness, LoaderCircle } from "lucide-react";

import {
  loginToNexova,
  NexovaApiError,
  registerNexovaUser,
  storeNexovaAccessToken,
} from "@/lib/nexova-api";

type AuthFormProps = {
  mode: "login" | "register";
};

function getErrorMessage(error: unknown, registered: boolean): string {
  if (registered) {
    return "Tu cuenta se creó, pero no pudimos iniciar sesión. Intenta iniciar sesión con tus credenciales.";
  }

  if (error instanceof NexovaApiError) {
    if (error.status === 401) {
      return "El email o la contraseña no son correctos.";
    }
    if (error.status === 409) {
      return "Ya existe una cuenta con ese email.";
    }
    if (error.status === 422) {
      return "Revisa los datos ingresados e inténtalo de nuevo.";
    }
    if (error.status >= 500) {
      return "El servicio no está disponible ahora. Inténtalo más tarde.";
    }
  }

  return "No pudimos conectar con el servicio. Comprueba tu conexión e inténtalo de nuevo.";
}

export default function AuthForm({ mode }: AuthFormProps) {
  const isRegistration = mode === "register";
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    let registered = false;

    try {
      if (isRegistration) {
        await registerNexovaUser({
          email: email.trim(),
          password,
          ...(name.trim() ? { name: name.trim() } : {}),
          ...(phone.trim() ? { phone: phone.trim() } : {}),
          ...(address.trim() ? { address: address.trim() } : {}),
        });
        registered = true;
      }

      const token = await loginToNexova({ email: email.trim(), password });
      storeNexovaAccessToken(token.access_token);
      router.replace("/");
    } catch (requestError) {
      setError(getErrorMessage(requestError, registered));
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
              Espacio de talento
            </p>
            <h2 className="mt-4 text-4xl font-semibold leading-tight">
              Una visión clara del talento que avanza con Nexova.
            </h2>
            <p className="mt-5 max-w-md leading-7 text-emerald-100/80">
              Accede al pipeline de candidatos y continúa el seguimiento de cada proceso.
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
              {isRegistration ? "Nueva cuenta" : "Acceso de equipo"}
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">
              {isRegistration ? "Crear cuenta" : "Iniciar sesión"}
            </h1>
            <p className="mt-3 leading-6 text-slate-600">
              {isRegistration
                ? "Registra tu cuenta para acceder al pipeline de talento."
                : "Introduce tus credenciales para acceder al pipeline de talento."}
            </p>

            <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
              {isRegistration ? (
                <>
                  <div>
                    <label className="mb-2 block text-sm font-medium" htmlFor="name">
                      Nombre
                    </label>
                    <input
                      autoComplete="name"
                      className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
                      id="name"
                      onChange={(event) => setName(event.target.value)}
                      value={name}
                    />
                  </div>
                  <div className="grid gap-5 sm:grid-cols-2">
                    <div>
                      <label className="mb-2 block text-sm font-medium" htmlFor="phone">
                        Teléfono <span className="font-normal text-slate-500">(opcional)</span>
                      </label>
                      <input
                        autoComplete="tel"
                        className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
                        id="phone"
                        onChange={(event) => setPhone(event.target.value)}
                        type="tel"
                        value={phone}
                      />
                    </div>
                    <div>
                      <label className="mb-2 block text-sm font-medium" htmlFor="address">
                        Dirección <span className="font-normal text-slate-500">(opcional)</span>
                      </label>
                      <input
                        autoComplete="street-address"
                        className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
                        id="address"
                        onChange={(event) => setAddress(event.target.value)}
                        value={address}
                      />
                    </div>
                  </div>
                </>
              ) : null}

              <div>
                <label className="mb-2 block text-sm font-medium" htmlFor="email">
                  Email
                </label>
                <input
                  autoComplete="email"
                  className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
                  id="email"
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  type="email"
                  value={email}
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium" htmlFor="password">
                  Contraseña
                </label>
                <input
                  autoComplete={isRegistration ? "new-password" : "current-password"}
                  className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
                  id="password"
                  minLength={8}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  type="password"
                  value={password}
                />
                {isRegistration ? (
                  <p className="mt-2 text-xs text-slate-500">
                    Usa al menos 8 caracteres.
                  </p>
                ) : null}
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
                className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-emerald-800 px-4 text-sm font-semibold text-white transition hover:bg-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:cursor-wait disabled:opacity-60"
                disabled={isSubmitting}
                type="submit"
              >
                {isSubmitting ? (
                  <LoaderCircle aria-hidden="true" className="animate-spin" size={18} />
                ) : (
                  <>
                    {isRegistration ? "Crear cuenta" : "Entrar"}
                    <ArrowRight aria-hidden="true" size={17} />
                  </>
                )}
              </button>
            </form>

            <p className="mt-7 text-sm text-slate-600">
              {isRegistration ? "¿Ya tienes cuenta? " : "¿Necesitas una cuenta? "}
              <Link
                className="font-semibold text-emerald-800 underline-offset-4 hover:underline"
                href={isRegistration ? "/login" : "/register"}
              >
                {isRegistration ? "Inicia sesión" : "Regístrate"}
              </Link>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}