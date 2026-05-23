"""Sunrise/sunset quadrant for the LED dashboard.

Times are passed in as "minutes since start of local day" to keep the
picker pure and CircuitPython-friendly (no datetime dependency).
"""

from brightness import scale


def next_event(sunrise_minutes, sunset_minutes, now_minutes):
    """Pick the next sun event.

    Returns (label, when_minutes) where label is "sunrise" or "sunset".
    If we're past sunset, the next event is the *next day's* sunrise; we
    return the same sunrise_minutes value (caller should treat it as "tomorrow").
    """
    if now_minutes < sunrise_minutes:
        return ("sunrise", sunrise_minutes)
    if now_minutes < sunset_minutes:
        return ("sunset", sunset_minutes)
    return ("sunrise", sunrise_minutes)


_LABEL_COLOR = 0x666666
_TIME_COLOR = 0xFFCC44

_state = {
    "group": None,
    "header": None,
    "time_label": None,
    "last_factor": 1.0,
    "font": None,  # lazily loaded in build()
    "width": 0,
    "height": 0,
}


def build(x, y, width, height):
    """Create the sunrise/sunset quadrant displayio.Group."""
    import displayio
    from adafruit_display_text.label import Label
    from adafruit_bitmap_font import bitmap_font

    if _state["font"] is None:
        _state["font"] = bitmap_font.load_font("/lib/fonts/5x8.bdf")

    group = displayio.Group(x=x, y=y)
    header = Label(_state["font"], text="next", color=_LABEL_COLOR)
    header.x = 2
    header.y = 8
    time_label = Label(_state["font"], text="--:--", color=_TIME_COLOR)
    time_label.x = 2
    time_label.y = 20
    group.append(header)
    group.append(time_label)
    _state["group"] = group
    _state["header"] = header
    _state["time_label"] = time_label
    _state["width"] = width
    _state["height"] = height
    return group


def render(sunrise_minutes, sunset_minutes, now_minutes):
    """Pick the next sun event and update the labels."""
    if _state["time_label"] is None:
        return
    label, when = next_event(sunrise_minutes, sunset_minutes, now_minutes)
    arrow = "^" if label == "sunrise" else "v"
    hh = when // 60
    mm = when % 60
    _state["time_label"].text = "{} {:02d}:{:02d}".format(arrow, hh, mm)


def render_unknown():
    """Show the no-data state."""
    if _state["time_label"] is None:
        return
    _state["time_label"].text = "--:--"


def apply_brightness(factor):
    _state["last_factor"] = factor
    if _state["header"] is not None:
        _state["header"].color = scale(_LABEL_COLOR, factor)
        _state["time_label"].color = scale(_TIME_COLOR, factor)


def set_hidden(hidden):
    if _state["group"] is not None:
        _state["group"].hidden = hidden
