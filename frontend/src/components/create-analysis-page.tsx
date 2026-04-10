"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, type Sample } from "@/lib/api";
import { SectionCard, SummaryCard } from "@/components/ui";

const defaultTerraform = `{
  "resource_changes": []
}`;

const defaultKubernetes = `apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample
  namespace: staging
spec:
  replicas: 1`;

export function CreateAnalysisPage() {
  const router = useRouter();
  const [samples, setSamples] = useState<Sample[]>([]);
  const [name, setName] = useState("Prod network and runtime change review");
  const [environment, setEnvironment] = useState("prod");
  const [terraformPlan, setTerraformPlan] = useState(defaultTerraform);
  const [kubernetesManifest, setKubernetesManifest] = useState(defaultKubernetes);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const payload = await api.getSamples();
        if (cancelled) return;
        setSamples(payload);
        if (payload[0]) {
          setName(payload[0].name.replace(/-/g, " "));
          setTerraformPlan(payload[0].terraform_plan);
          setKubernetesManifest(payload[0].kubernetes_manifest);
          setEnvironment(payload[0].name.includes("prod") ? "prod" : "staging");
        }
        setError(null);
      } catch (loadError) {
        if (cancelled) return;
        setError(loadError instanceof Error ? loadError.message : "Failed to load samples");
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

  function applySample(sample: Sample) {
    setName(sample.name.replace(/-/g, " "));
    setEnvironment(sample.name.includes("prod") ? "prod" : "staging");
    setTerraformPlan(sample.terraform_plan);
    setKubernetesManifest(sample.kubernetes_manifest);
  }

  async function submitJob() {
    setSubmitting(true);
    setError(null);
    try {
      const created = await api.createJob({
        name,
        environment,
        terraform_plan: terraformPlan,
        kubernetes_manifest: kubernetesManifest,
      });
      const queued = await api.runJob(created.id);
      router.push(`/jobs/${queued.id}`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to submit analysis");
      setSubmitting(false);
      return;
    }
    setSubmitting(false);
  }

  return (
    <div className="space-y-6">
      <SectionCard
        title="Create analysis"
        subtitle="Submit Terraform and Kubernetes artifacts, then queue the worker-backed review flow."
      >
        <div className="grid gap-4 md:grid-cols-3">
          <SummaryCard label="Worker-backed" value="Queued jobs" helper="Analysis executes asynchronously" />
          <SummaryCard label="Review output" value="Score + findings + approvals" helper="Built for change gates" />
          <SummaryCard label="Shareability" value="Markdown export" helper="Hand-off ready" />
        </div>
      </SectionCard>

      {error ? (
        <p className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-100">{error}</p>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <SectionCard title="Artifacts and metadata" subtitle="Paste raw inputs or start from a bundled sample">
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {samples.map((sample) => (
                <button
                  key={sample.name}
                  type="button"
                  onClick={() => applySample(sample)}
                  className="rounded-full border border-white/10 bg-black/30 px-4 py-2 text-sm text-white/75 transition hover:border-cyan-400/40 hover:text-white"
                >
                  Load {sample.name}
                </button>
              ))}
              {!samples.length && loading ? (
                <span className="rounded-full border border-white/10 bg-black/30 px-4 py-2 text-sm text-white/55">
                  Loading samples...
                </span>
              ) : null}
            </div>

            <label className="grid gap-2 text-sm text-white/75">
              Analysis name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none placeholder:text-white/30"
              />
            </label>

            <label className="grid gap-2 text-sm text-white/75">
              Environment
              <select
                value={environment}
                onChange={(event) => setEnvironment(event.target.value)}
                className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none"
              >
                <option value="dev">dev</option>
                <option value="staging">staging</option>
                <option value="prod">prod</option>
              </select>
            </label>

            <label className="grid gap-2 text-sm text-white/75">
              Terraform plan JSON
              <textarea
                value={terraformPlan}
                onChange={(event) => setTerraformPlan(event.target.value)}
                rows={16}
                className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3 font-mono text-xs leading-6 text-cyan-100 outline-none placeholder:text-white/30"
              />
            </label>

            <label className="grid gap-2 text-sm text-white/75">
              Kubernetes manifest YAML
              <textarea
                value={kubernetesManifest}
                onChange={(event) => setKubernetesManifest(event.target.value)}
                rows={16}
                className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3 font-mono text-xs leading-6 text-cyan-100 outline-none placeholder:text-white/30"
              />
            </label>

            <button
              type="button"
              disabled={submitting}
              onClick={() => void submitJob()}
              className="inline-flex items-center justify-center rounded-2xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Queueing analysis..." : "Run pre-deploy analysis"}
            </button>
          </div>
        </SectionCard>

        <SectionCard title="What this run produces" subtitle="The fuller app now keeps review state around the report">
          <ul className="space-y-3 text-sm leading-7 text-white/70">
            <li className="rounded-2xl border border-white/10 bg-black/25 p-4">
              Risk summary with score breakdown, highlights, and deterministic recommendations.
            </li>
            <li className="rounded-2xl border border-white/10 bg-black/25 p-4">
              Approval history so the report reads like a real change-management artifact.
            </li>
            <li className="rounded-2xl border border-white/10 bg-black/25 p-4">
              Markdown export for sharing with hiring managers or interviewers as a polished demo.
            </li>
          </ul>
        </SectionCard>
      </div>
    </div>
  );
}
