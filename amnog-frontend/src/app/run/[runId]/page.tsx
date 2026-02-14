"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ResultsView } from "@/components/shortlist/ResultsView";
import { Card } from "@/components/ui/card";
import { getRun } from "@/lib/api";
import type { ShortlistResponse } from "@/lib/types";

export default function RunPage() {
  const params = useParams<{ runId: string }>();
  const [data, setData] = useState<ShortlistResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const runId = params?.runId;
    if (!runId) return;

    getRun(runId)
      .then((run) => setData(run.response_payload))
      .catch((err) => setError(err instanceof Error ? err.message : "Fehler beim Laden."));
  }, [params?.runId]);

  if (error) return <Card>{error}</Card>;
  if (!data) return <Card>Lade Ergebnisse...</Card>;

  return <ResultsView data={data} />;
}
