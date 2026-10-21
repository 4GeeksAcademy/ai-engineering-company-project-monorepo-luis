import type {
  NexovaAuthActionResponse,
  NexovaChangePasswordInput,
  NexovaCurrentUser,
  NexovaForgotPasswordInput,
  NexovaLoginInput,
  NexovaProfile,
  NexovaProfileUpdate,
  NexovaRegistrationInput,
  NexovaResetPasswordInput,
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

  let response: Response;
  try {
    response = await fetch(`${NEXOVA_API_URL}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new NexovaApiError(
      "No se pudo conectar con el servicio de autenticación. Comprueba tu conexión e inténtalo de nuevo.",
      0,
    );
  }

  if (!response.ok) {
    let message = "La solicitud no pudo procesarse correctamente.";

    try {
      const error = (await response.json()) as { detail?: unknown; message?: unknown };
      if (typeof error.detail === "string" && error.detail.trim()) {
        message = error.detail;
      } else if (typeof error.message === "string" && error.message.trim()) {
        message = error.message;
      }
    } catch {
      if (response.status === 401) {
        message = "Inicia sesión para continuar.";
      } else if (response.status === 403) {
        message = "No tienes permisos suficientes para realizar esta acción.";
      } else if (response.status === 404) {
        message = "El recurso solicitado no fue encontrado.";
      } else if (response.status >= 500) {
        message = "El servicio de Nexova no está disponible temporalmente. Inténtalo más tarde.";
      }
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

export function requestNexovaPasswordReset(
  input: NexovaForgotPasswordInput,
): Promise<NexovaAuthActionResponse> {
  return request<NexovaAuthActionResponse>(
    "/auth/forgot-password",
    { method: "POST", body: JSON.stringify(input) },
    "public",
  );
}

export function resetNexovaPassword(
  input: NexovaResetPasswordInput,
): Promise<NexovaAuthActionResponse> {
  return request<NexovaAuthActionResponse>(
    "/auth/reset-password",
    { method: "POST", body: JSON.stringify(input) },
    "public",
  );
}

export function changeNexovaPassword(
  input: NexovaChangePasswordInput,
): Promise<NexovaAuthActionResponse> {
  return request<NexovaAuthActionResponse>(
    "/auth/change-password",
    { method: "POST", body: JSON.stringify(input) },
    "required",
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
