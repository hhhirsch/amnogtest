import Image from "next/image";
import { ScoringExplanationCard } from "@/components/shortlist/ScoringExplanationCard";
import { Wizard } from "@/components/shortlist/Wizard";

const INTRO_TEXT =
  "Im AMNOG-Verfahren ist die Wahl der zweckmäßigen Vergleichstherapie zentral: Sie bestimmt, gegen welche Therapie der Zusatznutzen bewertet wird und beeinflusst damit Studiendesign, Evidenzbewertung und Verhandlungsspielräume. Dieses Tool hilft, passende Comparator-Kandidaten aus bisherigen G-BA-Entscheidungen datenbasiert zu identifizieren.";

export default function Home() {
  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <p className="text-[9px] font-semibold uppercase tracking-wider text-gold-500">—— AMNOG-VERFAHREN</p>
        <Image src="/logo.svg" alt="zVT Navigator" width={200} height={64} className="h-16 w-auto" />
        <p className="max-w-4xl text-sm leading-6 text-slate-400 pt-2">{INTRO_TEXT}</p>
      </section>

      <section>
        <Wizard />
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
