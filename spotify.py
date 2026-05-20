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
