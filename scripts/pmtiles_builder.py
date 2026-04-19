#!/usr/bin/env python3
import json, os, re, subprocess, tempfile, argparse
from pathlib import Path
from config_parser import load_repo_config, sanitize_name

# --- Constants & Shared Logic ---

COLOR_PALETTE = {
    "1": "#2563eb", # Blau
    "2": "#16a34a", # Grün
    "3": "#f59e0b", # Gelb/Orange
    "4": "#dc2626", # Rot
    "5": "#7c3aed", # Violett
    "6": "#0891b2"  # Cyan
}

def load_global_color_mapping():
    project_root = Path(__file__).parent.parent
    path = project_root / "assets" / "mappings" / "color_mapping.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except:
            pass
    return {}

GLOBAL_COLOR_MAP = load_global_color_mapping()

# --- Pin Derivation Logic ---

def truthy_value(value):
    if isinstance(value, bool): return value
    if isinstance(value, (int, float)): return value != 0
    if isinstance(value, str): return value.strip().lower() in {"1", "true", "yes", "y", "ja"}
    return False

def derive_rd_pin(properties):
    emergency = str(properties.get("emergency", "")).strip().lower()
    if emergency == "mountain_rescue": return "brd-pin"
    if emergency != "ambulance_station": return "fallback-pin"
    has_nef = truthy_value(properties.get("ambulance_station:emergency_doctor"))
    has_rd = truthy_value(properties.get("ambulance_station:patient_transport"))
    pin_prefix = "nef" if has_nef else "rd" if (has_rd or emergency == "ambulance_station") else "fallback-pin"
    if pin_prefix == "fallback-pin": return "fallback-pin"
    
    brand_short = str(properties.get("brand:short", "")).strip().lower()
    mapping = {"brk":"brk", "örk":"oerk", "oerk":"oerk", "asb":"asb", "mhd":"mhd", "juh":"juh", "gk":"gk", "ma70":"ma70", "ims":"ims", "stadler":"stadler"}
    suffix = mapping.get(brand_short)
    if not suffix:
        text = " ".join(str(properties.get(k, "")).lower() for k in ("brand", "operator", "name", "short_name"))
        for k, v in mapping.items():
            if k in text: suffix = v; break
    return f"{pin_prefix}-{suffix}" if suffix else "fallback-pin"

def derive_nah_pin(properties):
    if str(properties.get("emergency", "")).lower() != "air_rescue_service": return "fallback-pin"
    text = " ".join(str(properties.get(k, "")).lower() for k in ("brand", "operator", "name", "short_name", "description", "alt_name"))
    rules = [("nah-adac-luftrettung", ("adac",)), ("nah-drf-luftrettung", ("drf",)), ("nah-oeamtc-flugrettung", ("oeamtc", "christophorus")), 
             ("nah-martin-flugrettung", ("martin flugrettung", "heli austria")), ("nah-schenk-air", ("schenkair", "schenk air")), 
             ("nah-ara-flugrettung", ("ara luftrettung",)), ("nah-wucher-helicopter", ("wucher",)), 
             ("nah-shs-schider-helicopter-service", ("schider", "shs")), ("nah-bundesministerium-des-inneren", ("bundesministerium des inneren", "polizei", "libelle"))]
    for pin, needles in rules:
        if any(n in text for n in needles): return pin
    return "fallback-pin"

def derive_zone_color(properties, local_map, layer_name):
    # Der Key steht laut Nutzer IMMER im Feld 'name'
    name_val = str(properties.get("name", ""))
    
    # 1. Lokales Mapping (farbzuordnung.json)
    if name_val in local_map:
        idx = str(local_map[name_val])
        return COLOR_PALETTE.get(idx, "#3b82f6")
        
    # 2. Globales Mapping (color_mapping.json)
    if name_val in GLOBAL_COLOR_MAP:
        return GLOBAL_COLOR_MAP[name_val]
        
    # Fallback basierend auf Layer-Name (Dateiname)
    if "nef" in layer_name.lower():
        return "#2563eb" # Blau
    if "sew" in layer_name.lower() or "rd" in layer_name.lower():
        return "#dc2626" # Rot
        
    return "#3b82f6" # Default Blau

# --- Build Logic ---

def process_geojson(src, dst, template):
    data = json.loads(src.read_text(encoding="utf-8"))
    
    # Für Zonen: Lokale Farbzuordnung laden
    local_map = {}
    if template == "zonen":
        farbz_path = src.parent / "farbzuordnung.json"
        if farbz_path.exists():
            try:
                local_map = json.loads(farbz_path.read_text(encoding="utf-8"))
            except:
                pass

    for f in data.get("features", []):
        props = f.setdefault("properties", {})
        if template == "rd": props["pin"] = derive_rd_pin(props)
        elif template == "nah": props["pin"] = derive_nah_pin(props)
        elif template == "zonen": props["color"] = derive_zone_color(props, local_map, src.stem)
        
    dst.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

def run_tippecanoe(out_file, layer_specs, template):
    # -Z 0 -z 15: Zoomstufen 0 bis 15
    cmd = ["tippecanoe", "-o", str(out_file), "-Z", "0", "-z", "15", "--force", "--no-feature-limit", "--no-tile-size-limit", "-r", "1"]
    
    # Spezifische Optimierungen für NAH
    if template == "nah":
        cmd.extend(["--no-line-simplification", "--no-tiny-polygon-reduction"])
    
    for layer_name, file_path in layer_specs:
        cmd.extend(["-L", f"{layer_name}:{file_path}"])
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    
    root = Path(args.root).resolve()
    out_base = Path(args.out).resolve() / "pmtiles"
    
    config = load_repo_config(root)
    generated_files = set()
    
    for dataset in config.get("datasets", []):
        rel_path = Path(dataset["path"])
        full_path = root / rel_path
        template = dataset["template"]
        
        if not full_path.exists():
            print(f"⚠️ Warning: Path {full_path} not found.")
            continue
            
        geojsons = list(full_path.glob("*.geojson"))
        if not geojsons:
            continue
            
        # Sanitized filename for PMTiles (Flat slug)
        slug = "-".join(sanitize_name(p).replace("_", "-") for p in rel_path.parts)
        out_file = out_base / f"{slug}.pmtiles"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📦 Building bundle: {rel_path} ({template}) -> {slug}.pmtiles")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            specs = []
            for g in sorted(geojsons):
                clean_name = sanitize_name(g.stem)
                target = tmp_path / g.name
                process_geojson(g, target, template)
                specs.append((clean_name, target))
            
            run_tippecanoe(out_file, specs, template)
            generated_files.add(out_file.resolve())

    # --- Cleanup obsolete PMTiles ---
    if out_base.exists():
        print("\n🧹 Cleaning up obsolete PMTiles...")
        for existing_file in out_base.glob("*.pmtiles"):
            if existing_file.resolve() not in generated_files:
                print(f"🗑️ Deleting obsolete file: {existing_file.name}")
                existing_file.unlink()

if __name__ == "__main__": main()
