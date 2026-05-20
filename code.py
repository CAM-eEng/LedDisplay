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
_SPOTIFY_REFRESH_SEC = int(os.getenv("SPOTIFY_REFRESH_SEC", "10"))


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
spotify_group = spotify.build(0, 32, 32, 32)
root.append(clock_group)
root.append(weather_group)
root.append(sun_group)
root.append(logo_group)
root.append(spotify_group)
display.root_group = root

brightness = Brightness(default_index=_BRIGHTNESS_DEFAULT)

QUADRANTS = (clock, weather, sun, logo, spotify)
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
