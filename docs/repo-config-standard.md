# Externer Repository-Standard (overlay_config.json)

Dieses Dokument beschreibt die Konventionen für externe GeoJSON-Repositories, die von der OE5ITH Overlay-Pipeline verarbeitet werden. Durch die Bereitstellung einer `overlay_config.json` im Hauptverzeichnis des Repositories kann der Build-Prozess (Kategorisierung, Pin-Logik, Styling) dynamisch gesteuert werden.

## Die Datei `overlay_config.json`

Die Datei definiert, welche Ordner im Repository verarbeitet werden sollen und welches Anzeige-Template (Preset) auf die darin enthaltenen GeoJSON-Dateien angewendet wird.

### Grundstruktur

```json
{
  "version": "1.0",
  "datasets": [
    {
      "path": "Zonen/X",
      "template": "zonen",
      "name": "Zonen X",
      "options": {
         "color_fallback": "#ff0000"
      }
    }
  ]
}
```

### Felder eines Datasets

*   **`path` (Pflichtfeld):** Der relative Pfad zum Ordner innerhalb des Repositories, der die `.geojson` Dateien enthält (z.B. `"RD/Wien"` oder `"Zonen/Kats"`).
*   **`template` (Pflichtfeld):** Die ID des Presets/Templates, das für das Styling und die Verarbeitung genutzt werden soll (siehe Liste unten).
*   **`name` (Optional):** Der Anzeigename des Datensatzes im Viewer und in der generierten `manifest.json`. Wenn nicht angegeben, wird der Ordnername verwendet.
*   **`options` (Optional):** Ein Objekt mit Template-spezifischen Überschreibungen (z.B. abweichende Farben oder Icons).

## Verfügbare Templates (Presets)

Die folgenden Templates werden von der Pipeline unterstützt und steuern sowohl die Generierung der Vektorkacheln (PMTiles) als auch das finale MapLibre-Styling.

### 1. `rd` (Rettungsdienst-Dienststellen)
*   **Datentyp:** Punkte.
*   **Verarbeitung:** Wendet die spezielle `derive_rd_pin`-Logik an, um Organisation (z.B. Rotes Kreuz, ASB) und Typ (z.B. NEF, RTW) aus den GeoJSON-Properties zu ermitteln und den passenden Pin zuzuweisen.
*   **Styling:** Zeigt den berechneten Pin und platziert den Text aus der Property `alt_name` darunter (in einer weißen Bubble mit dunklem Text).

### 2. `nah` (Notarzthubschrauber-Stützpunkte)
*   **Datentyp:** Punkte.
*   **Verarbeitung:** Wendet die `derive_nah_pin`-Logik an, um Betreiber (ADAC, ÖAMTC, etc.) zu erkennen. Nutzt `--no-line-simplification` beim Build.
*   **Styling:** Zeigt den NAH-spezifischen Pin und den Text `alt_name`.

### 3. `zonen` (Einsatzgebiete / Flächen)
*   **Datentyp:** Polygone, Linien, Punkte.
*   **Verarbeitung:** Standard-Vektorisierung.
*   **Styling:** Automatische Einfärbung basierend auf der Eigenschaft `alt_name` oder `name` unter Verwendung des globalen `color_mapping.json`.
*   **Optionen (`options`):**
    *   `color_fallback` (String, Hex): Überschreibt die Standard-Fallback-Farbe (Blau), falls kein Match im Mapping gefunden wird.

### 4. `gebiete` (Bezirke & Gemeinden)
*   **Datentyp:** Polygone.
*   **Verarbeitung:** Standard-Vektorisierung.
*   **Styling:** Zeichnet Polygon-Umrisse mit einem transparenten Fill-Layer (für Click-Detection). Das Label (`name`) wird automatisch im Zentroid der Fläche platziert.

### 5. `strassen` (Linien-Infrastruktur)
*   **Datentyp:** Linien.
*   **Verarbeitung:** Standard-Vektorisierung.
*   **Styling:** Zeichnet Linien mit Labels entlang des Pfades.
*   **Optionen (`options`):**
    *   `line_color` (String, Hex): Die Farbe der Linie.
    *   `bubble_icon` (String): Die ID des Icons für das Label-Shield (z.B. `"label-bubble-blue"` oder `"label-bubble-yellow"`).
    *   `text_color` (String, Hex): Die Schriftfarbe im Label.

### 6. `leitstellen` (Leitstellen-Bereiche)
*   **Datentyp:** Polygone.
*   **Verarbeitung:** Standard-Vektorisierung.
*   **Styling:** Wendet eine vordefinierte kategorische Farbpalette an, um benachbarte Bereiche visuell zu trennen. Text-Labels erhalten einen weißen Halo.

### 7. `anfahrtszeit` (Isochronen)
*   **Datentyp:** Polygone.
*   **Verarbeitung:** Standard-Vektorisierung.
*   **Styling:** Wendet einen Farbverlauf (Color Ramp von Grün nach Rot) basierend auf den Zeitintervallen an.

### 8. `sonstiges` (Liniennetzpläne)
*   **Datentyp:** Linien.
*   **Verarbeitung:** Standard-Vektorisierung.
*   **Styling:** Wendet spezielle Formatierungen (z.B. für Schnellbusse vs. reguläre Linien) basierend auf projektspezivischen Vorgaben (z.B. `linien.json`) an.

## Fallback-Verhalten (Legacy Mode)

Wenn im GeoJSON-Repository keine `overlay_config.json` gefunden wird, versucht die Pipeline weiterhin, die Ordner anhand ihrer Namen den Templates zuzuordnen (z.B. Ordner `RD-Dienststellen` wird als Template `rd` interpretiert). Es wird jedoch dringend empfohlen, neue Repositories mit einer `overlay_config.json` auszustatten.