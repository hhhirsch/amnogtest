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
import { ChevronRight } from "lucide-react";

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
          <Button
            type="button"
            variant="outline"
            onClick={() => setStep((prev) => Math.max(prev - 1, 0))}
            disabled={step === 0 || busy}
          >
            Zurück
          </Button>

          {step < steps.length - 1 ? (
            <Button type="button" onClick={onNext} disabled={busy} className="gap-2">
              Weiter <ChevronRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button type="button" onClick={onSubmit} disabled={busy}>
              {busy ? "Berechne..." : "Shortlist erstellen"}
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}