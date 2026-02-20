"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PrivacyPolicyModal } from "@/components/ui/privacy-policy";
import { createLead, getRun } from "@/lib/api";
import { NewRequestButton } from "@/components/shortlist/NewRequestButton";
import { CandidateCard } from "@/components/shortlist/CandidateCard";
import type { ShortlistResponse } from "@/lib/types";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const FALLBACK_REASON_FILTER = "bewertung basiert";

const checkIsNoResult = (data: Pick<ShortlistResponse, "plausibility" | "status" | "candidates">) =>
  data.plausibility === "niedrig" ||
  data.status === "no_result" ||
  !data.candidates?.length;

// Map ambiguity values to Eindeutigkeit (inverted)
const mapAmbiguityToEindeutigkeit = (
  ambiguity: "hoch" | "mittel" | "niedrig"
): "hoch" | "mittel" | "niedrig" => {
  const mapping: Record<"hoch" | "mittel" | "niedrig", "hoch" | "mittel" | "niedrig"> = {
    niedrig: "hoch",
    mittel: "mittel",
    hoch: "niedrig",
  };
  return mapping[ambiguity] ?? "mittel";
};

const getReliabilityBadge = (rel: "hoch" | "mittel" | "niedrig") => {
  const mapping = {
    hoch: {
      text: "✅ Belastbar",
      bgColor: "bg-green-500/10",
      textColor: "text-green-400",
      borderColor: "border-green-500/30",
    },
    mittel: {
      text: "🟡 Mit Einschränkungen",
      bgColor: "bg-yellow-500/10",
      textColor: "text-yellow-400",
      borderColor: "border-yellow-500/30",
    },
    niedrig: {
      text: "🔴 Nicht belastbar",
      bgColor: "bg-red-500/10",
      textColor: "text-red-400",
      borderColor: "border-red-500/30",
    },
  };
  return mapping[rel];
};

export default function LeadClient() {
  const router = useRouter();
  const params = useParams<{ runId: string }>();
  const runId = params?.runId;

  const [data, setData] = useState<ShortlistResponse | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [consentError, setConsentError] = useState(false);

  const emailIsValid = useMemo(() => EMAIL_REGEX.test(email.trim()), [email]);

  useEffect(() => {
    if (!runId) {
      setFetchError("Run-ID fehlt.");
      setLoading(false);
      return;
    }

    let mounted = true;
    getRun(runId)
      .then((res) => {
        if (!mounted) return;
        const payload = res.response_payload;
        const isWeak = checkIsNoResult(payload);
        if (isWeak) {
          // No gate for weak/no-result — redirect directly to /run
          localStorage.setItem(`lead_submitted:${runId}`, "true");
          router.replace(`/run/${runId}`);
          return;
        }
        setData(payload);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        setFetchError(err instanceof Error ? err.message : "Daten konnten nicht geladen werden.");
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [router, runId]);

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

  if (loading) {
    return <div className="p-6 text-slate-400">Lade Ergebnisse...</div>;
  }

  if (fetchError || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-4 text-center">
        <p className="text-slate-400">{fetchError ?? "Ergebnisse nicht gefunden."}</p>
        <NewRequestButton />
      </div>
    );
  }

  const reliability = data.reliability ?? data.plausibility ?? "mittel";
  const reliabilityBadge = getReliabilityBadge(reliability);
  const status = data.status || (data.candidates.length === 0 ? "no_result" : "ok");

  const rawReasons = (data.reliability_reasons ?? data.plausibility_reasons ?? []).filter(
    (r) => !r.toLowerCase().includes(FALLBACK_REASON_FILTER)
  );

  const topCandidate = data.candidates[0] ?? null;
  const blurredCandidates = data.candidates.slice(1, 5);

  const isNoResult = checkIsNoResult(data);

  return (
    <section className="space-y-6 pb-16">
      {/* Header — same branding as results page */}
      <header
        className="bg-bg pt-14 pb-9 px-5 relative overflow-hidden before:content-[attr(data-watermark)] before:font-serif before:text-[130px] before:text-white/[0.025] before:absolute before:top-0 before:right-0 before:pointer-events-none"
        data-watermark="SHORTLIST"
      >
        <div className="relative z-10 space-y-3">
          <p className="text-gold text-[10px] font-medium tracking-[0.18em] uppercase flex items-center gap-2">
            <span className="inline-block w-4 h-px bg-gold"></span>
            COMPARATOR-SHORTLIST
            <span className="inline-block w-4 h-px bg-gold"></span>
          </p>
          <h1 className="font-serif text-[42px] leading-tight text-white">
            Ergebnis<span className="italic text-white/40">liste</span>
          </h1>
          <p className="text-ink-soft text-sm font-light leading-relaxed max-w-sm">
            {isNoResult
              ? "Basierend auf Ihrer Eingabe konnten wir nur eingeschränkt Comparator-Kandidaten identifizieren."
              : "Basierend auf Ihrer Eingabe haben wir passende Comparator-Kandidaten identifiziert."}
          </p>
        </div>
      </header>

      {/* (A) Reliability Card */}
      <div
        className={`rounded-xl border ${reliabilityBadge.borderColor} ${reliabilityBadge.bgColor} px-4 py-4 space-y-3`}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-white">
            Ergebnis-Verlässlichkeit
          </h3>
          <span
            className={`text-xs font-semibold px-3 py-1 rounded-full ${reliabilityBadge.bgColor} ${reliabilityBadge.textColor} border ${reliabilityBadge.borderColor}`}
          >
            {reliabilityBadge.text}
          </span>
        </div>
        {reliability === "hoch" && (
          <p className="text-sm text-ink-soft leading-relaxed">
            Die Top-Option ist durch mehrere vergleichbare G-BA-Entscheidungen gut gestützt.
          </p>
        )}
        {reliability === "mittel" && rawReasons.length > 0 && (
          <p className="text-sm text-ink-soft leading-relaxed">
            Die Ergebnisse sind grundsätzlich gestützt, aber folgende Punkte schränken die
            Verlässlichkeit ein:
          </p>
        )}
        {rawReasons.length > 0 && (
          <ul className="space-y-2">
            {rawReasons.slice(0, 3).map((reason, i) => (
              <li key={i} className="text-sm text-ink-soft leading-relaxed flex items-start gap-2">
                <span className="text-gold mt-0.5">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        )}
        {reliability === "mittel" && rawReasons.length === 0 && (
          <p className="text-sm text-ink-soft leading-relaxed">
            Bewertung basiert auf verfügbaren G-BA-Entscheidungen.
          </p>
        )}
      </div>

      {/* (B) Data Basis Card */}
      <div className="rounded-xl border border-white/[0.13] bg-surface px-4 py-4 space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-white">Datenbasis</h3>
        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-1">
            <span className="block font-serif text-[24px] leading-none text-gold">
              {data.candidates[0]?.support_cases ?? 0}
            </span>
            <span className="block text-[10px] font-medium uppercase tracking-wider text-ink-muted">
              Fälle
            </span>
          </div>
          <div className="space-y-1">
            <span className="block font-serif text-[24px] leading-none text-gold">
              {data.candidates.length >= 2 && status !== "no_result"
                ? mapAmbiguityToEindeutigkeit(data.ambiguity)
                : "—"}
            </span>
            <span className="block text-[10px] font-medium uppercase tracking-wider text-ink-muted">
              Trennschärfe
            </span>
          </div>
          <div className="space-y-1">
            <span className="block font-serif text-[24px] leading-none text-gold">
              {data.candidates[0]?.confidence ?? "—"}
            </span>
            <span className="block text-[10px] font-medium uppercase tracking-wider text-ink-muted">
              Modellsicherheit
            </span>
          </div>
        </div>
      </div>

      {/* (C) Top Candidate + Lead Capture — tight vertical rhythm */}
      {isNoResult ? (
        /* No-result guidance card */
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-6 py-8 space-y-5">
          <div className="space-y-2">
            <h2 className="text-base font-semibold text-white">
              🔴 Kein belastbares Ergebnis gefunden
            </h2>
            <p className="text-sm text-ink-soft leading-relaxed">
              Bitte Anfrage nachschärfen und erneut generieren.
            </p>
          </div>
          <ul className="space-y-2">
            {[
              "Indikation präzisieren (z.B. Unterpopulation / Line of Therapy)",
              "Zielpopulation genauer definieren (z.B. vorbehandelt / refraktär)",
              "Comparator-Setting (BSC vs aktive Therapie) prüfen",
            ].map((tip) => (
              <li key={tip} className="flex items-start gap-2 text-sm text-ink-soft">
                <span className="text-gold mt-0.5">•</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
          <NewRequestButton />
        </div>
      ) : (
        <div className="space-y-3">
          {/* Top Candidate — fully visible, no details */}
          {topCandidate && (
            <div>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                Top-Kandidat
              </h2>
              <CandidateCard candidate={topCandidate} hideDetails />
            </div>
          )}

          {/* (D+E) Blurred list + overlay lead capture form */}
          {blurredCandidates.length > 0 && (
            <div className="relative">
              {/* Blurred candidates */}
              <div
                aria-hidden="true"
                style={{
                  filter: "blur(8px)",
                  opacity: 0.4,
                  pointerEvents: "none",
                  userSelect: "none",
                }}
              >
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Weitere Kandidaten
                </h2>
                {blurredCandidates.map((candidate) => (
                  <CandidateCard
                    key={`${candidate.rank}-${candidate.candidate_text}`}
                    candidate={candidate}
                    hideDetails
                  />
                ))}
              </div>

              {/* (E) Overlay Lead Capture Form */}
              <div className="absolute inset-0 flex items-center justify-center px-4 py-8 bg-bg/60 backdrop-blur-sm rounded-xl">
                <div className="w-full max-w-sm bg-surface border border-white/[0.13] rounded-[20px] p-6 shadow-[0_24px_64px_rgba(0,0,0,0.6)] relative overflow-hidden">
                  {/* Gold top-line */}
                  <div className="absolute h-0.5 inset-x-0 top-0 bg-gradient-to-r from-transparent via-gold to-transparent opacity-60" />

                  <h2 className="font-serif text-[22px] text-ink leading-snug mb-3">
                    Vollständige Shortlist freischalten
                  </h2>

                  <ul className="space-y-1.5 mb-4">
                    {["Kandidaten 2–5", "G-BA Belege pro Kandidat", "PDF-Export"].map((item) => (
                      <li key={item} className="flex items-center gap-2 text-sm text-ink-soft">
                        <span className="text-gold">✓</span>
                        {item}
                      </li>
                    ))}
                  </ul>

                  <form className="space-y-3" onSubmit={onSubmit}>
                    <Input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@firma.de"
                    />
                    <Input
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
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
                          Ich habe die Datenschutzerklärung gelesen und bin einverstanden.
                        </span>
                      </label>
                      {consentError && (
                        <p className="text-xs text-red-400 mt-1.5 ml-6">
                          Bitte stimmen Sie der Datenschutzerklärung zu.
                        </p>
                      )}
                      <p className="text-xs text-slate-400 opacity-70 mt-2 ml-6 leading-relaxed">
                        E-Mail nur zur Zustellung. Kein Newsletter ohne Zustimmung. Details in der{" "}
                        <PrivacyPolicyModal />.
                      </p>
                    </div>

                    <Button
                      type="submit"
                      disabled={busy || !emailIsValid || !consent}
                      className="w-full rounded-[10px] py-3.5 bg-gold hover:bg-gold/90 text-slate-900 font-medium"
                    >
                      {busy ? "Speichere..." : "Shortlist freischalten"}
                    </Button>
                  </form>
                </div>
              </div>
            </div>
          )}

          {/* Fallback when no blurred candidates (e.g. only 1 result) — show form inline */}
          {blurredCandidates.length === 0 && (
            <div className="rounded-[20px] border border-white/[0.13] bg-surface p-6 relative overflow-hidden shadow-[0_24px_64px_rgba(0,0,0,0.5)]">
              <div className="absolute h-0.5 inset-x-0 top-0 bg-gradient-to-r from-transparent via-gold to-transparent opacity-60" />
              <h2 className="font-serif text-[22px] text-ink leading-snug mb-3">
                Vollständige Shortlist freischalten
              </h2>
              <ul className="space-y-1.5 mb-4">
                {["G-BA Belege zum Kandidaten", "PDF-Export"].map((item) => (
                  <li key={item} className="flex items-center gap-2 text-sm text-ink-soft">
                    <span className="text-gold">✓</span>
                    {item}
                  </li>
                ))}
              </ul>
              <form className="space-y-3" onSubmit={onSubmit}>
                <Input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@firma.de"
                />
                <Input
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
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
                    <span>Ich habe die Datenschutzerklärung gelesen und bin einverstanden.</span>
                  </label>
                  {consentError && (
                    <p className="text-xs text-red-400 mt-1.5 ml-6">
                      Bitte stimmen Sie der Datenschutzerklärung zu.
                    </p>
                  )}
                  <p className="text-xs text-slate-400 opacity-70 mt-2 ml-6 leading-relaxed">
                    E-Mail nur zur Zustellung. Kein Newsletter ohne Zustimmung. Details in der{" "}
                    <PrivacyPolicyModal />.
                  </p>
                </div>
                <Button
                  type="submit"
                  disabled={busy || !emailIsValid || !consent}
                  className="w-full rounded-[10px] py-3.5 bg-gold hover:bg-gold/90 text-slate-900 font-medium"
                >
                  {busy ? "Speichere..." : "Shortlist freischalten"}
                </Button>
              </form>
            </div>
          )}
        </div>
      )}

      {/* New request link */}
      <div className="flex justify-center">
        <NewRequestButton variant="ghost" />
      </div>
    </section>
  );
}
