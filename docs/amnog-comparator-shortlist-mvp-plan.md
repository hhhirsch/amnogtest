# AMNOG Comparator Shortlist – Projektplan (MVP)

## 1) Ziel & MVP-Definition

### Ziel
Ein Nutzer hat ein Produkt + eine Studie und möchte für AMNOG schnell verstehen:
- Welche 5 Vergleichstherapie-Kandidaten (als G-BA-Formulierungen) plausibel sind.
- Warum diese Kandidaten plausibel sind (inkl. Belegstellen/Referenzen aus ähnlichen Beschlüssen).
- Wie sicher/unsicher das Ergebnis ist (Confidence, Ambiguity).

### MVP (Version 1)
- Filter ausschließlich über **Therapiegebiet** (analog G-BA-Liste).
- Input via kurzer Textbeschreibung (Population/AWG) + wenige Kontextfelder.
- Output: Top-5 Vergleichstherapie-Kandidaten (G-BA-Wording) + Referenzen (Beschlusslinks) + PDF-Export (Lead-gated).
- Explizite Positionierung als **„Shortlist plausibler Kandidaten“** (keine finale ZVT-Festlegung).

### Non-Goals (MVP)
- Keine vollständige Indikationsdatenbank / ICD-Navigation.
- Keine juristisch/HTA-verbindliche Entscheidung.
- Kein automatisches Pricing-/HEOR-Modell.

## 2) Datenbasis & Nutzung

Für den MVP zentrale Felder aus der Beschlussdatenbank:
- Produktname (z. B. `BE.ZUL.NAME_HN…`)
- AWG-Beschluss / Anwendungsgebietstext (`…AWG_BESCHLUSS…`)
- Patientengruppe/Population (`…NAME_PAT_GR…`)
- Vergleichstherapie(n) im Beschluss (`…ZVT_BEST.NAME_ZVT_BEST…`)
- Link zum Verfahren/Beschluss (`BE.URL…`)
- Aktenzeichen/Datum (`…ID_BE_AKZ…`, für Recency-Gewichtung)

Wichtig für den MVP-Filter:
- Pro Datensatz muss ein `therapiegebiet`-Tag vorliegen.
- Falls nicht vorhanden: im ETL-Prozess erzeugen (regelbasiert + manuelle QA/Overrides).

## 3) UX: User Journey & Screens

### 3.1 Entry Points (Lead-freundlich)
Landing Page:
- Value Prop: „In 2 Minuten: Top-5 plausible Vergleichstherapien aus ähnlichen G-BA-Beschlüssen.“
- CTA: „Comparator Shortlist erstellen“
- Trust + Disclaimer: „Basiert auf G-BA-Beschlüssen“, „kein Ersatz für formale Festlegung“

### 3.2 Hauptflow: Wizard (3 Schritte + Ergebnis)

#### Schritt 1 – Therapiegebiet & Projektkontext
Felder:
1. Therapiegebiet (Pflicht, Select)
   - Augenerkrankungen, Haut, Herz-Kreislauf, Infektionen, Atmung, Blut/Blutbildend,
     Muskel-Skelett, Nervensystem, Urogenital, Verdauung, Onkologie, Psychische,
     Stoffwechsel, Sonstiges
2. Projekt-/Produktname (optional, für Report/Export)
3. Ziel „Vergleichstherapie-Shortlist“ (read-only)

CTA: **Weiter**

#### Schritt 2 – Anwendungsgebiet & Population
Felder:
4. Anwendungsgebiet / Indikation (Freitext, Pflicht)
   - Placeholder: „Paste aus SmPC/Protokoll, 2–10 Sätze.“
5. Zielpopulation / Patientengruppe (Freitext, optional aber empfohlen)
   - Placeholder: „Einschlusskriterien, Linien, Vorbehandlung, Schweregrad.“

UX-Hinweis:
- „Je konkreter Population/Vorbehandlung/Setting, desto stabiler die Treffer.“

CTA: **Weiter**

#### Schritt 3 – Studien-/Kontextsignale
Felder:
6. Setting (Pflicht): ambulant / stationär / beides / unklar
7. Therapierolle (Pflicht): Replacement / Add-on / unklar
8. Therapielinie (optional): 1L / 2L / später / Switch / unklar
9. Studien-Comparator (optional): aktiv / placebo / BSC / physician’s choice / unklar
   - Optional Freitext: „Comparator im Kontrollarm…“

CTA: **Shortlist berechnen**

#### Ergebnis-Screen – „Top-5 Comparator Candidates“
Oben:
- Summary mit Therapiegebiet, Setting, Rolle, Linie
- Eingabetext einklappbar

Pro Kandidat (Card):
- Vergleichstherapie-Formulierung (G-BA-Wording)
- Confidence: hoch / mittel / niedrig
- Support: „in X ähnlichen Fällen (gewichtete Häufigkeit)“
- Top-Referenzen (3–5): Produkt/Verfahren, Datum, Link
- Snippet aus AWG/Patientengruppe als Ähnlichkeitsbegründung
- Expand: „Alle Referenzen anzeigen“

Zusatzbereiche:
- „Warum diese Kandidaten?“ (erklärbare Kurzbegründung)
- „Typische Risiken“ (Ambiguity-Hinweise)

Actions:
- PDF-Export (Lead-gated)
- Share Link (read-only)
- Optional: „Expert Review anfragen“

## 4) UX/UI Style & Design System

Prinzipien:
- Regulatory-seriös, kein gamifizierter Stil.
- Erklärbarkeit über Referenzen als Kernnutzen.
- Minimaler Cognitive Load mit Wizard + klaren Ergebnis-Cards.

Komponenten:
- 3-Step Stepper
- Searchable Select (Therapiegebiet)
- Textareas mit Character Counter und Beispielhilfe
- Result Cards + Referenz-Accordion
- Badges für Confidence und Support
- Skeleton Loader für Berechnung

Copy/Ton:
- Begriffe wie „plausibel“, „Kandidaten“, „ähnliche Beschlüsse“, „nicht verbindlich“
- Keine AI-Buzzwords in der Oberfläche

## 5) Fragenkatalog, Regeln & Validierung

Pflichtfelder:
- Therapiegebiet
- Anwendungsgebiet (Freitext)
- Setting
- Therapierolle

Optional:
- Therapielinie
- Studien-Comparator (+ Freitext)
- Zielpopulation

Validierungen:
- Anwendungsgebiet: Soft Warning unter 200 Zeichen, Maximum z. B. 6.000 Zeichen
- Bei „unklar“ für Setting/Rolle: Confidence-Downweight + Hinweistext

Assist-Logik:
- Bei sehr kurzen Eingaben: Hinweis auf Vorbehandlung/Schweregrad ergänzen
- Bei sehr langen Eingaben: Fokus-Hinweis auf Population/Comparator/Setting

## 6) Ergebnislogik (Matching, Extraktion, Ranking)

### 6.1 Vorverarbeitung (ETL)
- HTML → Plaintext (AWG, Patientengruppe)
- Normalisierung (Whitespace, Sonderzeichen, Listen)
- Datum aus Aktenzeichen extrahieren (Recency)
- Therapiegebiet-Tagging

### 6.2 Retrieval
Query = Anwendungsgebiet + optional Population + optional Comparator-Freitext

Filter:
- `therapy_area == user_selected`

MVP-Matching:
- Lexikalisches Retrieval (BM25 / Full-Text)
- Optional v1.1 Embedding-Retrieval
- Kombinierter Score:
  - `score = 0.7 * bm25 + 0.3 * cosine_embedding` (wenn Embeddings aktiv)

Kandidatenpool:
- Top-N ≈ 30 Patientengruppen-Datensätze

### 6.3 Kandidaten-Extraktion aus ZVT
- Cleanup + Normalisierung (`oder/und`, Bullets)
- Erkennung typischer Container:
  - „Patientenindividuelle Therapie …“
  - „Therapie nach ärztlicher Maßgabe …“
  - „Best supportive care / BSC“
  - „Beobachtendes Abwarten“
- Zweistufige Darstellung:
  - Primary: gesamte G-BA-Formulierung
  - Secondary: extrahierte Unteroptionen

Dedup:
- `normalized_key = lower(text) + collapse_whitespace + remove_trailing_footnotes`
- Synonym-Mapping minimal (`BSC == Best supportive care`)

### 6.4 Ranking Top-5
Für Kandidat `c`:
- `support(c) += retrieval_score(i) * recency_weight(i)` über alle Treffer `i`

Recency-Gewichtung (Beispiel):
- < 2 Jahre: 1.0
- 2–4 Jahre: 0.8
- > 4 Jahre: 0.6

Fit-Adjustments (regelbasiert, klein):
- Add-on + „in Kombination“ → leichter Boost
- Stationär + stationäre Hinweise im Text → leichter Boost

Top-5 = höchste `final_score`

### 6.5 Confidence & Ambiguity
Hohe Confidence bei:
- Starker Unterstützung aus mehreren ähnlichen Beschlüssen
- Klarer Score-Abstand zu niedrigeren Rängen
- Breiter Stützung aus verschiedenen Verfahren

Hohe Ambiguity bei:
- Viele Kandidaten mit ähnlichen Scores
- Thematisch heterogener Trefferpool

## 7) Frontend-Plan

Tech-Vorschlag:
- Next.js (React)
- React Hook Form + Zod
- Tailwind oder MUI + Design-Tokens
- Server-first State über API

Module:
1. Wizard (Step-Routing, Draft-Persistenz)
2. Results Page (Cards + Referenz-Accordion)
3. Export-Gate Modal (E-Mail/Consent)
4. Share-Link View (read-only)
5. Optional v1.1 Admin-UI (Tagging/Overrides/Synonyme)

Events:
- `select_therapy_area`
- `submit_query`
- `results_view`
- `export_click`
- `email_submitted`
- `expert_review_click`
- `share_link_created`

## 8) Backend-Plan

MVP-Service (monolithisch ausreichend):
- API Service (FastAPI oder Node/NestJS)
- Retrieval/Search Layer
- ETL/Indexer Job

Endpoints:
- `POST /api/shortlist`
- `POST /api/export/pdf`
- `POST /api/leads`
- `GET /api/run/{id}`

Performance:
- Antwortzeit in wenigen Sekunden
- Optional Caching für identische Inputs

## 9) Datenbankanbindung (ETL + Schema)

### 9.1 Persistenz
- PostgreSQL als SoT
- Optional `pgvector`
- Optional Postgres Full-Text oder OpenSearch/Elastic

### 9.2 Tabellen (vereinfacht)
- `decisions`
- `patient_groups`
- `runs`
- `run_results`
- `leads`

(Feldbelegung analog Planvorgabe.)

### 9.3 ETL-Pipeline
1. Excel einlesen
2. HTML bereinigen
3. Datum aus Aktenzeichen parsen
4. Upsert in `decisions` und `patient_groups`
5. Therapiegebiet-Tagging
6. Suchindex aktualisieren (Full-Text, optional Embeddings)

### 9.4 Therapiegebiet-Tagging
- MVP: regel-/keyword-basiert auf AWG + Patientengruppentext
- Fallback: `Sonstiges`
- Optional: Admin-Override zur Qualitätssteigerung

## 10) Export (PDF) & Lead Capture

PDF (1 Seite MVP):
- Header: Produktname (optional), Therapiegebiet, Datum
- Input-Summary
- Top-5 Kandidaten (Support + Confidence)
- Top-Referenzen
- Disclaimer

Gating:
- Klick auf Export → Modal (E-Mail, optional Company, Consent)
- Download nach erfolgreicher Lead-Erfassung

## 11) Qualität, Tests, Monitoring

Tests:
- Unit Tests (Parsing, Normalisierung, Tagging)
- Golden Set (30–50 kuratierte Fälle)
- Regression Tests nach ETL-/Datenupdates
- E2E: Wizard → Results → Export

Monitoring:
- Query-Latenz
- Retrieval-Hit-Rate
- Empty-Results-Rate
- Conversion (Export-Rate, Expert-Review-CTR)

## 12) Backlog-Phasen

### Phase 0 – Foundations
- Excel-Ingestion nach Postgres
- Text Cleaning
- Basis-Schema + Admin-Skripte
- Therapy Area Tagging v0 + QA

### Phase 1 – Search & Ranking MVP
- Full-Text Retrieval + Top-N
- ZVT Parsing/Normalization v0
- Candidate Ranking + Confidence
- API `POST /shortlist`

### Phase 2 – Frontend Wizard & Results
- Wizard + Validierung
- Results Cards + Referenz-Accordion
- Share-Link View

### Phase 3 – Export & Leads
- Lead Capture Modal + Persistenz
- PDF-Generierung
- Analytics Events

### Phase 4 – Hardening
- Golden Set + Regression
- Admin Override UI
- Optional Embedding-Retrieval

## 13) Akzeptanzkriterien (Definition of Done)

MVP ist erreicht, wenn:
1. Nutzer über Therapiegebiet + Texteingabe in wenigen Sekunden Top-5 erhält.
2. Jeder Kandidat mit 3+ Referenzen ausgegeben wird (wenn Datenlage vorhanden).
3. PDF-Export gated funktioniert und Lead gespeichert wird.
4. UI klar kommuniziert: plausible Shortlist ≠ finale ZVT-Festlegung.
