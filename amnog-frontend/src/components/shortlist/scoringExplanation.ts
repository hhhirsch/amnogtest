export const SCORING_EXPLANATION_TITLE = "Wie die Shortlist entsteht (MVP)";

export const SCORING_EXPLANATION_BULLETS = [
  "Wir filtern zuerst auf das ausgewählte Therapiegebiet.",
  "Dann suchen wir in bestehenden G-BA-Beschlüssen nach Textstellen, die zu Indikation/Population/Comparator passen.",
  "Ähnliche Beschlüsse zählen stärker, sehr alte Beschlüsse etwas weniger.",
  "Ähnliche ZVT-Formulierungen werden zusammengefasst, damit keine Dubletten entstehen.",
  "Support ist die Evidenzstärke: je höher, desto mehr (und/oder passendere) Beschlüsse stützen den Kandidaten.",
  "Fälle ist die Anzahl unterschiedlicher Beschlüsse, die den Kandidaten stützen.",
  "Confidence (hoch/mittel/niedrig) leitet sich aus Support + Fällen ab.",
  "Ambiguity beschreibt, wie eng die Scores der Top-Kandidaten zusammenliegen (hoch = mehrere ähnlich plausible Optionen).",
] as const;

export const SCORING_GLOSSARY = [
  "Support = Evidenzstärke (Ähnlichkeit × Aktualität × Fit; Summe über eindeutige G-BA-Entscheidungen)",
  "Fälle = Anzahl unterschiedlicher Entscheidungen (decision_id), die den Kandidaten stützen",
  "Confidence = Label aus Support + Fällen",
  "Ambiguity = wie nah die Kandidaten-Scores beieinander liegen",
] as const;

export const SCORING_RELATIVE_NOTE =
  "Support ist ein relativer Score innerhalb der Anfrage. Er ist keine klinische Empfehlung, sondern eine datenbasierte Näherung aus vorhandenen Beschlüssen.";
