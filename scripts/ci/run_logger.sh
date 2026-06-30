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
