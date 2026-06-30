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

# --- Case 6: run_log_num mit Non-Integer wird zu JSON null ---------------------
(
  export GEODATA_LOG_DIR="$TMP"
  source "$LOGGER"
  run_log_init h6.jsonl s6.json
  RUN_LOG_STATUS="ok"
  RUN_LOG_MESSAGE="Test non-numeric"
  RUN_LOG_ERROR=""
  run_log_num count abc
)
python3 - "$TMP/h6.jsonl" <<'PY' || fail "Case 6"
import json, sys
o = json.loads(open(sys.argv[1]).read().splitlines()[0])
assert o["count"] is None, f"expected null, got {o['count']}"
print("OK case6 non-numeric -> null")
PY

echo "✔ alle run_logger Tests bestanden"
