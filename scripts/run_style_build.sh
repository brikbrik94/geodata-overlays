#!/usr/bin/env bash
set -euo pipefail

# Hauptskript für den modularen Style-Build
# Nutzt den neuen Orchestrator basierend auf overlay_config.json

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL_DATA_DIR="$ROOT_DIR/data/geojson"
OUT_DIR="$ROOT_DIR/dist"

usage() {
  cat <<USAGE
Usage: $(basename "$0") [options]

Options:
  --root <path>  External GeoJSON root (default: $EXTERNAL_DATA_DIR)
  --out <path>   Output directory (default: $OUT_DIR)
  --base-url <url> Public base URL for PMTiles references
  -h, --help     Show this help
USAGE
}

BASE_URL=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) EXTERNAL_DATA_DIR="$2"; shift 2 ;;
    --out) OUT_DIR="$2"; shift 2 ;;
    --base-url) BASE_URL="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 2 ;;
  esac
done

mkdir -p "$OUT_DIR/styles"

# Python Pfad setzen damit config_parser und style_utils gefunden werden
export PYTHONPATH="$ROOT_DIR/scripts:$ROOT_DIR/scripts/style_builders:${PYTHONPATH:-}"

echo "🚀 Starting modular Style build with Orchestrator..."

# Der Orchestrator liest overlay_config.json oder nutzt den Legacy-Fallback
python3 "$ROOT_DIR/scripts/build_styles.py" \
  --root "$EXTERNAL_DATA_DIR" \
  --out "$OUT_DIR" \
  --base-url "$BASE_URL"

# Fonts kopieren (NEU für Plugin-Standard)
if [[ -d "$ROOT_DIR/assets/fonts" ]]; then
  echo "🔤 Copying fonts to dist/assets/fonts..."
  mkdir -p "$OUT_DIR/assets/fonts"
  cp -r "$ROOT_DIR/assets/fonts"/* "$OUT_DIR/assets/fonts/" 2>/dev/null || true
  rm -f "$OUT_DIR/assets/fonts/README.md"
fi

# Manifest generieren
echo "📜 Generating manifest.json for external scripts..."
python3 "$ROOT_DIR/scripts/generate_manifest.py"

echo
echo "✅ Style build complete. Styles, assets and manifest.json are ready."
