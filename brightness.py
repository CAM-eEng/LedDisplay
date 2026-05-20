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
