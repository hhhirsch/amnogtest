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
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [consentError, setConsentError] = useState(false);

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

    if (!consent) {
      setConsentError(true);
      toast.error("Bitte stimmen Sie der Datenschutzerklärung zu.");
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
    <section className="flex items-center justify-center min-h-[80vh] px-4">
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
          
          <div>
            <label className="flex items-start gap-2 text-sm text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => {
                  setConsent(e.target.checked);
                  setConsentError(false);
                }}
                className="mt-0.5 cursor-pointer accent-gold"
              />
              <span>
                Ich habe die Datenschutzerklärung gelesen und bin mit der Verarbeitung meiner Angaben 
                zur Kontaktaufnahme einverstanden.
              </span>
            </label>
            {consentError && (
              <p className="text-xs text-red-400 mt-1.5 ml-6">
                Bitte stimmen Sie der Datenschutzerklärung zu.
              </p>
            )}
            <p className="text-xs text-slate-400 opacity-70 mt-2 ml-6 leading-relaxed">
              Ich verarbeite deine E-Mail-Adresse (Pflichtangabe) und optional den Firmennamen zur Bearbeitung 
              deiner Anfrage und zur Kontaktaufnahme. Details findest du in der Datenschutzerklärung.
            </p>
          </div>

          <Button 
            type="submit" 
            disabled={busy || !emailIsValid || !consent}
            className="w-full rounded-[10px] py-3.5 bg-gold hover:bg-gold/90 text-slate-900 font-medium"
          >
            {busy ? "Speichere..." : "Shortlist anzeigen"}
          </Button>
        </form>
      </EmailGateCard>
    </section>
  );
}
