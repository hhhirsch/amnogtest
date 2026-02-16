"use client";

import { useState } from "react";
import { X } from "lucide-react";

export function PrivacyPolicyModal() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="text-gold hover:underline text-sm"
        type="button"
      >
        Datenschutzerklärung
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-slate-900 border border-white/[0.13] rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="sticky top-0 bg-slate-900 border-b border-white/[0.13] px-6 py-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-white">Datenschutzerklärung (Kurzfassung)</h2>
              <button
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-white transition-colors"
                type="button"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="px-6 py-4 space-y-4 text-sm text-slate-300">
              <section>
                <h3 className="font-semibold text-white mb-2">Verantwortlicher</h3>
                <p>Hans Hirsch</p>
                <p>E-Mail: hirsch.hans92@gmail.com</p>
              </section>

              <section>
                <h3 className="font-semibold text-white mb-2">Welche Daten verarbeite ich?</h3>
                <p>
                  Bei Nutzung des Kontaktformulars verarbeite ich deine E-Mail-Adresse (Pflichtangabe) sowie den 
                  Firmennamen (freiwillige Angabe), um deine Anfrage zu bearbeiten und dich zu kontaktieren.
                </p>
              </section>

              <section>
                <h3 className="font-semibold text-white mb-2">Zweck der Verarbeitung</h3>
                <p>Kontaktaufnahme und Bearbeitung deiner Anfrage.</p>
              </section>

              <section>
                <h3 className="font-semibold text-white mb-2">Rechtsgrundlage</h3>
                <p>
                  Art. 6 Abs. 1 lit. b DSGVO (Bearbeitung der Anfrage) und ggf. Art. 6 Abs. 1 lit. f DSGVO 
                  (berechtigtes Interesse an effizienter Kommunikation).
                </p>
              </section>

              <section>
                <h3 className="font-semibold text-white mb-2">Speicherdauer</h3>
                <p>
                  Ich lösche Anfragen, sobald sie erledigt sind, spätestens nach 90 Tagen, sofern keine 
                  gesetzlichen Aufbewahrungspflichten entgegenstehen.
                </p>
              </section>

              <section>
                <h3 className="font-semibold text-white mb-2">Hosting (Vercel)</h3>
                <p>
                  Diese Website wird über Vercel gehostet. Dabei können zur Bereitstellung und Sicherheit 
                  Server-Logdaten verarbeitet werden (z. B. IP-Adresse, Zeitstempel, aufgerufene Seite).
                </p>
              </section>

              <section>
                <h3 className="font-semibold text-white mb-2">Vercel Analytics</h3>
                <p>
                  Ich nutze Vercel Analytics, um die Nutzung der Website in aggregierter Form auszuwerten 
                  und die Website zu verbessern.
                </p>
              </section>

              <section>
                <h3 className="font-semibold text-white mb-2">Deine Rechte</h3>
                <p>
                  Du hast im Rahmen der gesetzlichen Voraussetzungen Rechte auf Auskunft, Berichtigung, 
                  Löschung, Einschränkung der Verarbeitung, Widerspruch sowie Datenübertragbarkeit. 
                  Außerdem kannst du dich bei einer Datenschutzaufsichtsbehörde beschweren.
                </p>
              </section>

              <section>
                <h3 className="font-semibold text-white mb-2">Kontakt</h3>
                <p>Datenschutzanfragen an: hirsch.hans92@gmail.com</p>
              </section>
            </div>

            <div className="sticky bottom-0 bg-slate-900 border-t border-white/[0.13] px-6 py-4">
              <button
                onClick={() => setIsOpen(false)}
                className="w-full rounded-lg bg-gold text-gold-dark font-medium px-4 py-2 hover:bg-gold-hover transition-colors"
                type="button"
              >
                Schließen
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
