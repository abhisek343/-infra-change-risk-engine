"use client";

import type { ReactNode } from "react";

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

export function decisionClass(decision: string): string {
  switch (decision) {
    case "BLOCK":
      return "bg-red-500 text-white";
    case "MANUAL_REVIEW":
      return "bg-orange-500 text-white";
    case "WARN":
      return "bg-amber-500 text-black";
    default:
      return "bg-emerald-500 text-black";
  }
}

export function severityClass(severity: string): string {
  switch (severity.toLowerCase()) {
    case "critical":
      return "bg-red-500/15 text-red-200 ring-1 ring-red-400/40";
    case "high":
      return "bg-orange-500/15 text-orange-200 ring-1 ring-orange-400/40";
    case "medium":
      return "bg-amber-500/15 text-amber-200 ring-1 ring-amber-400/40";
    default:
      return "bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-400/40";
  }
}

export function statusClass(status: string): string {
  switch (status) {
    case "completed":
      return "bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-400/30";
    case "failed":
      return "bg-red-500/15 text-red-200 ring-1 ring-red-400/30";
    case "running":
      return "bg-cyan-500/15 text-cyan-100 ring-1 ring-cyan-400/30";
    default:
      return "bg-white/10 text-white/70 ring-1 ring-white/10";
  }
}

export function SummaryCard({
  label,
  value,
  helper,
}: {
  label: string;
  value: string;
  helper?: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-xs uppercase tracking-[0.2em] text-white/50">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
      {helper ? <p className="mt-1 text-sm text-white/60">{helper}</p> : null}
    </div>
  );
}

export function SectionCard({
  title,
  subtitle,
  children,
  action,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/5 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-white">{title}</h2>
          {subtitle ? <p className="mt-1 text-sm text-white/60">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}
