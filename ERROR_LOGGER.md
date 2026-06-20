# Frontend Global Error Logger - changes & full code

Adds a floating **Error Log** panel to every page that automatically captures *every*
kind of client-side error - even errors that have **no name or message**:

- Uncaught runtime errors (`window` `error` event)
- Unhandled promise rejections (`unhandledrejection`)
- Anything sent to `console.error` / `console.warn` (originals still run)
- Failed network requests (non-2xx responses **and** thrown network errors, via a `fetch` wrapper)
- Resource load errors (scripts/images) - caught via the capture-phase `error` listener

Unnamed/empty errors are never dropped: they show with a clear fallback label
`(no message - unnamed error)`.

**UI:** a small bug button sits in the bottom-right corner with a red count badge. Click it
to open the panel, expand any entry to see the full stack/detail, and copy or clear all.

**No new dependencies** - it uses `lucide-react` (already installed) and your existing
Tailwind classes. It is client-only (`"use client"`), so SSR is unaffected.

---

## 1. NEW FILE - `frontend/components/ErrorLogger.tsx`

Create this file exactly as below:

```tsx
"use client";

/**
 * Global client-side error logger.
 *
 * Mounted once in app/layout.tsx, it captures EVERY kind of front-end error and
 * shows them in a floating panel (bottom-right). It never drops an error - even
 * ones with no name or message get a clear fallback label.
 *
 * Sources captured:
 *  - Uncaught runtime errors          (window 'error', capture phase -> also resource errors)
 *  - Unhandled promise rejections     (window 'unhandledrejection')
 *  - console.error / console.warn      (patched, originals still run)
 *  - Failed network requests          (fetch wrapper: non-2xx + thrown network errors)
 */
import { useEffect, useRef, useState } from "react";
import { Bug, X, Trash2, Copy, ChevronDown, ChevronUp } from "lucide-react";

type LogKind =
  | "error"
  | "unhandledrejection"
  | "console.error"
  | "console.warn"
  | "network";

interface LogEntry {
  id: number;
  ts: string;
  kind: LogKind;
  message: string;
  detail?: string;
}

const KIND_STYLES: Record<LogKind, string> = {
  error: "bg-red-500/15 text-red-300 border-red-500/30",
  unhandledrejection: "bg-orange-500/15 text-orange-300 border-orange-500/30",
  "console.error": "bg-red-500/15 text-red-300 border-red-500/30",
  "console.warn": "bg-amber-400/15 text-amber-300 border-amber-400/30",
  network: "bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-500/30",
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
    const add = (kind: LogKind, message: string, detail?: string) => {
      counter.current += 1;
      const id = counter.current;
      const ts = new Date().toLocaleTimeString();
      const msg = message && message.trim() ? message : "(no message - unnamed error)";
      setEntries((prev) => [{ id, ts, kind, message: msg, detail }, ...prev].slice(0, 200));
    };

    // 1) Uncaught runtime + resource errors (capture phase catches resource load failures).
    const onError = (event: ErrorEvent) => {
      const err = event.error;
      const where = `${event.filename || ""}:${event.lineno || 0}:${event.colno || 0}`;
      add(
        "error",
        event.message || (err && err.message) || "Unknown error",
        err ? safeStringify(err) : where
      );
    };

    // 2) Unhandled promise rejections.
    const onRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      const msg =
        (reason && (reason.message || (typeof reason === "string" ? reason : ""))) ||
        "Unhandled promise rejection";
      add("unhandledrejection", msg, safeStringify(reason));
    };

    window.addEventListener("error", onError, true);
    window.addEventListener("unhandledrejection", onRejection);

    // 3) Patch console.error / console.warn (originals still fire).
    const origError = console.error;
    const origWarn = console.warn;
    const summarize = (args: unknown[]) =>
      args.map((a) => (typeof a === "string" ? a : safeStringify(a))).join(" ").trim();

    console.error = (...args: unknown[]) => {
      add("console.error", summarize(args) || "console.error", args.map(safeStringify).join("\n"));
      origError(...args);
    };
    console.warn = (...args: unknown[]) => {
      add("console.warn", summarize(args) || "console.warn", args.map(safeStringify).join("\n"));
      origWarn(...args);
    };

    // 4) Wrap fetch to log failed network requests.
    const origFetch = window.fetch;
    window.fetch = (async (...args: Parameters<typeof fetch>) => {
      const target =
        typeof args[0] === "string"
          ? args[0]
          : args[0] instanceof URL
          ? args[0].toString()
          : (args[0] as Request).url;
      try {
        const res = await origFetch(...args);
        if (!res.ok) add("network", `${res.status} ${res.statusText} - ${target}`);
        return res;
      } catch (err) {
        add("network", `Network request failed - ${target}`, safeStringify(err));
        throw err;
      }
    }) as typeof window.fetch;

    return () => {
      window.removeEventListener("error", onError, true);
      window.removeEventListener("unhandledrejection", onRejection);
      console.error = origError;
      console.warn = origWarn;
      window.fetch = origFetch;
    };
  }, []);

  function copyAll() {
    const text = entries
      .map((e) => `[${e.ts}] ${e.kind}: ${e.message}${e.detail ? "\n" + e.detail : ""}`)
      .join("\n\n");
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(() => undefined);
    }
  }

  const count = entries.length;

  return (
    <div className="fixed bottom-4 right-4 z-[200] flex flex-col items-end gap-2 font-sans">
      {open && (
        <div className="glass-strong flex max-h-[60vh] w-[min(92vw,420px)] flex-col overflow-hidden rounded-2xl border border-white/10 shadow-glow">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <span className="flex items-center gap-2 text-sm font-semibold text-white/90">
              <Bug className="h-4 w-4 text-neon-fuchsia" /> Error log
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/60">{count}</span>
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
              <p className="px-3 py-6 text-center text-sm text-white/40">No errors captured yet.</p>
            ) : (
              entries.map((e) => (
                <div key={e.id} className="mb-1.5 rounded-xl border border-white/5 bg-ink-950/50 p-2.5">
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${KIND_STYLES[e.kind]}`}>
                      {e.kind}
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
                    <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-black/40 p-2 text-[11px] leading-relaxed text-white/60">
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
        title="Error log"
        className={`relative flex h-12 w-12 items-center justify-center rounded-full border border-white/10 shadow-glow transition-colors ${
          count > 0 ? "bg-red-500/20 text-red-200" : "glass-strong text-white/70"
        }`}
      >
        <Bug className="h-5 w-5" />
        {count > 0 && (
          <span className="absolute -right-1 -top-1 grid h-5 min-w-[20px] place-items-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>
    </div>
  );
}
```

---

## 2. CHANGED FILE - `frontend/app/layout.tsx`

Mount `<ErrorLogger />` as the **last** element inside `<body>`, so it loads after
everything else and overlays every page. Two additions: the import, and the component.

### Option A - full replacement (recommended)

This version also keeps the `AuthProvider` wrapper from the auth feature. **If you have
not added auth yet**, simply delete the two `AuthProvider` lines (the import and the
wrapper) - the logger does not depend on it.

```tsx
import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import ErrorLogger from "@/components/ErrorLogger";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const grotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Career Assistant - Land your next role",
  description:
    "A multi-agent AI that scrapes, verifies, matches, tailors, and tracks jobs for you. Stunning, fast, and smart.",
  metadataBase: new URL("https://ai-career-assistant.vercel.app"),
  openGraph: {
    title: "AI Career Assistant",
    description: "Your autonomous multi-agent career copilot.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${grotesk.variable}`}>
      <body className="min-h-screen font-sans antialiased">
        <AuthProvider>{children}</AuthProvider>
        <ErrorLogger />
      </body>
    </html>
  );
}
```

### Option B - minimal edit (if you don't want to replace the file)

1. Add this import near the top, with the other imports:
   ```tsx
   import ErrorLogger from "@/components/ErrorLogger";
   ```
2. Add the component as the **last child of `<body>`**, right before the closing `</body>`:
   ```tsx
           <ErrorLogger />
   ```

---

## 3. Done

- Works on every page automatically (mounted once in the root layout).
- Catches errors with no name/message and labels them clearly.
- To temporarily disable, remove the `<ErrorLogger />` line from `layout.tsx`.

### How to test it quickly

Open your site, then in the browser console run any of these - each appears instantly in
the panel:

```js
console.error("test error");                 // console.error
Promise.reject(new Error("boom"));           // unhandledrejection
throw new Error("manual");                    // uncaught error
fetch("/does-not-exist");                     // network (404)
```
