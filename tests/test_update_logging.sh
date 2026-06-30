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

# ===== TEST 2: Failing build (no-repo scenario) =====
# Create a fresh sandbox without data/geojson/.git (triggers no-repo branch)
SBX2="$TMP/sbx2"; mkdir -p "$SBX2/scripts/ci"
cp "$ROOT/update.sh" "$SBX2/update.sh"
cp "$ROOT/run.sh" "$SBX2/run.sh"
cp "$ROOT/scripts/ci/utils.sh" "$SBX2/scripts/ci/utils.sh"
cp "$ROOT/scripts/ci/run_logger.sh" "$SBX2/scripts/ci/run_logger.sh"
mkdir -p "$SBX2/data/geojson"
# run.sh stub that fails (exit 1)
cat > "$SBX2/run.sh" <<'STUB2'
#!/bin/bash
exit 1
STUB2
chmod +x "$SBX2/run.sh"

export GEODATA_LOG_DIR="$TMP/logs2"; mkdir -p "$GEODATA_LOG_DIR"
( cd "$SBX2" && bash update.sh ) >/dev/null 2>&1 || true

HIST2="$GEODATA_LOG_DIR/geodata_overlays_update_history.jsonl"
[ -f "$HIST2" ] || fail "keine update-history geschrieben (test 2)"
python3 - "$HIST2" <<'PY2' || fail "error status erwartet (test 2)"
import json, sys
o = json.loads(open(sys.argv[1]).read().splitlines()[-1])
assert o["status"] == "error", f"expected 'error', got {o['status']}"
assert o["error"] is not None, "error field must be non-null"
print("OK update error handling")
PY2

echo "✔ update.sh logging Test bestanden"
