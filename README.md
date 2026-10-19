# keyboard-handwiring — an Agent Skill for DIY keyboard builders

A [Claude Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) that helps Claude plan, wire and validate handwired mechanical keyboards:

- **Switch matrix design**: auto-assigns `row,col` coordinates from a KLE / kle-ng / VIA / QMK layout (rotation-aware), or validates the coordinates you already have.
- **Pinouts**: RP2040-Zero, RP2040-Tiny, RP2040-Plus / Pico, Pro Micro, nice!nano v2 and clones, including reserved pins (LEDs, power sense) and pin budgets.
- **Wiring plans**: per-row and per-column pin tables, diode orientation, soldering order, debugging table.
- **Split keyboards and cables**: TRRS/serial links, handedness, mirrored halves, and the difference between QMK (right half = extra rows) and ZMK (right half = extra columns).
- **Wireless and batteries**: LiPo choice and polarity, power switches, charge current, battery life, ZMK power/battery config.
- **Firmware config**: QMK `keyboard.json`, Vial (`vial.json`, UID, unlock combo), ZMK kscan + matrix transform.
- **Amoeba Royale single-key PCBs**: solder-side pad map, ROW2COL diode, LED chain and power feed.
- **Readable wiring diagrams**: dead zone between parallel wires, wires never over foreign pads, a controller per split half.

## Install

**Claude Code — all your projects** (update later with `git pull` in that folder):
```bash
git clone https://github.com/ArisAlt/keyboard-handwiring-skill.git ~/.claude/skills/keyboard-handwiring
```

**Claude Code — one project only** (run from the project root):
```bash
git clone https://github.com/ArisAlt/keyboard-handwiring-skill.git .claude/skills/keyboard-handwiring
```

**claude.ai / Claude Desktop:** download `keyboard-handwiring.skill` from the [latest release](https://github.com/ArisAlt/keyboard-handwiring-skill/releases/latest) and upload it under Settings → Capabilities → Skills.

Restart Claude Code (or start a new session) after installing so it picks up the skill.

Then just ask, for example: *"Here's my KLE layout, I have an RP2040-Zero — which pins do I solder and which way do the diodes go?"*

## The bundled tool

`scripts/matrix_tool.py` is Python 3, standard library only, and works without Claude too:

```bash
python scripts/matrix_tool.py boards
python scripts/matrix_tool.py route my-layout.json --board rp2040_zero --out via.json
python scripts/matrix_tool.py route my-layout.json --board pro_micro --split --format qmk --out keyboard.json   # --right-wiring mirrored|same|flipped
python scripts/matrix_tool.py route my-layout.json --board nice_nano_v2 --split --format zmk
python scripts/matrix_tool.py validate keyboard.json --board rp2040_plus --firmware vial --unlock 0,0 0,1
```

It prints a pin plan (each row/column wire → controller pin → keys on it), warnings and errors, and exits 1 when something is wrong. When the input already has `matrix_pins` (an already-wired board), `validate` checks those pins instead of suggesting new ones.

Input formats: KLE raw JSON (keyboard-layout-editor.com, [kle-ng](https://editor.keyboard-tools.xyz)), VIA/Vial JSON, QMK `info.json`/`keyboard.json` (including the `keyboards.qmk.fm` API wrapper).

## Layout

```
keyboard-handwiring-skill/
├── SKILL.md                     # workflow Claude follows
├── scripts/matrix_tool.py       # route / validate / pin-assign / export
├── references/
│   ├── boards.json / boards.md  # controller pin data
│   ├── qmk-vial.md
│   ├── zmk.md
│   ├── split-and-power.md       # two controllers, mirrored halves, TRRS, LiPo, LED power budget
│   ├── amoeba-royale.md         # single-key PCB pads, ROW2COL, LED chain
│   ├── wiring-practices.md      # diodes, wire, soldering order, debugging
│   └── layout-tools.md          # KLE, VIA labels, kle-ng, QMK formats
└── evals/evals.json             # test prompts for skill development
```

## Contributing

Pin data lives in `references/boards.json`. To add a board, add an entry with `pins` (recommended matrix pins in order), `extra` (usable but awkward), `reserved` (with the reason), `firmware`, and a source in the PR description. Boards whose pinout isn't confirmed against the manufacturer get `"verified": false`.

Facts were checked against: QMK docs (split keyboards, RP2040), ZMK docs and board files (nice!nano `pro_micro` gpio-map, battery config), Waveshare and Raspberry Pi pinouts, and the kle-ng documentation. Firmware projects move fast — corrections welcome.

## Changelog

- **1.3.0**: lessons from building and flashing real firmware (VIA, QMK and Vial compiled from generated files). `matrix_tool.py --format qmk` fixes rotated layouts that QMK rejected (negative `rx`/`ry`, e.g. Alice-style KLEs: the whole keyboard.json was dropped) without moving any key, starts the layout at 0,0 (no "offset" warning) and names the keyboard from a raw KLE's metadata — AliceZero now compiles as one board and as a split; new `pico` board. RP2040-Tiny verified from Waveshare's pinout (buttons on its USB-C adapter); Pico has no RESET button; RP2350 (Pico 2) not supported by QMK. QMK/Vial notes: keep pins only in keyboard.json (vial-qmk breaks on Python 3.14 when `config.h` defines the matrix), `make` needs QMK's compilers on PATH, remove stale files before re-exporting, first-flash vs double-tap reset, VIA's Design-tab loading, Linux udev (an `/etc` rule masks `/usr/lib`), layer 0 from KLE legends. Workflow: ask in one round when unclear, never fill board data with a default, prove the firmware builds.
- **1.2.0**: `matrix_tool.py --right-wiring mirrored|same|flipped` (mirrored is now the default; `--mirror-right` still works); split exports declare everything (`split.transport`, `split.serial`, `split.matrix_pins.right` with null = NO_PIN) and handedness is reported; split NOTEs (keys per half, unused pins per controller, uneven halves are fine); warning when an auto-split layout's halves touch/overlap (measured on rotated key positions); validation of a file's own `split.matrix_pins.right`. Docs: three right-half conventions, uneven halves (Quefrency 30+37, Sinc 38+44), explicit split declaration.
- **1.1.1**: checked against Ewen Cluney's *Hand-Wired Keyboard Guide* (2021): table of outdated QMK advice (`FLIP_HALF` removed 2023, `RGB_DI_PIN` now a build error, no `MATRIX_*_PINS_LEFT`, `MASTER_LEFT` belongs in config.h), direct wiring config, wire-prep tips, extra debug cases, Pro Micro Arduino↔port pin names.
- **1.1.0**: Amoeba Royale reference (pad map, ROW2COL); split conventions checked against QMK's lily58/sofle/iris/dactyl/sweep and the Sofle Pico (one pin list, mirrored vs same direction, controller per half, half/full-duplex TRRS); per-key RGB power budget; wiring-diagram readability rules; TRRS link pins and LED supply pins in `boards.json`.
- **1.0.0**: first release.

## License

MIT — see `LICENSE`.
