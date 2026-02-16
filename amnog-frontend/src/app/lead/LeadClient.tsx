"use client";

import { FormEvent, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createLead } from "@/lib/api";
import { Mail } from "lucide-react";

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
      <div className="bg-surface border border-white/[0.13] rounded-[20px] p-8 shadow-[0_24px_64px_rgba(0,0,0,0.5)] relative overflow-hidden max-w-xl w-full">
        {/* Gold top-line gradient */}
        <div className="absolute h-0.5 inset-x-0 top-0 bg-gradient-to-r from-transparent via-gold to-transparent opacity-60" />
        
        {/* Icon box */}
        <div className="w-12 h-12 rounded-xl bg-gold/10 border border-gold/25 flex items-center justify-center mb-4">
          <Mail className="w-6 h-6 text-gold" />
        </div>
        
        {/* Title */}
        <h1 className="font-serif text-[28px] text-ink leading-snug mb-2">Fast geschafft!</h1>
        
        {/* Description */}
        <p className="text-sm text-ink-soft font-light leading-relaxed mb-6">
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
          <Button 
            type="submit" 
            disabled={busy || !emailIsValid}
            className="w-full rounded-[10px] py-3.5 bg-gold hover:bg-gold/90 text-slate-900 font-medium"
          >
            {busy ? "Speichere..." : "Shortlist anzeigen"}
          </Button>
        </form>
      </div>
    </section>
  );
}
