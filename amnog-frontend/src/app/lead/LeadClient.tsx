"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createLead, API_BASE } from "@/lib/api";

export default function LeadClient() {
  const params = useParams<{ runId: string }>();
  const runId = params?.runId;
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [busy, setBusy] = useState(false);
  const [downloadStarted, setDownloadStarted] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!runId) {
      toast.error("Run-ID fehlt.");
      return;
    }

    setBusy(true);
    try {
      await createLead(runId, email.trim(), company.trim() || undefined);
      window.location.href = `${API_BASE}/api/export/pdf?run_id=${encodeURIComponent(runId)}`;
      setDownloadStarted(true);
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : "Lead konnte nicht gespeichert werden.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="mx-auto max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">PDF herunterladen</h1>
      <p className="text-sm text-slate-600">
        Bitte hinterlegen Sie Ihre E-Mail-Adresse, damit wir Ihnen die Shortlist als PDF bereitstellen können.
      </p>

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
        <Button type="submit" disabled={busy}>
          {busy ? "Speichere..." : "E-Mail speichern & PDF herunterladen"}
        </Button>
      </form>

      {runId && (
        <p className="text-sm text-slate-600">
          {downloadStarted ? "Download gestartet. " : "Optional: "}
          <Link className="underline" href={`/run/${runId}`}>
            Zur Ergebnis-Seite
          </Link>
        </p>
      )}
    </Card>
  );
}
