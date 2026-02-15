import { ScoringExplanationCard } from "@/components/shortlist/ScoringExplanationCard";
import { Wizard } from "@/components/shortlist/Wizard";

const INTRO_TEXT =
  "Im AMNOG-Verfahren ist die Wahl des zweckmäßigen Vergleichers zentral: Sie bestimmt, gegen welche Therapie der Zusatznutzen bewertet wird und beeinflusst damit Studiendesign, Evidenzbewertung und Verhandlungsspielräume. Dieses Tool hilft, passende Comparator-Kandidaten aus bisherigen G-BA-Entscheidungen datenbasiert zu identifizieren.";

export default function Home() {
  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h1 className="text-3xl font-bold tracking-tight">zVT Navigator</h1>
        <p className="max-w-4xl text-sm leading-6 text-slate-700">{INTRO_TEXT}</p>
      </section>

      <section
        className="relative overflow-hidden rounded-xl border border-slate-200 bg-slate-900/10 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: 'url("/assets/89374AF2-03B6-478F-908E-521C995CEB97.png")' }}
      >
        <div className="absolute inset-0 bg-white/80 backdrop-blur-[1px]" />
        <div className="relative p-4 sm:p-6">
          <Wizard />
        </div>
      </section>

      <details className="rounded-lg border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-base font-semibold text-slate-900">
          Wie die Shortlist entsteht (MVP)
        </summary>
        <div className="mt-4">
          <ScoringExplanationCard />
        </div>
      </details>
    </div>
  );
}
