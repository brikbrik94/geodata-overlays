# Design: Transparente Fill-Layer und Legenden-Metadaten

**Datum:** 2026-07-10  
**Bereich:** Style-Builder, Layer-Generierung, Legenden-Unterstützung

## Zweck

1. **Click-Interaktivität verbessern:** Polygon-Layer (Gemeinden, Bezirke) sollen als Fill-Layer dargestellt werden mit transparenter Farbe (`fill-opacity: 0`), damit MapLibre Click-Events auf der gesamten Fläche erkennt statt nur auf der dünnen Outline.

2. **Legenden-Metadaten:** Die `layer-list.json` soll erweitert werden um Informationen zur automatischen Generierung von Legenden in der Kartenanwendung (Layer-Typ, Farben, Kategorien).

## Änderungen

### 1. Style-Builder: Transparente Fill-Layer (build_bezirke.py)

**Aktuell:** Nur `line`-Layer (Outlines) und `symbol`-Layer (Labels).

**Neu:** Hinzufügen eines `fill`-Layers vor dem Outline:

```json
{
  "id": "{base_id}-fill",
  "type": "fill",
  "source": source_id,
  "source-layer": source_layer,
  "filter": geometry_filter("Polygon", "MultiPolygon"),
  "paint": {
    "fill-color": "#3b82f6",
    "fill-opacity": 0
  }
}
```

**Layer-Stack (Top-Down Rendering):**
1. Fill (transparent, für Hit-Detection)
2. Outline (blaue Linie, sichtbar)
3. Labels (Text)

**Scope:** Diese Änderung gilt für alle Polygon-Templates ohne bestehenden Fill:
- `gebiete` (Gemeinden, Bezirke) – **Priorität 1**
- Ggf. weitere identifizieren (nur wenn später Bedarf)

**Templates mit bestehenden Fills bleiben unverändert:**
- `zonen`, `leitstellen`, `anfahrtszeit` (haben bereits farbige Fills, brauchen keine Änderung)

### 2. Layer-List Generierung: Legenden-Metadaten

**Aktuell:** `layer-list.json` ist eine einfache Struktur mit Layer-Namen und Gruppierung.

**Neu:** Jeder Layer-Eintrag erhält Legenden-Metadaten:

```json
{
  "name": "Gemeinden",
  "type": "fill",
  "color": "#3b82f6",
  "label": "Gemeinden",
  "opacity": 0,
  "group": "Verwaltungsgrenzen"
}
```

Für Layer mit mehreren Kategorien (z.B. Anfahrtszeiten mit verschiedenen Zeitbereichen):

```json
{
  "name": "Anfahrtszeit",
  "type": "fill",
  "label": "Anfahrtszeiten",
  "group": "Erreichbarkeit",
  "legend_items": [
    {"label": "0-15 min", "color": "#grün"},
    {"label": "15-30 min", "color": "#gelb"},
    {"label": "30-45 min", "color": "#orange"},
    {"label": "> 45 min", "color": "#rot"}
  ]
}
```

**Metadaten pro Layer:**
- `type` (String): MapLibre-Layer-Typ (`fill`, `line`, `symbol`, etc.)
- `color` / `colors` (String oder Array): Die verwendete(n) Farbe(n) aus dem Style
- `label` (String): Beschreibender Name für Nutzer (z.B. "Gemeinden", "Anfahrtszeiten")
- `opacity` (Number, optional): Fill-Opacity falls relevant
- `legend_items` (Array, optional): Für kategorische Layer mit mehreren Einträgen
  - Jedes Item: `{label: "...", color: "#..."}`

**Quelle der Metadaten:** Diese werden aus den Style-Definitionen extrahiert:
- `color` aus `paint.fill-color` oder `paint.line-color`
- `type` aus `layer.type`
- `legend_items` aus den Kategorien im Style (z.B. Zoom-Level-basierte Farbschritte bei Anfahrtszeit)

### 3. Layer-List Struktur im Detail

```json
{
  "groups": [
    {
      "name": "Verwaltungsgrenzen",
      "layers": [
        {
          "id": "gemeinden",
          "name": "Gemeinden",
          "type": "fill",
          "color": "#3b82f6",
          "label": "Gemeinden",
          "opacity": 0,
          "style_file": "gemeinden.style.json"
        }
      ]
    },
    {
      "name": "Erreichbarkeit",
      "layers": [
        {
          "id": "anfahrtszeit",
          "name": "Anfahrtszeit",
          "type": "fill",
          "label": "Anfahrtszeiten",
          "legend_items": [
            {"label": "0-15 min", "color": "#22c55e"},
            {"label": "15-30 min", "color": "#facc15"},
            {"label": "30-45 min", "color": "#f97316"},
            {"label": "> 45 min", "color": "#ef4444"}
          ],
          "style_file": "anfahrtszeit.style.json"
        }
      ]
    }
  ]
}
```

## Implementierungsschritte

1. **build_bezirke.py:** Transparenten Fill-Layer hinzufügen
2. **generate_layer_list.py:** Legenden-Metadaten aus Style-Dateien extrahieren und in `layer-list.json` schreiben
3. **Andere Template-Builder (optional):** Falls andere Templates ebenfalls Legenden-Metadaten brauchen, später anpassen
4. **Testing:** Verifizieren, dass Click-Detection auf der Fläche funktioniert und `layer-list.json` valide ist

## Abhängigkeiten & Auswirkungen

- **Keine Breaking Changes:** Bestehende `layer-list.json` wird erweitert, alte Konsumenten ignorieren neue Felder
- **Rückwärtskompatibilität:** Alte Kartenanwendungen funktionieren weiterhin, neue Legenden-Funktion ist optional
- **Datenquellen:** Keine Änderung an GeoJSON oder `overlay_config.json` nötig

## Offene Fragen / Zukünftige Erweiterungen

- Sollen auch andere Templates (z.B. `zonen`, `leitstellen`) Legenden-Metadaten erhalten?
- Wie sollen komplexe Kategorisierungen (z.B. Data-driven Styling) in `legend_items` abgebildet werden?
