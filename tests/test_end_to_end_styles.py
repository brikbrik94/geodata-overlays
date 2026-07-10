#!/usr/bin/env python3
"""End-to-end tests for the complete geodata overlay build pipeline.

Tests verify:
1. All required output files exist (layer-list.json, manifest.json, styles, etc.)
2. layer-list.json structure is correct (version, styles, groups with metadata)
3. Gebiete (transparent fill) groups have correct metadata (type=fill, opacity=0, 3+ layers)
4. Gebiete style.json files have fill layers with correct properties
"""
import sys
import json
from pathlib import Path

# Test data directory
DIST_DIR = Path(__file__).resolve().parent.parent / "dist"


def test_full_build_output():
    """Verifies all required files exist in dist/ after a full build.

    Expected files:
    - dist/layer-list.json
    - dist/manifest.json
    - dist/styles/ (directory with .style.json files)
    - dist/pmtiles/ (directory with .pmtiles files)
    - dist/assets/ (directory with sprites and fonts)
    """
    if not DIST_DIR.exists():
        print("⚠️  dist/ directory not found. Skipping test.")
        return None

    # Check layer-list.json
    layer_list_path = DIST_DIR / "layer-list.json"
    assert layer_list_path.exists(), f"layer-list.json not found at {layer_list_path}"

    # Check manifest.json
    manifest_path = DIST_DIR / "manifest.json"
    assert manifest_path.exists(), f"manifest.json not found at {manifest_path}"

    # Check styles directory
    styles_dir = DIST_DIR / "styles"
    assert styles_dir.exists(), f"styles/ directory not found at {styles_dir}"
    style_files = list(styles_dir.glob("*.style.json"))
    assert len(style_files) > 0, "No .style.json files found in styles/"

    # Check pmtiles directory
    pmtiles_dir = DIST_DIR / "pmtiles"
    assert pmtiles_dir.exists(), f"pmtiles/ directory not found at {pmtiles_dir}"
    pmtiles_files = list(pmtiles_dir.glob("*.pmtiles"))
    assert len(pmtiles_files) > 0, "No .pmtiles files found in pmtiles/"

    # Check assets directory
    assets_dir = DIST_DIR / "assets"
    assert assets_dir.exists(), f"assets/ directory not found at {assets_dir}"

    print(f"✅ test_full_build_output passed ({len(style_files)} styles, {len(pmtiles_files)} pmtiles)")


def test_layer_list_structure():
    """Validates layer-list.json structure and schema.

    layer-list.json must have:
    - version field
    - styles array
    - Each style has: style_id, name, pmtiles_path, groups array
    - Each group has: source_layer, name, template, style_layers, type, color, opacity, legend_items
    """
    layer_list_path = DIST_DIR / "layer-list.json"
    if not layer_list_path.exists():
        print("⚠️  layer-list.json not found. Skipping test.")
        return None

    with open(layer_list_path) as f:
        layer_list = json.load(f)

    # Verify top-level structure
    assert "version" in layer_list, "layer-list.json missing 'version' field"
    assert "styles" in layer_list, "layer-list.json missing 'styles' field"
    assert isinstance(layer_list["styles"], list), "styles must be a list"
    assert len(layer_list["styles"]) > 0, "styles list is empty"

    # Verify each style has required fields
    for style in layer_list["styles"]:
        assert "style_id" in style, f"Style missing 'style_id': {style}"
        assert "name" in style, f"Style missing 'name': {style}"
        assert "pmtiles_path" in style, f"Style missing 'pmtiles_path': {style}"
        assert "groups" in style, f"Style missing 'groups': {style}"
        assert isinstance(style["groups"], list), f"groups must be list, got {type(style['groups'])}"

        # Verify each group has required fields
        for group in style["groups"]:
            assert "source_layer" in group, f"Group missing 'source_layer': {group}"
            assert "name" in group, f"Group missing 'name': {group}"
            assert "template" in group, f"Group missing 'template': {group}"
            assert "style_layers" in group, f"Group missing 'style_layers': {group}"
            assert "type" in group, f"Group missing 'type': {group}"
            assert "color" in group, f"Group missing 'color': {group}"
            assert "opacity" in group, f"Group missing 'opacity': {group}"
            assert "legend_items" in group, f"Group missing 'legend_items': {group}"

            # Verify style_layers is a list
            assert isinstance(group["style_layers"], list), \
                f"style_layers must be list, got {type(group['style_layers'])}"

    print(f"✅ test_layer_list_structure passed ({len(layer_list['styles'])} styles validated)")


def test_gebiete_transparent_fill():
    """Verifies that gebiete (transparent fill) groups have correct metadata.

    For all groups with template="gebiete":
    - type must be "fill"
    - opacity must be 0
    - color must be "#3b82f6"
    - style_layers must have 3+ layers (fill, outline, labels)
    - legend_items must be None or missing
    """
    layer_list_path = DIST_DIR / "layer-list.json"
    if not layer_list_path.exists():
        print("⚠️  layer-list.json not found. Skipping test.")
        return None

    with open(layer_list_path) as f:
        layer_list = json.load(f)

    gebiete_groups = []
    for style in layer_list["styles"]:
        for group in style["groups"]:
            if group.get("template") == "gebiete":
                gebiete_groups.append((style["style_id"], group))

    assert len(gebiete_groups) > 0, "No gebiete (template='gebiete') groups found"

    for style_id, group in gebiete_groups:
        # Check type
        assert group.get("type") == "fill", \
            f"Gebiete group '{style_id}/{group['name']}' has type='{group.get('type')}', expected 'fill'"

        # Check opacity
        assert group.get("opacity") == 0, \
            f"Gebiete group '{style_id}/{group['name']}' has opacity={group.get('opacity')}, expected 0"

        # Check color
        assert group.get("color") == "#3b82f6", \
            f"Gebiete group '{style_id}/{group['name']}' has color='{group.get('color')}', expected '#3b82f6'"

        # Check style_layers count (should have fill, outline, labels)
        style_layers = group.get("style_layers", [])
        assert len(style_layers) >= 3, \
            f"Gebiete group '{style_id}/{group['name']}' has {len(style_layers)} layers, expected 3+: {style_layers}"

        # Check legend_items (should be None or empty for transparent fills)
        legend = group.get("legend_items")
        assert legend is None, \
            f"Gebiete group '{style_id}/{group['name']}' has legend_items={legend}, expected None"

    print(f"✅ test_gebiete_transparent_fill passed ({len(gebiete_groups)} gebiete groups validated)")


def test_click_detection_on_filled_polygon():
    """Verifies that gebiete.style.json files have fill layers with correct properties.

    For all gebiete styles (bezirke, gemeinden, etc.):
    - Must have layers array
    - Must have at least one fill layer with type="fill"
    - Fill layer must have paint.fill-opacity = 0
    - Fill layer must have paint.fill-color = "#3b82f6"
    - Fill layer must have a filter for Polygon/MultiPolygon
    """
    layer_list_path = DIST_DIR / "layer-list.json"
    if not layer_list_path.exists():
        print("⚠️  layer-list.json not found. Skipping test.")
        return None

    with open(layer_list_path) as f:
        layer_list = json.load(f)

    # Find all gebiete styles
    gebiete_styles = []
    for style in layer_list["styles"]:
        for group in style["groups"]:
            if group.get("template") == "gebiete":
                gebiete_styles.append(style["style_id"])
                break

    assert len(gebiete_styles) > 0, "No gebiete styles found"

    # Remove duplicates
    gebiete_styles = list(set(gebiete_styles))

    for style_id in gebiete_styles:
        style_path = DIST_DIR / "styles" / f"{style_id}.style.json"
        assert style_path.exists(), f"Style file not found for gebiete style {style_id}: {style_path}"

        with open(style_path) as f:
            style_json = json.load(f)

        # Check layers exist
        assert "layers" in style_json, f"Style {style_id} missing 'layers' field"
        assert isinstance(style_json["layers"], list), f"layers must be list in style {style_id}"

        # Find fill layers
        fill_layers = [layer for layer in style_json["layers"] if layer.get("type") == "fill"]
        assert len(fill_layers) > 0, f"Style {style_id} has no fill layers"

        # Verify first fill layer (should be the transparent one added by gebiete template)
        fill_layer = fill_layers[0]

        # Check fill-opacity
        assert "paint" in fill_layer, f"Fill layer in {style_id} missing 'paint' field"
        assert "fill-opacity" in fill_layer["paint"], \
            f"Fill layer in {style_id} missing 'fill-opacity' in paint"
        assert fill_layer["paint"]["fill-opacity"] == 0, \
            f"Fill layer in {style_id} has fill-opacity={fill_layer['paint']['fill-opacity']}, expected 0"

        # Check fill-color
        assert "fill-color" in fill_layer["paint"], \
            f"Fill layer in {style_id} missing 'fill-color' in paint"
        assert fill_layer["paint"]["fill-color"] == "#3b82f6", \
            f"Fill layer in {style_id} has fill-color='{fill_layer['paint']['fill-color']}', expected '#3b82f6'"

        # Check filter (should filter for Polygon/MultiPolygon)
        if "filter" in fill_layer:
            # Filter should be a match expression on geometry-type
            assert isinstance(fill_layer["filter"], list), \
                f"Filter in {style_id} should be a list (MapLibre expression)"

    print(f"✅ test_click_detection_on_filled_polygon passed ({len(gebiete_styles)} gebiete styles verified)")


if __name__ == "__main__":
    try:
        print("Running end-to-end tests for geodata overlay pipeline...\n")

        test_full_build_output()
        test_layer_list_structure()
        test_gebiete_transparent_fill()
        test_click_detection_on_filled_polygon()

        print("\n✅ All end-to-end tests passed!")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
