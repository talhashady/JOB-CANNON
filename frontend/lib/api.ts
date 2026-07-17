import type {
  Application,
  AuthResponse,
  AutoApplyParams,
  AutoApplyResult,
  HealthResponse,
  PipelineResult,
  PublicUser,
  RunParams,
  UserProfile,
} from "./types";
import { logError } from "./logger";

// Trailing slash stripped so `${BASE}${path}` never produces a double slash.
const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

const TOKEN_KEY = "careeros_token";
const SESSION_FLAG = "careeros_has_session";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  // Only report "have token" if the user has signed in during this browser session
  return sessionStorage.getItem(SESSION_FLAG);
}
function setToken(_token: string): void {
  // Token is stored in httpOnly cookie by the backend; mark that we have a session
  if (typeof window !== "undefined") sessionStorage.setItem(SESSION_FLAG, "1");
}
function clearToken(): void {
  // Clear the session flag and tell the backend to delete the cookie
  if (typeof window !== "undefined") sessionStorage.removeItem(SESSION_FLAG);
  fetch(`${BASE}/auth/logout`, { method: "POST", credentials: "include" }).catch(() => {});
}

/**
 * Core request helper.
 * - Sets JSON content-type only for non-FormData bodies (so file uploads work).
 * - Adds a 30-second timeout via AbortController (handles backend cold-start).
 * - Retries once on network failure with a 2-second backoff.
 * - On ANY failure (network or HTTP) it logs the RAW error with full context
 *   (operation + url + raw error) and rethrows the raw error - nothing hidden.
 */
async function http<T>(operation: string, path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`;
  const method = (init && init.method) || "GET";
  const where = `${method} ${url}`;

  const headers: Record<string, string> = { ...((init && (init.headers as Record<string, string>)) || {}) };
  const isForm = typeof FormData !== "undefined" && init?.body instanceof FormData;
  if (init?.body && !isForm && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const doFetch = async (): Promise<Response> => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30_000);
    try {
      return await fetch(url, {
        ...init,
        headers,
        credentials: "include",
        cache: "no-store",
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeout);
    }
  };

  let res: Response;
  try {
    res = await doFetch();
  } catch (err) {
    // Network-level failure: retry once after 2s backoff (handles backend cold-start).
    await new Promise((r) => setTimeout(r, 2000));
    try {
      res = await doFetch();
    } catch (retryErr) {
      logError(`${operation} (network)`, where, retryErr);
      throw retryErr instanceof Error ? retryErr : new Error(String(retryErr));
    }
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body && body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* response had no JSON body */
    }
    const error = new Error(`HTTP ${res.status} ${detail}`);
    logError(operation, where, error);
    throw error;
  }

  return res.json() as Promise<T>;
}

export const api = {
  baseUrl: BASE,
  getToken,
  setToken,
  clearToken,

  health: () => http<HealthResponse>("Health check", "/health"),

  // --- auth ---
  signup: (body: { email: string; password: string; full_name: string }) =>
    http<AuthResponse>("Sign up", "/auth/signup", { method: "POST", body: JSON.stringify(body) }),

  login: (body: { email: string; password: string }) =>
    http<AuthResponse>("Log in", "/auth/login", { method: "POST", body: JSON.stringify(body) }),

  me: () => http<PublicUser>("Load current user", "/auth/me"),

  // --- profile ---
  createProfile: (cv_text: string, career_goals = "") =>
    http<UserProfile>("Save profile", "/profiles", {
      method: "POST",
      body: JSON.stringify({ cv_text, career_goals }),
    }),

  uploadCv: (file: File, career_goals = "") => {
    const form = new FormData();
    form.append("file", file);
    form.append("career_goals", career_goals);
    return http<UserProfile>("Upload CV", "/profiles/upload", { method: "POST", body: form });
  },

  // --- pipeline ---
  run: (params: RunParams) =>
    http<{ task_id: string }>("Run pipeline", "/run", { method: "POST", body: JSON.stringify(params) }),

  pollTask: (taskId: string) =>
    http<{ status: string; result: PipelineResult | null; error: string | null }>("Poll task status", `/run/${taskId}`),

  autoApply: (params: AutoApplyParams) =>
    http<AutoApplyResult>("Auto-apply", "/auto-apply", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  applicationsMe: () => http<Application[]>("Load applications", "/applications/me"),
};
