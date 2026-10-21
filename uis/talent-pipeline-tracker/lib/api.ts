import type {
  Candidate,
  CandidateInput,
  CandidateStatusUpdate,
  CandidatesQuery,
  Note,
  NoteInput,
  NotesResponse,
  PaginatedResponse,
} from "@/types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "https://playground.4geeks.com/tracker/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
  } catch {
    throw new Error(
      "No se pudo conectar con el servicio de talento. Comprueba tu conexión a internet e inténtalo de nuevo.",
    );
  }

  if (!response.ok) {
    let message = "La solicitud no pudo completarse. Inténtalo de nuevo más tarde.";

    try {
      const error = (await response.json()) as { message?: string; detail?: string };
      if (typeof error.message === "string" && error.message.trim()) {
        message = error.message;
      } else if (typeof error.detail === "string" && error.detail.trim()) {
        message = error.detail;
      }
    } catch {
      if (response.status === 404) {
        message = "El registro solicitado no fue encontrado o ya no está disponible.";
      } else if (response.status === 401 || response.status === 403) {
        message = "No tienes permisos suficientes para realizar esta acción.";
      } else if (response.status >= 500) {
        message = "El servidor encontró un error temporal. Inténtalo de nuevo más tarde.";
      }
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function buildQuery(query: CandidatesQuery = {}) {
  const params = new URLSearchParams();

  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  });

  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
}

export async function getCandidates(
  query?: CandidatesQuery,
): Promise<PaginatedResponse<Candidate>> {
  return request<PaginatedResponse<Candidate>>(`/records${buildQuery(query)}`);
}

export async function getCandidate(id: string): Promise<Candidate> {
  return request<Candidate>(`/records/${id}`);
}

export async function updateCandidate(
  id: string,
  update: CandidateStatusUpdate,
): Promise<Candidate> {
  return request<Candidate>(`/records/${id}`, {
    method: "PATCH",
    body: JSON.stringify(update),
  });
}

export async function createCandidate(input: CandidateInput): Promise<Candidate> {
  return request<Candidate>("/records", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function editCandidate(
  id: string,
  input: CandidateInput,
): Promise<Candidate> {
  return request<Candidate>(`/records/${id}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export async function getNotes(id: string): Promise<NotesResponse> {
  return request<NotesResponse>(`/records/${id}/notes`);
}

export async function addNote(id: string, input: NoteInput): Promise<Note> {
  return request<Note>(`/records/${id}/notes`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function deleteNote(id: string, noteId: string): Promise<void> {
  return request<void>(`/records/${id}/notes/${noteId}`, {
    method: "DELETE",
  });
}
