"use client";

/**
 * Lightweight activity + error bus for the whole frontend.
 *
 * Any component can call logStep / logSuccess / logInfo / logError and the
 * <ErrorLogger /> panel (mounted in app/layout.tsx) will show it live.
 *
 * Errors are shown RAW - no friendly rewrites. logError() always records exactly:
 *   - what it tried to execute (operation)
 *   - where it happened (url / location)
 *   - the raw error (message + stack / JSON)
 */

export type ActivityLevel = "info" | "step" | "success" | "warn" | "error";

export interface ActivityPayload {
  level: ActivityLevel;
  message: string;
  details?: string;
}

export const ACTIVITY_EVENT = "careeros:activity";

export function logActivity(level: ActivityLevel, message: string, details?: string): void {
  if (typeof window === "undefined") return;
  const payload: ActivityPayload = { level, message, details };
  window.dispatchEvent(new CustomEvent<ActivityPayload>(ACTIVITY_EVENT, { detail: payload }));
}

export const logInfo = (message: string, details?: string) => logActivity("info", message, details);
export const logStep = (message: string, details?: string) => logActivity("step", message, details);
export const logSuccess = (message: string, details?: string) =>
  logActivity("success", message, details);
export const logWarn = (message: string, details?: string) => logActivity("warn", message, details);

export function rawErrorText(error: unknown): string {
  if (error instanceof Error) return error.stack || `${error.name}: ${error.message}`;
  if (typeof error === "string") return error;
  try {
    return JSON.stringify(error, null, 2);
  } catch {
    return String(error);
  }
}

/**
 * Record a raw error with full context. `operation` = what you tried to do,
 * `where` = the URL or code location, `error` = the caught value (shown raw).
 */
export function logError(operation: string, where: string, error: unknown): void {
  const raw = rawErrorText(error);
  const details =
    `What it tried : ${operation}\n` +
    `Where         : ${where}\n` +
    `Raw error     : ${raw}`;
  logActivity("error", `${operation} - FAILED`, details);
}
