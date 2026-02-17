"use client";

import { useState } from "react";
import Image from "next/image";
import { RefreshCw } from "lucide-react";
import { ScoringExplanationCard } from "@/components/shortlist/ScoringExplanationCard";
import { Wizard } from "@/components/shortlist/Wizard";

const INTRO_TEXT =
  "Im AMNOG-Verfahren ist die Wahl der zweckmäßigen Vergleichstherapie zentral: Sie bestimmt, gegen welche Therapie der Zusatznutzen bewertet wird und beeinflusst damit Studiendesign, Evidenzbewertung und Verhandlungsspielräume. Dieses Tool hilft, passende Comparator-Kandidaten aus bisherigen G-BA-Entscheidungen datenbasiert zu identifizieren.";

const STORAGE_KEY = "amnog-shortlist-draft";

export default function Home() {
  const [currentStep, setCurrentStep] = useState(0);

  const handleNewRequest = () => {
    if (typeof window === "undefined") return;
    
    // Clear wizard draft from localStorage
    localStorage.removeItem(STORAGE_KEY);
    
    // Force reload to reset wizard
    window.location.reload();
  };

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        {/* Header with logo/eyebrow and button */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-wider text-gold-500">—— AMNOG-VERFAHREN</p>
            <Image src="/logozVTnavigator.svg" alt="zVT Navigator" width={200} height={32} className="mt-2 mb-4" />
          </div>
          {currentStep > 0 && (
            <button
              onClick={handleNewRequest}
              className="inline-flex items-center gap-2 bg-transparent border border-white/[0.12] rounded-lg text-[rgba(240,242,247,0.5)] text-xs font-['DM_Sans'] px-[14px] py-2 hover:bg-white/5 transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Neue Anfrage
            </button>
          )}
        </div>
        <p className="max-w-4xl text-sm leading-6 text-slate-400 pt-2">{INTRO_TEXT}</p>
      </section>

      <section>
        <Wizard onStepChange={setCurrentStep} />
      </section>

      <details className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <summary className="flex cursor-pointer items-center gap-2 text-base font-semibold text-white">
          Wie die Shortlist entsteht
        </summary>
        <div className="mt-4">
          <ScoringExplanationCard />
        </div>
      </details>
    </div>
  );
}
