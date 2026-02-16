"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { createShortlist } from "@/lib/api";
import { ShortlistRequestSchema, type ShortlistRequestInput } from "@/lib/validators";
import { StepContext } from "./StepContext";
import { StepIndication } from "./StepIndication";
import { StepTherapyArea } from "./StepTherapyArea";

const STORAGE_KEY = "amnog-shortlist-draft";

function loadDraft(): Partial<ShortlistRequestInput> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

export function Wizard() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [values, setValues] = useState<Partial<ShortlistRequestInput>>(() => loadDraft());

  const steps = useMemo(
    () => [
      <StepTherapyArea
        key="therapy"
        values={values}
        onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))}
      />,
      <StepIndication
        key="indication"
        values={values}
        onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))}
      />,
      <StepContext
        key="context"
        values={values}
        onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))}
      />,
    ],
    [values]
  );

  const persist = (next: Partial<ShortlistRequestInput>) => {
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  };

  const onNext = () => {
    const next = Math.min(step + 1, steps.length - 1);
    setStep(next);
    persist(values);
  };

  const onSubmit = async () => {
    const parsed = ShortlistRequestSchema.safeParse(values);
    if (!parsed.success) {
      toast.error(parsed.error.issues[0]?.message ?? "Bitte Eingaben prüfen.");
      return;
    }

    setBusy(true);
    try {
      const response = await createShortlist(parsed.data);
      localStorage.removeItem(STORAGE_KEY);
      router.push(`/lead/${response.run_id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unbekannter Fehler");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card goldBorder className="space-y-6">
      {/* Step Indicator */}
      <div className="flex items-center justify-center gap-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex items-center">
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors ${
                i < step
                  ? "border-gold-500 bg-gold-500 text-slate-900"
                  : i === step
                    ? "border-gold-500 bg-gold-500 text-slate-900"
                    : "border-slate-600 bg-slate-800 text-slate-400"
              }`}
            >
              {i + 1}
            </div>
            {i < 2 && (
              <div
                className={`h-0.5 w-12 transition-colors ${
                  i < step ? "bg-gold-500" : "bg-slate-600"
                }`}
              />
            )}
          </div>
        ))}
      </div>

      <div className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gold-500">
            SCHRITT {step + 1} VON 3
          </p>
          <h2 className="mt-1 text-2xl font-bold text-white">Eingaben für Ihre Comparator-Shortlist</h2>
        </div>

        {steps[step]}

        <div className="flex justify-between gap-2 pt-2">
          <button
            type="button"
            onClick={() => setStep((prev) => Math.max(prev - 1, 0))}
            disabled={step === 0 || busy}
            className="flex items-center gap-1.5 text-[13px] font-medium text-ink-muted bg-transparent border border-white/[0.13] rounded-[9px] px-4 py-2.5 transition-all hover:border-ink-soft hover:text-ink-soft disabled:opacity-25 disabled:cursor-not-allowed"
          >
            Zurück
          </button>

          {step < steps.length - 1 ? (
            <button 
              type="button" 
              onClick={onNext} 
              disabled={busy}
              className="group flex items-center gap-2 text-[14px] font-semibold text-[#1a1206] bg-gold border-none rounded-[9px] px-6 py-2.5 transition-all shadow-[0_4px_20px_rgba(232,184,75,0.25)] hover:bg-[#f0c55a] hover:shadow-[0_6px_28px_rgba(232,184,75,0.4)] hover:-translate-y-px disabled:opacity-25 disabled:cursor-not-allowed"
            >
              Weiter 
              <svg 
                className="h-4 w-4 transition-transform group-hover:translate-x-[3px]" 
                viewBox="0 0 16 16" 
                fill="none" 
                xmlns="http://www.w3.org/2000/svg"
              >
                <path 
                  d="M6 3L11 8L6 13" 
                  stroke="currentColor" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          ) : (
            <button 
              type="button" 
              onClick={onSubmit} 
              disabled={busy}
              className="group flex items-center gap-2 text-[14px] font-semibold text-[#1a1206] bg-gold border-none rounded-[9px] px-6 py-2.5 transition-all shadow-[0_4px_20px_rgba(232,184,75,0.25)] hover:bg-[#f0c55a] hover:shadow-[0_6px_28px_rgba(232,184,75,0.4)] hover:-translate-y-px disabled:opacity-25 disabled:cursor-not-allowed"
            >
              {busy ? "Berechne..." : "Shortlist erstellen"}
              <svg 
                className="h-4 w-4 transition-transform group-hover:translate-x-[3px]" 
                viewBox="0 0 16 16" 
                fill="none" 
                xmlns="http://www.w3.org/2000/svg"
              >
                <path 
                  d="M6 3L11 8L6 13" 
                  stroke="currentColor" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          )}
        </div>
      </div>
    </Card>
  );
}