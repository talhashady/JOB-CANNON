import type {
  Application,
  AuthResponse,
  AutoApplyResult,
  PipelineResult,
  PublicUser,
  RunParams,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "careeros_token";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}
function setToken(token: string): void {
  if (typeof window !== "undefined") window.localStorage.setItem(TOKEN_KEY, token);
}
function clearToken(): void {
  if (typeof window !== "undefined") window.localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getToken();
  return {
    ...(extra || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function parseError(res: Response): Promise<string> {
  let detail = res.statusText;
  try {
    const body = await res.json();
    detail = body.detail ?? detail;
  } catch {
    /* ignore */
  }
  return `${res.status}: ${detail}`;
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: authHeaders({ "Content-Type": "application/json", ...(init?.headers || {}) }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<T>;
}

export const api = {
  baseUrl: BASE,
  getToken,
  setToken,
  clearToken,

  health: () =>
    http<{ status: string; llm_enabled: boolean; live_apply: boolean; smtp_configured: boolean }>(
      "/health"
    ),

  signup: (body: { email: string; password: string; full_name: string }) =>
    http<AuthResponse>("/auth/signup", { method: "POST", body: JSON.stringify(body) }),

  login: (body: { email: string; password: string }) =>
    http<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(body) }),

  me: () => http<PublicUser>("/auth/me"),

  createProfile: (cv_text: string, career_goals = "") =>
    http("/profiles", { method: "POST", body: JSON.stringify({ cv_text, career_goals }) }),

  uploadCv: async (file: File, career_goals = "") => {
    const form = new FormData();
    form.append("file", file);
    form.append("career_goals", career_goals);
    const res = await fetch(`${BASE}/profiles/upload`, {
      method: "POST",
      headers: authHeaders(), // do NOT set Content-Type; browser adds the multipart boundary
      body: form,
      cache: "no-store",
    });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json();
  },

  run: (params: RunParams) =>
    http<PipelineResult>("/run", { method: "POST", body: JSON.stringify(params) }),

  autoApply: (params: {
    query: string;
    location: string;
    sites: string[];
    results_wanted: number;
    is_remote: boolean;
    min_score: number;
    max_applications: number;
  }) => http<AutoApplyResult>("/auto-apply", { method: "POST", body: JSON.stringify(params) }),

  applicationsMe: () => http<Application[]>("/applications/me"),
};
