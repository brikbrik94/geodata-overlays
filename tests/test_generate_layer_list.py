#!/usr/bin/env python3
"""Tests for layer metadata extraction and layer-list generation."""
import sys
import json
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from layer_metadata_extractor import (
    extract_layer_color,
    extract_layer_opacity,
    extract_legend_items,
    extract_layer_metadata,
)


def test_extract_layer_color_from_fill():
    """Test extracting color from fill layer."""
    layer = {
        "type": "fill",
        "paint": {
            "fill-color": "#3b82f6",
            "fill-opacity": 0.5
        }
    }
    color = extract_layer_color(layer)
    assert color == "#3b82f6", f"Expected '#3b82f6', got {color}"
    print("✓ test_extract_layer_color_from_fill passed")


def test_extract_layer_color_from_line():
    """Test extracting color from line layer."""
    layer = {
        "type": "line",
        "paint": {
            "line-color": "#ff0000",
            "line-width": 2
        }
    }
    color = extract_layer_color(layer)
    assert color == "#ff0000", f"Expected '#ff0000', got {color}"
    print("✓ test_extract_layer_color_from_line passed")


def test_extract_layer_color_missing():
    """Test extracting color when paint property is missing."""
    layer = {
        "type": "symbol",
        "layout": {
            "icon-image": "test-icon"
        }
    }
    color = extract_layer_color(layer)
    assert color is None, f"Expected None, got {color}"
    print("✓ test_extract_layer_color_missing passed")


def test_extract_layer_opacity_from_fill():
    """Test extracting opacity from fill layer."""
    layer = {
        "type": "fill",
        "paint": {
            "fill-color": "#3b82f6",
            "fill-opacity": 0
        }
    }
    opacity = extract_layer_opacity(layer)
    assert opacity == 0, f"Expected 0, got {opacity}"
    print("✓ test_extract_layer_opacity_from_fill passed")


def test_extract_layer_opacity_from_line():
    """Test extracting opacity from line layer."""
    layer = {
        "type": "line",
        "paint": {
            "line-color": "#3b82f6",
            "line-opacity": 0.8
        }
    }
    opacity = extract_layer_opacity(layer)
    assert opacity == 0.8, f"Expected 0.8, got {opacity}"
    print("✓ test_extract_layer_opacity_from_line passed")


def test_extract_layer_opacity_default():
    """Test extracting opacity when not specified."""
    layer = {
        "type": "symbol",
        "paint": {
            "text-color": "#ffffff"
        }
    }
    opacity = extract_layer_opacity(layer)
    assert opacity == 1, f"Expected 1 (default), got {opacity}"
    print("✓ test_extract_layer_opacity_default passed")


def test_extract_legend_items_none():
    """Test extract_legend_items returns None for simple layers."""
    layers = [
        {
            "id": "fill-layer",
            "type": "fill",
            "paint": {"fill-color": "#3b82f6"}
        }
    ]
    items = extract_legend_items(layers)
    assert items is None, f"Expected None for simple layers, got {items}"
    print("✓ test_extract_legend_items_none passed")


def test_extract_legend_items_interpolate():
    """Test extract_legend_items parses interpolate expressions."""
    layers = [
        {
            "id": "time-fill",
            "type": "fill",
            "paint": {
                "fill-color": [
                    "interpolate",
                    ["linear"],
                    ["get", "time"],
                    0, "#22c55e",
                    15, "#facc15",
                    30, "#f97316",
                    45, "#ef4444"
                ]
            }
        }
    ]
    items = extract_legend_items(layers)
    assert items is not None, "Expected legend items for interpolate expression"
    assert isinstance(items, list), f"Expected list, got {type(items)}"
    assert len(items) == 4, f"Expected 4 items, got {len(items)}"

    # Check first item
    assert items[0]["label"] == "0-15 min", f"Expected '0-15 min', got {items[0]['label']}"
    assert items[0]["color"] == "#22c55e", f"Expected '#22c55e', got {items[0]['color']}"

    # Check last item
    assert items[-1]["label"] == "45+ min", f"Expected '45+ min', got {items[-1]['label']}"
    assert items[-1]["color"] == "#ef4444", f"Expected '#ef4444', got {items[-1]['color']}"

    print("✓ test_extract_legend_items_interpolate passed")


def test_extract_legend_items_match():
    """Test extract_legend_items parses match expressions."""
    layers = [
        {
            "id": "anfahrtszeit-fill",
            "type": "fill",
            "paint": {
                "fill-color": [
                    "match",
                    ["get", "AA_MINS"],
                    15, "#10b981",
                    30, "#84cc16",
                    45, "#f59e0b",
                    60, "#f97316",
                    75, "#ef4444",
                    90, "#b91c1c",
                    "#3b82f6"
                ]
            }
        }
    ]
    items = extract_legend_items(layers)
    assert items is not None, "Expected legend items for match expression"
    assert isinstance(items, list), f"Expected list, got {type(items)}"
    assert len(items) == 6, f"Expected 6 items, got {len(items)}"

    # Check first item
    assert items[0]["label"] == "0-15 min", f"Expected '0-15 min', got {items[0]['label']}"
    assert items[0]["color"] == "#10b981", f"Expected '#10b981', got {items[0]['color']}"

    # Check last item
    assert items[-1]["label"] == "75-90 min", f"Expected '75-90 min', got {items[-1]['label']}"
    assert items[-1]["color"] == "#b91c1c", f"Expected '#b91c1c', got {items[-1]['color']}"

    print("✓ test_extract_legend_items_match passed")


def test_extract_layer_metadata_bezirke():
    """Test extract_layer_metadata for bezirke (gebiete) layers."""
    style_data = {
        "layers": [
            {
                "id": "bezirke-fill",
                "type": "fill",
                "source-layer": "bezirke",
                "paint": {
                    "fill-color": "#3b82f6",
                    "fill-opacity": 0
                }
            },
            {
                "id": "bezirke-outline",
                "type": "line",
                "source-layer": "bezirke",
                "paint": {
                    "line-color": "#3b82f6",
                    "line-opacity": 0.8
                }
            }
        ]
    }

    metadata = extract_layer_metadata(style_data, "bezirke")

    assert metadata is not None, "Expected metadata dict"
    assert metadata.get("type") == "fill", f"Expected type='fill', got {metadata.get('type')}"
    assert metadata.get("color") == "#3b82f6", f"Expected color='#3b82f6', got {metadata.get('color')}"
    assert metadata.get("opacity") == 0, f"Expected opacity=0, got {metadata.get('opacity')}"
    assert metadata.get("legend_items") is None, f"Expected legend_items=None, got {metadata.get('legend_items')}"
    print("✓ test_extract_layer_metadata_bezirke passed")


def test_extract_layer_metadata_line_priority():
    """Test that extract_layer_metadata prioritizes fill over line over symbol."""
    style_data = {
        "layers": [
            {
                "id": "symbol-layer",
                "type": "symbol",
                "source-layer": "test",
                "paint": {"text-color": "#ffffff"}
            },
            {
                "id": "line-layer",
                "type": "line",
                "source-layer": "test",
                "paint": {
                    "line-color": "#ff0000",
                    "line-opacity": 0.7
                }
            },
            {
                "id": "fill-layer",
                "type": "fill",
                "source-layer": "test",
                "paint": {
                    "fill-color": "#3b82f6",
                    "fill-opacity": 0.5
                }
            }
        ]
    }

    metadata = extract_layer_metadata(style_data, "test")

    # Should return fill layer metadata (highest priority)
    assert metadata.get("type") == "fill", f"Expected type='fill', got {metadata.get('type')}"
    assert metadata.get("color") == "#3b82f6", f"Expected color='#3b82f6', got {metadata.get('color')}"
    assert metadata.get("opacity") == 0.5, f"Expected opacity=0.5, got {metadata.get('opacity')}"
    print("✓ test_extract_layer_metadata_line_priority passed")


def test_extract_layer_metadata_no_layers():
    """Test extract_layer_metadata returns None when no matching layers."""
    style_data = {
        "layers": [
            {
                "id": "other-layer",
                "type": "fill",
                "source-layer": "other",
                "paint": {"fill-color": "#ffffff"}
            }
        ]
    }

    metadata = extract_layer_metadata(style_data, "nonexistent")
    assert metadata is None, f"Expected None for non-existent source-layer, got {metadata}"
    print("✓ test_extract_layer_metadata_no_layers passed")


if __name__ == "__main__":
    print("Running layer metadata extraction tests...\n")

    test_extract_layer_color_from_fill()
    test_extract_layer_color_from_line()
    test_extract_layer_color_missing()
    test_extract_layer_opacity_from_fill()
    test_extract_layer_opacity_from_line()
    test_extract_layer_opacity_default()
    test_extract_legend_items_none()
    test_extract_legend_items_interpolate()
    test_extract_legend_items_match()
    test_extract_layer_metadata_bezirke()
    test_extract_layer_metadata_line_priority()
    test_extract_layer_metadata_no_layers()

    print("\n✅ All tests passed!")
