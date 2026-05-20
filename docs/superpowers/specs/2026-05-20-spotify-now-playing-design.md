# Spotify Now-Playing Quadrant — Design

## Goal

Show the currently-playing Spotify track on the LED dashboard. When a track is playing (or paused), the bottom-left quadrant — currently the sunrise/sunset quadrant — displays the track title and artist scrolling as two independent marquees. When nothing is playing, the sun quadrant reappears.

## Non-goals

- Album art (text only — album art is deferred to the 4-panel expansion).
- Playback control (play/pause/skip from the panel).
- Lyrics, audio analysis, or any feature beyond the current track metadata.
- Multiple Spotify accounts; the feature targets a single user's account.
- Persistent token storage across reboots beyond what `settings.toml` already provides.

## Layout & visual states

The bottom-left 32×32 holds two `displayio.Group`s stacked at the same coordinates: the existing `sun_group` and a new `spotify_group`. Exactly one is `.hidden = False` at a time. `code.py` flips the flags after every Spotify fetch.

```
┌──────────────┬──────────────┐
│  12:34       │  22°C        │
│  PDT         │   ☀          │
│  May 19      │              │
│              │              │
├──────────────┼──────────────┤
│ ♪ Bohemian   │              │
│   Queen      │   [ARC]      │   ← Spotify visible
│              │              │
│              │              │
└──────────────┴──────────────┘
```

### Visual states inside the Spotify quadrant

| Playback state | Row 1 (track) | Row 2 (artist) | Notes |
|---|---|---|---|
| Playing | Scrolling track title | Scrolling artist | Both at the global brightness factor. |
| Paused | Same content | Same content | An additional 0.4× dim multiplier is applied. Scrolling stops. |
| No playback | (hidden) | (hidden) | `spotify_group.hidden = True`; `sun_group.hidden = False`. |

### Colors

| Element | Color |
|---|---|
| Track title | `0x1ED760` (Spotify green) |
| Artist | `0x999999` (dim white) |

Both colors are passed through `brightness.scale(color, factor)` like every other quadrant, and through an additional 0.4× multiplier when paused.

### Marquee

- Window width: 6 characters at the 5×8 font (the same font used by `sun`/`weather`).
- Tick rate: 250 ms per character step, driven by the main loop.
- Loop separator: text is padded with `"   "` (3 spaces) and the window wraps so the marquee runs forever.
- Strings ≤ 6 chars don't scroll — they sit static.
- When paused, scrolling stops (offset frozen at its current position).
- On track change, both offsets reset to 0.

## Module structure

```
LedDisplay/
├── spotify.py                  # NEW — quadrant module
├── scripts/
│   └── spotify_auth.py         # NEW — one-time host-side OAuth helper
├── tests/
│   └── test_spotify.py         # NEW — marquee + parser unit tests
├── code.py                     # MODIFIED — build spotify_group, swap each fetch
├── sun.py                      # MODIFIED — gains set_hidden(hidden: bool)
├── settings.toml               # MODIFIED — three required + one optional Spotify key
└── deploy.sh                   # MODIFIED — copy spotify.py
```

`install_libs.sh` is **not** modified: the Spotify path uses `adafruit_requests`, which is already installed.

### `spotify.py` interface

```python
# Pure helpers — unit-tested under host CPython:
def marquee_window(text: str, offset: int, window: int = 6, gap: str = "   ") -> str: ...
def parse_now_playing(payload: dict) -> dict | None: ...
    # Returns {"track": str, "artist": str, "is_playing": bool} or None.
    #
    # Field extraction:
    #   - track:  item["name"]
    #   - artist (track):    ", ".join(a["name"] for a in item["artists"])
    #   - artist (episode):  item["show"]["name"]
    #   - is_playing:        payload["is_playing"]
    #
    # Returns None for 204 (no playback), ads, or any payload missing
    # the required fields.

# CircuitPython interface — same shape as the other quadrant modules:
def build(x, y, width, height) -> displayio.Group: ...
def fetch(pool) -> dict | None: ...     # makes the HTTP calls
def render(data: dict | None) -> None:  # updates labels + pause dimming
def tick() -> None:                     # advances marquee one step
def apply_brightness(factor: float) -> None
def set_hidden(hidden: bool) -> None
```

### `sun.py` change

One added function. Otherwise untouched.

```python
def set_hidden(hidden: bool) -> None:
    if _state["group"] is not None:
        _state["group"].hidden = hidden
```

### `scripts/spotify_auth.py`

Stand-alone host-side script. No dependency on the rest of the repo. Stdlib only.

- Accepts `--client-id` and `--client-secret`. If absent, prompts for them on stdin.
- Spins up a one-shot HTTP server bound to `127.0.0.1:8080` (Spotify no longer allows the hostname `localhost`).
- Opens `https://accounts.spotify.com/authorize` in the user's browser via `webbrowser.open`, with:
  - `client_id`
  - `response_type=code`
  - `redirect_uri=http://127.0.0.1:8080/callback`
  - `scope=user-read-currently-playing`
  - `state=<random>` (CSRF protection; verified on callback)
- Catches the `?code=…` redirect, POSTs to `https://accounts.spotify.com/api/token` with `grant_type=authorization_code`, and prints the resulting `refresh_token` to stdout.
- The user pastes the refresh token (plus the client id and secret) into `settings.toml`.

The Spotify Developer dashboard side requires the redirect URI to be registered as `http://127.0.0.1:8080/callback` — exact match.

## Settings

```toml
# Spotify (optional — leave any of the three blank to disable the feature)
SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""
SPOTIFY_REFRESH_TOKEN = ""
SPOTIFY_REFRESH_SEC = "10"
```

### Behavior when any of the three required keys is empty

- `spotify.py` prints `"spotify: not configured, feature disabled"` once at boot.
- `spotify_group` is built (so it can be referenced safely) but stays `hidden = True` forever.
- `sun_group.hidden` stays `False`. The dashboard behaves exactly as it does today.

### Tuning parameters that stay in code

- Marquee tick rate: 250 ms (hardcoded in `spotify.py`).
- Pause dim multiplier: 0.4× (hardcoded).
- HTTP timeout: 5 s on token refresh, 5 s on currently-playing.

## Auth & token lifecycle

### One-time setup

1. Create a Spotify Developer app at developer.spotify.com → record `client_id` and `client_secret`.
2. Add `http://127.0.0.1:8080/callback` as a redirect URI on the app.
3. Run `python3 scripts/spotify_auth.py --client-id <id> --client-secret <secret>` on the laptop. The script prints a refresh token.
4. Paste `client_id`, `client_secret`, and `refresh_token` into `settings.toml`. Redeploy.

### On-device token refresh

```
                ┌─────────────────────────────────────────┐
                │  Need a request to api.spotify.com?     │
                └────────────────┬────────────────────────┘
                                 │
                 access_token cached and ≥ 60s until expiry?
                                 │
                ┌──── yes ───────┴─────── no ─────┐
                ▼                                 ▼
   Use cached access_token       POST /api/token with refresh_token
                ▼                                 ▼
   Authorization: Bearer …    Cache new access_token + expires_at
                                 ▼
                  (cached access_token now valid; proceed)
```

- Spotify access tokens last 3600 s. Refresh proactively at `expires - 60`.
- On a `401 Unauthorized` mid-window, force-refresh once and retry once.
- On a `400 invalid_grant` from `/api/token` (user revoked access), latch `_state["auth_failed"] = True`, print loudly, and skip all subsequent polls this boot. Recovery: re-run the host helper, paste fresh token, reboot.

### Module state

```python
_state = {
    "group": None,
    "track_label": None,
    "artist_label": None,
    "session": None,            # lazily created adafruit_requests.Session
    "access_token": None,
    "expires_at": 0.0,          # time.monotonic() value
    "refresh_token": os.getenv("SPOTIFY_REFRESH_TOKEN", ""),
    "client_id": os.getenv("SPOTIFY_CLIENT_ID", ""),
    "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET", ""),
    "auth_failed": False,       # latches on invalid_grant
    "track_text": "",
    "artist_text": "",
    "track_offset": 0,
    "artist_offset": 0,
    "is_playing": False,
    "has_data": False,
    "last_factor": 1.0,
}
```

## Data flow & main loop

### Boot additions

After the existing `_initial_weather(pool)` call:

```python
try:
    spotify_data = spotify.fetch(pool)
    spotify.render(spotify_data)
    _apply_spotify_swap(spotify_data)
except Exception as e:
    print("spotify: initial fetch failed:", e)
```

`_apply_spotify_swap` is a helper in `code.py`:

```python
def _apply_spotify_swap(data):
    if data is None:
        spotify.set_hidden(True)
        sun.set_hidden(False)
    else:
        spotify.set_hidden(False)
        sun.set_hidden(True)
```

### Main loop (with new cadences)

```python
while True:
    now = time.monotonic()

    if brightness.poll():
        for q in QUADRANTS: q.apply_brightness(brightness.factor)

    if now - last_marquee >= 0.25:                # 250 ms — NEW
        spotify.tick()
        last_marquee = now

    if now - last_tick >= 1.0:                    # 1 s
        blink_on = not blink_on
        clock.update(blink_on)
        if sunrise_minutes is not None and sunset_minutes is not None:
            sun.render(sunrise_minutes, sunset_minutes, _now_minutes())
        last_tick = now

    if now - last_spotify >= _SPOTIFY_REFRESH_SEC:  # 10 s — NEW
        try:
            data = spotify.fetch(pool)
            spotify.render(data)
            _apply_spotify_swap(data)
        except Exception as e:
            print("spotify: refresh failed:", e)
        last_spotify = now

    if now - last_weather >= _WEATHER_REFRESH_SEC:  # 15 min — unchanged
        ...

    if now - last_ntp >= _NTP_RESYNC_SEC:            # 1 hr — unchanged
        ...

    time.sleep(0.05)
```

- `sun.render()` is still called every second. When `sun_group.hidden = True`, displayio doesn't render it.
- `spotify.tick()` is unconditionally called every 250 ms but bails immediately if the group is hidden or the current track is paused.
- HTTPS to Spotify reuses the `socketpool.SocketPool` from `wifi_setup.connect()`. Spotify gets its own `adafruit_requests.Session` (lazily created in `spotify.fetch`, mirroring `weather.py`).

`QUADRANTS` becomes `(clock, weather, sun, logo, spotify)` so brightness updates reach the new module.

## Error handling

### Server responses

| Server response | Meaning | Behavior |
|---|---|---|
| `204 No Content` (empty body) | No active playback | Return `None` → sun visible. Not an error. |
| `200` with `currently_playing_type` ∈ {`track`, `episode`} | Normal case | Parse → return dict → Spotify visible. |
| `200` with other `currently_playing_type` (ads, unknown) | Spotify ad break, etc. | Return `None` → sun visible. |
| `200` with missing `item` | Spotify edge case | Return `None`. |
| `401 Unauthorized` on `/v1/me/player/currently-playing` | Access token expired | Force-refresh once, retry once. Still 401 → return `None`. |
| `400 invalid_grant` on `/api/token` | User revoked access | Latch `auth_failed = True`, print, skip all future polls. |
| `429 Too Many Requests` | Rate limited | Print, skip this cycle. |
| Network/TLS/timeout | Wi-Fi flaky, Spotify unreachable | Print, skip. No state change. |
| Malformed JSON | Truncated response | Print, skip. |

### Invariants

- A single Spotify failure never affects clock, weather, or sun.
- The swap is idempotent: `set_hidden(True)` on an already-hidden group is a no-op.
- `auth_failed = True` is sticky for the boot; recovery requires re-running the host helper.

### What the user sees

| Scenario | What's on the panel |
|---|---|
| Wi-Fi up, Spotify configured, music playing | Spotify visible, marquees scrolling |
| Wi-Fi up, Spotify configured, paused | Spotify visible, dimmed, marquee frozen |
| Wi-Fi up, Spotify configured, no music | Sun visible (idle) |
| Wi-Fi up, Spotify *not* configured | Sun visible always; serial logs "not configured" once |
| Wi-Fi down | Sun stays whatever it was. Serial logs network errors. |
| Refresh token rejected | Sun visible, never swaps to Spotify for the rest of this boot |

## Testing

- **`tests/test_spotify.py`** covers the pure helpers (~15 tests):
  - `marquee_window` — string shorter than window, exactly window, longer than window, wrap at end, large offset (wraps modulo length), empty string, custom gap, custom window.
  - `parse_now_playing` — typical track, podcast/episode, paused track, no `item`, unknown `currently_playing_type`, missing `artists` field, missing `name` field, empty payload, None payload.
- The HTTP/displayio paths are not unit tested; they're validated by on-device smoke testing.

### On-device smoke checklist (manual)

- [ ] Configure Spotify keys in `settings.toml`, deploy, cold-boot. Track shows when playing.
- [ ] Pause Spotify on phone — quadrant dims and marquee stops within 10 s.
- [ ] Stop Spotify entirely — sun quadrant reappears within 10 s.
- [ ] Empty out `SPOTIFY_REFRESH_TOKEN` — sun stays visible forever; serial says "not configured".
- [ ] Brightness up/down — Spotify text dims/brightens in sync with other quadrants.
- [ ] Revoke app access in Spotify settings, wait for next refresh — sun stays visible, serial prints `"spotify: refresh token rejected"`.
- [ ] Long title (e.g., "Bohemian Rhapsody – Remastered 2011") — scrolls cleanly, loops with a visible 3-space gap.

## Out of scope / future work

- Album art — naturally fits the 4-panel expansion at 32×32 or 48×48.
- Playback control (skip / pause / next).
- Persisting playback state across reboots (not useful for a glance display).
- Supporting multiple Spotify accounts.
- Lyrics, BPM, audio features, or any other Spotify endpoint beyond `currently-playing` + `/api/token`.
