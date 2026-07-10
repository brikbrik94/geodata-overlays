# Transparente Fill-Layer und Legenden-Metadaten Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polygon-Layer (Gemeinden) als Fill-Layer mit transparenter Farbe darstellen für bessere Click-Detection, und `layer-list.json` um Legenden-Metadaten erweitern.

**Architecture:** 
1. `build_bezirke.py`: Transparenten Fill-Layer vor dem Outline-Layer einfügen (fill-opacity: 0)
2. `generate_layer_list.py`: Style-Dateien parsen um Farben, Layer-Typen und Kategorien zu extrahieren
3. `layer-list.json`: Struktur erweitern um `type`, `color`, `legend_items` pro Layer

**Tech Stack:** Python 3.9+, MapLibre style.json (v8), JSON

## Global Constraints

- Font Stack: exakt `Open-Sans-Regular` (Hyphens erforderlich)
- Layer-IDs: ASCII-sanitized (via `sanitize_name()`)
- Fill-Opacity für transparent: `0` (nicht `0.0` oder `null`)
- Legenden-Metadaten müssen aus bestehenden Style-Definitionen extrahiert werden, nicht hardcoded
- Keine Breaking Changes in bestehenden `layer-list.json`-Konsumenten

---

## Task 1: Transparenten Fill-Layer in build_bezirke.py hinzufügen

**Files:**
- Modify: `scripts/style_builders/build_bezirke.py:6-44`
- Test: `tests/test_make_sdf.py` (ggf. anpassen oder neuer Test)

**Interfaces:**
- Consumes: `geometry_filter()` von `style_utils.py` (bereits importiert)
- Produces: Style-JSON mit neuem Fill-Layer vor Outline-Layer

- [ ] **Step 1: Aktuelle `add_gebiete_layer()` Funktion in build_bezirke.py lesen**

Die Funktion sollte momentan so aussehen:
```python
def add_gebiete_layer(style, source_layer, source_id):
    base_id = f"{source_id}-{source_layer}"
    
    # Umriss Layer
    style["layers"].append({...})  # line layer
    
    # Label Layer
    style["layers"].append({...})  # symbol layer
```

- [ ] **Step 2: Fill-Layer vor Outline-Layer hinzufügen**

Modifiziere `add_gebiete_layer()` um einen Fill-Layer als **erstes Element** in die `style["layers"]` Liste einzufügen:

```python
def add_gebiete_layer(style, source_layer, source_id):
    base_id = f"{source_id}-{source_layer}"
    
    # Fill Layer (transparent, für Hit-Detection)
    style["layers"].append({
        "id": f"{base_id}-fill",
        "type": "fill",
        "source": source_id,
        "source-layer": source_layer,
        "filter": geometry_filter("Polygon", "MultiPolygon"),
        "paint": {
            "fill-color": "#3b82f6",
            "fill-opacity": 0
        }
    })
    
    # Umriss Layer (existing)
    style["layers"].append({
        "id": f"{base_id}-outline",
        "type": "line",
        "source": source_id,
        "source-layer": source_layer,
        "filter": geometry_filter("Polygon", "MultiPolygon"),
        "paint": {
            "line-color": "#3b82f6",
            "line-width": ["interpolate", ["linear"], ["zoom"], 6, 1, 12, 2.5],
            "line-opacity": 0.8
        }
    })
    
    # Label Layer (existing)
    style["layers"].append({...})
```

- [ ] **Step 3: Test schreiben - überprüfe dass Fill-Layer existiert**

Falls `tests/test_make_sdf.py` existiert, einen Test hinzufügen (sonst neuen Test schreiben):

```python
def test_gebiete_fill_layer_transparency():
    """Fill-Layer sollte transparent sein für Click-Detection"""
    # Gegeben: Ein generierter Style für Gebiete-Dataset
    import json
    from pathlib import Path
    
    # Style-Datei laden (nach Build)
    style_file = Path("dist/styles/gebiete.style.json")
    assert style_file.exists(), "Style file not found"
    
    with open(style_file) as f:
        style = json.load(f)
    
    # Suche Fill-Layer
    fill_layers = [l for l in style["layers"] if l["type"] == "fill"]
    assert len(fill_layers) > 0, "No fill layer found"
    
    # Überprüfe Fill-Opacity
    for layer in fill_layers:
        if "gebiete-fill" in layer.get("id", ""):
            assert layer["paint"]["fill-opacity"] == 0, "Fill should be fully transparent"
```

- [ ] **Step 4: Vollständigen Build durchführen und testen**

```bash
./setup.sh
./run.sh --skip-pmtiles
```

Überprüfe in `dist/styles/gebiete.style.json` dass:
- Der Fill-Layer mit ID `*-fill` vor dem Outline-Layer existiert
- `"fill-opacity": 0` ist
- `"fill-color": "#3b82f6"` ist

- [ ] **Step 5: Commit**

```bash
git add scripts/style_builders/build_bezirke.py
git commit -m "feat: transparenter fill-layer für gebiete click-detection

Fügt einen unsichtbaren (fill-opacity: 0) Fill-Layer vor dem Outline-Layer
hinzu, um MapLibre Click-Detection auf der gesamten Fläche zu ermöglichen,
nicht nur auf der Linie."
```

---

## Task 2: Legenden-Metadaten aus Styles extrahieren und in layer-list.json schreiben

**Files:**
- Modify: `scripts/generate_layer_list.py` (erweitere die Funktion)
- New: `scripts/layer_metadata_extractor.py` (helper module für Metadaten-Extraktion)

**Interfaces:**
- Consumes: Style-JSON Dateien aus `dist/styles/*.style.json`
- Produces: `layer-list.json` mit erweiterten Metadaten (type, color, legend_items)

- [ ] **Step 1: Helper-Modul schreiben für Metadaten-Extraktion**

Erstelle `scripts/layer_metadata_extractor.py`:

```python
#!/usr/bin/env python3
"""Extrahiere Farben, Typen und kategorische Daten aus MapLibre Style-Layern"""

def extract_layer_color(layer):
    """
    Extrahiere die Hauptfarbe aus einem Layer basierend auf Paint-Properties.
    Rückgabe: Hex-String oder None
    """
    paint = layer.get("paint", {})
    
    # Versuche verschiedene Paint-Properties
    if "fill-color" in paint:
        color = paint["fill-color"]
        if isinstance(color, str):
            return color
    elif "line-color" in paint:
        color = paint["line-color"]
        if isinstance(color, str):
            return color
    elif "text-color" in paint:
        color = paint["text-color"]
        if isinstance(color, str):
            return color
    
    return None

def extract_layer_opacity(layer):
    """Extrahiere Opacity aus einem Fill oder Line Layer"""
    paint = layer.get("paint", {})
    if "fill-opacity" in paint:
        return paint["fill-opacity"]
    elif "line-opacity" in paint:
        return paint["line-opacity"]
    return 1

def extract_legend_items(style_layers):
    """
    Für komplexe Layer mit mehreren Kategorien (z.B. Anfahrtszeit):
    Extrahiere Kategorien und Farben aus Data-Driven Styling
    
    Rückgabe: Liste von {label, color} oder None wenn keine Kategorien
    """
    # Vereinfachte Implementierung: wenn nur ein einzelner Fill-Layer existiert,
    # gib None zurück. Komplexere Kategorisierung kann später erweitert werden.
    return None

def extract_layer_metadata(style_data, source_layer):
    """
    Extrahiere Metadaten für einen Source-Layer aus einem Style-JSON.
    
    Rückgabe: {
        "type": "fill" | "line" | "symbol",
        "color": "#xxxxxx" | None,
        "opacity": number,
        "legend_items": [{label, color}] | None
    }
    """
    # Finde Layer die zu diesem source_layer gehören
    relevant_layers = [
        l for l in style_data.get("layers", [])
        if l.get("source-layer") == source_layer
    ]
    
    if not relevant_layers:
        return None
    
    # Bestimme primären Layer-Typ (Fill > Line > Symbol)
    layer_type = "symbol"
    primary_layer = None
    for layer in relevant_layers:
        if layer["type"] == "fill":
            layer_type = "fill"
            primary_layer = layer
            break
        elif layer["type"] == "line" and layer_type != "fill":
            layer_type = "line"
            primary_layer = layer
    
    if primary_layer is None:
        primary_layer = relevant_layers[0]
    
    color = extract_layer_color(primary_layer)
    opacity = extract_layer_opacity(primary_layer)
    legend_items = extract_legend_items(relevant_layers)
    
    return {
        "type": layer_type,
        "color": color,
        "opacity": opacity,
        "legend_items": legend_items
    }
```

- [ ] **Step 2: generate_layer_list.py anpassen**

Importiere den neuen Extractor und erweitere die Struktur der Layer in `layer_list`:

Nach Zeile 12 in `generate_layer_list.py` hinzufügen:

```python
from layer_metadata_extractor import extract_layer_metadata
```

Dann in der Schleife `for layer in style_data.get("layers", []):` (ab Zeile 81), erweitere die Logik um Metadaten zu extrahieren.

Ändere den groups_dict initialization (ab Zeile 86) so:

```python
if source_layer and layer_id:
    if source_layer not in groups_dict:
        # Lookup metadata
        meta = layer_lookup.get((style_id, source_layer), {})
        
        # Extrahiere Legenden-Metadaten aus dem Style
        legend_meta = extract_layer_metadata(style_data, source_layer)
        if legend_meta is None:
            legend_meta = {"type": "unknown", "color": None, "opacity": 1, "legend_items": None}
        
        groups_dict[source_layer] = {
            "source_layer": source_layer,
            "name": meta.get("name", source_layer.replace("_", " ").title()),
            "template": meta.get("template", "unknown"),
            "original_file": meta.get("original_file", ""),
            "type": legend_meta["type"],
            "color": legend_meta["color"],
            "opacity": legend_meta["opacity"],
            "legend_items": legend_meta["legend_items"],
            "style_layers": []
        }
    groups_dict[source_layer]["style_layers"].append(layer_id)
```

- [ ] **Step 3: Test schreiben - Metadaten-Extraktion**

Erstelle oder modifiziere `tests/test_generate_layer_list.py`:

```python
import json
from pathlib import Path
from scripts.layer_metadata_extractor import extract_layer_metadata, extract_layer_color

def test_extract_fill_color():
    """Extrahiere Farbe aus Fill-Layer"""
    layer = {
        "type": "fill",
        "paint": {
            "fill-color": "#3b82f6",
            "fill-opacity": 0.5
        }
    }
    color = extract_layer_color(layer)
    assert color == "#3b82f6"

def test_extract_transparent_fill_metadata():
    """Metadaten für transparenten Fill-Layer"""
    style_data = {
        "layers": [
            {
                "id": "gebiete-fill",
                "type": "fill",
                "source-layer": "gebiete",
                "paint": {
                    "fill-color": "#3b82f6",
                    "fill-opacity": 0
                }
            },
            {
                "id": "gebiete-outline",
                "type": "line",
                "source-layer": "gebiete",
                "paint": {
                    "line-color": "#3b82f6",
                    "line-opacity": 0.8
                }
            }
        ]
    }
    
    meta = extract_layer_metadata(style_data, "gebiete")
    assert meta is not None
    assert meta["type"] == "fill"
    assert meta["color"] == "#3b82f6"
    assert meta["opacity"] == 0

def test_layer_list_json_has_metadata():
    """Überprüfe dass layer-list.json Metadaten hat"""
    layer_list_file = Path("dist/layer-list.json")
    assert layer_list_file.exists()
    
    with open(layer_list_file) as f:
        data = json.load(f)
    
    # Finde einen Gebiete-Layer
    gebiete_found = False
    for style in data.get("styles", []):
        for group in style.get("groups", []):
            if "gebiete" in group.get("source_layer", "").lower():
                gebiete_found = True
                assert "type" in group, "Layer sollte 'type' field haben"
                assert "color" in group, "Layer sollte 'color' field haben"
                assert group["type"] == "fill"
                assert group["opacity"] == 0
    
    assert gebiete_found, "Keine gebiete-Layer in layer-list.json gefunden"
```

- [ ] **Step 4: Vollständigen Build durchführen**

```bash
./run.sh --skip-pmtiles
```

Überprüfe `dist/layer-list.json` dass die Struktur erweitert ist und Metadaten enthält:

```bash
cat dist/layer-list.json | jq '.styles[0].groups[0]'
```

Sollte Output wie:
```json
{
  "source_layer": "gebiete",
  "name": "Gemeinden",
  "type": "fill",
  "color": "#3b82f6",
  "opacity": 0,
  "legend_items": null,
  "style_layers": ["gebiete-fill", "gebiete-outline", "gebiete-labels"]
}
```

- [ ] **Step 5: Commit**

```bash
git add scripts/layer_metadata_extractor.py scripts/generate_layer_list.py tests/test_generate_layer_list.py
git commit -m "feat: legenden-metadaten in layer-list.json

Extrahiert Farben, Layer-Typen und Kategorien aus Style-Definitionen
und schreibt sie in layer-list.json für automatisierte Legenden-Generierung
in der Kartenanwendung."
```

---

## Task 3: Komplexe Kategorisierung für Anfahrtszeit (legend_items)

**Files:**
- Modify: `scripts/layer_metadata_extractor.py` (extend `extract_legend_items()`)
- Modify: `scripts/style_builders/build_anfahrtszeit.py` (falls nötig)

**Interfaces:**
- Consumes: Style-JSON mit kategorischen Farben (z.B. Data-Driven Styling)
- Produces: `legend_items` Array in `layer-list.json`

- [ ] **Step 1: Aktuelle build_anfahrtszeit.py lesen**

Lese die Datei um zu verstehen, wie Zeitbereiche eingefärbt werden:

```bash
head -50 scripts/style_builders/build_anfahrtszeit.py
```

- [ ] **Step 2: extract_legend_items() implementieren**

Falls `build_anfahrtszeit.py` Zoom-basierte oder kategorische Farben benutzt, erweitere `extract_legend_items()` in `layer_metadata_extractor.py`:

```python
def extract_legend_items(style_layers):
    """
    Für Layer mit kategorischen Farben (z.B. Anfahrtszeit):
    Extrahiere Kategorien und Farben.
    
    Rückgabe: Liste von {label, color} oder None
    """
    if not style_layers:
        return None
    
    fill_layers = [l for l in style_layers if l["type"] == "fill"]
    if not fill_layers:
        return None
    
    primary = fill_layers[0]
    paint = primary.get("paint", {})
    fill_color = paint.get("fill-color")
    
    # Falls fill-color ein Array ist (interpolate, categorical), parse es
    if isinstance(fill_color, list) and len(fill_color) > 0:
        # Format: ["interpolate", [...], property, ...stops...]
        # oder: ["match", property, value1, color1, value2, color2, ...]
        
        if fill_color[0] == "interpolate" and len(fill_color) > 3:
            # Z.B. ["interpolate", ["linear"], ["get", "time"], 0, "#grün", 15, "#gelb", 30, "#orange", 45, "#rot"]
            items = []
            for i in range(4, len(fill_color), 2):
                if i + 1 < len(fill_color):
                    value = fill_color[i]
                    color = fill_color[i + 1]
                    if isinstance(color, str):
                        items.append({
                            "label": f"0-{value} min" if i == 4 else f"{fill_color[i-2]}-{value} min",
                            "color": color
                        })
            return items if items else None
    
    return None
```

- [ ] **Step 3: Test für Anfahrtszeit legend_items**

```python
def test_anfahrtszeit_legend_items():
    """Extrahiere Kategorien aus Anfahrtszeit-Style"""
    layer_list_file = Path("dist/layer-list.json")
    with open(layer_list_file) as f:
        data = json.load(f)
    
    for style in data.get("styles", []):
        for group in style.get("groups", []):
            if "anfahrtszeit" in group.get("source_layer", "").lower():
                # Sollte legend_items haben
                items = group.get("legend_items")
                if items:
                    assert isinstance(items, list)
                    for item in items:
                        assert "label" in item
                        assert "color" in item
                        assert item["color"].startswith("#")
```

- [ ] **Step 4: Build und Test**

```bash
./run.sh --skip-pmtiles
pytest tests/test_generate_layer_list.py::test_anfahrtszeit_legend_items -v
```

- [ ] **Step 5: Commit**

```bash
git add scripts/layer_metadata_extractor.py tests/test_generate_layer_list.py
git commit -m "feat: kategorische legenden-items für anfahrtszeit

Extrahiert Zeitbereiche und zugehörige Farben aus Anfahrtszeit-Styles
und speichert sie als legend_items in layer-list.json."
```

---

## Task 4: End-to-End Test und Verifizierung

**Files:**
- Test: `tests/test_end_to_end_styles.py` (neu oder erweitert)

**Interfaces:**
- Consumes: Gesamter Build (run.sh)
- Produces: Verifizierte dist/ Struktur mit allen Metadaten

- [ ] **Step 1: E2E Test schreiben**

Erstelle oder erweitere `tests/test_end_to_end_styles.py`:

```python
import json
from pathlib import Path

def test_full_build_output():
    """Überprüfe dass ein kompletter Build alle erforderlichen Dateien erzeugt"""
    dist = Path("dist")
    
    # Dateien müssen existieren
    assert (dist / "layer-list.json").exists()
    assert (dist / "manifest.json").exists()
    assert (dist / "styles").exists()
    assert list((dist / "styles").glob("*.style.json")), "Keine Style-Dateien gefunden"

def test_layer_list_structure():
    """Überprüfe dass layer-list.json die korrekte Struktur hat"""
    with open(Path("dist/layer-list.json")) as f:
        layer_list = json.load(f)
    
    assert "version" in layer_list
    assert "styles" in layer_list
    
    for style in layer_list["styles"]:
        assert "style_id" in style
        assert "name" in style
        assert "groups" in style
        
        for group in style["groups"]:
            # Neue Felder
            assert "type" in group, f"Group {group.get('source_layer')} missing 'type'"
            assert "color" in group or group["type"] == "symbol", f"Group {group.get('source_layer')} missing 'color'"
            assert "opacity" in group
            assert "style_layers" in group

def test_gebiete_transparent_fill():
    """Überprüfe dass Gebiete-Layer transparent Fill + Outline hat"""
    with open(Path("dist/layer-list.json")) as f:
        layer_list = json.load(f)
    
    gebiete_group = None
    for style in layer_list["styles"]:
        for group in style["groups"]:
            if "gebiete" in group.get("source_layer", "").lower():
                gebiete_group = group
                break
    
    assert gebiete_group is not None, "Gebiete group not found"
    assert gebiete_group["type"] == "fill"
    assert gebiete_group["opacity"] == 0
    assert len(gebiete_group["style_layers"]) >= 3  # fill, outline, labels

def test_click_detection_on_filled_polygon():
    """Verifizie dass der Fill-Layer tatsächlich transparent ist"""
    with open(Path("dist/styles/gebiete.style.json")) as f:
        style = json.load(f)
    
    fill_layer = None
    for layer in style["layers"]:
        if layer["type"] == "fill" and "fill" in layer["id"]:
            fill_layer = layer
            break
    
    assert fill_layer is not None, "Fill layer not found in gebiete style"
    assert fill_layer["paint"]["fill-opacity"] == 0
    assert fill_layer["paint"]["fill-color"] == "#3b82f6"
```

- [ ] **Step 2: Tests ausführen**

```bash
pytest tests/test_end_to_end_styles.py -v
```

- [ ] **Step 3: Manuell in der Kartenanwendung verifizieren (falls möglich)**

Falls du eine Test-Viewer-Instanz hast, überprüfe:
1. Gemeinden-Flächen sind sichtbar mit Outline und Label
2. Click auf die Fläche (nicht nur auf die Linie) funktioniert
3. Die `layer-list.json` wird korrekt geladen und enthält Metadaten

```bash
python3 tools/test_overlay_server.py --bundle-dir dist --host 127.0.0.1 --port 8000
# Browser: http://127.0.0.1:8000 - Click auf Gemeinden testen
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_end_to_end_styles.py
git commit -m "test: e2e test für transparent fills und legenden-metadaten"
```

---

## Task 5: Dokumentation aktualisieren

**Files:**
- Modify: `CLAUDE.md` (Update Abschnitt "Output layout")
- Modify: `docs/repo-config-standard.md` (Update gebiete Template-Beschreibung)

**Interfaces:**
- Consumes: Neues Verhalten
- Produces: Aktualisierte Dokumentation

- [ ] **Step 1: CLAUDE.md aktualisieren**

Finde den Abschnitt "Output layout" und ergänze:

```markdown
## Output layout (`dist/`)

`pmtiles/` (vector tiles, mirrors source folder structure), `styles/*.style.json`, `manifest.json`, `layer-list.json` (layers grouped logically by source, enriched with legend metadata: layer type, color(s), opacity, categorical items), `assets/` (sprites + fonts).
```

- [ ] **Step 2: docs/repo-config-standard.md aktualisieren**

Finde den Abschnitt "### 4. `gebiete`" und update:

```markdown
### 4. `gebiete` (Bezirke & Gemeinden)
*   **Datentyp:** Polygone.
*   **Verarbeitung:** Standard-Vektorisierung.
*   **Styling:** Zeichnet Polygon-Umrisse mit einem transparenten Fill-Layer (für Click-Detection). Das Label (`name`) wird automatisch im Zentroid der Fläche platziert.
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md docs/repo-config-standard.md
git commit -m "docs: dokumentiere transparente fill-layer für gebiete

Aktualisiere Output-Layout Beschreibung und gebiete Template-Dokumentation."
```

---

## Spec Coverage Check

✅ **Transparente Fill-Layer (Task 1):** `build_bezirke.py` fügt unsichtbaren Fill-Layer für Click-Detection hinzu  
✅ **Layer-Gruppierung (Task 2):** `generate_layer_list.py` gruppiert Fill + Outline + Labels unter einem Eintrag  
✅ **Legenden-Metadaten (Task 2):** Struktur mit `type`, `color`, `opacity`, `legend_items`  
✅ **Kategorische Kategorisierung (Task 3):** Anfahrtszeit legend_items werden extrahiert  
✅ **E2E Tests (Task 4):** Vollständige Verifizierung  
✅ **Dokumentation (Task 5):** CLAUDE.md und repo-config-standard.md aktualisiert  

---

## Plan complete and saved to `docs/superpowers/plans/2026-07-10-transparent-fill-legend-metadata.md`

Two execution options:

**1. Subagent-Driven (recommended)** - Ich dispatche einen frischen Subagent pro Task, reviewe zwischen Tasks, schnelle Iteration

**2. Inline Execution** - Execute Tasks in dieser Session mit superpowers:executing-plans, batch execution mit Checkpoints

**Welcher Ansatz?**
