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

export function Wizard() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [values, setValues] = useState<Partial<ShortlistRequestInput>>(() => loadDraft());

  const steps = useMemo(
    () => [
      <StepTherapyArea key="therapy" values={values} onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))} />,
      <StepIndication key="indication" values={values} onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))} />,
      <StepContext key="context" values={values} onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))} />,
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
      router.push(`/run/${response.run_id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unbekannter Fehler");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="space-y-4">
      <h1 className="text-2xl font-bold">AMNOG Comparator Wizard</h1>
      <p className="text-sm text-slate-600">Schritt {step + 1} von 3</p>
      {steps[step]}
      <div className="flex justify-between gap-2">
        <Button variant="outline" onClick={() => setStep((prev) => Math.max(prev - 1, 0))} disabled={step === 0 || busy}>
          Zurück
        </Button>
        {step < steps.length - 1 ? (
          <Button onClick={onNext} disabled={busy}>Weiter</Button>
        ) : (
          <Button onClick={onSubmit} disabled={busy}>{busy ? "Berechne..." : "Shortlist erstellen"}</Button>
        )}
      </div>
    </Card>
  );
}
