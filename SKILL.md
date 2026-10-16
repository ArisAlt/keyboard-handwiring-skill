---
name: keyboard-handwiring
description: Plan, wire and validate handwired (and simple PCB) mechanical keyboards — switch matrix design, row/column assignment, diode direction, microcontroller pinouts (RP2040-Zero/Tiny/Plus/Pico, Pro Micro, nice!nano and clones), pin budgets, split-keyboard links (TRRS/serial, handedness), wireless power and LiPo batteries, and firmware config for QMK, Vial/VIA and ZMK. Use this skill whenever someone is building or debugging a custom keyboard, imports a KLE / keyboard-layout-editor / kle-ng / VIA / QMK info.json layout, asks which pins to solder, how to route rows and columns, why keys ghost or don't register, how to wire a split or wireless board, how to size or connect a battery, or wants matrix/pin tables or keyboard.json, config.h, vial.json or ZMK overlay files generated — even if they never say "matrix" or "handwire".
---

# Keyboard Handwiring

Turn a physical key layout into a wiring plan someone can solder, plus firmware config that matches the wiring exactly. The single most common failure in DIY keyboards is a mismatch between three things that must agree: the **physical wires**, the **matrix coordinates** in the layout file, and the **pin lists** in firmware. Everything in this skill exists to keep those three in sync.

## Workflow

### 1. Pin down the inputs

Ask only for what you can't infer:

| Input | Why it matters |
|---|---|
| Layout source (KLE raw JSON, kle-ng share/export, VIA/Vial JSON, QMK `info.json`/`keyboard.json`) | Physical positions; may already carry `row,col` labels |
| Microcontroller board | Usable pins, firmware support, voltage |
| Firmware: QMK, Vial (QMK fork) or ZMK | nRF52840 boards (nice!nano) are **ZMK only** — QMK does not run on them |
| Split? Wired (TRRS/serial) or wireless? | Pins per half, link pin, handedness, power |
| Diode direction (default `COL2ROW`) | Diode orientation when soldering and firmware setting |

### 2. Design or verify the matrix

Run the bundled tool (Python 3, stdlib only) instead of eyeballing coordinates:

```bash
python scripts/matrix_tool.py boards                       # board profiles + pin notes
python scripts/matrix_tool.py route layout.json --board rp2040_zero --out via.json
python scripts/matrix_tool.py route layout.json --board rp2040_zero --split --mirror-right \
       --format qmk --out keyboard.json                    # QMK keyboard.json with pins + split
python scripts/matrix_tool.py route layout.json --board nice_nano_v2 --split --format zmk
python scripts/matrix_tool.py validate vial.json --board pro_micro --split --firmware vial --unlock 0,0 0,1
```

- `route` auto-assigns `row,col` from geometry (rotation-aware), keeps the file's key order, resolves collisions, and can write: `via`/`kle` (layout with `row,col` in legend position 0, original legends kept), `qmk` (`keyboard.json`: processor, pins, split serial, layout), or `zmk` (kscan + matrix-transform snippet, right half as column offset).
- `validate` checks an already-annotated layout: duplicate or missing coordinates (VIA `option,choice` alternates may share), unused rows/columns, pin budget per half, split row parity, Vial unlock-combo keys, board/firmware compatibility.
- Both print the pin plan: each row/column → MCU pin → the keys on that wire. Add `--json` for machine-readable output. Exit code 1 means errors.
- `--mirror-right` numbers the right half's columns from its outer edge — the usual choice when the right half is wired as a mirror image of the left with the same pin list.

The router favours **straight wires** (easiest to solder). Commercial designs often fold stray keys into another row to save a pin — e.g. Lily58 puts its inner `[`/`]` keys in the thumb row, giving 6 columns per half where straight routing gives 7. Offer folding only when pins are short, and describe the fold physically ("the `[` key joins the thumb-row wire").

If the user's layout already has `row,col` labels (e.g. from kle-ng's *Add Switch Matrix Coordinates* or a VIA file), **validate, don't re-route** — they may have wired it already. Wiring that is already soldered is the source of truth; change the file, not the wires.

Matrix design rules (and why):
- **Pins = rows + cols** (per half on splits). Squarer matrices use fewer pins: 60 keys as 5×12 = 17 pins, but as 8×8 = 16. Suggest folding only if pins are actually short — straight physical rows/cols are much easier to solder and debug.
- **Every key needs a unique `row,col`** or two keys will read as one. Exception: VIA layout alternatives (e.g. split vs 2u backspace) share a coordinate and are tagged `option,choice` in label position 8.
- **One diode per switch** prevents ghosting with 3+ keys held. With ≤ ~18 keys you can skip the matrix entirely and wire each switch direct-to-pin.
- Encoders' push switches can live in the matrix; their A/B pins cannot.

### 3. Assign pins

Use `references/boards.md` (human notes) — the tool reads the same data from `references/boards.json`. Rules:
- Never use pins marked reserved (onboard LEDs, power/sense pins, USB). Avoid pins needed for something else on this build: split link, I2C OLED (SDA/SCL), RGB data.
- Keep the split link pin identical on both halves.
- Prefer contiguous, edge-accessible pins in physical order so wires don't cross over the controller.
- RP2040 and nRF52840 are **3.3 V and not 5 V tolerant**; the Pro Micro (ATmega32U4) is 5 V. Don't mix logic levels on a split link.

### 4. Produce the wiring plan

Deliver, in this order:
1. **Pin table** — `Row 0 → GP0 → keys: Esc, 1, 2…` for every row and column (per half for splits).
2. **Diode orientation** — for `COL2ROW`, the diode's black band (cathode) faces the **row** wire; current flows column → switch → diode → row. For `ROW2COL` it's reversed. State it in physical terms ("stripe toward the row bus") — this is the #1 soldering mistake.
3. **Wiring order** — usually: diodes onto every switch, row buses through the diode legs, then column wires on the other switch pin, then controller wires last. Insulate where rows cross columns.
4. **Bottom-view note** — when you flip the board to solder, left and right swap. Describe positions as seen from the side being soldered.
5. **Test plan** — continuity-test each row and column to its pin before flashing; then flash and press every key (QMK `qmk console` / ZMK keymap tester / Vial matrix tester).

For split, wireless and battery builds also read `references/split-and-power.md`. For practical soldering detail read `references/wiring-practices.md`.

### 5. Generate firmware config

Read the reference for the target firmware before writing files — the details (file names, which keys go where) are where builds fail:
- QMK / Vial → `references/qmk-vial.md`
- ZMK → `references/zmk.md`

Generated config must reuse the **exact** pin order and coordinates from step 3. If you change one, re-run `validate`.

### 6. Validate before anyone solders or flashes

Re-run `validate` on the final layout. Also check:
- `MATRIX_ROWS` for a split = 2 × rows per half (QMK reads left rows first, then right).
- Vial unlock combo points at keys that exist.
- Board actually supports the chosen firmware.

## Layout editors

Users often come from **kle-ng** (editor.keyboard-tools.xyz) or keyboard-layout-editor.com. See `references/layout-tools.md` for how labels, rotation, ghost/decal keys and VIA metadata work there, and what kle-ng's PCB generator expects.

## Output format

Answer with: a one-line summary (board, matrix size, pins used / available), the pin table, the diode orientation sentence, any warnings from `validate`, then generated files. Keep warnings concrete: name the key, the coordinate and the fix.
