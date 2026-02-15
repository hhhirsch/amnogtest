"use client";

import { FormEvent, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
    <Card className="mx-auto max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">E-Mail speichern</h1>
      <p className="text-sm text-slate-600">
        Hinterlegen Sie Ihre E-Mail-Adresse, um die Ergebnisse aufzurufen und optional als PDF zu exportieren.
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
        <Button type="submit" disabled={busy || !emailIsValid}>
          {busy ? "Speichere..." : "E-Mail speichern"}
        </Button>
      </form>
    </Card>
  );
}
