"""Spotify now-playing quadrant for the LED dashboard."""

import binascii
import os
import time as _time

from brightness import scale


def marquee_window(text, offset, window=6, gap="   "):
    """Return a `window`-character slice of `text + gap`, wrapping at the end.

    Used to drive a character-step scrolling marquee. Strings shorter than
    `window` are returned unchanged (no scrolling). The gap separates the
    end of the text from its restart on the next loop.
    """
    if not text:
        return ""
    padded = text + gap
    n = len(padded)
    # If text is short enough to fit in the window and padded text is long enough,
    # the text won't need scrolling to fill the window
    if len(text) <= window and n >= window:
        return text
    # Scrolling is needed: use the wrapping logic
    o = offset % n
    if o + window <= n:
        return padded[o:o + window]
    return padded[o:] + padded[:window - (n - o)]


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
