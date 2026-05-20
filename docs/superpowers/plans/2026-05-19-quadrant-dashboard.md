# Quadrant Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the existing single-line clock on the 64×64 HUB75 panel into a four-quadrant dashboard (clock+zone+date, weather, next-sun-event, Arc Raiders logo) with automatic US DST handling and software brightness control via the on-board UP/DOWN buttons.

**Architecture:** Pure-Python DST and formatting logic is isolated in `tz.py` so it can be unit-tested under CPython. Each quadrant is its own CircuitPython module exposing `build`, `update`/`render`, and `apply_brightness`. `code.py` is a thin wiring + main-loop layer. Weather and sun data come from a single Open-Meteo request shared between two quadrants. Brightness is implemented in software by scaling every color (labels and BMP palettes) by a global factor changed by edge-triggered button presses.

**Tech Stack:** CircuitPython 9+, MatrixPortal S3, `rgbmatrix`/`displayio`, `adafruit_matrixportal`, `adafruit_display_text`, `adafruit_bitmap_font`, `adafruit_imageload`, `adafruit_ntp`, `adafruit_requests` (or `socketpool` + `ssl` + stdlib JSON), Open-Meteo. Tests use `pytest` running on the host machine against pure-Python helpers; CircuitPython modules are not imported from tests.

**Spec:** `docs/superpowers/specs/2026-05-19-quadrant-dashboard-design.md`

---

## File Map

### New
- `tz.py` — Pure US DST math, zone offset, zone abbreviation. No CircuitPython imports.
- `brightness.py` — `Brightness` class with `scale()` (pure math) and `poll()` (hardware-dependent).
- `weather.py` — Open-Meteo fetch, WMO-code → icon mapping (pure), `build`/`render`/`apply_brightness`.
- `sun.py` — Next-event picker (pure), `build`/`render`/`apply_brightness`.
- `logo.py` — Loads `images/arc_raiders.bmp` into a `displayio.Group`, palette-based dimming.
- `images/weather/{sun,cloud,rain,snow,fog,unknown}.bmp` — 16×16 weather icons (generated via host script).
- `lib/fonts/{5x8.bdf,6x10.bdf}` — Bitmap fonts (downloaded from Adafruit).
- `scripts/make_weather_icons.py` — Host-side PIL script that produces the six 16×16 BMPs.
- `tests/conftest.py` — Adds project root to `sys.path` so tests can import `tz`, `brightness`, etc.
- `tests/test_tz.py`, `tests/test_brightness.py`, `tests/test_weather.py`, `tests/test_sun.py` — Unit tests.
- `pyproject.toml` — Minimal pytest config so `pytest` discovers `tests/`.

### Modified
- `clock.py` — Re-written to use `tz.py`; gains `build`/`update`/`apply_brightness`/`zone_abbrev`.
- `code.py` — Re-written for four-quadrant layout, brightness polling, boot status states, cadence-based loop.
- `settings.toml` — Replace `TZ_OFFSET_HOURS` with `TZ_NAME`; add weather and brightness keys.

### Untouched
- `wifi_setup.py`, `deploy.sh`, `install_libs.sh`, `test_panel.py`, `led_panel_spec.txt`, `.gitignore`.

---

## Task 1: Test harness

**Files:**
- Create: `pyproject.toml`
- Create: `tests/conftest.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `pyproject.toml` with minimal pytest config**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-ra -q"
```

- [ ] **Step 2: Create empty `tests/__init__.py`**

```python
```

- [ ] **Step 3: Create `tests/conftest.py`**

```python
"""Make the project root importable so tests can `import tz`, `import brightness`, etc.

These modules are pure Python and don't depend on CircuitPython hardware modules,
so no stubbing is required.
"""
```

- [ ] **Step 4: Verify pytest runs (and finds no tests yet)**

Run: `pytest`
Expected: `no tests ran` exit 5, no import errors.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/
git commit -m "Add pytest harness"
```

---

## Task 2: tz.py — weekday helper (TDD)

**Files:**
- Create: `tz.py`
- Create: `tests/test_tz.py`

- [ ] **Step 1: Write failing tests for `_weekday`**

`tests/test_tz.py`:

```python
import tz


def test_weekday_returns_monday_for_known_monday():
    # 2024-01-01 was a Monday
    assert tz._weekday(2024, 1, 1) == 0


def test_weekday_returns_sunday_for_known_sunday():
    # 2024-03-10 was a Sunday (2nd Sunday of March 2024)
    assert tz._weekday(2024, 3, 10) == 6


def test_weekday_returns_friday_for_first_of_march_2024():
    # 2024-03-01 was a Friday
    assert tz._weekday(2024, 3, 1) == 4


def test_weekday_handles_january_correctly():
    # Zeller treats Jan/Feb as months 13/14 of previous year; verify the wrap.
    # 2025-01-01 was a Wednesday
    assert tz._weekday(2025, 1, 1) == 2


def test_weekday_handles_century_boundary():
    # 2000-01-01 was a Saturday
    assert tz._weekday(2000, 1, 1) == 5
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/test_tz.py -v`
Expected: 5 failures with `ModuleNotFoundError: No module named 'tz'`.

- [ ] **Step 3: Implement `_weekday` in `tz.py`**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/test_tz.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add tz.py tests/test_tz.py
git commit -m "Add weekday helper for DST math"
```

---

## Task 3: tz.py — nth Sunday of month (TDD)

**Files:**
- Modify: `tz.py`
- Modify: `tests/test_tz.py`

- [ ] **Step 1: Append failing tests for `_nth_sunday_of_month`**

Append to `tests/test_tz.py`:

```python
def test_second_sunday_of_march_2024():
    # 2nd Sunday of March 2024 = March 10
    assert tz._nth_sunday_of_month(2024, 3, 2) == 10


def test_first_sunday_of_november_2024():
    # 1st Sunday of November 2024 = November 3
    assert tz._nth_sunday_of_month(2024, 11, 1) == 3


def test_second_sunday_of_march_2026():
    # 2nd Sunday of March 2026 = March 8
    assert tz._nth_sunday_of_month(2026, 3, 2) == 8


def test_first_sunday_of_november_2026():
    # 1st Sunday of November 2026 = November 1
    assert tz._nth_sunday_of_month(2026, 11, 1) == 1


def test_first_sunday_when_month_starts_on_sunday():
    # November 2026 starts on a Sunday — the 1st Sunday is the 1st.
    assert tz._nth_sunday_of_month(2026, 11, 1) == 1
```

- [ ] **Step 2: Run tests — verify the new ones fail**

Run: `pytest tests/test_tz.py -v`
Expected: 5 failures with `AttributeError: module 'tz' has no attribute '_nth_sunday_of_month'`.

- [ ] **Step 3: Implement `_nth_sunday_of_month`**

Append to `tz.py`:

```python
def _nth_sunday_of_month(year, month, n):
    """Return day-of-month for the nth Sunday (1-indexed)."""
    first_wd = _weekday(year, month, 1)
    days_to_first_sunday = (6 - first_wd) % 7
    return 1 + days_to_first_sunday + (n - 1) * 7
```

- [ ] **Step 4: Run tests — verify all pass**

Run: `pytest tests/test_tz.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add tz.py tests/test_tz.py
git commit -m "Add nth-Sunday-of-month helper"
```

---

## Task 4: tz.py — is_dst (TDD)

**Files:**
- Modify: `tz.py`
- Modify: `tests/test_tz.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/test_tz.py`:

```python
import time


def _utc(year, month, day, hour=12, minute=0):
    """Build a struct_time with tm_year, tm_mon, tm_mday, tm_hour, tm_min set."""
    return time.struct_time((year, month, day, hour, minute, 0, 0, 0, 0))


def test_is_dst_returns_false_in_january():
    assert tz.is_dst(_utc(2026, 1, 15), "America/Los_Angeles") is False


def test_is_dst_returns_true_in_july():
    assert tz.is_dst(_utc(2026, 7, 4), "America/Los_Angeles") is True


def test_is_dst_just_before_spring_forward_boundary():
    # 2026 spring forward: 2nd Sun March = March 8; switch at 02:00 PST = 10:00 UTC
    # 09:59 UTC is still standard time.
    assert tz.is_dst(_utc(2026, 3, 8, 9, 59), "America/Los_Angeles") is False


def test_is_dst_at_spring_forward_boundary():
    # 10:00 UTC on March 8, 2026 = 02:00 PST = first moment of PDT
    assert tz.is_dst(_utc(2026, 3, 8, 10, 0), "America/Los_Angeles") is True


def test_is_dst_just_before_fall_back_boundary():
    # 2026 fall back: 1st Sun November = November 1; switch at 02:00 PDT = 09:00 UTC
    # 08:59 UTC is still daylight time.
    assert tz.is_dst(_utc(2026, 11, 1, 8, 59), "America/Los_Angeles") is True


def test_is_dst_at_fall_back_boundary():
    # 09:00 UTC on November 1, 2026 = 02:00 PDT = first moment of PST
    assert tz.is_dst(_utc(2026, 11, 1, 9, 0), "America/Los_Angeles") is False


def test_is_dst_unknown_zone_returns_false():
    assert tz.is_dst(_utc(2026, 7, 4), "Europe/Berlin") is False


def test_is_dst_eastern_time_boundary_differs_from_pacific():
    # March 8, 2026, 07:00 UTC = 02:00 EST → start of EDT
    # Same instant in Pacific = 23:00 UTC March 7 = still PST
    assert tz.is_dst(_utc(2026, 3, 8, 7, 0), "America/New_York") is True
    assert tz.is_dst(_utc(2026, 3, 8, 7, 0), "America/Los_Angeles") is False
```

- [ ] **Step 2: Run tests — verify the new ones fail**

Run: `pytest tests/test_tz.py -v`
Expected: 8 failures with `AttributeError: module 'tz' has no attribute 'is_dst'`.

- [ ] **Step 3: Implement zone table and `is_dst`**

Append to `tz.py`:

```python
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
```

- [ ] **Step 4: Run tests — verify all pass**

Run: `pytest tests/test_tz.py -v`
Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
git add tz.py tests/test_tz.py
git commit -m "Add is_dst with US DST window math"
```

---

## Task 5: tz.py — zone_offset and zone_abbrev (TDD)

**Files:**
- Modify: `tz.py`
- Modify: `tests/test_tz.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/test_tz.py`:

```python
def test_zone_offset_pacific_winter():
    assert tz.zone_offset(_utc(2026, 1, 15), "America/Los_Angeles") == -8


def test_zone_offset_pacific_summer():
    assert tz.zone_offset(_utc(2026, 7, 4), "America/Los_Angeles") == -7


def test_zone_offset_eastern_winter():
    assert tz.zone_offset(_utc(2026, 1, 15), "America/New_York") == -5


def test_zone_offset_unknown_zone_returns_zero():
    assert tz.zone_offset(_utc(2026, 7, 4), "Mars/Olympus") == 0


def test_zone_abbrev_pacific_winter():
    assert tz.zone_abbrev(_utc(2026, 1, 15), "America/Los_Angeles") == "PST"


def test_zone_abbrev_pacific_summer():
    assert tz.zone_abbrev(_utc(2026, 7, 4), "America/Los_Angeles") == "PDT"


def test_zone_abbrev_eastern_summer():
    assert tz.zone_abbrev(_utc(2026, 7, 4), "America/New_York") == "EDT"


def test_zone_abbrev_unknown_zone_returns_utc():
    assert tz.zone_abbrev(_utc(2026, 7, 4), "Mars/Olympus") == "UTC"
```

- [ ] **Step 2: Run tests — verify the new ones fail**

Run: `pytest tests/test_tz.py -v`
Expected: 8 failures.

- [ ] **Step 3: Implement `zone_offset` and `zone_abbrev`**

Append to `tz.py`:

```python
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
```

- [ ] **Step 4: Run tests — verify all pass**

Run: `pytest tests/test_tz.py -v`
Expected: 26 passed.

- [ ] **Step 5: Commit**

```bash
git add tz.py tests/test_tz.py
git commit -m "Add zone_offset and zone_abbrev"
```

---

## Task 6: brightness.py — scale() (TDD)

**Files:**
- Create: `brightness.py`
- Create: `tests/test_brightness.py`

- [ ] **Step 1: Write failing tests**

`tests/test_brightness.py`:

```python
from brightness import scale


def test_scale_full_brightness_returns_unchanged():
    assert scale(0xFFAA00, 1.0) == 0xFFAA00


def test_scale_zero_brightness_returns_black():
    assert scale(0xFFAA00, 0.0) == 0x000000


def test_scale_half_brightness_halves_each_channel():
    # 0xFFAA00 = (255, 170, 0); 0.5 = (127, 85, 0)
    assert scale(0xFFAA00, 0.5) == 0x7F5500


def test_scale_clamps_high_bound():
    # Defensive: caller passing > 1.0 should not overflow into other channels.
    result = scale(0xFFFFFF, 1.5)
    assert result == 0xFFFFFF


def test_scale_clamps_low_bound():
    assert scale(0xFFFFFF, -0.5) == 0x000000


def test_scale_pure_blue():
    assert scale(0x0000FF, 0.5) == 0x00007F
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/test_brightness.py -v`
Expected: 6 failures.

- [ ] **Step 3: Create `brightness.py` with `scale` (module-level, importable by tests)**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/test_brightness.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add brightness.py tests/test_brightness.py
git commit -m "Add brightness.scale helper"
```

---

## Task 7: brightness.py — Brightness class

**Files:**
- Modify: `brightness.py`

This task adds the `Brightness` class that depends on `board` and `digitalio`. These imports only succeed on CircuitPython, so the class is **not** unit-tested. The pure `scale()` helper from Task 6 stays at module top-level so tests keep working.

- [ ] **Step 1: Append the `Brightness` class to `brightness.py`**

```python
_LEVELS = (0.10, 0.25, 0.50, 0.75, 1.00)


class Brightness:
    """Edge-triggered up/down button polling with discrete brightness levels.

    `factor` is the current scale in [0, 1] for use with `scale(color, factor)`.
    `poll()` returns True when the level changed this tick.
    """

    def __init__(self, default_index=3):
        import board
        import digitalio
        if default_index < 0:
            default_index = 0
        if default_index >= len(_LEVELS):
            default_index = len(_LEVELS) - 1
        self._index = default_index
        self._up = digitalio.DigitalInOut(board.BUTTON_UP)
        self._up.switch_to_input(pull=digitalio.Pull.UP)
        self._down = digitalio.DigitalInOut(board.BUTTON_DOWN)
        self._down.switch_to_input(pull=digitalio.Pull.UP)
        # Buttons are active-low. Initialize "last" to released (True).
        self._last_up = True
        self._last_down = True

    @property
    def factor(self):
        return _LEVELS[self._index]

    def poll(self):
        """Return True if the level changed on this call."""
        up_now = self._up.value
        down_now = self._down.value
        changed = False
        # Trigger on falling edge (released -> pressed).
        if (not up_now) and self._last_up:
            new_index = min(self._index + 1, len(_LEVELS) - 1)
            if new_index != self._index:
                self._index = new_index
                changed = True
        if (not down_now) and self._last_down:
            new_index = max(self._index - 1, 0)
            if new_index != self._index:
                self._index = new_index
                changed = True
        self._last_up = up_now
        self._last_down = down_now
        return changed
```

- [ ] **Step 2: Run all tests — verify nothing broke**

Run: `pytest`
Expected: All previously-passing tests still pass. (Imports are inside `__init__`, so `brightness.scale` keeps working without hardware.)

- [ ] **Step 3: Commit**

```bash
git add brightness.py
git commit -m "Add Brightness class with edge-triggered button polling"
```

---

## Task 8: weather.py — WMO code to icon mapping (TDD)

**Files:**
- Create: `weather.py`
- Create: `tests/test_weather.py`

- [ ] **Step 1: Write failing tests**

`tests/test_weather.py`:

```python
from weather import code_to_icon


def test_clear_sky_maps_to_sun():
    assert code_to_icon(0) == "sun"


def test_partly_cloudy_maps_to_cloud():
    # WMO codes 1, 2, 3 = mainly clear, partly cloudy, overcast
    assert code_to_icon(2) == "cloud"
    assert code_to_icon(3) == "cloud"


def test_fog_maps_to_fog():
    # 45 = fog, 48 = depositing rime fog
    assert code_to_icon(45) == "fog"
    assert code_to_icon(48) == "fog"


def test_drizzle_and_rain_map_to_rain():
    # 51-67 covers drizzle, rain
    assert code_to_icon(51) == "rain"
    assert code_to_icon(61) == "rain"
    assert code_to_icon(65) == "rain"


def test_snow_maps_to_snow():
    # 71-77 covers snow
    assert code_to_icon(71) == "snow"
    assert code_to_icon(75) == "snow"


def test_showers_map_to_rain():
    # 80-82 = rain showers
    assert code_to_icon(80) == "rain"


def test_snow_showers_map_to_snow():
    # 85-86 = snow showers
    assert code_to_icon(85) == "snow"


def test_thunderstorm_maps_to_rain():
    # 95-99 = thunderstorms (we lump into rain since we don't have a storm icon)
    assert code_to_icon(95) == "rain"


def test_unknown_code_maps_to_unknown():
    assert code_to_icon(999) == "unknown"
    assert code_to_icon(-1) == "unknown"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/test_weather.py -v`
Expected: 9 failures (`ModuleNotFoundError: No module named 'weather'`).

- [ ] **Step 3: Create `weather.py` with the mapping**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/test_weather.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add weather.py tests/test_weather.py
git commit -m "Add WMO code to icon mapping"
```

---

## Task 9: sun.py — next event picker (TDD)

**Files:**
- Create: `sun.py`
- Create: `tests/test_sun.py`

- [ ] **Step 1: Write failing tests**

`tests/test_sun.py`:

```python
from sun import next_event


# All times in this module are "minutes since start of day local".
SUNRISE = 6 * 60 + 30        # 06:30
SUNSET = 20 * 60 + 45        # 20:45


def test_before_sunrise_picks_sunrise():
    assert next_event(SUNRISE, SUNSET, now_minutes=5 * 60) == ("sunrise", SUNRISE)


def test_at_sunrise_picks_sunset():
    # Exactly at sunrise, the next event is sunset.
    assert next_event(SUNRISE, SUNSET, now_minutes=SUNRISE) == ("sunset", SUNSET)


def test_midday_picks_sunset():
    assert next_event(SUNRISE, SUNSET, now_minutes=12 * 60) == ("sunset", SUNSET)


def test_after_sunset_picks_tomorrow_sunrise():
    # After sunset, the next event is tomorrow's sunrise.
    label, when = next_event(SUNRISE, SUNSET, now_minutes=22 * 60)
    assert label == "sunrise"
    assert when == SUNRISE


def test_just_before_sunset():
    assert next_event(SUNRISE, SUNSET, now_minutes=SUNSET - 1) == ("sunset", SUNSET)
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/test_sun.py -v`
Expected: 5 failures.

- [ ] **Step 3: Create `sun.py` with `next_event`**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/test_sun.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add sun.py tests/test_sun.py
git commit -m "Add sun next-event picker"
```

---

## Task 10: Settings file

**Files:**
- Modify: `settings.toml`

- [ ] **Step 1: Replace `settings.toml` contents**

```toml
CIRCUITPY_WIFI_SSID = "CabinInTheHills"
CIRCUITPY_WIFI_PASSWORD = "PizzaPizzaPumpkin66!"

TZ_NAME = "America/Los_Angeles"
USE_12_HOUR = "true"

WEATHER_LAT = "47.6062"
WEATHER_LON = "-122.3321"
WEATHER_REFRESH_MIN = "15"

BRIGHTNESS_DEFAULT = "3"
```

- [ ] **Step 2: Commit**

```bash
git add settings.toml
git commit -m "Switch settings to TZ_NAME and add weather/brightness keys"
```

---

## Task 11: Generate weather icons (host script)

**Files:**
- Create: `scripts/make_weather_icons.py`
- Create: `images/weather/{sun,cloud,rain,snow,fog,unknown}.bmp` (output)

- [ ] **Step 1: Create the host-side generator**

`scripts/make_weather_icons.py`:

```python
"""Generate six 16x16 BMP weather icons under images/weather/.

Run on the host (not on the device):
    python scripts/make_weather_icons.py

Requires Pillow:  pip install Pillow
"""
import os
from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "images", "weather")
SIZE = 16


def _new():
    return Image.new("RGB", (SIZE, SIZE), (0, 0, 0))


def sun_icon():
    img = _new()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 11, 11], fill=(255, 200, 0))
    for dx, dy in [(0, 8), (8, 0), (15, 8), (8, 15), (2, 2), (13, 2), (2, 13), (13, 13)]:
        d.point((dx, dy), fill=(255, 200, 0))
    return img


def cloud_icon():
    img = _new()
    d = ImageDraw.Draw(img)
    d.ellipse([2, 6, 9, 12], fill=(200, 200, 200))
    d.ellipse([6, 3, 13, 10], fill=(220, 220, 220))
    d.rectangle([3, 9, 13, 12], fill=(210, 210, 210))
    return img


def rain_icon():
    img = cloud_icon()
    d = ImageDraw.Draw(img)
    for x in (4, 8, 12):
        d.line([(x, 13), (x - 1, 15)], fill=(80, 160, 255))
    return img


def snow_icon():
    img = cloud_icon()
    d = ImageDraw.Draw(img)
    for x in (4, 8, 12):
        d.point((x, 13), fill=(255, 255, 255))
        d.point((x, 15), fill=(255, 255, 255))
    return img


def fog_icon():
    img = _new()
    d = ImageDraw.Draw(img)
    for y in (4, 7, 10, 13):
        d.line([(1, y), (14, y)], fill=(180, 180, 200))
    return img


def unknown_icon():
    img = _new()
    d = ImageDraw.Draw(img)
    d.text((5, 3), "?", fill=(255, 255, 255))
    return img


GENERATORS = {
    "sun": sun_icon,
    "cloud": cloud_icon,
    "rain": rain_icon,
    "snow": snow_icon,
    "fog": fog_icon,
    "unknown": unknown_icon,
}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, gen in GENERATORS.items():
        path = os.path.join(OUT_DIR, name + ".bmp")
        gen().save(path, "BMP")
        print("wrote", path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Install Pillow if not present**

Run: `python -c "import PIL" 2>/dev/null || pip install --user Pillow`
Expected: silent (already installed) or successful install.

- [ ] **Step 3: Run the generator**

Run: `python scripts/make_weather_icons.py`
Expected: six `wrote .../images/weather/<name>.bmp` lines.

- [ ] **Step 4: Verify the BMPs exist and are 16×16**

Run: `python -c "from PIL import Image; [print(p, Image.open(p).size) for p in __import__('glob').glob('images/weather/*.bmp')]"`
Expected: six lines, each `(16, 16)`.

- [ ] **Step 5: Commit**

```bash
git add scripts/make_weather_icons.py images/weather/
git commit -m "Generate 16x16 weather icon BMPs"
```

---

## Task 12: Bitmap fonts

**Files:**
- Create: `lib/fonts/5x8.bdf`
- Create: `lib/fonts/6x10.bdf`

- [ ] **Step 1: Create the fonts directory and download both BDFs from Adafruit's CircuitPython fonts bundle**

Run:

```bash
mkdir -p lib/fonts
curl -fsSL -o lib/fonts/5x8.bdf \
  https://raw.githubusercontent.com/adafruit/circuitpython-fonts/main/bdf/5x8.bdf
curl -fsSL -o lib/fonts/6x10.bdf \
  https://raw.githubusercontent.com/adafruit/circuitpython-fonts/main/bdf/6x10.bdf
```

Expected: two files, each non-empty.

If those URLs 404 (Adafruit moves fonts around occasionally), use the equivalent files from the Adafruit fonts repo at https://github.com/adafruit/Adafruit-GFX-Library/tree/master/Fonts as a fallback (use any BDF-format 5×8 and 6×10 monospace font). Note in the commit message which source you used.

- [ ] **Step 2: Sanity-check the files are valid BDFs**

Run: `head -1 lib/fonts/5x8.bdf lib/fonts/6x10.bdf`
Expected: each file starts with `STARTFONT 2.1`.

- [ ] **Step 3: Commit**

```bash
git add lib/fonts/
git commit -m "Add 5x8 and 6x10 BDF fonts"
```

---

## Task 13: Rewrite clock.py

**Files:**
- Modify: `clock.py`

This rewrite is large because the module changes shape. The pure-logic pieces (sync's offset computation, format string) are already exercised by `tz.py` tests; the displayio parts can only be smoke-tested on-device.

- [ ] **Step 1: Replace `clock.py` contents**

```python
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
```

- [ ] **Step 2: Run all tests — make sure nothing regressed**

Run: `pytest`
Expected: tests pass (clock.py imports CircuitPython modules at the top, so it isn't imported by the test suite — `tz` tests + others still pass).

- [ ] **Step 3: Commit**

```bash
git add clock.py
git commit -m "Rewrite clock.py for quadrant layout, DST, and brightness"
```

---

## Task 14: Implement weather.py rendering

**Files:**
- Modify: `weather.py`

- [ ] **Step 1: Append render + fetch code to `weather.py`**

Append (do not remove the existing `code_to_icon`):

```python
import os
import time

import adafruit_requests
import displayio
import adafruit_imageload
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

from brightness import scale


_FONT_SMALL = bitmap_font.load_font("/lib/fonts/5x8.bdf")
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
}


def build(x, y, width, height):
    """Create the weather quadrant displayio.Group."""
    group = displayio.Group(x=x, y=y)
    temp_label = Label(_FONT_SMALL, text="--C", color=_TEMP_COLOR)
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
    import ssl
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
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
```

- [ ] **Step 2: Run all tests — verify nothing regressed**

Run: `pytest`
Expected: tests pass. `weather.code_to_icon` still works because the heavy imports are below the function it tests.

- [ ] **Step 3: Commit**

```bash
git add weather.py
git commit -m "Add weather fetch, render, and brightness handling"
```

---

## Task 15: Implement sun.py rendering

**Files:**
- Modify: `sun.py`

- [ ] **Step 1: Append render + brightness code to `sun.py`**

Append (do not remove `next_event`):

```python
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

from brightness import scale


_FONT_SMALL = bitmap_font.load_font("/lib/fonts/5x8.bdf")

_LABEL_COLOR = 0x666666
_TIME_COLOR = 0xFFCC44

_state = {
    "group": None,
    "header": None,
    "time_label": None,
    "last_factor": 1.0,
}


def build(x, y, width, height):
    """Create the sunrise/sunset quadrant displayio.Group."""
    group = displayio.Group(x=x, y=y)
    header = Label(_FONT_SMALL, text="next", color=_LABEL_COLOR)
    header.x = 2
    header.y = 8
    time_label = Label(_FONT_SMALL, text="--:--", color=_TIME_COLOR)
    time_label.x = 2
    time_label.y = 20
    group.append(header)
    group.append(time_label)
    _state["group"] = group
    _state["header"] = header
    _state["time_label"] = time_label
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
```

- [ ] **Step 2: Run all tests — verify nothing regressed**

Run: `pytest`
Expected: still passing (sun.next_event tests are unaffected; the new imports are below the function).

- [ ] **Step 3: Commit**

```bash
git add sun.py
git commit -m "Add sun render and brightness handling"
```

---

## Task 16: logo.py

**Files:**
- Create: `logo.py`

- [ ] **Step 1: Write `logo.py`**

```python
"""Static Arc Raiders logo, bottom-right quadrant (32x32)."""
import displayio
import adafruit_imageload

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
```

- [ ] **Step 2: Commit**

```bash
git add logo.py
git commit -m "Add logo module with palette-based dimming"
```

---

## Task 17: Rewrite code.py

**Files:**
- Modify: `code.py`

- [ ] **Step 1: Replace `code.py` contents**

```python
"""LED dashboard main entry point.

Layout (64x64, four 32x32 quadrants):
    +-----------+-----------+
    | clock     | weather   |
    +-----------+-----------+
    | sun       | logo      |
    +-----------+-----------+
"""
import os
import time

import displayio
from adafruit_matrixportal.matrix import Matrix

import wifi_setup
import clock
import weather
import sun
import logo
from brightness import Brightness


MATRIX_WIDTH = 64
MATRIX_HEIGHT = 64
BIT_DEPTH = 4

_LAT = float(os.getenv("WEATHER_LAT", "47.6062"))
_LON = float(os.getenv("WEATHER_LON", "-122.3321"))
_TZ_NAME = os.getenv("TZ_NAME", "UTC")
_WEATHER_REFRESH_SEC = int(os.getenv("WEATHER_REFRESH_MIN", "15")) * 60
_NTP_RESYNC_SEC = 3600
_BRIGHTNESS_DEFAULT = int(os.getenv("BRIGHTNESS_DEFAULT", "3"))


matrix = Matrix(
    width=MATRIX_WIDTH,
    height=MATRIX_HEIGHT,
    bit_depth=BIT_DEPTH,
    tile_rows=1,
    serpentine=False,
)
display = matrix.display

root = displayio.Group()
clock_group = clock.build(0, 0, 32, 32)
weather_group = weather.build(32, 0, 32, 32)
sun_group = sun.build(0, 32, 32, 32)
logo_group = logo.build(32, 32, 32, 32)
root.append(clock_group)
root.append(weather_group)
root.append(sun_group)
root.append(logo_group)
display.root_group = root

brightness = Brightness(default_index=_BRIGHTNESS_DEFAULT)

QUADRANTS = (clock, weather, sun, logo)
for q in QUADRANTS:
    q.apply_brightness(brightness.factor)


def _now_minutes():
    t = time.localtime()
    return t.tm_hour * 60 + t.tm_min


def _connect_wifi():
    while True:
        try:
            return wifi_setup.connect()
        except Exception as e:
            print("wifi: connect failed:", e)
            clock.set_status("no wifi")
            time.sleep(10)


def _initial_ntp_sync(pool):
    while True:
        try:
            clock.sync(pool)
            return
        except Exception as e:
            print("ntp: initial sync failed:", e)
            clock.set_status("no time")
            time.sleep(30)


def _initial_weather(pool):
    try:
        data = weather.fetch(pool, _LAT, _LON, _TZ_NAME)
        weather.render(data)
        return data["sunrise_minutes"], data["sunset_minutes"]
    except Exception as e:
        print("weather: initial fetch failed:", e)
        weather.render_unknown()
        sun.render_unknown()
        return None, None


# Boot sequence
clock.set_status("boot")
pool = _connect_wifi()
clock.set_status("ntp")
_initial_ntp_sync(pool)
sunrise_minutes, sunset_minutes = _initial_weather(pool)

# Re-apply brightness now that all quadrants have content
for q in QUADRANTS:
    q.apply_brightness(brightness.factor)

last_tick = 0.0
last_weather = time.monotonic()
last_ntp = time.monotonic()
blink_on = True

while True:
    now = time.monotonic()

    if brightness.poll():
        for q in QUADRANTS:
            q.apply_brightness(brightness.factor)

    if now - last_tick >= 1.0:
        blink_on = not blink_on
        clock.update(blink_on)
        if sunrise_minutes is not None and sunset_minutes is not None:
            sun.render(sunrise_minutes, sunset_minutes, _now_minutes())
        last_tick = now

    if now - last_weather >= _WEATHER_REFRESH_SEC:
        try:
            data = weather.fetch(pool, _LAT, _LON, _TZ_NAME)
            weather.render(data)
            sunrise_minutes = data["sunrise_minutes"]
            sunset_minutes = data["sunset_minutes"]
        except Exception as e:
            print("weather: refresh failed:", e)
        last_weather = now

    if now - last_ntp >= _NTP_RESYNC_SEC:
        try:
            clock.sync(pool)
        except Exception as e:
            print("ntp: resync failed:", e)
        last_ntp = now

    time.sleep(0.05)
```

- [ ] **Step 2: Run pytest one more time to make sure nothing host-side regressed**

Run: `pytest`
Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add code.py
git commit -m "Rewrite code.py for four-quadrant layout with brightness control"
```

---

## Task 18: On-device smoke test checklist

These tests run on the MatrixPortal S3 itself. They are manual; check off as you complete each.

**Files (no edits; just deploy):**
- Run `./deploy.sh` to copy everything onto CIRCUITPY.
- Open the serial console (typically `screen /dev/ttyACM0 115200` or `tio /dev/ttyACM0`).

- [ ] **Step 1: Confirm `images/arc_raiders.bmp` exists**

The user is responsible for supplying this 32×32 BMP. If it's missing, the bottom-right quadrant will simply be blank and a warning prints on serial — that's the documented fallback, not a hard failure.

Run: `ls images/arc_raiders.bmp`
Expected: file exists. If not, create or copy a 32×32 BMP at that path before deploying.

- [ ] **Step 2: Cold-boot with Wi-Fi available**

Power-cycle the board (USB only is fine).
Expected serial output (in order):

```
Connecting to CabinInTheHills
Connected, IP: <some address>
```

Expected display: brief "boot" → "ntp" → full four-quadrant display within ~5 seconds.

- [ ] **Step 3: Verify time + zone + date in top-left**

Visually confirm:
- Time is correct for the configured zone (compare to phone).
- Zone abbreviation matches season (PST in winter, PDT mid-March → early November).
- Date format is `Mon DD`.

- [ ] **Step 4: Verify weather in top-right**

Visually confirm temperature looks plausible for Seattle right now and that the icon roughly matches conditions outside.

- [ ] **Step 5: Verify next sun event in bottom-left**

Visually confirm "next" label + an arrow (`^` for sunrise, `v` for sunset) + a time that matches what you'd expect for today.

- [ ] **Step 6: Verify Arc Raiders logo in bottom-right**

Visually confirm the BMP renders correctly.

- [ ] **Step 7: Verify brightness up**

Press the UP button five times. Each press should noticeably brighten the display until it reaches the top step (then further presses do nothing). All four quadrants should dim/brighten in sync, including the BMP icons.

- [ ] **Step 8: Verify brightness down**

Press the DOWN button five times. Each press should noticeably dim. At the lowest step, the display is still readable but very dim. Further presses do nothing.

- [ ] **Step 9: Verify Wi-Fi failure path**

Edit `settings.toml` so `CIRCUITPY_WIFI_SSID = "BogusNetwork"`, save, watch serial:
- Time quadrant shows "no wifi".
- Other quadrants stay blank.
- Serial logs `wifi: connect failed: ...` repeatedly every ~10s.

Restore the real SSID and confirm recovery on next boot.

- [ ] **Step 10: Verify weather failure path**

While running normally, briefly block outbound HTTPS (easiest: unplug router for ~30s and force a weather refresh by editing `WEATHER_REFRESH_MIN = "1"` temporarily). Confirm:
- Clock keeps ticking.
- Weather quadrant flips to `--C` + unknown icon.
- Sun quadrant shows `--:--`.
- Serial logs `weather: refresh failed: ...`.
- After router comes back, next refresh restores normal state.

Restore `WEATHER_REFRESH_MIN = "15"` when done.

- [ ] **Step 11: Verify DST boundary (optional, requires waiting until March or November)**

Either wait for an actual DST boundary, or temporarily edit `tz._ZONES["America/Los_Angeles"]` on the device to force a switch and verify the zone abbreviation flips correctly between PST and PDT. Revert when done.

- [ ] **Step 12: Final commit (if any tweaks were made during smoke testing)**

```bash
git status
# If anything changed (e.g., a tweaked color or icon coordinate), commit it:
git add -p
git commit -m "Smoke-test adjustments"
```

---

## Self-review notes

Cross-checked the plan against `docs/superpowers/specs/2026-05-19-quadrant-dashboard-design.md`:

- **Layout** (spec §Layout): covered in Tasks 13–17 with the exact pixel offsets and font choices from the spec.
- **DST** (spec §DST handling): Tasks 2–5 implement the rules exactly as specified, with tests covering both boundaries for both Pacific and Eastern. The four zones from the spec table are all in `_ZONES`.
- **Brightness** (spec §Brightness control): Tasks 6–7 cover scale and class; Task 17 wires polling into the main loop; Tasks 13–16 each implement `apply_brightness` per quadrant.
- **Settings** (spec §Settings): Task 10 produces the exact `settings.toml` from the spec.
- **Data flow** (spec §Data flow): Task 17's `code.py` matches the spec's main-loop structure cadence-for-cadence, including the 20 Hz button poll via `time.sleep(0.05)`.
- **Error handling** (spec §Error handling): Task 17 handles wifi/NTP/weather/logo failures with the same fallbacks the spec lists. Font missing → load_font raises and the board halts (matches the spec's "halt loudly" stance).
- **Testing** (spec §Testing): Tasks 2–9 cover all the pure-Python unit tests the spec calls out; Task 18 is the manual on-device checklist.

No type/name drift detected on a re-read (e.g., `code_to_icon`, `next_event`, `apply_brightness` are used consistently across tasks).

One scoped-out item per the spec: brightness persistence across reboots — intentionally not in the plan.
