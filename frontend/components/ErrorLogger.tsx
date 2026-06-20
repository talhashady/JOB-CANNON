"use client";

/**
 * Global activity + error logger.
 *
 * Mounted once in app/layout.tsx. It shows EVERYTHING in a floating panel:
 *  - Live activity from the app (CV upload, parsing, each agent start/finish) via
 *    the logger bus (lib/logger.ts).
 *  - Auto-captured errors: uncaught errors, unhandled promise rejections,
 *    console.error/warn, and failed network requests.
 *
 * Errors are shown RAW (message + stack/detail) - nothing hidden behind friendly text.
 */
import { useEffect, useRef, useState } from "react";
import { Bug, X, Trash2, Copy, ChevronDown, ChevronUp } from "lucide-react";
import { ACTIVITY_EVENT, type ActivityPayload, type ActivityLevel } from "@/lib/logger";

type Level = ActivityLevel; // "info" | "step" | "success" | "warn" | "error"

interface LogEntry {
  id: number;
  ts: string;
  level: Level;
  tag: string;
  message: string;
  detail?: string;
}

const LEVEL_STYLES: Record<Level, string> = {
  error: "bg-red-500/15 text-red-300 border-red-500/30",
  warn: "bg-amber-400/15 text-amber-300 border-amber-400/30",
  info: "bg-sky-400/15 text-sky-300 border-sky-400/30",
  step: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  success: "bg-lime-400/15 text-lime-300 border-lime-400/30",
};

function safeStringify(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (value instanceof Error) return value.stack || `${value.name}: ${value.message}`;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function ErrorLogger() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const counter = useRef(0);

  useEffect(() => {
    const add = (level: Level, tag: string, message: string, detail?: string) => {
      counter.current += 1;
      const id = counter.current;
      const ts = new Date().toLocaleTimeString();
      const msg = message && message.trim() ? message : "(no message - unnamed error)";
      setEntries((prev) => [{ id, ts, level, tag, message: msg, detail }, ...prev].slice(0, 300));
    };

    // 0) App activity bus (CV upload, parsing, agents, and contextual errors).
    const onActivity = (ev: Event) => {
      const payload = (ev as CustomEvent<ActivityPayload>).detail;
      if (!payload) return;
      add(payload.level, "activity", payload.message, payload.details);
    };

    // 1) Uncaught runtime + resource errors (capture phase catches resource failures).
    const onError = (event: ErrorEvent) => {
      const err = event.error;
      const where = `${event.filename || ""}:${event.lineno || 0}:${event.colno || 0}`;
      add("error", "uncaught", event.message || (err && err.message) || "Unknown error", err ? safeStringify(err) : where);
    };

    // 2) Unhandled promise rejections.
    const onRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      const msg = (reason && (reason.message || (typeof reason === "string" ? reason : ""))) || "Unhandled promise rejection";
      add("error", "promise", msg, safeStringify(reason));
    };

    window.addEventListener(ACTIVITY_EVENT, onActivity as EventListener);
    window.addEventListener("error", onError, true);
    window.addEventListener("unhandledrejection", onRejection);

    // 3) Patch console.error / console.warn (originals still fire).
    const origError = console.error;
    const origWarn = console.warn;
    const summarize = (args: unknown[]) =>
      args.map((a) => (typeof a === "string" ? a : safeStringify(a))).join(" ").trim();
    console.error = (...args: unknown[]) => {
      add("error", "console.error", summarize(args) || "console.error", args.map(safeStringify).join("\n"));
      origError(...args);
    };
    console.warn = (...args: unknown[]) => {
      add("warn", "console.warn", summarize(args) || "console.warn", args.map(safeStringify).join("\n"));
      origWarn(...args);
    };

    // 4) Wrap fetch to catch any network failure not already surfaced by the api client.
    const origFetch = window.fetch;
    window.fetch = (async (...args: Parameters<typeof fetch>) => {
      const target = typeof args[0] === "string" ? args[0] : args[0] instanceof URL ? args[0].toString() : (args[0] as Request).url;
      try {
        const res = await origFetch(...args);
        if (!res.ok) add("error", "network", `${res.status} ${res.statusText} - ${target}`);
        return res;
      } catch (err) {
        add("error", "network", `Network request failed - ${target}`, safeStringify(err));
        throw err;
      }
    }) as typeof window.fetch;

    return () => {
      window.removeEventListener(ACTIVITY_EVENT, onActivity as EventListener);
      window.removeEventListener("error", onError, true);
      window.removeEventListener("unhandledrejection", onRejection);
      console.error = origError;
      console.warn = origWarn;
      window.fetch = origFetch;
    };
  }, []);

  function copyAll() {
    const text = entries
      .map((e) => `[${e.ts}] (${e.level}/${e.tag}) ${e.message}${e.detail ? "\n" + e.detail : ""}`)
      .join("\n\n");
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(() => undefined);
    }
  }

  const total = entries.length;
  const hasErrors = entries.some((e) => e.level === "error");

  return (
    <div className="fixed bottom-4 right-4 z-[200] flex flex-col items-end gap-2 font-sans">
      {open && (
        <div className="glass-strong flex max-h-[65vh] w-[min(94vw,460px)] flex-col overflow-hidden rounded-2xl border border-white/10 shadow-glow">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <span className="flex items-center gap-2 text-sm font-semibold text-white/90">
              <Bug className="h-4 w-4 text-neon-fuchsia" /> Activity & errors
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/60">{total}</span>
            </span>
            <div className="flex items-center gap-1">
              <button onClick={copyAll} title="Copy all" className="rounded-lg p-1.5 text-white/50 hover:bg-white/10 hover:text-white">
                <Copy className="h-4 w-4" />
              </button>
              <button onClick={() => setEntries([])} title="Clear" className="rounded-lg p-1.5 text-white/50 hover:bg-white/10 hover:text-white">
                <Trash2 className="h-4 w-4" />
              </button>
              <button onClick={() => setOpen(false)} title="Close" className="rounded-lg p-1.5 text-white/50 hover:bg-white/10 hover:text-white">
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="overflow-y-auto p-2">
            {entries.length === 0 ? (
              <p className="px-3 py-6 text-center text-sm text-white/40">No activity yet.</p>
            ) : (
              entries.map((e) => (
                <div key={e.id} className="mb-1.5 rounded-xl border border-white/5 bg-ink-950/50 p-2.5">
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${LEVEL_STYLES[e.level]}`}>
                      {e.tag}
                    </span>
                    <span className="text-[10px] text-white/40">{e.ts}</span>
                    {e.detail ? (
                      <button
                        onClick={() => setExpanded(expanded === e.id ? null : e.id)}
                        className="ml-auto text-white/40 hover:text-white"
                      >
                        {expanded === e.id ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      </button>
                    ) : null}
                  </div>
                  <p className="mt-1 break-words text-xs text-white/85">{e.message}</p>
                  {expanded === e.id && e.detail ? (
                    <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded-lg bg-black/40 p-2 text-[11px] leading-relaxed text-white/60">
                      {e.detail}
                    </pre>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        title="Activity & errors"
        className={`relative flex h-12 w-12 items-center justify-center rounded-full border border-white/10 shadow-glow transition-colors ${
          hasErrors ? "bg-red-500/20 text-red-200" : "glass-strong text-white/70"
        }`}
      >
        <Bug className="h-5 w-5" />
        {total > 0 && (
          <span
            className={`absolute -right-1 -top-1 grid h-5 min-w-[20px] place-items-center rounded-full px-1 text-[10px] font-bold text-white ${
              hasErrors ? "bg-red-500" : "bg-violet-500"
            }`}
          >
            {total > 99 ? "99+" : total}
          </span>
        )}
      </button>
    </div>
  );
}
