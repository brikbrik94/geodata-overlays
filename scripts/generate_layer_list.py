#!/usr/bin/env python3
import json
import argparse
from pathlib import Path
import sys

# Add script directory to path for config_parser
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR / "scripts"))

from config_parser import load_repo_config, sanitize_name
from layer_metadata_extractor import extract_layer_metadata

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Path to the GeoJSON data root")
    parser.add_argument("--out", default=str(ROOT_DIR / "dist"), help="Output directory")
    args = parser.parse_args()
    
    repo_root = Path(args.root).resolve()
    dist_dir = Path(args.out).resolve()
    styles_dir = dist_dir / "styles"
    
    if not styles_dir.exists():
        print(f"⚠️ Styles directory {styles_dir} not found.")
        return

    config = load_repo_config(repo_root)
    
    # 1. Build a lookup map: sanitized_layer_name -> { original_name, template, dataset_path }
    # Since multiple datasets might have layers with the same name, we use (dataset_slug, layer_name) as key
    layer_lookup = {}
    
    for dataset in config.get("datasets", []):
        rel_path = Path(dataset["path"])
        full_path = repo_root / rel_path
        template = dataset["template"]
        
        # Dataset slug (same logic as in pmtiles_builder and build_styles)
        dataset_slug = "-".join(sanitize_name(p).replace("_", "-") for p in rel_path.parts)
        
        if full_path.exists():
            for g in full_path.glob("*.geojson"):
                clean_layer_name = sanitize_name(g.stem)
                key = (dataset_slug, clean_layer_name)
                layer_lookup[key] = {
                    "name": g.stem,
                    "template": template,
                    "original_file": str(rel_path / g.name)
                }

    # 2. Parse generated styles and group layers
    layer_list = {
        "version": "1.0",
        "styles": []
    }
    
    for style_file in sorted(styles_dir.glob("*.style.json")):
        style_id = style_file.stem.replace(".style", "")
        try:
            with open(style_file, "r", encoding="utf-8") as f:
                style_data = json.load(f)
                
            folder_name = style_data.get("metadata", {}).get("folder", style_id.title())
            
            # Extract PMTiles path
            pmtiles_rel = ""
            for source in style_data.get("sources", {}).values():
                if source.get("type") == "vector" and "url" in source:
                    url = source["url"]
                    if url.startswith("pmtiles://"):
                        p_rel = url.replace("pmtiles://", "").replace("../", "")
                        if "://" in p_rel:
                            parts = p_rel.split("/")
                            if len(parts) > 1 and parts[0].replace(".","").replace(":","").isalnum():
                                p_rel = "/".join(parts[1:])
                        pmtiles_rel = p_rel
                        break
            
            # Group layers by source-layer
            groups_dict = {}
            for layer in style_data.get("layers", []):
                source_layer = layer.get("source-layer")
                layer_id = layer.get("id")

                if source_layer and layer_id:
                    if source_layer not in groups_dict:
                        # Lookup metadata
                        meta = layer_lookup.get((style_id, source_layer), {})

                        # Extract layer metadata (type, color, opacity, legend_items)
                        layer_metadata = extract_layer_metadata(style_data, source_layer)

                        groups_dict[source_layer] = {
                            "source_layer": source_layer,
                            "name": meta.get("name", source_layer.replace("_", " ").title()),
                            "template": meta.get("template", "unknown"),
                            "original_file": meta.get("original_file", ""),
                            "style_layers": []
                        }

                        # Add metadata fields if available
                        if layer_metadata:
                            groups_dict[source_layer]["type"] = layer_metadata.get("type")
                            groups_dict[source_layer]["color"] = layer_metadata.get("color")
                            groups_dict[source_layer]["opacity"] = layer_metadata.get("opacity")
                            groups_dict[source_layer]["legend_items"] = layer_metadata.get("legend_items")

                    groups_dict[source_layer]["style_layers"].append(layer_id)
            
            if groups_dict:
                style_entry = {
                    "style_id": style_id,
                    "name": folder_name,
                    "pmtiles_path": pmtiles_rel,
                    "groups": list(groups_dict.values())
                }
                layer_list["styles"].append(style_entry)
                
        except Exception as e:
            print(f"⚠️ Error parsing {style_file.name}: {e}")

    # 3. Write layer-list.json
    out_file = dist_dir / "layer-list.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(layer_list, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Generated layer-list.json under: {out_file}")
    print(f"   - {len(layer_list['styles'])} styles documented")

if __name__ == "__main__":
    main()
