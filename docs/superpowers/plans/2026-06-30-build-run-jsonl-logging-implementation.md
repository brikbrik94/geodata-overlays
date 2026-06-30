# Build-Run JSONL-Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jeder Build-Pipeline-Lauf schreibt eine strukturierte JSONL-Zeile + atomare Status-Datei nach `/var/log`, registriert als zwei `log-api`-Quellen (Update-Check + Build).

**Architecture:** Ein wiederverwendbarer pure-bash Helper `scripts/ci/run_logger.sh` kapselt das Overpass-`trap … EXIT`-Muster (JSON bauen, atomar Status schreiben, History appenden, best-effort). `update.sh` (Quelle A) und `scripts/run_overlay_build.sh` (Quelle B) sourcen ihn, setzen Variablen und Extra-Felder. Beide JSONL-Dateien werden in `/opt/log-api/config.yaml` als Quellen eingetragen.

**Tech Stack:** Bash, JSONL, systemd (`log-api.service`), python3 (nur in Tests zur JSON-/YAML-Validierung).

## Global Constraints

- Log-Verzeichnis: `${GEODATA_LOG_DIR:-/var/log}` — Env-Override **muss** in jeder Schreib-Operation greifen (zur Init-Zeit ausgewertet, nicht zur Source-Zeit).
- Best-effort: Schreibfehler nach `/var/log` ergeben `log_warn`, brechen den aufrufenden Lauf **niemals** ab; der ursprüngliche Exit-Code bleibt erhalten.
- Helper ist pure-bash, keine bash-4-only-Konstrukte, keine externen Deps.
- Basisfeld-Reihenfolge jeder Zeile: `timestamp`, `status`, `duration_seconds`, <Extras in Setz-Reihenfolge>, `message`, `error`.
- Timestamp-Format: UTC `date -u '+%Y-%m-%dT%H:%M:%SZ'`.
- JSON-Escaping: `\` → `\\`, `"` → `\"`, `\n`/`\t` → Space.
- Leerer `RUN_LOG_ERROR` → JSON `null`; leerer numerischer Wert → JSON `null`.
- Status-Werte: Quelle A `up_to_date` | `build_triggered` | `error`; Quelle B `ok` | `error`.
- Alle drei Aufrufer-Scripte sind bash mit `set -euo pipefail`.

---

### Task 1: Helper `scripts/ci/run_logger.sh` + Unit-Tests

**Files:**
- Create: `scripts/ci/run_logger.sh`
- Create: `tests/test_run_logger.sh`

**Interfaces:**
- Produces:
  - `run_log_init <history_basename> <status_basename>` — wertet `${GEODATA_LOG_DIR:-/var/log}` aus, merkt Startzeit, setzt Defaults (`RUN_LOG_STATUS=error`, `RUN_LOG_ERROR="Unerwarteter Abbruch des Scripts."`), registriert `trap run_log_finalize EXIT`.
  - `run_log_str <key> <value>` — Extra-Feld als escapter String.
  - `run_log_num <key> <value>` — Extra-Feld als Zahl (leer → `null`).
  - `run_log_raw <key> <json>` — Extra-Feld als roher JSON-Wert (Bools, Arrays).
  - `run_log_finalize` — vom EXIT-Trap aufgerufen; nutzt globale Vars `RUN_LOG_STATUS`, `RUN_LOG_MESSAGE`, `RUN_LOG_ERROR`.
  - Konsumenten setzen `RUN_LOG_STATUS` / `RUN_LOG_MESSAGE` / `RUN_LOG_ERROR` vor regulärem Ende.

- [ ] **Step 1: Failing-Test schreiben**

Create `tests/test_run_logger.sh`:

```bash
#!/bin/bash
# Unit-Tests fuer scripts/ci/run_logger.sh. Aufruf: bash tests/test_run_logger.sh
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
LOGGER="$HERE/../scripts/ci/run_logger.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail() { echo "✖ $1"; exit 1; }

# --- Case 1: Erfolgszeile mit allen Extra-Typen --------------------------------
(
  export GEODATA_LOG_DIR="$TMP"
  source "$LOGGER"
  run_log_init hist.jsonl status.json
  RUN_LOG_STATUS="ok"
  RUN_LOG_MESSAGE="Build erfolgreich"
  RUN_LOG_ERROR=""
  run_log_str source external
  run_log_num datasets 14
  run_log_raw clean true
  run_log_raw stages '["pmtiles","styles"]'
)
python3 - "$TMP/hist.jsonl" "$TMP/status.json" <<'PY' || fail "Case 1"
import json, sys
lines = open(sys.argv[1]).read().splitlines()
assert len(lines) == 1, f"expected 1 line, got {len(lines)}"
o = json.loads(lines[0])
assert o["status"] == "ok", o
assert o["source"] == "external", o
assert o["datasets"] == 14, o
assert o["clean"] is True, o
assert o["stages"] == ["pmtiles", "styles"], o
assert isinstance(o["duration_seconds"], int), o
assert o["error"] is None, o
# Status-Datei = dieselbe Zeile
s = json.loads(open(sys.argv[2]).read())
assert s["status"] == "ok", s
print("OK case1")
PY

# --- Case 2: Default-Status error, wenn nichts gesetzt -------------------------
(
  export GEODATA_LOG_DIR="$TMP"
  source "$LOGGER"
  run_log_init h2.jsonl s2.json
)
python3 - "$TMP/h2.jsonl" <<'PY' || fail "Case 2"
import json, sys
o = json.loads(open(sys.argv[1]).read().splitlines()[0])
assert o["status"] == "error", o
assert o["error"] is not None, o
print("OK case2")
PY

# --- Case 3: Status-Datei wird ueberschrieben (kein Append) --------------------
(
  export GEODATA_LOG_DIR="$TMP"
  source "$LOGGER"
  run_log_init h3.jsonl s3.json
  RUN_LOG_STATUS="up_to_date"; RUN_LOG_ERROR=""
)
(
  export GEODATA_LOG_DIR="$TMP"
  source "$LOGGER"
  run_log_init h3.jsonl s3.json
  RUN_LOG_STATUS="ok"; RUN_LOG_ERROR=""
)
[ "$(wc -l < "$TMP/h3.jsonl")" -eq 2 ] || fail "Case 3 history sollte 2 Zeilen haben"
[ "$(wc -l < "$TMP/s3.json")" -eq 1 ] || fail "Case 3 status sollte 1 Zeile haben"

# --- Case 4: Nicht-existentes Log-Dir -> Warnung, kein Abbruch, Exit erhalten --
(
  export GEODATA_LOG_DIR="$TMP/does/not/exist"
  source "$LOGGER"
  run_log_init h4.jsonl s4.json
  RUN_LOG_STATUS="ok"; RUN_LOG_ERROR=""
) 2>/dev/null
[ ! -f "$TMP/does/not/exist/h4.jsonl" ] || fail "Case 4 sollte keine Datei anlegen"

# --- Case 5: Exit-Code des Aufrufers bleibt erhalten --------------------------
(
  export GEODATA_LOG_DIR="$TMP"
  source "$LOGGER"
  run_log_init h5.jsonl s5.json
  RUN_LOG_STATUS="ok"; RUN_LOG_ERROR=""
  false
)
[ "$?" -eq 1 ] || fail "Case 5 Exit-Code sollte 1 sein"

echo "✔ alle run_logger Tests bestanden"
```

- [ ] **Step 2: Test ausführen, Fehlschlag bestätigen**

Run: `bash tests/test_run_logger.sh`
Expected: FAIL — `scripts/ci/run_logger.sh` existiert nicht (`source: No such file or directory`).

- [ ] **Step 3: Helper implementieren**

Create `scripts/ci/run_logger.sh`:

```bash
#!/bin/bash
# scripts/ci/run_logger.sh
# Wiederverwendbarer JSONL-Run-Logger (Overpass-Muster, einmal gefaktet).
# Schreibt beim Script-Ende eine atomare Status-Datei + eine History-Zeile.
# Best-effort: Schreibfehler -> log_warn, niemals Abbruch; Exit-Code bleibt erhalten.
#
# Nutzung:
#   source scripts/ci/run_logger.sh
#   run_log_init <history.jsonl> <status.json>
#   RUN_LOG_STATUS="ok"; RUN_LOG_MESSAGE="..."; RUN_LOG_ERROR=""
#   run_log_str key val / run_log_num key val / run_log_raw key json

# Fallback fuer log_warn, falls ci/utils.sh nicht gesourct wurde.
if ! declare -f log_warn >/dev/null 2>&1; then
  log_warn() { echo "  ⚠ $1" >&2; }
fi

RUN_LOG_HISTORY=""
RUN_LOG_STATUS_FILE=""
RUN_LOG_START_EPOCH=0
RUN_LOG_STATUS="error"
RUN_LOG_MESSAGE="Unerwarteter Abbruch des Scripts."
RUN_LOG_ERROR="Unerwarteter Abbruch des Scripts."
_RUN_LOG_EXTRA=""

_run_log_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/ }"
  s="${s//$'\t'/ }"
  printf '%s' "$s"
}

run_log_init() {
  local dir="${GEODATA_LOG_DIR:-/var/log}"
  RUN_LOG_HISTORY="$dir/$1"
  RUN_LOG_STATUS_FILE="$dir/$2"
  RUN_LOG_START_EPOCH="$(date +%s)"
  RUN_LOG_STATUS="error"
  RUN_LOG_MESSAGE="Unerwarteter Abbruch des Scripts."
  RUN_LOG_ERROR="Unerwarteter Abbruch des Scripts."
  _RUN_LOG_EXTRA=""
  trap run_log_finalize EXIT
}

run_log_str() {
  _RUN_LOG_EXTRA+=",\"$1\":\"$(_run_log_escape "$2")\""
}

run_log_num() {
  local v="$2"
  [[ -z "$v" ]] && v="null"
  _RUN_LOG_EXTRA+=",\"$1\":$v"
}

run_log_raw() {
  _RUN_LOG_EXTRA+=",\"$1\":$2"
}

run_log_finalize() {
  local rc=$?
  local ts duration err_json msg_json line
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  duration=$(( $(date +%s) - RUN_LOG_START_EPOCH ))

  if [[ -n "$RUN_LOG_ERROR" ]]; then
    err_json="\"$(_run_log_escape "$RUN_LOG_ERROR")\""
  else
    err_json="null"
  fi
  msg_json="$(_run_log_escape "$RUN_LOG_MESSAGE")"

  line="{\"timestamp\":\"$ts\",\"status\":\"$RUN_LOG_STATUS\",\"duration_seconds\":$duration$_RUN_LOG_EXTRA,\"message\":\"$msg_json\",\"error\":$err_json}"

  if ! { printf '%s\n' "$line" > "$RUN_LOG_STATUS_FILE.tmp" \
         && mv -f "$RUN_LOG_STATUS_FILE.tmp" "$RUN_LOG_STATUS_FILE"; } 2>/dev/null; then
    log_warn "Konnte Status-Datei nicht schreiben: $RUN_LOG_STATUS_FILE"
  fi
  if ! printf '%s\n' "$line" >> "$RUN_LOG_HISTORY" 2>/dev/null; then
    log_warn "Konnte History nicht schreiben: $RUN_LOG_HISTORY"
  fi
  return "$rc"
}
```

- [ ] **Step 4: Test ausführen, Erfolg bestätigen**

Run: `bash tests/test_run_logger.sh`
Expected: PASS — endet mit `✔ alle run_logger Tests bestanden`.

- [ ] **Step 5: Commit**

```bash
git add scripts/ci/run_logger.sh tests/test_run_logger.sh
git commit -m "feat: wiederverwendbarer jsonl run-logger helper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Quelle A — `update.sh` instrumentieren

**Files:**
- Modify: `update.sh` (Sourcing-Block ~Zeile 10-21; Verzweigungen ~Zeile 23-45)
- Test: `tests/test_update_logging.sh` (Create)

**Interfaces:**
- Consumes: `run_log_init`, `RUN_LOG_STATUS`, `RUN_LOG_MESSAGE`, `RUN_LOG_ERROR` aus Task 1.
- Produces: History `geodata_overlays_update_history.jsonl`, Status `geodata_overlays_update_status.json` mit Status `up_to_date` | `build_triggered` | `error`.

- [ ] **Step 1: Failing-Test schreiben**

Create `tests/test_update_logging.sh`:

```bash
#!/bin/bash
# Integrationstest: update.sh schreibt up_to_date wenn Repo aktuell ist.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$HERE/.."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail() { echo "✖ $1"; exit 1; }

# Mini-"Upstream"-Repo + Klon als data/geojson-Ersatz, beide auf gleichem HEAD.
UP="$TMP/upstream.git"
git init -q --bare "$UP"
WORK="$TMP/seed"; git clone -q "$UP" "$WORK"
( cd "$WORK"; git config user.email t@t; git config user.name t;
  echo hi > a.txt; git add a.txt; git commit -qm init; git push -q origin HEAD:master )

# Sandbox-Repo-Wurzel mit data/geojson-Klon
SBX="$TMP/sbx"; mkdir -p "$SBX/scripts/ci"
cp "$ROOT/update.sh" "$SBX/update.sh"
cp "$ROOT/run.sh" "$SBX/run.sh"
cp "$ROOT/scripts/ci/utils.sh" "$SBX/scripts/ci/utils.sh"
cp "$ROOT/scripts/ci/run_logger.sh" "$SBX/scripts/ci/run_logger.sh"
git clone -q "$UP" "$SBX/data/geojson"
# run.sh durch Stub ersetzen, damit kein echter Build laeuft
cat > "$SBX/run.sh" <<'STUB'
#!/bin/bash
echo "STUB run.sh aufgerufen"
STUB
chmod +x "$SBX/run.sh"

export GEODATA_LOG_DIR="$TMP/logs"; mkdir -p "$GEODATA_LOG_DIR"
( cd "$SBX" && bash update.sh ) >/dev/null 2>&1 || true

HIST="$GEODATA_LOG_DIR/geodata_overlays_update_history.jsonl"
[ -f "$HIST" ] || fail "keine update-history geschrieben"
python3 - "$HIST" <<'PY' || fail "up_to_date erwartet"
import json, sys
o = json.loads(open(sys.argv[1]).read().splitlines()[-1])
assert o["status"] == "up_to_date", o
assert o["error"] is None, o
print("OK update up_to_date")
PY
echo "✔ update.sh logging Test bestanden"
```

- [ ] **Step 2: Test ausführen, Fehlschlag bestätigen**

Run: `bash tests/test_update_logging.sh`
Expected: FAIL — „keine update-history geschrieben" (update.sh loggt noch nicht).

- [ ] **Step 3: `update.sh` Sourcing erweitern**

In `update.sh` direkt **nach** dem bestehenden utils-Sourcing-Block (nach der schließenden `fi` der `if [ -f "$SCRIPT_DIR/ci/utils.sh" ]`-Konstruktion, vor `log_header "INTELLIGENT UPDATE CHECK"`) einfügen:

```bash
# Load Run-Logger (best-effort jsonl logging)
if [ -f "$SCRIPT_DIR/ci/run_logger.sh" ]; then
    source "$SCRIPT_DIR/ci/run_logger.sh"
    run_log_init geodata_overlays_update_history.jsonl geodata_overlays_update_status.json
fi
```

- [ ] **Step 4: Verzweigungs-Status setzen**

In `update.sh`, im „kein git-Repo"-Zweig (`if [ ! -d "$GEOJSON_DIR/.git" ]; then`) **vor** dem `bash "$ROOT_DIR/run.sh"`-Aufruf einfügen:

```bash
    RUN_LOG_STATUS="build_triggered"; RUN_LOG_MESSAGE="Kein git-Repo, Force-Build."; RUN_LOG_ERROR=""
```

Im „Update erkannt"-Zweig (`if [ "$LOCAL" != "$UPSTREAM" ]; then`) **vor** `cd "$ROOT_DIR"` einfügen:

```bash
    RUN_LOG_STATUS="build_triggered"
    RUN_LOG_MESSAGE="Update erkannt (${LOCAL:0:7}->${UPSTREAM:0:7}), Build gestartet."
    RUN_LOG_ERROR=""
```

Im `else`-Zweig (No updates) **vor** `exit 0` einfügen:

```bash
    RUN_LOG_STATUS="up_to_date"; RUN_LOG_MESSAGE="Keine Updates, Build uebersprungen."; RUN_LOG_ERROR=""
```

(Bei git-Fehlern greift der Default `error` über den EXIT-Trap — keine weitere Änderung nötig.)

- [ ] **Step 5: Test ausführen, Erfolg bestätigen**

Run: `bash tests/test_update_logging.sh`
Expected: PASS — `✔ update.sh logging Test bestanden`.

- [ ] **Step 6: Commit**

```bash
git add update.sh tests/test_update_logging.sh
git commit -m "feat: update.sh schreibt jsonl run-log (quelle A)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Quelle B — `scripts/run_overlay_build.sh` instrumentieren

**Files:**
- Modify: `scripts/run_overlay_build.sh` (Sourcing nach Zeile 9; Logging-Setup nach Zeile 119; Stage-Markierungen Zeile 121-132; Abschluss nach Zeile 132)
- Test: `tests/test_build_logging.sh` (Create)

**Interfaces:**
- Consumes: `run_log_init`, `run_log_str`, `run_log_num`, `run_log_raw`, `RUN_LOG_*` aus Task 1.
- Produces: History `geodata_overlays_build_history.jsonl`, Status `geodata_overlays_build_status.json` mit Feldern `source`, `clean`, `stages`, `datasets` und Status `ok` | `error`.

- [ ] **Step 1: Failing-Test schreiben**

Create `tests/test_build_logging.sh`:

```bash
#!/bin/bash
# Integrationstest: run_overlay_build.sh loggt Build-Zeile mit Stages/Feldern.
# Stage-Scripts werden durch Stubs ersetzt, damit kein echter Build laeuft.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$HERE/.."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail() { echo "✖ $1"; exit 1; }

SBX="$TMP/sbx"
mkdir -p "$SBX/scripts/ci" "$SBX/dist"
# data/geojson als git-Repo, damit external-Modus nicht download.sh aufruft
git init -q "$SBX/data/geojson"
cp "$ROOT/scripts/run_overlay_build.sh" "$SBX/scripts/run_overlay_build.sh"
cp "$ROOT/scripts/ci/utils.sh"          "$SBX/scripts/ci/utils.sh"
cp "$ROOT/scripts/ci/run_logger.sh"     "$SBX/scripts/ci/run_logger.sh"
# Stage-Stubs (run_style_build muss "manifest.json" mit datasets erzeugen)
for s in run_pmtiles_build run_sprite_pipeline; do
  printf '#!/bin/bash\necho stub %s\n' "$s" > "$SBX/scripts/$s.sh"; chmod +x "$SBX/scripts/$s.sh"
done
cat > "$SBX/scripts/run_style_build.sh" <<'STUB'
#!/bin/bash
# --out <dir> aus Argumenten ziehen und ein Manifest mit 3 datasets schreiben
out="dist"; while [ $# -gt 0 ]; do [ "$1" = "--out" ] && out="$2"; shift; done
mkdir -p "$out"; echo '{"datasets":[1,2,3]}' > "$out/manifest.json"
STUB
chmod +x "$SBX/scripts/run_style_build.sh"

export GEODATA_LOG_DIR="$TMP/logs"; mkdir -p "$GEODATA_LOG_DIR"
( cd "$SBX" && bash scripts/run_overlay_build.sh \
    --source external --skip-pmtiles --clean no --sprites no ) >/dev/null 2>&1 || true

HIST="$GEODATA_LOG_DIR/geodata_overlays_build_history.jsonl"
[ -f "$HIST" ] || fail "keine build-history geschrieben"
python3 - "$HIST" <<'PY' || fail "build-Zeile falsch"
import json, sys
o = json.loads(open(sys.argv[1]).read().splitlines()[-1])
assert o["status"] == "ok", o
assert o["source"] == "external", o
assert o["clean"] is False, o
assert "pmtiles" not in o["stages"], o          # --skip-pmtiles
assert o["stages"] == ["styles"], o             # sprites no + skip-pmtiles
assert o["datasets"] == 3, o                     # aus Stub-Manifest
assert o["error"] is None, o
print("OK build ok")
PY
echo "✔ run_overlay_build.sh logging Test bestanden"
```

- [ ] **Step 2: Test ausführen, Fehlschlag bestätigen**

Run: `bash tests/test_build_logging.sh`
Expected: FAIL — „keine build-history geschrieben".

- [ ] **Step 3: Sourcing + `dataset_count`-Helper einfügen**

In `scripts/run_overlay_build.sh` direkt **nach** Zeile 9 (`DEFAULT_OUT_DIR="$ROOT_DIR/dist"`) einfügen:

```bash

# CI-Utils + Run-Logger (best-effort jsonl logging)
if [ -f "$ROOT_DIR/scripts/ci/utils.sh" ]; then
  source "$ROOT_DIR/scripts/ci/utils.sh"
fi
if [ -f "$ROOT_DIR/scripts/ci/run_logger.sh" ]; then
  source "$ROOT_DIR/scripts/ci/run_logger.sh"
fi

# Anzahl Datasets aus dem gebauten Manifest (leer wenn nicht lesbar -> JSON null)
dataset_count() {
  local manifest="$OUT_DIR/manifest.json"
  [ -f "$manifest" ] || { printf ''; return; }
  python3 -c "import json,sys; print(len(json.load(open('$manifest')).get('datasets',[])))" 2>/dev/null || printf ''
}
```

- [ ] **Step 4: Logging-Setup nach dem Flag-Parsing einfügen**

In `scripts/run_overlay_build.sh` direkt **nach** Zeile 119 (Ende des `if [[ -z "$REBUILD_SPRITES" ]]`-Blocks, also nach dessen `fi`) und **vor** dem Sprite-Schritt (`if [[ "$REBUILD_SPRITES" =~ ...`) einfügen:

```bash

# --- Run-Logging initialisieren (Quelle B) ---
if declare -f run_log_init >/dev/null 2>&1; then
  run_log_init geodata_overlays_build_history.jsonl geodata_overlays_build_status.json
  run_log_str source "$SOURCE_MODE"
  if [[ "$CLEAN_MODE" =~ ^(yes|y|ja)$ ]]; then run_log_raw clean true; else run_log_raw clean false; fi
  STAGES=()
  [[ "$REBUILD_SPRITES" =~ ^(yes|y|ja)$ ]] && STAGES+=("sprites")
  [[ "$SKIP_PMTILES" -ne 1 ]] && STAGES+=("pmtiles")
  STAGES+=("styles")
  _stages_json="[$(printf '"%s",' "${STAGES[@]}")]"
  run_log_raw stages "${_stages_json/,]/]}"
fi
```

- [ ] **Step 5: Stage-Marker vor jedem Stage-Aufruf setzen**

In `scripts/run_overlay_build.sh` jeweils unmittelbar **vor** den drei Stage-Aufrufen eine Fehlerkontext-Zeile setzen.

Vor `bash "$ROOT_DIR/scripts/run_sprite_pipeline.sh"` (im Sprite-`if`):
```bash
    RUN_LOG_MESSAGE="Build bei Stage 'sprites' abgebrochen."; RUN_LOG_ERROR="Stage 'sprites' fehlgeschlagen."
```
Vor `bash "$ROOT_DIR/scripts/run_pmtiles_build.sh" ...` (im pmtiles-`if`):
```bash
    RUN_LOG_MESSAGE="Build bei Stage 'pmtiles' abgebrochen."; RUN_LOG_ERROR="Stage 'pmtiles' fehlgeschlagen."
```
Vor `bash "$ROOT_DIR/scripts/run_style_build.sh" ...`:
```bash
RUN_LOG_MESSAGE="Build bei Stage 'styles' abgebrochen."; RUN_LOG_ERROR="Stage 'styles' fehlgeschlagen."
```

- [ ] **Step 6: Erfolgs-Abschluss setzen**

In `scripts/run_overlay_build.sh` direkt **vor** der finalen `echo`-Erfolgsmeldung (vor Zeile 134 `echo`) einfügen:

```bash
if declare -f run_log_init >/dev/null 2>&1; then
  RUN_LOG_STATUS="ok"
  RUN_LOG_ERROR=""
  run_log_num datasets "$(dataset_count)"
  RUN_LOG_MESSAGE="Build erfolgreich (Stages: ${STAGES[*]})."
fi
```

- [ ] **Step 7: Test ausführen, Erfolg bestätigen**

Run: `bash tests/test_build_logging.sh`
Expected: PASS — `✔ run_overlay_build.sh logging Test bestanden`.

- [ ] **Step 8: Regressions-Check Task 1 + 2**

Run: `bash tests/test_run_logger.sh && bash tests/test_update_logging.sh`
Expected: beide PASS.

- [ ] **Step 9: Commit**

```bash
git add scripts/run_overlay_build.sh tests/test_build_logging.sh
git commit -m "feat: run_overlay_build.sh schreibt jsonl run-log (quelle B)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: log-api-Quellen registrieren

**Files:**
- Modify: `/opt/log-api/config.yaml` (zwei Sources anhängen)

**Interfaces:**
- Consumes: die in Task 2/3 erzeugten JSONL-Pfade.
- Produces: zwei log-api-Quellen `geodata-overlays-update` (interval 1d) und `geodata-overlays-build` (kein interval).

- [ ] **Step 1: Backup + aktuelle Validität prüfen**

```bash
cp /opt/log-api/config.yaml /opt/log-api/config.yaml.bak-$(date +%Y%m%d-%H%M%S)
python3 -c "import yaml,sys; yaml.safe_load(open('/opt/log-api/config.yaml')); print('config valid')"
```
Expected: `config valid`.

- [ ] **Step 2: Zwei Sources an `sources:` anhängen**

Ans **Ende** der `sources:`-Liste in `/opt/log-api/config.yaml` einfügen (Einrückung wie bestehende Einträge, `- id:` auf Spalte 0):

```yaml
  # ── Geodata-Overlays Build-Pipeline ─────────────────────────────────────────
- id: geodata-overlays-update
  label: Geodata-Overlays Update-Check
  path: /var/log/geodata_overlays_update_history.jsonl*
  format: jsonl
  ts_field: timestamp
  level_field: status
  message_field: message
  interval: 1d

- id: geodata-overlays-build
  label: Geodata-Overlays Build
  path: /var/log/geodata_overlays_build_history.jsonl*
  format: jsonl
  ts_field: timestamp
  level_field: status
  message_field: message
  # kein interval: event-getrieben (Build laeuft nur bei Upstream-Aenderung)
```

- [ ] **Step 3: YAML erneut validieren + IDs prüfen**

```bash
python3 -c "
import yaml
c = yaml.safe_load(open('/opt/log-api/config.yaml'))
ids = [s['id'] for s in c['sources']]
assert 'geodata-overlays-update' in ids, ids
assert 'geodata-overlays-build' in ids, ids
print('sources ok:', ids)
"
```
Expected: Liste enthält beide neuen IDs.

- [ ] **Step 4: log-api neu laden**

```bash
systemctl restart log-api.service
sleep 1
systemctl is-active log-api.service
```
Expected: `active`.

- [ ] **Step 5: Smoke-Test — eine echte Log-Zeile erzeugen und in der API sehen**

```bash
# Update-Check einmal laufen lassen (schreibt eine up_to_date- oder build_triggered-Zeile)
bash /mnt/geodata/geodata-overlays/update.sh >/dev/null 2>&1 || true
tail -n 1 /var/log/geodata_overlays_update_history.jsonl
systemctl restart log-api.service && sleep 1
curl -s http://127.0.0.1:8080/sources 2>/dev/null | grep -o 'geodata-overlays-[a-z]*' || \
  echo "Hinweis: API-Port/Pfad ggf. anpassen — /var/log-Zeile ist das maßgebliche Artefakt"
```
Expected: `/var/log/geodata_overlays_update_history.jsonl` enthält eine valide Zeile; beide Quellen tauchen in der log-api auf.

- [ ] **Step 6: Commit (Repo-Doku-Hinweis)**

`/opt/log-api/config.yaml` liegt außerhalb dieses Repos und wird **nicht** versioniert. Stattdessen im Repo-Commit nur vermerken, dass die Registrierung erfolgt ist (kein Code-Change nötig). Falls in diesem Schritt keine Repo-Datei geändert wurde, entfällt der Commit.

---

## Self-Review

**Spec-Coverage:**
- Helper `run_logger.sh` (init/str/num/raw/finalize, escaping, best-effort, `GEODATA_LOG_DIR`) → Task 1. ✓
- Quelle A `update.sh` (3 Status-Zweige) → Task 2. ✓
- Quelle B `run_overlay_build.sh` (`source`/`clean`/`stages`/`datasets`, CURRENT_STAGE-Fehlerkontext) → Task 3. ✓
- `datasets` aus `dist/manifest.json` → Task 3 Step 3 (`dataset_count`). ✓
- log-api-Registrierung (2 Sources, interval 1d / keins) → Task 4. ✓
- Best-effort/Exit-Code-Erhalt → Task 1 Steps (Case 4/5). ✓
- Nicht im Scope (Cron, reiche Metriken, run.sh-Änderung) → bleibt außen vor. ✓

**Placeholder-Scan:** Keine TBD/TODO; jeder Code-Schritt enthält vollständigen Code; Test-Code ausgeschrieben. ✓

**Typ-Konsistenz:** `run_log_init/str/num/raw/finalize` + `RUN_LOG_STATUS/MESSAGE/ERROR` + `GEODATA_LOG_DIR` durchgängig identisch in Tasks 1-3. Dateinamen `geodata_overlays_{update,build}_{history.jsonl,status.json}` identisch in Tasks 2-4. ✓
