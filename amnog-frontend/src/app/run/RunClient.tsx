"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ResultsView } from "@/components/shortlist/ResultsView";
import { ScoringExplanationCard } from "@/components/shortlist/ScoringExplanationCard";
import { Card } from "@/components/ui/card";
import { getRun } from "@/lib/api";
import type { RunResponse } from "@/lib/types";

export default function RunClient() {
  const router = useRouter();
  const params = useParams<{ runId: string }>();
  const runId = params?.runId;
  const [data, setData] = useState<RunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!runId) {
      setError("Missing runId.");
      setLoading(false);
      return;
    }

    if (typeof window !== "undefined") {
      const isLeadSubmitted = localStorage.getItem(`lead_submitted:${runId}`) === "true";
      if (!isLeadSubmitted) {
        router.replace(`/lead/${runId}`);
        return;
      }
    }

    let mounted = true;
    setLoading(true);

    getRun(runId)
      .then((response) => {
        if (!mounted) return;
        setData(response);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Run konnte nicht geladen werden.");
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [router, runId]);

  if (loading) {
    return <div className="p-6 text-slate-400">Lade Run...</div>;
  }

  if (error || !data) {
    return (
      <Card className="space-y-2">
        <h1 className="text-xl font-semibold text-white">Run</h1>
        <p className="text-slate-400">{error ?? "Run nicht gefunden."}</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <ResultsView data={data.response_payload} />

      <details className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-white">
          Wie die Shortlist entsteht (MVP)
        </summary>
        <div className="mt-3">
          <ScoringExplanationCard compact />
        </div>
      </details>

      <div className="border border-dashed border-white/[0.13] rounded-[10px] px-4 py-3 flex items-center gap-2.5 mt-6 mb-12">
        <span className="text-[9px] font-semibold tracking-[0.1em] uppercase text-ink-muted flex-shrink-0">
          Run ID
        </span>
        <span className="text-[10px] text-ink-muted font-mono overflow-hidden text-ellipsis whitespace-nowrap">
          {runId}
        </span>
      </div>
    </div>
  );
}
