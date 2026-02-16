"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createLead, downloadPdf } from "@/lib/api";
import { Mail } from "lucide-react";

export function LeadGateDialog({ runId }: { runId: string }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);

  const onSubmit = async () => {
    if (!email || !consent) {
      toast.error("Bitte E-Mail und Consent ausfüllen.");
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
    <div className="bg-surface border border-white/[0.13] rounded-[20px] p-8 shadow-[0_24px_64px_rgba(0,0,0,0.5)] relative overflow-hidden">
      {/* Gold top-line gradient */}
      <div className="absolute h-0.5 inset-x-0 top-0 bg-gradient-to-r from-transparent via-gold to-transparent opacity-60" />
      
      {/* Icon box */}
      <div className="w-12 h-12 rounded-xl bg-gold/10 border border-gold/25 flex items-center justify-center mb-4">
        <Mail className="w-6 h-6 text-gold" />
      </div>
      
      {/* Title */}
      <h3 className="font-serif text-[28px] text-ink leading-snug mb-2">Fast geschafft!</h3>
      
      {/* Description */}
      <p className="text-sm text-ink-soft font-light leading-relaxed mb-6">
        Bitte geben Sie Ihre E-Mail-Adresse ein, um fortzufahren.
      </p>
      
      <div className="space-y-3">
        <Input placeholder="E-Mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Input placeholder="Firma (optional)" value={company} onChange={(e) => setCompany(e.target.value)} />
        <label className="flex items-center gap-2 text-sm text-ink-soft">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          Ich stimme der Kontaktaufnahme zu.
        </label>
        <div className="flex flex-col gap-2 pt-2">
          <Button 
            onClick={onSubmit} 
            disabled={busy}
            className="w-full rounded-[10px] py-3.5 bg-gold hover:bg-gold/90 text-slate-900 font-medium"
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
    </div>
  );
}
