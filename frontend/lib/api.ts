import type { Application, PipelineResult, RunParams } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  baseUrl: BASE,

  health: () => http<{ status: string; llm_enabled: boolean; live_apply: boolean }>("/health"),

  createProfile: (user_id: string, cv_text: string, career_goals = "") =>
    http("/profiles", {
      method: "POST",
      body: JSON.stringify({ user_id, cv_text, career_goals }),
    }),

  run: (params: RunParams) =>
    http<PipelineResult>("/run", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  applications: (user_id: string) => http<Application[]>(`/applications/${user_id}`),
};
