"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Download, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
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
      <header 
        className="bg-bg pt-14 pb-9 px-5 relative overflow-hidden before:content-[attr(data-watermark)] before:font-serif before:text-[130px] before:text-white/[0.025] before:absolute before:top-0 before:right-0 before:pointer-events-none"
        data-watermark="SHORTLIST"
      >
        <div className="relative z-10 space-y-3">
          <p className="text-gold text-[10px] font-medium tracking-[0.18em] uppercase flex items-center gap-2">
            <span className="inline-block w-4 h-px bg-gold"></span>
            COMPARATOR-SHORTLIST
            <span className="inline-block w-4 h-px bg-gold"></span>
          </p>
          <h1 className="font-serif text-[42px] leading-tight text-white">
            Ergebnis<span className="italic text-white/40">liste</span>
          </h1>
          <p className="text-ink-soft text-sm font-light leading-relaxed max-w-sm">
            Basierend auf Ihrer Eingabe haben wir passende Comparator-Kandidaten identifiziert.
          </p>
        </div>
      </header>

        <div className="flex flex-wrap items-center gap-2 mt-3">
          <Badge variant="gold">Ambiguity: {data.ambiguity}</Badge>
          <Badge>
            <Users className="h-3 w-3" />
            {data.candidates.length} Kandidaten
          </Badge>
          <button
            onClick={handleDownloadPdf}
            disabled={busyPdf}
            className="inline-flex items-center gap-1.5 bg-gold text-gold-dark text-[11px] font-semibold rounded-lg px-3.5 py-1.5 hover:bg-gold-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="h-4 w-4" />
            {busyPdf ? "Lade PDF..." : "PDF exportieren"}
          </button>
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
        <div>
          <p className="text-slate-400">Top-Score</p>
          <p className="text-lg font-semibold text-white">
            {data.candidates[0]?.support_score.toFixed(2) ?? "—"}
          </p>
        </div>
        <div>
          <p className="text-slate-400">G-BA-Fälle</p>
          <p className="text-lg font-semibold text-white">
            {data.candidates.reduce((sum, c) => sum + c.support_cases, 0)}
          </p>
        </div>
        <div>
          <p className="text-slate-400">Run-ID</p>
          <p className="truncate text-lg font-semibold text-white">{data.run_id.slice(0, 8)}</p>
        </div>
      </div>

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