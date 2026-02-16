"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
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
  const [showEvidence, setShowEvidence] = useState(false);

  const confidence = confidenceMap[candidate.confidence];

  return (
    <Card className="flex gap-4">
      {/* Left: Rank Number */}
      <div className="flex w-16 flex-shrink-0 items-start justify-center pt-1">
        <div className="text-3xl font-bold text-gold-500">#{candidate.rank}</div>
      </div>

      {/* Right: Content */}
      <div className="flex-1 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-lg font-semibold text-white">Kandidat {candidate.rank}</h3>
          <Badge variant={confidence.variant} dot>
            {confidence.label}
          </Badge>
        </div>

        <p className={expanded ? "text-slate-300" : "line-clamp-3 text-slate-300"}>
          {candidate.candidate_text}
        </p>

        <button
          className="text-sm text-gold-500 hover:underline"
          onClick={() => setExpanded((prev) => !prev)}
        >
          {expanded ? "Weniger anzeigen" : "Mehr anzeigen"}
        </button>

        {/* Support Score Progress Bar */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">Support Score</span>
            <span className="font-semibold text-white">{candidate.support_score.toFixed(2)}</span>
          </div>
          <Progress value={candidate.support_score} max={1} />
        </div>

        {/* Collapsible Evidence Section */}
        <div>
          <button
            className="inline-flex items-center gap-1 text-[11px] font-medium text-gold opacity-85 bg-transparent border-none cursor-pointer"
            onClick={() => setShowEvidence((prev) => !prev)}
          >
            Evidence
            <svg
              className={`w-3 h-3 transition-transform ${showEvidence ? "rotate-180" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showEvidence && (
            <div className="relative">
              {candidate.references.map((ref) => (
                <div
                  key={`${ref.decision_id}-${ref.url}`}
                  className="relative border-t border-white/[0.07] ml-11 px-4 py-3"
                >
                  {/* 2px left accent bar */}
                  <div className="absolute left-0 h-[calc(100%-28px)] top-3.5 w-[2px] bg-gold/15 rounded-full" />
                  
                  {/* Drug name and date */}
                  <div className="flex justify-between items-start">
                    <span className="text-[12px] font-medium text-gold">{ref.product_name}</span>
                    <span className="text-[10px] text-ink-muted">{ref.decision_date}</span>
                  </div>
                  
                  {/* Description text */}
                  <p className="text-[12px] text-ink-soft leading-relaxed mt-1">{ref.snippet}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="text-sm text-slate-400">Fälle: {candidate.support_cases}</div>

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
    </Card>
  );
}
