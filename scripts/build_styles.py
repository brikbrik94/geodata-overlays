#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

# Add script directory to path so we can import our modules
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR / "scripts"))
sys.path.append(str(ROOT_DIR / "scripts" / "style_builders"))

from config_parser import load_repo_config
import build_zonen
import build_rd
import build_nah
import build_bezirke  # For 'gebiete'
import build_strassen
import build_leitstellen
import build_anfahrtszeit
import build_linz_ag_linien
import build_sonstiges

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--sprite-url", default="../assets/sprites/oe5ith-markers/sprite")
    parser.add_argument("--glyphs-url", default="https://tiles.oe5ith.at/assets/fonts/{fontstack}/{range}.pbf")
    args = parser.parse_args()
    
    repo_root = Path(args.root).resolve()
    out_dir = Path(args.out).resolve()
    styles_out = out_dir / "styles"
    config = load_repo_config(repo_root)
    
    print(f"🚀 Starting Style Orchestrator for {len(config.get('datasets', []))} datasets...")
    
    # Mapping of template ID to module
    template_map = {
        "zonen": build_zonen,
        "rd": build_rd,
        "nah": build_nah,
        "gebiete": build_bezirke,
        "strassen": build_strassen,
        "leitstellen": build_leitstellen,
        "anfahrtszeit": build_anfahrtszeit,
        "linz-ag-linien": build_linz_ag_linien,
        "sonstiges": build_sonstiges
    }
    
    generated_styles = set()
    for dataset in config.get("datasets", []):
        template_id = dataset.get("template")
        builder = template_map.get(template_id)
        
        if builder:
            try:
                print(f"  🎨 Building {dataset['name']} (Template: {template_id})...")
                slug = builder.build_style(dataset, args)
                if slug:
                    style_path = styles_out / f"{slug}.style.json"
                    generated_styles.add(style_path.resolve())
            except Exception as e:
                print(f"  ❌ Error building {dataset['name']}: {e}")
        else:
            print(f"  ⚠️ Unknown template '{template_id}' for dataset {dataset['name']}")

    # --- Cleanup obsolete Styles ---
    if styles_out.exists():
        print("\n🧹 Cleaning up obsolete Styles...")
        for existing_file in styles_out.glob("*.style.json"):
            if existing_file.resolve() not in generated_styles:
                print(f"🗑️ Deleting obsolete style: {existing_file.name}")
                existing_file.unlink()

    print("✅ All styles built.")

if __name__ == "__main__":
    main()
