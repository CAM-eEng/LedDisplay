"""Spotify now-playing quadrant for the LED dashboard."""


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
