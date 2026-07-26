"use client";

/**
 * Lightweight activity + error bus for the whole frontend.
 *
 * Any component can call logStep / logSuccess / logInfo / logError and the
 * <ErrorLogger /> panel (mounted in app/layout.tsx) will show it live.
 *
 * Errors are sanitized for the user - raw diagnostics go to console.error only.
 */

export type ActivityLevel = "info" | "step" | "success" | "warn" | "error";

export interface ActivityPayload {
  level: ActivityLevel;
  message: string;
  details?: string;
}

export const ACTIVITY_EVENT = "jobcannon:activity";

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

function rawErrorText(error: unknown): string {
  if (error instanceof Error) return error.stack || `${error.name}: ${error.message}`;
  if (typeof error === "string") return error;
  try {
    return JSON.stringify(error, null, 2);
  } catch {
    return String(error);
  }
}

/**
 * Extract an HTTP status code from an error message like "HTTP 401 Unauthorized".
 */
function extractHttpStatus(error: unknown): string | null {
  if (error instanceof Error) {
    const m = error.message.match(/^HTTP (\d{3})/);
    if (m) return m[1];
  }
  return null;
}

/**
 * Map common HTTP statuses to user-friendly messages.
 */
function userFriendlyMessage(operation: string, error: unknown): string {
  const status = extractHttpStatus(error);
  switch (status) {
    case "401": return "Your session has expired. Please log in again.";
    case "403": return "You don't have permission to perform this action.";
    case "404": return `${operation}: The requested resource was not found.`;
    case "409": return "This resource already exists or conflicts with another.";
    case "413": return "The uploaded file is too large.";
    case "422": return "The submitted data could not be processed. Please check your input.";
    case "429": return "Too many requests. Please wait a moment and try again.";
    case "500": case "502": case "503":
      return "The server encountered an error. Please try again in a few moments.";
    default:
      return `${operation} failed. Please try again or contact support if the issue persists.`;
  }
}

/**
 * Record an error with safe, user-facing messages in the activity panel.
 * Raw diagnostic details (URL, stack trace) go only to console.error.
 */
export function logError(operation: string, where: string, error: unknown): void {
  // Full diagnostics to browser console only (not shown to user)
  const raw = rawErrorText(error);
  console.error(`[JOB CANNON Error] ${operation}\n  Where: ${where}\n  Raw: ${raw}`);

  // Safe user-facing message in the UI activity panel
  const friendlyMessage = userFriendlyMessage(operation, error);
  const status = extractHttpStatus(error);
  const safeDetails = status ? `Error code: ${status}` : "An unexpected error occurred.";
  logActivity("error", friendlyMessage, safeDetails);
}
