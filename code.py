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
import spotify
import layouts
from brightness import Brightness


BIT_DEPTH = 4

_LAT = float(os.getenv("WEATHER_LAT", "47.6062"))
_LON = float(os.getenv("WEATHER_LON", "-122.3321"))
_TZ_NAME = os.getenv("TZ_NAME", "UTC")
_WEATHER_REFRESH_SEC = int(os.getenv("WEATHER_REFRESH_MIN", "15")) * 60
_NTP_RESYNC_SEC = 3600
_BRIGHTNESS_DEFAULT = int(os.getenv("BRIGHTNESS_DEFAULT", "0"))
_SPOTIFY_REFRESH_SEC = int(os.getenv("SPOTIFY_REFRESH_SEC", "10"))


_MODULES = {
    "clock": clock,
    "weather": weather,
    "sun": sun,
    "logo": logo,
    "spotify": spotify,
}

_layout_name = os.getenv("LAYOUT_NAME", layouts.DEFAULT_LAYOUT)
_layout = layouts.LAYOUTS.get(_layout_name)
if _layout is None:
    print("layout: unknown LAYOUT_NAME", _layout_name,
          "— falling back to", layouts.DEFAULT_LAYOUT)
    _layout_name = layouts.DEFAULT_LAYOUT
    _layout = layouts.LAYOUTS[_layout_name]
print("layout:", _layout_name,
      "(" + str(_layout["width"]) + "x" + str(_layout["height"]) + ",",
      len(_layout["quadrants"]), "quadrants)")

matrix = Matrix(
    width=_layout["width"],
    height=_layout["height"],
    bit_depth=BIT_DEPTH,
    tile_rows=_layout["tile_rows"],
    serpentine=_layout["serpentine"],
)
display = matrix.display

root = displayio.Group()
_seen_modules = set()
_ordered_quadrants = []
for name, x, y, w, h in _layout["quadrants"]:
    if name not in _MODULES:
        print("layout: unknown module name", name, "— skipping")
        continue
    module = _MODULES[name]
    group = module.build(x, y, w, h)
    root.append(group)
    if name not in _seen_modules:
        _seen_modules.add(name)
        _ordered_quadrants.append(module)
display.root_group = root

brightness = Brightness(default_index=_BRIGHTNESS_DEFAULT)

QUADRANTS = tuple(_ordered_quadrants)
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


def _apply_spotify_swap(data):
    if data is None:
        spotify.set_hidden(True)
        sun.set_hidden(False)
    else:
        spotify.set_hidden(False)
        sun.set_hidden(True)


def _initial_spotify(pool):
    try:
        data = spotify.fetch(pool)
        spotify.render(data)
        _apply_spotify_swap(data)
    except Exception as e:
        print("spotify: initial fetch failed:", e)


# Boot sequence
clock.set_status("boot")
pool = _connect_wifi()
clock.set_status("ntp")
_initial_ntp_sync(pool)
sunrise_minutes, sunset_minutes = _initial_weather(pool)
_initial_spotify(pool)

# Re-apply brightness now that all quadrants have content
for q in QUADRANTS:
    q.apply_brightness(brightness.factor)

last_tick = 0.0
last_weather = time.monotonic()
last_ntp = time.monotonic()
last_spotify = time.monotonic()
last_marquee = time.monotonic()
blink_on = True

while True:
    now = time.monotonic()

    if brightness.poll():
        for q in QUADRANTS:
            q.apply_brightness(brightness.factor)

    if now - last_marquee >= 0.25:
        spotify.tick()
        last_marquee = now

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

    if now - last_spotify >= _SPOTIFY_REFRESH_SEC:
        try:
            data = spotify.fetch(pool)
            spotify.render(data)
            _apply_spotify_swap(data)
        except Exception as e:
            print("spotify: refresh failed:", e)
        last_spotify = now

    if now - last_ntp >= _NTP_RESYNC_SEC:
        try:
            clock.sync(pool)
        except Exception as e:
            print("ntp: resync failed:", e)
        last_ntp = now

    time.sleep(0.05)
