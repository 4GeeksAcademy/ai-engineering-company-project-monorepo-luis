"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CircleAlert, LoaderCircle, Save } from "lucide-react";

import {
  getNexovaCurrentUser,
  NexovaApiError,
  updateNexovaProfile,
} from "@/lib/nexova-api";
import type { NexovaCurrentUser, NexovaProfileUpdate } from "@/types/auth";

type ProfileFields = {
  name: string;
  phone: string;
  address: string;
};

const emptyFields: ProfileFields = {
  name: "",
  phone: "",
  address: "",
};

function getLoadError(error: unknown): string {
  if (error instanceof NexovaApiError) {
    if (error.status === 404) {
      return "No encontramos un perfil asociado a esta cuenta.";
    }
    if (error.status >= 500) {
      return "El servicio de perfiles no está disponible ahora. Inténtalo más tarde.";
    }
  }

  return "No pudimos cargar tu perfil. Comprueba tu conexión e inténtalo de nuevo.";
}

function getSaveError(error: unknown): string {
  if (error instanceof NexovaApiError && error.status >= 500) {
    return "No se pudo guardar el perfil por un problema del servicio. Inténtalo más tarde.";
  }

  return "No se pudieron guardar los cambios. Revisa tu conexión e inténtalo de nuevo.";
}

export default function AccountProfile() {
  const [attempt, setAttempt] = useState(0);
  const [user, setUser] = useState<NexovaCurrentUser | null>(null);
  const [fields, setFields] = useState<ProfileFields>(emptyFields);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let active = true;

    getNexovaCurrentUser()
      .then((currentUser) => {
        if (active) {
          setUser(currentUser);
          setFields({
            name: currentUser.profile.name ?? "",
            phone: currentUser.profile.phone ?? "",
            address: currentUser.profile.address ?? "",
          });
        }
      })
      .catch((error: unknown) => {
        if (active && !(error instanceof NexovaApiError && error.status === 401)) {
          setLoadError(getLoadError(error));
        }
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [attempt]);

  function updateField(field: keyof ProfileFields, value: string) {
    setFields((current) => ({ ...current, [field]: value }));
    setSaved(false);
    setSaveError(null);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setSaveError(null);
    setSaved(false);

    const update: NexovaProfileUpdate = {
      name: fields.name.trim() || null,
      phone: fields.phone.trim() || null,
      address: fields.address.trim() || null,
    };

    try {
      const profile = await updateNexovaProfile(update);
      setUser((current) =>
        current ? { ...current, profile } : current,
      );
      setFields({
        name: profile.name ?? "",
        phone: profile.phone ?? "",
        address: profile.address ?? "",
      });
      setSaved(true);
    } catch (error) {
      if (!(error instanceof NexovaApiError && error.status === 401)) {
        setSaveError(getSaveError(error));
      }
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f6f7f2] px-5 py-8 text-slate-950 sm:px-8 lg:px-10 lg:py-12">
      <div className="mx-auto w-full max-w-7xl">
        <Link
          className="inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-emerald-800 hover:text-emerald-950 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-800"
          href="/"
        >
          <ArrowLeft aria-hidden="true" size={17} />
          Volver al pipeline
        </Link>

        <header className="mt-8 border-b border-slate-200 pb-7">
          <p className="text-sm font-semibold uppercase text-emerald-800">
            Cuenta Nexova
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
            Perfil de cuenta
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            Consulta y actualiza los datos de contacto asociados a tu cuenta.
          </p>
        </header>

        {isLoading ? (
          <div
            aria-live="polite"
            className="flex min-h-64 items-center justify-center gap-3 text-slate-600"
            role="status"
          >
            <LoaderCircle aria-hidden="true" className="animate-spin text-emerald-800" size={22} />
            <span className="text-sm">Cargando perfil...</span>
          </div>
        ) : loadError ? (
          <section
            aria-labelledby="profile-load-error"
            className="mt-8 max-w-xl border-l-4 border-amber-500 bg-white p-6 shadow-sm"
          >
            <CircleAlert aria-hidden="true" className="text-amber-700" size={24} />
            <h2 className="mt-4 text-lg font-semibold" id="profile-load-error">
              No se pudo cargar el perfil
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">{loadError}</p>
            <button
              className="mt-5 min-h-10 rounded-lg bg-emerald-800 px-4 text-sm font-semibold text-white hover:bg-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
              onClick={() => {
                setIsLoading(true);
                setLoadError(null);
                setAttempt((current) => current + 1);
              }}
              type="button"
            >
              Reintentar
            </button>
          </section>
        ) : user ? (
          <section className="mt-8 max-w-2xl rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
            <div className="mb-7 border-b border-slate-100 pb-5">
              <p className="text-xs font-semibold uppercase text-slate-500">
                Email de la cuenta
              </p>
              <p className="mt-2 break-all text-base font-medium text-slate-900">
                {user.email}
              </p>
            </div>

            <form className="space-y-5" onSubmit={handleSubmit}>
              <div>
                <label className="mb-2 block text-sm font-medium" htmlFor="profile-name">
                  Nombre
                </label>
                <input
                  autoComplete="name"
                  className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
                  id="profile-name"
                  onChange={(event) => updateField("name", event.target.value)}
                  value={fields.name}
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium" htmlFor="profile-phone">
                  Teléfono
                </label>
                <input
                  autoComplete="tel"
                  className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
                  id="profile-phone"
                  onChange={(event) => updateField("phone", event.target.value)}
                  type="tel"
                  value={fields.phone}
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium" htmlFor="profile-address">
                  Dirección
                </label>
                <input
                  autoComplete="street-address"
                  className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
                  id="profile-address"
                  onChange={(event) => updateField("address", event.target.value)}
                  value={fields.address}
                />
              </div>

              {saveError ? (
                <p aria-live="polite" className="text-sm text-red-800" role="alert">
                  {saveError}
                </p>
              ) : null}
              {saved ? (
                <p aria-live="polite" className="text-sm font-medium text-emerald-800" role="status">
                  Cambios guardados.
                </p>
              ) : null}

              <button
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-emerald-800 px-4 text-sm font-semibold text-white transition hover:bg-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:cursor-wait disabled:opacity-60"
                disabled={isSaving}
                type="submit"
              >
                {isSaving ? (
                  <LoaderCircle aria-hidden="true" className="animate-spin" size={17} />
                ) : (
                  <Save aria-hidden="true" size={17} />
                )}
                Guardar cambios
              </button>
            </form>
          </section>
        ) : null}
      </div>
    </main>
  );
}