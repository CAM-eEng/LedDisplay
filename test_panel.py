import board
import displayio
import terminalio
from adafruit_matrixportal.matrix import Matrix
from adafruit_display_text.label import Label
from adafruit_display_shapes.rect import Rect

# === EDIT THESE TO TEST DIFFERENT CONFIGS ===
WIDTH = 64
HEIGHT = 64
BIT_DEPTH = 4
TILE_ROWS = 1
SERPENTINE = True
FORCE_4_ADDR_PINS = False
# ============================================

addr_pins = None
if FORCE_4_ADDR_PINS:
    addr_pins = [
        board.MTX_ADDRA,
        board.MTX_ADDRB,
        board.MTX_ADDRC,
        board.MTX_ADDRD,
    ]

matrix = Matrix(
    width=WIDTH,
    height=HEIGHT,
    bit_depth=BIT_DEPTH,
    tile_rows=TILE_ROWS,
    serpentine=SERPENTINE,
    alt_addr_pins=addr_pins,
)
display = matrix.display

group = displayio.Group()

EDGE = 0x222222
group.append(Rect(0, 0, WIDTH, 1, fill=EDGE))
group.append(Rect(0, HEIGHT - 1, WIDTH, 1, fill=EDGE))
group.append(Rect(0, 0, 1, HEIGHT, fill=EDGE))
group.append(Rect(WIDTH - 1, 0, 1, HEIGHT, fill=EDGE))

CHAR_WIDTH = 6


def add_label(text, x, y, color):
    lab = Label(terminalio.FONT, text=text, color=color)
    lab.x = x
    lab.y = y
    group.append(lab)


add_label("TL", 4, 6, 0xFF0000)
add_label("TR", WIDTH - 4 - len("TR") * CHAR_WIDTH, 6, 0x00FF00)
add_label("BL", 4, HEIGHT - 6, 0x0000FF)
add_label("BR", WIDTH - 4 - len("BR") * CHAR_WIDTH, HEIGHT - 6, 0xFFFF00)

addrs = "4" if FORCE_4_ADDR_PINS else "auto"
line1 = "{}x{} t={}".format(WIDTH, HEIGHT, TILE_ROWS)
line2 = "s={} a={}".format("T" if SERPENTINE else "F", addrs)
add_label(line1, (WIDTH - len(line1) * CHAR_WIDTH) // 2, HEIGHT // 2 - 4, 0xFFFFFF)
add_label(line2, (WIDTH - len(line2) * CHAR_WIDTH) // 2, HEIGHT // 2 + 4, 0xFFFFFF)

display.root_group = group

while True:
    pass
