"use client";

import { useCallback, useRef, useState } from "react";
import { UploadCloud, FileText, Loader2, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";

/**
 * Drag-and-drop CV uploader. Accepts .pdf/.docx/.txt, posts to /profiles/upload
 * (multipart), and reports the parsed profile back to the parent.
 */
export default function CvDropzone({
  careerGoals = "",
  onParsed,
}: {
  careerGoals?: string;
  onParsed?: (profile: { skills?: string[]; full_name?: string }) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      setBusy(true);
      setError(null);
      setDone(false);
      setFileName(file.name);
      try {
        const profile = await api.uploadCv(file, careerGoals);
        setDone(true);
        onParsed?.(profile as { skills?: string[]; full_name?: string });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setBusy(false);
      }
    },
    [careerGoals, onParsed]
  );

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
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
        {busy ? (
          <Loader2 className="mb-3 h-8 w-8 animate-spin text-neon-cyan" />
        ) : done ? (
          <CheckCircle2 className="mb-3 h-8 w-8 text-neon-lime" />
        ) : (
          <UploadCloud className="mb-3 h-8 w-8 text-neon-violet" />
        )}
        <p className="text-sm font-semibold text-white/85">
          {busy
            ? "Parsing your CV..."
            : done
            ? "CV parsed - you're ready to run"
            : "Drag & drop your CV, or click to browse"}
        </p>
        <p className="mt-1 text-xs text-white/45">PDF, DOCX, or TXT</p>
        {fileName && !error && (
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
