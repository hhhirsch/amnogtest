"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getRun } from "@/lib/api";
import type { RunResponse } from "@/lib/types";

export default function RunPage() {
  const params = useParams<{ runId: string }>();
  const runId = params?.runId;

  const [data, setData] = useState<RunResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    getRun(runId)
      .then(setData)
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : "Fehler"));
  }, [runId]);

  if (!runId) return <div style={{ padding: 24 }}>Missing runId</div>;
  if (err) return <div style={{ padding: 24 }}>Run lookup failed: {err}</div>;
  if (!data) return <div style={{ padding: 24 }}>Lade Run…</div>;

  return (
    <div style={{ padding: 24 }}>
      <h1>Run {runId}</h1>
      <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}