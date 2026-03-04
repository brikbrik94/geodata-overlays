# PMTiles Folder-Styles (CI-konform)

Dieses Paket enthält **MapLibre-Style-JSONs pro Datenordner** für die geplante Zielstruktur auf `tiles.oe5ith.at`:

- pro Ordner genau **eine PMTiles-Datei** (z. B. `.../pmtiles/Gemeinden.pmtiles`)
- innerhalb dieser PMTiles liegen die bisherigen Einzellayer als `source-layer`
- pro Ordner ein Style-JSON, das alle `source-layer` des Ordners anspricht

Die Styles wurden aus den vorhandenen `_manifest.json`-Dateien abgeleitet und folgen den CI-Vorgaben aus `docs/corporate-identity.md` (Dark UI, Akzent-Blau, saubere Borders/Kontrast).

## Erzeugte Style-Dateien

Sie liegen unter:

- `docs/pmtiles/styles/*.style.json`
- Index/Übersicht: `docs/pmtiles/styles/index.json`

## Generierung

Die Styles werden per Script erzeugt:

```bash
node scripts/generate-pmtiles-folder-styles.js
```

Das Script:

1. liest alle `public/data/tiles/**/_manifest.json`
2. sammelt pro Ordner alle `sourceLayer`
3. erzeugt ein Style-JSON pro Ordner mit Quelle:
   - `pmtiles://https://tiles.oe5ith.at/pmtiles/<ORDNER>.pmtiles`
4. setzt je `source-layer` passende Layer-Typen:
   - Standard: `fill` + `line` + `circle`
   - `RD-Dienststellen`/`NAH-Stützpunkte`: `symbol` (mit Marker-Icons)

## Hinweis zum Betrieb auf tiles.oe5ith.at

Die Styles sind so vorbereitet, dass sie extern gehostet werden können. Für produktive Nutzung müssen die in der Asset-Checkliste genannten Sprite-/Font-Dateien bereitgestellt werden (siehe `docs/pmtiles/asset-checklist.md`).
