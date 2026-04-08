"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api, markdownExportUrl, mcpEndpointUrl, type FixPatch, type Job, type Violation } from "@/lib/api";
import { decisionClass, formatDate, SectionCard, severityClass, statusClass, SummaryCard } from "@/components/ui";

function ViolationItem({ violation }: { violation: Violation }) {
  return (
    <li className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${severityClass(violation.severity)}`}>
          {violation.severity.toUpperCase()}
        </span>
        <span className="text-xs uppercase tracking-[0.2em] text-white/40">{violation.code}</span>
      </div>
      <h4 className="mt-3 text-lg font-semibold text-white">{violation.title}</h4>
      <p className="mt-2 text-sm leading-6 text-white/70">{violation.message}</p>
      {Object.keys(violation.evidence ?? {}).length ? (
        <pre className="mt-3 overflow-x-auto rounded-xl bg-black/40 p-3 text-xs text-cyan-100">
          {JSON.stringify(violation.evidence, null, 2)}
        </pre>
      ) : null}
    </li>
  );
}

function patchBadgeClass(patchType: string): string {
  if (patchType === "terraform") return "bg-violet-500/15 text-violet-200";
  if (patchType === "kubernetes") return "bg-blue-500/15 text-blue-200";
  return "bg-white/10 text-white/60";
}

function FixPatchItem({ patch }: { patch: FixPatch }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <li className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${patchBadgeClass(patch.patch_type)}`}>
          {patch.patch_type.toUpperCase()}
        </span>
        <span className="text-xs uppercase tracking-[0.2em] text-white/40">{patch.violation_code}</span>
        {patch.llm_model ? (
          <span className="rounded-full bg-cyan-500/10 px-2.5 py-1 text-[11px] text-cyan-300">
            {patch.llm_model}
          </span>
        ) : (
          <span className="rounded-full bg-white/5 px-2.5 py-1 text-[11px] text-white/40">advisory</span>
        )}
      </div>
      <h4 className="mt-3 text-base font-semibold text-white">{patch.violation_title}</h4>
      <p className="mt-1 text-sm leading-6 text-white/65">{patch.explanation}</p>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="mt-3 text-xs text-cyan-400 hover:text-cyan-300 transition"
      >
        {expanded ? "Hide patch ↑" : "Show patch ↓"}
      </button>
      {expanded ? (
        <pre className="mt-3 overflow-x-auto rounded-xl bg-black/50 p-4 text-xs leading-5 text-emerald-200 border border-white/10">
          {patch.patch_content}
        </pre>
      ) : null}
    </li>
  );
}

function AgentGatewayPanel() {
  const mcpUrl = mcpEndpointUrl();
  const examplePayload = JSON.stringify(
    {
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: {
        name: "analyze_infrastructure",
        arguments: { environment: "prod", terraform_plan: "<json>" },
      },
    },
    null,
    2,
  );

  return (
    <SectionCard
      title="Agent gateway · MCP"
      subtitle="AI agents can invoke this engine natively over the Model Context Protocol"
    >
      <div className="space-y-4 text-sm">
        <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-400">MCP endpoint</p>
          <p className="mt-2 font-mono text-sm text-white break-all">{mcpUrl}</p>
          <p className="mt-2 text-xs text-white/50">
            HTTP POST · JSON-RPC 2.0 · <a href={mcpUrl} target="_blank" rel="noreferrer" className="text-cyan-400 hover:text-cyan-300">GET for discovery info</a>
          </p>
        </div>
        <div>
          <p className="mb-2 text-xs uppercase tracking-[0.2em] text-white/45">Available tools</p>
          <ul className="space-y-2">
            {[
              { name: "analyze_infrastructure", desc: "Run full risk analysis and get fix patches" },
              { name: "list_policy_rules", desc: "Enumerate all deterministic policy checks" },
              { name: "generate_fixes", desc: "LLM-generate corrective patches for violations" },
            ].map((t) => (
              <li key={t.name} className="rounded-xl border border-white/8 bg-black/25 p-3">
                <span className="font-mono text-xs text-cyan-200">{t.name}</span>
                <span className="ml-3 text-xs text-white/50">{t.desc}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-2 text-xs uppercase tracking-[0.2em] text-white/45">Example call</p>
          <pre className="overflow-x-auto rounded-xl bg-black/50 border border-white/10 p-3 text-xs text-white/70">
            {`curl -X POST ${mcpUrl} \\\n  -H 'Content-Type: application/json' \\\n  -d '${examplePayload.slice(0, 120)}...'`}
          </pre>
        </div>
      </div>
    </SectionCard>
  );
}

export function JobDetailPage({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<Job | null>(null);
  const [reviewer, setReviewer] = useState("Abhisek");
  const [approvalDecision, setApprovalDecision] = useState("WARN");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [submittingApproval, setSubmittingApproval] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [generatingFixes, setGeneratingFixes] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadJob = useCallback(async () => {
    try {
      const payload = await api.getJob(jobId);
      setJob(payload);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load job");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const payload = await api.getJob(jobId);
        if (cancelled) return;
        setJob(payload);
        setError(null);
      } catch (loadError) {
        if (cancelled) return;
        setError(loadError instanceof Error ? loadError.message : "Failed to load job");
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
  }, [jobId]);

  useEffect(() => {
    if (!job || !["pending", "running"].includes(job.status)) return;
    const interval = window.setInterval(() => {
      void loadJob();
    }, 1500);
    return () => window.clearInterval(interval);
  }, [job, loadJob]);

  const report = job?.report ?? null;
  const graphPreview = useMemo(() => report?.graph.edges.slice(0, 10) ?? [], [report]);

  async function submitApproval() {
    if (!job) return;
    setSubmittingApproval(true);
    try {
      const updated = await api.addApproval(job.id, {
        reviewer,
        decision: approvalDecision,
        note,
      });
      setJob(updated);
      setNote("");
      setError(null);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to save approval");
    } finally {
      setSubmittingApproval(false);
    }
  }

  async function rerunJob() {
    if (!job) return;
    setRerunning(true);
    try {
      const updated = await api.runJob(job.id);
      setJob(updated);
      setError(null);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Failed to requeue job");
    } finally {
      setRerunning(false);
    }
  }

  async function triggerFixes() {
    if (!job) return;
    setGeneratingFixes(true);
    try {
      await api.triggerFixes(job.id);
      // Reload the full job to pick up new fix_patches
      await loadJob();
      setError(null);
    } catch (fixError) {
      setError(fixError instanceof Error ? fixError.message : "Failed to generate fixes");
    } finally {
      setGeneratingFixes(false);
    }
  }

  const fixPatches = job?.fix_patches ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Analysis report</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">{job?.name ?? "Loading analysis..."}</h1>
          <p className="mt-2 text-sm text-white/60">
            {job ? `${job.environment.toUpperCase()} · created ${formatDate(job.created_at)}` : "Fetching report"}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/new"
            className="rounded-2xl border border-white/10 bg-black/30 px-4 py-2 text-sm text-white/80 transition hover:border-cyan-400/40 hover:text-white"
          >
            New analysis
          </Link>
          {job ? (
            <>
              <button
                type="button"
                onClick={() => void rerunJob()}
                disabled={rerunning}
                className="rounded-2xl border border-white/10 bg-black/30 px-4 py-2 text-sm text-white/80 transition hover:border-cyan-400/40 hover:text-white disabled:opacity-60"
              >
                {rerunning ? "Queueing..." : "Re-run"}
              </button>
              {job.status === "completed" && (report?.violations.length ?? 0) > 0 ? (
                <button
                  type="button"
                  onClick={() => void triggerFixes()}
                  disabled={generatingFixes}
                  className="rounded-2xl border border-violet-400/30 bg-violet-500/10 px-4 py-2 text-sm text-violet-200 transition hover:bg-violet-500/20 disabled:opacity-60"
                >
                  {generatingFixes ? "Generating fixes..." : fixPatches.length > 0 ? "Regenerate fixes" : "Generate AI fixes"}
                </button>
              ) : null}
              <a
                href={markdownExportUrl(job.id)}
                target="_blank"
                rel="noreferrer"
                className="rounded-2xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300"
              >
                Export markdown
              </a>
            </>
          ) : null}
        </div>
      </div>

      {error ? (
        <p className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-100">{error}</p>
      ) : null}

      {loading ? <p className="text-white/60">Loading report...</p> : null}

      {job ? (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <SummaryCard label="Status" value={job.status.toUpperCase()} helper={`Updated ${formatDate(job.updated_at)}`} />
            <SummaryCard label="Completed" value={formatDate(job.completed_at)} />
            <SummaryCard label="Approvals" value={String(job.approvals.length)} />
            <SummaryCard label="Decision" value={report?.decision.decision ?? "Pending"} helper={report ? `${report.decision.score}/100` : "Awaiting report"} />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${statusClass(job.status)}`}>
              {job.status}
            </span>
            {report ? (
              <span className={`rounded-full px-3 py-1 text-sm font-semibold ${decisionClass(report.decision.decision)}`}>
                {report.decision.decision}
              </span>
            ) : null}
            {fixPatches.length > 0 ? (
              <span className="rounded-full bg-violet-500/15 px-3 py-1 text-xs font-semibold text-violet-200">
                {fixPatches.length} AI fix{fixPatches.length !== 1 ? "es" : ""} ready
              </span>
            ) : null}
          </div>

          {report ? (
            <>
              <SectionCard title="Executive summary" subtitle="Fast readout for a hiring manager or reviewer">
                <div className="grid gap-4 lg:grid-cols-[0.65fr_0.35fr]">
                  <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-5">
                    <p className="text-5xl font-semibold text-white">{report.decision.score}</p>
                    <p className="mt-4 text-sm leading-7 text-white/70">{report.summary}</p>
                  </div>
                  <div className="grid gap-4">
                    <SummaryCard label="Blast radius" value={String(report.blast_radius.size)} helper={report.blast_radius.touched_domains.join(", ") || "No domains"} />
                    <SummaryCard label="Cost delta" value={`$${report.cost.monthly_delta.toFixed(2)}`} helper="Projected monthly impact" />
                    <SummaryCard label="Violations" value={String(report.violations.length)} helper={report.affected_domains.join(", ") || "No impacted domains"} />
                  </div>
                </div>
              </SectionCard>

              <div className="grid gap-6 xl:grid-cols-[0.7fr_0.3fr]">
                <div className="space-y-6">
                  <SectionCard title="Highlights" subtitle="Top talking points for the change review">
                    <ul className="space-y-3 text-sm leading-7 text-white/70">
                      {report.highlights.map((highlight) => (
                        <li key={highlight} className="rounded-2xl border border-white/10 bg-black/25 p-4">
                          {highlight}
                        </li>
                      ))}
                    </ul>
                  </SectionCard>

                  <SectionCard title="Recommendations" subtitle="What should happen before this change is allowed through">
                    <div className="space-y-3">
                      {report.recommendations.map((recommendation) => (
                        <div key={`${recommendation.priority}-${recommendation.title}`} className="rounded-2xl border border-white/10 bg-black/25 p-4">
                          <div className="flex items-center gap-2">
                            <span className="rounded-full bg-cyan-500/15 px-2.5 py-1 text-xs font-semibold text-cyan-200">
                              {recommendation.priority}
                            </span>
                            <h3 className="text-base font-semibold text-white">{recommendation.title}</h3>
                          </div>
                          <p className="mt-2 text-sm leading-6 text-white/70">{recommendation.action}</p>
                        </div>
                      ))}
                    </div>
                  </SectionCard>

                  <SectionCard title="Policy findings" subtitle="Deterministic violations generated from the artifact set">
                    <ul className="grid gap-4">
                      {report.violations.length ? (
                        report.violations.map((violation) => (
                          <ViolationItem key={`${violation.code}-${violation.message}`} violation={violation} />
                        ))
                      ) : (
                        <li className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
                          No rule violations detected for this change set.
                        </li>
                      )}
                    </ul>
                  </SectionCard>

                  {/* AI Fix Patches */}
                  {fixPatches.length > 0 ? (
                    <SectionCard
                      title="AI-generated fix patches"
                      subtitle="LLM-produced corrective Terraform HCL and Kubernetes YAML — one patch per violation"
                    >
                      <ul className="grid gap-4">
                        {fixPatches.map((patch) => (
                          <FixPatchItem key={`${patch.violation_code}-${patch.patch_type}`} patch={patch} />
                        ))}
                      </ul>
                    </SectionCard>
                  ) : report.violations.length > 0 && job.status === "completed" ? (
                    <SectionCard
                      title="AI-generated fix patches"
                      subtitle="LLM-produced corrective Terraform HCL and Kubernetes YAML — one patch per violation"
                    >
                      <div className="rounded-2xl border border-white/10 bg-black/25 p-5 text-center">
                        <p className="text-sm text-white/60">
                          No patches generated yet. Click <strong className="text-white">Generate AI fixes</strong> above to invoke the LLM fix agent.
                        </p>
                        <p className="mt-2 text-xs text-white/40">
                          Patches are also generated automatically by the worker if <code className="text-cyan-300">OPENAI_API_KEY</code> is set.
                        </p>
                      </div>
                    </SectionCard>
                  ) : null}

                  <SectionCard title="Changed resources" subtitle="Normalized resource deltas generated by the analysis engine">
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-sm">
                        <thead className="text-left text-white/45">
                          <tr>
                            <th className="pb-3">Identifier</th>
                            <th className="pb-3">Type</th>
                            <th className="pb-3">Domain</th>
                            <th className="pb-3">Action</th>
                            <th className="pb-3 text-right">Cost Δ</th>
                          </tr>
                        </thead>
                        <tbody className="text-white/80">
                          {report.resources.map((resource) => (
                            <tr key={resource.identifier} className="border-t border-white/5 align-top">
                              <td className="py-3 pr-4 font-mono text-xs">{resource.identifier}</td>
                              <td className="py-3 pr-4">{resource.resource_type}</td>
                              <td className="py-3 pr-4">{resource.domain}</td>
                              <td className="py-3 pr-4">{resource.action}</td>
                              <td className="py-3 text-right">${resource.monthly_cost_delta.toFixed(2)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </SectionCard>
                </div>

                <div className="space-y-6">
                  <SectionCard title="Score breakdown" subtitle="Why the engine produced this decision">
                    <ul className="space-y-3">
                      {report.score_breakdown.map((factor) => (
                        <li key={`${factor.label}-${factor.weight}`} className="rounded-2xl border border-white/10 bg-black/25 p-4">
                          <div className="flex items-center justify-between gap-3">
                            <p className="font-semibold text-white">{factor.label}</p>
                            <span className="rounded-full bg-white/10 px-2.5 py-1 text-xs text-white/75">
                              +{factor.weight}
                            </span>
                          </div>
                          <p className="mt-2 text-sm leading-6 text-white/70">{factor.reason}</p>
                        </li>
                      ))}
                    </ul>
                  </SectionCard>

                  <SectionCard title="Reviewer checklist" subtitle="Operational guardrails before apply">
                    <ul className="space-y-2 text-sm text-white/70">
                      {report.review_checklist.map((item) => (
                        <li key={item} className="rounded-2xl border border-white/10 bg-black/25 p-3">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </SectionCard>

                  {/* Agent Gateway / MCP Panel */}
                  <AgentGatewayPanel />

                  <SectionCard title="Approval workflow" subtitle="Capture reviewer sign-off on the analysis">
                    <div className="space-y-4">
                      <label className="grid gap-2 text-sm text-white/75">
                        Reviewer
                        <input
                          value={reviewer}
                          onChange={(event) => setReviewer(event.target.value)}
                          className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none"
                        />
                      </label>
                      <label className="grid gap-2 text-sm text-white/75">
                        Decision
                        <select
                          value={approvalDecision}
                          onChange={(event) => setApprovalDecision(event.target.value)}
                          className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none"
                        >
                          <option value="APPROVE">APPROVE</option>
                          <option value="WARN">WARN</option>
                          <option value="BLOCK">BLOCK</option>
                        </select>
                      </label>
                      <label className="grid gap-2 text-sm text-white/75">
                        Note
                        <textarea
                          value={note}
                          onChange={(event) => setNote(event.target.value)}
                          rows={4}
                          className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none"
                        />
                      </label>
                      <button
                        type="button"
                        disabled={submittingApproval}
                        onClick={() => void submitApproval()}
                        className="inline-flex items-center justify-center rounded-2xl bg-cyan-400 px-4 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:opacity-60"
                      >
                        {submittingApproval ? "Saving..." : "Add approval"}
                      </button>
                      <div className="space-y-3">
                        {job.approvals.map((approval) => (
                          <div key={approval.id} className="rounded-2xl border border-white/10 bg-black/25 p-4">
                            <div className="flex items-center justify-between gap-3">
                              <p className="font-semibold text-white">{approval.reviewer}</p>
                              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${decisionClass(approval.decision)}`}>
                                {approval.decision}
                              </span>
                            </div>
                            <p className="mt-2 text-xs uppercase tracking-[0.2em] text-white/40">
                              {formatDate(approval.created_at)}
                            </p>
                            {approval.note ? <p className="mt-2 text-sm leading-6 text-white/70">{approval.note}</p> : null}
                          </div>
                        ))}
                        {!job.approvals.length ? <p className="text-sm text-white/60">No approvals recorded yet.</p> : null}
                      </div>
                    </div>
                  </SectionCard>

                  <SectionCard title="Graph and evidence" subtitle="Blast-radius preview and evidence trail">
                    <ul className="space-y-3">
                      {graphPreview.map((edge, index) => (
                        <li key={`${edge.source}-${edge.target}-${index}`} className="rounded-xl border border-white/10 bg-black/30 p-3 text-sm text-white/75">
                          <span className="font-mono text-cyan-200">{edge.source}</span>
                          <span className="mx-2 text-white/40">→</span>
                          <span className="font-mono text-cyan-200">{edge.target}</span>
                          <span className="ml-3 rounded-full bg-white/5 px-2 py-1 text-[11px] uppercase tracking-[0.2em] text-white/50">
                            {edge.relation}
                          </span>
                        </li>
                      ))}
                    </ul>
                    <div className="mt-4 rounded-xl border border-white/10 bg-black/30 p-3">
                      <p className="text-xs uppercase tracking-[0.2em] text-white/45">Evidence trail</p>
                      <ul className="mt-3 space-y-2 text-sm text-white/70">
                        {report.evidence.map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ul>
                    </div>
                  </SectionCard>
                </div>
              </div>
            </>
          ) : (
            <SectionCard title="Execution state" subtitle="Worker-driven analysis status">
              <p className="text-sm leading-7 text-white/65">
                {job.status === "failed"
                  ? job.error_text ?? "Analysis failed."
                  : "This job is waiting for the worker to produce a report. Keep the worker process running and the page will refresh automatically."}
              </p>
            </SectionCard>
          )}
        </>
      ) : null}
    </div>
  );
}
