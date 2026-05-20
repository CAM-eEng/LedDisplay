"""Clock quadrant: top-left 32x32. Time + zone abbreviation + date."""
import os
import time

import rtc
import adafruit_ntp
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

import tz
from brightness import scale


_FONT_TIME = bitmap_font.load_font("/lib/fonts/6x10.bdf")
_FONT_SMALL = bitmap_font.load_font("/lib/fonts/5x8.bdf")

_TIME_COLOR = 0xFFAA00
_ZONE_COLOR = 0x4488FF
_DATE_COLOR = 0xCCCCCC

_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)

_TZ_NAME = os.getenv("TZ_NAME", "UTC")
_USE_12H = os.getenv("USE_12_HOUR", "true").lower() == "true"

_state = {
    "group": None,
    "time_label": None,
    "zone_label": None,
    "date_label": None,
    "last_utc": None,        # last struct_time in UTC (from NTP) for DST queries
    "last_factor": 1.0,
}


def build(x, y, width, height):
    """Create the clock quadrant displayio.Group."""
    group = displayio.Group(x=x, y=y)
    time_label = Label(_FONT_TIME, text="boot", color=_TIME_COLOR)
    time_label.x = 1
    time_label.y = 6
    zone_label = Label(_FONT_SMALL, text="", color=_ZONE_COLOR)
    zone_label.x = 1
    zone_label.y = 16
    date_label = Label(_FONT_SMALL, text="", color=_DATE_COLOR)
    date_label.x = 1
    date_label.y = 26
    group.append(time_label)
    group.append(zone_label)
    group.append(date_label)
    _state["group"] = group
    _state["time_label"] = time_label
    _state["zone_label"] = zone_label
    _state["date_label"] = date_label
    return group


def set_status(text):
    """Show a short status message on the time line (used during boot)."""
    if _state["time_label"] is None:
        return
    _state["time_label"].text = text
    _state["zone_label"].text = ""
    _state["date_label"].text = ""


def sync(pool):
    """NTP fetch (UTC), compute current local offset from DST, set RTC to local time."""
    ntp = adafruit_ntp.NTP(pool, tz_offset=0)
    utc_now = ntp.datetime
    _state["last_utc"] = utc_now
    offset_hours = tz.zone_offset(utc_now, _TZ_NAME)
    local_epoch = time.mktime(utc_now) + int(offset_hours * 3600)
    rtc.RTC().datetime = time.localtime(local_epoch)


def zone_abbrev():
    """Return the current zone abbreviation based on the last NTP UTC reading."""
    if _state["last_utc"] is None:
        return ""
    return tz.zone_abbrev(_state["last_utc"], _TZ_NAME)


def _format_time(t, blink_on):
    hour = t.tm_hour
    if _USE_12H:
        hour = hour % 12 or 12
    sep = ":" if blink_on else " "
    if _USE_12H:
        # No AM/PM suffix — the zone label below replaces it.
        return "{}{}{:02d}".format(hour, sep, t.tm_min)
    return "{:02d}{}{:02d}".format(hour, sep, t.tm_min)


def update(blink_on=True):
    """Refresh time/zone/date labels from the RTC."""
    if _state["time_label"] is None:
        return
    now = time.localtime()
    _state["time_label"].text = _format_time(now, blink_on)
    _state["zone_label"].text = zone_abbrev()
    _state["date_label"].text = "{} {:02d}".format(_MONTHS[now.tm_mon - 1], now.tm_mday)


def apply_brightness(factor):
    """Re-tint all labels for a new brightness factor."""
    _state["last_factor"] = factor
    if _state["time_label"] is not None:
        _state["time_label"].color = scale(_TIME_COLOR, factor)
        _state["zone_label"].color = scale(_ZONE_COLOR, factor)
        _state["date_label"].color = scale(_DATE_COLOR, factor)
