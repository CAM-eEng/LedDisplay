# Two-Panel Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a horizontal two-panel (128×64) display layout alongside the existing 64×64 layout, selected by a single `LAYOUT_NAME` key. Architecture is data-driven so future panel configurations are single dict-entry additions.

**Architecture:** A new `layouts.py` module declares named layouts as dicts containing driver fields (width/height/tile_rows/serpentine) and a list of `(module_name, x, y, w, h)` quadrant rects. `code.py` resolves the layout at boot and iterates the quadrants instead of hardcoding them. Three quadrant modules (`logo`, `spotify`, `sun`) gain small adaptations to honor the size passed to their `build()`. `clock` and `weather` are unchanged because both planned layouts only use them at 32×32.

**Tech Stack:** CircuitPython 9+, `adafruit_matrixportal.matrix.Matrix`, `displayio`. Tests use pytest on the host against the pure data structures and small extracted helpers.

**Spec:** `docs/superpowers/specs/2026-05-22-two-panel-layout-design.md`

---

## File Map

### New
- `layouts.py` — module-level `LAYOUTS` dict + `DEFAULT_LAYOUT` string. Pure data; no imports beyond stdlib.
- `tests/test_layouts.py` — structural sanity tests (~5 tests).

### Modified
- `logo.py` — extract `_default_logo_path(width, height)` and call it from `build()` when `path=None`.
- `spotify.py` — extract `_marquee_window_for(width)`, store result in `_state["marquee_window"]` at build time, pass through to `marquee_window(...)` calls in `render`/`tick`.
- `sun.py` — store `width`/`height` in `_state` at build time.
- `code.py` — replace hardcoded `Matrix(...)` + quadrant builds with a layout dispatcher; change `BRIGHTNESS_DEFAULT` fallback `"3"` → `"0"`.
- `test_panel.py` — read `LAYOUT_NAME`, source `WIDTH`/`HEIGHT`/`TILE_ROWS`/`SERPENTINE` from the layout dict.

### Local-only (gitignored)
- `settings.toml` — append `LAYOUT_NAME = "128x64"`; change `BRIGHTNESS_DEFAULT` to `"0"`.

### Untouched
- `clock.py`, `weather.py`, `tz.py`, `brightness.py`, `wifi_setup.py`, `deploy.sh`, `install_libs.sh`, `pyproject.toml`, `tests/conftest.py`, all existing test files.

---

## Task 1: layouts.py + structural tests

**Files:**
- Create: `layouts.py`
- Create: `tests/test_layouts.py`

- [ ] **Step 1: Write failing tests**

`tests/test_layouts.py`:

```python
import layouts


def test_layouts_dict_exists_and_is_a_dict():
    assert isinstance(layouts.LAYOUTS, dict)
    assert len(layouts.LAYOUTS) >= 2


def test_default_layout_is_a_key():
    assert layouts.DEFAULT_LAYOUT in layouts.LAYOUTS


def test_default_layout_is_64x64():
    assert layouts.DEFAULT_LAYOUT == "64x64"


def test_each_layout_has_required_keys():
    required = {"width", "height", "tile_rows", "serpentine", "quadrants"}
    for name, layout in layouts.LAYOUTS.items():
        missing = required - set(layout.keys())
        assert not missing, "{} missing keys: {}".format(name, missing)


def test_each_quadrant_rect_fits_within_layout_dimensions():
    for name, layout in layouts.LAYOUTS.items():
        w, h = layout["width"], layout["height"]
        for q in layout["quadrants"]:
            mod, x, y, qw, qh = q
            assert x >= 0 and y >= 0, "{}: negative origin {}".format(name, q)
            assert x + qw <= w, "{}: {} runs past width {}".format(name, q, w)
            assert y + qh <= h, "{}: {} runs past height {}".format(name, q, h)


def test_each_quadrant_tuple_has_five_elements():
    for name, layout in layouts.LAYOUTS.items():
        for q in layout["quadrants"]:
            assert len(q) == 5, "{}: bad quadrant tuple {}".format(name, q)


def test_128x64_layout_contains_expected_modules():
    quads = layouts.LAYOUTS["128x64"]["quadrants"]
    names = [q[0] for q in quads]
    assert set(names) == {"logo", "clock", "weather", "sun", "spotify"}


def test_128x64_logo_is_64x64_hero_at_origin():
    quads = layouts.LAYOUTS["128x64"]["quadrants"]
    logo = next(q for q in quads if q[0] == "logo")
    assert logo == ("logo", 0, 0, 64, 64)


def test_64x64_layout_matches_today_behavior():
    layout = layouts.LAYOUTS["64x64"]
    assert layout["width"] == 64 and layout["height"] == 64
    assert layout["tile_rows"] == 1
    assert layout["serpentine"] is False
    names = [q[0] for q in layout["quadrants"]]
    assert set(names) == {"clock", "weather", "sun", "logo", "spotify"}
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `python3 -m pytest tests/test_layouts.py -v`
Expected: 9 failures with `ModuleNotFoundError: No module named 'layouts'`.

- [ ] **Step 3: Create `layouts.py`**

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

- [ ] **Step 4: Run tests — verify all pass**

Run: `python3 -m pytest tests/test_layouts.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add layouts.py tests/test_layouts.py
git commit -m "Add layouts.py with 64x64 and 128x64 entries"
```

---

## Task 2: logo.py — _default_logo_path (TDD)

**Files:**
- Modify: `logo.py`
- Modify: `tests/test_spotify.py` (add a new test file is also fine; piggybacking to keep file count down) — actually create `tests/test_logo.py`

**Note:** `tests/test_logo.py` doesn't exist yet — create it.

- [ ] **Step 1: Write failing tests**

`tests/test_logo.py`:

```python
from logo import _default_logo_path


def test_returns_32_for_32x32():
    assert _default_logo_path(32, 32) == "/images/arc_raiders_logo/logo32.bmp"


def test_returns_64_for_64x64():
    assert _default_logo_path(64, 64) == "/images/arc_raiders_logo/logo64.bmp"


def test_returns_64_when_either_dim_is_64():
    assert _default_logo_path(64, 32) == "/images/arc_raiders_logo/logo64.bmp"
    assert _default_logo_path(32, 64) == "/images/arc_raiders_logo/logo64.bmp"


def test_returns_64_for_larger_sizes():
    assert _default_logo_path(96, 96) == "/images/arc_raiders_logo/logo64.bmp"


def test_returns_32_for_smaller_sizes():
    assert _default_logo_path(16, 16) == "/images/arc_raiders_logo/logo32.bmp"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `python3 -m pytest tests/test_logo.py -v`
Expected: 5 failures with `ImportError: cannot import name '_default_logo_path' from 'logo'`.

- [ ] **Step 3: Read current `logo.py` to understand the structure**

Run: `cat logo.py`

Confirm `build()` signature is `def build(x, y, width, height, path="/images/arc_raiders_logo/logo32.bmp")`.

- [ ] **Step 4: Modify `logo.py`**

At the top of the file, after the module docstring, add the helper:

```python
def _default_logo_path(width, height):
    if max(width, height) >= 64:
        return "/images/arc_raiders_logo/logo64.bmp"
    return "/images/arc_raiders_logo/logo32.bmp"
```

Then change the `build()` signature and its first line:

```python
# from this:
def build(x, y, width, height, path="/images/arc_raiders_logo/logo32.bmp"):
    """Load the logo BMP and return a positioned displayio.Group.
    ...

# to this:
def build(x, y, width, height, path=None):
    """Load the logo BMP and return a positioned displayio.Group.

    If `path` is None, picks `logo32.bmp` or `logo64.bmp` based on the
    largest of width/height (the BMP needs to fit, not be exact).
    ...
    """
    if path is None:
        path = _default_logo_path(width, height)
    # rest of function unchanged
```

The function body below the new `if path is None:` block stays identical.

- [ ] **Step 5: Run tests — verify they pass**

Run: `python3 -m pytest tests/test_logo.py -v`
Expected: 5 passed.

- [ ] **Step 6: Run full suite — verify no regression**

Run: `python3 -m pytest`
Expected: 73 passed (68 existing + 5 new).

- [ ] **Step 7: Commit**

```bash
git add logo.py tests/test_logo.py
git commit -m "Auto-pick logo BMP based on quadrant size"
```

---

## Task 3: spotify.py — _marquee_window_for + dynamic window (TDD)

**Files:**
- Modify: `spotify.py`
- Modify: `tests/test_spotify.py`

- [ ] **Step 1: Append failing test for `_marquee_window_for`**

Append to `tests/test_spotify.py`:

```python
from spotify import _marquee_window_for


def test_marquee_window_for_32px_returns_6():
    assert _marquee_window_for(32) == 6


def test_marquee_window_for_64px_returns_12():
    assert _marquee_window_for(64) == 12


def test_marquee_window_for_very_small_widths_returns_at_least_1():
    assert _marquee_window_for(4) == 1
    assert _marquee_window_for(0) == 1


def test_marquee_window_for_128px_returns_25():
    # 128 // 5 = 25
    assert _marquee_window_for(128) == 25
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `python3 -m pytest tests/test_spotify.py -v`
Expected: 4 failures (`ImportError: cannot import name '_marquee_window_for' from 'spotify'`).

- [ ] **Step 3: Add the helper to `spotify.py`**

Append near the top of `spotify.py`, after `parse_now_playing` and before the display/state code:

```python
def _marquee_window_for(width):
    """Pick a marquee window size in characters for a quadrant of the given pixel width.

    The 5x8 font is 5 px wide per character, so width // 5 maximizes legible
    text while leaving the loop separator visible. Clamped to a minimum of 1
    so degenerate widths don't produce a zero-length window.
    """
    return max(1, width // 5)
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `python3 -m pytest tests/test_spotify.py -v`
Expected: all spotify tests pass (4 new ones included).

- [ ] **Step 5: Wire the helper into `build` and the marquee calls**

In `spotify.py`'s `build()`, after `_state["track_label"] = track_label` and `_state["artist_label"] = artist_label`, add:

```python
    _state["width"] = width
    _state["marquee_window"] = _marquee_window_for(width)
```

In `spotify.py`'s `render()`, find:

```python
    _state["track_label"].text = marquee_window(track, _state["track_offset"])
    _state["artist_label"].text = marquee_window(artist, _state["artist_offset"])
```

and replace with:

```python
    _state["track_label"].text = marquee_window(
        track, _state["track_offset"], window=_state["marquee_window"]
    )
    _state["artist_label"].text = marquee_window(
        artist, _state["artist_offset"], window=_state["marquee_window"]
    )
```

In `spotify.py`'s `tick()`, find:

```python
    _state["track_label"].text = marquee_window(
        _state["track_text"], _state["track_offset"]
    )
    _state["artist_label"].text = marquee_window(
        _state["artist_text"], _state["artist_offset"]
    )
```

and replace with:

```python
    _state["track_label"].text = marquee_window(
        _state["track_text"], _state["track_offset"], window=_state["marquee_window"]
    )
    _state["artist_label"].text = marquee_window(
        _state["artist_text"], _state["artist_offset"], window=_state["marquee_window"]
    )
```

Also update the `_state` dict declaration (top of the file) to include the new keys with safe defaults:

Find:

```python
_state = {
    ...
    "last_factor": 1.0,
}
```

Add two new entries at the bottom of the dict literal (before the closing `}`):

```python
    "width": 0,
    "marquee_window": 6,
```

(`marquee_window` defaults to 6 so any code that calls `render()`/`tick()` before `build()` ever runs — which shouldn't happen but is defensive — gets the existing window size.)

- [ ] **Step 6: Run full suite — verify no regression**

Run: `python3 -m pytest`
Expected: 77 passed (73 + 4 new).

- [ ] **Step 7: Commit**

```bash
git add spotify.py tests/test_spotify.py
git commit -m "Derive spotify marquee window from quadrant width"
```

---

## Task 4: sun.py — stash dimensions

**Files:**
- Modify: `sun.py`

- [ ] **Step 1: Read current `sun.py` `build()` to locate the insertion point**

Run: `grep -n "def build" sun.py`

The current `build()` ends with `return group`.

- [ ] **Step 2: Add width/height to `_state` at build time**

In `sun.py`, find the existing `_state` dict near the top:

```python
_state = {
    "group": None,
    "header": None,
    "time_label": None,
    "last_factor": 1.0,
    "font": None,
}
```

Add two new keys at the end (before the closing brace):

```python
    "width": 0,
    "height": 0,
```

In `build()`, after `_state["time_label"] = time_label` and before `return group`, add:

```python
    _state["width"] = width
    _state["height"] = height
```

- [ ] **Step 3: Run pytest — verify no regression**

Run: `python3 -m pytest`
Expected: 77 passed (no change in count; sun.py isn't unit-tested).

- [ ] **Step 4: Commit**

```bash
git add sun.py
git commit -m "Stash quadrant dimensions in sun._state for future use"
```

---

## Task 5: code.py refactor

**Files:**
- Modify: `code.py`

- [ ] **Step 1: Add layouts import**

In `code.py`, near the other module imports (after `import spotify`), add:

```python
import layouts
```

- [ ] **Step 2: Replace the hardcoded layout block**

In `code.py`, find:

```python
MATRIX_WIDTH = 64
MATRIX_HEIGHT = 64
BIT_DEPTH = 4
```

and replace with:

```python
BIT_DEPTH = 4
```

(Drop `MATRIX_WIDTH` and `MATRIX_HEIGHT` — they're replaced by the layout dict.)

Then find:

```python
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
```

and replace with:

```python
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
```

- [ ] **Step 3: Change BRIGHTNESS_DEFAULT fallback**

Find:

```python
_BRIGHTNESS_DEFAULT = int(os.getenv("BRIGHTNESS_DEFAULT", "3"))
```

Replace with:

```python
_BRIGHTNESS_DEFAULT = int(os.getenv("BRIGHTNESS_DEFAULT", "0"))
```

- [ ] **Step 4: Run pytest — verify no host-side regression**

Run: `python3 -m pytest`
Expected: 77 passed. `code.py` isn't imported by the test suite; this is a sanity check on the other modules.

- [ ] **Step 5: Verify the rest of `code.py` is intact by reading it end-to-end**

Open `code.py` and confirm:
- `import layouts` is present at the top
- `_MODULES` dict exists with five entries
- `_layout_name` is resolved with fallback warning
- `Matrix(...)` uses `_layout["width"]`, `_layout["height"]`, `_layout["tile_rows"]`, `_layout["serpentine"]`
- Quadrant build loop iterates `_layout["quadrants"]` and dedups into `_ordered_quadrants`
- `QUADRANTS = tuple(_ordered_quadrants)` is in place
- `_BRIGHTNESS_DEFAULT = int(os.getenv("BRIGHTNESS_DEFAULT", "0"))` — the fallback is `"0"` not `"3"`
- All helpers (`_now_minutes`, `_connect_wifi`, `_initial_ntp_sync`, `_initial_weather`, `_apply_spotify_swap`, `_initial_spotify`) are present and unchanged
- Boot sequence (`clock.set_status("boot")` through `_initial_spotify(pool)`) is present and unchanged
- Main loop is unchanged (250 ms marquee, 1 s clock tick, 15 min weather, 10 s spotify, 1 hr NTP, 50 ms sleep)

- [ ] **Step 6: Commit**

```bash
git add code.py
git commit -m "Refactor code.py to use data-driven layouts"
```

---

## Task 6: test_panel.py refactor

**Files:**
- Modify: `test_panel.py`

- [ ] **Step 1: Read current `test_panel.py` to locate the constants**

Run: `head -15 test_panel.py`

The file currently begins with imports and then `WIDTH = 64`, `HEIGHT = 64`, etc.

- [ ] **Step 2: Replace the constants block**

In `test_panel.py`, find:

```python
# === EDIT THESE TO TEST DIFFERENT CONFIGS ===
WIDTH = 64
HEIGHT = 64
BIT_DEPTH = 4
TILE_ROWS = 1
SERPENTINE = True
FORCE_4_ADDR_PINS = False
# ============================================
```

Replace with:

```python
import os
import layouts

# Driver fields are sourced from layouts.py using LAYOUT_NAME from settings.toml.
# Edit a layout entry in layouts.py to change defaults; override here for ad-hoc
# diagnostics by reassigning WIDTH / HEIGHT / TILE_ROWS / SERPENTINE below.
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

The rest of `test_panel.py` (corner labels, centered config text, `Matrix(...)` init, `while True: pass`) is unchanged. The center text labels (`"{}x{} t={}"` and `"s={} a={}"`) already read the dynamic constants.

- [ ] **Step 3: Syntax-check**

Run: `python3 -c "import ast; ast.parse(open('test_panel.py').read())"`
Expected: no output, exit 0. (The file uses CircuitPython-only imports that won't import on the host, but `ast.parse` doesn't execute imports.)

- [ ] **Step 4: Run pytest — verify no regression**

Run: `python3 -m pytest`
Expected: 77 passed (test_panel.py isn't imported by tests).

- [ ] **Step 5: Commit**

```bash
git add test_panel.py
git commit -m "Source test_panel dimensions from layouts.py"
```

---

## Task 7: settings.toml updates (local only)

**Files:**
- Modify: `settings.toml` (gitignored — do NOT `git add`)

- [ ] **Step 1: Update `settings.toml`**

In `settings.toml`, change `BRIGHTNESS_DEFAULT` value and append `LAYOUT_NAME`.

Find:

```toml
BRIGHTNESS_DEFAULT = "3"
```

Replace with:

```toml
BRIGHTNESS_DEFAULT = "0"
LAYOUT_NAME = "128x64"
```

Leave all other lines unchanged.

- [ ] **Step 2: Verify the file is still gitignored**

Run: `git status`
Expected: no `settings.toml` entry in either staged or unstaged sections.

- [ ] **Step 3: No commit**

`settings.toml` is gitignored. This task changes only the local file.

---

## Task 8: On-device smoke test

These steps run on the MatrixPortal S3. Manual.

**Setup:**

- [ ] **Step 1: Deploy with new settings**

Run from project root:

```bash
./deploy.sh --with-settings
```

The serial console (`tio /dev/ttyACM0` or `screen /dev/ttyACM0 115200`) should print, near the top of the output:

```
layout: 128x64 (128x64, 5 quadrants)
```

**Chain validation (run before relying on the dashboard):**

- [ ] **Step 2: Push test_panel.py and verify corner markers**

```bash
./deploy.sh --test
```

Expect to see `TL` (red) at the absolute top-left of the 128×64 array, `TR` (green) at the absolute top-right, `BL` (blue) at the bottom-left, `BR` (yellow) at the bottom-right. Center text: `128x64 t=1` / `s=F a=auto`.

If any corner is in the wrong place or text appears mirrored, the chain wiring or `serpentine`/`tile_rows` are wrong. Fix in `layouts.py` (`128x64` entry) or in the wiring, then redeploy.

- [ ] **Step 3: Return to the dashboard**

```bash
./deploy.sh
```

The dashboard reboots.

**Dashboard checks:**

- [ ] **Step 4: Logo hero**

Visually confirm `logo64.bmp` renders in the left 64×64 hero slot (sharp, not stretched).

- [ ] **Step 5: Clock**

Upper-right area shows time + zone abbreviation + date at the (64, 0, 32, 32) position.

- [ ] **Step 6: Weather**

Upper-right-right area shows temperature + condition icon at (96, 0, 32, 32).

- [ ] **Step 7: Spotify wide marquee**

Start a track on the configured Spotify account. Within ~10 s the bottom-right swaps to the Spotify display. Pick a track with a long title; confirm the marquee shows roughly 12 characters at a time (twice today's width).

- [ ] **Step 8: Sun reappearance**

Stop playback. Within ~10 s the sun-next-event reappears in the wide 64×32 slot.

- [ ] **Step 9: Brightness uniformity**

Press UP/DOWN. All five quadrants — across both panels — dim/brighten in sync. Brightness now starts at the lowest level on cold boot (because `BRIGHTNESS_DEFAULT = "0"`).

- [ ] **Step 10: Backward compatibility**

Set `LAYOUT_NAME = "64x64"` in `settings.toml`, redeploy with `--with-settings`. Confirm the left panel shows the original 4-quadrant layout and the right panel goes dark. Restore `LAYOUT_NAME = "128x64"` afterward.

- [ ] **Step 11: Unknown layout name**

Set `LAYOUT_NAME = "typo"` in `settings.toml`, redeploy. Serial should print:

```
layout: unknown LAYOUT_NAME typo — falling back to 64x64
layout: 64x64 (64x64, 5 quadrants)
```

Dashboard runs the 64×64 layout on the first panel; second panel goes dark. Restore `LAYOUT_NAME = "128x64"`.

- [ ] **Step 12: Final commit (if any tweaks were made during smoke testing)**

```bash
git status
# If any colors or positions were tweaked to taste:
git add -p
git commit -m "Smoke-test adjustments"
```

---

## Self-review notes

Cross-checked the plan against `docs/superpowers/specs/2026-05-22-two-panel-layout-design.md`:

- **Layout — 128×64** (spec §Layout): Task 1 declares the entry; Task 5 wires `code.py` to iterate quadrants; Task 6 propagates dimensions into `test_panel.py`.
- **File map** (spec §File map): every new/modified file is covered by exactly one task.
- **`layouts.py`** (spec §`layouts.py`): Task 1, with 9 structural tests.
- **Per-module changes** (spec §Per-module changes): Task 2 (logo path), Task 3 (spotify marquee window), Task 4 (sun dimensions).
- **`code.py` refactor** (spec §`code.py` refactor): Task 5, replacing the hardcoded block plus the BRIGHTNESS_DEFAULT change.
- **Settings** (spec §Settings): Task 7 — local-only edit, no commit.
- **`test_panel.py` updates** (spec §`test_panel.py` updates): Task 6.
- **Error handling** (spec §Error handling): exercised by Task 8 steps 11 (unknown layout) and 10 (backward compat).
- **Testing** (spec §Testing): host-side covered by Tasks 1–3 (9 + 5 + 4 = 18 new tests, raising the suite to 86). Smoke checklist is Task 8.

No type/name drift on re-read — `_default_logo_path`, `_marquee_window_for`, `_MODULES`, `_layout`, `_ordered_quadrants`, `QUADRANTS`, `LAYOUTS`, `DEFAULT_LAYOUT` are used consistently across all tasks.

One small clarification baked into the plan: spotify's `_state` dict gets new keys `width` and `marquee_window` with safe defaults at the dict declaration site, so any defensive code path that reads them before `build()` runs gets sensible values.
