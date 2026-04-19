#!/usr/bin/env bash
set -euo pipefail

# Modulares Build-Skript für Overlays
# Nutzt das externe GeoJSON-Repository als primäre Datenquelle.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_EXTERNAL_ROOT="$ROOT_DIR/data/geojson"
DEFAULT_OUT_DIR="$ROOT_DIR/dist"

SOURCE_MODE="external"
CUSTOM_ROOT=""
OUT_DIR="$DEFAULT_OUT_DIR"
CLEAN_MODE=""
REBUILD_SPRITES=""
SKIP_PMTILES=0

usage() {
  cat <<USAGE
Usage: $(basename "$0") [options]

Options:
  --source <external|custom>  Data source mode (defaults to external)
  --root <path>               Custom data root (implies --source custom)
  --out <path>                Output directory (default: $DEFAULT_OUT_DIR)
  --clean <yes|no>            Clean output directory before build
  --sprites <yes|no>          Rebuild sprites before build
  --skip-pmtiles              Build only manifests/styles/index (no tippecanoe)
  -h, --help                  Show this help
USAGE
}

ask_yes_no() {
  local prompt="$1"
  local default="$2"
  local answer
  while true; do
    read -r -p "$prompt" answer
    answer="${answer:-$default}"
    case "${answer,,}" in
      y|yes|ja) echo "yes"; return 0 ;;
      n|no|nein) echo "no"; return 0 ;;
      *) echo "Bitte yes/no bzw. y/n eingeben." ;;
    esac
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE_MODE="$2"
      shift 2
      ;;
    --root)
      SOURCE_MODE="custom"
      CUSTOM_ROOT="$2"
      shift 2
      ;;
    --out)
      OUT_DIR="$2"
      shift 2
      ;;
    --clean)
      CLEAN_MODE="$2"
      shift 2
      ;;
    --sprites)
      REBUILD_SPRITES="$2"
      shift 2
      ;;
    --skip-pmtiles)
      SKIP_PMTILES=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

# Legacy/Compatibility Mapping
if [[ "$SOURCE_MODE" == "local" ]]; then
  SOURCE_MODE="external"
fi

if [[ "$SOURCE_MODE" == "external" ]]; then
  DATA_ROOT="$DEFAULT_EXTERNAL_ROOT"
  if [[ ! -d "$DATA_ROOT/.git" ]]; then
    echo "ℹ️ External repo nicht vorhanden. Initialisiere es jetzt..."
    bash "$ROOT_DIR/scripts/init_external_geojson_repo.sh" --target "$DATA_ROOT"
  fi
elif [[ "$SOURCE_MODE" == "custom" ]]; then
  if [[ -z "$CUSTOM_ROOT" ]]; then
    read -r -p "Pfad zum GeoJSON-Root: " CUSTOM_ROOT
  fi
  DATA_ROOT="$CUSTOM_ROOT"
else
  echo "Unsupported --source value: $SOURCE_MODE (Use 'external' or 'custom')" >&2
  exit 2
fi

if [[ ! -d "$DATA_ROOT" ]]; then
  echo "Data root does not exist: $DATA_ROOT" >&2
  exit 2
fi

if [[ -z "$CLEAN_MODE" ]]; then
  CLEAN_MODE="$(ask_yes_no "Clean build starten? [y/N]: " "no")"
fi

if [[ -z "$REBUILD_SPRITES" ]]; then
  REBUILD_SPRITES="$(ask_yes_no "Sprites neu bauen? [y/N]: " "no")"
fi

if [[ "$REBUILD_SPRITES" =~ ^(yes|y|ja)$ ]]; then
  echo "🎨 Rebuilding sprites..."
  bash "$ROOT_DIR/scripts/run_sprite_pipeline.sh"
fi

if [[ "$SKIP_PMTILES" -ne 1 ]]; then
  echo "🗺️ Building PMTiles..."
  bash "$ROOT_DIR/scripts/run_pmtiles_build.sh" --root "$DATA_ROOT" --out "$OUT_DIR"
fi

echo "🎨 Building Styles and Manifest..."
bash "$ROOT_DIR/scripts/run_style_build.sh" --root "$DATA_ROOT" --out "$OUT_DIR"

echo
echo "✨ All-in-one build complete! Output is in: $OUT_DIR"
