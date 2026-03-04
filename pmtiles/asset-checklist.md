# PMTiles Style Assets – benötigte Dateien & Sprite-Vorschlag

## 1) Bereits vorhandene Pin-SVGs im Repo

Folgende Markerquellen sind bereits vorhanden:

- `src/assets/fonts/rd-pin-sprite.svg`
- `src/assets/fonts/nah-pin-sprite.svg`
- `src/assets/fonts/nef-pin-sprite.svg`
- `src/assets/fonts/brd-pin-sprite.svg`
- `src/assets/fonts/fallback-pin-sprite.svg`

## 2) Für externe Style-JSONs benötigte Runtime-Assets

Damit die erzeugten Styles direkt von `tiles.oe5ith.at` geladen werden können, werden serverseitig zusätzlich benötigt:

1. **Sprite-Atlas** (MapLibre-Standard)

   - `https://tiles.oe5ith.at/assets/sprites/oe5ith-markers.png`
   - `https://tiles.oe5ith.at/assets/sprites/oe5ith-markers@2x.png`
   - `https://tiles.oe5ith.at/assets/sprites/oe5ith-markers.json`

2. **Glyphs (PBF)** für Textlabels

   - `https://tiles.oe5ith.at/assets/fonts/{fontstack}/{range}.pbf`

3. optional: **Fallback-Styles** je Ordner
   - z. B. `/styles/rd-dienststellen.style.json`

## 3) Vorschlag: Pin-SVGs zu einem gemeinsamen Sprite zusammenfassen

### Ziel

Statt pro Kategorie getrennte SVG-Logik zu fahren, ein einheitlicher MapLibre-Sprite-Atlas mit klaren IDs:

- `rd-pin`
- `nah-pin`
- `nef-pin`
- `brd-pin`
- `fallback-pin`

### Empfohlener Workflow

1. SVGs normalisieren (ViewBox, Padding, visuelle Baseline)
2. Atlas bauen (`.png`, `@2x.png`, `.json`)
3. IDs stabil halten (keine Umbenennungen ohne Migration)
4. Styles nur über `icon-image` referenzieren

### Tooling-Optionen

- `@jutaz/spritezero` / `spritezero-cli`
- alternativ Build-Schritt mit eigenem Node-Script

## 4) Datenstruktur für die ausgelagerten PMTiles

Empfohlene Zielstruktur auf `tiles.oe5ith.at`:

- `/pmtiles/Bezirke.pmtiles`
- `/pmtiles/Gemeinden.pmtiles`
- `/pmtiles/Leitstellen-Bereiche.pmtiles`
- `/pmtiles/NAH-Stützpunkte.pmtiles`
- `/pmtiles/RD-Dienststellen.pmtiles`
- `/pmtiles/Sonstiges.pmtiles`
- `/pmtiles/Straßen-Autobahnen.pmtiles`
- `/pmtiles/Straßen-Bundesstraßen.pmtiles`
- `/pmtiles/Zonen.pmtiles`

Die einzelnen ursprünglichen Dateien bleiben als `source-layer` in der jeweiligen Ordner-PMTiles enthalten.
