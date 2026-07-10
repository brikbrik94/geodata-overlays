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

    Parses categorized styles (interpolate and match expressions) to extract
    time-range legend items with labels and colors.

    Args:
        style_layers (list): List of MapLibre layer objects

    Returns:
        list: List of {label, color} dicts for categorized layers, or None for simple layers
        Example: [{label: "0-15 min", color: "#22c55e"}, {label: "15-30 min", color: "#facc15"}, ...]
    """
    if not style_layers:
        return None

    # Find a fill layer with a color expression
    for layer in style_layers:
        if layer.get("type") != "fill":
            continue

        paint = layer.get("paint", {})
        fill_color = paint.get("fill-color")

        if not isinstance(fill_color, list):
            continue

        # Parse interpolate expression
        if fill_color[0] == "interpolate":
            return _parse_interpolate_expression(fill_color)

        # Parse match expression
        elif fill_color[0] == "match":
            return _parse_match_expression(fill_color)

    return None


def _parse_interpolate_expression(expr):
    """
    Parse MapLibre interpolate expression and extract legend items.

    Expected format:
    ["interpolate", ["linear"], ["get", "property"], stop1, color1, stop2, color2, ...]

    Args:
        expr (list): Interpolate expression array

    Returns:
        list: List of {label, color} dicts representing ranges
    """
    if len(expr) < 5:
        return None

    # Extract stops and colors: [stop1, color1, stop2, color2, ...]
    stops_and_colors = expr[3:]

    if len(stops_and_colors) % 2 != 0:
        return None

    # Parse stops and colors
    stops = []
    colors = []
    for i in range(0, len(stops_and_colors), 2):
        stop = stops_and_colors[i]
        color = stops_and_colors[i + 1]
        if isinstance(stop, (int, float)) and isinstance(color, str):
            stops.append(stop)
            colors.append(color)

    if not stops:
        return None

    # Create legend items from ranges
    legend_items = []
    for i, stop in enumerate(stops):
        color = colors[i]
        if i < len(stops) - 1:
            next_stop = stops[i + 1]
            label = f"{int(stop)}-{int(next_stop)} min"
        else:
            label = f"{int(stop)}+ min"
        legend_items.append({
            "label": label,
            "color": color
        })

    return legend_items


def _parse_match_expression(expr):
    """
    Parse MapLibre match expression and extract legend items.

    Expected format:
    ["match", ["get", "property"], value1, color1, value2, color2, ..., fallback_color]

    Args:
        expr (list): Match expression array

    Returns:
        list: List of {label, color} dicts representing ranges
    """
    if len(expr) < 4:
        return None

    # Extract values and colors: [value1, color1, value2, color2, ..., fallback]
    values_colors_and_fallback = expr[2:]

    if len(values_colors_and_fallback) < 2:
        return None

    # Last element might be fallback if we have odd number of elements
    fallback_color = None
    if len(values_colors_and_fallback) % 2 != 0:
        fallback_color = values_colors_and_fallback[-1]
        values_colors_and_fallback = values_colors_and_fallback[:-1]

    # Parse values and colors
    stops = []
    colors = []
    for i in range(0, len(values_colors_and_fallback), 2):
        value = values_colors_and_fallback[i]
        color = values_colors_and_fallback[i + 1]
        if isinstance(value, (int, float)) and isinstance(color, str):
            stops.append(value)
            colors.append(color)

    if not stops:
        return None

    # Sort stops to ensure they're in order
    stop_color_pairs = list(zip(stops, colors))
    stop_color_pairs.sort(key=lambda x: x[0])
    stops = [x[0] for x in stop_color_pairs]
    colors = [x[1] for x in stop_color_pairs]

    # Create legend items from ranges
    legend_items = []
    for i, stop in enumerate(stops):
        color = colors[i]
        if i == 0:
            # First range: 0 to first stop
            label = f"0-{int(stop)} min"
        else:
            prev_stop = stops[i - 1]
            label = f"{int(prev_stop)}-{int(stop)} min"
        legend_items.append({
            "label": label,
            "color": color
        })

    return legend_items


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
