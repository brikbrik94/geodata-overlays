# Standard: Automatisierte Geodata-Plugins (v1.4)

Dieser Standard definiert die Architektur und den Workflow für Repositories innerhalb des `geodata-updater` Ökosystems. Ziel ist eine nahtlose Integration in automatisierte Deployment-Pipelines.

## 1. Kern-Prinzipien

1. **Die Dreifaltigkeit der Einstiegspunkte**:
   - `setup.sh`: Initialisierung & Abhängigkeitsprüfung.
   - `run.sh`: Kompletter Build-Durchlauf (erzwingt Update).
   - `update.sh`: Intelligenter Orchestrator (prüft auf Änderungen vor `run.sh`).

2. **Standardisierte Ausgabe**:  
   Das Ergebnis des Build-Prozesses liegt ausnahmslos im Ordner `dist/`.

3. **Metadaten-getrieben**:  
   Die Dateien `dist/manifest.json` und `dist/layer-list.json` beschreiben den Inhalt für nachgelagerte Systeme (Deployment/Viewer/UI).

4. **Corporate Identity (CI)**:  
   Alle Ausgaben nutzen die standardisierten Logging-Utilities aus `scripts/ci/`.

---

## 2. Verzeichnisstruktur

```
geodata-plugin-repo/
├── setup.sh
├── run.sh
├── update.sh
├── DEPENDENCIES.md
├── docs/
├── assets/
├── styles/
├── sources/
├── scripts/
│   ├── ci/
│   │   ├── utils.sh
│   │   ├── utils.py
│   │   └── run_logger.sh
│   ├── check_dependencies.sh
│   ├── download.sh
│   ├── convert.sh
│   └── generate_manifest.py
└── dist/
    ├── manifest.json
    ├── layer-list.json
    ├── pmtiles/
    ├── styles/
    └── assets/
```

---

## 3. Der 4-Phasen-Workflow

### Phase 1: Pre-Flight (Check & Init)
- Aufruf von `scripts/check_dependencies.sh`.
- Prüfung auf notwendige API-Keys oder Umgebungsvariablen.
- Initialisierung der Ordnerstruktur (`mkdir -p dist build tmp`).

### Phase 2: Ingest (Download)
- Bezug der Rohdaten via `scripts/download.sh`.
- Empfehlung: Nutzung von `aria2c` oder `curl` mit ETag-Prüfung.

### Phase 3: Processing (Convert)
- Transformation der Daten via `scripts/convert.sh`.
- Typische Tools: `ogr2ogr`, `tippecanoe`, `planetiler`.
- Zielformat: PMTiles.

### Phase 4: Finalize (Manifest & Assets)
- Aufruf von `scripts/generate_manifest.py`.
- Erstellung der `manifest.json` und `layer-list.json`.

---

## 4. Manifest-Spezifikation

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| project | String | Name des Repositories |
| generated_at | String | ISO-8601 Timestamp |
| datasets | Array | Kartenebenen |

---

## 5. Layer-Listen-Spezifikation

Die `dist/layer-list.json` beschreibt die generierten Style-Layer gruppiert nach `source-layer`,
angereichert mit Metadaten für automatisiertes Legenden-Rendering in nachgelagerten UIs
(Viewer/Frontend).

> **Scope:** Diese Spezifikation (inkl. `legend_items`) ist nur für **Overlay-Plugins**
> relevant — also Repos, deren `dist/pmtiles/` als Overlay über eine Basemap gelegt wird
> (z. B. `geodata-overlays`). Die Layer-Info wird ausschließlich für Overlay-PMTiles
> konsumiert; Basemap-/Untergrund-Repos (z. B. `geodata-basemap-at`) brauchen kein
> `layer-list.json` mit dieser Legenden-Anreicherung.

### 5.1 Top-Level

| Feld | Typ | Beschreibung |
| :-- | :-- | :-- |
| `version` | String | Schema-Version, aktuell `"1.0"` |
| `styles` | Array | Ein Eintrag pro generierter `*.style.json` |

### 5.2 Style-Eintrag

| Feld | Typ | Beschreibung |
| :-- | :-- | :-- |
| `style_id` | String | Dateiname ohne `.style.json` |
| `name` | String | Anzeigename (aus `style.metadata.folder`, Fallback: title-cased `style_id`) |
| `pmtiles_path` | String | Pfad relativ zu `dist/pmtiles/`, aus der Vector-Source-URL extrahiert |
| `groups` | Array | Ein Eintrag pro `source-layer`, der im Style vorkommt |

### 5.3 Group-Eintrag (Layer-Metadaten für Legenden)

Jede `group` fasst alle Style-Layer zusammen, die dieselbe `source-layer` referenzieren (z. B.
mehrere Symbol-Layer für Icon + Label derselben Ebene), und liefert daraus abgeleitete
Anzeige-Metadaten:

| Feld | Typ | Beschreibung |
| :-- | :-- | :-- |
| `source_layer` | String | Name der Vector-Tile-Source-Layer |
| `name` | String | Anzeigename, aus der Dataset-Config aufgelöst (Fallback: `source_layer` humanisiert) |
| `template` | String | Template-Name des Datasets (`rd`, `zonen`, `strassen`, …) |
| `original_file` | String | Pfad zur Quell-GeoJSON relativ zum Datenrepo-Root |
| `style_layers` | Array\<String\> | IDs aller MapLibre-Layer dieser Gruppe |
| `type` | `"fill"` \| `"line"` \| `"symbol"` | Primärer Layer-Typ, Priorität `fill` > `line` > `symbol` |
| `color` | String \| null | Hex-Farbe des Primär-Layers (`fill-color`/`line-color`/`text-color`\|`icon-color`) |
| `opacity` | Number | Deckkraft des Primär-Layers (`*-opacity`), Default `1` |
| `legend_items` | Array\<{label, color}\> \| null | Nur gesetzt bei kategorisiertem Fill-Color (siehe 5.4); sonst `null` |

**Priorität bei Mehrfach-Layern:** Teilt sich eine `source-layer` mehrere MapLibre-Layer-Typen
(z. B. Fill + Outline-Line), gewinnt für `type`/`color`/`opacity` der Layer mit der höchsten
Priorität (`fill` > `line` > `symbol`).

### 5.4 Kategorisierte Legenden (`legend_items`)

`legend_items` wird nur befüllt, wenn unter den Layern einer `source-layer` ein `fill`-Layer
existiert, dessen `fill-color` eine `interpolate`- oder `match`-Expression ist (typisch für
Zeitstufen-/Werte-Choroplethen wie Anfahrtszeiten). Einfarbige Layer (die meisten Overlays:
Straßen, Bezirke, Symbol-Ebenen, Zonen mit fixer Farbe) liefern `null` — dort reichen
`type`/`color`/`opacity` für ein einfaches Farbfeld in der UI.

Unterstützte Expression-Formen:

- **`interpolate`**: `["interpolate", ["linear"], ["get", <prop>], stop1, color1, stop2, color2, …]`
  → ein Legenden-Eintrag pro Stufe, Label `"<stop>-<nextStop> min"`, letzte Stufe `"<stop>+ min"`.
- **`match`**: `["match", ["get", <prop>], val1, color1, val2, color2, …, fallback]`
  → nach Werten sortiert, Label `"0-<val1> min"`, danach `"<prevVal>-<val> min"` je Stufe.

```json
{ "label": "15-30 min", "color": "#facc15" }
```

> Hinweis: Die Label-Erzeugung ist aktuell fest auf die Einheit „min" verdrahtet
> (Zeitstufen-Anwendungsfall). Repos mit anderen kategorisierten Werten (z. B. Höhenstufen,
> Kapazitäten) müssen die Label-Formatierung bei der Portierung anpassen.

### 5.5 Beispiel

```json
{
  "version": "1.0",
  "styles": [
    {
      "style_id": "anfahrtszeit-linz",
      "name": "Anfahrtszeit Linz",
      "pmtiles_path": "anfahrtszeit/linz.pmtiles",
      "groups": [
        {
          "source_layer": "15_0",
          "name": "15 0",
          "template": "anfahrtszeit",
          "original_file": "anfahrtszeit/linz/15_0.geojson",
          "style_layers": ["15_0-fill"],
          "type": "fill",
          "color": "#22c55e",
          "opacity": 0.6,
          "legend_items": [
            { "label": "0-15 min", "color": "#22c55e" },
            { "label": "15-30 min", "color": "#facc15" }
          ]
        }
      ]
    },
    {
      "style_id": "bezirke",
      "name": "Bezirke",
      "pmtiles_path": "gebiete/bezirke.pmtiles",
      "groups": [
        {
          "source_layer": "bezirke",
          "name": "Bezirke",
          "template": "gebiete",
          "original_file": "gebiete/bezirke/bezirke.geojson",
          "style_layers": ["bezirke-fill", "bezirke-outline", "bezirke-label"],
          "type": "fill",
          "color": "#3b82f6",
          "opacity": 0.1,
          "legend_items": null
        }
      ]
    }
  ]
}
```

### 5.6 Referenz-Implementierung

`scripts/layer_metadata_extractor.py` (Extraktion) + `scripts/generate_layer_list.py` (Aufbau
der Gruppen-Struktur) im Repo `geodata-overlays`, einfach übernehmen. Die Extraktion läuft
generisch über **alle** Layer jedes generierten Styles — kein Template-spezifischer Sonderfall
nötig; neue Templates bekommen die Metadaten automatisch mit.

---

## 6. Logging-Standard (Konsole/CI)

- log_header
- log_step
- log_info / log_success / log_warn / log_error

---

## 7. Run-Logging & Monitoring (JSONL)

Jeder Lauf hinterlässt zusätzlich zur Konsolenausgabe einen **maschinenlesbaren Status**
unter `/var/log`, der von der zentralen **`log-api`** eingesammelt und im Monitoring
angezeigt wird. So ist auf einen Blick ersichtlich, ob ein Plugin-Lauf funktioniert hat.

### 7.1 Prinzip — zwei Quellen pro Plugin

| Quelle | Geschrieben von | Status-Werte | `interval` (log-api) |
| :-- | :-- | :-- | :-- |
| **Update-Check** | `update.sh` | `up_to_date` \| `build_triggered` \| `error` | `1d` (Heartbeat) |
| **Build** | `run.sh` / Build-Orchestrator | `ok` \| `error` | — (event-getrieben) |

`update.sh` schreibt bei **jedem** Lauf (auch wenn kein Build nötig ist) → liefert der
log-api einen verlässlichen Heartbeat. Triggert der Check einen Build und dieser schlägt
fehl, meldet die Update-Zeile `error`. Die Build-Quelle schreibt nur bei tatsächlichem Build.

### 7.2 Dateien & Namenskonvention

Pro Quelle eine **History** (append, eine JSON-Zeile pro Lauf) und eine **Status-Datei**
(atomar überschrieben, letzter Zustand). `<slug>` = Repository-Name, `-` → `_`
(z. B. `geodata-overlays` → `geodata_overlays`):

```
/var/log/<slug>_update_history.jsonl   /var/log/<slug>_update_status.json
/var/log/<slug>_build_history.jsonl    /var/log/<slug>_build_status.json
```

### 7.3 Schema

Basisfelder in fixer Reihenfolge, dazwischen quellen-spezifische Extras:

```
timestamp, status, duration_seconds, <extras…>, message, error
```

| Feld | Typ | Beschreibung |
| :-- | :-- | :-- |
| `timestamp` | String | UTC, `date -u '+%Y-%m-%dT%H:%M:%SZ'` |
| `status` | String | siehe 7.1 (`level_field` für die log-api; nur `error` ist „schlecht") |
| `duration_seconds` | Number | Laufdauer |
| `message` | String | menschenlesbare Kurzmeldung |
| `error` | String \| null | Fehlertext, `null` bei Erfolg |

Empfohlene **Build-Extras**: `source` (external/custom), `datasets` (aus `dist/manifest.json`),
`stages` (Array der gelaufenen Stufen), `clean` (bool). Beispiel:

```json
{"timestamp":"2026-06-30T06:35:12Z","status":"ok","duration_seconds":418,"source":"external","clean":false,"stages":["pmtiles","styles"],"datasets":14,"message":"Build erfolgreich.","error":null}
```

### 7.4 Helper `scripts/ci/run_logger.sh`

Wiederverwendbarer, pure-bash Helper (Referenz-Implementierung im Repo `geodata-overlays`,
einfach übernehmen). API:

```sh
source scripts/ci/run_logger.sh
run_log_init <history.jsonl> <status.json>   # registriert trap EXIT, Default-Status=error
run_log_str  <key> <value>                   # Extra-Feld: escapter String
run_log_num  <key> <value>                   # Extra-Feld: Zahl (nicht-ganzzahlig/leer → null)
run_log_raw  <key> <json>                     # Extra-Feld: roher JSON-Wert (Bool, Array)
# vor regulärem Ende setzen:
RUN_LOG_STATUS="ok"; RUN_LOG_MESSAGE="…"; RUN_LOG_ERROR=""   # leerer error → null
```

**Semantik (verbindlich):**
- **Best-effort:** Schreibfehler nach `/var/log` (z. B. manueller non-root-Lauf) ergeben nur
  `log_warn`, brechen den Lauf **nie** ab; der ursprüngliche Exit-Code bleibt erhalten.
- **EXIT-Trap:** bei unerwartetem Abbruch greift der Default `status=error` automatisch.
- **`GEODATA_LOG_DIR`** überschreibt das Log-Verzeichnis (Default `/var/log`) — für Tests
  ohne Root.
- Helper muss in **dieselbe** Shell gesourct werden, deren EXIT geloggt werden soll.

### 7.5 Registrierung in der log-api

Pro Plugin zwei Sources an `/opt/log-api/config.yaml` (`sources:`) anhängen, dann
`systemctl restart log-api.service`:

```yaml
- id: <slug>-update
  label: <Plugin> Update-Check
  path: /var/log/<slug>_update_history.jsonl*
  format: jsonl
  ts_field: timestamp
  level_field: status
  message_field: message
  interval: 1d

- id: <slug>-build
  label: <Plugin> Build
  path: /var/log/<slug>_build_history.jsonl*
  format: jsonl
  ts_field: timestamp
  level_field: status
  message_field: message
  # kein interval: event-getrieben
```

### 7.6 Scheduling

Der `update.sh`-Lauf wird per Cron geplant (der `interval: 1d` der Update-Quelle ist darauf
ausgelegt). Empfehlung: täglich, kurz nach Verfügbarkeit der Upstream-Daten, z. B.:

```
30 2 * * * /pfad/zum/plugin/update.sh >> /dev/null 2>&1
```
