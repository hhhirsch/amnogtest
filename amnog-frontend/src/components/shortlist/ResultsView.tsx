"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Download, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ShortlistResponse } from "@/lib/types";
import { downloadPdf } from "@/lib/api";

import { CandidateCard } from "./CandidateCard";

export function ResultsView({ data }: { data: ShortlistResponse }) {
  const [busyPdf, setBusyPdf] = useState(false);

  const handleDownloadPdf = async () => {
    setBusyPdf(true);
    try {
      const blob = await downloadPdf(data.run_id);

      // Download im Browser auslösen
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;

      // Fallback-Name (Backend setzt normalerweise Content-Disposition)
      a.download = "zVT_Shortlist.pdf";

      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      toast.success("PDF wurde heruntergeladen.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "PDF Download fehlgeschlagen.");
    } finally {
      setBusyPdf(false);
    }
  };

  return (
    <section className="space-y-6">
      <header className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gold-500">
            —— COMPARATOR-SHORTLIST
          </p>
          <h1 className="mt-1 text-3xl font-bold text-white">
            Ergebnis<span className="italic">liste</span>
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="gold">Ambiguity: {data.ambiguity}</Badge>
          <Badge>
            <Users className="h-3 w-3" />
            {data.candidates.length} Kandidaten
          </Badge>
          <Button onClick={handleDownloadPdf} disabled={busyPdf} size="sm" className="gap-2">
            <Download className="h-4 w-4" />
            {busyPdf ? "Lade PDF..." : "PDF exportieren"}
          </Button>
        </div>

        <div className="flex">
          <div className="flex-1 rounded-l-xl border border-white/[0.13] bg-surface px-3 py-3.5 text-center">
            <span className="block font-serif text-[24px] leading-none text-gold">{data.candidates.length}</span>
            <span className="mt-1 block text-[9px] font-medium uppercase tracking-[0.08em] text-ink-muted">Kandidaten</span>
          </div>
          <div className="flex-1 border border-white/[0.13] bg-surface px-3 py-3.5 text-center">
            <span className="block font-serif text-[24px] leading-none text-gold">
              {data.candidates[0]?.support_score.toFixed(2) ?? "—"}
            </span>
            <span className="mt-1 block text-[9px] font-medium uppercase tracking-[0.08em] text-ink-muted">Top-Score</span>
          </div>
          <div className="flex-1 border border-white/[0.13] bg-surface px-3 py-3.5 text-center">
            <span className="block font-serif text-[24px] leading-none text-gold">
              {data.candidates.reduce((sum, c) => sum + c.support_cases, 0)}
            </span>
            <span className="mt-1 block text-[9px] font-medium uppercase tracking-[0.08em] text-ink-muted">G-BA-Fälle</span>
          </div>
          <div className="flex-1 rounded-r-xl border border-white/[0.13] bg-surface px-3 py-3.5 text-center">
            <span className="block truncate font-serif text-[24px] leading-none text-gold">{data.run_id.slice(0, 8)}</span>
            <span className="mt-1 block text-[9px] font-medium uppercase tracking-[0.08em] text-ink-muted">Run-ID</span>
          </div>
        </div>
      </header>

      <div>
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-400">
          RANKED NACH SUPPORT SCORE
        </h2>
        <div className="space-y-4">
          {data.candidates.map((candidate) => (
            <CandidateCard key={`${candidate.rank}-${candidate.candidate_text}`} candidate={candidate} />
          ))}
        </div>
      </div>
    </section>
  );
}