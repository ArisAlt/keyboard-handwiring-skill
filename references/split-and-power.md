# Split links, connections and batteries

## Wired split (QMK / Vial)

**Two controllers, one firmware, one pin list.** Both halves run the same firmware with the same `matrix_pins` (`MATRIX_ROW_PINS` / `MATRIX_COL_PINS`), so "GP0" on the left controller and "GP0" on the right controller are two different physical pins. Only add `split.matrix_pins.right` (`MATRIX_ROW_PINS_RIGHT` / `MATRIX_COL_PINS_RIGHT`) if the right half is wired to *different* pins (keebio/iris rev8 does this). QMK reads the left half's rows first, then the right's: `MATRIX_ROWS` = 2 × rows per half, and right-half rows are `rows_per_half + r`.

**Each half's wires go to its own controller.** Rows and columns of the left half run only to the left controller, right to right. Nothing crosses between halves except the link cable. In a wiring diagram, draw a controller per half with every row/column home-run to it.

**Mirrored or same direction: a wiring choice the matrix must match.** QMK doesn't force either; both appear in QMK's own keyboards:

| Convention | Right half col 0 | QMK examples |
|---|---|---|
| **Mirrored** (mirror-image halves) | outer edge | `lily58/rev1`, `sofle/rev1`, `keebio/iris/rev8`, Sofle Pico |
| **Same direction** | inner edge (leftmost) | `handwired/dactyl_manuform/5x6`, `ferris/sweep` |
| **Flipped in firmware** | inner edge (leftmost), but wired mirror-image | right controller gets a reversed `split.matrix_pins.right` cols list (`NO_PIN`/null padded), like `keebio/iris/rev8` (which uses fully different right pins) |

Mirrored is the common choice for mirror-image handwired halves: each column pin then goes to the matching column on both halves (GP10 = outer column on both). It's `matrix_tool.py route --split`'s default (`--right-wiring mirrored|same|flipped`).

**Uneven halves are allowed.** Most splits are symmetric (Lily58, Corne, Sofle, Kyria), but QMK only needs the same matrix size and pin count on both controllers: Keebio Quefrency has 30 + 37 keys, Sinc 38 + 44. The smaller half simply leaves some matrix positions (and column pins) unused, or uses its own `split.matrix_pins.right` padded with `NO_PIN`.

**Declare the split explicitly in firmware** (keyboard.json shown; config.h/rules.mk equivalents in `qmk-vial.md`):
```json
"split": {
  "enabled": true,
  "transport": {"protocol": "serial"},
  "serial": {"driver": "vendor", "pin": "GP28"},
  "matrix_pins": {"right": {"rows": ["GP0","GP1","GP2","GP3","GP4"], "cols": ["GP10","GP9","GP8","GP7","GP6","GP5"]}}
}
```
plus handedness in config.h: `#define MASTER_LEFT` (USB on the left), or `#define EE_HANDS` and flash each half once with `:uf2-split-left` / `:uf2-split-right`, or a hand pin (`split.handedness.pin`). When validating an existing build, make sure *every* row of the right half follows one convention. A single thumb key wired the other way is a classic mistake.

**Number columns by physical order.** A column's index should follow its position (outer → inner), not the order a router happened to create it in.

**Cable:** TRRS/TRS (audio jack) is the norm; USB-C-to-USB-C between halves works but looks like a USB port and invites plugging a computer into it.

| Link | Conductors | Pins per half | Notes |
|---|---|---|---|
| Half-duplex serial | VCC, GND, DATA → TRS is enough | 1 | Default. AVR: soft serial on D0–D3 (`split.serial.pin`). RP2040: `driver: vendor`, any GPIO. |
| Full-duplex serial | VCC, GND, TX, RX → TRRS | 2 | `SERIAL_USART_FULL_DUPLEX`, `SERIAL_USART_TX_PIN` / `RX_PIN`, often `SERIAL_USART_PIN_SWAP`; RP2040 `SERIAL_DRIVER = vendor`. Example: Sofle Pico (TX GP16, RX GP17). |
| I2C | VCC, GND, SDA, SCL → TRRS | 2 | Needs ~4.7 kΩ pull-ups on SDA and SCL (one set, on one half). Uses the I2C pins, so no OLED on the same bus without care. |

Suggested half-duplex link pins (kept out of the matrix and counted in the pin budget): RP2040-Plus/Pico **GP28**, RP2040-Zero/Tiny **GP29**, Pro Micro **D2**.

Rules:
- **Same link pin on both halves**, wired jack sleeve/ring/tip identically on both sides (mirror the jack, not the wiring).
- **Never plug or unplug the TRRS cable while USB is connected.** Sliding the plug briefly shorts VCC to data/GND and can kill a pin or the controller.
- RP2040 halves: carry 5 V (VSYS/5V pin) over the cable so the far half's regulator powers it; the data line is 3.3 V. Don't link a 5 V Pro Micro half to a 3.3 V RP2040 half.
- Handedness: decide `EE_HANDS` (flash each half with `uf2-split-left` / `uf2-split-right`), `MASTER_LEFT`, or a hand pin (`split.handedness.pin`) before flashing (see `qmk-vial.md`). Wrong handedness = right half types left-half keys.

## Wireless (ZMK, nRF52840)

- No link wire. Each half has its own controller, battery and power switch.
- Central half (left by default) drains noticeably faster. A dongle (third controller on USB as central) makes both halves peripherals.

## Batteries

Use a **single-cell 3.7 V LiPo with a protection circuit (PCM)**. Typical keyboard cells: 100–1000 mAh, flat pouch (e.g. 301230 ≈ 110 mAh, 502030 ≈ 250 mAh).

Wiring on nice!nano-style boards:
- Battery **+ → power switch → B+**, battery **− → B−**. The switch must be on the battery side; on most such boards the battery only charges while the switch is **on**.
- **Check connector polarity with a meter.** JST-PH 2.0 batteries from different sellers have red/black swapped; reversed polarity can destroy the charger.
- Charge rate: nice!nano v2 charges at ~100 mA, so cells ≥ 100 mAh are safe (≤ 1C). Clones may charge faster — check the seller's spec before using a tiny cell.

Battery life is dominated by what's always on:
| Load | Effect |
|---|---|
| ZMK idle, no lights | microamps to tens of µA → weeks to months |
| OLED/nice!view | small but constant; nice!view is low-power, OLEDs are not |
| Per-key RGB / underglow | tens of mA → days or hours. Cut it with ext-power (P0.13) when idle |
| Central half | extra radio work; expect it to die first |

Rough estimate: `hours ≈ capacity_mAh / average_mA`. Measure average current with a USB/inline meter or a power profiler if the user needs real numbers.

Safety notes worth giving every time:
- Insulate the cell and leads (Kapton); keep it away from screw bosses, switch pins and anything that can puncture or crush it.
- Don't solder directly onto cell tabs; use the leads.
- Disconnect the battery while soldering the controller.
- A puffy/swollen cell goes out of service — don't charge it.

## Power-only connection checklist
- USB powers whichever half it's plugged into; on wired splits it also powers the other half through the link VCC.
- Never connect two USB cables to both halves of a wired split at the same time unless the firmware/board is designed for it.
- LEDs (WS2812) want 5 V power and a data signal; RP2040's 3.3 V data usually works at short distances, use a level shifter if the first LED misbehaves.

## Per-key RGB on USB power (SK6812MINI / WS2812)

No extra supply is needed if brightness is capped:
- Each SK6812MINI draws up to **~60 mA at full white** (20 mA per colour) and **~1 mA when dark**. 70 LEDs ≈ 70 mA idle, ≈ 4.2 A full white.
- A normal USB port gives **500 mA** (many USB-C ports give more, but don't count on it). Subtract ~30–50 mA for the controller.
- Cap it: `RGB_MATRIX_MAXIMUM_BRIGHTNESS` (or `rgb_matrix.max_brightness` in keyboard.json); for ~70 LEDs ≈ 25 for full white, ~60–80 for typical single-colour effects. Sofle Pico (58 LEDs) uses 127 and relies on dim effects.
- Take LED **+ from VBUS / 5V** (RP2040-Plus/Pico: VBUS = header pin 40; GND e.g. pin 38), not 3V3.
- Put **100–470 µF** across + and − at the first LED; on long chains, feed + and − into the far end too.
- 3.3 V data into LEDs powered at 5 V is out of spec (V_IH ≈ 3.5 V) but usually works over a short first wire; if the first LED flickers, add a 74AHCT125 level shifter.
- Splits: one chain per half, each from its own controller's `ws2812` pin; tell QMK the count per half with `rgb_matrix.split_count` (e.g. `[29, 29]`).
