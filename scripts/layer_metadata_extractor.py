#!/usr/bin/env python3
"""
Metadata extractor for MapLibre style layers.

Extracts type, color, opacity, and legend items from style JSON layers
to support automated legend rendering.
"""


def extract_layer_color(layer):
    """
    Extract color from a MapLibre style layer.

    For fill layers, looks for 'fill-color' in paint properties.
    For line layers, looks for 'line-color' in paint properties.
    For symbol layers, tries 'text-color' or 'icon-color'.

    Args:
        layer (dict): A MapLibre layer object

    Returns:
        str: Hex color string (e.g., "#3b82f6") or None if not found
    """
    if "paint" not in layer:
        return None

    paint = layer.get("paint", {})
    layer_type = layer.get("type")

    # Try type-specific color properties
    if layer_type == "fill":
        return paint.get("fill-color")
    elif layer_type == "line":
        return paint.get("line-color")
    elif layer_type == "symbol":
        return paint.get("text-color") or paint.get("icon-color")
    elif layer_type == "background":
        return paint.get("background-color")

    return None


def extract_layer_opacity(layer):
    """
    Extract opacity from a MapLibre style layer.

    For fill layers, looks for 'fill-opacity' in paint properties.
    For line layers, looks for 'line-opacity' in paint properties.
    For symbol layers, tries 'text-opacity' or 'icon-opacity'.
    Defaults to 1 if not specified.

    Args:
        layer (dict): A MapLibre layer object

    Returns:
        float: Opacity value (0-1), defaults to 1
    """
    paint = layer.get("paint", {})
    layer_type = layer.get("type")

    # Try type-specific opacity properties
    if layer_type == "fill":
        opacity = paint.get("fill-opacity")
        if opacity is not None:
            return opacity
    elif layer_type == "line":
        opacity = paint.get("line-opacity")
        if opacity is not None:
            return opacity
    elif layer_type == "symbol":
        opacity = paint.get("text-opacity") or paint.get("icon-opacity")
        if opacity is not None:
            return opacity

    # Default to 1 if not specified
    return 1


def extract_legend_items(style_layers):
    """
    Extract legend items from style layers.

    This function can be extended to extract categorical legend items
    from layers with property-based styling.

    Args:
        style_layers (list): List of MapLibre layer objects

    Returns:
        list: List of {label, color} dicts, or None for simple layers
    """
    # For now, return None for simple layers
    # This will be extended in Task 3 for categorized layers
    return None


def extract_layer_metadata(style_data, source_layer):
    """
    Extract comprehensive metadata for a source layer from a style.

    Determines the primary layer type based on priority: fill > line > symbol.
    Extracts color and opacity from the primary layer.

    Args:
        style_data (dict): A MapLibre style JSON object
        source_layer (str): The source-layer name to extract metadata for

    Returns:
        dict: Metadata object with keys:
            - type: "fill" | "line" | "symbol" (from primary layer)
            - color: hex string or None
            - opacity: number (0-1)
            - legend_items: list or None
        Returns None if no matching layers found for source_layer
    """
    layers = style_data.get("layers", [])

    # Filter layers by source-layer
    matching_layers = [
        layer for layer in layers
        if layer.get("source-layer") == source_layer
    ]

    if not matching_layers:
        return None

    # Determine primary layer type by priority: fill > line > symbol
    primary_layer = None
    layer_type_priority = {"fill": 3, "line": 2, "symbol": 1}

    for layer in matching_layers:
        layer_type = layer.get("type")
        if layer_type in layer_type_priority:
            if primary_layer is None:
                primary_layer = layer
            else:
                current_priority = layer_type_priority.get(layer_type, 0)
                existing_priority = layer_type_priority.get(primary_layer.get("type"), 0)
                if current_priority > existing_priority:
                    primary_layer = layer

    if primary_layer is None:
        return None

    # Extract metadata from primary layer
    return {
        "type": primary_layer.get("type"),
        "color": extract_layer_color(primary_layer),
        "opacity": extract_layer_opacity(primary_layer),
        "legend_items": extract_legend_items(matching_layers),
    }
