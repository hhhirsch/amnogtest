"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
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
      <header className="rounded-2xl border-2 border-slate-200 bg-white p-6 shadow-soft">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold text-slate-900">Ergebnisliste</h1>
              <Badge variant="primary">
                <svg className="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                {data.candidates.length} Kandidaten
              </Badge>
            </div>
            <p className="text-sm text-slate-500 font-mono">Run-ID: {data.run_id}</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex flex-col items-end gap-1">
              <Badge variant={data.ambiguity === "niedrig" ? "success" : data.ambiguity === "mittel" ? "warning" : "danger"}>
                Ambiguity: {data.ambiguity}
              </Badge>
            </div>
            <Button onClick={handleDownloadPdf} disabled={busyPdf}>
              {busyPdf ? (
                <>
                  <svg className="h-4 w-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Lade PDF...
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  PDF exportieren
                </>
              )}
            </Button>
          </div>
        </div>
      </header>

      <div className="space-y-4">
        {data.candidates.map((candidate) => (
          <CandidateCard key={`${candidate.rank}-${candidate.candidate_text}`} candidate={candidate} />
        ))}
      </div>
    </section>
  );
}