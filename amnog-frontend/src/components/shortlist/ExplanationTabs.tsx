"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import {
  SCORING_EXPLANATION_BULLETS,
  SCORING_EXPLANATION_TITLE,
  SCORING_GLOSSARY,
} from "./scoringExplanation";

type Tab = "explanation" | "glossary";

export function ExplanationTabs() {
  const [activeTab, setActiveTab] = useState<Tab>("explanation");

  return (
    <Card className="space-y-4">
      {/* Tab navigation */}
      <div className="flex gap-2 border-b border-white/[0.13]" role="tablist">
        <button
          onClick={() => setActiveTab("explanation")}
          role="tab"
          aria-selected={activeTab === "explanation"}
          aria-controls="explanation-panel"
          id="explanation-tab"
          className={`px-4 py-2 text-sm font-medium transition-colors relative ${
            activeTab === "explanation"
              ? "text-gold"
              : "text-slate-400 hover:text-slate-300"
          }`}
        >
          Wie die Shortlist entsteht
          {activeTab === "explanation" && (
            <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-gold" />
          )}
        </button>
        <button
          onClick={() => setActiveTab("glossary")}
          role="tab"
          aria-selected={activeTab === "glossary"}
          aria-controls="glossary-panel"
          id="glossary-tab"
          className={`px-4 py-2 text-sm font-medium transition-colors relative ${
            activeTab === "glossary"
              ? "text-gold"
              : "text-slate-400 hover:text-slate-300"
          }`}
        >
          Glossar
          {activeTab === "glossary" && (
            <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-gold" />
          )}
        </button>
      </div>

      {/* Tab content */}
      <div className="pt-2">
        <div
          role="tabpanel"
          id="explanation-panel"
          aria-labelledby="explanation-tab"
          hidden={activeTab !== "explanation"}
          className="space-y-3"
        >
          <h2 className="text-xl font-semibold text-white">{SCORING_EXPLANATION_TITLE}</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-400">
            {SCORING_EXPLANATION_BULLETS.map((bullet) => (
              <li key={bullet}>{bullet}</li>
            ))}
          </ul>
        </div>

        <div
          role="tabpanel"
          id="glossary-panel"
          aria-labelledby="glossary-tab"
          hidden={activeTab !== "glossary"}
          className="space-y-3"
        >
          <h2 className="text-xl font-semibold text-white">Glossar</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-400">
            {SCORING_GLOSSARY.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}
