"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  CircleAlert,
  ExternalLink,
  LoaderCircle,
  Mail,
  Phone,
  Plus,
  Trash2,
} from "lucide-react";

import {
  addNote,
  deleteNote,
  getCandidate,
  getNotes,
  updateCandidate,
} from "@/lib/api";
import {
  STAGES,
  STATUSES,
  type Candidate,
  type Note,
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

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-ES", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export default function CandidateDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [stageLoading, setStageLoading] = useState(false);
  const [noteDraft, setNoteDraft] = useState("");
  const [noteSaving, setNoteSaving] = useState(false);
  const [noteError, setNoteError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      return;
    }

    let active = true;

    async function loadCandidateData() {
      setLoading(true);
      setError(null);

      try {
        const [candidateData, notesResponse] = await Promise.all([
          getCandidate(id),
          getNotes(id),
        ]);

        if (active) {
          setCandidate(candidateData);
          setNotes(notesResponse.data);
        }
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "No se pudo cargar el perfil del candidato.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadCandidateData();

    return () => {
      active = false;
    };
  }, [id]);

  async function handleStatusChange(nextStatus: Status) {
    if (!candidate || candidate.status === nextStatus) {
      return;
    }

    setStatusLoading(true);
    setError(null);

    try {
      const updated = await updateCandidate(id, { status: nextStatus });
      setCandidate((current) =>
        current
          ? {
              ...current,
              status: updated.status,
              updated_at: updated.updated_at,
            }
          : current,
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo actualizar el estado.",
      );
    } finally {
      setStatusLoading(false);
    }
  }

  async function handleStageChange(nextStage: Stage) {
    if (!candidate || candidate.stage === nextStage) {
      return;
    }

    setStageLoading(true);
    setError(null);

    try {
      const updated = await updateCandidate(id, { stage: nextStage });
      setCandidate((current) =>
        current
          ? {
              ...current,
              stage: updated.stage,
              updated_at: updated.updated_at,
            }
          : current,
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo actualizar la etapa.",
      );
    } finally {
      setStageLoading(false);
    }
  }

  async function handleAddNote(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!noteDraft.trim()) {
      return;
    }

    setNoteSaving(true);
    setNoteError(null);

    try {
      const newNote = await addNote(id, { content: noteDraft.trim() });
      setNotes((current) => [newNote, ...current]);
      setCandidate((current) =>
        current
          ? {
              ...current,
              notes_count: current.notes_count + 1,
            }
          : current,
      );
      setNoteDraft("");
    } catch (requestError) {
      setNoteError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo guardar la nota.",
      );
    } finally {
      setNoteSaving(false);
    }
  }

  async function handleDeleteNote(noteId: string) {
    setNoteSaving(true);
    setNoteError(null);

    try {
      await deleteNote(id, noteId);
      setNotes((current) => current.filter((note) => note.id !== noteId));
      setCandidate((current) =>
        current
          ? {
              ...current,
              notes_count: Math.max(0, current.notes_count - 1),
            }
          : current,
      );
    } catch (requestError) {
      setNoteError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo borrar la nota.",
      );
    } finally {
      setNoteSaving(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-[#f6f7f2] p-6 text-slate-900">
        <div className="mx-auto flex max-w-5xl items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white p-10 shadow-sm">
          <LoaderCircle className="animate-spin text-emerald-700" size={22} />
          <p className="text-sm text-slate-600">Cargando perfil del candidato...</p>
        </div>
      </main>
    );
  }

  if (error || !candidate) {
    return (
      <main className="min-h-screen bg-[#f6f7f2] p-6 text-slate-900">
        <div className="mx-auto max-w-3xl rounded-2xl border border-red-200 bg-white p-8 text-center shadow-sm">
          <CircleAlert className="mx-auto text-red-600" size={28} />
          <h1 className="mt-4 text-2xl font-semibold">No se pudo cargar el perfil</h1>
          <p className="mt-2 text-sm text-slate-600">{error ?? "El candidato no existe."}</p>
          <Link
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
            href="/"
          >
            <ArrowLeft size={16} />
            Volver a la lista
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f6f7f2] p-4 text-slate-900 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-6xl">
        <Link
          className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-emerald-700"
          href="/"
        >
          <ArrowLeft size={16} />
          Volver a candidatos
        </Link>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
          <div className="flex flex-col gap-6 border-b border-slate-200 pb-6 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="mb-2 text-sm font-semibold uppercase tracking-[0.14em] text-emerald-700">
                Perfil candidato
              </p>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                {candidate.full_name}
              </h1>
              <p className="mt-2 text-base text-slate-600">{candidate.position}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className={`rounded-full px-3 py-1.5 text-xs font-semibold ring-1 ring-inset ${statusStyles[candidate.status]}`}>
                {statusLabels[candidate.status]}
              </span>
              <span className={`rounded-full px-3 py-1.5 text-xs font-semibold ring-1 ring-inset ${stageStyles[candidate.stage]}`}>
                {stageLabels[candidate.stage]}
              </span>
            </div>
          </div>

          <div className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <section className="space-y-6">
              <div>
                <h2 className="mb-3 text-lg font-semibold text-slate-900">Datos principales</h2>
                <div className="grid gap-4 sm:grid-cols-2">
                  <InfoField label="Email" value={candidate.email} icon={<Mail size={15} />} href={`mailto:${candidate.email}`} />
                  <InfoField label="Teléfono" value={candidate.phone} icon={<Phone size={15} />} href={candidate.phone ? `tel:${candidate.phone.replace(/\s+/g, "")}` : undefined} />
                  <InfoField label="LinkedIn" value={candidate.linkedin_url ?? "No disponible"} icon={<ExternalLink size={15} />} href={candidate.linkedin_url ?? undefined} />
                  <InfoField label="CV" value={candidate.cv_url ?? "No adjunto"} icon={<ExternalLink size={15} />} href={candidate.cv_url ?? undefined} />
                  <InfoField label="Experiencia" value={`${candidate.experience_years} años`} />
                  <InfoField label="Solicitud" value={formatDate(candidate.applied_at)} />
                  <InfoField label="Última actualización" value={formatDate(candidate.updated_at)} />
                  <InfoField label="Notas" value={`${candidate.notes_count}`} />
                </div>
              </div>

              <div>
                <h2 className="mb-3 text-lg font-semibold text-slate-900">Gestión del proceso</h2>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-slate-700">Estado</span>
                    <select
                      aria-label="Actualizar estado"
                      className="h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100 disabled:cursor-not-allowed disabled:bg-slate-50"
                      disabled={statusLoading}
                      onChange={(event) => void handleStatusChange(event.target.value as Status)}
                      value={candidate.status}
                    >
                      {STATUSES.map((status) => (
                        <option key={status} value={status}>
                          {statusLabels[status]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-slate-700">Etapa</span>
                    <select
                      aria-label="Actualizar etapa"
                      className="h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100 disabled:cursor-not-allowed disabled:bg-slate-50"
                      disabled={stageLoading}
                      onChange={(event) => void handleStageChange(event.target.value as Stage)}
                      value={candidate.stage}
                    >
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

            <aside className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">Notas</h2>
                <span className="rounded-full bg-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700">
                  {notes.length}
                </span>
              </div>

              <form className="mb-5 space-y-3" onSubmit={(event) => void handleAddNote(event)}>
                <textarea
                  aria-label="Añadir nota"
                  className="min-h-28 w-full rounded-xl border border-slate-200 bg-white p-3 text-sm outline-none focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"
                  onChange={(event) => setNoteDraft(event.target.value)}
                  placeholder="Añade una nota sobre la conversación, fit o próximos pasos..."
                  value={noteDraft}
                />
                <button
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-emerald-300"
                  disabled={noteSaving || !noteDraft.trim()}
                  type="submit"
                >
                  <Plus size={16} />
                  {noteSaving ? "Guardando..." : "Añadir nota"}
                </button>
                {noteError ? <p className="text-sm text-red-600">{noteError}</p> : null}
              </form>

              <div className="space-y-3">
                {notes.length === 0 ? (
                  <p className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">
                    Todavía no hay notas para este candidato.
                  </p>
                ) : (
                  notes.map((note) => (
                    <article key={note.id} className="rounded-xl border border-slate-200 bg-white p-3">
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">
                          {formatDate(note.created_at)}
                        </p>
                        <button
                          aria-label="Borrar nota"
                          className="inline-flex items-center gap-1 rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
                          onClick={() => void handleDeleteNote(note.id)}
                          type="button"
                        >
                          <Trash2 size={12} />
                          Borrar
                        </button>
                      </div>
                      <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">
                        {note.content}
                      </p>
                    </article>
                  ))
                )}
              </div>
            </aside>
          </div>
        </div>
      </div>
    </main>
  );
}

function InfoField({
  label,
  value,
  href,
  icon,
}: {
  label: string;
  value: string;
  href?: string;
  icon?: React.ReactNode;
}) {
  const content = (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">{label}</p>
      <div className="mt-2 flex items-center gap-2 text-sm text-slate-700">
        {icon ? <span className="text-slate-500">{icon}</span> : null}
        <span className="break-all">{value}</span>
      </div>
    </div>
  );

  if (!href) {
    return content;
  }

  return (
    <a className="block transition hover:opacity-90" href={href} rel="noreferrer" target="_blank">
      {content}
    </a>
  );
}
