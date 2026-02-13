# AMNOG Comparator Shortlist MVP

Implementierung des MVP aus dem Projektplan:

- Therapiegebiet-Filter als Pflichtsignal
- Top-5 plausible Vergleichstherapie-Kandidaten aus ähnlichen Beschlussfällen
- Referenzen mit Belegstellen (Beschluss-Link, Datum, Snippet)
- Confidence-/Ambiguity-Labels
- Speicherung von Runs und Lead-Capture
- Gated PDF-Export

## Schnellstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

OpenAPI: `http://127.0.0.1:8000/docs`

## Beispiel-Request

```bash
curl -X POST http://127.0.0.1:8000/api/shortlist \
  -H 'Content-Type: application/json' \
  -d '{
    "therapy_area": "Onkologie",
    "indication_text": "Erwachsene mit metastasiertem NSCLC nach Progress unter Erstlinientherapie und hoher Tumorlast.",
    "population_text": "ECOG 0-1, vorbehandelt in 2L.",
    "setting": "ambulant",
    "role": "add-on",
    "line": "2L",
    "comparator_type": "aktiv"
  }'
```
