"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { ResultsView } from "@/components/shortlist/ResultsView";
import { ScoringExplanationCard } from "@/components/shortlist/ScoringExplanationCard";
import { Card } from "@/components/ui/card";
import { getRun } from "@/lib/api";
import type { RunResponse } from "@/lib/types";

export default function RunClient() {
  const sp = useSearchParams();
  const pathname = usePathname();
  const [data, setData] = useState<RunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const runId = useMemo(() => {
    const fromQuery = sp.get("runId");
    if (fromQuery) return fromQuery;

    const parts = pathname.split("/").filter(Boolean);
    const maybeId = parts[1];
    return maybeId && maybeId !== "run" ? maybeId : null;
  }, [pathname, sp]);

  useEffect(() => {
    if (!runId) {
      setError("Missing runId.");
      setLoading(false);
      return;
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
  }, [runId]);

  if (loading) {
    return <div className="p-6">Lade Run...</div>;
  }

  if (error || !data) {
    return (
      <Card className="space-y-2">
        <h1 className="text-xl font-semibold">Run</h1>
        <p>{error ?? "Run nicht gefunden."}</p>
        <p>
          Use: <code>/run?runId=123</code>
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <ResultsView data={data.response_payload} />
      <ScoringExplanationCard compact />
    </div>
  );
}
