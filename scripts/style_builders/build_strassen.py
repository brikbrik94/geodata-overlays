#!/usr/bin/env python3
import argparse, os, json, re
from pathlib import Path
from style_builders.style_utils import create_base_style, build_pmtiles_source_url, write_style, geometry_filter, DEFAULT_FONT_STACK
from config_parser import sanitize_name

def add_strassen_line_layers(style, source_layer, source_id, options):
    base_id = f"{source_id}-{source_layer}"
    line_color = options.get("line_color", "#888888")
    
    # Filter for proposed/construction roads
    is_proposed_filter = ["any",
        ["match", ["coalesce", ["get", "highway"], ["get", "Highway"], ""], ["proposed", "construction"], True, False],
        ["has", "proposed"],
        ["has", "construction"],
        ["==", ["get", "construction"], "yes"],
        ["==", ["get", "proposed"], "yes"]
    ]
    
    # Normal Line Layer
    style["layers"].append({
        "id": f"{base_id}-line",
        "type": "line",
        "source": source_id,
        "source-layer": source_layer,
        "filter": ["all",
            geometry_filter("LineString", "MultiLineString"),
            ["!", is_proposed_filter]
        ],
        "paint": {
            "line-color": line_color,
            "line-width": ["interpolate", ["linear"], ["zoom"], 6, 1, 12, 3],
            "line-opacity": 0.8
        }
    })

    # Proposed/Construction Line Layer (Dashed & Transparent)
    style["layers"].append({
        "id": f"{base_id}-line-proposed",
        "type": "line",
        "source": source_id,
        "source-layer": source_layer,
        "filter": ["all",
            geometry_filter("LineString", "MultiLineString"),
            is_proposed_filter
        ],
        "paint": {
            "line-color": line_color,
            "line-width": ["interpolate", ["linear"], ["zoom"], 6, 1, 12, 3],
            "line-opacity": 0.4,
            "line-dasharray": [3, 2]
        }
    })

def add_strassen_label_layers(style, source_layer, source_id, options):
    base_id = f"{source_id}-{source_layer}"
    bubble_icon = options.get("bubble_icon", "label-bubble")
    text_color = options.get("text_color", "#ffffff")
    
    is_proposed_filter = ["any",
        ["match", ["coalesce", ["get", "highway"], ["get", "Highway"], ""], ["proposed", "construction"], True, False],
        ["has", "proposed"],
        ["has", "construction"],
        ["==", ["get", "construction"], "yes"],
        ["==", ["get", "proposed"], "yes"]
    ]
    
    # Label Layer (Shields)
    style["layers"].append({
        "id": f"{base_id}-labels",
        "type": "symbol",
        "source": source_id,
        "source-layer": source_layer,
        "filter": ["all",
            geometry_filter("LineString", "MultiLineString"),
            ["has", "ref"]
        ],
        "layout": {
            "text-field": ["get", "ref"],
            "text-font": DEFAULT_FONT_STACK,
            "text-size": 10,
            "icon-image": bubble_icon,
            "icon-text-fit": "both",
            "icon-text-fit-padding": [1, 2, 1, 2],
            "symbol-placement": "line",
            "symbol-spacing": 200,
            "text-allow-overlap": False,
            "icon-allow-overlap": False
        },
        "paint": {
            "text-color": text_color,
            "icon-opacity": ["case", is_proposed_filter, 0.5, 1.0],
            "text-opacity": ["case", is_proposed_filter, 0.5, 1.0]
        }
    })

def build_style(dataset_config, args):
    rel_path = Path(dataset_config["path"])
    full_path = Path(args.root) / rel_path
    options = dataset_config.get("options", {})
    
    slug = "-".join(sanitize_name(p).replace("_", "-") for p in rel_path.parts)
    pmtiles_rel = f"pmtiles/{slug}.pmtiles"
    pmtiles_url = build_pmtiles_source_url(args.base_url, pmtiles_rel)
    
    style = create_base_style(f"OE5ITH {dataset_config['name']}", pmtiles_url, args.sprite_url, args.glyphs_url, slug)
    style["metadata"]["folder"] = dataset_config["name"]
    
    geojsons = sorted(list(full_path.glob("*.geojson")))
    
    # First loop: Add all line layers (background)
    for g in geojsons:
        layer_name = g.stem
        source_layer = sanitize_name(layer_name)
        add_strassen_line_layers(style, source_layer, slug, options)
        
    # Second loop: Add all label layers (foreground)
    # This ensures labels are always on top of all lines
    for g in geojsons:
        layer_name = g.stem
        source_layer = sanitize_name(layer_name)
        # Sonderfall: Autobahnauffahrten haben keine Labels (A1 Schilder)
        if source_layer != "autobahnauffahrten":
            add_strassen_label_layers(style, source_layer, slug, options)
        
    write_style(Path(args.out) / "styles" / f"{slug}.style.json", style)
    return slug

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--sprite-url", default="../assets/sprites/oe5ith-markers/sprite")
    parser.add_argument("--glyphs-url", default="https://tiles.oe5ith.at/assets/fonts/{fontstack}/{range}.pbf")
    parser.add_argument("--path", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    
    dataset_config = {
        "path": args.path,
        "name": args.name,
        "template": "strassen"
    }
    build_style(dataset_config, args)
