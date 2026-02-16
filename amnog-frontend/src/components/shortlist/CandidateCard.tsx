"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { CandidateResult } from "@/lib/types";

const confidenceMap: Record<CandidateResult["confidence"], { label: string; variant: "red" | "yellow" | "green" }> = {
  niedrig: { label: "Low confidence", variant: "red" },
  mittel: { label: "Medium confidence", variant: "yellow" },
  hoch: { label: "High confidence", variant: "green" },
};

export function CandidateCard({ candidate }: { candidate: CandidateResult }) {
  const [expanded, setExpanded] = useState(false);
  const [showReferences, setShowReferences] = useState(false);

  const confidence = confidenceMap[candidate.confidence];

  return (
    <div 
      className="bg-bg-surface border border-white/[0.13] rounded-[14px] overflow-hidden shadow-[0_4px_20px_rgba(0,0,0,0.25)] mb-2.5 animate-fade-up"
      style={{
        animationDelay: `${(candidate.rank - 1) * 60}ms`,
        animationFillMode: 'backwards'
      }}
    >
      {/* Card body */}
      <div className="flex">
        {/* Left rank stripe */}
        <div className="w-11 flex-shrink-0 bg-bg2 border-r border-white/[0.07] flex items-start justify-center pt-4">
          <span className="font-serif text-[18px] text-gold italic">{candidate.rank}</span>
        </div>

        {/* Right content area */}
        <div className="flex-1 px-4 pt-4 pb-3.5">
          {/* Header row */}
          <div className="flex items-start justify-between gap-2 mb-3">
            <h3 className={`text-[13px] font-medium text-ink leading-snug flex-1 ${!expanded ? 'line-clamp-2' : ''}`}>
              {candidate.candidate_text}
            </h3>
            <Badge variant={confidence.variant} dot>
              {confidence.label}
            </Badge>
          </div>

          <button
            className="text-sm text-gold-500 hover:underline mb-3"
            onClick={() => setExpanded((prev) => !prev)}
          >
            {expanded ? "Weniger anzeigen" : "Mehr anzeigen"}
          </button>

          {/* Support Score Progress Bar */}
          <div className="space-y-1.5 mb-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-400">Support Score</span>
              <span className="font-semibold text-white">{candidate.support_score.toFixed(2)}</span>
            </div>
            <Progress value={candidate.support_score} max={1} />
          </div>

          <div className="text-sm text-slate-400 mb-3">Fälle: {candidate.support_cases}</div>

          {/* Expandable References */}
          <div>
            <button
              className="flex items-center gap-1 text-sm font-medium text-gold-500 hover:underline"
              onClick={() => setShowReferences((prev) => !prev)}
            >
              Belege anzeigen
              {showReferences ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {showReferences && (
              <ul className="mt-3 space-y-2 text-sm">
                {candidate.references.map((ref) => (
                  <li key={ref.decision_id + ref.url} className="rounded-md border border-slate-700 bg-slate-900 p-3">
                    <a
                      className="font-medium text-gold-400 hover:underline"
                      href={ref.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {ref.product_name} · {ref.decision_date}
                    </a>
                    <p className="mt-1 text-slate-400">{ref.snippet}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
