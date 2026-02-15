"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { CandidateResult } from "@/lib/types";

const confidenceMap: Record<CandidateResult["confidence"], { label: string; variant: "success" | "warning" | "danger" }> = {
  hoch: { label: "High confidence", variant: "success" },
  mittel: { label: "Medium confidence", variant: "warning" },
  niedrig: { label: "Low confidence", variant: "danger" },
};

export function CandidateCard({ candidate }: { candidate: CandidateResult }) {
  const [expanded, setExpanded] = useState(false);
  const { label, variant } = confidenceMap[candidate.confidence];

  return (
    <Card className="space-y-4 hover:border-primary-200 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 text-lg font-bold text-primary-700">
            #{candidate.rank}
          </div>
          <div>
            <Badge variant={variant}>{label}</Badge>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm text-slate-600">
          <div className="text-right">
            <div className="font-semibold text-slate-900">{candidate.support_score.toFixed(2)}</div>
            <div className="text-xs">Support Score</div>
          </div>
          <div className="h-8 w-px bg-slate-200" />
          <div className="text-right">
            <div className="font-semibold text-slate-900">{candidate.support_cases}</div>
            <div className="text-xs">Fälle</div>
          </div>
        </div>
      </div>
      
      <div className="rounded-lg bg-slate-50 p-4">
        <p className={`text-sm leading-relaxed ${expanded ? "" : "line-clamp-3"}`}>
          {candidate.candidate_text}
        </p>
        <button 
          className="mt-2 text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors" 
          onClick={() => setExpanded((prev) => !prev)}
        >
          {expanded ? "Weniger anzeigen ↑" : "Mehr anzeigen ↓"}
        </button>
      </div>
      
      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-slate-900">Referenzen</h4>
        <ul className="space-y-2">
          {candidate.references.map((ref) => (
            <li key={ref.decision_id + ref.url} className="group rounded-lg border-2 border-slate-100 bg-slate-50 p-3 transition-all hover:border-primary-200 hover:bg-primary-50/50">
              <a 
                className="flex items-start gap-2 text-sm font-medium text-primary-700 hover:text-primary-800 transition-colors" 
                href={ref.url} 
                target="_blank" 
                rel="noreferrer"
              >
                <svg className="h-4 w-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                <span>{ref.product_name} · {ref.decision_date}</span>
              </a>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">{ref.snippet}</p>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}
