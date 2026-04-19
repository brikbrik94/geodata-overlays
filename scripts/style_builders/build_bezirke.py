#!/usr/bin/env python3
import argparse, os, json, re
from pathlib import Path
from style_builders.style_utils import create_base_style, build_pmtiles_source_url, write_style, geometry_filter, DEFAULT_FONT_STACK
from config_parser import sanitize_name

def add_gebiete_layer(style, source_layer, source_id):
    base_id = f"{source_id}-{source_layer}"
    
    # Umriss Layer
    style["layers"].append({
        "id": f"{base_id}-outline",
        "type": "line",
        "source": source_id,
        "source-layer": source_layer,
        "filter": geometry_filter("Polygon", "MultiPolygon"),
        "paint": {
            "line-color": "#3b82f6",
            "line-width": ["interpolate", ["linear"], ["zoom"], 6, 1, 12, 2.5],
            "line-opacity": 0.8
        }
    })
    
    # Label Layer (Zentroid-basiert)
    style["layers"].append({
        "id": f"{base_id}-labels",
        "type": "symbol",
        "source": source_id,
        "source-layer": source_layer,
        "filter": geometry_filter("Polygon", "MultiPolygon"),
        "layout": {
            "text-field": ["get", "name"],
            "text-font": ["Open-Sans-Bold"],
            "text-size": ["interpolate", ["linear"], ["zoom"], 6, 11, 12, 16],
            "text-anchor": "center",
            "text-allow-overlap": False,
            "text-padding": 5
        },
        "paint": {
            "text-color": "#ffffff",
            "text-halo-color": "#000000",
            "text-halo-width": 2
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
        add_gebiete_layer(style, source_layer, slug)
        
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
        "template": "gebiete"
    }
    build_style(dataset_config, args)
