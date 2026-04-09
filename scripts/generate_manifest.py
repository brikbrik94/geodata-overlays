#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone

def main():
    # Basisverzeichnisse relativ zum Projekt-Root
    project_root = Path(__file__).parent.parent.resolve()
    dist_dir = project_root / "dist"
    styles_dir = dist_dir / "styles"
    
    # Manifest-Struktur initialisieren nach neuem Standard v1.0
    manifest = {
        "version": "1.0",
        "project": "OE5ITH Overlay Pipeline",
        "tileset": "overlays",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "datasets": [],
        "resources": {
            "sprites": [],
            "fonts": []
        }
    }

    # 1. Scanne Sprites im dist/assets/sprites Ordner
    # Zuerst Sprites scannen, damit wir sprite_id in datasets zuordnen können
    dist_sprites_dir = dist_dir / "assets" / "sprites"
    sprite_map = {} # Mapping von Pfad-Teil zu Sprite-ID
    if dist_sprites_dir.exists():
        for sprite_group in sorted(dist_sprites_dir.iterdir()):
            if sprite_group.is_dir():
                sprite_id = sprite_group.name
                sprite_path = f"assets/sprites/{sprite_id}"
                manifest["resources"]["sprites"].append({
                    "id": sprite_id,
                    "path": sprite_path
                })
                sprite_map[sprite_id] = sprite_id

    # 2. Scanne Fonts im dist/assets/fonts Ordner
    dist_fonts_dir = dist_dir / "assets" / "fonts"
    if dist_fonts_dir.exists():
        for font_group in sorted(dist_fonts_dir.iterdir()):
            if font_group.is_dir():
                manifest["resources"]["fonts"].append({
                    "id": font_group.name,
                    "path": f"assets/fonts/{font_group.name}"
                })

    # 3. Scanne Styles und zugehörige PMTiles
    if styles_dir.exists():
        for style_file in sorted(styles_dir.glob("*.style.json")):
            # Pfad relativ zu dist/
            style_rel = f"styles/{style_file.name}"
            
            pmtiles_rel = ""
            sprite_id = None
            source_layer_count = 0
            folder_name = style_file.stem.replace(".style", "").replace("-", " ").title()
            
            try:
                with open(style_file, "r", encoding="utf-8") as f:
                    style_data = json.load(f)
                    
                    # Metadata Folder extrahieren (für Name)
                    if "metadata" in style_data and "folder" in style_data["metadata"]:
                        folder_name = style_data["metadata"]["folder"]
                    
                    # PMTiles Pfad extrahieren
                    for source in style_data.get("sources", {}).values():
                        if source.get("type") == "vector" and "url" in source:
                            url = source["url"]
                            if url.startswith("pmtiles://"):
                                # Extrahiere Pfad nach dem Protokoll
                                p_rel = url.replace("pmtiles://", "")
                                # Normalisiere Pfade wie ../pmtiles/xyz.pmtiles -> pmtiles/xyz.pmtiles
                                pmtiles_rel = p_rel.replace("../", "")
                                # Falls es noch immer ein Protokoll hat (z.B. pmtiles://http://...)
                                if "://" in pmtiles_rel:
                                    # Dann nehmen wir nur den Teil nach dem Host falls möglich
                                    parts = pmtiles_rel.split("/")
                                    if len(parts) > 1 and parts[0].replace(".","").replace(":","").isalnum():
                                        pmtiles_rel = "/".join(parts[1:])
                                break
                    
                    # Sprite ID erkennen
                    sprite_url = style_data.get("sprite", "")
                    if sprite_url:
                        # Suche nach bekannten Sprite IDs in der URL
                        for sid in sprite_map:
                            if sid in sprite_url:
                                sprite_id = sid
                                break
                    
                    # Layer zählen (alle außer Background und OSM)
                    layers = style_data.get("layers", [])
                    source_layers = set()
                    for l in layers:
                        sl = l.get("source-layer")
                        if sl:
                            source_layers.add(sl)
                    source_layer_count = len(source_layers)

            except Exception as e:
                print(f"⚠️ Warnung: Konnte {style_file.name} nicht parsen: {e}")

            # Fallback falls Extraktion fehlschlägt
            if not pmtiles_rel:
                pmtiles_rel = f"pmtiles/{style_file.stem.replace('.style', '')}.pmtiles"

            dataset = {
                "id": style_file.stem.replace(".style", ""),
                "name": folder_name,
                "style_path": style_rel,
                "pmtiles_path": pmtiles_rel,
                "source_layer_count": source_layer_count
            }
            if sprite_id:
                dataset["sprite_id"] = sprite_id
                
            manifest["datasets"].append(dataset)

    # 4. Manifest schreiben
    dist_dir.mkdir(exist_ok=True)
    manifest_path = dist_dir / "manifest.json"
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"✅ Manifest erstellt unter: {manifest_path}")
    print(f"   - {len(manifest['datasets'])} Datasets gefunden")
    print(f"   - {len(manifest['resources']['sprites'])} Sprite-Sheets gefunden")
    print(f"   - {len(manifest['resources']['fonts'])} Fonts gefunden")

if __name__ == "__main__":
    main()
