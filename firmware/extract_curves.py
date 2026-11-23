#!/usr/bin/env python3
"""Extract the per-switch-type travel curves from a Jet75-II firmware image.

The firmware converts the normalized sensor value (stream bytes 4-5, 0..1600) into travel by a
binary search in a table of 16-bit thresholds per switch type: travel (0.01 mm) = index + 1 of
the last entry <= value (function fn_bd6c, table at app address 0x1403C, 800 bytes per type;
max travel per type at 0x13FEC, 8 bytes per type). See open-he-mchose/docs, keyboards/jet75-ii/switches-and-travel.md.

    python3 firmware/extract_curves.py firmware.bin > curves.json      (MIT licence)
The extracted tables are vendor data: keep them locally, do not commit them.
"""
import json, os, struct, sys

APP_BASE, MAX_TABLE, CURVE_TABLE, CURVE_STRIDE, TYPES = 0x5000, 0x13FEC, 0x1403C, 800, 10


def extract(fw):
    d = open(fw, "rb").read()
    out = {"source": os.path.basename(fw), "types": {}}
    for t in range(TYPES):
        mx = struct.unpack_from("<H", d, MAX_TABLE - APP_BASE + 8 * t)[0]
        curve = list(struct.unpack_from("<%dH" % mx, d, CURVE_TABLE - APP_BASE + CURVE_STRIDE * t))
        dips = [i for i in range(len(curve) - 1) if curve[i] > curve[i + 1]]
        if len(dips) > 3 or curve[-1] < 1000:
            raise ValueError("curve %d does not look like a travel curve - wrong firmware image?" % t)
        if dips:  # V116 type 7 has one bad entry (index 315); keep raw data, note it
            print("warning: type %d curve not monotonic at %s (kept as in firmware)" % (t, dips), file=sys.stderr)
        out["types"][str(t)] = {"max_travel": mx, "curve": curve}
    return out


def main():
    data = extract(sys.argv[1])
    json.dump(data, sys.stdout)
    print("", file=sys.stdout)
    print(", ".join("type %s: %d" % (k, v["max_travel"]) for k, v in data["types"].items()), file=sys.stderr)


if __name__ == "__main__":
    main()
