# Two-Panel Layout — Design

## Goal

Support a horizontal two-panel chain (128×64) in addition to the existing single 64×64 panel. The active configuration is selected by a single `LAYOUT_NAME` key in `settings.toml`. The architecture is data-driven so adding more configurations later (e.g. a 4-panel 128×128 build) is a single dict-entry change in `layouts.py` with no other code touched.

## Non-goals

- Hardware procurement guidance (covered by `docs/4-panel-expansion-todo.md`).
- Larger fonts than 5×8 / 6×10 (deferred — existing fonts work at the new layout's quadrant sizes).
- Persisting layout choice across reboots (it already does — `LAYOUT_NAME` lives in `settings.toml`).
- Hot-reload of layout without rebooting.
- 4-panel or vertically-chained configurations (those become new `layouts.py` entries when they land).

## Layout — 128×64

Horizontal 2×1 chain. One 64×64 hero on the left panel, three smaller widgets on the right panel: two 32×32 across the top and one 64×32 across the bottom.

```
┌───────────────┬───────┬───────┐
│               │ clock │weather│   ← two 32×32 widgets
│               │ 32×32 │ 32×32 │
│   logo (hero) ├───────┴───────┤
│   64×64       │               │
│               │  spotify/sun  │   ← wide 64×32 widget
│               │     64×32     │
└───────────────┴───────────────┘
  panel 1 (0,0)        panel 2 (64,0)
```

### Content slot mapping

| Rect (x, y, w, h) | Content |
|---|---|
| 0, 0, 64, 64 | Arc Raiders logo (`logo64.bmp`) |
| 64, 0, 32, 32 | Clock + zone abbrev + date |
| 96, 0, 32, 32 | Weather temp + condition icon |
| 64, 32, 64, 32 | Spotify (when playing or paused) / sun next-event (idle) — conditional swap via existing `_apply_spotify_swap` |

The existing 64×64 layout is preserved unchanged as a separate entry in `layouts.py`.

## File map

### New

- `layouts.py` — declarative layout definitions. Module-level dict only; no logic.

### Modified

- `code.py` — replace the hardcoded `Matrix(...)` init + quadrant build block with a layout-driven composer that resolves `LAYOUT_NAME` and iterates `layout["quadrants"]`. Change `BRIGHTNESS_DEFAULT` fallback from `"3"` to `"0"`.
- `logo.py` — `build()` auto-picks `logo64.bmp` vs `logo32.bmp` based on the passed `width` when no explicit `path=` is supplied.
- `sun.py` — `build()` stashes `width` and `height` in `_state` (label positions unchanged).
- `spotify.py` — `build()` stashes `width` in `_state` and computes a per-layout `marquee_window` (`width // 5` chars). `render` and `tick` pass that window through to `marquee_window(...)`.
- `test_panel.py` — read `LAYOUT_NAME` and source `WIDTH`/`HEIGHT`/`TILE_ROWS`/`SERPENTINE` from the same layout dict.
- `settings.toml` — add `LAYOUT_NAME = "128x64"`; change `BRIGHTNESS_DEFAULT` from `"3"` to `"0"` (local edit; file is gitignored).

### Untouched

- `clock.py`, `weather.py` — appear only at 32×32 in both current layouts.
- `tz.py`, `brightness.py`, `wifi_setup.py` — unrelated.
- `deploy.sh` — already copies every `.py` at the project root; picks up `layouts.py` for free.
- `install_libs.sh` — no new libs.
- `pyproject.toml`, `tests/conftest.py`, all existing test files — unchanged.

## `layouts.py`

```python
"""Named display layouts. Each entry describes a panel chain and the
quadrant rectangles within it. Add new entries here when adding new
panel configurations; no other code changes required for content
modules that already support the requested sizes.

Quadrant rect tuples: (module_name, x, y, width, height).
Append order = displayio z-order (later = drawn on top).
"""

LAYOUTS = {
    "64x64": {
        "width": 64,
        "height": 64,
        "tile_rows": 1,
        "serpentine": False,
        "quadrants": [
            ("clock",    0,  0, 32, 32),
            ("weather", 32,  0, 32, 32),
            ("sun",      0, 32, 32, 32),
            ("logo",    32, 32, 32, 32),
            ("spotify",  0, 32, 32, 32),
        ],
    },
    "128x64": {
        "width": 128,
        "height": 64,
        "tile_rows": 1,
        "serpentine": False,
        "quadrants": [
            ("logo",     0,  0, 64, 64),
            ("clock",   64,  0, 32, 32),
            ("weather", 96,  0, 32, 32),
            ("sun",     64, 32, 64, 32),
            ("spotify", 64, 32, 64, 32),
        ],
    },
}

DEFAULT_LAYOUT = "64x64"
```

Important conventions captured by the data:
- The `quadrants` list is **z-ordered**. Sun is declared before Spotify so Spotify renders on top when both are visible (matches today's behavior).
- The driver fields (`tile_rows`, `serpentine`, `width`, `height`) live in the same dict as the rects; they can't desync.
- Module names are strings, not direct references — keeps the data clean and lets `code.py` own the name→module mapping.

## Per-module changes

### `logo.py`

```python
def build(x, y, width, height, path=None):
    if path is None:
        if max(width, height) >= 64:
            path = "/images/arc_raiders_logo/logo64.bmp"
        else:
            path = "/images/arc_raiders_logo/logo32.bmp"
    # rest unchanged
```

The existing OSError/ValueError catch for missing BMP files stays. Explicit `path=` argument still overrides.

### `sun.py`

```python
def build(x, y, width, height):
    # existing displayio.Group setup unchanged
    _state["width"] = width
    _state["height"] = height
    # labels at (2, 8) and (2, 20) — unchanged. They left-align cleanly
    # at both 32 wide and 64 wide.
```

No render-path change. The 64-wide quadrant simply has empty pixels to the right of the labels, which on a low-res panel looks fine.

### `spotify.py`

```python
def build(x, y, width, height):
    # existing displayio.Group + label setup unchanged
    _state["width"] = width
    _state["marquee_window"] = max(1, width // 5)   # ~6 chars at 32px, ~12 at 64px
```

```python
# In render() and tick(), replace existing marquee_window calls:
_state["track_label"].text = marquee_window(
    _state["track_text"], _state["track_offset"], window=_state["marquee_window"]
)
_state["artist_label"].text = marquee_window(
    _state["artist_text"], _state["artist_offset"], window=_state["marquee_window"]
)
```

`marquee_window` already accepts `window=` — no changes to the helper or its tests.

### `clock.py`, `weather.py`

No changes. They're only invoked at 32×32 in every planned layout.

## `code.py` refactor

Replace the hardcoded layout block:

```python
# Old:
MATRIX_WIDTH = 64
MATRIX_HEIGHT = 64
BIT_DEPTH = 4

matrix = Matrix(width=MATRIX_WIDTH, height=MATRIX_HEIGHT, bit_depth=BIT_DEPTH,
                tile_rows=1, serpentine=False)
display = matrix.display

root = displayio.Group()
clock_group = clock.build(0, 0, 32, 32)
# ... five hardcoded build/append calls
QUADRANTS = (clock, weather, sun, logo, spotify)
```

with:

```python
import layouts

BIT_DEPTH = 4

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

QUADRANTS = tuple(_ordered_quadrants)
```

Change `BRIGHTNESS_DEFAULT` fallback in the same file:

```python
# Old:
_BRIGHTNESS_DEFAULT = int(os.getenv("BRIGHTNESS_DEFAULT", "3"))
# New:
_BRIGHTNESS_DEFAULT = int(os.getenv("BRIGHTNESS_DEFAULT", "0"))
```

Everything else in `code.py` — boot sequence, helper functions, main loop cadences — is unchanged. `_apply_spotify_swap`, `brightness.poll()` fan-out, the 250 ms marquee tick, the 10 s Spotify poll, the 15 min weather refresh, the 1 hr NTP resync: all unmodified.

## Settings

`settings.toml` gains one key and changes one value:

```toml
LAYOUT_NAME = "128x64"
BRIGHTNESS_DEFAULT = "0"   # was "3"
```

Defaults if either key is missing:
- `LAYOUT_NAME` missing → `"64x64"` (no behavior change for existing devices).
- `BRIGHTNESS_DEFAULT` missing → `"0"` (the dimmest level, per the new in-code fallback).

## `test_panel.py` updates

The diagnostic switches from hardcoded dimensions to reading from `layouts.LAYOUTS`. The rest of the file (corner labels, centered config text, `Matrix(...)` init pattern) stays the same — those already adapt to `WIDTH`/`HEIGHT`.

```python
# Top of test_panel.py
import os
import layouts

BIT_DEPTH = 4
FORCE_4_ADDR_PINS = False

_layout = layouts.LAYOUTS.get(
    os.getenv("LAYOUT_NAME", layouts.DEFAULT_LAYOUT),
    layouts.LAYOUTS[layouts.DEFAULT_LAYOUT],
)
WIDTH = _layout["width"]
HEIGHT = _layout["height"]
TILE_ROWS = _layout["tile_rows"]
SERPENTINE = _layout["serpentine"]
```

### Standard chain-bring-up workflow

1. `settings.toml` → `LAYOUT_NAME = "128x64"`.
2. `./deploy.sh --with-settings` — pushes the regular dashboard plus `layouts.py` and the new settings.
3. `./deploy.sh --test` — overwrites `code.py` with `test_panel.py` for the corner-marker diagnostic. `TL`/`TR`/`BL`/`BR` should land at the four corners of the combined 128×64 array. If a panel is rotated, `serpentine` is wrong; if pixels are scrambled, `tile_rows` is wrong.
4. `./deploy.sh` — restore the dashboard.

## Error handling

| Failure | Behavior |
|---|---|
| `LAYOUT_NAME` unset / empty | Default to `"64x64"`. Single-panel dashboards unaffected. |
| `LAYOUT_NAME` set to an unknown key | Print warning, fall back to `"64x64"`. No halt. |
| Layout references an unknown module name | Print warning, skip that quadrant. Remaining quadrants build normally. |
| `Matrix(...)` init fails (dimensions don't match wiring) | Hard crash with serial traceback. Recovery: fix `LAYOUT_NAME` or the chain. |
| `logo64.bmp` missing for the `128x64` layout | The hero stays blank; serial logs "logo: could not load …". Other quadrants render normally. |
| Future layout omits `sun` or `spotify` | `set_hidden` no-ops when the module's group is `None`; swap helper doesn't crash. |
| Power droop on the second panel | Hardware issue, not software. Visible as dimming/flicker; software brightness scaling still works to cap draw. |

### Boot output

On a successful `128x64` boot, the serial log shows:

```
layout: 128x64 (128x64, 5 quadrants)
Connecting to <SSID>
Connected, IP: <addr>
```

The single `layout: …` line makes it obvious from the console which layout is active.

## Testing

### Host-side (pytest)

The existing 68 tests are layout-agnostic and remain valid (`marquee_window`, `parse_now_playing`, `tz` helpers, `brightness.scale`, `sun.next_event`, `weather.code_to_icon`). No new pytest coverage is added — the changes are either declarative data (`layouts.py`), a small `build()` parameter pass-through (`spotify`, `sun`), or path selection (`logo`), all hardware-rendered surfaces.

### On-device smoke checklist

- [ ] `settings.toml` → `LAYOUT_NAME = "128x64"`, `BRIGHTNESS_DEFAULT = "0"`. Deploy with `--with-settings`.
- [ ] `./deploy.sh --test` → corner markers land at the four corners of the 128×64 array.
- [ ] `./deploy.sh` → dashboard boots. Serial shows `layout: 128x64 (128x64, 5 quadrants)`.
- [ ] Logo renders sharp in the left panel's 64×64 hero slot (`logo64.bmp`).
- [ ] Clock occupies upper-right 32×32 (`64, 0, 32, 32`); time/zone/date readable.
- [ ] Weather occupies upper-right-right 32×32 (`96, 0, 32, 32`).
- [ ] With Spotify playing: bottom-right shows wide marquees, ~12 chars per row instead of 6.
- [ ] With Spotify idle: bottom-right shows the sun next-event in the wider slot.
- [ ] Brightness UP/DOWN affects all five quadrants uniformly across both panels.
- [ ] Set `LAYOUT_NAME = "64x64"`, redeploy with `--with-settings` — left panel shows the original 4-quadrant layout; right panel goes dark. Confirms backward compatibility.
- [ ] Set `LAYOUT_NAME = "typo"`, redeploy — serial warns about unknown layout, dashboard falls back to `64x64`.

## Out of scope / future work

- 4-panel (2×2 = 128×128) layout entry — straightforward addition to `layouts.py` once hardware is in hand.
- Larger fonts (10×20 etc.) for the bigger quadrants in future layouts.
- Per-layout color overrides.
- Per-layout `BIT_DEPTH` if performance demands it on bigger chains.
- Layout-aware brightness ceilings (e.g., cap max brightness for power-limited setups).
