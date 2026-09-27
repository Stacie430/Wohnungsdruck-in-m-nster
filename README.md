# Eignungsanalyse „Wohnungsdruck & Verdichtungspotenzial Münster“

Datenpipeline und Dashboard-Prototyp zur Frage, wo Münster junge Zuwanderer verliert und wo datenbasiert neuer studentischer Wohnraum entstehen könnte.

## Projektinhalt

Die Pipeline verarbeitet vier lokale Open-Data-Eingaben und erzeugt:

- eine Zeitreihen-Payload zum Wanderungsdruck je Stadtbezirk
- ein 250-m-Raster mit Nachfrage-, Campusnähe- und Grünschutz-Indikatoren
- JSON/GeoJSON-Payloads für ein interaktives Leaflet-Dashboard

## Relevante Dateien

| Datei | Zweck |
|---|---|
| `build_analysis.py` | Lädt Rohdaten, aggregiert Wanderungssalden, baut das Raster, berechnet Scores und exportiert die Analyse-Outputs. |
| `inject_payloads.py` | Fügt die erzeugten JSON/GeoJSON-Dateien in `dashboard_template.html` ein und schreibt eine eigenständige HTML-Datei. |
| `methodik_verdichtungspotenzial.md` | Methodik, Formeln, Gewichtungslogik, Limitationen und Quellenhinweise zur Analyse. |

## Voraussetzungen

- Python **3.10+** (empfohlen: 3.10 oder 3.11)
- Lokale Projektdateien im gleichen Verzeichnis wie die Skripte
- Webbrowser mit aktiviertem JavaScript

## Setup (reproduzierbar)

### 1) Virtuelle Umgebung erstellen

**macOS/Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Abhängigkeiten installieren

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` enthält die Laufzeitabhängigkeiten, die in den Python-Skripten verwendet werden.

## Erforderliche Eingabedateien

Vor dem Start müssen diese Dateien im Projektverzeichnis liegen:

- `05515000_csv_altersgruppenwanderungen_saldiert.csv`
- `stadtbezirk_und_teilbereich.geojson`
- `gruen_opendata.csv`
- `umweltzone_opendata.csv`

## Pipeline ausführen

```bash
python build_analysis.py
```

Erwartete Ausgabedateien:

- `pivot_20_39.csv`
- `grid_scored.csv`
- `grid2.geojson`
- `protected_green.geojson`
- `campus_points.json`
- `map_payload.json`

## Dashboard erzeugen

`inject_payloads.py` erwartet zusätzlich `dashboard_template.html` im Projektverzeichnis.

```bash
python inject_payloads.py
```

Erwartete Ausgabe:

- `muenster_wanderungsdruck.html`

## Dashboard lokal öffnen

Zuerst versuchen:

- `muenster_wanderungsdruck.html` direkt im Browser öffnen.

Falls der Browser lokale Inhalte blockiert (z. B. Sicherheitsbeschränkungen bei `file://`), stattdessen:

```bash
python -m http.server 8000
```

Dann im Browser öffnen:

- `http://localhost:8000/muenster_wanderungsdruck.html`

## Anpassungsmöglichkeiten

Wichtige Parameter in `build_analysis.py`:

- `CELL_SIZE_M` (Rasterzellgröße)
- `GRUEN_SCHUTZGEWICHT` (Schutzgewichte der Grünflächenarten)
- `CAMPUS_PUNKTE` (Campus-Referenzpunkte)
- `PROX_DECAY_KM` (Distanzzerfall für Campusnähe)

Die Gewichtung der Scores kann zusätzlich im Dashboard interaktiv angepasst werden.
