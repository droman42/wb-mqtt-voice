#!/usr/bin/env python3
"""BUG-14: make the bundled onnxruntime armv7 `.so` loadable on a 4 KB-page kernel.

sherpa-onnx's prebuilt armv7 `libonnxruntime.so` has `PT_LOAD` segments with `p_align = 0x10000`
(64 KB). On the Wirenboard 7 (armv7, 4 KB pages) the dynamic loader then rejects it with
`ELF load command address/offset not properly aligned` (the segment's file offset and virtual
address are not congruent mod 64 KB). Reducing `p_align` to `0x1000` (4 KB) — exactly what linking
with `-z max-page-size=4096` would have produced — satisfies the loader; the mapping is unchanged.

Run at Docker build time over the installed venv:  python patch_onnx_align.py /opt/venv
Pure stdlib (struct), so it runs under any Python on the build host. Idempotent.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

_PT_LOAD = 1
_ELF32 = 1


def patch_so(path: Path) -> int:
    """Rewrite PT_LOAD p_align 0x10000 -> 0x1000 in an ELF32 shared object. Returns #segments changed."""
    b = bytearray(path.read_bytes())
    if b[:4] != b"\x7fELF" or b[4] != _ELF32:
        return 0  # not a 32-bit ELF (nothing to do — e.g. 64-bit builds are unaffected)
    e_phoff = struct.unpack_from("<I", b, 0x1c)[0]
    e_phentsize = struct.unpack_from("<H", b, 0x2a)[0]
    e_phnum = struct.unpack_from("<H", b, 0x2c)[0]
    changed = 0
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        if struct.unpack_from("<I", b, off)[0] == _PT_LOAD:
            align_off = off + 28  # ELF32 program header: p_align is the last 4-byte field
            if struct.unpack_from("<I", b, align_off)[0] == 0x10000:
                struct.pack_into("<I", b, align_off, 0x1000)
                changed += 1
    if changed:
        path.write_bytes(b)
    return changed


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path("/opt/venv")
    sos = sorted(root.rglob("libonnxruntime.so*"))
    if not sos:
        print(f"patch_onnx_align: no libonnxruntime.so under {root} (nothing to patch)")
        return 0
    total = 0
    for so in sos:
        n = patch_so(so)
        total += n
        print(f"patch_onnx_align: {so} -> patched {n} PT_LOAD segment(s)")
    return 0 if total or not sos else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
