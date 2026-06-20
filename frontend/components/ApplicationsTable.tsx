"use client";

import { Mail, Clock, AlertTriangle, Ban, CheckCircle2, ExternalLink } from "lucide-react";
import type { Application } from "@/lib/types";

const STATUS_META: Record<string, { label: string; cls: string }> = {
  email_sent: { label: "Email sent", cls: "bg-neon-lime/15 text-neon-lime border-neon-lime/30" },
  dry_run: { label: "Dry run", cls: "bg-neon-cyan/15 text-neon-cyan border-neon-cyan/30" },
  no_contact: { label: "No contact", cls: "bg-amber-400/15 text-amber-300 border-amber-400/30" },
  rate_limited: { label: "Rate limited", cls: "bg-orange-400/15 text-orange-300 border-orange-400/30" },
  error: { label: "Error", cls: "bg-red-500/15 text-red-300 border-red-500/30" },
  queued: { label: "Queued", cls: "bg-white/10 text-white/70 border-white/20" },
  submitted: { label: "Submitted", cls: "bg-neon-lime/15 text-neon-lime border-neon-lime/30" },
};

function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status] ?? { label: status, cls: "bg-white/10 text-white/70 border-white/20" };
  const Icon =
    status === "email_sent" || status === "submitted"
      ? CheckCircle2
      : status === "dry_run"
      ? Mail
      : status === "no_contact"
      ? Ban
      : status === "error"
      ? AlertTriangle
      : Clock;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${meta.cls}`}>
      <Icon className="h-3.5 w-3.5" /> {meta.label}
    </span>
  );
}

export default function ApplicationsTable({ applications }: { applications: Application[] }) {
  if (!applications.length) {
    return (
      <div className="glass rounded-2xl p-10 text-center text-white/50">
        No applications yet. Run the pipeline or use auto-apply to get started.
      </div>
    );
  }

  return (
    <div className="glass-strong overflow-hidden rounded-2xl">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-white/10 text-xs uppercase tracking-wider text-white/50">
            <tr>
              <th className="px-5 py-4">Role</th>
              <th className="px-5 py-4">Company</th>
              <th className="px-5 py-4">Match</th>
              <th className="px-5 py-4">Status</th>
              <th className="px-5 py-4">Contact</th>
              <th className="px-5 py-4">When</th>
            </tr>
          </thead>
          <tbody>
            {applications.map((a) => (
              <tr key={a.id} className="border-b border-white/5 transition-colors hover:bg-white/5">
                <td className="px-5 py-4 font-medium text-white/90">
                  <div className="flex items-center gap-2">
                    {a.job_title || a.job_id}
                    {a.job_url ? (
                      <a href={a.job_url} target="_blank" rel="noreferrer" className="text-white/40 hover:text-neon-cyan">
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    ) : null}
                  </div>
                </td>
                <td className="px-5 py-4 text-white/70">{a.company || "-"}</td>
                <td className="px-5 py-4">
                  <span className="font-semibold text-gradient">
                    {typeof a.match_score === "number" ? `${Math.round(a.match_score * 100)}%` : "-"}
                  </span>
                </td>
                <td className="px-5 py-4"><StatusBadge status={a.status} /></td>
                <td className="px-5 py-4 text-white/60">{a.apply_email || "-"}</td>
                <td className="px-5 py-4 text-white/50">
                  {a.created_at ? new Date(a.created_at).toLocaleDateString() : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
