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
