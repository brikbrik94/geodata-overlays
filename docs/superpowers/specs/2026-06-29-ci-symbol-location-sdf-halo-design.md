# ci-symbol-location — SDF ohne Halo

**Datum:** 2026-06-29  
**Status:** Entschieden  
**Scope:** Einzelnes Icon `ci-symbol-location` aus dem `vendor/oe5ith-ci` Submodul

## Problem

`ci-symbol-location` ist ein Kompass-/Fadenkreuz-Symbol mit einem Donut-Ring (Außenkreis r=18, Innenkreis r=13, `fill-rule="evenodd"`), 4 Kardinalstrichen und einem Mittelpunkt.

Bei der SDF-Konvertierung (`build_ci_map_icons.py`, `make_sdf()`) gilt das transparente Loch im Ring als "außen" — identisch zum Bereich außerhalb des Symbols. MapLibre rendert `icon-halo-color` überall dort, wo der SDF-Wert im Gradienten-Bereich liegt. Da das Loch zwei Außenbereiche erzeugt, blutet der Halo in beide:

- außerhalb des Außenrings → gewünschter Halo-Effekt ✓
- innerhalb des Innenkreises (Loch) → Halo füllt das Loch mit Halo-Farbe ✗

Getestete SVG-Varianten (Stroke-Ring, Filled-Disc) bestätigen: das Problem ist strukturell. Jede Donut-Form mit transparentem Zentrum zeigt dasselbe Verhalten. Eine Filled-Disc würde den Halo-Bleed verhindern, opfert aber das Loch — nicht akzeptabel.

## Entscheidung

`ci-symbol-location` wird als SDF-Icon eingesetzt, aber **ohne `icon-halo-color` und `icon-halo-width`** in allen MapLibre-Layers, die dieses Icon verwenden.

Das Loch bleibt transparent (Karte sichtbar). Der Icon-Color-Mechanismus von SDF bleibt voll nutzbar.

## Umsetzung

### Pipeline

Keine Änderung notwendig. `build_ci_map_icons.py` generiert das Icon bereits korrekt:

- `sdf: true` (in `icons.json` und im gebauten Sprite)
- `spread=3.0` (via `_SPREAD_OVERRIDES["ci-symbol-location"]`), weil der Ring (5 px) und die Ticks (4 px) zu dünn für den globalen `spread=8` sind

### MapLibre Style-Layer

Jeder Layer der `ci-symbol-location` verwendet:

```json
{
  "layout": {
    "icon-image": "ci-symbol-location",
    "icon-size": 1.0
  },
  "paint": {
    "icon-color": "<accent-farbe>"
  }
}
```

**Nicht verwenden:**

```json
"icon-halo-color": "...",
"icon-halo-width": ...
```

### Readability-Strategie

Da der Icon-Halo wegfällt, wird die Lesbarkeit auf wechselndem Untergrund über den zugehörigen Text-Layer gelöst:

```json
"paint": {
  "text-color": "#ffffff",
  "text-halo-color": "#000000",
  "text-halo-width": 1.5
}
```

Das Icon selbst ist primär für den Dark-CI-Theme ausgelegt (`ACCENT=#3b82f6` auf dunklem Hintergrund).

## Konvention für zukünftige CI-Icons

CI-Symbole mit `fill-rule="evenodd"` (Donut-Shapes, Hohlformen) erhalten in `vendor/oe5ith-ci/assets/map-icons/icons.json` einen `"halo": false`-Hinweis:

```json
{
  "name": "ci-symbol-location",
  "sdf": true,
  "halo": false,
  "halo_note": "fill-rule evenodd erzeugt Loch — SDF-Halo blutet ins Loch"
}
```

`halo: false` ist kein technisches Gate (die Pipeline ignoriert es), sondern Guidance für Style-Autoren. Das Feld wird von `build_ci_map_icons.py` nicht ausgewertet — es dient nur der Dokumentation im Manifest.
