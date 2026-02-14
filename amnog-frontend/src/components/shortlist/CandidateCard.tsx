"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { CandidateResult } from "@/lib/types";

const confidenceMap: Record<CandidateResult["confidence"], string> = {
  hoch: "High confidence",
  mittel: "Medium confidence",
  niedrig: "Low confidence",
};

export function CandidateCard({ candidate }: { candidate: CandidateResult }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">#{candidate.rank}</h3>
        <Badge>{confidenceMap[candidate.confidence]}</Badge>
      </div>
      <p className={expanded ? "" : "line-clamp-3"}>{candidate.candidate_text}</p>
      <button className="text-sm underline" onClick={() => setExpanded((prev) => !prev)}>
        {expanded ? "Weniger anzeigen" : "Mehr anzeigen"}
      </button>
      <div className="text-sm text-slate-600">Support Score: {candidate.support_score.toFixed(2)} · Fälle: {candidate.support_cases}</div>
      <ul className="space-y-2 text-sm">
        {candidate.references.map((ref) => (
          <li key={ref.decision_id + ref.url} className="rounded-md border p-2">
            <a className="font-medium underline" href={ref.url} target="_blank" rel="noreferrer">
              {ref.product_name} · {ref.decision_date}
            </a>
            <p>{ref.snippet}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
