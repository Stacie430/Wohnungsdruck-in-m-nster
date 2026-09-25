"""
Fügt die von build_analysis.py erzeugten JSON-Payloads in das HTML-Template ein
und schreibt die fertige, eigenständige Dashboard-Datei.

Aufruf (im selben Verzeichnis wie die Payload-Dateien):
    python3 inject_payloads.py
"""

from pathlib import Path

TEMPLATE = Path("dashboard_template.html")
OUTPUT = Path("muenster_wanderungsdruck.html")

PLACEHOLDERS = {
    "__PAYLOAD_MIGRATION__": "map_payload.json",
    "__PAYLOAD_GRID__": "grid2.geojson",
    "__PAYLOAD_GREEN__": "protected_green.geojson",
    "__PAYLOAD_CAMPUS__": "campus_points.json",
    "__PAYLOAD_CLUSTERS__": "clusters.json",  # optional, wird im Dashboard nicht mehr zwingend benötigt
}


def main():
    html = TEMPLATE.read_text(encoding="utf-8")
    for placeholder, filename in PLACEHOLDERS.items():
        path = Path(filename)
        if not path.exists():
            if placeholder == "__PAYLOAD_CLUSTERS__":
                # Cluster werden inzwischen client-seitig berechnet; leeres Array reicht.
                html = html.replace(placeholder, "[]")
                continue
            raise FileNotFoundError(f"Fehlende Datei: {filename} (aus build_analysis.py)")
        html = html.replace(placeholder, path.read_text(encoding="utf-8"))

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Geschrieben: {OUTPUT} ({OUTPUT.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
