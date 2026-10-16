# ZMK (nRF52840: nice!nano and clones)

ZMK changes between releases (board naming moved with Zephyr hardware model v2; physical layouts were added). Before writing files, check the ZMK version the user's `zmk-config` pins, and follow that version's docs at zmk.dev where they disagree with this page.

## Where things go

Users normally build in GitHub Actions from a repo made from `zmk-config` template. A handwired board is a **shield** on top of the controller board:

```
config/
├── <name>.keymap
├── <name>.conf
└── boards/shields/<name>/
    ├── Kconfig.shield
    ├── Kconfig.defconfig
    ├── <name>.dtsi            # shared: kscan, transform (splits)
    ├── <name>_left.overlay    # split: left pins
    ├── <name>_right.overlay   # split: right pins + col-offset
    └── <name>.zmk.yml
build.yaml                     # board + shield combinations
```

`build.yaml` board name depends on ZMK version (`nice_nano_v2` on older releases; newer ones use revisioned names — copy from ZMK's supported-hardware page).

## Matrix (kscan)

```dts
kscan0: kscan {
    compatible = "zmk,kscan-gpio-matrix";
    diode-direction = "col2row";
    wakeup-source;
    col-gpios
        = <&pro_micro 21 GPIO_ACTIVE_HIGH>
        , <&pro_micro 20 GPIO_ACTIVE_HIGH>
        ;
    row-gpios
        = <&pro_micro 4 (GPIO_ACTIVE_HIGH | GPIO_PULL_DOWN)>
        , <&pro_micro 5 (GPIO_ACTIVE_HIGH | GPIO_PULL_DOWN)>
        ;
};
```

- `col2row`: columns are outputs, rows are inputs with pull-down. For `row2col` swap which list gets `GPIO_PULL_DOWN`.
- Use `&pro_micro N` (see the index table in `boards.md`) so the shield works on any Pro-Micro-footprint nRF board; raw `&gpio0 6` also works but ties it to one board.
- `wakeup-source` lets a keypress wake the board from deep sleep.

## Matrix transform

```dts
default_transform: keymap_transform_0 {
    compatible = "zmk,matrix-transform";
    columns = <12>;
    rows = <4>;
    map = <
        RC(0,0) RC(0,1) RC(0,2)  /* one RC per physical key, in layout order */
    >;
};
```

**Splits differ from QMK:** ZMK puts the right half into extra **columns**, not rows. Both halves share the transform; the right overlay sets `&default_transform { col-offset = 6; };` so its local columns 0–5 become 6–11. Convert a QMK-style layout (right rows offset) before reusing coordinates.

Point `chosen` at them (`zmk,kscan = &kscan0; zmk,matrix-transform = &default_transform;`), or, on newer ZMK, wrap them in a `zmk,physical-layout` node.

## Wireless split

- The **central** (usually left, connects to the computer) does more radio work and drains faster. A third nRF board as a USB dongle-central evens it out.
- No wire between halves; pair each half after flashing `settings_reset` if pairing gets stuck.
- Flash each half's own `.uf2` (left/right) by double-tapping reset and copying to the `NICENANO` drive.

## Power and battery Kconfig

| Option | Meaning |
|---|---|
| `CONFIG_ZMK_SLEEP=y` | Deep sleep after idle (big battery win) |
| `CONFIG_ZMK_IDLE_SLEEP_TIMEOUT` | ms before deep sleep |
| `CONFIG_ZMK_BATTERY_REPORTING` | Report battery % (on by default with BLE) |
| `CONFIG_ZMK_BATTERY_REPORT_INTERVAL` | Seconds between reports (default 60) |
| `CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING=y` + `..._PROXY=y` | Also report the peripheral half's battery |
| `CONFIG_BT_BAS=n` | Stop battery packets waking some Macs (on-board display still works) |

Battery sensor in devicetree (`chosen { zmk,battery = &vbatt; }`): `zmk,battery-nrf-vddh` on nice!nano-style boards (no config), or `zmk,battery-voltage-divider` when the battery is read through a resistor divider on an ADC pin.

External power for RGB/OLED: nice!nano switches VCC with P0.13 (`zmk,ext-power-generic`); turning it off when idle is the difference between weeks and days of battery.
