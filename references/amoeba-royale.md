# Amoeba Royale v2.0 single-key PCBs

Source: `amoeba-royale.kicad_pcb` in github.com/mtl/keyboard-pcbs (CC0). Each board carries one MX switch in a Kailh hot-swap socket, its diode, and an SK6812MINI LED. All three sit on the board's back (B.Cu).

## Orientation: the pinout picture is the SOLDER side
The common pinout diagram (Row/Col/LED pads around the edge) shows the board **from the back**: KiCad front-view coordinates mirrored left↔right. Describe wiring from that side, because that's where you'll be soldering.

## Pads (solder side, % of the 18.8 × 18.1 mm board, from top-left)

| Net | Pads (x %, y %) | Notes |
|---|---|---|
| R (row) | (10.8, 7.4) (89.2, 7.4) | top corners: row bus runs along the top edge |
| C (column) | (25.7, 7.4) (77.4, 7.4) (32.1, 93) (78, 93) | two on top, two on bottom: column bus runs top↔bottom |
| LED + (VDD) | (41.6, 7) (10.8, 82.5) (89.2, 82.5) (43.6, 93) | all four sides |
| LED − (VSS) | (52.7, 7) (10.8, 71.9) (89.2, 71.9) (55.1, 93) | all four sides |
| LED DIN | (63.9, 7.4) (9.8, 36.8) (89.2, 93) | top, left side, bottom-right corner |
| LED DOUT | (89.2, 20.4) (66.6, 93) (10.8, 93) | right side, bottom, bottom-left corner |

- Wire pads are **Ø1.5 mm** (0.9 mm drill), about 6 px apart along an edge at 55 px per key. That's too tight to run a wire *between* two pads, so plan wires to enter pads from outside the board edge.
- Pads of one net are joined on the board, so a bus can enter on one pad and leave on another.
- DIN and DOUT sit on opposite sides and corners on purpose, so an LED chain can snake: right then down then left (DOUT bottom-left corner → next board's DIN bottom-right corner).

## Diode direction: ROW2COL
On both diode footprints, the cathode (pad 1, square) goes to the switch and the **anode goes to the R pad**. Current flows row → diode → switch → column, so firmware must use **`DIODE_DIRECTION ROW2COL`** (QMK `diode_direction: "ROW2COL"`; ZMK `diode-direction = "row2col"`). With COL2ROW, no key registers. If in doubt, check with a meter in diode mode: red probe on R, black on the switch-side diode pad should read about 0.6 V.

## Wiring plan
- **Rows:** link neighbouring boards' R pads (right R → next board's left R).
- **Columns:** link C pads top ↔ bottom between boards stacked in a column. Use whichever of the two C pads faces the other board most directly.
- **LED data:** one chain per controller (per split half), snaking through the rows: DOUT → next board's DIN. The first board's DIN goes to a free GPIO (the `ws2812` pin).
- **LED power:** daisy-chain + and − along the same path. Feed the first board from 5 V (USB VBUS) and GND. With long chains, also connect the far end back to 5 V/GND.
- **Rotated keys:** the board rotates with the switch, so pads rotate too. On the solder side, the rotation angle flips sign.

## LED power budget (SK6812MINI)
See `split-and-power.md` for the full budget: about 60 mA per LED at full white and about 1 mA each when dark, against 500 mA from a normal USB port. Cap brightness (`RGB_MATRIX_MAXIMUM_BRIGHTNESS`) and add 100–470 µF across + and − at the first board.
