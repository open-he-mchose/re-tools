#!/usr/bin/env python3
"""Wrap a raw Jet75-II application image into a RISC-V ELF for Ghidra / REA.

    python3 firmware/make_elf.py update_jet75II_v116.bin jet75II_v116_b5000.elf     (MIT licence)

- load address 0x5000 (the bootloader occupies flash below; verified by the command jump table at
  0x13840 whose 243 entries all fall inside the image only for this base)
- RAM segment 0x20000000 (64 KiB, NOBITS)
- e_flags = RVC | soft-float, .riscv.attributes = rv32imac (what REA's Ghidra lane accepts)
- FUNC symbols for every direct call target (jal ra / c.jal, found with binutils objdump) and every
  vector table entry, so Ghidra's auto-analysis finds the interrupt handlers and called functions

The CPU is a WCH QingKe core: its "XW" compressed byte/half loads/stores reuse the c.fld/c.fsd
encodings, so for readable decompilation open the ELF with the language from ghidra/
(RISCV:LE:32:wch-qingke), see ghidra/README.md.
"""
import re, struct, subprocess, sys

BASE = 0x5000
RAM_BASE, RAM_SIZE = 0x20000000, 0x10000


def function_starts(binf, size):
    dis = subprocess.run(["objdump", "-D", "-b", "binary", "-m", "riscv:rv32", "-M", "no-aliases", binf],
                         capture_output=True, text=True, check=True).stdout
    starts, targets = set(), set()
    for line in dis.splitlines():
        m = re.match(r"\s*([0-9a-f]+):\s+([0-9a-f]+)\s+(\S+)\s*(.*)", line)
        if not m:
            continue
        a, op, args = int(m.group(1), 16), m.group(3), m.group(4)
        starts.add(a)
        if (op == "jal" and args.startswith("ra,")) or op == "c.jal":
            t = re.search(r"0x([0-9a-f]+)", args)
            if t:
                targets.add(int(t.group(1), 16))
    fn = {t for t in targets if t in starts and t % 2 == 0 and t < size}
    d = open(binf, "rb").read()
    for off in range(0x38, 0x200, 4):  # vector table entries are absolute addresses
        v = struct.unpack_from("<I", d, off)[0]
        if BASE + 0x100 <= v < BASE + size and v % 2 == 0:
            fn.add(v - BASE)
    return sorted(BASE + t for t in fn)


def build(src, dst):
    code = open(src, "rb").read()
    syms = [(a, "fn_%x" % a) for a in function_starts(src, len(code))]
    arch = b"rv32i2p1_m2p0_a2p1_c2p0\0"
    attrs = bytes([5]) + arch + bytes([4, 16])
    filesub = bytes([1]) + struct.pack("<I", 5 + len(attrs)) + attrs
    attrsec = b"A" + struct.pack("<I", 4 + 6 + len(filesub)) + b"riscv\0" + filesub
    strtab, symtab = b"\0", b"\0" * 16
    for a, n in syms:
        no = len(strtab)
        strtab += n.encode() + b"\0"
        symtab += struct.pack("<IIIBBH", no, a, 0, (1 << 4) | 2, 0, 1)
    names = [b"", b".text", b".bss", b".shstrtab", b".riscv.attributes", b".symtab", b".strtab"]
    shstr, noff = b"", []
    for n in names:
        noff.append(len(shstr))
        shstr += n + b"\0"
    ehsz, phsz, shsz = 52, 32, 40
    blobs, offs, cur = [code, attrsec, shstr, symtab, strtab], [], ehsz + 2 * phsz
    for b in blobs:
        cur = (cur + 3) & ~3
        offs.append(cur)
        cur += len(b)
    off_sh = (cur + 3) & ~3
    eh = b"\x7fELF" + bytes([1, 1, 1, 0]) + b"\0" * 8
    eh += struct.pack("<HHIIIIIHHHHHH", 2, 243, 1, BASE, ehsz, off_sh, 0x1, ehsz, phsz, 2, shsz, 7, 3)
    ph = struct.pack("<IIIIIIII", 1, offs[0], BASE, BASE, len(code), len(code), 5, 4)
    ph += struct.pack("<IIIIIIII", 1, 0, RAM_BASE, RAM_BASE, 0, RAM_SIZE, 6, 4)
    sh = b"\0" * shsz
    sh += struct.pack("<IIIIIIIIII", noff[1], 1, 6, BASE, offs[0], len(code), 0, 0, 4, 0)
    sh += struct.pack("<IIIIIIIIII", noff[2], 8, 3, RAM_BASE, 0, RAM_SIZE, 0, 0, 4, 0)
    sh += struct.pack("<IIIIIIIIII", noff[3], 3, 0, 0, offs[2], len(shstr), 0, 0, 1, 0)
    sh += struct.pack("<IIIIIIIIII", noff[4], 0x70000003, 0, 0, offs[1], len(attrsec), 0, 0, 1, 0)
    sh += struct.pack("<IIIIIIIIII", noff[5], 2, 0, 0, offs[3], len(symtab), 6, 1, 4, 16)
    sh += struct.pack("<IIIIIIIIII", noff[6], 3, 0, 0, offs[4], len(strtab), 0, 0, 1, 0)
    out = bytearray(off_sh)
    out[0:len(eh)] = eh
    out[ehsz:ehsz + len(ph)] = ph
    for b, o in zip(blobs, offs):
        out[o:o + len(b)] = b
    out += sh
    open(dst, "wb").write(out)
    print("%s: %d bytes, %d function symbols" % (dst, len(out), len(syms)))


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
