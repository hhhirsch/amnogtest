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
    <section className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Ergebnisliste</h1>
          <p className="text-sm text-slate-600">Run-ID: {data.run_id}</p>
        </div>

        <div className="flex items-center gap-2">
          <Badge>Ambiguity: {data.ambiguity}</Badge>
          <Button onClick={handleDownloadPdf} disabled={busyPdf}>
            {busyPdf ? "Lade PDF..." : "PDF exportieren"}
          </Button>
        </div>
      </header>

      <Separator />

      <div className="space-y-4">
        {data.candidates.map((candidate) => (
          <CandidateCard key={`${candidate.rank}-${candidate.candidate_text}`} candidate={candidate} />
        ))}
      </div>
    </section>
  );
}