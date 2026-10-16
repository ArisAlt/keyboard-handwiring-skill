# Layout files and editors

## KLE raw JSON (keyboard-layout-editor.com, kle-ng)
- Array of rows; each row is an array of key legend strings, preceded by property objects that change the *next* keys.
- Optional first element `{...}` = keyboard metadata (name, author…).
- Per-key props reset after each key: `x`/`y` (offsets), `w`/`h` (default 1), `d` (decal). Persistent until changed: `r`/`rx`/`ry` (rotation and its origin), `a` (legend alignment), `g` (ghost), colours.
- A new `rx`/`ry` resets the cursor to that origin. Each new row moves `y` down 1 and resets `x` to `rx`.
- Rotation is clockwise in degrees around (`rx`,`ry`); the key's `x`/`y` are its position before rotation.
- Legends: a key string splits on `\n` into up to 12 lines; with the default alignment (`a: 4`) line 0 is the top-left legend (position 0) and line 3 is the bottom-right legend (position 8). Other `a` values remap lines to positions.
- Ghost (`g`) and decal (`d`) keys are cosmetic — exclude them from the matrix.

## VIA / Vial layout convention
- Each real key's top-left legend (position 0) is `"row,col"`.
- Layout alternatives share a coordinate and carry `"option,choice"` in the bottom-right legend (position 8, raw line 3): `"0,13\n\n\n0,1"`.
- VIA/Vial JSON wraps the KLE array: `{"name", "vendorId", "productId", "matrix": {"rows", "cols"}, "layouts": {"keymap": [...KLE...], "labels": [...]}}`.

## kle-ng (editor.keyboard-tools.xyz, MIT, github.com/adamws/kle-ng)
- Modern KLE reimplementation; reads/writes KLE JSON, imports VIA/Vial JSON (keeps VIA metadata in `_kleng_via_data`, exportable via *Download VIA JSON*), imports QMK `info.json` (matrix → `row,col` legends), exports PNG with embedded layout (re-importable), SVG/HTML.
- **Extra Tools → Add Switch Matrix Coordinates**: automatic annotation (geometry clustering, rotation- and symmetry-aware) or draw rows/columns manually. Its docs warn auto-annotation can be wrong on ergonomic layouts with strong column splay — validate the result.
- Duplicate `row,col` without `option,choice` is flagged as invalid.
- QMK imports often lose exact rotation — re-check positions before making plates/PCBs.
- **Plate generator:** switch/stabiliser cutouts → SVG, DXF, STL, JSCAD (MX, Alps, Choc).
- **PCB generator:** KiCad 9+ project (matrix schematic + placed switches/diodes, optional basic routing). Needs `row,col` on every key, ≤150 keys; files expire after 1 h; runs on their server. The MCU, USB, edge cuts and mounting holes are still the user's job; always run DRC.
- Share links (`#share=…`) encode the whole layout — ask users for one; it's the easiest way to get their exact layout.

## QMK info.json / keyboard.json
- `layouts.<NAME>.layout[]`: `{"matrix": [r, c], "x", "y", "w", "h", "r", "rx", "ry"}`. Order = `LAYOUT()` macro arguments.
- The QMK API (`keyboards.qmk.fm/v1/keyboards/<path>/info.json`) wraps the data: `{"keyboards": {"<path>": {...}}}`. `matrix_tool.py` unwraps it.

## Cubify
Browser handwiring visualizer (github.com/ArisAlt/cubify): imports KLE, auto-routes rows/columns, draws wires in top/bottom view and exports a Vial ZIP. Same `row,col` label convention as above.
