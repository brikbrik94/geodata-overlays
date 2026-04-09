#!/usr/bin/env python3
import json
import os
from pathlib import Path
from datetime import datetime

def main():
    # Basisverzeichnisse relativ zum Projekt-Root
    project_root = Path(__file__).parent.parent.resolve()
    dist_dir = project_root / "dist"
    pmtiles_dir = project_root / "pmtiles"
    styles_dir = pmtiles_dir / "styles"
    
    # Manifest-Struktur initialisieren
    manifest = {
        "project": "Modulare Overlay-Pipeline",
        "generated_at": datetime.now().isoformat(),
        "overlays": [],
        "resources": {
            "sprites": []
        }
    }

    # 1. Scanne Styles und zugehörige PMTiles
    if styles_dir.exists():
        for style_file in sorted(styles_dir.glob("*.style.json")):
            # Pfad relativ zu dist/ für externe Nutzung
            style_rel = os.path.relpath(style_file, project_root)
            
            # Versuche, das PMTiles aus dem Style zu extrahieren
            pmtiles_rel = ""
            try:
                with open(style_file, "r", encoding="utf-8") as f:
                    style_data = json.load(f)
                    for source in style_data.get("sources", {}).values():
                        if source.get("type") == "vector" and "url" in source:
                            url = source["url"]
                            if url.startswith("pmtiles://"):
                                # Extrahiere Pfad nach dem Protokoll
                                pmtiles_rel = url.replace("pmtiles://", "")
                                # Normalisiere Pfade wie ../pmtiles/xyz.pmtiles -> pmtiles/xyz.pmtiles
                                pmtiles_rel = pmtiles_rel.replace("../", "")
                                break
            except Exception as e:
                print(f"⚠️ Warnung: Konnte {style_file.name} nicht parsen: {e}")

            manifest["overlays"].append({
                "id": style_file.stem.replace(".style", ""),
                "name": style_file.stem.replace(".style", "").replace("-", " ").title(),
                "style_path": style_rel,
                "pmtiles_path": pmtiles_rel if pmtiles_rel else f"pmtiles/{style_file.stem.replace('.style', '')}.pmtiles"
            })

    # 2. Scanne Sprites im dist/ Ordner
    dist_sprites_dir = dist_dir / "assets" / "sprites"
    if dist_sprites_dir.exists():
        for sprite_group in sorted(dist_sprites_dir.iterdir()):
            if sprite_group.is_dir():
                # Wir listen nur den Basisnamen des Sprites auf
                manifest["resources"]["sprites"].append({
                    "id": sprite_group.name,
                    "sprite_url": f"assets/sprites/{sprite_group.name}/sprite"
                })

    # 3. Verzeichnis dist/ sicherstellen und Manifest schreiben
    dist_dir.mkdir(exist_ok=True)
    manifest_path = dist_dir / "manifest.json"
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"✅ Manifest erstellt unter: {manifest_path}")
    print(f"   - {len(manifest['overlays'])} Overlays gefunden")
    print(f"   - {len(manifest['resources']['sprites'])} Sprite-Sheets gefunden")

if __name__ == "__main__":
    main()
