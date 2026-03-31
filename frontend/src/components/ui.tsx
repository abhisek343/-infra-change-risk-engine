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
