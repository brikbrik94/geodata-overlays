# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A build pipeline that turns a folder tree of GeoJSON files into a hostable MapLibre overlay bundle: vector tiles (`.pmtiles`), MapLibre `style.json` files, a sprite sheet, a `manifest.json`, and a `layer-list.json`. The output (`dist/`) is deployed to a tile server (e.g. `tiles.oe5ith.at`). The domain is Austrian emergency-services geodata (Rettungsdienst, Notarzthubschrauber, Bergrettung, zones, districts, roads).

This repo follows the **GEODATA_PLUGIN_STANDARD** (currently v1.4). The source GeoJSON lives in a **separate git repo** that is cloned into `data/geojson/` — it is not committed here. Comments, logs, and docs are predominantly in German; match that when editing.

## Entry points (the "Trinity")

- `setup.sh` — one-time setup: checks system deps, creates `dist/ work/ data/geojson/ logs/`, builds `.venv`, installs `scripts/requirements-sprite-tools.txt`, chmods scripts.
- `update.sh` — intelligent orchestrator: `git fetch` in `data/geojson/` and only runs a full build if upstream changed. Use this for routine rebuilds.
- `run.sh` — forces a full build: refreshes external data (`scripts/download.sh --refresh`) then runs `scripts/run_overlay_build.sh`.

`run_overlay_build.sh` is interactive (prompts for clean build / sprite rebuild) and chains the three stage scripts. To drive it non-interactively, pass flags: `--source external|custom`, `--root <path>`, `--out <path>`, `--clean yes|no`, `--sprites yes|no`, `--skip-pmtiles`.

Run a single stage directly:
```bash
scripts/run_pmtiles_build.sh  --root data/geojson --out dist   # GeoJSON -> dist/pmtiles
scripts/run_style_build.sh    --root data/geojson --out dist   # styles + manifest + layer-list
scripts/run_sprite_pipeline.sh                                  # sprites -> dist/assets/sprites
```
`--skip-pmtiles` builds only styles/manifest/sprites (no `tippecanoe` needed) — useful when iterating on styling.

## Pipeline architecture

The build has three independent stages, all reading the same `data/geojson/overlay_config.json`:

1. **PMTiles** (`scripts/pmtiles_builder.py`): converts each dataset's GeoJSON to a `.pmtiles` via `tippecanoe`. Applies pin-derivation logic (`derive_rd_pin`, `derive_nah_pin`) and zone coloring at tile-build time, injecting computed properties into features.
2. **Styles** (`scripts/build_styles.py`): the **orchestrator**. Loads the config, then for each dataset dispatches to a per-template builder module in `scripts/style_builders/` via a `template_map`. Each module exposes `build_style(dataset, args)` returning a slug; the orchestrator deletes any `*.style.json` no longer produced. After styles, `run_style_build.sh` also copies fonts and runs `generate_manifest.py` and `generate_layer_list.py`.
3. **Sprites** (`scripts/run_sprite_pipeline.sh` → `extract_sprite_icons.py` → `convert_sprite_svgs.py` → `build_ci_map_icons.py` → `build_sprites.py`): extracts icons from `*-pin-sprite.svg`, rasterizes, merges with the local SDF assets and the CI map-icons, and packs the combined `oe5ith-markers` sprite sheet.

### CI map-icons submodule (`vendor/oe5ith-ci`)

`git@github.com:brikbrik94/oe5ith-ci.git` is vendored as a git submodule at `vendor/oe5ith-ci`. Its `assets/map-icons/` is the source of truth for generic, single-color **SDF** shapes (`ci-pin`, `ci-bubble-label`, `ci-marker-*`, `ci-symbol-*`), described by `icons.json`. The sprite pipeline ingests these per that repo's "Builder-Vertrag" (`docs/map-icons.md`): `scripts/build_ci_map_icons.py` renders each SVG to a white-alpha PNG and emits a sidecar meta JSON; `build_sprites.py --meta` then writes `sdf:true` plus the `stretchX`/`stretchY`/`content` zones (scaled for `@2x`) into the sheet. Org-specific full-color icons (`rd-*`, `nef-*`, `nah-*`, `label-bubble*`) stay in this repo and coexist additively. `setup.sh` runs `git submodule update --init --recursive`; if the submodule is absent the CI step is skipped with a warning.

### Config-driven datasets

`scripts/config_parser.py` `load_repo_config()` reads `overlay_config.json` from the data repo root. Each dataset has `path`, `template`, optional `name`, and optional `options` (per-template overrides like `line_color`, `bubble_icon`, `text_color`, `color_fallback`). If the config is missing, a **legacy fallback** maps known folder names to templates by directory name.

### Templates (presets)

`template` values map to modules in `scripts/style_builders/`: `rd`, `nah`, `zonen`, `gebiete` (→ `build_bezirke.py`), `strassen`, `leitstellen`, `anfahrtszeit`, `linz-ag-linien`, `sonstiges`. To add a template: create the builder module with a `build_style()` function and register it in the `template_map` in `scripts/build_styles.py`. See `docs/repo-config-standard.md` for the per-template data/styling contract.

### Shared style constants

`scripts/style_builders/style_utils.py` holds the dark CI theme (`ACCENT=#3b82f6`, dark background), the kategorical `COLOR_PALETTE`, base-style scaffolding (`create_base_style`, `write_style`), and PMTiles source-URL construction. Change visual defaults here, not in individual builders.

## Conventions

- **Font stack must be exactly `Open-Sans-Regular`** (with hyphens) everywhere — glyph URLs depend on it.
- **All layer IDs / slugs / filenames are ASCII-sanitized** via `sanitize_name()` in `config_parser.py` (ä→ae, ö→oe, ü→ue, ß→ss, lowercase, non-alnum→`_`). Reuse it rather than re-implementing.
- Pin-derivation reads OSM-style properties (`emergency`, `ambulance_station:*`, `brand:short`, `operator`); see `docs/rd-pin-mapping.md` and `docs/nah-pin-mapping.md` for the org/operator → pin mappings.
- `scripts/ci/utils.sh` provides the `log_header/log_info/log_success/log_error` helpers sourced by every shell script (with inline fallbacks).
- `scripts/archive/` holds the superseded monolithic pipeline (`build_hosted_overlays.py` etc.) — kept for reference only; do not extend it. Note the README still documents this old flow and is partly outdated; GEMINI.md reflects the current modular pipeline.

## Dependencies

System tools (checked by `scripts/check_dependencies.sh`): `tippecanoe`, `git`, `python3` (+`venv`), `ogr2ogr` (GDAL). Python 3.9+. Sprite tooling deps are in `scripts/requirements-sprite-tools.txt`, installed into `.venv` by `setup.sh`.

## Local preview

`tools/test_overlay_server.py` serves a MapLibre viewer (`tools/viewer/`) over a built bundle, rewriting PMTiles URLs to local paths and supporting byte-range requests:
```bash
scripts/run_overlay_build.sh --skip-pmtiles   # or a full build
python3 tools/test_overlay_server.py --bundle-dir dist --host 127.0.0.1 --port 8000
```

## Output layout (`dist/`)

`pmtiles/` (vector tiles, mirrors source folder structure), `styles/*.style.json`, `manifest.json`, `layer-list.json` (layers grouped logically by source, enriched with legend metadata: layer type, color(s), opacity, categorical items), `assets/` (sprites + fonts).
