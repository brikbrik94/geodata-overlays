#!/usr/bin/env bash
set -euo pipefail

# --- KONFIGURATION ---
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="$ROOT_DIR/scripts"

# CI Utils laden
if [ -f "$SCRIPT_DIR/ci/utils.sh" ]; then
    source "$SCRIPT_DIR/ci/utils.sh"
else
    log_header() { echo -e "\n=== $1 ===\n"; }
    log_info() { echo -e "  ℹ $1"; }
    log_success() { echo -e "  ✔ $1"; }
    log_error() { echo -e "  ✖ $1"; }
fi

log_header "OVERLAY PIPELINE UPDATE"

log_info "Starte Overlay Build Prozess..."
if bash "$SCRIPT_DIR/run_overlay_build.sh" --source external --clean yes --sprites yes "$@"; then
    log_success "Build erfolgreich abgeschlossen. Artefakte sind in dist/"
else
    log_error "Build fehlgeschlagen."
    exit 1
fi
