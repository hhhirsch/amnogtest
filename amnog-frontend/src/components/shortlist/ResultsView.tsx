"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Download, Users, Mail, RefreshCw, Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { ShortlistResponse } from "@/lib/types";
import { downloadPdf } from "@/lib/api";

import { CandidateCard } from "./CandidateCard";

// Map ambiguity values to Eindeutigkeit (inverted)
const mapAmbiguityToEindeutigkeit = (ambiguity: "hoch" | "mittel" | "niedrig"): string => {
  const mapping = {
    niedrig: "hoch",
    mittel: "mittel",
    hoch: "niedrig",
  };
  return mapping[ambiguity] ?? "mittel"; // Fallback to "mittel" for safety
};

const STORAGE_KEY = "amnog-shortlist-draft";

export function ResultsView({ data }: { data: ShortlistResponse }) {
  const router = useRouter();
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

  const handleContactClick = () => {
    const subject = encodeURIComponent("zVT Navigator – Kontaktaufnahme");
    const body = encodeURIComponent(
      `Hallo,\n\nich möchte Kontakt aufnehmen bezüglich meiner Analyse.\n\nViele Grüße`
    );
    window.location.href = `mailto:hirsch.hans92@gmail.com?subject=${subject}&body=${body}`;
  };

  const handleNewRequest = () => {
    if (typeof window === "undefined") return;
    
    // Clear wizard draft from localStorage
    localStorage.removeItem(STORAGE_KEY);
    
    // Navigate to home
    router.push("/");
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

      <div className="space-y-3 mt-3">
        {/* First row: PDF Download + Contact (two equal gold buttons) */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleDownloadPdf}
            disabled={busyPdf}
            className="flex-1 inline-flex items-center justify-center gap-1.5 bg-gold text-gold-dark text-[11px] font-semibold rounded-lg px-3.5 py-1.5 hover:bg-gold-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="h-4 w-4" />
            {busyPdf ? "Lade PDF..." : "PDF downloaden"}
          </button>
          <button
            onClick={handleContactClick}
            className="flex-1 inline-flex items-center justify-center gap-1.5 bg-gold text-gold-dark text-[11px] font-semibold rounded-lg px-3.5 py-1.5 hover:bg-gold-hover transition-colors"
          >
            <Mail className="h-4 w-4" />
            Kontakt aufnehmen
          </button>
        </div>
        
        {/* Second row: Neue Anfrage (full-width ghost button) */}
        <button
          onClick={handleNewRequest}
          className="w-full inline-flex items-center justify-center gap-2 bg-transparent border border-white/[0.12] rounded-[10px] text-[rgba(240,242,247,0.5)] text-sm font-['DM_Sans'] px-[13px] py-[13px] hover:bg-white/5 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Neue Anfrage
        </button>
        
        {/* Third row: Eindeutigkeit + Candidates */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5">
            <Badge variant="gold">Eindeutigkeit: {mapAmbiguityToEindeutigkeit(data.ambiguity)}</Badge>
            <div className="group relative">
              <Info 
                className="h-3.5 w-3.5 text-ink-muted cursor-help" 
                tabIndex={0}
                role="button"
                aria-label="Erklärung zur Eindeutigkeit"
              />
              <div 
                className="absolute left-0 top-6 z-50 hidden group-hover:block group-focus-within:block w-64 rounded-lg bg-surface border border-white/[0.13] p-3 shadow-lg"
                role="tooltip"
              >
                <p className="text-xs text-ink-soft leading-relaxed">
                  Misst, wie stark sich der Top-Kandidat vom Rest absetzt. Hoch = klarer Favorit, niedrig = mehrere ähnlich plausible Optionen.
                </p>
              </div>
            </div>
          </div>
          <Badge>
            <Users className="h-3 w-3" />
            {data.candidates.length} Kandidaten
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-3">
        <div className="rounded-l-xl border border-white/[0.13] bg-surface px-3 py-3.5 text-center">
          <span className="block font-serif text-[24px] leading-none text-gold">{data.candidates.length}</span>
          <span className="mt-1 block text-[9px] font-medium uppercase tracking-[0.08em] text-ink-muted">Kandidaten</span>
        </div>
        <div className="border-t border-b border-white/[0.13] bg-surface px-3 py-3.5 text-center">
          <span className="block font-serif text-[24px] leading-none text-gold">
            {data.candidates[0]?.support_score.toFixed(2) ?? "—"}
          </span>
          <span className="mt-1 block text-[9px] font-medium uppercase tracking-[0.08em] text-ink-muted">Top-Score</span>
        </div>
        <div className="rounded-r-xl border border-white/[0.13] bg-surface px-3 py-3.5 text-center">
          <span className="block font-serif text-[24px] leading-none text-gold">
            {data.candidates.reduce((sum, c) => sum + c.support_cases, 0)}
          </span>
          <span className="mt-1 block text-[9px] font-medium uppercase tracking-[0.08em] text-ink-muted">G-BA-Fälle</span>
        </div>
      </div>

      <div>
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-400">
          RANKED NACH SUPPORT SCORE
        </h2>
        <div>
          {data.candidates.map((candidate) => (
            <CandidateCard key={`${candidate.rank}-${candidate.candidate_text}`} candidate={candidate} />
          ))}
        </div>
      </div>
    </section>
  );
}
