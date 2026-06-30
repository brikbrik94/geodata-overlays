#!/usr/bin/env bash
set -euo pipefail

# --- CONFIGURATION ---
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="$ROOT_DIR/scripts"
GEOJSON_DIR="$ROOT_DIR/data/geojson"

# Load CI Utils
if [ -f "$SCRIPT_DIR/ci/utils.sh" ]; then
    source "$SCRIPT_DIR/ci/utils.sh"
else
    log_header() { echo -e "\n=== $1 ===\n"; }
    log_info() { echo -e "  ℹ $1"; }
    log_success() { echo -e "  ✔ $1"; }
    log_error() { echo -e "  ✖ $1"; }
fi

# Load Run-Logger (best-effort jsonl logging)
if [ -f "$SCRIPT_DIR/ci/run_logger.sh" ]; then
    source "$SCRIPT_DIR/ci/run_logger.sh"
    run_log_init geodata_overlays_update_history.jsonl geodata_overlays_update_status.json
fi

log_header "INTELLIGENT UPDATE CHECK"

# Check if data/geojson exists and is a git repository
if [ ! -d "$GEOJSON_DIR/.git" ]; then
    log_info "GeoJSON directory not found or not a git repository. Forcing update."
    RUN_LOG_STATUS="build_triggered"; RUN_LOG_MESSAGE="Kein git-Repo, Force-Build."; RUN_LOG_ERROR=""
    bash "$ROOT_DIR/run.sh" "$@"
    exit 0
fi

# Go to data/geojson
cd "$GEOJSON_DIR"

log_info "Fetching latest changes in $GEOJSON_DIR..."
git fetch --quiet

LOCAL=$(git rev-parse HEAD)
UPSTREAM=$(git rev-parse @{u})

if [ "$LOCAL" != "$UPSTREAM" ]; then
    log_info "Update detected (Local: $LOCAL, Upstream: $UPSTREAM). Starting build."
    RUN_LOG_STATUS="build_triggered"
    RUN_LOG_MESSAGE="Update erkannt (${LOCAL:0:7}->${UPSTREAM:0:7}), Build gestartet."
    RUN_LOG_ERROR=""
    cd "$ROOT_DIR"
    bash "$ROOT_DIR/run.sh" "$@"
else
    log_success "No updates found. Skipping build."
    RUN_LOG_STATUS="up_to_date"; RUN_LOG_MESSAGE="Keine Updates, Build uebersprungen."; RUN_LOG_ERROR=""
    exit 0
fi
