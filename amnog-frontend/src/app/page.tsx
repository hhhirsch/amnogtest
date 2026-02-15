"use client";

import { Wizard } from "@/components/shortlist/Wizard";
import { ScoringExplanationCard } from "@/components/shortlist/ScoringExplanationCard";

export default function Home() {
  return (
    <div className="space-y-6">
      <ScoringExplanationCard />
      <Wizard />
    </div>
  );
}
