"""
Multikriterielle Eignungsanalyse für studentischen Wohnraum in Münster
========================================================================
Baut aus vier Open-Data-Quellen der Stadt Münster:
  1. Wanderungsstatistik 05515000 (CSV, Stadtteilebene, 2011-2025)
  2. Stadtbezirksgrenzen (GeoJSON, WGS84)
  3. Grünflächenkataster (CSV mit WKT, WGS84)
  4. Umweltzone (CSV mit WKT, EPSG:25832) -- nur zur Kontextdarstellung

... ein 250m-Raster mit Nachfragedruck-, Campusnähe- und Grünschutz-Indikatoren
sowie die JSON-Payloads für das interaktive Leaflet-Dashboard (dashboard_template.html).

Abhängigkeiten: pandas, numpy, shapely>=2.0, pyproj
    pip install pandas numpy shapely pyproj --break-system-packages

Erwartete Eingabedateien im Arbeitsverzeichnis (Namen wie im Open-Data-Portal Münster):
    05515000_csv_altersgruppenwanderungen_saldiert.csv
    stadtbezirk_und_teilbereich.geojson
    gruen_opendata.csv
    umweltzone_opendata.csv
"""

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import pyproj
from shapely import wkt as shp_wkt
from shapely.geometry import box, mapping, shape, Point
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

# ----------------------------------------------------------------------
# Konfiguration
# ----------------------------------------------------------------------

DATA_DIR = Path(".")
CELL_SIZE_M = 250.0          # Rasterzellgröße in Metern
MIN_CELL_COVERAGE = 0.15     # Mindestanteil einer Zelle im Stadtgebiet
PROX_DECAY_KM = 2.5          # Zerfallskonstante der Campusnähe-Funktion
CLUSTER_THRESHOLD = 0.75     # Mindest-Eignung für Clusterbildung
CLUSTER_MIN_CELLS = 3

TO_METRIC = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True).transform
TO_WGS84 = pyproj.Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True).transform

# Offizielle Zuordnung Stadtteil-Code -> Stadtbezirk (Stadt Münster)
STADTTEIL_ZU_BEZIRK = {
    "1 Altstadt": [11, 12, 13, 14, 15],
    "2 Innenstadtring": [21, 22, 23, 24, 25, 26, 27, 28, 29],
    "3 Mitte-Süd": [31, 32, 33, 34],
    "4 Mitte-Nordost": [43, 44, 45, 46, 47],
    "5 Münster-West": [51, 52, 54, 56, 57, 58],
    "6 Münster-Nord": [61, 62, 63, 68],
    "7 Münster-Ost": [71, 76, 77],
    "8 Münster-Südost": [81, 82, 86, 87, 91],
    "9 Münster-Hiltrup": [95, 96, 97, 98],
}
CODE_TO_BEZIRK = {c: b for b, codes in STADTTEIL_ZU_BEZIRK.items() for c in codes}

# Objektart-Schutzgewichte für das Grünflächenkataster (amtliche Legende der Stadt Münster:
# 01 Grünfläche, 02 Spielplatz, 03 Radwanderweg, 04 Ausgleichsfläche, 05 Verkehrsgrün,
# 06 Schule, 07 Kindergarten, 08/09 Sonstige Flächen, 10 Neue Fläche, 34 Reitweg)
GRUEN_SCHUTZGEWICHT = {
    1: 0.55, 2: 1.00, 3: 0.15, 4: 1.00, 5: 0.15,
    6: 0.50, 7: 0.90, 8: 0.30, 9: 0.30, 10: 0.20, 34: 0.15,
    # Fallback für unbekannte/seltene Codes
    0: 0.30, 23: 0.30, 60: 0.30, 99: 0.30,
}

# Hochschulstandorte (Näherung, für Distanzberechnung)
CAMPUS_PUNKTE = [
    {"name": "WWU Hauptgebäude (Schloss)", "lat": 51.9622, "lon": 7.6098},
    {"name": "Leonardo-Campus", "lat": 51.9647, "lon": 7.6053},
    {"name": "FH Münster (Stegerwaldstr.)", "lat": 51.9535, "lon": 7.5813},
    {"name": "Uniklinik / Coesfelder Kreuz", "lat": 51.9506, "lon": 7.6136},
]


def parse_age_group(merkmal: str) -> str:
    """Extrahiert die Altersgruppe aus dem MERKMAL-Freitext, robust gegen
    Encoding-Artefakte (nutzt nur die Zahlen, nicht den Text drumherum)."""
    m = pd.Series([merkmal]).str.extract(r"von (\d+) und mehr|von (\d+) bis")
    hi_open, lo = m.iloc[0]
    if pd.notna(hi_open):
        return "80+"
    lo = int(lo)
    return {0: "0-19", 20: "20-39", 40: "40-59", 60: "60-79"}.get(lo, "unknown")


def load_migration_by_bezirk(csv_path: Path) -> pd.DataFrame:
    """Lädt die Wanderungsstatistik und aggregiert den Saldo der 20-39-Jährigen
    von Stadtteil- auf Stadtbezirksebene. Rückgabe: Pivot-Tabelle Bezirk x Jahr."""
    df = pd.read_csv(csv_path, sep=";", encoding="utf-8")
    df["code"] = df["RAUM"].str.extract(r"^(\d+)").astype(int)
    df["age"] = df["MERKMAL"].apply(parse_age_group)
    df["bezirk"] = df["code"].map(CODE_TO_BEZIRK)

    sub = df[df["age"] == "20-39"].copy()
    agg = sub.groupby(["bezirk", "ZEIT"], as_index=False)["WERT"].sum()
    pivot = agg.pivot(index="bezirk", columns="ZEIT", values="WERT").fillna(0).astype(int)
    return pivot.sort_index()


def load_bezirk_geometries(geojson_path: Path):
    """Lädt die Stadtbezirksgrenzen und reprojiziert sie nach EPSG:25832.
    Rückgabe: Liste von (Name, shapely-Geometrie in Metern)."""
    geo = json.load(open(geojson_path, encoding="utf-8"))
    out = []
    for f in geo["features"]:
        name = f["properties"]["STADTBEZIR"]
        geom_m = transform(TO_METRIC, shape(f["geometry"]))
        out.append((name, geom_m))
    return out


def load_green_spaces(csv_path: Path):
    """Lädt das Grünflächenkataster (WGS84-WKT), reprojiziert nach EPSG:25832
    und ordnet jedem Polygon sein Schutzgewicht zu."""
    gr = pd.read_csv(csv_path)
    geoms, weights = [], []
    for _, row in gr.iterrows():
        try:
            g = shp_wkt.loads(row["WKT"])
            g_m = transform(TO_METRIC, g)
            if not g_m.is_valid:
                g_m = g_m.buffer(0)
            geoms.append(g_m)
            weights.append(GRUEN_SCHUTZGEWICHT.get(row["obj_art"], 0.3))
        except Exception:
            continue
    return geoms, np.array(weights)


def build_grid(bezirk_geoms, cell_size=CELL_SIZE_M):
    """Erzeugt ein regelmäßiges Raster über der Vereinigungsfläche der Stadtbezirke
    und ordnet jede Zelle ihrem flächenmäßig dominanten Bezirk zu."""
    city_union = unary_union([g for _, g in bezirk_geoms])
    minx, miny, maxx, maxy = city_union.bounds
    nx = int(np.ceil((maxx - minx) / cell_size))
    ny = int(np.ceil((maxy - miny) / cell_size))

    names = [n for n, _ in bezirk_geoms]
    geoms = [g for _, g in bezirk_geoms]
    tree = STRtree(geoms)

    rows = []
    for i in range(nx):
        for j in range(ny):
            x0, y0 = minx + i * cell_size, miny + j * cell_size
            cell = box(x0, y0, x0 + cell_size, y0 + cell_size)
            best_bezirk, best_area = None, 0.0
            for idx in tree.query(cell):
                a = geoms[idx].intersection(cell).area
                if a > best_area:
                    best_area, best_bezirk = a, names[idx]
            if best_bezirk is None or best_area < cell_size * cell_size * MIN_CELL_COVERAGE:
                continue
            rows.append({"x0": x0, "y0": y0, "bezirk": best_bezirk})
    return pd.DataFrame(rows)


def score_grid(grid: pd.DataFrame, green_geoms, green_weights, migration_recent: pd.Series,
               cell_size=CELL_SIZE_M):
    """Berechnet je Rasterzelle: Grünschutzgrad, Campusdistanz sowie die
    (noch ungewichteten, min-max-normierten) Nachfrage- und Nähe-Scores."""
    tree = STRtree(green_geoms)
    campus_pts_m = [transform(TO_METRIC, Point(p["lon"], p["lat"])) for p in CAMPUS_PUNKTE]

    green_penalty, dist_campus_km, demand_raw = [], [], []
    for _, r in grid.iterrows():
        cell = box(r.x0, r.y0, r.x0 + cell_size, r.y0 + cell_size)

        penalty = 0.0
        for idx in tree.query(cell):
            inter_a = green_geoms[idx].intersection(cell).area
            if inter_a > 0:
                penalty += (inter_a / (cell_size ** 2)) * green_weights[idx]
        green_penalty.append(min(penalty, 1.0))

        centroid = Point(r.x0 + cell_size / 2, r.y0 + cell_size / 2)
        dist_campus_km.append(min(p.distance(centroid) for p in campus_pts_m) / 1000.0)

        demand_raw.append(float(migration_recent.get(r.bezirk, 0.0)))

    grid = grid.copy()
    grid["green_penalty"] = green_penalty
    grid["dist_campus_km"] = dist_campus_km
    grid["demand_raw"] = demand_raw

    demand_inv = -grid["demand_raw"]
    grid["demand_score"] = (demand_inv - demand_inv.min()) / (demand_inv.max() - demand_inv.min())

    prox_raw = np.exp(-grid["dist_campus_km"] / PROX_DECAY_KM)
    grid["prox_score"] = (prox_raw - prox_raw.min()) / (prox_raw.max() - prox_raw.min())

    return grid


def export_grid_geojson(grid: pd.DataFrame, out_path: Path, cell_size=CELL_SIZE_M):
    """Exportiert das bewertete Raster als GeoJSON (WGS84) für das Dashboard.
    Die Rohgewichte (ds, ps, g) werden mitgegeben, damit die Gewichtung im
    Browser interaktiv verändert werden kann, statt sie serverseitig festzulegen."""
    features = []
    for _, r in grid.iterrows():
        cell_m = box(r.x0, r.y0, r.x0 + cell_size, r.y0 + cell_size)
        cell_ll = transform(TO_WGS84, cell_m)
        clon, clat = TO_WGS84(r.x0 + cell_size / 2, r.y0 + cell_size / 2)
        features.append({
            "type": "Feature",
            "properties": {
                "b": r.bezirk,
                "g": round(float(r.green_penalty), 3),
                "d": round(float(r.demand_raw), 0),
                "c": round(float(r.dist_campus_km), 2),
                "ds": round(float(r.demand_score), 4),
                "ps": round(float(r.prox_score), 4),
                "x": int(r.x0), "y": int(r.y0),
                "lat": round(clat, 5), "lon": round(clon, 5),
            },
            "geometry": mapping(cell_ll),
        })
    fc = {"type": "FeatureCollection", "features": features}
    out_path.write_text(json.dumps(fc), encoding="utf-8")
    return fc


def export_protected_green(green_geoms, green_weights, out_path: Path, min_weight=0.85, simplify_m=20):
    """Vereint alle hoch geschützten Grünflächen (Ausgleichsflächen, Spielplätze,
    Kindergärten) zu einem vereinfachten Kontext-Layer für die Karte."""
    protected = [g for g, w in zip(green_geoms, green_weights) if w >= min_weight]
    merged = unary_union(protected).simplify(simplify_m, preserve_topology=True)
    merged_ll = transform(TO_WGS84, merged)
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": mapping(merged_ll)}]}
    out_path.write_text(json.dumps(fc), encoding="utf-8")
    return fc


def main():
    # 1) Wanderungsdaten auf Bezirksebene
    pivot = load_migration_by_bezirk(DATA_DIR / "05515000_csv_altersgruppenwanderungen_saldiert.csv")
    pivot.to_csv(DATA_DIR / "pivot_20_39.csv")
    migration_recent = pivot[[c for c in pivot.columns if c >= pivot.columns.max() - 2]].mean(axis=1)

    # 2) Geometrien
    bezirk_geoms = load_bezirk_geometries(DATA_DIR / "stadtbezirk_und_teilbereich.geojson")
    green_geoms, green_weights = load_green_spaces(DATA_DIR / "gruen_opendata.csv")

    # 3) Raster aufbauen und bewerten
    grid = build_grid(bezirk_geoms)
    grid = score_grid(grid, green_geoms, green_weights, migration_recent)
    grid.to_csv(DATA_DIR / "grid_scored.csv", index=False)

    # 4) Payloads für das Dashboard exportieren
    export_grid_geojson(grid, DATA_DIR / "grid2.geojson")
    export_protected_green(green_geoms, green_weights, DATA_DIR / "protected_green.geojson")
    (DATA_DIR / "campus_points.json").write_text(json.dumps(CAMPUS_PUNKTE, ensure_ascii=False), encoding="utf-8")

    # 5) Wanderungssaldo-Payload (für den ersten Dashboard-Tab)
    years = [str(y) for y in pivot.columns]
    series = {bez: {str(y): int(v) for y, v in row.items()} for bez, row in pivot.iterrows()}
    geo_wgs84 = json.load(open(DATA_DIR / "stadtbezirk_und_teilbereich.geojson", encoding="utf-8"))
    for f in geo_wgs84["features"]:
        f["properties"] = {"STADTBEZIR": f["properties"]["STADTBEZIR"], "NR_STADTBE": f["properties"]["NR_STADTBE"]}
    migration_payload = {"geojson": geo_wgs84, "series": series, "years": years}
    (DATA_DIR / "map_payload.json").write_text(json.dumps(migration_payload, ensure_ascii=False), encoding="utf-8")

    print(f"Fertig: {len(grid)} Rasterzellen bewertet und Payloads exportiert.")
    print("Erzeugte Dateien: pivot_20_39.csv, grid_scored.csv, grid2.geojson,")
    print("                  protected_green.geojson, campus_points.json, map_payload.json")


if __name__ == "__main__":
    main()
