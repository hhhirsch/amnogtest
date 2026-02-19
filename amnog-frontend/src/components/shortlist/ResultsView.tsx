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
const MAX_RELIABILITY_REASONS = 3;

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

  // Derive status if not explicitly provided
  const status = data.status || (data.candidates.length === 0 ? "no_result" : "ok");
  const reliability = data.reliability ?? data.plausibility ?? "mittel";

  // Filter the generic fallback sentence which is not suitable as a bullet for hoch/mittel
  const rawReasons = (data.reliability_reasons ?? data.plausibility_reasons ?? []).filter(
    (r) => !r.toLowerCase().includes("bewertung basiert")
  );

  // Compute FE-side fallback reasons when backend provided none
  const cases = data.candidates[0]?.support_cases ?? 0;
  const topConf = data.candidates[0]?.confidence ?? "mittel";
  const ambiguity = data.ambiguity ?? "mittel";

  let reliabilityReasons: string[];
  if (rawReasons.length > 0) {
    reliabilityReasons = rawReasons.slice(0, MAX_RELIABILITY_REASONS);
  } else if (reliability === "mittel") {
    const lim: string[] = [];
    if (cases === 2) lim.push("Nur 2 ähnliche Entscheidungen vorhanden.");
    if (ambiguity === "hoch") lim.push("Mehrere Comparatoren sind ähnlich plausibel.");
    else if (ambiguity === "mittel") lim.push("Trennschärfe ist nur mittel – mehrere Optionen bleiben möglich.");
    if (topConf === "niedrig") lim.push("Die Übereinstimmung ist nur schwach.");
    reliabilityReasons = lim.slice(0, 2); // max 2, same as backend fallback
  } else if (reliability === "hoch") {
    const pos: string[] = [];
    if (cases >= 3) pos.push(`${cases} vergleichbare Entscheidungen stützen die Top-Option.`);
    if (ambiguity === "niedrig") pos.push("Klare Trennschärfe zwischen Top-Option und Alternativen.");
    if (topConf === "hoch") pos.push("Hohe Modellsicherheit des Matchings.");
    reliabilityReasons = pos.slice(0, 2); // max 2, same as backend fallback
  } else {
    reliabilityReasons = [];
  }

  // Determine header text based on reliability/status
  const getHeaderText = () => {
    if (status === "no_result" || reliability === "niedrig") {
      return "Basierend auf Ihrer Eingabe konnten wir nur eingeschränkt Comparator-Kandidaten identifizieren.";
    }
    return "Basierend auf Ihrer Eingabe haben wir passende Comparator-Kandidaten identifiziert.";
  };

  // Reliability badge mapping
  const getReliabilityBadge = (rel: "hoch" | "mittel" | "niedrig") => {
    const mapping = {
      hoch: { text: "✅ Belastbar", bgColor: "bg-green-500/10", textColor: "text-green-400", borderColor: "border-green-500/30" },
      mittel: { text: "🟡 Mit Einschränkungen", bgColor: "bg-yellow-500/10", textColor: "text-yellow-400", borderColor: "border-yellow-500/30" },
      niedrig: { text: "🔴 Nicht belastbar", bgColor: "bg-red-500/10", textColor: "text-red-400", borderColor: "border-red-500/30" },
    };
    return mapping[rel];
  };

  const reliabilityBadge = getReliabilityBadge(reliability);

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
            {getHeaderText()}
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
      </div>

      {/* (1) Reliability Card - Always visible at top */}
      <div className={`rounded-xl border ${reliabilityBadge.borderColor} ${reliabilityBadge.bgColor} px-4 py-4 space-y-3`}>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-white">
            Ergebnis-Verlässlichkeit
          </h3>
          <span className={`text-xs font-semibold px-3 py-1 rounded-full ${reliabilityBadge.bgColor} ${reliabilityBadge.textColor} border ${reliabilityBadge.borderColor}`}>
            {reliabilityBadge.text}
          </span>
        </div>
        
        {reliability === "hoch" && (
          <div className="space-y-1">
            <p className="text-sm text-ink-soft leading-relaxed">
              Die Top-Option ist durch mehrere vergleichbare G-BA-Entscheidungen gut gestützt.
            </p>
          </div>
        )}
        {reliability === "mittel" && reliabilityReasons.length > 0 && (
          <p className="text-sm text-ink-soft leading-relaxed">
            Die Ergebnisse sind grundsätzlich gestützt, aber folgende Punkte schränken die Verlässlichkeit ein:
          </p>
        )}
        {reliabilityReasons.length > 0 && (
          <ul className="space-y-2">
            {reliabilityReasons.map((reason, i) => (
              <li key={i} className="text-sm text-ink-soft leading-relaxed flex items-start gap-2">
                <span className="text-gold mt-0.5">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        )}
        {reliability === "mittel" && reliabilityReasons.length === 0 && (
          <p className="text-sm text-ink-soft leading-relaxed">
            Bewertung basiert auf verfügbaren G-BA-Entscheidungen.
          </p>
        )}
        
        {/* Notices (if any) - visually separated */}
        {data.notices && data.notices.length > 0 && (
          <div className="mt-4 pt-3 border-t border-white/[0.1] space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-gold/80">
              Hinweise
            </p>
            {data.notices.map((notice, i) => (
              <p key={i} className="text-sm text-ink-soft leading-relaxed">{notice}</p>
            ))}
          </div>
        )}
      </div>

      {/* (2) Data Basis Card - Always visible, NOT collapsible */}
      <div className="rounded-xl border border-white/[0.13] bg-surface px-4 py-4 space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-white">
          Datenbasis
        </h3>
        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-1">
            <span className="block font-serif text-[24px] leading-none text-gold">
              {data.candidates[0]?.support_cases ?? 0}
            </span>
            {/* Show support_cases from top candidate only (as per requirements: focus on top candidate's evidence) */}
            <span className="block text-[10px] font-medium uppercase tracking-wider text-ink-muted">Fälle</span>
          </div>
          <div className="space-y-1">
            <span className="block font-serif text-[24px] leading-none text-gold">
              {data.candidates.length >= 2 && status !== "no_result" ? mapAmbiguityToEindeutigkeit(data.ambiguity) : "—"}
            </span>
            <span className="block text-[10px] font-medium uppercase tracking-wider text-ink-muted">Trennschärfe</span>
          </div>
          <div className="space-y-1">
            <span className="block font-serif text-[24px] leading-none text-gold">
              {data.candidates[0]?.confidence ?? "—"}
            </span>
            <span className="block text-[10px] font-medium uppercase tracking-wider text-ink-muted">Modellsicherheit</span>
          </div>
        </div>
      </div>

      {/* (3) Candidate List - conditional on status */}
      {status === "no_result" || data.candidates.length === 0 ? (
        <div className="rounded-xl border border-white/[0.13] bg-surface px-6 py-8 text-center space-y-4">
          <p className="text-lg text-ink-soft">
            Leider konnten wir keine passenden Comparator-Kandidaten identifizieren.
          </p>
          <p className="text-sm text-ink-muted">
            Bitte präzisieren Sie Ihre Eingabe oder kontaktieren Sie uns für weitere Unterstützung.
          </p>
        </div>
      ) : (
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
      )}
    </section>
  );
}
