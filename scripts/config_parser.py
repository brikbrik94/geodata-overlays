#!/usr/bin/env python3
import json
import re
from pathlib import Path

def sanitize_name(name):
    """Sanitizes a name for use as a layer or slug."""
    name = name.lower()
    name = (name.replace("ä", "ae")
                .replace("ö", "oe")
                .replace("ü", "ue")
                .replace("ß", "ss"))
    name = name.replace(" ", "_").replace("-", "_")
    name = re.sub(r"[^a-z0-9_]", "_", name)
    return re.sub(r"_+", "_", name).strip("_")

def load_repo_config(repo_root: Path):
    """
    Loads overlay_config.json from the repository root.
    If it doesn't exist, it generates a fallback configuration based on directory names.
    """
    config_path = repo_root / "overlay_config.json"
    
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading overlay_config.json: {e}")
            # Fallback will be used
    
    # --- Legacy Fallback Logic ---
    print("ℹ️ No overlay_config.json found, using legacy directory-based fallback.")
    datasets = []
    
    # We look for specific folders that matched our old build scripts
    legacy_mappings = {
        "RD-Dienststellen": "rd",
        "NAH-Stuetzpunkte": "nah",
        "Zonen": "zonen",
        "Anfahrtszeit": "anfahrtszeit",
        "Leitstellen": "leitstellen",
        "Bezirke": "gebiete",
        "Gemeinden": "gebiete",
        "Linien": "linz-ag-linien",
        "Straßen": "strassen"
    }
    
    # Walk the directory to find datasets
    for item in sorted(repo_root.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
            
        template = legacy_mappings.get(item.name)
        if template:
            # Check if it has subfolders (like Zonen/X)
            subfolders = [d for d in item.rglob("*") if d.is_dir() and list(d.glob("*.geojson"))]
            if subfolders:
                for sub in sorted(subfolders):
                    rel_path = sub.relative_to(repo_root)
                    datasets.append({
                        "path": str(rel_path),
                        "template": template,
                        "name": str(rel_path)
                    })
            
            # Check if root folder itself has geojsons
            if list(item.glob("*.geojson")):
                datasets.append({
                    "path": item.name,
                    "template": template,
                    "name": item.name
                })
        else:
            # If unknown but contains GeoJSON, assume it's "zonen" as a safe default
            if list(item.glob("*.geojson")):
                datasets.append({
                    "path": item.name,
                    "template": "zonen",
                    "name": item.name
                })
                
    return {
        "version": "1.0",
        "datasets": datasets
    }
