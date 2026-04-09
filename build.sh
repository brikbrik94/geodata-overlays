#!/usr/bin/env bash
set -euo pipefail

# Build-Skript für den Plugin-Standard
# Führt die gesamte Pipeline nicht-interaktiv aus

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting full build for Plugin-Standard..."

# Wir führen den Build mit Standardeinstellungen aus:
# --source external: Nutzt die Daten aus external/geojson-data
# --clean yes: Löscht dist/ vorher
# --sprites yes: Baut die Sprites neu
bash "$ROOT_DIR/scripts/run_overlay_build.sh" --source external --clean yes --sprites yes "$@"

echo "✅ Full build complete. Artefacts are in dist/"
