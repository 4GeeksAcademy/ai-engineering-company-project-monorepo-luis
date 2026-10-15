import type {
  NexovaCurrentUser,
  NexovaLoginInput,
  NexovaProfile,
  NexovaProfileUpdate,
  NexovaRegistrationInput,
  NexovaTokenResponse,
  NexovaUser,
} from "@/types/auth";

const ACCESS_TOKEN_KEY = "nexova_access_token";
const NEXOVA_API_URL = process.env.NEXT_PUBLIC_NEXOVA_API_URL?.replace(/\/$/, "");
export const NEXOVA_SESSION_EXPIRED_EVENT = "nexova:session-expired";

type Authentication = "public" | "required";

export class NexovaApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "NexovaApiError";
  }
}

export function getNexovaAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function storeNexovaAccessToken(token: string): void {
  if (typeof window === "undefined") {
    throw new Error("La sesión solo puede guardarse desde el navegador.");
  }

  window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearNexovaSession(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  }
}

export function redirectToNexovaLogin(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(NEXOVA_SESSION_EXPIRED_EVENT));
  }
}

export function endNexovaSession(): void {
  clearNexovaSession();
  redirectToNexovaLogin();
}

async function request<T>(
  path: string,
  options: RequestInit,
  authentication: Authentication,
): Promise<T> {
  if (!NEXOVA_API_URL) {
    throw new Error("Falta configurar NEXT_PUBLIC_NEXOVA_API_URL.");
  }

  const headers = new Headers(options.headers);
  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (authentication === "required") {
    const token = getNexovaAccessToken();
    if (!token) {
      endNexovaSession();
      throw new NexovaApiError("Inicia sesión para continuar.", 401);
    }
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${NEXOVA_API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = `La solicitud a Nexova falló (${response.status}).`;

    try {
      const error = (await response.json()) as { detail?: unknown; message?: unknown };
      if (typeof error.detail === "string") {
        message = error.detail;
      } else if (typeof error.message === "string") {
        message = error.message;
      }
    } catch {
      message = response.statusText || message;
    }

    if (authentication === "required" && response.status === 401) {
      endNexovaSession();
    }

    throw new NexovaApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function registerNexovaUser(
  input: NexovaRegistrationInput,
): Promise<NexovaUser> {
  return request<NexovaUser>(
    "/users",
    { method: "POST", body: JSON.stringify(input) },
    "public",
  );
}

export function loginToNexova(input: NexovaLoginInput): Promise<NexovaTokenResponse> {
  return request<NexovaTokenResponse>(
    "/auth/login",
    { method: "POST", body: JSON.stringify(input) },
    "public",
  );
}

export function getNexovaCurrentUser(): Promise<NexovaCurrentUser> {
  return request<NexovaCurrentUser>("/auth/me", {}, "required");
}

export function getNexovaProfile(): Promise<NexovaProfile> {
  return request<NexovaProfile>("/profiles/me", {}, "required");
}

export function updateNexovaProfile(
  update: NexovaProfileUpdate,
): Promise<NexovaProfile> {
  return request<NexovaProfile>(
    "/profiles/me",
    { method: "PUT", body: JSON.stringify(update) },
    "required",
  );
}
