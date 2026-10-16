# Wiring practice

## Parts
- **Diodes:** 1N4148 (through-hole, easiest to bend round switch pins) or SMD 1N4148W/SOD-123 on hot-swap PCBs. One per switch.
- **Wire:** solid-core 22–26 AWG for row/column buses (strip short windows at each joint), or stranded/enamelled (magnet) wire for the long runs to the controller. Enamelled wire needs the coating burnt off with a hot iron.
- **Hot-swap sockets** (Kailh/Gateron MX or Choc) or Mill-Max sockets let switches be replaced without desoldering — glue or clip them so they don't pop out.

## Diode orientation
- `COL2ROW` (QMK default): current flows **column → switch → diode → row**. The diode's **black band (cathode) faces the row** wire.
- `ROW2COL`: the band faces the column.
- Many builders use the diode leg itself as the row bus: bend each cathode leg sideways to touch the next diode's leg along the row.
- Reversed diodes make whole rows/keys dead or ghost; if *every* key is dead, the firmware direction is probably the opposite of the soldering — flip `diode_direction` instead of resoldering.

## Order of work
1. Plan on paper/screen: pin table, which way diodes face, which side is up.
2. Fit switches into the plate.
3. Solder diodes onto each switch (one pin), forming the row buses.
4. Run column wires across the other switch pins. Insulate wherever a column crosses a row.
5. Continuity-check every row and column end-to-end.
6. Wire rows and columns to the controller last, keeping wires short and strain-relieved.
7. Flash a test firmware and press every key.

When soldering from the back, the left/right order is mirrored. Label rows/columns on masking tape at the board edge.

## Colour-coding
Use one colour for rows and another for columns (or a ribbon cable whose colour order matches pin order). Write the mapping in the pin table you hand the user.

## Debugging table

| Symptom | Likely cause |
|---|---|
| Whole row or column dead | Broken bus or bad joint at the controller pin; pin is reserved/used by something else |
| One key dead | Cold joint at switch or diode; dead switch; missing coordinate in layout |
| Two keys type the same thing | Duplicate `row,col` in layout file |
| Pressing one key types a different key | Pin order in firmware differs from wiring; split halves swapped |
| Extra keys appear when 3 are held (ghosting) | Missing or reversed diode |
| Key repeats/chatters | Cold joint, damaged switch; raise debounce (`DEBOUNCE`) only after checking hardware |
| Right half types left half's keys | Handedness config wrong |
| Nothing works, controller is detected | `diode_direction` opposite to soldering |

Quick test without switches: short a row pin to a column pin at the controller with tweezers — the matching key should register. Multimeter in diode mode across a diode shows ~0.6 V one way and open the other.

## Drawing a wiring diagram people can follow
- **Dead zone:** wires running side by side (within ~30° of parallel) keep a clear gap between their *edges*, around 2 px at 1:1 / 4 px zoomed. Crossing at an angle is fine; rows cross columns everywhere.
- **Pads:** a wire touches only the pads at its own two ends and stays clear of every other pad. On a real board a wire over a foreign pad could short. Draw pads at true size so clearances are honest.
- **Shortest clean route:** use a straight link between facing pads when it keeps both rules; otherwise route down → across → down in its own lane. Never detour where a straight link is clean.
- **Colour by pin**, not by drawing order, so one row keeps one colour on both halves and colours follow a ribbon cable's order.
- **Splits:** draw one controller per half, home-run each half's rows/columns to its own controller, and draw the TRRS/BLE link between them.
