"use client";

import { useCallback, useRef, useState } from "react";
import { UploadCloud, FileText, Loader2, CheckCircle2, Lock } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { logStep, logSuccess } from "@/lib/logger";
import type { UserProfile } from "@/lib/types";

/**
 * Drag-and-drop CV uploader.
 * - Requires sign-in: when logged out it shows "Please sign in to upload" and
 *   opens the auth modal (via onRequireAuth) instead of firing a doomed request.
 * - Logs every stage (upload start -> parsing -> done) to the activity logger.
 * - Returns the full parsed UserProfile so the parent can fill the CV + goals fields.
 */
export default function CvDropzone({
  careerGoals = "",
  onParsed,
  onRequireAuth,
}: {
  careerGoals?: string;
  onParsed?: (profile: UserProfile) => void;
  onRequireAuth?: () => void;
}) {
  const { user } = useAuth();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const requireAuth = useCallback((): boolean => {
    if (user) return true;
    setError("Please sign in to upload");
    onRequireAuth?.();
    return false;
  }, [user, onRequireAuth]);

  const handleFile = useCallback(
    async (file: File) => {
      if (!requireAuth()) return;
      setBusy(true);
      setError(null);
      setDone(false);
      setFileName(file.name);
      logStep(`CV upload started - ${file.name} (${Math.round(file.size / 1024)} KB)`);
      try {
        logStep("Parsing CV (server-side extraction + profile build)...");
        const profile = await api.uploadCv(file, careerGoals);
        logSuccess(
          `CV parsing complete - ${profile.skills?.length || 0} skills detected; CV & career-goals fields updated`
        );
        setDone(true);
        onParsed?.(profile);
      } catch (err) {
        // api.uploadCv already logged the RAW error with full context.
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setBusy(false);
      }
    },
    [careerGoals, onParsed, requireAuth]
  );

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (!requireAuth()) return;
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  function onZoneClick() {
    if (!requireAuth()) return;
    inputRef.current?.click();
  }

  const signedOut = !user;

  return (
    <div>
      <div
        onClick={onZoneClick}
        onDragOver={(e) => {
          e.preventDefault();
          if (user) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={
          "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-colors " +
          (dragging
            ? "border-neon-cyan bg-neon-cyan/5"
            : "border-white/15 bg-ink-950/40 hover:border-neon-violet/50")
        }
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        {signedOut ? (
          <Lock className="mb-3 h-8 w-8 text-white/50" />
        ) : busy ? (
          <Loader2 className="mb-3 h-8 w-8 animate-spin text-neon-cyan" />
        ) : done ? (
          <CheckCircle2 className="mb-3 h-8 w-8 text-neon-lime" />
        ) : (
          <UploadCloud className="mb-3 h-8 w-8 text-neon-violet" />
        )}
        <p className="text-sm font-semibold text-white/85">
          {signedOut
            ? "Please sign in to upload"
            : busy
            ? "Parsing your CV..."
            : done
            ? "CV parsed - your CV & goals were filled in below"
            : "Drag & drop your CV, or click to browse"}
        </p>
        <p className="mt-1 text-xs text-white/45">
          {signedOut ? "Sign in to enable CV upload" : "PDF, DOCX, or TXT"}
        </p>
        {fileName && !error && !signedOut && (
          <p className="mt-3 flex items-center gap-1.5 text-xs text-white/60">
            <FileText className="h-3.5 w-3.5" /> {fileName}
          </p>
        )}
      </div>
      {error && (
        <p className="mt-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">
          {error}
        </p>
      )}
    </div>
  );
}
