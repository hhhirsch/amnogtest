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

// Button styles
const BACK_BUTTON_CLASSES = "flex items-center gap-1.5 text-[13px] font-medium text-ink-muted bg-transparent border border-white/[0.13] rounded-[9px] px-4 py-2.5 transition-all hover:border-ink-soft hover:text-ink-soft disabled:opacity-25 disabled:cursor-not-allowed";
const NEXT_BUTTON_CLASSES = "group flex items-center gap-2 text-[14px] font-semibold text-[#1a1206] bg-[#e8b84b] border-none rounded-[9px] px-6 py-2.5 transition-all shadow-[0_4px_20px_rgba(232,184,75,0.25)] hover:bg-[#f0c55a] hover:shadow-[0_6px_28px_rgba(232,184,75,0.4)] hover:-translate-y-px disabled:opacity-25 disabled:cursor-not-allowed";

// Right arrow SVG icon component
const RightArrowIcon = () => (
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
);

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
    <Card className="bg-surface rounded-[20px] border border-white/[0.13] overflow-hidden shadow-[0_24px_64px_rgba(0,0,0,0.5)] space-y-6">
      {/* Gold top-line */}
      <div className="h-0.5 bg-gradient-to-r from-transparent via-gold to-transparent opacity-60" />
      {/* Step Indicator */}
      <div className="flex items-center justify-center">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex items-center">
            <div
              className={`flex h-[34px] w-[34px] items-center justify-center rounded-full border-2 text-xs transition-all ${
                i < step
                  ? "border-gold bg-gold/15 text-gold"
                  : i === step
                    ? "border-gold bg-gold text-gold-dark font-semibold shadow-[0_0_0_6px_rgba(232,184,75,0.15),0_4px_16px_rgba(232,184,75,0.3)]"
                    : "border-white/20 bg-bg2 text-ink-muted font-medium"
              }`}
            >
              {i < step ? (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M11.6666 3.5L5.24992 9.91667L2.33325 7"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : (
                i + 1
              )}
            </div>
            {i < 2 && (
              <div className="relative h-0.5 flex-1 mx-2 bg-white/10">
                <div
                  className={`absolute inset-0 bg-gold transition-all duration-500 ${
                    i < step ? "w-full" : "w-0"
                  }`}
                />
              </div>
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
            className={BACK_BUTTON_CLASSES}
          >
            Zurück
          </button>

          {step < steps.length - 1 ? (
            <button 
              type="button" 
              onClick={onNext} 
              disabled={busy}
              className={NEXT_BUTTON_CLASSES}
            >
              Weiter 
              <RightArrowIcon />
            </button>
          ) : (
            <button 
              type="button" 
              onClick={onSubmit} 
              disabled={busy}
              className={NEXT_BUTTON_CLASSES}
            >
              {busy ? "Berechne..." : "Shortlist erstellen"}
              <RightArrowIcon />
            </button>
          )}
        </div>
      </div>
    </Card>
  );
}