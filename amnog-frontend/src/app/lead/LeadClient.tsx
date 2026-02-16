"use client";

import { FormEvent, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmailGateCard } from "@/components/ui/email-gate-card";
import { createLead } from "@/lib/api";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LeadClient() {
  const router = useRouter();
  const params = useParams<{ runId: string }>();
  const runId = params?.runId;
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [busy, setBusy] = useState(false);

  const emailIsValid = useMemo(() => EMAIL_REGEX.test(email.trim()), [email]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!runId) {
      toast.error("Run-ID fehlt.");
      return;
    }

    if (!emailIsValid) {
      toast.error("Bitte eine gültige E-Mail-Adresse eingeben.");
      return;
    }

    setBusy(true);
    try {
      const normalizedEmail = email.trim();
      const normalizedCompany = company.trim() || undefined;

      await createLead(runId, normalizedEmail, normalizedCompany);
      await fetch("/api/notify-lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ runId, email: normalizedEmail, company: normalizedCompany }),
      });

      localStorage.setItem(`lead_submitted:${runId}`, "true");
      toast.success("Vielen Dank! Ihre Angaben wurden gespeichert.");
      router.push(`/run/${runId}`);
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : "Lead konnte nicht gespeichert werden.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="flex items-center justify-center min-h-[80vh]">
      <EmailGateCard
        title="Fast geschafft!"
        description="Hinterlegen Sie Ihre E-Mail-Adresse, um die Ergebnisse aufzurufen und optional als PDF zu exportieren."
        className="max-w-xl w-full"
      >
        <form className="space-y-3" onSubmit={onSubmit}>
          <Input
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="name@firma.de"
          />
          <Input
            value={company}
            onChange={(event) => setCompany(event.target.value)}
            placeholder="Firma (optional)"
          />
          <Button 
            type="submit" 
            disabled={busy || !emailIsValid}
            className="w-full rounded-[10px] py-3.5 bg-gold hover:bg-gold/90 text-slate-900 font-medium"
          >
            {busy ? "Speichere..." : "Shortlist anzeigen"}
          </Button>
        </form>
      </EmailGateCard>

      {runId && (
        <div className="mx-auto max-w-xl border border-dashed border-white/[0.13] rounded-[10px] px-4 py-3 flex items-center gap-2.5 mt-6 mb-12">
          <span className="text-[9px] font-semibold tracking-[0.1em] uppercase text-ink-muted flex-shrink-0">
            Run ID
          </span>
          <span className="text-[10px] text-ink-muted font-mono overflow-hidden text-ellipsis whitespace-nowrap">
            {runId}
          </span>
        </div>
      )}
    </section>
  );
}
