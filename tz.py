"""Pure US DST + zone math. No CircuitPython imports."""


def _weekday(year, month, day):
    """Return weekday: 0=Mon, 1=Tue, ..., 6=Sun."""
    if month < 3:
        month += 12
        year -= 1
    k = year % 100
    j = year // 100
    h = (day + (13 * (month + 1)) // 5 + k + k // 4 + j // 4 + 5 * j) % 7
    # Zeller's h: 0=Sat, 1=Sun, ..., 6=Fri. Convert to 0=Mon..6=Sun.
    return (h + 5) % 7


def _nth_sunday_of_month(year, month, n):
    """Return day-of-month for the nth Sunday (1-indexed)."""
    first_wd = _weekday(year, month, 1)
    days_to_first_sunday = (6 - first_wd) % 7
    return 1 + days_to_first_sunday + (n - 1) * 7


# (std_offset_hours, dst_offset_hours, std_abbrev, dst_abbrev)
_ZONES = {
    "America/Los_Angeles": (-8, -7, "PST", "PDT"),
    "America/Denver":      (-7, -6, "MST", "MDT"),
    "America/Chicago":     (-6, -5, "CST", "CDT"),
    "America/New_York":    (-5, -4, "EST", "EDT"),
}


def is_dst(utc_struct_time, tz_name):
    """Return True if the given UTC time falls inside the US DST window for tz_name."""
    if tz_name not in _ZONES:
        return False
    std, dst, _, _ = _ZONES[tz_name]
    year = utc_struct_time.tm_year
    start_day = _nth_sunday_of_month(year, 3, 2)   # 2nd Sun March
    end_day = _nth_sunday_of_month(year, 11, 1)    # 1st Sun November
    # DST begins at 02:00 LOCAL standard time = (-std + 2) UTC hours.
    # DST ends at 02:00 LOCAL daylight time = (-dst + 2) UTC hours.
    start_hour_utc = -std + 2
    end_hour_utc = -dst + 2
    cur = (utc_struct_time.tm_mon, utc_struct_time.tm_mday,
           utc_struct_time.tm_hour, utc_struct_time.tm_min)
    start = (3, start_day, start_hour_utc, 0)
    end = (11, end_day, end_hour_utc, 0)
    return start <= cur < end


def zone_offset(utc_struct_time, tz_name):
    """Return the local UTC offset in hours for tz_name at the given UTC time."""
    if tz_name not in _ZONES:
        return 0
    std, dst, _, _ = _ZONES[tz_name]
    return dst if is_dst(utc_struct_time, tz_name) else std


def zone_abbrev(utc_struct_time, tz_name):
    """Return the zone abbreviation (e.g., "PST"/"PDT") for tz_name at the given UTC time."""
    if tz_name not in _ZONES:
        return "UTC"
    _, _, std_abbr, dst_abbr = _ZONES[tz_name]
    return dst_abbr if is_dst(utc_struct_time, tz_name) else std_abbr
