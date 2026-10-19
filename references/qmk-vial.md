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
- Don't define the same thing in both `keyboard.json` and `config.h`/`rules.mk` (e.g. pins, MCU) — QMK lint complains and the build may pick the wrong one. Keep pins and matrix size **only** in keyboard.json: `config.h` is for what JSON can't say (handedness, notes). This matters for Vial too (see below).
- The layout should start at `x = 0` and `y = 0`, or QMK warns "Layout is offset on X/Y axis". KLE exports often start at 0.14 or 0.7 — shift every key by the same amount.
- **No negative `rx`/`ry`**: QMK's schema rejects them and then drops the *whole* keyboard.json ("No LAYOUTs defined", bootmagic range errors follow). KLEs of angled boards (Alice, Arisu) often rotate around a point left of or above the board (`rx: -0.25`). Fix without moving anything: re-express each rotated key as rotating about its own rotated top-left corner (`x = rx = X`, `y = ry = Y`), then shift. `matrix_tool.py --format qmk` does both, and its output compiles.
- Re-exporting into a folder that already holds an older version: delete the old `info.json`, `config.h`, `rules.mk`, `keyboard.h` first. Left-over files override the new keyboard.json and the build fails or warns in confusing ways.
- Prove it builds: `qmk compile -kb handwired/<name> -km <keymap>` validates keyboard.json too. Run it before telling anyone the firmware is ready.

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

- **First flash**: unplug, hold BOOT (BOOTSEL on a Pico; on the RP2040-Tiny the button is on its USB-C adapter), plug in, let go → a drive called `RPI-RP2` appears. Nothing else works yet, because there's no QMK on the chip.
- **After that**: Bootmagic (hold the key set in `bootmagic.matrix`, default `[0,0]`, while plugging in), the `QK_BOOT` keycode, or double-tapping RESET. Double-tap is already on when keyboard.json sets no `board` (QMK's default RP2040 board, `GENERIC_PROMICRO_RP2040`, defines `RP2040_BOOTLOADER_DOUBLE_TAP_RESET`); with `BOARD = GENERIC_RP_RP2040` add the define yourself. The Pico has no RESET button.
- Flash by copying the `.uf2` to the `RPI-RP2` drive, or `qmk flash -kb … -km …`, which waits for the drive and copies it (`uf2conv --deploy`).

## Vial

Vial = QMK fork with live remapping and a security unlock. Build in the **vial-qmk** repo (`make handwired/<name>:vial`), not upstream QMK. Current vial-qmk reads a data-driven `keyboard.json` like QMK (proven 2026-10).

Build gotchas (each one found by actually compiling):
- **Python 3.14**: vial-qmk's helper `qmk/math.py` still uses `ast.Num`, removed in Python 3.14. It only runs when `config.h` defines `MATRIX_ROWS`/`MATRIX_COLS`, so `AttributeError: module 'ast' has no attribute 'Num'` goes away when the matrix lives only in keyboard.json `matrix_pins` (the right way anyway).
- **`make` can't find `arm-none-eabi-gcc`**: the QMK CLI installer puts its compilers in `~/.local/share/qmk/bin` (or `$QMK_DISTRIB_DIR/bin`), and only the `qmk` command adds that to PATH. Vial's docs say to build with `make`, so add it yourself: `PATH="$HOME/.local/share/qmk/bin:$PATH" make handwired/<name>:vial`.

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

## VIA

- `keymaps/via/rules.mk`: `VIA_ENABLE = yes` (keymap level only; on a Pro Micro add `LTO_ENABLE = yes` for space). VIA keeps 4 dynamic layers by default.
- VIA only knows boards from its own list, so a handwired board needs its definition loaded by hand: a VIA v3 `via.json` with `name`, `vendorId`, `productId` (same as keyboard.json `usb`), `matrix: {rows, cols}` (total rows on a split) and `layouts.keymap` = the KLE with each key's first legend set to `"row,col"`. Keep the user's original KLE (rotation and all) and only relabel its keys, rather than rebuilding rows.
- Load it in **usevia.app** with Chrome or Edge (VIA uses WebHID; Firefox and Safari can't): Settings → turn on **"Show Design tab"** → Design → **"Load Draft Definition"** → Load → pick `via.json`. The keyboard then appears under Configure. (Labels as in VIA's app source.)
- Give every board its own VID/PID pair: VIA tells definitions apart by it.

## Linux: device access (udev)

- Flashing (DFU/caterina/avrdude): install QMK's rules with `sh ~/qmk_firmware/util/install_udev.sh` (newer trees; older ones had `util/udev/50-qmk.rules`).
- A rule file in `/etc/udev/rules.d/` **overrides** a same-named one in `/usr/lib/udev/rules.d/`. A broken copy there (e.g. a saved "404: Not Found" page from a failed download) silently masks the working rules: check `head /etc/udev/rules.d/50-qmk.rules` when flashing can't find the board.
- VIA in the browser needs access to the keyboard's hidraw device:
  `echo 'KERNEL=="hidraw*", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="feed", ATTRS{idProduct}=="<pid>", MODE="0660", TAG+="uaccess"' | sudo tee /etc/udev/rules.d/59-<name>-via.rules && sudo udevadm control --reload && sudo udevadm trigger`
- Vial: use Vial's own rule (`59-vial.rules`, matches its serial) from get.vial.today/manual/linux-udev.html.

## Keymap sanity

Give layer 0 real keycodes. A layer 0 full of `KC_TRNS` produces a keyboard that types nothing until remapped — and a dead board after an EEPROM reset. 4 layers is the VIA/Vial default dynamic layer count.

Layer 0 from the KLE legends works well for a first firmware:
- KLE puts a key's **shifted** symbol top-left (slot 0) and the **unshifted** one bottom-left (slot 1): `"!\n1"` → `KC_1`, `"_\n-"` → `KC_MINS`, `"\"\n'"` → `KC_QUOT`. Use slot 1 when slot 0 is a lone symbol.
- Letters, digits, F-keys and names (Esc, Tab, Caps, Enter, Backspace, Del, Ins, PgUp/PGDW, arrows) map directly; `Shift`/`Ctrl`/`Alt`/`Win` right of the board's middle get the right-hand keycode; a blank key ≥ 2u is the space bar; `Fn` → `MO(1)`.
- Don't guess the rest (`MOD`, `Hyper`, custom names): make them `KC_NO` and list them so the user sets them in VIA/Vial.

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
