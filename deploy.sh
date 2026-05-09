#!/usr/bin/env bash
set -euo pipefail

CIRCUITPY="${CIRCUITPY:-/media/dexter/CIRCUITPY}"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

MODE="clock"
WITH_SETTINGS="no"

for arg in "$@"; do
  case "$arg" in
    --test) MODE="test" ;;
    --with-settings) WITH_SETTINGS="yes" ;;
    *) echo "Unknown flag: $arg"; exit 1 ;;
  esac
done

if [[ ! -d "$CIRCUITPY" ]]; then
  echo "CIRCUITPY drive not found at $CIRCUITPY"
  echo "Set CIRCUITPY=/path/to/drive if it's mounted elsewhere."
  exit 1
fi

if [[ ! -f "$CIRCUITPY/boot_out.txt" ]]; then
  echo "boot_out.txt missing — is this really a CIRCUITPY drive?"
  exit 1
fi

if [[ "$MODE" == "test" ]]; then
  cp "$SRC_DIR/test_panel.py" "$CIRCUITPY/code.py"
  echo "  + test_panel.py → code.py"
else
  for f in code.py clock.py wifi_setup.py; do
    src="$SRC_DIR/$f"
    if [[ ! -f "$src" ]]; then
      echo "  - $f missing in project, skipped"
      continue
    fi
    cp "$src" "$CIRCUITPY/$f"
    echo "  + $f"
  done
fi

if [[ "$WITH_SETTINGS" == "yes" ]]; then
  cp "$SRC_DIR/settings.toml" "$CIRCUITPY/settings.toml"
  echo "  + settings.toml (overwritten — re-add your WiFi creds!)"
else
  echo "  ~ settings.toml left alone (pass --with-settings to overwrite)"
fi

sync
echo "Deployed. Board will auto-reload code.py."
