# Code zur Eignungsanalyse „Wohnungsdruck & Verdichtungspotenzial Münster“

## Dateien

| Datei | Zweck |
|---|---|
| `build_analysis.py` | Kompletter Datenpipeline: lädt die vier Rohdatensätze, aggregiert die Wanderungsstatistik auf Stadtbezirksebene, baut das 250m-Raster, berechnet Nachfrage-, Nähe- und Grünschutz-Scores und exportiert alle JSON/GeoJSON-Payloads. |
| `dashboard_template.html` | Das interaktive Leaflet-Dashboard (zwei Tabs: Wanderungsdruck-Zeitreihe, Verdichtungspotenzial mit live verstellbaren Gewichtungs-Reglern). Enthält Platzhalter (`__PAYLOAD_...__`) anstelle der eingebetteten Daten. |
| `inject_payloads.py` | Ersetzt die Platzhalter im Template durch die von `build_analysis.py` erzeugten JSON-Dateien und schreibt die fertige, eigenständige HTML-Datei. |
| `methodik_verdichtungspotenzial.md` | Ausformulierter Methodik-Abschnitt für die Bachelorarbeit (Formeln, Gewichtungslogik, Limitationen, Quellen). |

## Reproduktion

1. Die vier Rohdaten-Dateien der Stadt Münster ins selbe Verzeichnis legen:
   - `05515000_csv_altersgruppenwanderungen_saldiert.csv`
   - `stadtbezirk_und_teilbereich.geojson`
   - `gruen_opendata.csv`
   - `umweltzone_opendata.csv`
2. Abhängigkeiten installieren:
   ```
   pip install pandas numpy shapely pyproj --break-system-packages
   ```
3. Pipeline ausführen:
   ```
   python3 build_analysis.py
   ```
   Erzeugt u. a. `grid2.geojson`, `protected_green.geojson`, `campus_points.json`, `map_payload.json`.
4. Dashboard zusammenbauen:
   ```
   python3 inject_payloads.py
   ```
   Erzeugt `muenster_wanderungsdruck.html` — im Browser öffnen, fertig.

## Anpassungsmöglichkeiten

- **Zellgröße**: `CELL_SIZE_M` in `build_analysis.py` (Standard 250 m).
- **Schutzgewichte** der Grünflächen-Objektarten: `GRUEN_SCHUTZGEWICHT`.
- **Hochschulstandorte**: `CAMPUS_PUNKTE` — bei Bedarf weitere Standorte ergänzen.
- **Zerfallskonstante der Campusnähe**: `PROX_DECAY_KM`.
- Die Gewichtung von Nachfragedruck vs. Campusnähe sowie die Stärke des Grünflächenschutzes müssen **nicht** im Python-Code geändert werden — sie sind im Dashboard selbst über zwei Regler live einstellbar.
