# keyboard-handwiring — an Agent Skill for DIY keyboard builders

A [Claude Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) that helps Claude plan, wire and validate handwired mechanical keyboards:

- **Switch matrix design**: auto-assigns `row,col` coordinates from a KLE / kle-ng / VIA / QMK layout (rotation-aware), or validates the coordinates you already have.
- **Pinouts**: RP2040-Zero, RP2040-Tiny, RP2040-Plus / Pico, Pro Micro, nice!nano v2 and clones, including reserved pins (LEDs, power sense) and pin budgets.
- **Wiring plans**: per-row and per-column pin tables, diode orientation, soldering order, debugging table.
- **Split keyboards and cables**: TRRS/serial links, handedness, mirrored halves, and the difference between QMK (right half = extra rows) and ZMK (right half = extra columns).
- **Wireless and batteries**: LiPo choice and polarity, power switches, charge current, battery life, ZMK power/battery config.
- **Firmware config**: QMK `keyboard.json`, Vial (`vial.json`, UID, unlock combo), ZMK kscan + matrix transform.

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
python scripts/matrix_tool.py route my-layout.json --board pro_micro --split --mirror-right --format qmk --out keyboard.json
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
│   ├── split-and-power.md       # TRRS links, handedness, LiPo, battery life
│   ├── wiring-practices.md      # diodes, wire, soldering order, debugging
│   └── layout-tools.md          # KLE, VIA labels, kle-ng, QMK formats
└── evals/evals.json             # test prompts for skill development
```

## Contributing

Pin data lives in `references/boards.json`. To add a board, add an entry with `pins` (recommended matrix pins in order), `extra` (usable but awkward), `reserved` (with the reason), `firmware`, and a source in the PR description. Boards whose pinout isn't confirmed against the manufacturer get `"verified": false` — `rp2040_tiny` needs a confirmation.

Facts were checked against: QMK docs (split keyboards, RP2040), ZMK docs and board files (nice!nano `pro_micro` gpio-map, battery config), Waveshare and Raspberry Pi pinouts, and the kle-ng documentation. Firmware projects move fast — corrections welcome.

## License

MIT — see `LICENSE`.
