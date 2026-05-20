"""Open-Meteo weather fetch + quadrant rendering for the LED dashboard."""


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
