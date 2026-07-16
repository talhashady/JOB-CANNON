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

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  // Dummy token to trigger auth check on mount in auth.tsx (cookies are used for actual auth)
  return "session";
}
function setToken(token: string): void {
  // No-op: token is stored in httpOnly cookie
}
function clearToken(): void {
  // Clear cookie on backend via POST logout
  fetch(`${BASE}/auth/logout`, { method: "POST", credentials: "include" }).catch(() => {});
}

/**
 * Core request helper.
 * - Sets JSON content-type only for non-FormData bodies (so file uploads work).
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

  let res: Response;
  try {
    res = await fetch(url, { ...init, headers, credentials: "include", cache: "no-store" });
  } catch (err) {
    // Network-level failure: DNS, CORS, backend asleep, wrong/missing API URL, offline.
    logError(`${operation} (network)`, where, err);
    throw err instanceof Error ? err : new Error(String(err));
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
