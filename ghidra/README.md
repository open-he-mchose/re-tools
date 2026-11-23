# Ghidra language for the WCH QingKe core

*AI-generated (Claude, Anthropic); checked on real hardware only where marked **verified**. Report errors via issues.*

Adds the language `RISCV:LE:32:wch-qingke` = RV32IMAFC + the WCH "XW" compressed byte/halfword loads and
stores (encodings in the [docs](https://github.com/open-he-mchose/docs/blob/main/reverse-engineering/firmware-analysis.md#wch-qingke-xw-instructions)).
`FPSIZE "32"` drops the D-extension compressed instructions whose encodings XW reuses. The stock RISC-V
languages are not modified. Encodings were inferred from code context and produced consistent
decompilation of the Jet75-II firmware (~290 functions); they are not checked against WCH documentation.

| File | Purpose |
|---|---|
| `riscv.wch.slaspec` | language entry point (includes the stock RISC-V `.sinc` files + `riscv.xwchc.sinc`) |
| `riscv.xwchc.sinc` | the XW instructions |
| `riscv.wch.ldefs` | language definition (`RISCV:LE:32:wch-qingke`, compiler spec `gcc`) |
| `DecompileAllToFile.java` | headless post-script: decompile every function into one C file |

## Install (Ghidra 12.x)

```sh
L=<ghidra>/Ghidra/Processors/RISCV/data/languages
cp riscv.wch.slaspec riscv.xwchc.sinc riscv.wch.ldefs "$L"/
(cd "$L" && ../../../../../support/sleigh riscv.wch.slaspec)        # builds riscv.wch.sla
```

## Use

```sh
python3 firmware/make_elf.py firmware.bin firmware.elf             # base 0x5000, function symbols
<ghidra>/support/analyzeHeadless /tmp/proj fw -import firmware.elf \
    -processor RISCV:LE:32:wch-qingke -cspec gcc \
    -scriptPath ghidra -postScript DecompileAllToFile.java firmware.c
```

Licence of these files: MIT (they are new work, not copies of Ghidra's SLEIGH sources; they `@include`
Ghidra's own RISC-V files at build time).
