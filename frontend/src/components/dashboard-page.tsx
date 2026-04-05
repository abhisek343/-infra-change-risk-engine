"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api, type DashboardData, type Job } from "@/lib/api";
import { decisionClass, formatDate, SectionCard, statusClass, SummaryCard } from "@/components/ui";

export function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    try {
      const payload = await api.getDashboard();
      setDashboard(payload);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const payload = await api.getDashboard();
        if (cancelled) return;
        setDashboard(payload);
        setError(null);
      } catch (loadError) {
        if (cancelled) return;
        setError(loadError instanceof Error ? loadError.message : "Failed to load dashboard");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const activeJobs = useMemo(
    () => dashboard?.recent_jobs.filter((job) => ["pending", "running"].includes(job.status)) ?? [],
    [dashboard],
  );

  useEffect(() => {
    if (!activeJobs.length) return;
    const interval = window.setInterval(() => {
      void loadDashboard();
    }, 2000);
    return () => window.clearInterval(interval);
  }, [activeJobs.length, loadDashboard]);

  const latestJob: Job | null = dashboard?.recent_jobs[0] ?? null;

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-cyan-400/20 bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.14),_transparent_40%),linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,8,23,0.98))] p-8 shadow-2xl shadow-cyan-950/30">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-300">
              Infra Change Risk Engine
            </p>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight text-white md:text-5xl">
              Review infra changes like a release gate, not a demo widget.
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-300">
              The app analyzes Terraform plans and Kubernetes manifests, scores rollout risk, tracks
              approvals, and exports deterministic reports for change review.
            </p>
          </div>
          <div className="flex gap-3">
            <Link
              href="/new"
              className="inline-flex items-center justify-center rounded-2xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300"
            >
              New analysis
            </Link>
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <SummaryCard label="Decisioning" value="Rules + graph + cost" helper="Deterministic review engine" />
          <SummaryCard label="Workflows" value="Jobs + approvals" helper="Approval history is persisted" />
          <SummaryCard label="Artifacts" value="Terraform + K8s" helper="Cross-surface infra review" />
          <SummaryCard label="Exports" value="Markdown report" helper="Shareable change packet" />
        </div>
      </section>

      {error ? (
        <p className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-100">{error}</p>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
