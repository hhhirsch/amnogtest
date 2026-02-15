"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
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

const STEP_LABELS = ["Therapiegebiet", "Indikation", "Kontext"];

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
    <Card className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-slate-900">Eingaben für Ihre Comparator-Shortlist</h2>
        
        {/* Visual Step Progress Indicator */}
        <div className="flex items-center gap-2 pt-2">
          {STEP_LABELS.map((label, index) => (
            <div key={label} className="flex items-center gap-2 flex-1">
              <div className="flex items-center gap-2 flex-1">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition-all ${
                    index < step
                      ? "bg-success-500 text-white"
                      : index === step
                      ? "bg-primary-600 text-white ring-4 ring-primary-100"
                      : "bg-slate-200 text-slate-500"
                  }`}
                >
                  {index < step ? (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    index + 1
                  )}
                </div>
                <span
                  className={`text-xs font-medium hidden sm:inline ${
                    index === step ? "text-slate-900" : "text-slate-500"
                  }`}
                >
                  {label}
                </span>
              </div>
              {index < STEP_LABELS.length - 1 && (
                <div
                  className={`h-0.5 flex-1 transition-colors ${
                    index < step ? "bg-success-500" : "bg-slate-200"
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl bg-slate-50 p-6">
        {steps[step]}
      </div>

      <div className="flex justify-between gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={() => setStep((prev) => Math.max(prev - 1, 0))}
          disabled={step === 0 || busy}
        >
          Zurück
        </Button>

        {step < steps.length - 1 ? (
          <Button type="button" onClick={onNext} disabled={busy}>
            Weiter
          </Button>
        ) : (
          <Button type="button" variant="success" onClick={onSubmit} disabled={busy}>
            {busy ? "Berechne..." : "Shortlist erstellen"}
          </Button>
        )}
      </div>
    </Card>
  );
}