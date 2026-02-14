"use client";

import { useSearchParams } from "next/navigation";

export default function RunPage() {
  const sp = useSearchParams();
  const runId = sp.get("runId");

  if (!runId) {
    return (
      <div style={{ padding: 24 }}>
        <h1>Run</h1>
        <p>Missing <code>runId</code>.</p>
        <p>Use: <code>/run?runId=123</code></p>
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <h1>Run {runId}</h1>
      <p>(Hier dann deine Run-Details laden/rendern.)</p>
    </div>
  );
}
