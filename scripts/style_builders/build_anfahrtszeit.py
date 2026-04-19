#!/usr/bin/env python3
import argparse, os, json, re, copy
from pathlib import Path
from style_builders.style_utils import create_base_style, build_pmtiles_source_url, write_style, geometry_filter, DEFAULT_FONT_STACK
from config_parser import sanitize_name

def add_anfahrtszeit_layer(style, source_layer, source_id):
    base_id = f"{source_id}-{source_layer}"
    
    # Categorical Color Ramp (Grün -> Rot)
    # Nutzt 'AA_MINS' aus den GeoJSON Properties
    expr = ["match", ["get", "AA_MINS"]]
    mapping = {
        15: "#10b981", # Grün
        30: "#84cc16", # Hellgrün
        45: "#f59e0b", # Gelb/Orange
        60: "#f97316", # Orange
        75: "#ef4444", # Rot
        90: "#b91c1c"  # Dunkelrot
    }
    for k, v in mapping.items():
        expr.extend([k, v])
    expr.append("#3b82f6") # Fallback (Blau)
    
    # Fill Layer
    style["layers"].append({
        "id": f"{base_id}-fill",
        "type": "fill",
        "source": source_id,
        "source-layer": source_layer,
        "filter": geometry_filter("Polygon", "MultiPolygon"),
        "paint": {
            "fill-color": expr,
            "fill-opacity": 0.4,
            "fill-outline-color": "#ffffff"
        }
    })
    
    # Label Layer
    style["layers"].append({
        "id": f"{base_id}-labels",
        "type": "symbol",
        "source": source_id,
        "source-layer": source_layer,
        "filter": geometry_filter("Polygon", "MultiPolygon"),
        "layout": {
            "text-field": ["concat", ["to-string", ["get", "AA_MINS"]], " Min"],
            "text-font": DEFAULT_FONT_STACK,
            "text-size": 11,
            "text-allow-overlap": False
        },
        "paint": {
            "text-color": "#ffffff",
            "text-halo-color": "#000000",
            "text-halo-width": 1
        }
    })

def build_style(dataset_config, args):
    rel_path = Path(dataset_config["path"])
    full_path = Path(args.root) / rel_path
    
    slug = "-".join(sanitize_name(p).replace("_", "-") for p in rel_path.parts)
    safe_rel_path = Path(*(sanitize_name(p).replace("_", "-") for p in rel_path.parts))
    pmtiles_rel = f"pmtiles/{slug}.pmtiles"
    pmtiles_url = build_pmtiles_source_url(args.base_url, pmtiles_rel)
    
    style = create_base_style(f"OE5ITH {dataset_config['name']}", pmtiles_url, args.sprite_url, args.glyphs_url, slug)
    style["metadata"]["folder"] = dataset_config["name"]
    
    geojsons = list(full_path.glob("*.geojson"))
    for g in sorted(geojsons):
        layer_name = g.stem
        source_layer = sanitize_name(layer_name)
        add_anfahrtszeit_layer(style, source_layer, slug)
        
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
        "template": "anfahrtszeit"
    }
    build_style(dataset_config, args)
