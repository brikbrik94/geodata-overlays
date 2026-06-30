# Build-Run JSONL-Logging — Design

**Datum:** 2026-06-30
**Status:** Entschieden
**Scope:** `update.sh`, `scripts/run_overlay_build.sh`, neuer Helper `scripts/ci/run_logger.sh`, Registrierung in `/opt/log-api/config.yaml`

## Problem

Die Build-Pipeline (`update.sh` → `run.sh` → `run_overlay_build.sh`) hinterlässt keinen
strukturierten, maschinenlesbaren Lauf-Status. Ob ein Lauf funktioniert hat, ist nur aus
dem flüchtigen Terminal-Output ersichtlich. Auf demselben Host existiert bereits ein
JSONL-Logging-Ökosystem (Overpass-Updater + zentrale `log-api`), in das sich die Pipeline
einreihen soll.

### Bestehendes Vorbild (Overpass)

`/mnt/geodata/overpass/bin/update_hourly.sh` und `update_areas.sh` schreiben nach jedem Lauf:

- eine **Status-Datei** (`*_status.json`, atomar via `.tmp` + `mv`) — der jeweils letzte Zustand
- eine **History-Zeile** (`*_history.jsonl`, append) — eine JSON-Zeile pro Lauf

Realisiert über einen `trap finalize EXIT`, der **immer** schreibt: Default-Status `error`
(„Unerwarteter Abbruch"), auf den Erfolgspfaden auf `ok`/`up_to_date` gesetzt. Felder u.a.
`timestamp`, `status`, `duration_seconds`, `message`, `error`.

Die `log-api` (`/opt/log-api/config.yaml`) liest solche Quellen mit `ts_field`/`level_field`/
`message_field` und optionalem `interval` (→ `state=ok` solange jünger als `interval`, sonst
`stale`).

## Entscheidung

**Zwei getrennte JSONL-Quellen**, gespeist über **einen gemeinsamen Shell-Helper**, plus
Registrierung beider Quellen in der `log-api`. Das Overpass-Muster wird übernommen, aber die
Trap-/JSON-Logik **einmal** in einen wiederverwendbaren Helper gefaktet (statt wie bei
Overpass pro Script dupliziert).

| Quelle | Datei (History) | Status-Datei | Geschrieben von | interval |
| :-- | :-- | :-- | :-- | :-- |
| A — Update-Check | `/var/log/geodata_overlays_update_history.jsonl` | `…_update_status.json` | `update.sh` | `1d` |
| B — Build | `/var/log/geodata_overlays_build_history.jsonl` | `…_build_status.json` | `run_overlay_build.sh` | — (event-getrieben) |

Der Cron-Eintrag für den regelmäßigen `update.sh`-Lauf wird **vom Betreiber separat**
hinzugefügt (nicht Teil dieser Umsetzung). `interval: 1d` für Quelle A ist darauf ausgelegt.

## Komponenten

### 1. Helper `scripts/ci/run_logger.sh` (neu)

Pure-bash, sourcebar; fügt sich in die bestehende `scripts/ci/utils.sh`-Konvention ein
(nutzt deren `log_warn`/`log_info`, mit Inline-Fallback wenn nicht geladen). Bewusst portabel
gehalten (keine bash-4-only-Konstrukte), obwohl alle aktuellen Aufrufer bash sind.

**Öffentliche API:**

```sh
run_log_init <history_basename> <status_basename>
    # Merkt START_EPOCH; setzt Defaults RUN_LOG_STATUS=error,
    # RUN_LOG_ERROR="Unerwarteter Abbruch des Scripts.", leeres Extra-Feld-Set;
    # registriert  trap run_log_finalize EXIT.
    # Dateipfade = "${GEODATA_LOG_DIR:-/var/log}/<basename>".

run_log_str <key> <value>   # fügt  "key":"escaped-value"  zur Zeile hinzu
run_log_num <key> <value>   # fügt  "key":value  hinzu (leer → null)
run_log_raw <key> <json>    # fügt  "key":<json>  hinzu (z.B. Arrays wie ["pmtiles",…])

run_log_finalize
    # Wird vom EXIT-Trap aufgerufen (nicht manuell nötig).
    # 1. rc=$?  zuerst sichern → Exit-Code des Scripts bleibt unverändert.
    # 2. duration_seconds = jetzt − START_EPOCH.
    # 3. Baut JSON: Basisfelder + alle via run_log_* gesetzten Extras.
    # 4. Status-Datei atomar schreiben (.tmp + mv), History-Zeile appenden.
    # 5. Alle Schreibvorgänge best-effort: Fehler → log_warn, niemals Abbruch.
    # 6. return $rc.
```

**Vom Aufrufer gesetzte Variablen** (vor regulärem Ende):
`RUN_LOG_STATUS`, `RUN_LOG_MESSAGE`, `RUN_LOG_ERROR` (leer/`""` → JSON `null`).

**Basisfelder jeder Zeile** (immer, in dieser Reihenfolge zuerst):
`timestamp` (UTC `%Y-%m-%dT%H:%M:%SZ`), `status`, `duration_seconds`, danach die Extras,
dann `message`, `error`.

**JSON-Escaping:** `\` und `"` escapen, `\n`/`\t` → Space (wie Overpass `json_escape`).

**Best-effort / Berechtigungen:** Default-Log-Dir `/var/log` erfordert i.d.R. root (Cron).
Bei manuellem non-root-Lauf scheitert der Write → `log_warn`, Script läuft normal weiter.
`GEODATA_LOG_DIR` erlaubt Umleitung (Tests, Entwicklung).

### 2. Quelle A — `update.sh`

`run_log_init geodata_overlays_update_history.jsonl geodata_overlays_update_status.json`
direkt nach dem Sourcing der CI-Utils. Status je Zweig:

| Situation | `RUN_LOG_STATUS` | `RUN_LOG_MESSAGE` | `RUN_LOG_ERROR` |
| :-- | :-- | :-- | :-- |
| Kein git-Repo in `data/geojson` | `build_triggered` | „Kein git-Repo, Force-Build." | `""` |
| `LOCAL != UPSTREAM` | `build_triggered` | „Update erkannt (`<local7>`→`<upstream7>`), Build gestartet." | `""` |
| `LOCAL == UPSTREAM` | `up_to_date` | „Keine Updates, Build übersprungen." | `""` |
| Triggered Build (`run.sh`) schlägt fehl | `error` | „Build fehlgeschlagen." | „run.sh exit non-zero" |
| git-Fehler / unerwarteter Abbruch | `error` (Default) | (Default) | (Default) |

Quelle A protokolliert das Ergebnis des Update-Checks **inkl. des Triggered-Build-Ausgangs**:
Wird ein Build getriggert, wird `run.sh` so aufgerufen, dass ein Fehlschlag erkannt wird
(`if ! bash run.sh …`) und `RUN_LOG_STATUS=error` setzt, bevor `update.sh` non-zero endet.
Bei Erfolg bleibt der Status `build_triggered`. Die **detaillierten** Build-Metriken
(Stages, datasets, …) liegen weiterhin ausschließlich in Quelle B.

### 3. Quelle B — `scripts/run_overlay_build.sh`

`run_log_init geodata_overlays_build_history.jsonl geodata_overlays_build_status.json`
nach dem Flag-Parsing (Zeile ~120, nachdem `SOURCE_MODE`/`CLEAN_MODE`/`REBUILD_SPRITES`/
Skip-PMTiles feststehen). Felder:

```sh
run_log_str source  "$SOURCE_MODE"          # external | custom
run_log_raw clean   "$([[ clean ]] && echo true || echo false)"
# stages-Array aus den effektiven Flags zusammensetzen:
#   sprites   (nur wenn REBUILD_SPRITES aktiv)
#   pmtiles   (außer bei --skip-pmtiles)
#   styles    (immer)
run_log_raw stages  '["sprites","pmtiles","styles"]'   # gefiltert
```

`CURRENT_STAGE` wird vor jedem Stage-Aufruf gesetzt (`sprites`/`pmtiles`/`styles`); bricht
eine Stage ab (`set -e` → EXIT-Trap), nennt `run_log_finalize` über
`RUN_LOG_ERROR`/`RUN_LOG_MESSAGE` die fehlgeschlagene Stage. Bei vollständigem Durchlauf:

```sh
RUN_LOG_STATUS="ok"
run_log_num datasets "$(dataset_count)"   # aus dist/manifest.json (len .datasets)
RUN_LOG_MESSAGE="Build erfolgreich (<datasets> Datasets, Stages: …)."
```

`dataset_count` liest `dist/manifest.json` und zählt `.datasets` (Feld existiert bereits).
Schlägt das Lesen fehl (z.B. `--skip-pmtiles` ohne Manifest), wird `datasets` zu `null`.

### Beispiel-Zeilen

Quelle A:
```json
{"timestamp":"2026-06-30T06:30:00Z","status":"up_to_date","duration_seconds":2,"message":"Keine Updates, Build übersprungen.","error":null}
```
Quelle B:
```json
{"timestamp":"2026-06-30T06:35:12Z","status":"ok","duration_seconds":418,"source":"external","clean":false,"stages":["pmtiles","styles"],"datasets":14,"message":"Build erfolgreich (14 Datasets, Stages: pmtiles, styles).","error":null}
```

### 4. log-api-Registrierung (`/opt/log-api/config.yaml`)

Zwei Sources anhängen (Format identisch zu den bestehenden Overpass-Einträgen):

```yaml
- id: geodata-overlays-update
  label: Geodata-Overlays Update-Check
  path: /var/log/geodata_overlays_update_history.jsonl*
  format: jsonl
  ts_field: timestamp
  level_field: status
  message_field: message
  interval: 1d

- id: geodata-overlays-build
  label: Geodata-Overlays Build
  path: /var/log/geodata_overlays_build_history.jsonl*
  format: jsonl
  ts_field: timestamp
  level_field: status
  message_field: message
  # kein interval: event-getrieben (Build läuft nur bei Upstream-Änderung)
```

Danach `log-api` neu laden (systemd-Service) und prüfen, dass beide Sources erscheinen.
`level_field: status` — der einzige „schlechte" Wert ist `error`; `ok`/`up_to_date`/
`build_triggered` sind unkritisch.

## Nicht im Scope (YAGNI)

- Cron-Eintrag für `update.sh` (Betreiber fügt selbst hinzu).
- „Reiche" Build-Metriken (Output-Größen, Sprite/Icon-Zähler, Per-Stage-Dauer).
- Log-Rotation (`path`-Glob `*` deckt rotierte Dateien bereits ab; Rotation selbst regelt
  ggf. logrotate, nicht diese Umsetzung).
- Änderungen an `run.sh` (reiner Pass-Through zu `run_overlay_build.sh`; kein eigener Log).

## Testing

**Helper-Unit** (mit `GEODATA_LOG_DIR=<tmp>`):
- Dummy-Aufruf mit `RUN_LOG_STATUS=ok` + Extras → genau eine History-Zeile, valides JSON,
  erwartete Felder/Typen (`duration_seconds` Zahl, `clean` bool, `stages` Array).
- Status-Datei existiert und enthält dieselbe Zeile; zweiter Lauf überschreibt sie (kein Append).
- Read-only Log-Dir → `log_warn`, Exit-Code des Aufrufers unverändert (kein Abbruch).
- Default-Pfad ohne Erfolgssetzung → `status=error` (Trap-Default greift).

**Integration:**
- `update.sh` bei `LOCAL==UPSTREAM` (gemockt) → `up_to_date`-Zeile in Quelle A.
- `run_overlay_build.sh --source external --skip-pmtiles --clean no --sprites no` →
  Build-Zeile mit `stages` **ohne** `pmtiles`, `source=external`, `clean=false`.

## Offene Verifikationspunkte (bei Umsetzung)

- log-api-Reload-Mechanismus bestätigen (systemd-Unit-Name) und nach dem Edit ausführen.
- Sicherstellen, dass der EXIT-Trap in `run_overlay_build.sh` nicht mit einem bereits
  vorhandenen Trap kollidiert (aktuell keiner vorhanden — verifizieren).
