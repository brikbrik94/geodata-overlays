#!/usr/bin/env python3
import argparse, os, json, re, copy
from pathlib import Path
from style_builders.style_utils import create_base_style, build_pmtiles_source_url, write_style, geometry_filter
from config_parser import sanitize_name

def add_zonen_layer(style, source_layer, source_id):
    base_id = f"{source_id}-{source_layer}"
    
    # Wir nutzen die vom pmtiles_builder injizierte 'color' Eigenschaft.
    # Falls diese fehlt (z.B. bei alten Tiles), nutzen wir ein Fallback.
    fill_color = ["coalesce", ["get", "color"], "#3b82f6"]

    # Fill Layer
    style["layers"].append({
        "id": f"{base_id}-fill",
        "type": "fill",
        "source": source_id,
        "source-layer": source_layer,
        "filter": geometry_filter("Polygon", "MultiPolygon"),
        "paint": {
            "fill-color": fill_color,
            "fill-opacity": 0.35,
            "fill-outline-color": "#ffffff"
        }
    })
    
    # Outline Layer
    style["layers"].append({
        "id": f"{base_id}-line",
        "type": "line",
        "source": source_id,
        "source-layer": source_layer,
        "filter": geometry_filter("Polygon", "MultiPolygon"),
        "paint": {
            "line-color": "#ffffff",
            "line-width": 1,
            "line-opacity": 0.5
        }
    })

def build_style(dataset_config, args):
    rel_path = Path(dataset_config["path"])
    
    slug = "-".join(sanitize_name(p).replace("_", "-") for p in rel_path.parts)
    pmtiles_rel = f"pmtiles/{slug}.pmtiles"
    pmtiles_url = build_pmtiles_source_url(args.base_url, pmtiles_rel)
    
    style = create_base_style(f"OE5ITH {dataset_config['name']}", pmtiles_url, args.sprite_url, args.glyphs_url, slug)
    style["metadata"]["folder"] = dataset_config["name"]
    
    # Wir müssen hier nicht mehr die Files durchsuchen um Mappings zu bauen,
    # da die Farben bereits in den Vektortiles enthalten sind.
    # Wir nehmen an, dass die Source-Layers den GeoJSON-Dateinamen entsprechen.
    # Da wir aber die GeoJSONs kennen, loopen wir trotzdem drüber um die Layer anzulegen.
    full_path = Path(args.root) / rel_path
    geojsons = list(full_path.glob("*.geojson"))
    for g in sorted(geojsons):
        layer_name = g.stem
        source_layer = sanitize_name(layer_name)
        add_zonen_layer(style, source_layer, slug)
        
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
        "template": "zonen"
    }
    build_style(dataset_config, args)
