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
      <header className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gold-500">
            —— COMPARATOR-SHORTLIST
          </p>
          <h1 className="mt-1 text-3xl font-bold text-white">
            Ergebnis<span className="italic">liste</span>
          </h1>
        </div>

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

        <div className="grid grid-cols-2 gap-4 rounded-lg border border-slate-700 bg-slate-800 p-4 text-sm sm:grid-cols-4">
          <div>
            <p className="text-slate-400">Kandidaten</p>
            <p className="text-lg font-semibold text-white">{data.candidates.length}</p>
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