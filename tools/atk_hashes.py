#!/usr/bin/env python3
"""
atk_hashes.py - extract Anvil Toolkit's bone/string name dictionary.

Anvil names things by **CRC32 of the name**, so a skeleton stores `LeftForeArm`
as the number 220238864. ATK ships the reverse lookup as an embedded, compressed
resource (`AnvilToolkit.Resources.hashes.hl`) - roughly 276,000 names. This pulls
it out of *your own* ATK install and writes it as plain text, one name per line.

    python atk_hashes.py "E:\\Anvil Toolkit" -o hashes.txt

Then feed it to reflex3.py to see bone NAMES instead of numbers:

    python reflex3.py Watch_Skeleton.data --names hashes.txt

The dictionary is ATK's own data and is NOT redistributed with this repo - run
this against your own copy. Requires `Libs/fast-lzma2.dll` from the same install
(ATK compresses the resource with Fast-LZMA2 and P/Invokes that DLL itself).

⚠️ Coverage note: the list is built for ATK's primary games (the Assassin's Creed
line), so it resolves the **standard biped bones** GRB shares with them - Spine2,
LeftForeArm, Head - but NOT GRB's bespoke dangle-bone names (kilt panels, hair
strands, coat flaps). Roughly 4% of GRB's skeleton bone hashes resolve. The ones
that do are the useful ones: they tell you what a rig ATTACHES to.

READ-ONLY on the toolkit.

HOW IT WORKS: .NET manifest resources sit in the assembly's *Resources* data
directory as `[int32 length][bytes]`. This walks the PE headers to find that
directory (CLI header, data directory 14), then inside it looks for the length-
prefixed blob that Fast-LZMA2 both recognises and expands into a name list.
Confining the scan to that directory keeps it fast and avoids false positives
elsewhere in a 16 MB assembly.
"""
import ctypes, os, sys, struct

MIN_BLOB = 64 << 10           # ignore anything implausibly small
MAX_BLOB = 64 << 20
MAX_OUT = 256 << 20           # cap on a candidate's claimed decompressed size


def load_fl2(atk_dir):
    dll = os.path.join(atk_dir, "Libs", "fast-lzma2.dll")
    if not os.path.isfile(dll):
        raise SystemExit(f"  ! not found: {dll}\n    (pass the folder containing AnvilToolkit.exe)")
    try:
        os.add_dll_directory(os.path.dirname(dll))
    except Exception:
        pass
    fl2 = ctypes.CDLL(dll)
    fl2.FL2_findDecompressedSize.restype = ctypes.c_uint64
    fl2.FL2_findDecompressedSize.argtypes = [ctypes.c_char_p, ctypes.c_int64]
    fl2.FL2_decompressMt.restype = ctypes.c_int64
    fl2.FL2_decompressMt.argtypes = [ctypes.c_char_p, ctypes.c_int64,
                                     ctypes.c_char_p, ctypes.c_int64, ctypes.c_uint32]
    return fl2


def clr_resources_region(data):
    """(offset, size) of the assembly's Resources data directory, from the PE headers."""
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise SystemExit("  ! not a PE file")
    n_sections = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    dd = opt + (96 if magic == 0x10B else 112)          # PE32 vs PE32+
    clr_rva = struct.unpack_from("<I", data, dd + 14 * 8)[0]
    if not clr_rva:
        raise SystemExit("  ! no CLR header - not a .NET assembly")

    sections = []
    sec = pe + 24 + opt_size
    for i in range(n_sections):
        o = sec + i * 40
        vsize, va, rawsize, rawptr = struct.unpack_from("<IIII", data, o + 8)
        sections.append((va, max(vsize, rawsize), rawptr))

    def rva_to_off(rva):
        for va, size, ptr in sections:
            if va <= rva < va + size:
                return ptr + (rva - va)
        raise SystemExit(f"  ! RVA {rva:#x} outside every section")

    clr = rva_to_off(clr_rva)
    res_rva, res_size = struct.unpack_from("<II", data, clr + 24)
    if not res_rva or not res_size:
        raise SystemExit("  ! assembly embeds no manifest resources")
    return rva_to_off(res_rva), res_size


def looks_like_name_list(b):
    """Newline-separated printable ASCII - the shape of hashes.hl once expanded."""
    sample = b[:8192]
    if b"\n" not in sample:
        return False
    ok = sum(1 for c in sample if 32 <= c < 127 or c in (9, 10, 13))
    return ok / max(1, len(sample)) > 0.98


def find_blob(data, fl2):
    """Embedded [int32 len][payload] that Fast-LZMA2 both recognises AND expands
    into a newline-separated name list. Candidates are verified, not guessed -
    a bare length-prefix match hits false positives in a 16 MB assembly."""
    base, size = clr_resources_region(data)
    end = base + size
    cands = []
    for off in range(base, end - 4):           # byte-granular, but only inside Resources
        n = struct.unpack_from("<I", data, off)[0]
        if not (MIN_BLOB <= n <= MAX_BLOB) or off + 4 + n > end:
            continue
        blob = data[off + 4:off + 4 + n]
        size = fl2.FL2_findDecompressedSize(blob, n)
        # random bytes make FL2 report nonsense sizes, so demand a sane ratio:
        # real text compresses, but not by 64x, and never expands to < its input.
        if n < size <= min(MAX_OUT, n * 64):
            cands.append((n, blob, size))
    # No ranking heuristic survives contact with a 14 MB resource directory
    # (random bytes in the metadata tables make FL2 report plausible-looking
    # sizes), so verify candidates exhaustively - smallest first, since a failed
    # decompression of a small claim is cheap. The FIRST one that expands into a
    # newline-separated ASCII list is the dictionary; nothing else in the
    # assembly does that.
    cands.sort(key=lambda c: c[2])
    for n, blob, size in cands:
        try:
            dst = ctypes.create_string_buffer(size)
            got = fl2.FL2_decompressMt(dst, size, blob, n, 0)
        except Exception:
            continue
        if got > 0 and looks_like_name_list(dst.raw[:got]):
            return n, dst.raw[:got]
    return None


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    out = "hashes.txt"
    if "-o" in argv:
        k = argv.index("-o"); out = argv[k + 1]; del argv[k:k + 2]
    if len(argv) < 2:
        print(__doc__)
        return
    atk = argv[1]
    asm = os.path.join(atk, "AnvilToolkit.dll")
    if not os.path.isfile(asm):
        raise SystemExit(f"  ! not found: {asm}")

    fl2 = load_fl2(atk)
    print(f"  scanning {os.path.basename(asm)} for the compressed dictionary...")
    hit = find_blob(open(asm, "rb").read(), fl2)
    if not hit:
        raise SystemExit("  ! no name-list resource found - is this ATK 1.3.x?")
    n, text = hit
    print(f"  found {n:,} B compressed -> {len(text):,} B")

    with open(out, "wb") as f:
        f.write(text)
    lines = text.decode("utf-8", "replace").splitlines()
    print(f"  wrote {out}  ({len(text):,} B, {len(lines):,} names)")
    print("  sample: " + ", ".join(lines[:5]))


if __name__ == "__main__":
    main(sys.argv)
