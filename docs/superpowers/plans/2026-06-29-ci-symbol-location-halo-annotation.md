# ci-symbol-location Halo-Annotation — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `halo: false` als Dokumentationsfeld in `icons.json` des `oe5ith-ci`-Submoduls eintragen, damit Style-Autoren wissen dass `ci-symbol-location` kein `icon-halo-color` verträgt.

**Architecture:** Einzige Änderung ist das `icons.json` im Git-Submodul `vendor/oe5ith-ci`. Der Eintrag für `ci-symbol-location` bekommt zwei neue Felder: `"halo": false` und `"halo_note"`. Die Sprite-Pipeline ignoriert diese Felder (sie liest nur `name`, `file`, `viewBox`, `sdf`, `stretchX`, `stretchY`, `content`). Danach wird der Submodul-Pointer im Parent-Repo aktualisiert.

**Tech Stack:** JSON, Git Submodule

## Global Constraints

- Submodul-Pfad: `vendor/oe5ith-ci/` — alle Submodul-Commits dort, Pointer-Update im Parent
- `build_ci_map_icons.py` darf nicht verändert werden — `halo` ist reines Dokumentationsfeld
- Sprite-Build muss nach der Änderung fehlerfrei durchlaufen

---

### Task 1: `halo: false` in `icons.json` eintragen und Sprite-Build verifizieren

**Files:**
- Modify: `vendor/oe5ith-ci/assets/map-icons/icons.json` (Zeile mit `ci-symbol-location`)

**Interfaces:**
- Produziert: `icons.json` mit `"halo": false` auf dem `ci-symbol-location`-Eintrag
- `build_ci_map_icons.py` ignoriert das neue Feld — keine Code-Änderung nötig

- [ ] **Step 1: `icons.json` editieren**

Den `ci-symbol-location`-Eintrag in `vendor/oe5ith-ci/assets/map-icons/icons.json` ändern:

```json
{ 
  "name": "ci-symbol-location",
  "category": "symbol",
  "file": "ci-symbol-location.svg",
  "viewBox": [64, 64],
  "anchor": "center",
  "sdf": true,
  "recommendedColor": "--accent",
  "halo": false,
  "halo_note": "fill-rule evenodd erzeugt Loch — SDF-Halo blutet ins Loch (getestet 2026-06-29)"
}
```

- [ ] **Step 2: Sprite-Build ausführen und auf Fehler prüfen**

```bash
source .venv/bin/activate
mkdir -p work/sprites/oe5ith-markers
python3 scripts/build_ci_map_icons.py \
  --manifest vendor/oe5ith-ci/assets/map-icons/icons.json \
  --svg-dir   vendor/oe5ith-ci/assets/map-icons \
  --out-dir   work/sprites/oe5ith-markers \
  --meta-out  work/sprites/ci_meta.json
```

Erwartete Ausgabe (alle 7 Icons, kein Fehler durch neue Felder):
```
✅ Rendered 7 CI map-icons into work/sprites/oe5ith-markers (meta: ci_meta.json)
```

- [ ] **Step 3: Prüfen dass `ci_meta.json` kein `halo`-Feld enthält**

```bash
python3 -c "
import json
meta = json.load(open('work/sprites/ci_meta.json'))
loc = meta.get('ci-symbol-location', {})
print(json.dumps(loc, indent=2))
assert 'halo' not in loc, 'halo darf nicht im Meta-Output landen!'
print('OK — halo-Feld korrekt ignoriert')
"
```

Erwartete Ausgabe:
```json
{
  "sdf": true
}
OK — halo-Feld korrekt ignoriert
```

- [ ] **Step 4: Submodul committen**

```bash
cd vendor/oe5ith-ci
git add assets/map-icons/icons.json
git commit -m "docs: ci-symbol-location halo:false annotation

evenodd-Loch im Ring ist SDF-inkompatibel mit icon-halo-color.
Kein technisches Gate — reines Dokumentationsfeld fuer Style-Autoren."
cd ../..
```

- [ ] **Step 5: Submodul-Pointer im Parent-Repo aktualisieren und committen**

```bash
git add vendor/oe5ith-ci
git commit -m "chore: update oe5ith-ci submodule (halo-annotation fuer ci-symbol-location)"
```

- [ ] **Step 6: Finaler Smoke-Test — komplette Sprite-Pipeline**

```bash
bash scripts/run_sprite_pipeline.sh
```

Erwartete Ausgabe: keine Fehler, Sprite-Dateien in `dist/assets/sprites/oe5ith-markers/` aktualisiert.
