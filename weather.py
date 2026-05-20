"""Open-Meteo weather fetch + quadrant rendering for the LED dashboard."""

from brightness import scale


def code_to_icon(wmo_code):
    """Map a WMO weather code (0-99) to one of our six icon names."""
    if wmo_code == 0:
        return "sun"
    if wmo_code in (1, 2, 3):
        return "cloud"
    if wmo_code in (45, 48):
        return "fog"
    if 51 <= wmo_code <= 67:
        return "rain"
    if 71 <= wmo_code <= 77:
        return "snow"
    if 80 <= wmo_code <= 82:
        return "rain"
    if 85 <= wmo_code <= 86:
        return "snow"
    if 95 <= wmo_code <= 99:
        return "rain"
    return "unknown"


_TEMP_COLOR = 0x44FF66
_ICON_DIR = "/images/weather/"

_state = {
    "group": None,
    "temp_label": None,
    "icon_tile": None,
    "icon_bitmap": None,
    "icon_palette": None,
    "icon_name": None,
    "base_palette": None,    # original RGB ints per palette index, for re-dimming
    "last_factor": 1.0,
    "font": None,            # lazily loaded in build()
    "session": None,         # lazily created in fetch() and reused across calls
}


def build(x, y, width, height):
    """Create the weather quadrant displayio.Group."""
    import displayio
    from adafruit_display_text.label import Label
    from adafruit_bitmap_font import bitmap_font

    if _state["font"] is None:
        _state["font"] = bitmap_font.load_font("/lib/fonts/5x8.bdf")

    group = displayio.Group(x=x, y=y)
    temp_label = Label(_state["font"], text="--C", color=_TEMP_COLOR)
    temp_label.x = 2
    temp_label.y = 5
    group.append(temp_label)
    # Icon tile is loaded lazily by render(); for now insert a placeholder TileGrid
    # using the unknown icon so the slot exists.
    _load_icon(group, "unknown")
    _state["group"] = group
    _state["temp_label"] = temp_label
    return group


def _load_icon(group, name):
    """Replace the current icon (if any) with the named one."""
    import displayio
    import adafruit_imageload

    path = _ICON_DIR + name + ".bmp"
    bitmap, palette = adafruit_imageload.load(
        path, bitmap=displayio.Bitmap, palette=displayio.Palette
    )
    # Remove any existing icon tile.
    if _state["icon_tile"] is not None:
        try:
            group.remove(_state["icon_tile"])
        except ValueError:
            pass
    tile = displayio.TileGrid(bitmap, pixel_shader=palette, x=8, y=14)
    group.append(tile)
    base = [palette[i] for i in range(len(palette))]
    _state["icon_tile"] = tile
    _state["icon_bitmap"] = bitmap
    _state["icon_palette"] = palette
    _state["icon_name"] = name
    _state["base_palette"] = base
    # Re-apply brightness so the new icon matches.
    _apply_palette_brightness(_state["last_factor"])


def _apply_palette_brightness(factor):
    palette = _state["icon_palette"]
    base = _state["base_palette"]
    if palette is None or base is None:
        return
    for i, color in enumerate(base):
        palette[i] = scale(color, factor)


def fetch(pool, lat, lon, tz_name):
    """Single Open-Meteo request returning current + daily sunrise/sunset.

    Returns: {
        "temp_c": float,
        "condition": str (icon name),
        "sunrise_minutes": int (minutes since local midnight today),
        "sunset_minutes": int,
    }
    """
    if _state["session"] is None:
        import ssl
        import adafruit_requests
        _state["session"] = adafruit_requests.Session(
            pool, ssl.create_default_context()
        )
    requests = _state["session"]
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,weather_code"
        "&daily=sunrise,sunset"
        "&timezone={tz}"
        "&temperature_unit=celsius"
    ).format(lat=lat, lon=lon, tz=tz_name)
    resp = requests.get(url)
    try:
        data = resp.json()
    finally:
        resp.close()
    current = data["current"]
    daily = data["daily"]
    sunrise_str = daily["sunrise"][0]    # e.g., "2026-05-19T05:42"
    sunset_str = daily["sunset"][0]
    return {
        "temp_c": float(current["temperature_2m"]),
        "condition": code_to_icon(int(current["weather_code"])),
        "sunrise_minutes": _hhmm_minutes(sunrise_str),
        "sunset_minutes": _hhmm_minutes(sunset_str),
    }


def _hhmm_minutes(iso_str):
    """Extract HH:MM from an Open-Meteo local-time ISO string and return minutes-since-midnight."""
    # Format: "YYYY-MM-DDTHH:MM"
    hh = int(iso_str[11:13])
    mm = int(iso_str[14:16])
    return hh * 60 + mm


def render(data):
    """Update the weather quadrant from a fetch() result."""
    if _state["temp_label"] is None:
        return
    _state["temp_label"].text = "{}C".format(int(round(data["temp_c"])))
    if data["condition"] != _state["icon_name"] and _state["group"] is not None:
        _load_icon(_state["group"], data["condition"])


def render_unknown():
    """Show the failure state: '--C' + unknown icon."""
    if _state["temp_label"] is None:
        return
    _state["temp_label"].text = "--C"
    if _state["icon_name"] != "unknown" and _state["group"] is not None:
        _load_icon(_state["group"], "unknown")


def apply_brightness(factor):
    _state["last_factor"] = factor
    if _state["temp_label"] is not None:
        _state["temp_label"].color = scale(_TEMP_COLOR, factor)
    _apply_palette_brightness(factor)
