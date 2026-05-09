import time
import displayio
import terminalio
from adafruit_matrixportal.matrix import Matrix
from adafruit_display_text.label import Label

import wifi_setup
import clock

MATRIX_WIDTH = 64
MATRIX_HEIGHT = 64
BIT_DEPTH = 4
CHAR_WIDTH = 6
TILE_ROWS = 2
RESYNC_SECONDS = 3600

matrix = Matrix(
    width=MATRIX_WIDTH,
    height=MATRIX_HEIGHT,
    bit_depth=BIT_DEPTH,
    tile_rows=TILE_ROWS,
    serpentine=False,
)
display = matrix.display

group = displayio.Group()

time_label = Label(terminalio.FONT, text="booting...", color=0xFFAA00)
time_label.x = 4
time_label.y = MATRIX_HEIGHT // 2
group.append(time_label)

date_label = Label(terminalio.FONT, text="", color=0x4488FF)
date_label.y = MATRIX_HEIGHT - 6
group.append(date_label)

display.root_group = group


def center_x(text):
    return (MATRIX_WIDTH - len(text) * CHAR_WIDTH) // 2


try:
    pool = wifi_setup.connect()
    clock.sync(pool)
    time_label.color = 0x00CCFF
except Exception as exc:
    time_label.text = "err"
    time_label.color = 0xFF2244
    print("Boot failure:", exc)
    while True:
        pass

time_label.y = 22
date_label.y = 44

last_sync = time.monotonic()
blink_on = True

while True:
    if time.monotonic() - last_sync > RESYNC_SECONDS:
        try:
            clock.sync(pool)
            last_sync = time.monotonic()
        except Exception as exc:
            print("Resync failed:", exc)

    time_text = clock.time_string(blink_on=blink_on)
    date_text = clock.date_string()

    time_label.text = time_text
    time_label.x = center_x(time_text)
    date_label.text = date_text
    date_label.x = center_x(date_text)

    blink_on = not blink_on
    time.sleep(1)
