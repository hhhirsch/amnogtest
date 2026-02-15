import { Card } from "@/components/ui/card";
import {
  SCORING_EXPLANATION_BULLETS,
  SCORING_EXPLANATION_TITLE,
  SCORING_GLOSSARY,
  SCORING_RELATIVE_NOTE,
} from "./scoringExplanation";

type ScoringExplanationCardProps = {
  compact?: boolean;
};

export function ScoringExplanationCard({ compact = false }: ScoringExplanationCardProps) {
  if (compact) {
    return (
      <Card className="space-y-2">
        <h2 className="text-lg font-semibold text-white">Einordnung der Ergebnisse</h2>
        <p className="text-sm text-slate-400">
          Support ist die Evidenzstärke aus ähnlichen, aktuellen und passenden Beschlüssen. Höher bedeutet mehr Evidenz.
        </p>
        <details className="text-sm text-slate-400">
          <summary className="cursor-pointer font-medium text-slate-200">Mehr erfahren</summary>
          <div className="mt-2 space-y-3">
            <FullExplanation />
          </div>
        </details>
      </Card>
    );
  }

  return (
    <Card className="space-y-3">
      <FullExplanation />
    </Card>
  );
}

function FullExplanation() {
  return (
    <>
      <h2 className="text-xl font-semibold text-white">{SCORING_EXPLANATION_TITLE}</h2>
      <ul className="list-disc space-y-1 pl-5 text-sm text-slate-400">
        {SCORING_EXPLANATION_BULLETS.map((bullet) => (
          <li key={bullet}>{bullet}</li>
        ))}
      </ul>
      <p className="text-sm text-slate-400">{SCORING_RELATIVE_NOTE}</p>
      <div>
        <h3 className="text-sm font-semibold text-slate-200">Glossar</h3>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-400">
          {SCORING_GLOSSARY.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </>
  );
}
