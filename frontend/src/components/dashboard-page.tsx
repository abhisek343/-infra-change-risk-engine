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
        <SectionCard title="Portfolio-grade operations view" subtitle="Totals and decision mix across recent jobs">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <SummaryCard label="Total jobs" value={String(dashboard?.totals.total ?? 0)} />
            <SummaryCard label="Pending" value={String(dashboard?.totals.pending ?? 0)} />
            <SummaryCard label="Running" value={String(dashboard?.totals.running ?? 0)} />
            <SummaryCard label="Completed" value={String(dashboard?.totals.completed ?? 0)} />
            <SummaryCard label="Failed" value={String(dashboard?.totals.failed ?? 0)} />
            <SummaryCard
              label="Blocked"
              value={String(dashboard?.decision_counts.BLOCK ?? 0)}
              helper={`Warn: ${dashboard?.decision_counts.WARN ?? 0} · Manual: ${dashboard?.decision_counts.MANUAL_REVIEW ?? 0}`}
            />
          </div>
        </SectionCard>

        <SectionCard
          title="Latest analysis"
          subtitle="The most recent job stays pinned here for a quick high-signal read."
          action={
            latestJob ? (
              <Link
                href={`/jobs/${latestJob.id}`}
                className="rounded-2xl border border-white/10 bg-black/30 px-4 py-2 text-sm text-white/80 transition hover:border-cyan-400/40 hover:text-white"
              >
                Open report
              </Link>
            ) : null
          }
        >
          {loading ? <p className="text-white/60">Loading dashboard...</p> : null}
          {!latestJob && !loading ? <p className="text-white/60">No analyses have been created yet.</p> : null}
          {latestJob ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm uppercase tracking-[0.2em] text-white/45">{latestJob.environment}</p>
                  <h3 className="mt-1 text-2xl font-semibold text-white">{latestJob.name}</h3>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${statusClass(latestJob.status)}`}>
                    {latestJob.status}
                  </span>
                  {latestJob.report ? (
                    <span className={`rounded-full px-3 py-1 text-sm font-semibold ${decisionClass(latestJob.report.decision.decision)}`}>
                      {latestJob.report.decision.decision}
                    </span>
                  ) : null}
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <SummaryCard label="Created" value={formatDate(latestJob.created_at)} />
                <SummaryCard label="Score" value={String(latestJob.report?.decision.score ?? 0)} />
                <SummaryCard
                  label="Approvals"
                  value={String(latestJob.approvals.length)}
                  helper={latestJob.approvals[0] ? `${latestJob.approvals[0].decision} by ${latestJob.approvals[0].reviewer}` : "No sign-off yet"}
                />
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-5">
                <p className="text-sm leading-7 text-white/70">
                  {latestJob.report?.summary ??
                    latestJob.error_text ??
                    "This analysis is still waiting for the worker to produce a report."}
                </p>
              </div>
            </div>
          ) : null}
        </SectionCard>
      </section>

      <SectionCard title="Recent analysis jobs" subtitle="Open any job for the full report, approval trail, and export">
        <div className="space-y-3">
          {dashboard?.recent_jobs.map((job) => (
            <Link
              key={job.id}
              href={`/jobs/${job.id}`}
              className="block rounded-2xl border border-white/10 bg-black/25 p-4 transition hover:border-cyan-400/40 hover:bg-black/40"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-lg font-semibold text-white">{job.name}</p>
                  <p className="mt-1 text-sm text-white/45">
                    {job.environment.toUpperCase()} · {formatDate(job.created_at)}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${statusClass(job.status)}`}>
                    {job.status}
                  </span>
                  {job.report ? (
                    <span className={`rounded-full px-3 py-1 text-sm font-semibold ${decisionClass(job.report.decision.decision)}`}>
                      {job.report.decision.decision} · {job.report.decision.score}
                    </span>
                  ) : null}
                </div>
              </div>
            </Link>
          ))}
          {!dashboard?.recent_jobs.length && !loading ? <p className="text-sm text-white/60">No analyses yet.</p> : null}
        </div>
      </SectionCard>
    </div>
  );
}
