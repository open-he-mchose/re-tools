# re-tools — reverse-engineering tools for MCHOSE magnetic keyboards

> **⚠️ AI-generated content.** The tools in this repository were written almost entirely by an AI assistant
> (Claude, by Anthropic). The maintainer directed the work and used them on real hardware and files, but did
> not write the code by hand. Read a script before running it, and please report mistakes.

**Unofficial community project. Not affiliated with or endorsed by MCHOSE.** No vendor firmware, software or
code is distributed here — the tools work on copies you obtain yourself, and their output (decompiled code,
extracted tables, saved web-driver files) is vendor material: keep it local, do not commit or publish it.

Documentation of the results: [open-he-mchose/docs](https://github.com/open-he-mchose/docs)
(methods in [reverse-engineering/](https://github.com/open-he-mchose/docs/tree/main/reverse-engineering)).

## Contents

| Path | What it does | Tested on |
|---|---|---|
| [`webdriver/fetch_cizhou.py`](webdriver/fetch_cizhou.py) | Save a local copy of the magnetic-keyboard web driver (`/cizhou/`): page, all JS chunks incl. lazily loaded ones, English locale | runtime-map parsing on a 2026-11 copy |
| [`webdriver/webpack_module.py`](webdriver/webpack_module.py) | Cut one webpack module out of minified chunks; find modules mentioning a name | 2026-11 copy |
| [`firmware/extract_pe_resources.py`](firmware/extract_pe_resources.py) | List / extract resources of a Windows updater (firmware images are `BIN` resources) | Jet75-II updater V115 |
| [`firmware/make_elf.py`](firmware/make_elf.py) | Wrap a raw firmware image into an ELF (base `0x5000`, RAM, function symbols) for Ghidra | Jet75-II V116 (276 functions) |
| [`firmware/extract_curves.py`](firmware/extract_curves.py) | Extract max-travel and travel-curve tables (switch types 0–9) as JSON | Jet75-II V116 |
| [`ghidra/`](ghidra/README.md) | Ghidra language `RISCV:LE:32:wch-qingke` (WCH QingKe "XW" instructions) + headless decompile-all script | Ghidra 12.2 |
| [`usb/hidlog.py`](usb/hidlog.py) | Log raw HID input reports next to Linux key events and summarise (keys lost, max keys held) | Jet75-II |

Everything is Python 3 standard library only (plus Ghidra for `ghidra/`). Firmware offsets and table
addresses are Jet75-II values; other models need checking.

## Typical workflow for a new model

```sh
# 1. web driver: command set, structures, device table
python3 webdriver/fetch_cizhou.py ~/re/webdriver
python3 webdriver/webpack_module.py ~/re/webdriver --grep getFuncConfig
#    device table → docs repo: python3 scripts/extract_devices.py <chunk with module 83050>

# 2. firmware: from the Windows updater or the update URL in the device table
python3 firmware/extract_pe_resources.py Updater.exe --type BIN ~/re/fw
python3 firmware/make_elf.py ~/re/fw/BIN_134.bin ~/re/fw/app.elf
#    then Ghidra with the language from ghidra/ (see ghidra/README.md)

# 3. hardware: compare what the keyboard sends with what the OS reports
python3 usb/hidlog.py record 41e4:211a 30 ~/re/log.txt && python3 usb/hidlog.py analyze ~/re/log.txt
```

Safety: these tools only read files or listen to the keyboard; none of them writes to a keyboard.
Logs from `usb/hidlog.py` contain everything typed during the recording.

## Licence

MIT, see [LICENSE](LICENSE).
