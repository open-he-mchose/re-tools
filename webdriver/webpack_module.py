#!/usr/bin/env python3
"""Cut one webpack module out of minified chunks and make it readable.

    python3 webdriver/webpack_module.py CHUNKS_DIR 45474            # find module 45474 in any chunk, print it
    python3 webdriver/webpack_module.py CHUNKS_DIR 45474 --raw      # without line breaks
    python3 webdriver/webpack_module.py CHUNKS_DIR --grep setAllKeyTravel   # which modules mention a name

Useful module ids in the 2026-11 build of the cizhou app: 83050 device table, 45474 glw channel
(framing/commands), 14905 glw SDK (struct serialisers), 82398 transport base, 53542/86369 qhw.
Stdlib only. MIT licence.
"""
import argparse, glob, os, re, sys


def module_text(text, mid):
    m = re.search(r"(?<![\w.])%s:function\(\w,\w,\w\)\{" % mid, text)
    if not m:
        return None
    k, depth, quote = m.end() - 1, 0, None
    while k < len(text):
        c = text[k]
        if quote:
            if c == "\\":
                k += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'`":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[m.start():k + 1]
        k += 1
    return None


def modules_of(text):
    return re.findall(r"(?<![\w.])(\d+):function\(\w,\w,\w\)\{", text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chunks")
    ap.add_argument("module", nargs="?")
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--grep")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.chunks, "**", "*.js"), recursive=True))
    if a.grep:
        for f in files:
            t = open(f, encoding="utf-8", errors="replace").read()
            for mid in modules_of(t):
                body = module_text(t, mid)
                if body and a.grep in body:
                    print("%s  module %s  (%d bytes)" % (os.path.relpath(f, a.chunks), mid, len(body)))
        return
    for f in files:
        t = open(f, encoding="utf-8", errors="replace").read()
        body = module_text(t, a.module)
        if body:
            print("// %s" % os.path.relpath(f, a.chunks), file=sys.stderr)
            print(body if a.raw else re.sub(r"(;|\}(?=async |function |class ))", r"\1\n", body))
            return
    sys.exit("module %s not found" % a.module)


if __name__ == "__main__":
    main()
