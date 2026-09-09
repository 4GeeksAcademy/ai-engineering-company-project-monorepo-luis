"use client";

import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  ArrowRight,
  BriefcaseBusiness,
  CircleAlert,
  Filter,
  LoaderCircle,
  Search,
  Users,
} from "lucide-react";

import { getCandidates } from "@/lib/api";
import {
  STAGES,
  STATUSES,
  type Candidate,
  type Stage,
  type Status,
} from "@/types";

const statusLabels: Record<Status, string> = {
  received: "Recibido",
  in_progress: "En proceso",
  discarded: "Descartado",
};

const stageLabels: Record<Stage, string> = {
  pending: "Pendiente",
  review: "Revisión",
  personal_interview: "Entrevista personal",
  technical_interview: "Entrevista técnica",
};

const statusStyles: Record<Status, string> = {
  received: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  in_progress: "bg-amber-50 text-amber-700 ring-amber-200",
  discarded: "bg-slate-100 text-slate-600 ring-slate-200",
};

const stageStyles: Record<Stage, string> = {
  pending: "bg-sky-50 text-sky-700 ring-sky-200",
  review: "bg-violet-50 text-violet-700 ring-violet-200",
  personal_interview: "bg-orange-50 text-orange-700 ring-orange-200",
  technical_interview: "bg-rose-50 text-rose-700 ring-rose-200",
};

function isStatus(value: string | null): value is Status {
  return value !== null && STATUSES.includes(value as Status);
}

function isStage(value: string | null): value is Stage {
  return value !== null && STAGES.includes(value as Stage);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-ES", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function updateQuery(
  pathname: string,
  current: URLSearchParams,
  key: string,
  value: string,
) {
  const next = new URLSearchParams(current.toString());

  if (value) {
    next.set(key, value);
  } else {
    next.delete(key);
  }

  next.delete("page");
  const query = next.toString();
  return query ? `${pathname}?${query}` : pathname;
}

export default function CandidateList() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryString = searchParams.toString();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const rawStatus = searchParams.get("status");
  const rawStage = searchParams.get("stage");
  const selectedStatus = isStatus(rawStatus) ? rawStatus : undefined;
  const selectedStage = isStage(rawStage) ? rawStage : undefined;

  useEffect(() => {
    let active = true;

    async function loadCandidates() {
      setLoading(true);
      setError(null);

      try {
        const response = await getCandidates({
          search: searchParams.get("search") || undefined,
          stage: selectedStage,
          status: selectedStatus,
        });

        if (active) {
          setCandidates(response.data);
          setTotal(response.total);
        }
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "No se pudo cargar la bolsa de talento.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadCandidates();

    return () => {
      active = false;
    };
  }, [queryString, searchParams, selectedStage, selectedStatus]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    router.replace(updateQuery(pathname, searchParams, "search", search.trim()));
  }

  function handleFilterChange(key: "status" | "stage", value: string) {
    router.replace(updateQuery(pathname, searchParams, key, value));
  }

  const hasFilters = Boolean(
    searchParams.get("search") || selectedStatus || selectedStage,
  );

  return (
    <main className="min-h-screen bg-[#f6f7f2] text-slate-950">
      <div className="mx-auto w-full max-w-7xl px-5 py-8 sm:px-8 lg:px-10 lg:py-12">
        <header className="mb-10 flex flex-col justify-between gap-6 border-b border-slate-200 pb-8 md:flex-row md:items-end">
          <div>
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold tracking-wide text-emerald-700">
              <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-700 text-white">
                <BriefcaseBusiness size={17} />
              </span>
              NEXOVA / TALENTO
            </div>
            <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
              Pipeline de candidatos
            </h1>
            <p className="mt-3 max-w-xl text-base leading-7 text-slate-600">
              Una vista clara del talento que está avanzando con Nexova.
            </p>
          </div>
          <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
            <Users className="text-emerald-700" size={20} />
            <div>
              <p className="text-2xl font-semibold leading-none">{total}</p>
              <p className="mt-1 text-xs font-medium uppercase tracking-wider text-slate-500">
                perfiles en cartera
              </p>
            </div>
          </div>
        </header>

        <section aria-label="Filtros de candidatos" className="mb-6">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <form onSubmit={handleSearch} className="relative min-w-0 flex-1">
              <Search
                aria-hidden="true"
                className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                size={19}
              />
              <input
                aria-label="Buscar por nombre o email"
                className="h-12 w-full rounded-xl border border-slate-200 bg-white pl-11 pr-4 text-sm outline-none transition placeholder:text-slate-400 focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar por nombre o email"
                type="search"
                value={search}
              />
            </form>
            <div className="flex flex-col gap-3 sm:flex-row">
              <label className="relative flex h-12 items-center rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm text-slate-700 focus-within:border-emerald-600 focus-within:ring-4 focus-within:ring-emerald-100">
                <Filter className="absolute left-3 text-slate-400" size={16} />
                <span className="sr-only">Filtrar por estado</span>
                <select
                  aria-label="Filtrar por estado"
                  className="bg-transparent outline-none"
                  onChange={(event) =>
                    handleFilterChange("status", event.target.value)
                  }
                  value={selectedStatus ?? ""}
                >
                  <option value="">Todos los estados</option>
                  {STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {statusLabels[status]}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex h-12 items-center rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 focus-within:border-emerald-600 focus-within:ring-4 focus-within:ring-emerald-100">
                <span className="sr-only">Filtrar por etapa</span>
                <select
                  aria-label="Filtrar por etapa"
                  className="bg-transparent outline-none"
                  onChange={(event) =>
                    handleFilterChange("stage", event.target.value)
                  }
                  value={selectedStage ?? ""}
                >
                  <option value="">Todas las etapas</option>
                  {STAGES.map((stage) => (
                    <option key={stage} value={stage}>
                      {stageLabels[stage]}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
        </section>

        <section
          aria-live="polite"
          className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
        >
          {loading ? (
            <div className="flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-slate-500">
              <LoaderCircle className="animate-spin text-emerald-700" size={26} />
              <p className="text-sm">Cargando perfiles de talento...</p>
            </div>
          ) : error ? (
            <div className="flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-center">
              <CircleAlert className="text-red-600" size={28} />
              <div>
                <h2 className="font-semibold text-slate-900">
                  No pudimos cargar los candidatos
                </h2>
                <p className="mt-1 text-sm text-slate-500">{error}</p>
              </div>
              <button
                className="mt-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800"
                onClick={() => router.refresh()}
                type="button"
              >
                Intentar de nuevo
              </button>
            </div>
          ) : candidates.length === 0 ? (
            <div className="flex min-h-72 flex-col items-center justify-center p-8 text-center">
              <Search className="text-slate-400" size={28} />
              <h2 className="mt-3 font-semibold text-slate-900">
                No encontramos perfiles
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                {hasFilters
                  ? "Prueba a cambiar los filtros de búsqueda."
                  : "Todavía no hay candidatos en la cartera."}
              </p>
            </div>
          ) : (
            <>
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full min-w-[760px] text-left">
                  <thead className="border-b border-slate-200 bg-slate-50/70">
                    <tr className="text-xs uppercase tracking-wider text-slate-500">
                      <th className="px-6 py-4 font-semibold">Candidato</th>
                      <th className="px-6 py-4 font-semibold">Posición</th>
                      <th className="px-6 py-4 font-semibold">Estado</th>
                      <th className="px-6 py-4 font-semibold">Etapa</th>
                      <th className="px-6 py-4 font-semibold">Solicitud</th>
                      <th aria-label="Abrir detalle" className="px-6 py-4" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {candidates.map((candidate) => (
                      <CandidateRow candidate={candidate} key={candidate.id} />
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="divide-y divide-slate-100 md:hidden">
                {candidates.map((candidate) => (
                  <CandidateCard candidate={candidate} key={candidate.id} />
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}

function CandidateRow({ candidate }: { candidate: Candidate }) {
  return (
    <tr className="group transition-colors hover:bg-emerald-50/30">
      <td className="px-6 py-5">
        <Link className="block" href={`/candidates/${candidate.id}`}>
          <p className="font-semibold text-slate-900 group-hover:text-emerald-800">
            {candidate.full_name}
          </p>
          <p className="mt-1 text-sm text-slate-500">{candidate.email}</p>
        </Link>
      </td>
      <td className="px-6 py-5 text-sm text-slate-700">{candidate.position}</td>
      <td className="px-6 py-5">
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${statusStyles[candidate.status]}`}
        >
          {statusLabels[candidate.status]}
        </span>
      </td>
      <td className="px-6 py-5">
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${stageStyles[candidate.stage]}`}
        >
          {stageLabels[candidate.stage]}
        </span>
      </td>
      <td className="px-6 py-5 text-sm text-slate-500">
        {formatDate(candidate.applied_at)}
      </td>
      <td className="px-6 py-5 text-right">
        <Link
          aria-label={`Abrir perfil de ${candidate.full_name}`}
          href={`/candidates/${candidate.id}`}
        >
          <ArrowRight
            className="ml-auto text-slate-400 transition group-hover:translate-x-1 group-hover:text-emerald-700"
            size={19}
          />
        </Link>
      </td>
    </tr>
  );
}

function CandidateCard({ candidate }: { candidate: Candidate }) {
  return (
    <Link
      className="block p-5 transition-colors hover:bg-emerald-50/30"
      href={`/candidates/${candidate.id}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-semibold text-slate-900">{candidate.full_name}</p>
          <p className="mt-1 text-sm text-slate-500">{candidate.email}</p>
        </div>
        <ArrowRight className="shrink-0 text-slate-400" size={19} />
      </div>
      <p className="mt-4 text-sm text-slate-700">{candidate.position}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${statusStyles[candidate.status]}`}
        >
          {statusLabels[candidate.status]}
        </span>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${stageStyles[candidate.stage]}`}
        >
          {stageLabels[candidate.stage]}
        </span>
      </div>
    </Link>
  );
}