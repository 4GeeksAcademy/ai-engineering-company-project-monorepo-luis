"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { CircleAlert, LoaderCircle } from "lucide-react";

import {
  getNexovaAccessToken,
  getNexovaCurrentUser,
  NexovaApiError,
} from "@/lib/nexova-api";

type GuardStatus = "checking" | "allowed" | "error";

function isPublicPath(pathname: string): boolean {
  return pathname === "/login" || pathname === "/register";
}

function isProtectedPath(pathname: string): boolean {
  return (
    pathname === "/" ||
    pathname.startsWith("/candidates/") ||
    pathname === "/account/profile"
  );
}

export default function NexovaAuthGuard({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();
  const [attempt, setAttempt] = useState(0);
  const [guardState, setGuardState] = useState<{
    pathname: string;
    status: GuardStatus;
  }>({ pathname: "", status: "checking" });

  useEffect(() => {
    if (!isProtectedPath(pathname)) {
      return;
    }

    let active = true;

    if (!getNexovaAccessToken()) {
      router.replace("/login");
      return () => {
        active = false;
      };
    }

    getNexovaCurrentUser()
      .then(() => {
        if (active) {
          setGuardState({ pathname, status: "allowed" });
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        if (error instanceof NexovaApiError && error.status === 401) {
          router.replace("/login");
          return;
        }

        setGuardState({ pathname, status: "error" });
      });

    return () => {
      active = false;
    };
  }, [attempt, pathname, router]);

  if (!isProtectedPath(pathname) || isPublicPath(pathname)) {
    return children;
  }

  const status =
    guardState.pathname === pathname ? guardState.status : "checking";

  if (status === "allowed") {
    return children;
  }

  if (status === "error") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f6f7f2] px-5 text-slate-950">
        <section
          aria-labelledby="auth-check-error"
          className="w-full max-w-md border-l-4 border-amber-500 bg-white p-6 shadow-sm"
        >
          <CircleAlert aria-hidden="true" className="text-amber-700" size={24} />
          <h1 className="mt-4 text-lg font-semibold" id="auth-check-error">
            No se pudo verificar tu sesión
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Comprueba tu conexión e inténtalo de nuevo. Tu sesión no se ha cerrado.
          </p>
          <button
            className="mt-5 min-h-10 rounded-lg bg-emerald-800 px-4 text-sm font-semibold text-white hover:bg-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
            onClick={() => {
              setGuardState({ pathname, status: "checking" });
              setAttempt((current) => current + 1);
            }}
            type="button"
          >
            Reintentar
          </button>
        </section>
      </main>
    );
  }

  return (
    <main
      aria-live="polite"
      className="flex min-h-screen items-center justify-center bg-[#f6f7f2] text-slate-600"
      role="status"
    >
      <div className="flex items-center gap-3">
        <LoaderCircle aria-hidden="true" className="animate-spin text-emerald-800" size={22} />
        <span className="text-sm">Verificando sesión...</span>
      </div>
    </main>
  );
}
