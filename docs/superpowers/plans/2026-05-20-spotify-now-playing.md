# Spotify Now-Playing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Spotify now-playing quadrant that swaps in for the sun quadrant when the configured Spotify account has playback, showing the track title and artist as two scrolling marquees.

**Architecture:** A new `spotify.py` module mirrors the existing quadrant module shape (`build`/`render`/`apply_brightness`). Its pure helpers — `marquee_window` and `parse_now_playing` — are unit-tested under host CPython. A one-time host-side OAuth helper (`scripts/spotify_auth.py`) produces a refresh token that lives in `settings.toml`; the device exchanges it for short-lived access tokens. `code.py` toggles `sun_group.hidden` and `spotify_group.hidden` after every Spotify fetch.

**Tech Stack:** CircuitPython 9+, `adafruit_requests` (already installed), Python `binascii` for HTTP Basic auth, stdlib `http.server` for the host-side OAuth flow. Tests use pytest on the host machine.

**Spec:** `docs/superpowers/specs/2026-05-20-spotify-now-playing-design.md`

---

## File Map

### New
- `spotify.py` — quadrant module. Pure helpers (`marquee_window`, `parse_now_playing`) + CircuitPython display/HTTP layer.
- `scripts/spotify_auth.py` — host-side one-shot OAuth helper.
- `tests/test_spotify.py` — pytest tests for the pure helpers.

### Modified
- `sun.py` — add `set_hidden(hidden: bool)` (≤ 4 lines).
- `code.py` — wire spotify into boot, main loop, brightness fan-out.
- `deploy.sh` — copy `spotify.py` to the device.
- `settings.toml` — add four Spotify keys (local edit only; file is gitignored).

### Untouched
- `tz.py`, `brightness.py`, `weather.py`, `logo.py`, `clock.py`, `wifi_setup.py`, `install_libs.sh`, `pyproject.toml`, `tests/conftest.py`, all existing test files.

---

## Task 1: marquee_window (TDD)

**Files:**
- Create: `spotify.py`
- Create: `tests/test_spotify.py`

- [ ] **Step 1: Write failing tests**

`tests/test_spotify.py`:

```python
from spotify import marquee_window


def test_empty_string_returns_empty():
    assert marquee_window("", 0) == ""


def test_string_shorter_than_window_returns_as_is():
    assert marquee_window("Hey", 0) == "Hey"
    assert marquee_window("Hey", 42) == "Hey"


def test_string_exactly_window_returns_as_is():
    assert marquee_window("123456", 0) == "123456"


def test_offset_zero_returns_first_window_chars_padded():
    # "Bohemian Rhapsody" + "   " = 20 chars total; first 6 at offset 0
    assert marquee_window("Bohemian Rhapsody", 0) == "Bohemi"


def test_offset_one_advances_by_one_char():
    assert marquee_window("Bohemian Rhapsody", 1) == "ohemia"


def test_window_wraps_at_end_of_padded_text():
    # Padded text length = 17 + 3 = 20. At offset 18, we read positions
    # 18, 19 (end of gap), then wrap to 0, 1, 2, 3 — "  Bohe"
    assert marquee_window("Bohemian Rhapsody", 18) == "  Bohe"


def test_large_offset_wraps_modulo_padded_length():
    # offset 38 = 38 % 20 = 18 -> same window as offset 18
    assert marquee_window("Bohemian Rhapsody", 38) == "  Bohe"


def test_custom_window_size():
    assert marquee_window("Bohemian Rhapsody", 0, window=4) == "Bohe"


def test_custom_gap():
    # Gap is "*" — padded = "AB*" length 3; offset 0 returns first 4 chars
    # wrapping: "AB*A"
    assert marquee_window("AB", 0, window=4, gap="*") == "AB*A"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `python3 -m pytest tests/test_spotify.py -v`
Expected: 9 failures with `ModuleNotFoundError: No module named 'spotify'`.

- [ ] **Step 3: Create `spotify.py` with the pure helper**

```python
"""Spotify now-playing quadrant for the LED dashboard."""


def marquee_window(text, offset, window=6, gap="   "):
    """Return a `window`-character slice of `text + gap`, wrapping at the end.

    Used to drive a character-step scrolling marquee. Strings shorter than
    `window` are returned unchanged (no scrolling). The gap separates the
    end of the text from its restart on the next loop.
    """
    if not text:
        return ""
    if len(text) <= window:
        return text
    padded = text + gap
    n = len(padded)
    o = offset % n
    if o + window <= n:
        return padded[o:o + window]
    return padded[o:] + padded[:window - (n - o)]
```

- [ ] **Step 4: Run tests — verify all pass**

Run: `python3 -m pytest tests/test_spotify.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add spotify.py tests/test_spotify.py
git commit -m "Add marquee_window pure helper"
```

---

## Task 2: parse_now_playing (TDD)

**Files:**
- Modify: `spotify.py` (append)
- Modify: `tests/test_spotify.py` (append)

- [ ] **Step 1: Append failing tests**

Append to `tests/test_spotify.py`:

```python
from spotify import parse_now_playing


def _track_payload(name="Bohemian Rhapsody", artists=("Queen",), is_playing=True):
    return {
        "is_playing": is_playing,
        "currently_playing_type": "track",
        "item": {
            "name": name,
            "artists": [{"name": a} for a in artists],
        },
    }


def _episode_payload(name="Hard Fork", show="The New York Times", is_playing=True):
    return {
        "is_playing": is_playing,
        "currently_playing_type": "episode",
        "item": {
            "name": name,
            "show": {"name": show},
        },
    }


def test_parse_returns_none_for_empty_payload():
    assert parse_now_playing({}) is None


def test_parse_returns_none_for_none_payload():
    assert parse_now_playing(None) is None


def test_parse_returns_none_when_item_missing():
    assert parse_now_playing({"is_playing": True}) is None


def test_parse_track_returns_track_artist_is_playing():
    data = parse_now_playing(_track_payload())
    assert data == {
        "track": "Bohemian Rhapsody",
        "artist": "Queen",
        "is_playing": True,
    }


def test_parse_paused_track_preserves_is_playing_false():
    data = parse_now_playing(_track_payload(is_playing=False))
    assert data["is_playing"] is False


def test_parse_multi_artist_joins_with_comma_space():
    data = parse_now_playing(_track_payload(artists=("Daft Punk", "Pharrell Williams")))
    assert data["artist"] == "Daft Punk, Pharrell Williams"


def test_parse_episode_uses_show_name_as_artist():
    data = parse_now_playing(_episode_payload())
    assert data == {
        "track": "Hard Fork",
        "artist": "The New York Times",
        "is_playing": True,
    }


def test_parse_ad_returns_none():
    payload = {
        "is_playing": True,
        "currently_playing_type": "ad",
        "item": None,
    }
    assert parse_now_playing(payload) is None


def test_parse_unknown_type_returns_none():
    payload = {
        "is_playing": True,
        "currently_playing_type": "unknown_thing",
        "item": {"name": "x", "artists": [{"name": "y"}]},
    }
    assert parse_now_playing(payload) is None


def test_parse_track_with_missing_name_returns_none():
    payload = {
        "is_playing": True,
        "currently_playing_type": "track",
        "item": {"artists": [{"name": "Queen"}]},
    }
    assert parse_now_playing(payload) is None


def test_parse_track_with_no_artists_returns_none():
    payload = {
        "is_playing": True,
        "currently_playing_type": "track",
        "item": {"name": "x", "artists": []},
    }
    assert parse_now_playing(payload) is None


def test_parse_episode_with_missing_show_returns_none():
    payload = {
        "is_playing": True,
        "currently_playing_type": "episode",
        "item": {"name": "x"},
    }
    assert parse_now_playing(payload) is None
```

- [ ] **Step 2: Run tests — verify the new ones fail**

Run: `python3 -m pytest tests/test_spotify.py -v`
Expected: 12 failures with `AttributeError: module 'spotify' has no attribute 'parse_now_playing'`.

- [ ] **Step 3: Append implementation to `spotify.py`**

```python
def parse_now_playing(payload):
    """Extract track/artist/is_playing from a Spotify currently-playing payload.

    Returns dict or None. Returns None for:
      - empty / None payload
      - missing or null `item`
      - `currently_playing_type` not in {"track", "episode"}
      - missing `name`
      - track with empty or missing `artists`
      - episode with missing `show.name`
    """
    if not payload:
        return None
    item = payload.get("item")
    if not item:
        return None
    cp_type = payload.get("currently_playing_type", "")
    name = item.get("name")
    if not name:
        return None
    if cp_type == "track":
        artists = item.get("artists") or []
        artist_names = [a.get("name", "") for a in artists if a.get("name")]
        if not artist_names:
            return None
        artist = ", ".join(artist_names)
    elif cp_type == "episode":
        show = item.get("show") or {}
        artist = show.get("name", "")
        if not artist:
            return None
    else:
        return None
    return {
        "track": name,
        "artist": artist,
        "is_playing": bool(payload.get("is_playing")),
    }
```

- [ ] **Step 4: Run tests — verify all pass**

Run: `python3 -m pytest tests/test_spotify.py -v`
Expected: 21 passed.

- [ ] **Step 5: Commit**

```bash
git add spotify.py tests/test_spotify.py
git commit -m "Add parse_now_playing for Spotify API payloads"
```

---

## Task 3: spotify.py display layer (no network)

**Files:**
- Modify: `spotify.py` (append display/state code)

This task adds `build`, `render`, `tick`, `apply_brightness`, `set_hidden`, plus the `_state` dict and color constants. No network code yet — those come in Tasks 4 and 5.

- [ ] **Step 1: Append display layer to `spotify.py`**

Append (do not remove `marquee_window` or `parse_now_playing`):

```python
import os

from brightness import scale


_TRACK_COLOR = 0x1ED760    # Spotify green
_ARTIST_COLOR = 0x999999   # Dim white
_PAUSE_DIM = 0.4

_state = {
    "group": None,
    "track_label": None,
    "artist_label": None,
    "font": None,              # lazily loaded in build()
    "session": None,           # lazily created in fetch() (Task 5)
    "access_token": None,
    "expires_at": 0.0,
    "refresh_token": os.getenv("SPOTIFY_REFRESH_TOKEN", ""),
    "client_id": os.getenv("SPOTIFY_CLIENT_ID", ""),
    "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET", ""),
    "auth_failed": False,
    "logged_not_configured": False,
    "track_text": "",
    "artist_text": "",
    "track_offset": 0,
    "artist_offset": 0,
    "is_playing": False,
    "has_data": False,
    "last_factor": 1.0,
}


def build(x, y, width, height):
    """Create the Spotify quadrant displayio.Group (initially hidden)."""
    import displayio
    from adafruit_display_text.label import Label
    from adafruit_bitmap_font import bitmap_font

    if _state["font"] is None:
        _state["font"] = bitmap_font.load_font("/lib/fonts/5x8.bdf")

    group = displayio.Group(x=x, y=y)
    track_label = Label(_state["font"], text="", color=_TRACK_COLOR)
    track_label.x = 2
    track_label.y = 8
    artist_label = Label(_state["font"], text="", color=_ARTIST_COLOR)
    artist_label.x = 2
    artist_label.y = 20
    group.append(track_label)
    group.append(artist_label)
    group.hidden = True

    _state["group"] = group
    _state["track_label"] = track_label
    _state["artist_label"] = artist_label
    return group


def render(data):
    """Update labels from a parse_now_playing() result (or None to clear)."""
    if _state["track_label"] is None:
        return
    if data is None:
        _state["has_data"] = False
        _state["track_text"] = ""
        _state["artist_text"] = ""
        _state["track_label"].text = ""
        _state["artist_label"].text = ""
        _apply_label_brightness()
        return

    track = data["track"]
    artist = data["artist"]
    is_playing = bool(data["is_playing"])

    if track != _state["track_text"] or artist != _state["artist_text"]:
        _state["track_offset"] = 0
        _state["artist_offset"] = 0
    _state["track_text"] = track
    _state["artist_text"] = artist
    _state["is_playing"] = is_playing
    _state["has_data"] = True

    _state["track_label"].text = marquee_window(track, _state["track_offset"])
    _state["artist_label"].text = marquee_window(artist, _state["artist_offset"])
    _apply_label_brightness()


def tick():
    """Advance the marquee by one character. No-op when hidden or paused."""
    if _state["group"] is None or _state["group"].hidden:
        return
    if not _state["has_data"] or not _state["is_playing"]:
        return
    _state["track_offset"] += 1
    _state["artist_offset"] += 1
    _state["track_label"].text = marquee_window(
        _state["track_text"], _state["track_offset"]
    )
    _state["artist_label"].text = marquee_window(
        _state["artist_text"], _state["artist_offset"]
    )


def apply_brightness(factor):
    _state["last_factor"] = factor
    _apply_label_brightness()


def _apply_label_brightness():
    if _state["track_label"] is None:
        return
    factor = _state["last_factor"]
    paused = _state["has_data"] and not _state["is_playing"]
    eff = factor * (_PAUSE_DIM if paused else 1.0)
    _state["track_label"].color = scale(_TRACK_COLOR, eff)
    _state["artist_label"].color = scale(_ARTIST_COLOR, eff)


def set_hidden(hidden):
    if _state["group"] is not None:
        _state["group"].hidden = hidden
```

- [ ] **Step 2: Run pytest — verify no regression**

Run: `python3 -m pytest`
Expected: 67 passed (46 existing + 21 from Tasks 1-2). The new imports (`os`, `brightness.scale`) are host-safe; the CircuitPython imports are inside `build()`.

- [ ] **Step 3: Commit**

```bash
git add spotify.py
git commit -m "Add spotify.py display layer (build/render/tick/brightness/hide)"
```

---

## Task 4: spotify.py auth (refresh-token exchange)

**Files:**
- Modify: `spotify.py` (append)

- [ ] **Step 1: Append the auth helper**

Append to `spotify.py`:

```python
import binascii
import time as _time


def _ensure_session(pool):
    if _state["session"] is None:
        import ssl
        import adafruit_requests
        _state["session"] = adafruit_requests.Session(
            pool, ssl.create_default_context()
        )
    return _state["session"]


def _refresh_access_token(pool):
    """POST refresh_token grant to /api/token. Returns True on success.

    On a 400 invalid_grant, latches _state["auth_failed"] = True so subsequent
    polls do nothing until reboot + re-running scripts/spotify_auth.py.
    """
    session = _ensure_session(pool)
    creds = "{}:{}".format(_state["client_id"], _state["client_secret"]).encode()
    auth = binascii.b2a_base64(creds, newline=False).decode()
    headers = {
        "Authorization": "Basic " + auth,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    body = "grant_type=refresh_token&refresh_token=" + _state["refresh_token"]
    try:
        resp = session.post(
            "https://accounts.spotify.com/api/token",
            data=body,
            headers=headers,
        )
    except Exception as e:
        print("spotify: token refresh request failed:", e)
        return False
    try:
        if resp.status_code == 400:
            _state["auth_failed"] = True
            print(
                "spotify: refresh token rejected — "
                "run scripts/spotify_auth.py again"
            )
            return False
        if resp.status_code != 200:
            print("spotify: token refresh HTTP", resp.status_code)
            return False
        try:
            token_data = resp.json()
        except Exception as e:
            print("spotify: token JSON parse failed:", e)
            return False
    finally:
        resp.close()

    access = token_data.get("access_token")
    if not access:
        print("spotify: no access_token in refresh response")
        return False
    _state["access_token"] = access
    expires_in = int(token_data.get("expires_in", 3600))
    _state["expires_at"] = _time.monotonic() + expires_in - 60
    return True
```

- [ ] **Step 2: Run pytest — verify no regression**

Run: `python3 -m pytest`
Expected: 67 passed. `binascii` is in stdlib; `time as _time` doesn't break host imports.

- [ ] **Step 3: Commit**

```bash
git add spotify.py
git commit -m "Add spotify refresh-token exchange"
```

---

## Task 5: spotify.py fetch (currently-playing)

**Files:**
- Modify: `spotify.py` (append)

- [ ] **Step 1: Append `fetch`**

Append to `spotify.py`:

```python
_CURRENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"


def _is_configured():
    return bool(
        _state["client_id"]
        and _state["client_secret"]
        and _state["refresh_token"]
    )


def _log_not_configured_once():
    if not _state["logged_not_configured"]:
        print("spotify: not configured, feature disabled")
        _state["logged_not_configured"] = True


def fetch(pool):
    """Fetch the currently-playing track. Returns parse_now_playing() result or None."""
    if not _is_configured():
        _log_not_configured_once()
        return None
    if _state["auth_failed"]:
        return None

    if (
        _state["access_token"] is None
        or _time.monotonic() >= _state["expires_at"]
    ):
        if not _refresh_access_token(pool):
            return None

    payload = _request_currently_playing(pool)
    if payload is _RETRY_AFTER_REFRESH:
        if not _refresh_access_token(pool):
            return None
        payload = _request_currently_playing(pool)
        if payload is _RETRY_AFTER_REFRESH:
            return None
    return parse_now_playing(payload) if payload else None


_RETRY_AFTER_REFRESH = object()  # sentinel for 401 path


def _request_currently_playing(pool):
    """Make the GET request. Returns:
      - dict payload on 200
      - None on 204, 429, network error, or non-recoverable HTTP
      - _RETRY_AFTER_REFRESH sentinel on 401 (caller should re-refresh and retry once)
    """
    session = _ensure_session(pool)
    headers = {"Authorization": "Bearer " + _state["access_token"]}
    try:
        resp = session.get(_CURRENTLY_PLAYING_URL, headers=headers)
    except Exception as e:
        print("spotify: currently-playing request failed:", e)
        return None
    try:
        if resp.status_code == 204:
            return None
        if resp.status_code == 401:
            return _RETRY_AFTER_REFRESH
        if resp.status_code == 429:
            print("spotify: rate limited (429)")
            return None
        if resp.status_code != 200:
            print("spotify: currently-playing HTTP", resp.status_code)
            return None
        try:
            return resp.json()
        except Exception as e:
            print("spotify: currently-playing JSON parse failed:", e)
            return None
    finally:
        resp.close()
```

- [ ] **Step 2: Run pytest — verify no regression**

Run: `python3 -m pytest`
Expected: 67 passed.

- [ ] **Step 3: Commit**

```bash
git add spotify.py
git commit -m "Add spotify.fetch for currently-playing endpoint"
```

---

## Task 6: sun.set_hidden

**Files:**
- Modify: `sun.py`

- [ ] **Step 1: Append `set_hidden` to `sun.py`**

Append to `sun.py` (after `apply_brightness`):

```python
def set_hidden(hidden):
    if _state["group"] is not None:
        _state["group"].hidden = hidden
```

- [ ] **Step 2: Run pytest — verify no regression**

Run: `python3 -m pytest`
Expected: 67 passed.

- [ ] **Step 3: Commit**

```bash
git add sun.py
git commit -m "Add sun.set_hidden for Spotify swap"
```

---

## Task 7: scripts/spotify_auth.py (host-side OAuth helper)

**Files:**
- Create: `scripts/spotify_auth.py`

- [ ] **Step 1: Write the helper script**

```python
#!/usr/bin/env python3
"""One-time host-side OAuth helper for the Spotify currently-playing scope.

Usage:
    python3 scripts/spotify_auth.py --client-id <id> --client-secret <secret>

Steps:
  1. Spins up a one-shot HTTP server on http://127.0.0.1:8080/callback.
  2. Opens the Spotify authorize URL in the user's browser.
  3. Captures the redirect's code, exchanges it for a refresh_token.
  4. Prints settings.toml lines to paste into the project's settings.toml.

The Spotify Developer app must have http://127.0.0.1:8080/callback registered
as a redirect URI (exact match — Spotify rejects the hostname "localhost").
"""
import argparse
import http.server
import json
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser


REDIRECT_URI = "http://127.0.0.1:8080/callback"
SCOPE = "user-read-currently-playing"
HOST = "127.0.0.1"
PORT = 8080

_captured = {"code": None, "state": None, "error": None}


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        q = urllib.parse.parse_qs(parsed.query)
        _captured["code"] = q.get("code", [None])[0]
        _captured["state"] = q.get("state", [None])[0]
        _captured["error"] = q.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if _captured["error"]:
            msg = "Spotify denied authorization: " + _captured["error"]
        else:
            msg = "Authorization captured. You can close this tab."
        self.wfile.write(
            ("<html><body><h2>" + msg + "</h2></body></html>").encode()
        )

    def log_message(self, fmt, *args):
        return  # silence default access log


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--client-id", required=True)
    p.add_argument("--client-secret", required=True)
    args = p.parse_args()

    state = secrets.token_urlsafe(16)
    authorize_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(
        {
            "client_id": args.client_id,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "state": state,
        }
    )

    print("Opening browser for Spotify authorization...")
    print("If it doesn't open, paste this URL into your browser:")
    print("  " + authorize_url)
    webbrowser.open(authorize_url)

    server = http.server.HTTPServer((HOST, PORT), _CallbackHandler)
    print("Waiting for the redirect on " + REDIRECT_URI + " ...")
    server.handle_request()
    server.server_close()

    if _captured["error"]:
        print("Spotify returned error:", _captured["error"], file=sys.stderr)
        sys.exit(1)
    if _captured["state"] != state:
        print("State mismatch — possible CSRF; aborting.", file=sys.stderr)
        sys.exit(1)
    if not _captured["code"]:
        print("No authorization code received.", file=sys.stderr)
        sys.exit(1)

    token_req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode(
            {
                "grant_type": "authorization_code",
                "code": _captured["code"],
                "redirect_uri": REDIRECT_URI,
                "client_id": args.client_id,
                "client_secret": args.client_secret,
            }
        ).encode(),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(token_req, timeout=10) as resp:
            token_data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print("Token exchange failed:", e.code, e.read().decode(), file=sys.stderr)
        sys.exit(1)

    refresh = token_data.get("refresh_token")
    if not refresh:
        print("Spotify did not return a refresh_token:", token_data, file=sys.stderr)
        sys.exit(1)

    print()
    print("=== Success! ===")
    print("Add these lines to settings.toml (the file is gitignored):")
    print()
    print('SPOTIFY_CLIENT_ID = "{}"'.format(args.client_id))
    print('SPOTIFY_CLIENT_SECRET = "{}"'.format(args.client_secret))
    print('SPOTIFY_REFRESH_TOKEN = "{}"'.format(refresh))
    print('SPOTIFY_REFRESH_SEC = "10"')
    print()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Syntax-check**

Run: `python3 -m py_compile scripts/spotify_auth.py`
Expected: no output, exit 0.

- [ ] **Step 3: Smoke-test the help text**

Run: `python3 scripts/spotify_auth.py --help`
Expected: argparse help with `--client-id` and `--client-secret` listed.

- [ ] **Step 4: Commit**

```bash
git add scripts/spotify_auth.py
git commit -m "Add host-side Spotify OAuth helper"
```

---

## Task 8: settings.toml updates (local only)

**Files:**
- Modify: `settings.toml` (gitignored — do NOT `git add`)

- [ ] **Step 1: Append Spotify keys to `settings.toml`**

Open `settings.toml` and append:

```toml

# Spotify (optional — leave any of the three blank to disable the feature)
SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""
SPOTIFY_REFRESH_TOKEN = ""
SPOTIFY_REFRESH_SEC = "10"
```

Keep the values empty unless you've already run `scripts/spotify_auth.py`. With empty values, the dashboard behaves exactly as it does today.

- [ ] **Step 2: Verify the file is still gitignored**

Run: `git status`
Expected: no `settings.toml` entry in either staged or unstaged sections. If it appears, stop — the `.gitignore` rule is broken and the credentials would leak.

- [ ] **Step 3: No commit**

This task has no git commit. `settings.toml` is gitignored.

---

## Task 9: deploy.sh — copy spotify.py

**Files:**
- Modify: `deploy.sh`

- [ ] **Step 1: Add `spotify.py` to the module copy list**

Find the line in `deploy.sh`:

```bash
  for f in code.py clock.py wifi_setup.py tz.py brightness.py weather.py sun.py logo.py; do
```

Replace with:

```bash
  for f in code.py clock.py wifi_setup.py tz.py brightness.py weather.py sun.py logo.py spotify.py; do
```

- [ ] **Step 2: Syntax-check**

Run: `bash -n deploy.sh`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add deploy.sh
git commit -m "Deploy spotify.py to CIRCUITPY"
```

---

## Task 10: code.py — wire spotify into boot + main loop

**Files:**
- Modify: `code.py`

- [ ] **Step 1: Add spotify import + setting + group construction**

In `code.py`, near the top with the other module imports, after `import logo`:

```python
import spotify
```

In the settings block at the top, after `_BRIGHTNESS_DEFAULT = ...`, add:

```python
_SPOTIFY_REFRESH_SEC = int(os.getenv("SPOTIFY_REFRESH_SEC", "10"))
```

After `logo_group = logo.build(32, 32, 32, 32)`, add:

```python
spotify_group = spotify.build(0, 32, 32, 32)
```

After `root.append(logo_group)`, add:

```python
root.append(spotify_group)
```

Find the `QUADRANTS = (clock, weather, sun, logo)` line and change it to:

```python
QUADRANTS = (clock, weather, sun, logo, spotify)
```

- [ ] **Step 2: Add the swap helper**

After `_initial_weather(pool)` function definition (around the existing helper functions), add:

```python
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
```

- [ ] **Step 3: Add the boot call after `_initial_weather`**

Find the line `sunrise_minutes, sunset_minutes = _initial_weather(pool)` and add immediately after it:

```python
_initial_spotify(pool)
```

- [ ] **Step 4: Add the main-loop cadences**

Find the existing main loop. Before `while True:` add (alongside `last_tick`, `last_weather`, `last_ntp`):

```python
last_spotify = time.monotonic()
last_marquee = time.monotonic()
```

Inside `while True:`, after the `brightness.poll()` block and BEFORE the `if now - last_tick >= 1.0:` block, add the marquee tick:

```python
    if now - last_marquee >= 0.25:
        spotify.tick()
        last_marquee = now
```

After the existing weather refresh block (`if now - last_weather >= _WEATHER_REFRESH_SEC:`), add the spotify refresh block:

```python
    if now - last_spotify >= _SPOTIFY_REFRESH_SEC:
        try:
            data = spotify.fetch(pool)
            spotify.render(data)
            _apply_spotify_swap(data)
        except Exception as e:
            print("spotify: refresh failed:", e)
        last_spotify = now
```

- [ ] **Step 5: Run pytest — verify no host-side regression**

Run: `python3 -m pytest`
Expected: 67 passed. `code.py` isn't imported by the test suite, so this is a sanity check on the other modules.

- [ ] **Step 6: Read the modified `code.py` end-to-end**

Open `code.py` and verify by eye:
- One `import spotify` near the top
- `spotify_group = spotify.build(0, 32, 32, 32)` and `root.append(spotify_group)` are present
- `QUADRANTS` includes `spotify`
- `_initial_spotify(pool)` is called once after `_initial_weather(pool)`
- `_apply_spotify_swap(data)` is defined and called from both boot and the loop
- The main loop has the 250 ms marquee block and the 10 s spotify block

- [ ] **Step 7: Commit**

```bash
git add code.py
git commit -m "Wire spotify into code.py boot and main loop"
```

---

## Task 11: On-device smoke test

These tests run on the MatrixPortal S3 itself. They are manual.

**Setup (do this once before the checklist):**

- [ ] **Step 1: Create a Spotify Developer app**

1. Go to https://developer.spotify.com/dashboard and create a new app.
2. Note the Client ID and Client Secret (use "Show client secret" once).
3. Edit Settings → Redirect URIs → add `http://127.0.0.1:8080/callback` exactly. Save.

- [ ] **Step 2: Run the OAuth helper**

Run from the project root:

```bash
python3 scripts/spotify_auth.py --client-id <YOUR_ID> --client-secret <YOUR_SECRET>
```

A browser opens. Log in to Spotify, grant access. The script prints four `settings.toml` lines.

- [ ] **Step 3: Paste credentials into `settings.toml`**

Replace the empty Spotify keys in `settings.toml` with the four lines the script printed. Keep them inside the existing `# Spotify (...)` block.

- [ ] **Step 4: Deploy**

```bash
./deploy.sh --with-settings
```

The `--with-settings` flag is needed so the new Spotify keys reach the device.

**Smoke checks:**

- [ ] **Step 5: Cold boot with nothing playing**

Watch the panel: clock, weather, sun (bottom-left), logo all visible. Open `screen /dev/ttyACM0 115200` and confirm no spotify error lines printed.

- [ ] **Step 6: Start a track on the configured account**

Within ~10 s the bottom-left quadrant swaps from the sun to the Spotify display. Title and artist appear (scrolling if longer than 6 chars).

- [ ] **Step 7: Verify the marquee**

Pick a track with a long title (e.g., "Bohemian Rhapsody – Remastered 2011"). Title scrolls character-by-character with a visible 3-space gap between loops.

- [ ] **Step 8: Pause the track on the phone**

Within ~10 s the Spotify quadrant dims (0.4× extra dim) and the marquee freezes. Sun does not reappear.

- [ ] **Step 9: Stop playback entirely**

Close the Spotify app on the phone, or wait for the active device to drop. Within ~10 s the sun quadrant returns.

- [ ] **Step 10: Brightness still works**

Press UP/DOWN buttons while a track is playing. All four visible quadrants (clock, weather, spotify, logo) dim/brighten in sync.

- [ ] **Step 11: Revoke app access (failure path)**

Go to https://www.spotify.com/account/apps/, revoke the dashboard's access. On next refresh (≤ 10 s), the serial log prints `"spotify: refresh token rejected — run scripts/spotify_auth.py again"`. The sun quadrant stays visible and no further polls happen. Re-grant access by re-running the helper.

- [ ] **Step 12: Empty creds (disabled-feature path)**

Empty `SPOTIFY_REFRESH_TOKEN` in `settings.toml`, redeploy with `--with-settings`, reboot. Serial logs `"spotify: not configured, feature disabled"` once at boot. Sun quadrant always visible regardless of playback.

(Restore the token afterward.)

- [ ] **Step 13: Final commit (if anything was tweaked during smoke testing)**

```bash
git status
# If you tweaked any colors, offsets, or polling cadence to taste:
git add -p
git commit -m "Smoke-test adjustments"
```

---

## Self-review notes

Cross-checked the plan against `docs/superpowers/specs/2026-05-20-spotify-now-playing-design.md`:

- **Layout & visual states** (spec §Layout): Tasks 3, 10 (build + render + swap helper). Colors `0x1ED760` / `0x999999`, 0.4× pause dim, label positions match spec.
- **Module structure** (spec §Module structure): all five new/modified files mapped to specific tasks.
- **`spotify.py` interface**: Task 1 (marquee_window), Task 2 (parse_now_playing), Task 3 (build/render/tick/apply_brightness/set_hidden), Tasks 4-5 (fetch + token refresh).
- **`sun.py` change**: Task 6.
- **`scripts/spotify_auth.py`**: Task 7. Uses 127.0.0.1 (not localhost), stdlib only, state CSRF check.
- **Settings**: Task 8 — local-only edit, no git add.
- **Auth & token lifecycle** (spec §Auth): Task 4 covers refresh; Task 5 covers 401 retry-once and 400 auth-failed latch.
- **Module state**: Task 3.
- **Data flow & main loop**: Task 10 — boot, 250 ms marquee, 10 s spotify, swap on each cadence.
- **Error handling** (spec §Error handling): Task 5 covers 204/200/401/429/network/JSON paths; Task 4 covers 400 invalid_grant; Task 10 wraps top-level exception in the main loop.
- **Testing** (spec §Testing): Task 1 (marquee tests), Task 2 (parser tests), Task 11 (on-device smoke).

No type/name drift on re-read — `_state` keys are introduced in Task 3 and referenced consistently in Tasks 4/5; `set_hidden`, `marquee_window`, `parse_now_playing` signatures match across all uses.

Pillow's `ImageDraw.text()` deprecation noted in the previous review is unrelated and stays out of scope here.
