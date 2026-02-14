"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createLead, downloadPdf } from "@/lib/api";

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
    <Card className="space-y-3">
      <h3 className="text-lg font-semibold">PDF Download freischalten</h3>
      <Input placeholder="E-Mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <Input placeholder="Firma (optional)" value={company} onChange={(e) => setCompany(e.target.value)} />
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        Ich stimme der Kontaktaufnahme zu.
      </label>
      <div className="flex gap-2">
        <Button onClick={onSubmit} disabled={busy}>{busy ? "Lädt..." : "Lead senden + PDF"}</Button>
        <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>Abbrechen</Button>
      </div>
    </Card>
  );
}
