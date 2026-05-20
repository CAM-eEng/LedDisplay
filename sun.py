"""Sunrise/sunset quadrant for the LED dashboard.

Times are passed in as "minutes since start of local day" to keep the
picker pure and CircuitPython-friendly (no datetime dependency).
"""


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
