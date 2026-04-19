# Projekt-Status: Modulare Overlay-Build-Pipeline

Diese Datei dient als Gedächtnisstütze für den aktuellen Stand der Umstellung auf das modulare Build-System.

## Aktueller Fortschritt
Wir haben die Umstellung auf das modulare Build-System und die Konfigurations-Hoheit via `overlay_config.json` erfolgreich abgeschlossen.

### Implementierte Module
- **PMTiles-Builder:** `scripts/pmtiles_builder.py` übernimmt die Konvertierung von GeoJSON zu PMTiles. Nutzt die `overlay_config.json` zur Steuerung von Pin-Logik (RD/NAH) und Tippecanoe-Parametern.
- **Config-Parser:** `scripts/config_parser.py` liest die `overlay_config.json` aus dem GeoJSON-Repo und stellt einen Legacy-Fallback bereit.
- **Style-Orchestrator:** `scripts/build_styles.py` ist der zentrale Einstiegspunkt für den Style-Build. Er mappt Datensätze auf Templates.
- **Manifest-Generator:** `scripts/generate_manifest.py` erstellt die finale `manifest.json` für das Deployment (Plugin-Standard v1.0).

### Meilensteine (Abgeschlossen)
- [x] **Rename auf `overlay_config.json`**: Konsistente Benennung im gesamten Repo (Code & Docs).
- [x] **Externer Repo-Sync**: `scripts/init_external_geojson_repo.sh` erfolgreich für CI/CD-Workflows integriert.
- [x] **Validierung**: Test-Build mit 12+ Datensätzen erfolgreich durchgeführt.
- [x] **SDF-Icons**: Label-Bubbles und Pins werden korrekt gerendert.

### Verfügbare Templates (Presets)
1.  **`rd`**: Rettungsdienst mit automatischer Pin-Ermittlung und Label-Bubbles.
2.  **`nah`**: Notarzthubschrauber mit Betreiber-Pins und optimierten Build-Flags.
3.  **`zonen`**: Flächen/Linien mit automatischer Einfärbung via `color_mapping.json`.
4.  **`gebiete`**: Bezirke/Gemeinden (Umrisse + Zentroid-Labels).
5.  **`strassen`**: Linien mit Shields (Autobahnen/Bundesstraßen).
6.  **`leitstellen`**: Gebiete mit kategorischer Farbpalette.
7.  **`anfahrtszeit`**: Isochronen mit Color-Ramp (Grün-Rot).
8.  **`sonstiges`**: Spezial-Styles (z.B. Liniennetzpläne).

## Konventionen für externe Repos
Ein GeoJSON-Repo kann eine `overlay_config.json` im Root bereitstellen:
```json
{
  "datasets": [
    { "path": "Ordner/Pfad", "template": "zonen", "name": "Anzeigename" }
  ]
}
```
Ohne diese Datei greift der **Legacy-Mode**, der versucht, Ordnernamen automatisch den Templates zuzuordnen.

## Wichtige Konfigurationen
- **Schriftart:** Muss zwingend `Open-Sans-Regular` (mit Bindestrichen) sein.
- **Pfad-Sanitierung:** Alle Layer-IDs und Dateinamen werden in ASCII-Kleinschreibung umgewandelt (ä->ae, etc.).
- **Test-Server:** `test_overlay_server.py` wurde angepasst, um keine Text-Attribute im RD-Style mehr zu filtern.

## Offene Aufgaben (Next Steps)
- [x] **Finaler Cleanup:** Alle veralteten Skripte (`build_hosted_overlays.py`, etc.) wurden in den Ordner `legacy/` verschoben. Die modulare Pipeline ist nun der Standard.

## Build ausführen
```bash
# PMTiles bauen (aus external/geojson-data)
bash scripts/run_pmtiles_build.sh

# Styles und Manifest bauen
bash scripts/run_style_build.sh
```
