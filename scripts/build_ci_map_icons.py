#!/usr/bin/env python3
"""Render the oe5ith-ci SDF map-icons into the combined sprite source folder.

Implements the "Builder-Vertrag" from the oe5ith-ci repo
(docs/map-icons.md): scan every SVG listed in icons.json, render it as an
SDF source (single-channel alpha mask, recolored at runtime via MapLibre
`icon-color`), keep the `ci-` prefixed name unchanged, and forward the
`stretchX` / `stretchY` / `content` metadata so `build_sprites.py` can write
it into sprite.json.

The icons are written as <name>.png into --out-dir (the combined
`oe5ith-markers` folder). A sidecar meta file (--meta-out) maps each icon
name to {sdf, stretchX?, stretchY?, content?} so the sprite packer can apply
SDF flag and stretch zones without re-parsing icons.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def render_svg_to_png(svg_path: Path, out_png: Path, width: int, height: int) -> None:
    import cairosvg

    out_png.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(out_png),
        output_width=width,
        output_height=height,
    )


def make_sdf(png_path: Path, spread: float = 8.0) -> None:
    """Wandelt ein gerendertes PNG in eine echte SDF-Textur um.

    MapLibre braucht für icon-halo-color / icon-halo-width einen echten
    Signed-Distance-Field-Kanal: Pixel tief innen haben hohe Alpha-Werte (~255),
    Pixel an der Kante ~128, Pixel außen niedrige Werte (~0). Eine simple
    binäre Maske (0/255) erlaubt kein Halo, weil der nötige Gradient fehlt.

    Algorithmus:
    1. Alpha-Kanal als binäre Maske extrahieren
    2. Euklidische Distanztransformation auf Innen- und Außen-Pixel
    3. Signierte Distanz → Alpha normiert auf spread-Pixel Gradient-Breite
    """
    import numpy as np
    from PIL import Image
    from scipy.ndimage import distance_transform_edt

    img = Image.open(png_path).convert("RGBA")
    arr = np.array(img)

    mask = arr[:, :, 3] > 127

    dist_inside = distance_transform_edt(mask)
    dist_outside = distance_transform_edt(~mask)

    # Signierte Distanz: positiv innen, negativ außen; normiert auf spread.
    signed = (dist_inside - dist_outside) / (2.0 * spread)
    alpha = np.clip((0.5 + signed) * 255.0, 0.0, 255.0).round().astype(np.uint8)

    result = np.zeros_like(arr)
    result[:, :, 0] = 255
    result[:, :, 1] = 255
    result[:, :, 2] = 255
    result[:, :, 3] = alpha

    Image.fromarray(result).save(png_path)


# Icons mit zu dünnen Features für den globalen spread-Wert.
# ci-symbol-location: Ring (5px) und Ticks (4px) bei spread=8 → max. SDF-Alpha ~62%,
# Halo und Fill sind kaum unterscheidbar → Render-Artefakte. spread=3 gibt ~84-92%.
# ci-marker-ring: Donut-Ring (8px breit) bei spread=8 → max. SDF-Alpha ~76%, Ring
# wird blass/washed-out gerendert. spread=3 gibt volle 100% Deckung.
_SPREAD_OVERRIDES: dict[str, float] = {
    "ci-symbol-location": 3.0,
    "ci-marker-ring": 3.0,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to oe5ith-ci icons.json")
    parser.add_argument("--svg-dir", required=True, help="Directory containing the ci-*.svg sources")
    parser.add_argument("--out-dir", required=True, help="Combined sprite source dir (oe5ith-markers)")
    parser.add_argument("--meta-out", required=True, help="Where to write the sidecar meta JSON")
    parser.add_argument("--spread", type=float, default=8.0,
                        help="SDF-Gradientbreite in Pixel (default: 8). Bestimmt, wie weit "
                             "icon-halo-width maximal reichen kann.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    svg_dir = Path(args.svg_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    meta_out = Path(args.meta_out).resolve()

    if not manifest_path.exists():
        print(f"❌ CI manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    icons = payload.get("icons", [])

    meta: dict[str, dict] = {}
    rendered = 0
    for icon in icons:
        name = icon.get("name")
        file_name = icon.get("file")
        if not name or not file_name:
            print(f"⚠️ Skipping malformed icon entry: {icon}", file=sys.stderr)
            continue

        svg_path = svg_dir / file_name
        if not svg_path.exists():
            # "Geplante" Icons sind im Manifest gelistet, aber noch ohne SVG.
            print(f"ℹ️ Skipping planned icon without SVG: {file_name}")
            continue

        width, height = icon.get("viewBox", [64, 64])
        out_png = out_dir / f"{name}.png"
        render_svg_to_png(svg_path, out_png, int(width), int(height))
        effective_spread = _SPREAD_OVERRIDES.get(name, args.spread)
        make_sdf(out_png, spread=effective_spread)
        rendered += 1

        entry: dict = {"sdf": bool(icon.get("sdf", True))}
        for key in ("stretchX", "stretchY", "content"):
            if key in icon:
                entry[key] = icon[key]
        meta[name] = entry

    meta_out.parent.mkdir(parents=True, exist_ok=True)
    meta_out.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ Rendered {rendered} CI map-icons into {out_dir} (meta: {meta_out.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
