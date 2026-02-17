export const SCORING_EXPLANATION_TITLE = "Wie die Shortlist entsteht";

export const SCORING_EXPLANATION_BULLETS = [
  "Wir starten im gewählten Therapiegebiet (bei sehr wenigen Treffern ergänzen wir andere Gebiete mit Abschlag).",
  "Wir matchen Indikation, Population und Comparator gegen Textstellen aus G-BA-Beschlüssen (gewichtete Textähnlichkeit: AWG > Population > zVT/Comparator).",
  "Neuere Beschlüsse zählen etwas stärker als sehr alte (Recency-Gewichtung).",
  "Ähnliche zVT-Formulierungen werden zusammengefasst; pro Entscheidung zählt jeweils der beste Treffer.",
  "Support = Evidenzstärke (mehr und/oder passendere Entscheidungen → höher; kleiner Bonus für Breite).",
  "Fälle = Anzahl unterschiedlicher Entscheidungen (decision_id), die den Kandidaten stützen.",
  "Confidence ist relativ innerhalb der Anfrage aus Support (vs. Top-Kandidat) + Fällen abgeleitet.",
  "Ambiguity zeigt, wie nah die Top-Kandidaten beieinander liegen.",
  "Hinweis: Support ist keine klinische Empfehlung, sondern eine datenbasierte Näherung aus vorhandenen Beschlüssen.",
] as const;

export const SCORING_GLOSSARY = [
  "Support: Evidenzstärke über eindeutige Entscheidungen (inkl. Aktualität & Breite)",
  "Fälle: Anzahl stützender Entscheidungen",
  "Confidence: relatives Label aus Support + Fällen",
  "Ambiguity: Nähe der Kandidaten-Scores",
] as const;

export const SCORING_RELATIVE_NOTE = "";
