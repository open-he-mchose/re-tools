#!/usr/bin/env python3
"""Save a local copy of the magnetic-keyboard part ("cizhou") of the MCHOSE web driver for reading.

Downloads /cizhou/index.html, every chunk it references, the lazily loaded chunks listed in the webpack
runtime, and the English locale. The files are the vendor's code: keep them local, do not redistribute.

    python3 webdriver/fetch_cizhou.py out/              # default base https://www.mchose.com.cn/cizhou

Stdlib only. MIT licence.
"""
import argparse, os, re, sys, urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def save(out, base, rel, data):
    path = os.path.join(out, rel.lstrip("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(data)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--base", default="https://www.mchose.com.cn/cizhou")
    a = ap.parse_args()
    base = a.base.rstrip("/")
    html = get(base + "/index.html")
    save(a.out, base, "index.html", html)
    text = html.decode("utf-8", "replace")
    chunks = set(re.findall(r"(?:/_next/)?(static/chunks/[^\"'`\s\\]+\.js)", text))
    done, fails = set(), 0
    queue = sorted(chunks)
    while queue:
        rel = queue.pop(0)
        if rel in done:
            continue
        done.add(rel)
        try:
            data = get("%s/_next/%s" % (base, rel))
        except Exception as e:  # noqa: BLE001 - report and continue
            print("FAIL", rel, e, file=sys.stderr)
            fails += 1
            continue
        save(a.out, base, "_next/" + rel, data)
        if "/webpack-" in rel:   # runtime: chunk id -> name/hash map of lazy chunks
            t = data.decode("utf-8", "replace")
            queue.extend(re.findall(r'"(static/chunks/[\w.\-]+\.js)"', t))      # explicit N===e?"…" entries
            m = re.search(r'static/chunks/"\+(?:\(\{([^}]*)\}\[e\]\|\|e\)|e)\+"\."\+\(\{([^}]*)\}\)\[e\]\+"\.js"', t)
            if m:
                names = dict(re.findall(r'(\d+):"([^"]+)"', m.group(1) or ""))
                for cid, h in re.findall(r'(\d+):"([0-9a-f]+)"', m.group(2)):
                    queue.append("static/chunks/%s.%s.js" % (names.get(cid, cid), h))
    for lang in ("en",):
        try:
            save(a.out, base, "locales/%s/common.json" % lang, get("%s/locales/%s/common.json" % (base, lang)))
        except Exception as e:  # noqa: BLE001
            print("FAIL locale", lang, e, file=sys.stderr)
    print("saved %d chunks to %s (%d failed)" % (len(done) - fails, a.out, fails))


if __name__ == "__main__":
    main()
