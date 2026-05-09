#!/usr/bin/env bash
set -euo pipefail

CIRCUITPY="${CIRCUITPY:-/media/dexter/CIRCUITPY}"

LIBS=(
  adafruit_matrixportal
  adafruit_portalbase
  adafruit_display_text
  adafruit_bitmap_font
  adafruit_display_shapes
  adafruit_minimqtt
  adafruit_io
  adafruit_esp32spi
  adafruit_requests.mpy
  adafruit_connection_manager.mpy
  adafruit_ntp.mpy
  adafruit_fakerequests.mpy
)

if [[ ! -d "$CIRCUITPY" ]]; then
  echo "CIRCUITPY drive not found at $CIRCUITPY"
  echo "Set CIRCUITPY=/path/to/drive if it's mounted elsewhere."
  exit 1
fi

if [[ ! -f "$CIRCUITPY/boot_out.txt" ]]; then
  echo "boot_out.txt missing — is this really a CIRCUITPY drive?"
  exit 1
fi

CP_MAJOR=$(grep -oE 'CircuitPython [0-9]+' "$CIRCUITPY/boot_out.txt" | grep -oE '[0-9]+$' | head -1)
if [[ -z "$CP_MAJOR" ]]; then
  echo "Could not parse CircuitPython major version from boot_out.txt"
  exit 1
fi
echo "Detected CircuitPython ${CP_MAJOR}.x"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

echo "Looking up latest bundle release..."
ASSET_URL=$(curl -fsSL https://api.github.com/repos/adafruit/Adafruit_CircuitPython_Bundle/releases/latest \
  | grep -oE "https://[^\"]+adafruit-circuitpython-bundle-${CP_MAJOR}\.x-mpy-[^\"]+\.zip" \
  | head -1)

if [[ -z "$ASSET_URL" ]]; then
  echo "No ${CP_MAJOR}.x bundle found in latest release."
  exit 1
fi

echo "Downloading $(basename "$ASSET_URL")"
curl -fL --progress-bar -o "$WORK/bundle.zip" "$ASSET_URL"
unzip -q "$WORK/bundle.zip" -d "$WORK"

BUNDLE_LIB=$(find "$WORK" -mindepth 2 -maxdepth 3 -type d -name lib | head -1)
if [[ -z "$BUNDLE_LIB" ]]; then
  echo "Could not locate lib/ inside bundle archive."
  exit 1
fi

mkdir -p "$CIRCUITPY/lib"
for lib in "${LIBS[@]}"; do
  src="$BUNDLE_LIB/$lib"
  dst="$CIRCUITPY/lib/$lib"
  if [[ -e "$src" ]]; then
    rm -rf "$dst"
    cp -r "$src" "$dst"
    echo "  + $lib"
  else
    echo "  - $lib (not in bundle, skipped)"
  fi
done

echo "Syncing..."
sync
echo "Done. Safe to eject CIRCUITPY."
