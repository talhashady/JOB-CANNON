import type {
  Application,
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
// In production, crash early if the env var is missing instead of silently
// calling localhost:8000 from the deployed site (which causes "Failed to fetch").
// Guard only runs in the browser — SSG prerendering doesn't need the API URL.
const _raw = process.env.NEXT_PUBLIC_API_URL;
if (!_raw && typeof window !== "undefined" && process.env.NODE_ENV === "production") {
  throw new Error(
    "NEXT_PUBLIC_API_URL is not set. " +
      "Add it to your Vercel project settings (Settings → Environment Variables) " +
      "and redeploy."
  );
}
const BASE = (_raw ?? "http://localhost:8000").replace(/\/+$/, "");

const TOKEN_KEY = "careeros_jwt";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token?: string): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function clearToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
  }
  fetch(`${BASE}/auth/logout`, { method: "POST", credentials: "include" }).catch(() => {});
}

/**
 * Core request helper.
 * - Sets JSON content-type only for non-FormData bodies (so file uploads work).
 * - Attaches Authorization Bearer token header if token is stored in localStorage.
 * - Adds a 30-second timeout via AbortController (handles backend cold-start).
 * - Retries once on network failure with a 2-second backoff.
 */
async function http<T>(operation: string, path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`;
  const method = (init && init.method) || "GET";
  const where = `${method} ${path}`; // Use path only, not full URL (privacy)

  const headers: Record<string, string> = { ...((init && (init.headers as Record<string, string>)) || {}) };
  const token = getToken();
  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const isForm = typeof FormData !== "undefined" && init?.body instanceof FormData;
  if (init?.body && !isForm && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  // CSRF protection: send custom header on all state-changing requests
  if (method !== "GET" && method !== "HEAD" && method !== "OPTIONS") {
    headers["X-Requested-With"] = "XMLHttpRequest";
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
      // Surface a friendlier message than the raw "Failed to fetch" TypeError.
      const raw = retryErr instanceof Error ? retryErr : new Error(String(retryErr));
      if (raw.name === "TypeError" || /failed to fetch/i.test(raw.message)) {
        throw new Error("Could not reach the server \u2014 check your connection or try again in a few seconds.");
      }
      throw raw;
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
    // Use path (not full URL) in error message for user privacy
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
  signup: async (body: { email: string; password: string; full_name: string }) => {
    const res = await http<{ user: PublicUser; token?: string }>("Sign up", "/auth/signup", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (res.token) setToken(res.token);
    return res;
  },

  login: async (body: { email: string; password: string }) => {
    const res = await http<{ user: PublicUser; token?: string }>("Log in", "/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (res.token) setToken(res.token);
    return res;
  },

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

  updateApplicationStatus: (id: string, status: string, note = "") =>
    http<Application>("Update application status", `/applications/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, note }),
    }),
};
