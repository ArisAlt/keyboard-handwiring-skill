# QMK and Vial

Check the user's QMK version when something doesn't build — QMK moves fast. Current QMK expects a data-driven `keyboard.json` per buildable keyboard (older trees used `info.json` + `rules.mk`; both still appear in the wild).

## Folder layout

```
keyboards/handwired/<name>/
├── keyboard.json          # hardware: MCU, pins, matrix, layout
├── config.h               # optional: things keyboard.json can't express
└── keymaps/
    ├── default/keymap.c
    └── vial/              # only for Vial (vial-qmk fork)
        ├── keymap.c
        ├── rules.mk       # VIA_ENABLE = yes / VIAL_ENABLE = yes
        ├── config.h       # VIAL_KEYBOARD_UID, unlock combo
        └── vial.json
```

## keyboard.json essentials

```json
{
  "keyboard_name": "my_handwired",
  "manufacturer": "me",
  "maintainer": "me",
  "processor": "RP2040",
  "bootloader": "rp2040",
  "usb": {"vid": "0xFEED", "pid": "0x0001", "device_version": "1.0.0"},
  "diode_direction": "COL2ROW",
  "matrix_pins": {"rows": ["GP0","GP1","GP2","GP3"], "cols": ["GP4","GP5","GP6","GP7","GP8","GP9"]},
  "features": {"bootmagic": true, "extrakey": true, "mousekey": true},
  "layouts": {"LAYOUT": {"layout": [{"matrix": [0, 0], "x": 0, "y": 0}]}}
}
```

- `layout` array order = argument order of the `LAYOUT(...)` macro in `keymap.c`. Each entry's `matrix` is `[row, col]`; `x/y/w/h/r/rx/ry` follow KLE semantics.
- Pin names: RP2040 `GPn`, AVR `D4`/`F6`… Pin order in `rows`/`cols` = matrix index order.
- Use a non-zero, unique-ish `pid`; `0xFEED` vid is the QMK hobby convention.
- Don't define the same thing in both `keyboard.json` and `config.h`/`rules.mk` (e.g. pins, MCU) — QMK lint complains and the build may pick the wrong one.

## Split keyboards

```json
"split": {
  "enabled": true,
  "transport": {"protocol": "serial"},
  "serial": {"driver": "vendor", "pin": "GP28"},
  "matrix_pins": {"right": {"rows": ["..."], "cols": ["..."]}}
}
```
config.h equivalents: `SPLIT_KEYBOARD = yes` (rules.mk), `SOFT_SERIAL_PIN` / `SERIAL_USART_TX_PIN`, `MATRIX_ROW_PINS_RIGHT` / `MATRIX_COL_PINS_RIGHT`, `MASTER_LEFT` / `EE_HANDS`. Writing `split.matrix_pins.right` even when it equals the left list is harmless and makes each side's wiring explicit.

- `matrix_pins.rows` lists **one half's** rows; QMK makes `MATRIX_ROWS` = 2 × that. In `layout`, right-half keys use rows `rows_per_half + r`.
- `split.matrix_pins.right` is required when the right half uses different pins (or a reversed order); both halves must have the same pin count — pad with `NO_PIN` (`null` in JSON).
- Serial driver: AVR → `bitbang` (soft serial on D0–D3); RP2040 → `vendor` (PIO; single-wire half duplex on any GPIO). Full duplex needs TX+RX pins and a 4-conductor cable.
- Handedness, highest priority first: `SPLIT_HAND_PIN`, `SPLIT_HAND_MATRIX_GRID`, `EE_HANDS` (flash each half with `:uf2-split-left` / `:uf2-split-right` or `dfu-split-*` / `avrdude-split-*`), `MASTER_LEFT`/`MASTER_RIGHT` (default: left = USB side).

## RP2040 specifics

- Bootloader entry: hold BOOT while plugging in, or bootmagic (hold key `[0,0]` while plugging), or the `QK_BOOT` keycode. Add `#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET` (and optional `RP2040_BOOTLOADER_DOUBLE_TAP_RESET_TIMEOUT 200U`) to `config.h` to enter it by double-tapping reset.
- Flash by copying the `.uf2` to the `RPI-RP2` drive.

## Vial

Vial = QMK fork with live remapping and a security unlock. Build in the **vial-qmk** repo (`make handwired/<name>:vial`), not upstream QMK.

- `keymaps/vial/rules.mk`: `VIA_ENABLE = yes` and `VIAL_ENABLE = yes` (here, not in the keyboard's rules).
- `keymaps/vial/config.h`:
  ```c
  #define VIAL_KEYBOARD_UID {0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0}
  #define VIAL_UNLOCK_COMBO_ROWS { 0, 0 }
  #define VIAL_UNLOCK_COMBO_COLS { 0, 1 }
  ```
  Generate the UID once with `python3 util/vial_generate_keyboard_uid.py` and **keep it** — a new UID makes Vial treat it as a different keyboard. Unlock combo coordinates must exist in the layout (`matrix_tool.py validate --unlock 0,0 0,1`). `VIAL_INSECURE = yes` in rules.mk skips the unlock (fine for personal boards).
- `vial.json`: `name`, `vendorId`, `productId` (match `usb`), `matrix: {rows, cols}` (total rows for splits), and `layouts.keymap` = KLE array whose keys carry `"row,col"` as the first legend. `matrix_tool.py route --out` produces exactly this.
- Layout alternatives (split backspace, ISO enter…) share coordinates and add `"option,choice"` as the 4th legend line (label position 8); `layouts.labels` names the options.

## Keymap sanity

Give layer 0 real keycodes. A layer 0 full of `KC_TRNS` produces a keyboard that types nothing until remapped — and a dead board after an EEPROM reset. 4 layers is the VIA/Vial default dynamic layer count.

## Outdated advice in older guides (pre-2023)

Many handwiring guides predate QMK's data-driven config. Translate before copying:

| Old guide says | Current QMK |
|---|---|
| `#define FLIP_HALF` to mirror a split | **Not a QMK setting** (it was a per-keyboard layout trick, removed May 2023). Mirror with the matrix numbering (right half's outer column = col 0) or a reversed `MATRIX_COL_PINS_RIGHT` / `split.matrix_pins.right`. |
| `RGB_DI_PIN`, `RGBLED_NUM` | `RGB_DI_PIN` now **fails the build**: use `ws2812.pin` (or `WS2812_DI_PIN`) and `rgblight.led_count` / `rgb_matrix` layout in keyboard.json. |
| `MATRIX_ROW_PINS_LEFT` | Doesn't exist: the plain `MATRIX_*_PINS` are the left half; only `_RIGHT` exists. |
| `MASTER_LEFT` in rules.mk | `config.h` (or prefer `EE_HANDS` / `split.handedness`). |
| `SPLIT_KEYBOARD = yes`, `SOFT_SERIAL_PIN`, `USE_I2C` | Still work, but keyboard.json `split.enabled`, `split.serial.pin`/`driver`, `split.transport.protocol` is the current way. |
| `ENCODERS_PAD_A/B`, `ENCODER_DIRECTION_FLIP` in rules.mk | keyboard.json `encoder.rotary: [{pin_a, pin_b}]`; `ENCODER_DIRECTION_FLIP` goes in `config.h`. |
| `#define LAYOUT(...)` macro in `<kb>.h` with `KC_NO` gaps | The `layouts` array in keyboard.json generates `LAYOUT()`; empty matrix positions need nothing. |
| `make <kb>:<keymap>` | Still works; `qmk compile -kb <kb> -km <keymap>` for QMK (Vial: use `make` in vial-qmk). |

## Direct wiring (≤ ~18 keys, no diodes)

Each switch: one leg to a GPIO, the other to GND. keyboard.json: `"matrix_pins": {"direct": [["F7", "F6", "F5", "F4"]]}` (rows of pins, `null` for gaps); old config.h equivalent `DIRECT_PINS`. Splits: `split.matrix_pins.right.direct`. A 3×3 matrix still uses fewer pins (6) than direct (9), so direct wiring wins only for very small pads or when you want no diodes.
