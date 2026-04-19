#!/usr/bin/env python3
import argparse, os, json, re, copy
from pathlib import Path
from style_builders.style_utils import create_base_style, build_pmtiles_source_url, write_style, geometry_filter, DEFAULT_FONT_STACK
from config_parser import sanitize_name

def add_leitstellen_layer(style, source_layer, source_id):
    base_id = f"{source_id}-{source_layer}"
    
    # Categorical Color Ramp für Leitstellen
    # Da die Layer-Properties oft "Bezirk XYZ" enthalten, nutzen wir ein Mapping
    # das auf dem sanitized source_layer basiert (der meist HRV, INN, RLZ etc. heißt)
    
    # Wir bauen ein Match-Statement, das auf den source_layer (den Dateinamen) prüft
    # oder alternativ auf bekannte Muster in der 'layer' property
    colors = {
        "hrv": "#3b82f6", # Blau
        "inn": "#10b981", # Grün
        "rlz": "#f59e0b", # Orange
        "skg": "#ec4899", # Pink
        "srki": "#8b5cf6" # Violett
    }
    
    # Wir versuchen erst den source_layer (Dateinamen) zu matchen
    expr = ["match", ["literal", source_layer]]
    for key, color in colors.items():
        expr.extend([key, color])
    
    # Fallback: Falls der Dateiname nicht gematcht hat (sollte er aber in dieser Pipeline),
    # schauen wir in die Property 'layer'
    fallback_expr = ["match", ["get", "layer"]]
    # Hier müssten wir sehr viele Varianten abdecken, daher ist der Match auf den 
    # source_layer (Dateinamen) in unserem System am stabilsten.
    fallback_expr.extend(["Bezirk Steyr-Land", "#8b5cf6"])
    fallback_expr.append("#3b82f6") # Finaler Fallback
    
    expr.append(fallback_expr)
    
    # Fill Layer
    style["layers"].append({
        "id": f"{base_id}-fill",
        "type": "fill",
        "source": source_id,
        "source-layer": source_layer,
        "filter": geometry_filter("Polygon", "MultiPolygon"),
        "paint": {
            "fill-color": expr,
            "fill-opacity": 0.25,
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
            "text-field": ["get", "name"],
            "text-font": DEFAULT_FONT_STACK,
            "text-size": ["interpolate", ["linear"], ["zoom"], 6, 11, 12, 14],
            "text-anchor": "center",
            "text-allow-overlap": False
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
    pmtiles_rel = f"pmtiles/{slug}.pmtiles"
    pmtiles_url = build_pmtiles_source_url(args.base_url, pmtiles_rel)
    
    style = create_base_style(f"OE5ITH {dataset_config['name']}", pmtiles_url, args.sprite_url, args.glyphs_url, slug)
    style["metadata"]["folder"] = dataset_config["name"]
    
    geojsons = list(full_path.glob("*.geojson"))
    for g in sorted(geojsons):
        layer_name = g.stem
        source_layer = sanitize_name(layer_name)
        add_leitstellen_layer(style, source_layer, slug)
        
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
        "template": "leitstellen"
    }
    build_style(dataset_config, args)
