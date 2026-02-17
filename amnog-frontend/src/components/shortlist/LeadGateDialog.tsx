"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmailGateCard } from "@/components/ui/email-gate-card";
import { createLead, downloadPdf } from "@/lib/api";

export function LeadGateDialog({ runId }: { runId: string }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [consentError, setConsentError] = useState(false);

  const onSubmit = async () => {
    // Reset error state
    setConsentError(false);
    
    if (!email) {
      toast.error("Bitte E-Mail ausfüllen.");
      return;
    }
    
    if (!consent) {
      setConsentError(true);
      toast.error("Bitte stimmen Sie der Datenschutzerklärung zu.");
      return;
    }
    
    setBusy(true);
    try {
      await createLead(runId, email, company || undefined);
      const blob = await downloadPdf(runId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `amnog-shortlist-${runId}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("PDF Download gestartet.");
      setOpen(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unbekannter Fehler");
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return <Button onClick={() => setOpen(true)}>PDF exportieren</Button>;
  }

  return (
    <EmailGateCard 
      title="Fast geschafft!"
      description="Bitte geben Sie Ihre E-Mail-Adresse ein, um fortzufahren."
    >
      <div className="space-y-3">
        <Input placeholder="E-Mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Input placeholder="Firma (optional)" value={company} onChange={(e) => setCompany(e.target.value)} />
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
        <div className="flex flex-col gap-2 pt-2">
          <Button 
            onClick={onSubmit} 
            disabled={busy || !consent}
            className="w-full rounded-[10px] py-3.5 bg-gold hover:bg-gold/90 text-slate-900 font-medium disabled:opacity-50"
          >
            {busy ? "Lädt..." : "Shortlist anzeigen"}
          </Button>
          <Button 
            variant="outline" 
            onClick={() => setOpen(false)} 
            disabled={busy}
            className="w-full rounded-[10px] py-3.5"
          >
            Abbrechen
          </Button>
        </div>
      </div>
    </EmailGateCard>
  );
}
