#!/usr/bin/env python3
"""
matrix_tool.py — route, validate and pin-assign keyboard switch matrices.

Inputs (auto-detected):
  * KLE raw JSON (keyboard-layout-editor.com / kle-ng "raw" export)
  * VIA / Vial JSON  ({"layouts": {"keymap": [...KLE...]}, "matrix": {...}})
  * QMK info.json / keyboard.json (also the keyboards.qmk.fm API wrapper)

Commands:
  route     assign row,col to every key from geometry, then validate
  validate  check an already-annotated layout
  boards    list controller profiles

Examples:
  matrix_tool.py route layout.json --board rp2040_zero --out annotated.json
  matrix_tool.py route layout.json --board pro_micro --split --format qmk --out keyboard.json
  matrix_tool.py validate vial.json --board rp2040_plus --unlock 0,0 0,1
  matrix_tool.py route layout.json --board nice_nano_v2 --split --format zmk

Standard library only. Exit code 1 when validation finds errors.
"""
import argparse
import copy
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOARDS_PATH = os.path.join(HERE, "..", "references", "boards.json")

# kle-serial label map: LABEL_MAP[align][raw_line_index] -> legend position
LABEL_MAP = [
    [0, 6, 2, 8, 9, 11, 3, 5, 1, 4, 7, 10],
    [1, 7, -1, -1, 9, 11, 4, -1, -1, -1, -1, 10],
    [3, -1, 5, -1, 9, 11, -1, -1, 4, -1, -1, 10],
    [4, -1, -1, -1, 9, 11, -1, -1, -1, -1, -1, 10],
    [0, 6, 2, 8, 10, -1, 3, 5, 1, 4, 7, -1],
    [1, 7, -1, -1, 10, -1, 4, -1, -1, -1, -1, -1],
    [3, -1, 5, -1, 10, -1, -1, -1, 4, -1, -1, -1],
    [4, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1],
]
RC_RE = re.compile(r"^\s*(\d+)\s*,\s*(\d+)\s*$")


# ─────────────────────────────── loading ────────────────────────────────

def load_boards():
    with open(BOARDS_PATH) as f:
        return json.load(f)["boards"]


def decode_labels(raw, align):
    labels = [""] * 12
    amap = LABEL_MAP[align if 0 <= align < 8 else 4]
    for i, text in enumerate(raw.split("\n")):
        if i < 12 and amap[i] >= 0:
            labels[amap[i]] = text
    return labels


def encode_labels(labels, align):
    amap = LABEL_MAP[align]
    lines = [""] * 12
    dropped = 0
    for pos, text in enumerate(labels):
        if not text:
            continue
        if pos in amap:
            lines[amap.index(pos)] = text
        else:
            dropped += 1
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines), dropped


def key_center(x, y, w, h, r, rx, ry):
    cx, cy = x + w / 2, y + h / 2
    if r:
        a = math.radians(r)
        dx, dy = cx - rx, cy - ry
        cx = rx + dx * math.cos(a) - dy * math.sin(a)
        cy = ry + dx * math.sin(a) + dy * math.cos(a)
    return cx, cy


def parse_kle(rows):
    """kle-serial compatible parse. Returns list of key dicts in file order."""
    keys = []
    cur = {"x": 0.0, "y": 0.0, "r": 0.0, "rx": 0.0, "ry": 0.0, "a": 4, "g": False}
    for ri, row in enumerate(rows):
        if isinstance(row, dict):
            continue  # keyboard metadata
        if not isinstance(row, list):
            raise ValueError(f"KLE row {ri} is not a list")
        w = h = 1.0
        decal = False
        for ii, item in enumerate(row):
            if isinstance(item, dict):
                if "r" in item:
                    cur["r"] = float(item["r"])
                if "rx" in item:
                    cur["rx"] = float(item["rx"])
                if "ry" in item:
                    cur["ry"] = float(item["ry"])
                if "rx" in item or "ry" in item:
                    cur["x"], cur["y"] = cur["rx"], cur["ry"]
                if "a" in item:
                    cur["a"] = int(item["a"])
                if "g" in item:
                    cur["g"] = bool(item["g"])
                cur["x"] += float(item.get("x", 0))
                cur["y"] += float(item.get("y", 0))
                w = float(item.get("w", w))
                h = float(item.get("h", h))
                if item.get("d"):
                    decal = True
            elif isinstance(item, str):
                labels = decode_labels(item, cur["a"])
                k = make_key(cur["x"], cur["y"], w, h, cur["r"], cur["rx"], cur["ry"], labels)
                k["ghost"], k["decal"], k["src"] = cur["g"], decal, (ri, ii)
                keys.append(k)
                cur["x"] += w
                w = h = 1.0
                decal = False
        cur["y"] += 1
        cur["x"] = cur["rx"]
    return keys


def make_key(x, y, w, h, r, rx, ry, labels):
    cx, cy = key_center(x, y, w, h, r, rx, ry)
    m = RC_RE.match(labels[0] or "")
    o = RC_RE.match(labels[8] or "")
    if labels[0] and not m:
        legend = labels[0]
    else:
        legend = next((l for i, l in enumerate(labels) if l and i not in (0, 8)), "")
    return {
        "x": x, "y": y, "w": w, "h": h, "r": r, "rx": rx, "ry": ry,
        "cx": cx, "cy": cy, "labels": labels, "legend": legend.replace("<br>", " "),
        "matrix": [int(m.group(1)), int(m.group(2))] if m else None,
        "option": (int(o.group(1)), int(o.group(2))) if o else None,
        "ghost": False, "decal": False,
    }


def load_layout(path, layout_name=None):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"kind": "kle", "raw": data, "keys": parse_kle(data), "meta": {}}
    if not isinstance(data, dict):
        raise ValueError("Unrecognised file: expected a JSON array or object")
    if "keyboards" in data and isinstance(data["keyboards"], dict):  # QMK API wrapper
        data = next(iter(data["keyboards"].values()))
    layouts = data.get("layouts", {})
    if isinstance(layouts, dict) and "keymap" in layouts:
        return {"kind": "via", "raw": layouts["keymap"], "keys": parse_kle(layouts["keymap"]), "meta": data}
    if isinstance(layouts, dict) and layouts:
        name = layout_name or next(iter(layouts))
        if name not in layouts:
            raise ValueError(f"Layout {name!r} not found; have: {', '.join(layouts)}")
        keys = []
        for i, e in enumerate(layouts[name].get("layout", [])):
            labels = [""] * 12
            labels[0] = e.get("label", "")
            k = make_key(float(e.get("x", 0)), float(e.get("y", 0)), float(e.get("w", 1)), float(e.get("h", 1)),
                         float(e.get("r", 0)), float(e.get("rx", 0)), float(e.get("ry", 0)), labels)
            k["matrix"] = list(e["matrix"]) if "matrix" in e else None
            k["legend"] = e.get("label", "") or f"#{i}"
            k["src"] = i
            keys.append(k)
        return {"kind": "qmk", "raw": None, "keys": keys, "meta": data, "layout_name": name}
    raise ValueError("Unrecognised JSON: not KLE, VIA/Vial or QMK info.json/keyboard.json")


def matrix_keys(keys):
    return [k for k in keys if not k["ghost"] and not k["decal"]]


def key_name(k):
    return k["legend"].strip() or f"@({k['x']:.2f},{k['y']:.2f})"


# ─────────────────────────────── routing ────────────────────────────────

def band(values, tol):
    """1-D clustering: returns list of band centres (sorted)."""
    bands = []
    for v in sorted(values):
        if bands and abs(v - bands[-1][0]) < tol:
            b = bands[-1]
            b[1].append(v)
            b[0] = sum(b[1]) / len(b[1])
        else:
            bands.append([v, [v]])
    return [b[0] for b in bands]


def nearest(centres, v):
    return min(range(len(centres)), key=lambda i: abs(centres[i] - v))


def grid_route(keys, row_tol, col_tol):
    """Assign (row, col) local to this group. Returns (n_rows, n_cols)."""
    if not keys:
        return 0, 0
    row_c = band([k["cy"] for k in keys], row_tol)
    col_c = band([k["cx"] for k in keys], col_tol)
    rows = {}
    for k in keys:
        rows.setdefault(nearest(row_c, k["cy"]), []).append(k)
    col_x = {i: c for i, c in enumerate(col_c)}
    next_id = len(col_c)
    for _, rkeys in rows.items():
        used = set()
        for k in sorted(rkeys, key=lambda k: k["cx"]):
            order = sorted(col_x, key=lambda i: abs(col_x[i] - k["cx"]))
            pick = next((i for i in order if i not in used and abs(col_x[i] - k["cx"]) < 1.5), None)
            if pick is None:  # collision: open a new column at this key's x
                pick, next_id = next_id, next_id + 1
                col_x[pick] = k["cx"]
            used.add(pick)
            k["_col"] = pick
    # Renumber columns left→right by mean x of their keys, dropping empty ones
    members = {}
    for k in keys:
        members.setdefault(k["_col"], []).append(k["cx"])
    order = sorted(members, key=lambda c: sum(members[c]) / len(members[c]))
    remap = {c: i for i, c in enumerate(order)}
    row_order = sorted(rows, key=lambda r: row_c[r])
    rmap = {r: i for i, r in enumerate(row_order)}
    for ri, rkeys in rows.items():
        for k in rkeys:
            k["_lr"], k["_lc"] = rmap[ri], remap[k["_col"]]
            del k["_col"]
    return len(row_order), len(order)


def split_x(keys):
    xs = sorted(k["cx"] for k in keys)
    lo, hi = xs[0], xs[-1]
    span = hi - lo
    best_gap, best_x = 0.0, (lo + hi) / 2
    for a, b in zip(xs, xs[1:]):
        mid = (a + b) / 2
        if lo + 0.3 * span <= mid <= hi - 0.3 * span and b - a > best_gap:
            best_gap, best_x = b - a, mid
    return best_x


def route(keys, split, mirror_right, row_tol, col_tol):
    mk = matrix_keys(keys)
    if not mk:
        raise ValueError("No keys found in layout")
    info = {"split": split}
    if split:
        sx = split_x(mk)
        left = [k for k in mk if k["cx"] <= sx]
        right = [k for k in mk if k["cx"] > sx]
        lr, lc = grid_route(left, row_tol, col_tol)
        rr, rc = grid_route(right, row_tol, col_tol)
        rph = max(lr, rr)
        for k in left:
            k["matrix"] = [k.pop("_lr"), k.pop("_lc")]
        for k in right:
            c = k.pop("_lc")
            k["matrix"] = [rph + k.pop("_lr"), (rc - 1 - c) if mirror_right else c]
        info.update(split_at=round(sx, 3), rows_per_half=rph, left=(lr, lc), right=(rr, rc))
    else:
        grid_route(mk, row_tol, col_tol)
        for k in mk:
            k["matrix"] = [k.pop("_lr"), k.pop("_lc")]
    return info


# ────────────────────────────── validation ──────────────────────────────

def analyse(keys, board, split, unlock, firmware, split_link, file_pins=None):
    errors, warnings = [], []
    mk = matrix_keys(keys)
    missing = [k for k in mk if not k["matrix"]]
    for k in missing:
        errors.append(f"Key {key_name(k)} has no row,col coordinate")
    seen = {}
    for k in mk:
        if k["matrix"]:
            seen.setdefault(tuple(k["matrix"]), []).append(k)
    for rc, ks in sorted(seen.items()):
        if len(ks) < 2:
            continue
        opts = [k["option"] for k in ks]
        if None in opts or len(set(opts)) < len(opts):
            errors.append(f"Duplicate coordinate {rc[0]},{rc[1]} on keys: "
                          + ", ".join(key_name(k) for k in ks)
                          + " (allowed only for VIA layout alternatives with different option,choice)")
    coords = [tuple(k["matrix"]) for k in mk if k["matrix"]]
    if not coords:
        return {"errors": errors or ["No matrix coordinates found"], "warnings": warnings}
    n_rows = max(r for r, _ in coords) + 1
    n_cols = max(c for _, c in coords) + 1
    used_rows = {r for r, _ in coords}
    used_cols = {c for _, c in coords}

    if split:
        if n_rows % 2:
            warnings.append(f"Split layout has {n_rows} total rows; QMK uses 2 × rows-per-half "
                            f"→ treating as {(n_rows + 1) // 2} rows per half")
        rph = (n_rows + 1) // 2
        lr = {r for r in used_rows if r < rph}
        rr = {r - rph for r in used_rows if r >= rph}
        if not rr:
            errors.append("Split layout but no keys use right-half rows (right rows must start at rows_per_half)")
        rows_needed = rph
    else:
        rph = n_rows
        rows_needed = n_rows
    for r in range(rph):
        if split and r not in lr and r not in rr:
            warnings.append(f"Row {r} (per half) has no keys on either half (wastes a pin)")
        elif not split and r not in used_rows:
            warnings.append(f"Row {r} has no keys (wastes a pin)")
    for c in range(n_cols):
        if c not in used_cols:
            warnings.append(f"Column {c} has no keys (wastes a pin)")

    for u in unlock or []:
        if tuple(u) not in seen:
            errors.append(f"Vial unlock combo key {u[0]},{u[1]} does not exist in the layout")

    plan = None
    if board:
        if not board.get("verified", True):
            warnings.append(f"{board['label']}: pin list is unverified — check the manufacturer's pinout")
        if firmware and firmware not in board["firmware"]:
            errors.append(f"{board['label']} does not support {firmware.upper()} "
                          f"(supported: {', '.join(board['firmware'])})")
        pool = list(board["pins"])
        link = None
        if split and "zmk" not in board["firmware"]:
            link = split_link or board.get("split_link")
            if link in pool:
                pool.remove(link)
        need = rows_needed + n_cols
        if need > len(pool):
            extra = board.get("extra", [])
            msg = (f"Need {need} pins ({rows_needed} rows + {n_cols} cols{' per half' if split else ''}) "
                   f"but {board['label']} has {len(pool)} recommended matrix pins")
            if need <= len(pool) + len(extra):
                msg += f"; possible using awkward pins {', '.join(extra[:need - len(pool)])}"
                pool += extra
                warnings.append(msg)
            else:
                errors.append(msg + ". Fold the matrix (squarer rows×cols) or use a bigger controller")
        row_pins = pool[:rows_needed]
        col_pins = pool[rows_needed:rows_needed + n_cols]
        plan = {"rows": row_pins, "cols": col_pins, "split_link": link, "source": "suggested",
                "pins_used": len(row_pins) + len(col_pins), "pins_available": len(pool)}
        if file_pins:
            # Board is (probably) already wired: the file's pins are the truth — check them, don't replace them.
            errors[:] = [e for e in errors if not e.startswith("Need ")]
            warnings[:] = [w for w in warnings if not w.startswith("Need ")]
            fr, fc = list(file_pins.get("rows", [])), list(file_pins.get("cols", []))
            known = set(board["pins"]) | set(board.get("extra", []))
            for kind, pins in (("row", fr), ("col", fc)):
                for p in pins:
                    if p in board.get("reserved", {}):
                        errors.append(f"{kind} pin {p} is reserved on {board['label']}: {board['reserved'][p]}")
                    elif p in board.get("extra", []):
                        warnings.append(f"{kind} pin {p} is an awkward pin on {board['label']} (see notes)")
                    elif p not in known and p != "NO_PIN":
                        errors.append(f"{kind} pin {p} is not a usable GPIO on {board['label']}")
            dup = {p for p in fr + fc if (fr + fc).count(p) > 1 and p != "NO_PIN"}
            if dup:
                errors.append(f"Pins used twice in matrix_pins: {', '.join(sorted(dup))}")
            if link and link in fr + fc:
                errors.append(f"Split link pin {link} is also used in the matrix")
            if len(fr) != rows_needed:
                errors.append(f"matrix_pins.rows has {len(fr)} pins but the layout uses {rows_needed} rows"
                              + (" per half" if split else ""))
            if len(fc) != n_cols:
                errors.append(f"matrix_pins.cols has {len(fc)} pins but the layout uses {n_cols} columns")
            plan.update(rows=fr, cols=fc, source="file", pins_used=len(fr) + len(fc))
    return {"errors": errors, "warnings": warnings, "rows": n_rows, "cols": n_cols,
            "rows_per_half": rph if split else None, "plan": plan}


# ─────────────────────────────── outputs ────────────────────────────────

def annotate_kle(raw, keys):
    """Rewrite KLE raw rows with "row,col" in legend position 0 (VIA convention)."""
    out, it, dropped = [], iter(keys), 0
    in_a = 4
    for row in raw:
        if isinstance(row, dict):
            out.append(copy.deepcopy(row))
            continue
        new_row = []
        for item in row:
            if isinstance(item, dict):
                d = copy.deepcopy(item)
                if "a" in d:
                    in_a = int(d["a"])
                    if d["a"] not in (0, 4):
                        d["a"] = 4  # keep legend position 0 addressable
                new_row.append(d)
            elif isinstance(item, str):
                k = next(it)
                labels = list(k["labels"])
                if k["matrix"] and not k["ghost"] and not k["decal"]:
                    if labels[0] and not RC_RE.match(labels[0]):
                        # keep the old top-left legend visible: move it to the first free spot
                        free = next((p for p in (4, 1, 2, 6, 7, 3, 5) if not labels[p]), None)
                        if free is not None:
                            labels[free] = labels[0]
                    labels[0] = f"{k['matrix'][0]},{k['matrix'][1]}"
                out_a = in_a if in_a in (0, 4) else 4
                s, d = encode_labels(labels, out_a)
                dropped += d
                new_row.append(s)
            else:
                new_row.append(item)
        out.append(new_row)
    return out, dropped


def kle_from_keys(keys):
    rows = []
    for k in matrix_keys(keys):
        props = {"r": k["r"], "rx": k["rx"], "ry": k["ry"], "x": round(k["x"] - k["rx"], 4),
                 "y": round(k["y"] - k["ry"], 4)}
        if k["w"] != 1:
            props["w"] = k["w"]
        if k["h"] != 1:
            props["h"] = k["h"]
        legend = f"{k['matrix'][0]},{k['matrix'][1]}" if k["matrix"] else ""
        if k["legend"] and not RC_RE.match(k["legend"]):
            legend += "\n\n\n\n\n\n\n\n\n" + k["legend"]  # raw line 9 → position 4 (centre)
        rows.append([props, legend])
    return rows


def build_output(fmt, layout, keys, res, board, split, args):
    name = args.name or layout["meta"].get("keyboard_name") or layout["meta"].get("name") or "handwired"
    if fmt in ("kle", "via"):
        if layout["raw"] is not None:
            kle, dropped = annotate_kle(layout["raw"], keys)
            if dropped:
                res["warnings"].append(f"{dropped} legends in positions 9/11 could not be kept after re-aligning to a=4")
        else:
            kle = kle_from_keys(keys)
        if fmt == "kle":
            return kle
        via = copy.deepcopy(layout["meta"]) if layout["kind"] == "via" else {
            "name": name, "vendorId": "0xFEED", "productId": "0x0001"}
        via.setdefault("layouts", {})
        via["layouts"]["keymap"] = kle
        via["matrix"] = {"rows": res["rows"] if not split else 2 * res["rows_per_half"], "cols": res["cols"]}
        return via
    if fmt == "qmk":
        if not board:
            raise ValueError("--format qmk needs --board")
        plan = res["plan"]
        kb = {
            "keyboard_name": name, "manufacturer": "handwired", "maintainer": "handwired",
            "usb": {"vid": "0xFEED", "pid": "0x0001", "device_version": "1.0.0"},
            "diode_direction": args.diode.upper(),
            "matrix_pins": {"rows": plan["rows"], "cols": plan["cols"]},
            "features": {"bootmagic": True, "extrakey": True, "mousekey": True},
            "layouts": {"LAYOUT": {"layout": []}},
        }
        kb.update({k: v for k, v in board.get("qmk", {}).items()})
        if split:
            drv = "vendor" if board["mcu"] == "RP2040" else "bitbang"
            kb["split"] = {"enabled": True, "serial": {"driver": drv, "pin": plan["split_link"]}}
        for k in matrix_keys(keys):
            e = {"matrix": k["matrix"], "x": round(k["x"], 3), "y": round(k["y"], 3)}
            for f, d in (("w", 1), ("h", 1), ("r", 0), ("rx", 0), ("ry", 0)):
                if k[f] != d:
                    e[f] = round(k[f], 3)
            if k["legend"]:
                e["label"] = k["legend"]
            kb["layouts"]["LAYOUT"]["layout"].append(e)
        return kb
    if fmt == "zmk":
        if not board or "pro_micro_index" not in board:
            raise ValueError("--format zmk needs a ZMK board (e.g. --board nice_nano_v2)")
        plan, idx = res["plan"], board["pro_micro_index"]
        def gp(p, flags):
            return f"<&pro_micro {idx[p]} {flags}>" if p in idx else f"<&gpio{p[1]} {int(p.split('.')[1])} {flags}>"
        rin = "(GPIO_ACTIVE_HIGH | GPIO_PULL_DOWN)" if args.diode == "col2row" else "GPIO_ACTIVE_HIGH"
        cin = "GPIO_ACTIVE_HIGH" if args.diode == "col2row" else "(GPIO_ACTIVE_HIGH | GPIO_PULL_DOWN)"
        rph = res["rows_per_half"] or res["rows"]
        mk = matrix_keys(keys)
        def zrc(k):  # ZMK: right half goes to extra columns, not rows
            r, c = k["matrix"]
            return (r - rph, c + res["cols"]) if split and r >= rph else (r, c)
        cols_total = res["cols"] * (2 if split else 1)
        rc = " ".join(f"RC({a},{b})" for a, b in (zrc(k) for k in mk))
        txt = [
            "/* kscan — goes in <shield>.dtsi (or <shield>_left/_right.overlay for splits) */",
            "kscan0: kscan {",
            '    compatible = "zmk,kscan-gpio-matrix";',
            f'    diode-direction = "{args.diode}";',
            "    wakeup-source;",
            "    row-gpios\n        = " + "\n        , ".join(gp(p, rin) for p in plan["rows"]) + "\n        ;",
            "    col-gpios\n        = " + "\n        , ".join(gp(p, cin) for p in plan["cols"]) + "\n        ;",
            "};",
            "",
            "default_transform: keymap_transform_0 {",
            '    compatible = "zmk,matrix-transform";',
            f"    columns = <{cols_total}>;",
            f"    rows = <{rph}>;",
            f"    map = < {rc} >;",
            "};",
        ]
        if split:
            txt += ["", f"/* <shield>_right.overlay */\n&default_transform {{ col-offset = <{res['cols']}>; }};"]
        return "\n".join(txt)
    raise ValueError(f"Unknown format {fmt}")


def print_report(keys, res, board, split, route_info):
    mk = matrix_keys(keys)
    print(f"Keys: {len(mk)}  Matrix: {res.get('rows')} rows × {res.get('cols')} cols"
          + (f"  (split: {res['rows_per_half']} rows per half)" if split else ""))
    if route_info and split:
        print(f"Split at x≈{route_info['split_at']}u  left {route_info['left'][0]}×{route_info['left'][1]}, "
              f"right {route_info['right'][0]}×{route_info['right'][1]}")
    plan = res.get("plan")
    if plan:
        print(f"Board: {board['label']}  pins used {plan['pins_used']}/{plan['pins_available']}"
              + ("  (pins from file)" if plan.get("source") == "file" else "  (suggested pins)")
              + (f"  split link: {plan['split_link']}" if plan["split_link"] else ""))
    rph = res.get("rows_per_half") or res.get("rows") or 0
    by_row, by_col = {}, {}
    for k in mk:
        if k["matrix"]:
            by_row.setdefault(k["matrix"][0], []).append(k)
            by_col.setdefault(k["matrix"][1], []).append(k)
    print("\nRows:")
    for r in sorted(by_row):
        pin = plan["rows"][r % rph] if plan and r % rph < len(plan["rows"]) else "-"
        side = (" (R)" if r >= rph else " (L)") if split else ""
        ks = sorted(by_row[r], key=lambda k: k["cx"])
        print(f"  row {r:>2}{side} → {pin:<6} {', '.join(key_name(k) for k in ks)}")
    print("Columns:")
    for c in sorted(by_col):
        pin = plan["cols"][c] if plan and c < len(plan["cols"]) else "-"
        ks = sorted(by_col[c], key=lambda k: (k["cx"] > (route_info or {}).get("split_at", 1e9), k["cy"]))
        print(f"  col {c:>2} → {pin:<6} {', '.join(key_name(k) for k in ks)}")
    for w in res["warnings"]:
        print(f"WARNING: {w}")
    for e in res["errors"]:
        print(f"ERROR: {e}")
    print("OK — no errors" if not res["errors"] else f"{len(res['errors'])} error(s)")


# ──────────────────────────────── CLI ───────────────────────────────────

def parse_rc(s):
    m = RC_RE.match(s)
    if not m:
        raise argparse.ArgumentTypeError(f"expected row,col — got {s!r}")
    return int(m.group(1)), int(m.group(2))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("boards", help="list controller profiles")
    for name in ("route", "validate"):
        s = sub.add_parser(name)
        s.add_argument("layout")
        s.add_argument("--board", help="board id (see `boards`)")
        s.add_argument("--split", action="store_true", help="split keyboard (QMK convention: right rows offset)")
        s.add_argument("--split-link", help="pin reserved for the wired split link (default: board's)")
        s.add_argument("--firmware", choices=["qmk", "vial", "zmk"])
        s.add_argument("--unlock", nargs="*", type=parse_rc, help="Vial unlock combo keys, e.g. 0,0 0,1")
        s.add_argument("--layout-name", help="QMK layout to use (default: first)")
        s.add_argument("--diode", choices=["col2row", "row2col"], default="col2row")
        s.add_argument("--out", help="write output file (default: stdout for zmk)")
        s.add_argument("--format", choices=["kle", "via", "qmk", "zmk"],
                       help="output format (default: same kind as input; QMK input → via)")
        s.add_argument("--name", help="keyboard name for generated files")
        s.add_argument("--json", action="store_true", help="print machine-readable report")
        if name == "route":
            s.add_argument("--mirror-right", action="store_true",
                           help="number right-half columns from its outer edge (mirrored handwiring)")
            s.add_argument("--row-tol", type=float, default=0.6, help="row band tolerance in u")
            s.add_argument("--col-tol", type=float, default=0.55, help="column band tolerance in u")
    args = p.parse_args(argv)
    boards = load_boards()

    if args.cmd == "boards":
        for bid, b in boards.items():
            flag = "" if b.get("verified", True) else "  [pins unverified]"
            print(f"{bid:<14} {b['label']}  — {len(b['pins'])} pins (+{len(b.get('extra', []))} extra), "
                  f"{'/'.join(b['firmware'])}{flag}")
            print(f"{'':<14} {b['notes']}")
        return 0

    board = None
    if args.board:
        if args.board not in boards:
            p.error(f"unknown board {args.board!r}; choose from {', '.join(boards)}")
        board = boards[args.board]
    layout = load_layout(args.layout, args.layout_name)
    keys = layout["keys"]
    route_info = None
    if args.cmd == "route":
        route_info = route(keys, args.split, args.mirror_right, args.row_tol, args.col_tol)
    file_pins = layout["meta"].get("matrix_pins") if args.cmd == "validate" else None
    if file_pins and args.split is False and layout["meta"].get("split", {}).get("enabled"):
        args.split = True
    res = analyse(keys, board, args.split, args.unlock, args.firmware, args.split_link, file_pins)

    fmt = args.format or (None if args.cmd == "validate" and not args.out else
                          {"kle": "kle", "via": "via", "qmk": "via"}[layout["kind"]])
    output = None
    if fmt and (args.out or fmt == "zmk"):
        if res.get("plan") is None and fmt in ("qmk", "zmk"):
            p.error(f"--format {fmt} needs --board")
        output = build_output(fmt, layout, keys, res, board, args.split, args)

    if args.json:
        mk = matrix_keys(keys)
        print(json.dumps({**{k: v for k, v in res.items()}, "route": route_info,
                          "keys": [{"legend": key_name(k), "matrix": k["matrix"],
                                    "x": round(k["x"], 3), "y": round(k["y"], 3)} for k in mk]}, indent=2))
    else:
        print_report(keys, res, board, args.split, route_info)

    if output is not None:
        text = output if isinstance(output, str) else json.dumps(output, indent=2)
        if args.out:
            with open(args.out, "w") as f:
                f.write(text + "\n")
            print(f"\nWrote {fmt} → {args.out}", file=sys.stderr)
        else:
            print("\n" + text)
    return 1 if res["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
