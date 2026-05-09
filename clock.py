import os
import time
import rtc
import adafruit_ntp


_USE_12H = os.getenv("USE_12_HOUR", "true").lower() == "true"

_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def sync(pool, tz_offset_hours=None):
    if tz_offset_hours is None:
        tz_offset_hours = float(os.getenv("TZ_OFFSET_HOURS", "0"))
    ntp = adafruit_ntp.NTP(pool, tz_offset=tz_offset_hours)
    rtc.RTC().datetime = ntp.datetime


def time_string(blink_on=True):
    t = time.localtime()
    hour = t.tm_hour
    suffix = ""
    if _USE_12H:
        suffix = " AM" if hour < 12 else " PM"
        hour = hour % 12 or 12
    sep = ":" if blink_on else " "
    return "{:02d}{}{:02d}{}".format(hour, sep, t.tm_min, suffix)


def date_string():
    t = time.localtime()
    return "{} {:02d}".format(_MONTHS[t.tm_mon - 1], t.tm_mday)
