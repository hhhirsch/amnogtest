"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Download, Mail, RefreshCw } from "lucide-react";

import type { ShortlistResponse } from "@/lib/types";
import { downloadPdf } from "@/lib/api";

import { CandidateCard } from "./CandidateCard";

// Map ambiguity values to Eindeutigkeit (inverted)
const mapAmbiguityToEindeutigkeit = (ambiguity: "hoch" | "mittel" | "niedrig"): "hoch" | "mittel" | "niedrig" => {
  const mapping: Record<"hoch" | "mittel" | "niedrig", "hoch" | "mittel" | "niedrig"> = {
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
  
  // Get status with backward compatibility  const status = data.status || "ok";
  const notices = data.notices || [];
  const reasons = data.reasons || [];

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
  
  // Helper to get appropriate status message
  const getStatusMessage = () => {
    if (status === "no_result") {
      return "Keine belastbaren Ergebnisse gefunden. Bitte präzisieren Sie Ihre Eingaben.";
    }
    if (status === "needs_clarification") {
      return "Ergebnisse gefunden, aber mit Unsicherheiten. Erwägen Sie eine Präzisierung Ihrer Eingaben.";
    }
    return "Basierend auf Ihrer Eingabe haben wir passende Comparator-Kandidaten identifiziert.";
  };
  
  // Helper to get reason text in German
  const getReasonText = (reason: string) => {
    const reasonMap: Record<string, string> = {
      "NO_CANDIDATES": "Keine passenden Kandidaten gefunden",
      "TOO_GENERIC": "Eingabe zu unspezifisch (weniger als 3 aussagekräftige Begriffe)",
      "LOW_EVIDENCE": "Geringe Evidenzstärke",
      "HIGH_AMBIGUITY": "Mehrere Optionen ähnlich plausibel",
      "AREA_FALLBACK": "Ergänzend andere Therapiegebiete berücksichtigt",
    };
    return reasonMap[reason] || reason;
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
            {getStatusMessage()}
          </p>
        </div>
      </header>
      
      {/* Status indicators and notices */}
      {(status !== "ok" || notices.length > 0 || reasons.length > 0) && (
        <div className="space-y-3">
          {/* Status banner */}
          {status === "no_result" && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3">
              <h3 className="text-sm font-semibold text-red-400 mb-2">Kein belastbares Ergebnis</h3>
              <p className="text-xs text-ink-soft leading-relaxed">
                Um bessere Ergebnisse zu erzielen, erwägen Sie:
              </p>
              <ul className="mt-2 text-xs text-ink-soft space-y-1 list-disc list-inside">
                {reasons.includes("TOO_GENERIC") && <li>Detailliertere Beschreibung des Anwendungsgebiets</li>}
                {reasons.includes("NO_CANDIDATES") && <li>Anpassung der Suchkriterien oder des Therapiegebiets</li>}
                <li>Angabe von Therapielinie und Comparator-Typ</li>
                <li>Spezifischere Population oder Setting-Angaben</li>
              </ul>
            </div>
          )}
          
          {status === "needs_clarification" && (
            <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-3">
              <h3 className="text-sm font-semibold text-yellow-400 mb-2">Hinweis</h3>
              <p className="text-xs text-ink-soft leading-relaxed">
                Die Ergebnisse sind mit Unsicherheiten behaftet. Für präzisere Empfehlungen können Sie:
              </p>
              <ul className="mt-2 text-xs text-ink-soft space-y-1 list-disc list-inside">
                {reasons.includes("TOO_GENERIC") && <li>Mehr Details zum Anwendungsgebiet angeben</li>}
                {reasons.includes("LOW_EVIDENCE") && <li>Zusätzliche Suchkriterien spezifizieren</li>}
                {reasons.includes("HIGH_AMBIGUITY") && <li>Weitere Eingrenzung der Patientenpopulation</li>}
              </ul>
            </div>
          )}
          
          {/* Notices */}
          {notices.length > 0 && (
            <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 px-4 py-3">
              <h3 className="text-sm font-semibold text-blue-400 mb-2">Hinweise zur Datengrundlage</h3>
              <ul className="space-y-2">
                {notices.map((notice, idx) => (
                  <li key={idx} className="text-xs text-ink-soft leading-relaxed">
                    {notice}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Reasons (for debugging/transparency) */}
          {reasons.length > 0 && (
            <details className="rounded-lg border border-white/10 bg-surface px-4 py-2">
              <summary className="text-xs font-medium text-ink-muted cursor-pointer hover:text-ink-soft">
                Qualitätsindikatoren anzeigen
              </summary>
              <ul className="mt-2 space-y-1">
                {reasons.map((reason, idx) => (
                  <li key={idx} className="text-xs text-ink-soft">
                    • {getReasonText(reason)}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

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
        

      </div>

      {/* Only show stats and candidates if we have results */}
      {data.candidates.length > 0 && (
        <>
          <div className="grid grid-cols-4">
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
            <div className="border-t border-b border-white/[0.13] bg-surface px-3 py-3.5 text-center">
              <span className="block font-serif text-[24px] leading-none text-gold">
                {data.candidates.reduce((sum, c) => sum + c.support_cases, 0)}
              </span>
              <span className="mt-1 block text-[9px] font-medium uppercase tracking-[0.08em] text-ink-muted">G-BA-Fälle</span>
            </div>
            <div className="rounded-r-xl border border-white/[0.13] bg-surface px-3 py-3.5 text-center">
              <span className="block font-serif text-[24px] leading-none text-gold">
                {mapAmbiguityToEindeutigkeit(data.ambiguity)}
              </span>
              <span className="mt-1 block text-[9px] font-medium uppercase tracking-[0.08em] text-ink-muted">Eindeutigkeit</span>
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
        </>
      )}
    </section>
  );
}
