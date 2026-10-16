# Controller boards

Machine-readable copy: `boards.json` (used by `scripts/matrix_tool.py`). When a user names a board not listed here, look up its pinout from the manufacturer and apply the same questions: which pins are on the edge, which are wired to LEDs/power/USB, logic voltage, and which firmware runs on it.

## Quick comparison

| Board | MCU | Matrix pins (edge) | Firmware | Logic |
|---|---|---|---|---|
| Waveshare RP2040-Zero | RP2040 | 20 (+9 bottom pads) | QMK, Vial | 3.3 V |
| Waveshare RP2040-Tiny | RP2040 | 20 | QMK, Vial | 3.3 V |
| Waveshare RP2040-Plus / Raspberry Pi Pico | RP2040 | 26 | QMK, Vial | 3.3 V |
| Pro Micro (ATmega32U4) | AVR | 18 | QMK, Vial | 5 V |
| nice!nano v2 / SuperMini nRF52840 | nRF52840 | 16 (+5 awkward) | **ZMK only** | 3.3 V |

On a wired split, one pin per half is the TRRS link (suggested: Plus GP28, Zero/Tiny GP29, Pro Micro D2) — it's not available for the matrix.

Max keys without tricks ≈ (pins/2)² — 18 pins → 9×9 = 81 keys. For a split, each half has its own pins; rows per half × 2 = total rows.

## Waveshare RP2040-Zero
- Edge: GP0–GP15, GP26–GP29 (20 pins). Underside pads: GP17–GP25 (usable, fiddly).
- **GP16 = onboard WS2812 RGB LED** — don't use for the matrix.
- BOOT + RESET buttons; RP2040 is not 5 V tolerant.

## Waveshare RP2040-Tiny
- 20 castellated GPIOs; USB-C is on a separate adapter joined by an 8-pin FPC cable (keep the cable strain-free inside a case).
- GP16 drives the onboard WS2812.
- The exact edge pin list in `boards.json` is **unverified** — confirm with the Waveshare pinout before wiring.

## Waveshare RP2040-Plus / Raspberry Pi Pico
- Header GPIOs: GP0–GP22, GP26–GP28 (26 pins).
- Not usable: GP23 (regulator mode), GP24 (VBUS sense), GP25 (LED), GP29 (VSYS sense, not on header). Pico W boards use these for the radio.
- Power: VBUS = header pin 40 (USB 5 V — feed per-key LEDs from here), VSYS = 39, 3V3 = 36; GND = pins 3, 8, 13, 18, 23, 28, 33, 38 (skip these when running a ribbon cable).

## Pro Micro (ATmega32U4)
- 18 GPIOs: D3 (TX), D2 (RX), D1 (SDA), D0 (SCL), D4, C6, D7, E6, B4, B5, B6, B2, B3, B1, F7, F6, F5, F4.
- `SOFT_SERIAL_PIN` must be an interrupt pin: **D0–D3**. D2 is the usual split pin; avoid D0/D1 if you also want an I2C OLED.
- 5 V logic. Elite-C and other clones add pins (B7, D5, C7, F1, F0) — only use them if the user has that board.
- Bootloader `caterina` (Pro Micro) vs `atmel-dfu` (Elite-C) — ask which board.

## nice!nano v2 (and Pro-Micro-footprint nRF52840 clones)
- **ZMK only.** If a user wants QMK/Vial on it, tell them early.
- Edge pins and ZMK `&pro_micro N` index:

| pro_micro | GPIO | | pro_micro | GPIO |
|---|---|---|---|---|
| 0 | P0.08 | | 9 | P1.06 |
| 1 | P0.06 | | 10 | P0.09 (NFC) |
| 2 | P0.17 | | 14 | P1.11 |
| 3 | P0.20 | | 15 | P1.13 |
| 4 | P0.22 | | 16 | P0.10 (NFC) |
| 5 | P0.24 | | 18 | P1.15 |
| 6 | P1.00 | | 19 | P0.02 |
| 7 | P0.11 | | 20 | P0.29 |
| 8 | P1.04 | | 21 | P0.31 |

- NFC pins P0.09/P0.10: usable as GPIO, use last. Inner pads P1.01/P1.02/P1.07 are low-frequency only.
- P0.13 switches external VCC (for RGB/OLED power cut); P0.15 = blue LED. Battery is read through VDDH.
- Clones (SuperMini etc.) share the edge pinout but may differ in charge current, power switch and extra pads.
