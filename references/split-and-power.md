# Split links, connections and batteries

## Wired split (QMK / Vial)

**Cable:** TRRS/TRS (audio jack) is the norm; USB-C-to-USB-C between halves works but looks like a USB port and invites plugging a computer into it.

| Link | Conductors | Notes |
|---|---|---|
| Single-wire serial (half duplex) | VCC, GND, DATA → TRS is enough | Default. AVR: soft serial on D0–D3. RP2040: `vendor` driver, any GPIO. |
| Full-duplex serial | VCC, GND, TX, RX → TRRS | Cross TX→RX between halves. RP2040 only in practice. |
| I2C | VCC, GND, SDA, SCL → TRRS | Needs ~4.7 kΩ pull-ups on SDA and SCL (one set, on one half). Uses the I2C pins, so no OLED on the same bus without care. |

Rules:
- **Same link pin on both halves**, wired jack sleeve/ring/tip identically on both sides (mirror the jack, not the wiring).
- **Never plug or unplug the TRRS cable while USB is connected.** Sliding the plug briefly shorts VCC to data/GND and can kill a pin or the controller.
- RP2040 halves: carry 5 V (VSYS/5V pin) over the cable so the far half's regulator powers it; the data line is 3.3 V. Don't link a 5 V Pro Micro half to a 3.3 V RP2040 half.
- Handedness: decide `EE_HANDS` vs `MASTER_LEFT` vs a hand pin before flashing (see `qmk-vial.md`). Wrong handedness = right half types left-half keys.
- **Mirrored halves:** handwired right halves are usually built as a mirror image using the same pin list. Decide whether column 0 is the *outer* or *inner* column on each half and make the layout file match. `matrix_tool.py route --split` numbers each half's columns left→right as seen from the top; pass `--mirror-right` to number the right half from its outer edge (same pins, mirrored wiring).

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
