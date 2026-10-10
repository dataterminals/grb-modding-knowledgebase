#!/usr/bin/env python3
"""
prefetch_inspect.py - read a forge's PrefetchingFileInfos table (entry ID 145).

Every Ubisoft-written forge carries one PrefetchingFileInfos sidecar: for each
entry in the forge, the list of other IDs the engine should load alongside it.
A new item that only exists in a mod needs its own records here (the SCUBA CoD
package ships them as `prefetch_add` ops); this tool shows what vanilla holds,
so a mod's records can be checked against the donor they were copied from.

    python prefetch_inspect.py DataPC.forge                        # summary
    python prefetch_inspect.py DataPC.forge 0x1ACBFE0A150          # one record
    python prefetch_inspect.py DataPC_Resources.forge 1838302011730 --install "D:\\...\\Ghost Recon Breakpoint"
    python prefetch_inspect.py DataPC_patch_01_000001F01C1B0200.bin --install "D:\\..."   # a grbmod record file

`--install` indexes every forge in that folder so listed IDs print with names
(without it, only IDs in the same forge get names). READ-ONLY.

FORMAT (decoded 2026-10-07 from the live forges; the table closes exactly - header,
records and data end on the last decoded byte - in every forge checked, and the
record count is the forge's entry count minus the two sidecars):

    wrapper := u64 magic 0x1004FA9957FBAA33        (CompressedFileData's magic)
               u16 version 3 | u8 algorithm 0 (LZO1X) | u16 0x8000 | u16 0
               { u8 more=1 | u32 comp | u32 uncomp | u32 check | comp bytes }*
    table   := u32 n | n x { u64 ID | u32 size | u32 offset } | u32 data_size | data
    record  := u16 0 | u16 k | k x { u64 ID | 3 bytes }       (at data[offset], size bytes)

Blocks hold <= 32768 decompressed bytes. `check` = Adler-32 seeded 0 (not 1) over the
block's compressed bytes - ATK's `lzo_adler32`; verified on all 740 blocks of four
vanilla forges (2026-10-10). Vanilla frames end on the last block's last byte: there
is no closing `u8 0` (an earlier note said there was), and no vanilla block is stored
raw. `unwrap()` still accepts both, treating comp == uncomp as raw. The 3-byte tail is
`01 00 00` on every gear record looked at and `04 00 00` on the weapon parts in
OrphanCells' cell record - its meaning is not established. Not every record starts
`u16 0`: in MaungaNui_Split_patch_01, 893 of 1402 do (and are exactly 4 + 11k bytes); the
other 509 start with 1..7+ and are longer (Cell45147_DataBlock: `01 00 01 00 …`, 5099 B,
with ID-like u64s inside). That first u16 looks like a group count, but the grouped layout
is not decoded, so `record_items()` misreads those records. `prefetch_write.py` copies
records verbatim and does not need to parse them.

This is a different frame from the .data containers' (Oodle, block table up
front): the per-block `more` byte is what read_cfd() does not parse.
"""
import sys, os, struct, glob

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from forge_inspect import forge_entries          # noqa: E402

PFI_ID = 145
MAGIC = bytes.fromhex("33aafb5799fa0410")


def lzo1x(src):
    """Plain LZO1X decompression (the reference decoder's state machine)."""
    out = bytearray()
    ip, state = 0, 0
    if src[0] > 17:
        t = src[0] - 17
        ip = 1
        out += src[ip:ip + t]; ip += t
        state = min(t, 4)
    while True:
        t = src[ip]; ip += 1
        if t < 16:
            if state == 0:                                  # literal run
                if t == 0:
                    while src[ip] == 0:
                        t += 255; ip += 1
                    t += 15 + src[ip]; ip += 1
                t += 3
                out += src[ip:ip + t]; ip += t
                state = 4
                continue
            if state < 4:                                   # M1, 2 bytes
                dist = (t >> 2) + (src[ip] << 2) + 1; ip += 1; length = 2
            else:                                           # M1 after a literal run
                dist = (t >> 2) + (src[ip] << 2) + 2049; ip += 1; length = 3
        elif t >= 64:                                       # M2
            length = (t >> 5) + 1
            dist = ((t >> 2) & 7) + (src[ip] << 3) + 1; ip += 1
        elif t >= 32:                                       # M3
            length = t & 31
            if length == 0:
                while src[ip] == 0:
                    length += 255; ip += 1
                length += 31 + src[ip]; ip += 1
            length += 2
            ds = src[ip] | (src[ip + 1] << 8); ip += 2
            dist = (ds >> 2) + 1
            t = ds
        else:                                               # M4, or end of stream
            length = t & 7
            if length == 0:
                while src[ip] == 0:
                    length += 255; ip += 1
                length += 7 + src[ip]; ip += 1
            length += 2
            ds = src[ip] | (src[ip + 1] << 8); ip += 2
            dist = ((t & 8) << 11) + (ds >> 2)
            if dist == 0:
                break
            dist += 16384
            t = ds
        for _ in range(length):
            out.append(out[-dist])
        state = t & 3
        out += src[ip:ip + state]; ip += state
    return bytes(out)


def unwrap(b):
    """(decompressed bytes, block count, offset where the frame ended)."""
    if b[:8] != MAGIC:
        raise ValueError("not a PrefetchingFileInfos frame (CompressedFileData magic missing)")
    o, out, nb = 15, bytearray(), 0
    while o < len(b):
        more = b[o]; o += 1
        if more == 0:
            break
        comp, unc, _check = struct.unpack_from("<IiI", b, o); o += 12
        blk = b[o:o + comp]; o += comp
        d = blk if comp == unc else lzo1x(blk)
        if len(d) != unc:
            raise ValueError(f"block {nb}: decoded {len(d)} bytes, header says {unc}")
        out += d; nb += 1
    return bytes(out), nb, o


def table(d):
    """({ID: (size, offset)}, data base offset, data size)."""
    n = struct.unpack_from("<I", d, 0)[0]
    ents = {}
    for k in range(n):
        fid, size, off = struct.unpack_from("<QII", d, 4 + 16 * k)
        ents[fid] = (size, off)
    total = struct.unpack_from("<I", d, 4 + 16 * n)[0]
    return ents, 4 + 16 * n + 4, total


def record_items(rec):
    """[(ID, tail hex)] for one record."""
    _zero, k = struct.unpack_from("<HH", rec, 0)
    return [(struct.unpack_from("<Q", rec, 4 + 11 * i)[0], rec[12 + 11 * i:15 + 11 * i].hex())
            for i in range(k)]


def read_pfi(forge_path):
    for fid, _ext, _name, off, ln in forge_entries(forge_path):
        if fid == PFI_ID:
            with open(forge_path, "rb") as f:
                f.seek(off)
                return f.read(ln)
    return None


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    install = None
    if "--install" in argv:
        k = argv.index("--install"); install = argv[k + 1]; del argv[k:k + 2]
    args = argv[1:]
    if not args:
        print(__doc__)
        return
    target, want = args[0], [int(a, 0) for a in args[1:]]

    names = {}
    for fg in sorted(glob.glob(os.path.join(install, "*.forge"))) if install else []:
        for fid, _e, nm, _o, _l in forge_entries(fg):
            names.setdefault(fid, nm)
    nm = lambda v: names.get(v, f"0x{v:X}")

    if not target.lower().endswith(".forge"):                     # one record file
        items = record_items(open(target, "rb").read())
        print(f"{os.path.basename(target)}: {len(items)} prefetch item(s)")
        for i, tail in items:
            print(f"  {i:#018x}  [{tail}]  {nm(i)}")
        return

    if not install:
        for fid, _e, n, _o, _l in forge_entries(target):
            names.setdefault(fid, n)
    raw = read_pfi(target)
    if raw is None:
        print(f"{os.path.basename(target)}: no entry 145 (PrefetchingFileInfos)")
        return
    d, nb, end = unwrap(raw)
    ents, base, total = table(d)
    print("=" * 78)
    print(f"FILE: {os.path.basename(target)}   PrefetchingFileInfos {len(raw):,} B")
    print(f"  {nb} LZO1X block(s) -> {len(d):,} B; frame ends at {end:,} of {len(raw):,}")
    print(f"  {len(ents):,} record(s); table closes exactly: {base + total == len(d)}")
    for fid in want:
        if fid not in ents:
            print(f"  {fid:#x}: no record")
            continue
        size, off = ents[fid]
        items = record_items(d[base + off: base + off + size])
        print(f"  {nm(fid)} ({fid:#x}): {len(items)} item(s)")
        for i, tail in items:
            print(f"    {i:#018x}  [{tail}]  {nm(i)}")


if __name__ == "__main__":
    main(sys.argv)
