#!/usr/bin/env python3
import argparse, os, json, re, copy
from pathlib import Path
from style_builders.style_utils import create_base_style, build_pmtiles_source_url, write_style, geometry_filter, DEFAULT_FONT_STACK
from config_parser import sanitize_name

def add_linz_ag_layer(style, source_layer, source_id):
    base_id = f"{source_id}-{source_layer}"
    
    # Mapping aus linien.json
    # Wir matchen den source_layer (z.B. "linie_1", "linie_11")
    line_num_match = re.search(r"linie_([a-z0-9]+)", source_layer)
    line_key = line_num_match.group(1) if line_num_match else source_layer.replace("linie_", "")
    
    mapping = {
        "1": {"color": "#E61E58", "width": 4},
        "2": {"color": "#BDA5D9", "width": 4},
        "3": {"color": "#5B1A80", "width": 4},
        "4": {"color": "#E11E26", "width": 4},
        "50": {"color": "#0BA34A", "width": 4},
        "11": {"color": "#F39C12", "width": 3},
        "12": {"color": "#2ECC71", "width": 3},
        "17": {"color": "#F1C40F", "width": 3},
        "18": {"color": "#3498DB", "width": 3},
        "19": {"color": "#E74C3C", "width": 3},
        "25": {"color": "#D4A86F", "width": 3},
        "26": {"color": "#2C82C9", "width": 3},
        "27": {"color": "#27AE60", "width": 3},
        "33": {"color": "#E6B0AA", "width": 3},
        "33a": {"color": "#AF7AC5", "width": 3},
        "38": {"color": "#D35400", "width": 3},
        "41": {"color": "#C0392B", "width": 3},
        "43": {"color": "#1C6EA4", "width": 3},
        "45": {"color": "#A93226", "width": 3},
        "45a": {"color": "#F1948A", "width": 3},
        "46": {"color": "#5DADE2", "width": 3},
        "70": {"color": "#3498DB", "width": 3},
        "71": {"color": "#3498DB", "width": 3},
        "72": {"color": "#3498DB", "width": 3},
        "73": {"color": "#3498DB", "width": 3},
        "77": {"color": "#3498DB", "width": 3}
    }
    
    # Fallback-Logik für Kategorien
    if line_key in mapping:
        spec = mapping[line_key]
    elif line_key.startswith("n"): # Nachtlinien
        spec = {"color": "#111827", "width": 2}
    elif line_key.isdigit() and int(line_key) >= 100: # Regionalbusse / 100er
        spec = {"color": "#8B5A2B", "width": 2} # Schnellbus/Regionalbraun
    else:
        spec = {"color": "#888888", "width": 2}
    
    # Line Layer
    style["layers"].append({
        "id": f"{base_id}-line",
        "type": "line",
        "source": source_id,
        "source-layer": source_layer,
        "filter": geometry_filter("LineString", "MultiLineString"),
        "paint": {
            "line-color": spec["color"],
            "line-width": ["interpolate", ["linear"], ["zoom"], 10, spec["width"]*0.5, 14, spec["width"]],
            "line-opacity": 0.9
        }
    })
    
    # Label Layer
    style["layers"].append({
        "id": f"{base_id}-labels",
        "type": "symbol",
        "source": source_id,
        "source-layer": source_layer,
        "layout": {
            "text-field": line_key.upper(),
            "text-font": DEFAULT_FONT_STACK,
            "text-size": 10,
            "symbol-placement": "line",
            "text-allow-overlap": False
        },
        "paint": {
            "text-color": "#ffffff",
            "text-halo-color": spec["color"],
            "text-halo-width": 2
        }
    })

def build_style(dataset_config, args):
    rel_path = Path(dataset_config["path"])
    full_path = Path(args.root) / rel_path
    
    slug = "-".join(sanitize_name(p).replace("_", "-") for p in rel_path.parts)
    pmtiles_rel = f"pmtiles/{slug}.pmtiles"
    pmtiles_url = build_pmtiles_source_url(args.base_url, pmtiles_rel)
    
    style = create_base_style(f"OE5ITH {dataset_config['name']}", pmtiles_url, args.sprite_url, args.glyphs_url, slug)
    style["metadata"]["folder"] = dataset_config["name"]
    
    geojsons = list(full_path.glob("*.geojson"))
    for g in sorted(geojsons):
        layer_name = g.stem
        source_layer = sanitize_name(layer_name)
        add_linz_ag_layer(style, source_layer, slug)
        
    write_style(Path(args.out) / "styles" / f"{slug}.style.json", style)
    return slug
