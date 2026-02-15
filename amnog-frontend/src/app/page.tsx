import { ScoringExplanationCard } from "@/components/shortlist/ScoringExplanationCard";
import { Wizard } from "@/components/shortlist/Wizard";

const INTRO_TEXT =
  "Im AMNOG-Verfahren ist die Wahl des zweckmäßigen Vergleichers zentral: Sie bestimmt, gegen welche Therapie der Zusatznutzen bewertet wird und beeinflusst damit Studiendesign, Evidenzbewertung und Verhandlungsspielräume. Dieses Tool hilft, passende Comparator-Kandidaten aus bisherigen G-BA-Entscheidungen datenbasiert zu identifizieren.";

export default function Home() {
  return (
    <div className="space-y-10">
      <section className="space-y-4 text-center">
        <div className="inline-flex rounded-full bg-primary-100 px-4 py-1.5 text-sm font-semibold text-primary-700">
          AMNOG Comparator Tool
        </div>
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-primary-600 to-primary-800 bg-clip-text text-transparent sm:text-5xl">
          zVT Navigator
        </h1>
        <p className="mx-auto max-w-3xl text-base leading-7 text-slate-600">{INTRO_TEXT}</p>
      </section>

      <section
        className="relative overflow-hidden rounded-2xl border-2 border-slate-200 bg-slate-900/10 bg-cover bg-center bg-no-repeat shadow-soft"
        style={{ backgroundImage: 'url("/assets/89374AF2-03B6-478F-908E-521C995CEB97.png")' }}
      >
        <div className="absolute inset-0 bg-white/85 backdrop-blur-[2px]" />
        <div className="relative p-6 sm:p-8">
          <Wizard />
        </div>
      </section>

      <details className="group rounded-2xl border-2 border-slate-200 bg-white p-6 shadow-soft transition-all hover:shadow-lg">
        <summary className="cursor-pointer list-none text-lg font-semibold text-slate-900 flex items-center justify-between">
          <span>Wie die Shortlist entsteht (MVP)</span>
          <svg
            className="h-5 w-5 transition-transform group-open:rotate-180"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </summary>
        <div className="mt-6 border-t border-slate-100 pt-6">
          <ScoringExplanationCard />
        </div>
      </details>
    </div>
  );
}
