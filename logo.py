"""Static Arc Raiders logo, bottom-right quadrant (32x32)."""
from brightness import scale


_state = {
    "group": None,
    "tile": None,
    "palette": None,
    "base_palette": None,
    "last_factor": 1.0,
}


def build(x, y, width, height, path="/images/arc_raiders.bmp"):
    """Load the logo BMP and return a positioned displayio.Group.

    If the file is missing, returns an empty group (logo quadrant stays blank)
    and prints a warning to serial.
    """
    import displayio
    import adafruit_imageload
    group = displayio.Group(x=x, y=y)
    try:
        bitmap, palette = adafruit_imageload.load(
            path, bitmap=displayio.Bitmap, palette=displayio.Palette
        )
    except (OSError, ValueError) as e:
        print("logo: could not load", path, "-", e)
        _state["group"] = group
        return group
    tile = displayio.TileGrid(bitmap, pixel_shader=palette)
    group.append(tile)
    _state["group"] = group
    _state["tile"] = tile
    _state["palette"] = palette
    _state["base_palette"] = [palette[i] for i in range(len(palette))]
    return group


def apply_brightness(factor):
    _state["last_factor"] = factor
    palette = _state["palette"]
    base = _state["base_palette"]
    if palette is None or base is None:
        return
    for i, color in enumerate(base):
        palette[i] = scale(color, factor)
