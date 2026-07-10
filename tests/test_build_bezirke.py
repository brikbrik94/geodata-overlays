#!/usr/bin/env python3
"""Tests für build_bezirke.py, insbesondere den transparenten Fill-Layer."""
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from style_builders.build_bezirke import build_style


def test_add_fill_layer_to_gebiete():
    """Test, dass add_gebiete_layer einen transparenten Fill-Layer hinzufügt.

    Fill-Layer muss:
    - vor dem Outline-Layer kommen (für korrektes Rendering)
    - fill-opacity = 0 (genau 0, nicht 0.0)
    - fill-color = #3b82f6
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Erstelle temporäre Test-GeoJSON-Datei
        geojson_dir = Path(tmp_dir) / "test_gebiete"
        geojson_dir.mkdir()
        test_geojson = geojson_dir / "gemeinden.geojson"
        test_geojson.write_text(json.dumps({
            "type": "FeatureCollection",
            "features": []
        }))

        output_dir = Path(tmp_dir) / "output"
        output_dir.mkdir()
        (output_dir / "styles").mkdir()

        # Erstelle Mock-Arguments
        class Args:
            root = geojson_dir.parent
            out = output_dir
            base_url = ""
            sprite_url = "../assets/sprites/oe5ith-markers/sprite"
            glyphs_url = "https://tiles.oe5ith.at/assets/fonts/{fontstack}/{range}.pbf"

        dataset_config = {
            "path": "test_gebiete",
            "name": "Test Gebiete",
            "template": "gebiete"
        }

        # Baue den Style
        slug = build_style(dataset_config, Args())

        # Lade den generierten Style
        style_path = output_dir / "styles" / f"{slug}.style.json"
        assert style_path.exists(), f"Style file not found: {style_path}"

        with open(style_path) as f:
            style = json.load(f)

        # Verifiziere, dass die Layers in korrekter Reihenfolge sind
        layer_ids = [layer["id"] for layer in style["layers"]]

        # Finde die Gemeinden-Layer
        gemeinden_fill_id = "test-gebiete-gemeinden-fill"
        gemeinden_outline_id = "test-gebiete-gemeinden-outline"
        gemeinden_labels_id = "test-gebiete-gemeinden-labels"

        assert gemeinden_fill_id in layer_ids, f"Fill layer {gemeinden_fill_id} not found in layers: {layer_ids}"
        assert gemeinden_outline_id in layer_ids, f"Outline layer {gemeinden_outline_id} not found"
        assert gemeinden_labels_id in layer_ids, f"Labels layer {gemeinden_labels_id} not found"

        # Verifiziere die Reihenfolge: Fill vor Outline vor Labels
        fill_idx = layer_ids.index(gemeinden_fill_id)
        outline_idx = layer_ids.index(gemeinden_outline_id)
        labels_idx = layer_ids.index(gemeinden_labels_id)

        assert fill_idx < outline_idx, "Fill layer must come before Outline layer"
        assert outline_idx < labels_idx, "Outline layer must come before Labels layer"

        # Finde den Fill-Layer und verifiziere seine Properties
        fill_layer = next(layer for layer in style["layers"] if layer["id"] == gemeinden_fill_id)

        assert fill_layer["type"] == "fill", f"Fill layer type should be 'fill', got {fill_layer['type']}"
        assert fill_layer["paint"]["fill-color"] == "#3b82f6", f"Fill color should be #3b82f6, got {fill_layer['paint']['fill-color']}"
        # Wichtig: fill-opacity muss genau 0 sein, nicht 0.0 (Integer vs Float)
        assert fill_layer["paint"]["fill-opacity"] == 0, f"Fill opacity should be 0, got {fill_layer['paint']['fill-opacity']}"

        # Verifiziere den Filter
        assert "filter" in fill_layer, "Fill layer should have a filter"

        print("✅ Fill-Layer Test passed")
        return True


if __name__ == "__main__":
    try:
        test_add_fill_layer_to_gebiete()
        print("All tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
