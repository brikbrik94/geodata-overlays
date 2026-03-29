#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="${ROOT_DIR}/.venv/bin/python"
INPUT_SVG=""
WORK_DIR="${ROOT_DIR}/assets/sprites/work"
DIST_DIR="${ROOT_DIR}/dist/assets/sprites"

usage() {
  cat <<USAGE
Usage: $(basename "$0") --input <preview.svg> [--work-dir <dir>] [--dist-dir <dir>] [--provider-map <json>]
USAGE
}

PROVIDER_MAP=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT_SVG="$2"; shift 2 ;;
    --work-dir) WORK_DIR="$2"; shift 2 ;;
    --dist-dir) DIST_DIR="$2"; shift 2 ;;
    --provider-map) PROVIDER_MAP="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 2 ;;
  esac
done

if [[ -z "$INPUT_SVG" ]]; then
  echo "Missing --input" >&2
  usage
  exit 2
fi

if [[ ! -x "$VENV_PY" ]]; then
  echo "Local .venv not found. Running dependency installer..."
  bash "$ROOT_DIR/scripts/install_python_deps.sh"
fi

EXTRACT_DIR="$WORK_DIR/extracted"
PNG_DIR="$WORK_DIR/png"
mkdir -p "$EXTRACT_DIR" "$PNG_DIR" "$DIST_DIR"

EXTRACT_CMD=("$VENV_PY" "$ROOT_DIR/scripts/extract_sprite_icons.py" --input "$INPUT_SVG" --out "$EXTRACT_DIR" --provider-names)
if [[ -n "$PROVIDER_MAP" ]]; then
  EXTRACT_CMD+=(--provider-map "$PROVIDER_MAP")
fi
"${EXTRACT_CMD[@]}"

"$VENV_PY" "$ROOT_DIR/scripts/convert_sprite_svgs.py" --source "$EXTRACT_DIR" --out "$PNG_DIR"
"$VENV_PY" "$ROOT_DIR/scripts/build_sprites.py" --source "$PNG_DIR" --manifest "$PNG_DIR/icons.manifest.json" --out "$DIST_DIR"

echo "Done. Sprites written to: $DIST_DIR"
