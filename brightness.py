"""Software brightness for HUB75 panel.

The CircuitPython rgbmatrix driver has no working runtime brightness knob,
so we scale every color (label colors and BMP palettes) before assigning.
"""

# Pure helper, importable by tests without any CircuitPython modules.
def scale(color, factor):
    """Multiply each RGB channel of `color` by `factor`, clamped to [0, 1]."""
    if factor < 0.0:
        factor = 0.0
    if factor > 1.0:
        factor = 1.0
    r = int(((color >> 16) & 0xFF) * factor)
    g = int(((color >> 8) & 0xFF) * factor)
    b = int((color & 0xFF) * factor)
    return (r << 16) | (g << 8) | b
