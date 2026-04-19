#!/usr/bin/env python3
import argparse, os, json, re
from pathlib import Path
from style_builders.style_utils import create_base_style, build_pmtiles_source_url, write_style, geometry_filter, DEFAULT_FONT_STACK
from config_parser import sanitize_name

def add_rd_point_layer(style, source_layer, source_id):
    base_id = f"{source_id}-{source_layer}"
    
    # Symbol Layer (Pins)
    style["layers"].append({
        "id": f"{base_id}-symbols",
        "type": "symbol",
        "source": source_id,
        "source-layer": source_layer,
        "filter": geometry_filter("Point", "MultiPoint"),
        "layout": {
            "icon-image": ["coalesce", ["get", "pin"], "fallback-pin"],
            "icon-size": ["interpolate", ["linear"], ["zoom"], 6, 0.35, 12, 0.65],
            "icon-anchor": "bottom",
            "icon-allow-overlap": True,
            "icon-ignore-placement": True,
            "icon-padding": 0
        }
    })
    
    # Text Layer (SDF Bubble, feld 'alt_name' unter dem Pin)
    style["layers"].append({
        "id": f"{base_id}-text",
        "type": "symbol",
        "source": source_id,
        "source-layer": source_layer,
        "filter": ["all",
            geometry_filter("Point", "MultiPoint"),
            ["has", "alt_name"],
            ["!=", ["get", "alt_name"], ""]
        ],
        "layout": {
            "text-field": ["get", "alt_name"],
            "text-size": ["interpolate", ["linear"], ["zoom"], 6, 9.5, 12, 11],
            "text-font": DEFAULT_FONT_STACK,
            "text-variable-anchor": ["top"],
            "text-radial-offset": 1.5,
            "text-allow-overlap": True,
            "text-ignore-placement": True,
            "text-optional": False,
            "icon-image": "label-bubble",
            "icon-anchor": "top",
            "icon-text-fit": "both",
            "icon-text-fit-padding": [1, 3, 1, 3],
            "icon-allow-overlap": True,
            "icon-ignore-placement": True,
            "icon-optional": True
        },
        "paint": {
            "text-color": "#111827",
            "icon-opacity": 0.95
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
        add_rd_point_layer(style, source_layer, slug)
        
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
        "template": "rd"
    }
    build_style(dataset_config, args)
