#!/usr/bin/env python3
"""Record what a keyboard sends (raw HID input reports of every hidraw node) next to what Linux makes of it
(key events from /dev/input), then summarise. Used to prove the Jet75-II NKRO descriptor bug.

    python3 usb/hidlog.py record 41e4:211a 40 log.txt     # 40 seconds; press keys meanwhile
    python3 usb/hidlog.py analyze log.txt

Needs read access to the keyboard's /dev/hidraw* and /dev/input/event* (e.g. groups plugdev/input).
The log contains everything typed during the recording — do not publish it. Stdlib only. MIT licence.
"""
import glob, os, select, struct, sys, time
from collections import Counter


def nodes(vid, pid):
    raw, ev = {}, []
    tag = "%08X:%08X" % (vid, pid)
    for n in glob.glob("/sys/class/hidraw/hidraw*"):
        try:
            if tag in open(n + "/device/uevent").read():
                iface = os.path.basename(os.path.dirname(os.path.realpath(n + "/device")))
                raw["/dev/" + os.path.basename(n)] = iface
        except OSError:
            pass
    for e in glob.glob("/sys/class/input/event*"):
        try:
            v = int(open(e + "/device/id/vendor").read(), 16)
            p = int(open(e + "/device/id/product").read(), 16)
            if (v, p) == (vid, pid) and "virtual" not in open(e + "/device/name").read().lower():
                ev.append("/dev/input/" + os.path.basename(e))
        except OSError:
            pass
    return raw, ev


def record(vidpid, dur, path):
    vid, pid = (int(x, 16) for x in vidpid.split(":"))
    raw, ev = nodes(vid, pid)
    rfd = {}
    for dev, iface in raw.items():
        try:
            rfd[os.open(dev, os.O_RDONLY | os.O_NONBLOCK)] = iface
        except OSError as e:
            print("skip %s: %s" % (dev, e), file=sys.stderr)
    efd = [os.open(p, os.O_RDONLY | os.O_NONBLOCK) for p in ev]
    print("recording %g s: hidraw %s, input %s" % (dur, sorted(rfd.values()), ev), flush=True)
    out, t0 = open(path, "w"), time.monotonic()
    while time.monotonic() - t0 < dur:
        for fd in select.select(list(rfd) + efd, [], [], 0.2)[0]:
            t = time.monotonic() - t0
            if fd in rfd:
                out.write("%.3f RAW %s %s\n" % (t, rfd[fd], os.read(fd, 64).hex()))
            else:
                d = os.read(fd, 24 * 64)
                for k in range(0, len(d) - 23, 24):
                    _, _, ty, code, val = struct.unpack("<qqHHi", d[k:k + 24])
                    if ty == 1 and val in (0, 1):
                        out.write("%.3f EV %d %d\n" % (t, code, val))
        out.flush()


def analyze(path):
    lines = [l.split() for l in open(path)]
    per_iface = Counter(l[2] for l in lines if l[1] == "RAW")
    print("raw input reports per interface:", dict(per_iface))
    held, mx, presses = set(), 0, Counter()
    for l in lines:
        if l[1] == "EV":
            code, val = int(l[2]), int(l[3])
            if val:
                held.add(code)
                presses[code] += 1
            else:
                held.discard(code)
            mx = max(mx, len(held))
    print("Linux key presses: %d (distinct keys %d), max keys held at once: %d" % (sum(presses.values()), len(presses), mx))
    print("most pressed (Linux keycodes):", presses.most_common(10))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "record" and len(sys.argv) == 5:
        record(sys.argv[2], float(sys.argv[3]), sys.argv[4])
    elif len(sys.argv) == 3 and sys.argv[1] == "analyze":
        analyze(sys.argv[2])
    else:
        sys.exit(__doc__)
