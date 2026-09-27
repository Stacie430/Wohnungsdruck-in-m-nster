# Wohnungsdruck & Verdichtungspotenzial in Münster

## Projektzweck
Dieses Repository enthält einen **Analyse- und Dashboard-Prototyp** zur Frage, wo in Münster Hinweise auf zusätzlichen Bedarf an studentischem Wohnraum bestehen könnten. 

Die Pipeline kombiniert Wanderungsdaten (insbesondere Altersgruppe 20–39), Bezirksgeometrien und Grünflächeninformationen zu Rasterindikatoren und bereitet daraus eine lokale, interaktive HTML-Ausgabe auf.

> **Wichtig:** Das Projekt ist ein datengetriebener Prototyp zur Exploration. Es ist keine amtliche, rechtliche oder investive Bewertung.

## Kurzüberblick
- Datengrundlage: kommunale Open-Data-Dateien der Stadt Münster.
- Verarbeitung: `build_analysis.py` erzeugt CSV-/GeoJSON-/JSON-Artefakte.
- Ausgabe: `inject_payloads.py` baut daraus `muenster_wanderungsdruck.html`.
- Nutzung: lokales Öffnen im Browser über einen HTTP-Server.

## Relevante Dateien im Repository
| Datei | Zweck |
|---|---|
| `build_analysis.py` | Hauptpipeline für Einlesen, Aufbereitung, Rasterbewertung und Export der Analyseartefakte. |
| `inject_payloads.py` | Ersetzt Platzhalter im Dashboard-Template durch erzeugte Payloads und schreibt die finale HTML-Datei. |
| `methodik_verdichtungspotenzial.md` | Methodische Einordnung (Annahmen, Gewichtung, Grenzen). |
| `README.md` | Zusätzliche Projektdokumentation (derzeit inhaltlich ähnlich). |
| `README-1.md` | Diese überarbeitete, ausführliche Anleitung zur Reproduktion und lokalen Nutzung. |
| `LICENSE` | Lizenzinformationen. |

## Voraussetzungen
- Python **3.10+** (empfohlen: 3.10 oder 3.11)
- Befehle werden aus dem **Repository-Root** ausgeführt
- Browser mit aktiviertem JavaScript

## Eingabedaten (erforderlich)
`build_analysis.py` erwartet im Projektverzeichnis genau diese Dateien:
- `05515000_csv_altersgruppenwanderungen_saldiert.csv`
- `stadtbezirk_und_teilbereich.geojson`
- `gruen_opendata.csv`

Die Dateien stammen aus dem Open-Data-Angebot der Stadt Münster. Für reproduzierbare Ergebnisse sollten Download-Datum und ggf. Versionsstand der verwendeten Dateien dokumentiert werden.

### Optionaler Kontextdatensatz
- `umweltzone_opendata.csv` wird von der aktuellen Pipeline **nicht** eingelesen und ist daher nicht erforderlich.

## Setup (virtuelle Umgebung + `requirements.txt`)

### macOS/Linux
```bash
# im Repository-Root
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Windows PowerShell
```powershell
# im Repository-Root
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Pipeline ausführen (Reihenfolge ist wichtig)
```bash
python build_analysis.py
python inject_payloads.py
```

1. `build_analysis.py` erzeugt Analyse- und Payload-Dateien.
2. `inject_payloads.py` erzeugt daraus die finale Dashboard-Datei.

## Erwartete erzeugte Dateien
Nach erfolgreicher Ausführung sollten insbesondere folgende Dateien vorliegen:
- `pivot_20_39.csv`
- `grid_scored.csv`
- `grid2.geojson`
- `protected_green.geojson`
- `campus_points.json`
- `map_payload.json`
- `muenster_wanderungsdruck.html`

## Dashboard lokal starten (empfohlen)
Direktes Öffnen per `file://` kann je nach Browser eingeschränkt sein. Empfohlener Weg:

```bash
python -m http.server 8000
```

Dann im Browser öffnen:
- `http://localhost:8000/muenster_wanderungsdruck.html`

## Konfigurierbare Parameter in `build_analysis.py`
Folgende Parameter sind aktuell zentral konfigurierbar:
- `CELL_SIZE_M`
- `MIN_CELL_COVERAGE`
- `PROX_DECAY_KM`
- `CLUSTER_THRESHOLD`
- `CLUSTER_MIN_CELLS`
- `GRUEN_SCHUTZGEWICHT`
- `CAMPUS_PUNKTE`

## Troubleshooting (kurz)
- **`FileNotFoundError` / fehlende Eingabedateien:** Prüfen, ob alle erforderlichen Rohdateien im Repository-Root liegen und die Dateinamen exakt stimmen.
- **Fehlende Python-Pakete:** Virtuelle Umgebung aktivieren und `python -m pip install -r requirements.txt` erneut ausführen.
- **Dashboard lädt lokal nicht korrekt:** Nicht per `file://`, sondern per `python -m http.server 8000` und `http://localhost:8000/...` öffnen.
- **PowerShell-Aktivierung blockiert:** Bei restriktiver Execution Policy z. B. temporär in aktueller Sitzung erlauben: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

## Interpretation und Grenzen
Die Ergebnisse sind eine indikative Entscheidungshilfe für explorative Analysen. Sie ersetzen keine rechtliche, planerische oder investive Prüfung. Die Resultate hängen insbesondere ab von:
- den konkret verwendeten Eingabedaten,
- den gesetzten `CAMPUS_PUNKTE`,
- den Schutzgewichten in `GRUEN_SCHUTZGEWICHT`,
- sowie den übrigen Parametern der Raster- und Scoring-Logik.
