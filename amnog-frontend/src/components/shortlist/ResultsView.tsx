import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { ShortlistResponse } from "@/lib/types";
import { CandidateCard } from "./CandidateCard";
import { LeadGateDialog } from "./LeadGateDialog";

export function ResultsView({ data }: { data: ShortlistResponse }) {
  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Ergebnisliste</h1>
          <p className="text-sm text-slate-600">Run-ID: {data.run_id}</p>
        </div>
        <Badge>Ambiguity: {data.ambiguity}</Badge>
      </header>
      <LeadGateDialog runId={data.run_id} />
      <Separator />
      <div className="space-y-4">
        {data.candidates.map((candidate) => (
          <CandidateCard key={`${candidate.rank}-${candidate.candidate_text}`} candidate={candidate} />
        ))}
      </div>
    </section>
  );
}
