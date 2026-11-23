#!/usr/bin/env python3
"""List or extract resources of a Windows PE file (e.g. a vendor firmware updater).

MCHOSE's "FirmwareUpdateTool" executables embed the raw firmware images as resources of type "BIN".

    python3 firmware/extract_pe_resources.py Updater.exe                 # list all resources
    python3 firmware/extract_pe_resources.py Updater.exe --type BIN out/  # extract BIN resources

Stdlib only, no execution of the file. MIT licence.
"""
import argparse, hashlib, os, struct, sys


def sections(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    if d[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE file")
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    opt_size = struct.unpack_from("<H", d, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", d, opt)[0]
    dd = opt + (96 if magic == 0x10B else 112)          # data directories (PE32 / PE32+)
    rsrc_rva = struct.unpack_from("<I", d, dd + 2 * 8)[0]
    secs = []
    s = opt + opt_size
    for i in range(nsec):
        vsize, va, rawsize, raw = struct.unpack_from("<IIII", d, s + 40 * i + 8)
        secs.append((va, max(vsize, rawsize), raw))
    return rsrc_rva, secs


def rva2off(secs, rva):
    for va, size, raw in secs:
        if va <= rva < va + size:
            return rva - va + raw
    raise ValueError("RVA %#x not in any section" % rva)


def walk(d, base, off, path, out):
    named, ids = struct.unpack_from("<HH", d, off + 12)
    for i in range(named + ids):
        name, entry = struct.unpack_from("<II", d, off + 16 + 8 * i)
        if name & 0x80000000:
            p = base + (name & 0x7FFFFFFF)
            n = struct.unpack_from("<H", d, p)[0]
            name = d[p + 2:p + 2 + 2 * n].decode("utf-16le")
        if entry & 0x80000000:
            walk(d, base, base + (entry & 0x7FFFFFFF), path + [name], out)
        else:
            rva, size = struct.unpack_from("<II", d, base + entry)
            out.append((path + [name], rva, size))


def resources(path):
    d = open(path, "rb").read()
    rsrc_rva, secs = sections(d)
    base = rva2off(secs, rsrc_rva)
    out = []
    walk(d, base, base, [], out)
    return d, secs, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pe")
    ap.add_argument("--type", help="resource type to extract, e.g. BIN or 10 (RCDATA)")
    ap.add_argument("outdir", nargs="?")
    a = ap.parse_args()
    d, secs, res = resources(a.pe)
    for path, rva, size in res:
        typ, name = str(path[0]), str(path[1]) if len(path) > 1 else "?"
        blob = d[rva2off(secs, rva):rva2off(secs, rva) + size]
        line = "%-10s %-28s %8d bytes  sha256 %s  head %s" % (typ, name, size, hashlib.sha256(blob).hexdigest()[:16], blob[:8].hex())
        if a.type and typ != a.type:
            continue
        print(line)
        if a.type and a.outdir:
            os.makedirs(a.outdir, exist_ok=True)
            fn = os.path.join(a.outdir, "%s_%s.bin" % (typ, name))
            open(fn, "wb").write(blob)
            print("  -> %s" % fn)


if __name__ == "__main__":
    sys.exit(main())
