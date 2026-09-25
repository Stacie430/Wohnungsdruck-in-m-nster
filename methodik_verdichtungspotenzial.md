# Methodik: Multikriterielle Eignungsanalyse für studentischen Wohnraum in Münster

## 1. Datengrundlage

Die Analyse stützt sich auf vier Datenquellen der Stadt Münster:

1. **Wanderungsstatistik 05515000** – Jährlicher Wanderungssaldo (Zu- minus Fortzüge) der wohnberechtigten Bevölkerung, gegliedert nach fünf Altersgruppen (0–19, 20–39, 40–59, 60–79, 80+) und 44 statistischen Stadtteilen, Zeitreihe 2011–2025.
2. **Stadtbezirksgrenzen** (`stadtbezirk_und_teilbereich.geojson`) – Verwaltungsgrenzen der neun Münsteraner Stadtbezirke im Koordinatenreferenzsystem WGS84 (EPSG:4326).
3. **Grünflächenkataster** (`gruen_opendata.csv`) – 3.024 Einzelflächen mit amtlicher Objektart-Klassifikation (`obj_art`) gemäß der Legende der Stadt Münster (u. a. 01 Grünfläche, 02 Spielplatz, 04 Ausgleichsfläche, 05 Verkehrsgrün, 06 Schule, 07 Kindergarten).
4. **Umweltzone** (`umweltzone_opendata.csv`) – Abgrenzung der Feinstaub-Plakettenzone im Altstadtkern (EPSG:25832), eine straßenverkehrsrechtliche, keine baurechtliche Festlegung.

Da die Wanderungsstatistik auf Stadtteilebene (n = 44) vorliegt, die übrigen Geodaten jedoch teils feiner (Einzelparzellen) und die Stadtbezirksgrenzen gröber (n = 9) aufgelöst sind, wurden die Stadtteile anhand ihrer amtlichen Codes den neun Stadtbezirken zugeordnet (z. B. Stadtteile 11–15 → Stadtbezirk 1 Altstadt) und die Wanderungssalden je Stadtbezirk und Jahr summiert.

## 2. Raumbezug

Alle Geometrien wurden für die flächenbasierten Berechnungen von WGS84 in das metrische, für Münster geeignete System **ETRS89 / UTM Zone 32N (EPSG:25832)** transformiert (`pyproj.Transformer`). Dies ist notwendig, da Flächen- und Distanzberechnungen in einem geografischen Koordinatensystem (Grad) verzerrt wären. Die Rückprojektion nach WGS84 erfolgte ausschließlich für die kartografische Darstellung.

## 3. Rasteraufbau

Über die Vereinigungsfläche der neun Stadtbezirke (303,1 km², was der amtlichen Fläche Münsters entspricht und als Plausibilitätskontrolle diente) wurde ein regelmäßiges Raster mit einer Zellgröße von **250 m × 250 m** gelegt. Zellen mit weniger als 15 % Überlappung mit dem Stadtgebiet wurden verworfen; es verblieben 4.978 Rasterzellen. Jede Zelle wurde dem Stadtbezirk mit dem größten Flächenanteil zugeordnet.

Die Zellgröße von 250 m stellt einen Kompromiss zwischen räumlicher Differenzierung und Rechenaufwand dar; sie liegt deutlich unter der Auflösung der zugrunde liegenden Wanderungsstatistik (Stadtbezirksebene) und dient primär der kartografisch glatten Darstellung von Distanz- und Grünflächen-Gradienten innerhalb der Bezirke.

## 4. Indikatoren

Für jede Rasterzelle wurden drei Indikatoren berechnet:

**(a) Nachfragedruck.** Aus dem über die Jahre 2023–2025 gemittelten Wanderungssaldo der 20- bis 39-Jährigen je Stadtbezirk wurde ein Nachfragedruck-Indikator gebildet, indem das Vorzeichen invertiert wurde (starker Nettowegzug → hoher Druck) und anschließend eine Min-Max-Normierung auf das Intervall [0, 1] über alle Zellen erfolgte:

```
demand_score = (−ø_saldo_bezirk − min) / (max − min)
```

Diese Altersgruppe wurde als Näherung für Studierende und junge Berufstätige gewählt, da für Münster keine hochschulscharfe Wohnstatistik auf Stadtteilebene öffentlich vorliegt.

**(b) Campusnähe.** Für jede Zelle wurde die euklidische Distanz zum nächstgelegenen von vier Hochschulstandorten (WWU-Hauptgebäude, Leonardo-Campus, FH Münster Stegerwaldstraße, Universitätsklinikum) berechnet und mittels einer Exponentialfunktion in einen Nähe-Score überführt:

```
prox_raw = exp(−distanz_km / 2,5)
prox_score = Min-Max-normiert auf [0, 1]
```

Die Zerfallskonstante von 2,5 km wurde so gewählt, dass der Score innerhalb der fußläufig/fahrradnah erreichbaren Distanz spürbar abfällt, ohne den Modellraum auf ein zu enges Umfeld zu beschränken.

**(c) Grünflächenschutz.** Jeder Grünflächen-Polygon wurde nach Objektart mit einem Schutzgewicht *w* ∈ [0, 1] versehen:

| Objektart | Schutzgewicht |
|---|---|
| Ausgleichsfläche, Spielplatz, Kindergarten | 0,85–1,0 |
| Grünfläche, Schule | 0,50–0,55 |
| Sonstige Fläche, Neue Fläche | 0,20–0,30 |
| Verkehrsgrün, Rad-/Reitweg | 0,15 |

Für jede Rasterzelle wurde der flächengewichtete Grünschutzgrad als Summe der Produkte aus überlappendem Flächenanteil und Objektart-Gewicht berechnet (gekappt bei 1,0). Die Gewichtung folgt der Überlegung, dass ökologische Ausgleichsflächen sowie soziale Infrastruktur (Spielplätze, Kindergärten) rechtlich bzw. funktional kaum verfügbar sind, während schmale Verkehrsgrünstreifen eher Umgestaltungspotenzial besitzen.

Die Umweltzone wurde **nicht** als Kriterium einbezogen, da sie ausschließlich eine verkehrsrechtliche Zufahrtsbeschränkung (Feinstaubplakette) regelt und keine bauplanungsrechtliche Aussage trifft.

## 5. Eignungsindex

Der Eignungsindex einer Zelle ergibt sich als:

```
Eignung = (1 − Grünschutz × s) × (w_N × demand_score + w_C × prox_score)
```

mit interaktiv wählbaren Gewichten w_N + w_C = 1 (Standard: 0,55 / 0,45) und einem Grünschutz-Wirkungsfaktor *s* ∈ [0, 1] (Standard: 1,0). Der resultierende Rohwert wird abschließend über alle Zellen erneut min-max-normiert, sodass der Index stets das Intervall [0, 1] ausschöpft und relative Vorrangflächen unter der jeweils gewählten Gewichtung unmittelbar ablesbar sind.

Diese Parametrisierung wurde bewusst offen gehalten (siehe interaktives Dashboard), da die Gewichtung von Nachfragedruck versus Standortnähe eine normative, nicht rein datengetriebene Entscheidung ist.

## 6. Clusterbildung

Um von einzelnen Rasterzellen zu planungsrelevanten Flächen zu gelangen, wurden benachbarte Zellen mit einem Eignungswert ≥ 0,75 mittels eines Union-Find-Algorithmus über die Rasternachbarschaft (4-Konnektivität) zu zusammenhängenden Clustern zusammengefasst. Cluster mit weniger als drei Zellen (< 18,75 ha) wurden als nicht aussagekräftig verworfen.

## 7. Software

Die Datenaufbereitung erfolgte in Python 3 (pandas 2.x, shapely 2.1, pyproj 3.8, numpy). Die interaktive Visualisierung wurde als eigenständige HTML/JavaScript-Anwendung mit Leaflet.js 1.9 umgesetzt, in der Nutzer:innen die Gewichtung der Indikatoren live verändern können.

## 8. Limitationen

- **Räumliche Auflösung der Nachfrage**: Der Nachfragedruck liegt nur auf Stadtbezirksebene vor und wird gleichmäßig auf alle Zellen eines Bezirks übertragen; kleinräumige Unterschiede innerhalb eines Bezirks werden dadurch nicht abgebildet.
- **Fehlende Flurstücks- und Planungsdaten**: Eigentumsverhältnisse, Bebauungspläne, Baurecht, Altlasten, Denkmalschutz und tatsächliche Flächenverfügbarkeit sind nicht berücksichtigt. Das Modell identifiziert Vorranggebiete auf grobem Screening-Niveau, keine baureifen Grundstücke.
- **Normative Gewichtung**: Die Gewichte für Nachfragedruck, Campusnähe und Grünschutz sind Modellannahmen; die interaktive Gestaltung macht diese Annahme transparent, ersetzt aber keine fachlich-politische Abwägung.
- **Proxy-Variable Altersgruppe**: Die Altersgruppe 20–39 umfasst nicht nur Studierende, sondern auch junge Berufstätige und Familien in Gründungsphase; eine trennscharfe Zuordnung ist mit den verfügbaren Daten nicht möglich.
- **Funktionsformen**: Die exponentielle Distanzabnahme und die linearen Normierungen sind vereinfachende Annahmen ohne empirische Kalibrierung an tatsächlichem Nachfrageverhalten.
- **Zeitliche Aktualität**: Die Wanderungsdaten reichen bis 2025; kurzfristige Marktveränderungen (z. B. neue Bauprojekte nach Redaktionsschluss) sind nicht erfasst.

## Quellen

- Stadt Münster, Amt für Stadtentwicklung, Stadtplanung, Verkehrsplanung – Wanderungsstatistik 05515000, Grünflächenkataster, Stadtbezirksgrenzen, Umweltzone (Open-Data-Portal Münster)
- MLP/IW-Studentenwohnreport 2023 (Institut der deutschen Wirtschaft Köln) – zur Einordnung des studentischen Wohnungsmarkts
- Studierendenwerk Münster – Angaben zu Wartelisten für Wohnheimplätze
