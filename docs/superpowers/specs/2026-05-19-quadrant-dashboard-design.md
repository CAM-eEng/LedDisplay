# Quadrant Dashboard — Design

## Goal

Turn the existing single-line clock on the 64×64 HUB75 panel into a four-quadrant dashboard:

- **Top-left:** time (12-hour) + zone abbreviation + date
- **Top-right:** current weather (°C + condition icon)
- **Bottom-left:** the next sun event (sunrise or sunset)
- **Bottom-right:** static Arc Raiders logo

The clock gains automatic US DST handling and a displayed zone abbreviation (PST / PDT). The MatrixPortal S3's on-board UP / DOWN buttons control panel brightness in software.

When `USE_12_HOUR = "true"`, the time line shows 12-hour numeric format (e.g., `1:23`) **without** an AM/PM suffix — the zone label below replaces it. When `USE_12_HOUR = "false"`, the time line is 24-hour (e.g., `13:23`).

## Non-goals

- IANA-correct timezone handling for non-US zones (US DST rules are hardcoded).
- Persisting brightness across reboots (resets to default).
- Hot-reloading layout or content at runtime.
- A configuration UI on the panel itself (`settings.toml` is the configuration surface).

## Layout

64×64 panel divided into four non-overlapping 32×32 quadrants. Each quadrant owns a `displayio.Group` positioned at its top-left corner.

```
┌──────────────┬──────────────┐
│  12:34       │  22°C        │
│  PDT         │   ☀          │
│  May 19      │              │
│              │              │
├──────────────┼──────────────┤
│  next        │              │
│  ↓ 20:51     │   [ARC]      │
│              │              │
│              │              │
└──────────────┴──────────────┘
```

### Fonts

- Top-left time row uses Adafruit's 6×10 BDF font for visual hierarchy.
- All other text uses Adafruit's 5×8 BDF font.
- Both fonts are bundled under `lib/fonts/` so they load from CIRCUITPY without internet.

### Colors

| Element            | Color       |
|--------------------|-------------|
| Time               | `0xFFAA00`  |
| Zone (PST/PDT)     | `0x4488FF`  |
| Date               | `0xCCCCCC`  |
| Temperature        | `0x44FF66`  |
| Sun "next" label   | `0x666666`  |
| Sun time           | `0xFFCC44`  |

All colors are passed through `Brightness.scale()` before being assigned to labels, so the values above are "100% brightness" reference points.

## Modules and interfaces

```
LedDisplay/
├── code.py              # main loop, wires modules together
├── clock.py             # extended — DST + zone abbreviation
├── weather.py           # NEW — Open-Meteo fetch + render
├── sun.py               # NEW — sunrise/sunset render
├── logo.py              # NEW — loads images/arc_raiders.bmp
├── brightness.py        # NEW — button polling + global scale factor
├── wifi_setup.py        # unchanged
├── settings.toml        # extended
├── images/
│   ├── arc_raiders.bmp  # user-supplied, 32×32
│   └── weather/
│       ├── sun.bmp
│       ├── cloud.bmp
│       ├── rain.bmp
│       ├── snow.bmp
│       ├── fog.bmp
│       └── unknown.bmp
└── lib/
    └── fonts/
        ├── 5x8.bdf
        └── 6x10.bdf
```

Each quadrant module follows a small, uniform interface so `code.py` can treat them as peers:

```python
# clock.py (extended)
def build(x, y, width, height) -> displayio.Group: ...
def update(blink_on: bool) -> None: ...
def apply_brightness(scale: float) -> None: ...
def sync(pool) -> None: ...        # NTP + DST recompute
def zone_abbrev() -> str: ...      # "PST" or "PDT"

# weather.py
def build(x, y, width, height) -> displayio.Group: ...
def fetch(pool, lat, lon) -> dict: ...   # {temp_c, condition, sunrise, sunset}
def render(data) -> None: ...
def apply_brightness(scale: float) -> None: ...

# sun.py
def build(x, y, width, height) -> displayio.Group: ...
def render(sunrise_dt, sunset_dt, now_dt) -> None: ...
def apply_brightness(scale: float) -> None: ...

# logo.py
def build(x, y, width, height, path) -> displayio.Group: ...
def apply_brightness(scale: float) -> None: ...

# brightness.py
class Brightness:
    factor: float                  # current scale, e.g., 0.75
    def poll(self) -> bool: ...    # True if level changed this tick
    @staticmethod
    def scale(color: int, factor: float) -> int: ...
```

## DST handling

US DST rules are hardcoded:

- DST begins on the **second Sunday of March** at 02:00 local.
- DST ends on the **first Sunday of November** at 02:00 local.

`clock.sync(pool)` performs an NTP fetch with offset = 0, then computes the local offset from `TZ_NAME`:

| TZ_NAME                     | Standard | Daylight |
|-----------------------------|----------|----------|
| `America/Los_Angeles`       | PST (-8) | PDT (-7) |
| `America/Denver`            | MST (-7) | MDT (-6) |
| `America/Chicago`           | CST (-6) | CDT (-5) |
| `America/New_York`          | EST (-5) | EDT (-4) |

Unknown `TZ_NAME` → fall back to UTC with a printed warning. The abbreviation function returns the standard or daylight string based on whether the current UTC time falls inside the DST window for the configured zone.

DST is recomputed on every NTP resync (hourly). Worst-case drift at a transition: clock is one hour wrong for up to 60 minutes; acceptable.

## Brightness control

The HUB75 panel via `rgbmatrix.RGBMatrix` has no functional runtime brightness setting in CircuitPython, so brightness is implemented in software by scaling all colors before assigning them.

- Discrete levels: `[0.10, 0.25, 0.50, 0.75, 1.00]`
- Default boot index: `BRIGHTNESS_DEFAULT` from `settings.toml` (default `3` → 75%).
- `board.BUTTON_UP` raises the index (clamped at top).
- `board.BUTTON_DOWN` lowers it (clamped at bottom).
- Buttons are configured `DigitalInOut`, `Pull.UP`, active-low.
- Edge-triggered: a level change happens on the falling edge of the button press, not on hold.
- On level change, `code.py` calls `apply_brightness(factor)` on each quadrant.
- BMP-backed quadrants (weather icon, Arc Raiders logo) dim by recomputing their palette entries; label-backed quadrants set `label.color`.

Brightness is not persisted across reboots (writing to CIRCUITPY at runtime conflicts with the USB mount). Boot always starts at `BRIGHTNESS_DEFAULT`.

## Settings

`settings.toml` is the single configuration surface:

```toml
# Wi-Fi
CIRCUITPY_WIFI_SSID = "CabinInTheHills"
CIRCUITPY_WIFI_PASSWORD = "PizzaPizzaPumpkin66!"

# Clock
TZ_NAME = "America/Los_Angeles"
USE_12_HOUR = "true"

# Weather / sun (defaults to Seattle)
WEATHER_LAT = "47.6062"
WEATHER_LON = "-122.3321"
WEATHER_REFRESH_MIN = "15"

# Brightness
BRIGHTNESS_DEFAULT = "3"
```

`TZ_OFFSET_HOURS` from the previous version is removed.

## Data flow

### Boot sequence

1. Build four quadrant `displayio.Group`s, attach to root, show "booting..." in the time quadrant.
2. `wifi_setup.connect()`.
3. `clock.sync(pool)` (NTP + DST + RTC set).
4. `weather.fetch(pool, lat, lon)` returns current temp, weather code, sunrise, sunset.
5. `logo.build(...)` loads `images/arc_raiders.bmp` once.
6. `brightness` initialized; `apply_brightness(factor)` called on every quadrant.
7. Enter main loop.

### Open-Meteo request

A single endpoint serves both the weather and sun quadrants:

```
https://api.open-meteo.com/v1/forecast
  ?latitude=47.6062&longitude=-122.3321
  &current=temperature_2m,weather_code
  &daily=sunrise,sunset
  &timezone=America/Los_Angeles
  &temperature_unit=celsius
```

The `weather_code` integer (WMO codes 0–99) is mapped to one of five icons: sun / cloud / rain / snow / fog. Any code that doesn't map cleanly (or a failed fetch) shows `unknown.bmp`. Mapping lives in `weather.py`.

### Main loop cadence

```python
while True:
    now = time.monotonic()

    if brightness.poll():
        for q in quadrants: q.apply_brightness(brightness.factor)

    if now - last_tick >= 1.0:
        blink_on = not blink_on
        clock.update(blink_on)
        sun.render(sunrise_dt, sunset_dt, now_dt())
        last_tick = now

    if now - last_weather >= WEATHER_REFRESH_MIN * 60:
        try:
            data = weather.fetch(pool, lat, lon)
            weather.render(data)
            sunrise_dt, sunset_dt = data["sunrise"], data["sunset"]
        except Exception as e:
            print("weather refresh failed:", e)
        last_weather = now

    if now - last_ntp >= 3600:
        try:
            clock.sync(pool)
        except Exception as e:
            print("ntp resync failed:", e)
        last_ntp = now

    time.sleep(0.05)   # ~20 Hz button polling
```

Button polling at 20 Hz is the only fast loop; all rendering work is gated by its own timer.

## Error handling

### Boot

| Failure                            | Behavior                                                                                     |
|------------------------------------|----------------------------------------------------------------------------------------------|
| Wi-Fi connect fails                | Show "no wifi" in the time quadrant. Retry every 10s. Other quadrants stay blank.            |
| NTP fails after Wi-Fi connects     | Show "no time" in the time quadrant. Retry every 30s. Weather/sun still fetched.             |
| Weather fetch fails at boot        | Clock displays normally. Weather quadrant shows `--°C` + `unknown.bmp` icon; sun quadrant `—`. |
| `images/arc_raiders.bmp` missing   | Bottom-right quadrant stays blank. Print warning. Boot continues.                            |
| Font files missing                 | Show "font err" with `terminalio.FONT` and halt — packaging mistake, not a runtime state.    |

### Runtime

- Weather refresh failure → keep last-known values; no UI flicker; serial log.
- NTP resync failure → keep current RTC; clock keeps ticking; serial log.
- DST boundary mid-run → caught at next hourly NTP resync (≤60 min stale at transitions, twice a year).
- Long-running HTTP fetch → buttons may lag by up to ~3-5s during a fetch. Acceptable.

### Time quadrant status progression

```
boot          → wifi          → ntp           → ok
   ↓ (fail)      ↓ (fail)        ↓ (fail)
                "no wifi"       "no time"
```

## Testing

The MatrixPortal target runs CircuitPython, so traditional pytest harnessing isn't available on-device. Validation strategy:

- **Pure-Python unit tests for DST math** — `clock` module's DST-window function is plain integer date math; can be exercised under CPython with a small shim. Cover: 2nd Sunday of March / 1st Sunday of November for several years; both sides of each boundary.
- **Manual smoke tests on device** — boot with Wi-Fi unplugged ("no wifi"); boot with Wi-Fi but firewall blocking Open-Meteo (clock OK, weather `--°C`); boot with `arc_raiders.bmp` removed (logo blank).
- **Brightness end-to-end** — press UP from default to max, then DOWN to min; verify both clamps and that every quadrant (including BMP-backed ones) dims uniformly.

## Out of scope / future work

- Non-US timezone DST rules.
- A second time zone quadrant.
- Persisting brightness across reboots (would require NVM storage).
- Per-quadrant configuration of what content is displayed.
- Animated weather icons or sun-arc progress visualization.
