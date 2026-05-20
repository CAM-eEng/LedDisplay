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
