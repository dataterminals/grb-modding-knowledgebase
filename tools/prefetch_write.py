#!/usr/bin/env python3
"""
prefetch_write.py - add records to a forge's PrefetchingFileInfos table (entry ID 145).

The write half of `prefetch_inspect.py`. Every entry Ubisoft ships in a `_patch_01`
forge has a record in that forge's own 145 table - including each of the 607 world
cells MaungaNui_Split_patch_01 overrides, whose records are byte-identical to the base
forge's. ATK 1.3.1 repacks the stale 145 it unpacked, so an entry added with ATK has no
record. This tool copies records from a donor forge (normally the base forge whose entry
you override) into a 145 file you then repack with ATK as usual.

    python prefetch_write.py <145 source> <donor forge> <ID> [<ID> ...] -o <out file>

`<145 source>` is a forge (its entry 145 is read) or an unpacked `.PrefetchInfo` file.
Existing records are kept byte for byte: the new records are appended to the data blob
and their table rows inserted in ID order. Writes nothing in place.

WRAPPER (matches Ubisoft's frame, see prefetch_inspect.py):
    u64 magic | u16 3 | u8 0 (LZO1X) | u16 0x8000 | u16 0
    { u8 1 | u32 comp | u32 uncomp | u32 check | comp bytes }*  - blocks of <= 32768 B
    u8 0
`check` = Adler-32 seeded 0 over the compressed bytes (ATK's `lzo_adler32`; the same
recipe our .data writer uses). Each block is a literal-only LZO1X stream: one literal run
plus the end marker `11 00 00`. Any LZO1X decoder must accept it, and it never has
comp == uncomp, so no reader can mistake it for a stored block.
"""
import sys, os, struct, zlib, bisect

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import prefetch_inspect as pi                     # noqa: E402

BLOCK = 0x8000


def _ext(n, base):
    """LZO's run-length extension: n > base is written as 0x00, (n - base) // 255 zero bytes, remainder."""
    z, last = divmod(n - base, 255)
    if last == 0:
        z, last = z - 1, 255
    return b"\x00" * z + bytes([last])


def lzo1x_compress(data, tries=16):
    """A standard LZO1X stream for `data`, using only literal runs and M3 matches
    (length >= 3, distance 1..16384) plus the end marker `11 00 00`. Greedy, chained hash on 3 bytes.
    Every instruction is one the reference decoder (lzo1x_d.ch) handles; prefetch_inspect.lzo1x
    round-trips it (asserted in wrap())."""
    n, out, heads = len(data), bytearray(), {}
    lit, ip, last_state_at = 0, 0, None            # lit = start of the pending literal run

    def flush_literals(end):
        nonlocal last_state_at
        L = end - lit
        if L == 0:
            return
        if not out:                                # stream start: first byte > 17 carries the run
            out.extend(bytes([L + 17]) if L <= 238 else b"\x00" + _ext(L - 3, 15))
        elif L <= 3:                               # 1..3 literals ride in the previous match's state bits
            out[last_state_at] |= L
        elif L - 3 <= 15:
            out.append(L - 3)
        else:
            out.extend(b"\x00" + _ext(L - 3, 15))
        out.extend(data[lit:end])

    while ip + 3 <= n:
        key = data[ip:ip + 3]
        best_len, best_pos = 0, 0
        for cand in reversed(heads.get(key, ())[-tries:]):
            if ip - cand > 16384:
                break
            m = 3
            while ip + m < n and data[cand + m] == data[ip + m]:
                m += 1
            if m > best_len:
                best_len, best_pos = m, cand
        heads.setdefault(key, []).append(ip)
        if best_len < 3:
            ip += 1
            continue
        flush_literals(ip)
        t = best_len - 2
        out.extend(bytes([32 | t]) if t <= 31 else b"\x20" + _ext(t, 31))
        d = (ip - best_pos - 1) << 2              # low 2 bits = trailing-literal count, filled later
        last_state_at = len(out)
        out.extend(struct.pack("<H", d))
        for k in range(ip + 1, min(ip + best_len, n - 2)):
            heads.setdefault(data[k:k + 3], []).append(k)
        ip += best_len
        lit = ip
    flush_literals(n)
    out.extend(b"\x11\x00\x00")
    return bytes(out)


def wrap(table_bytes):
    """Frame a decompressed 145 table the way Ubisoft does: 32 KB LZO1X blocks, no closing byte."""
    out = bytearray(pi.MAGIC + struct.pack("<HBHH", 3, 0, 0x8000, 0))
    for o in range(0, len(table_bytes), BLOCK):
        raw = table_bytes[o:o + BLOCK]
        comp = lzo1x_compress(raw)
        assert pi.lzo1x(comp) == raw, "LZO1X round trip failed"
        assert len(comp) < len(raw) or len(raw) < 64, "block did not compress"
        out += struct.pack("<BIII", 1, len(comp), len(raw), zlib.adler32(comp, 0) & 0xFFFFFFFF) + comp
    return bytes(out)


def parse(wrapped):
    """(rows [(ID, size, offset)] in table order, data blob)."""
    d, _nb, _end = pi.unwrap(wrapped)
    n = struct.unpack_from("<I", d, 0)[0]
    rows = [struct.unpack_from("<QII", d, 4 + 16 * k) for k in range(n)]
    base = 4 + 16 * n + 4
    size = struct.unpack_from("<I", d, base - 4)[0]
    return rows, d[base:base + size]


def build(rows, data):
    return (struct.pack("<I", len(rows)) + b"".join(struct.pack("<QII", *r) for r in rows)
            + struct.pack("<I", len(data)) + data)


TAIL_TEMPLATE, TAIL_TEXTURE = b"\x01\x00\x00", b"\x02\x00\x00"   # as on every vanilla mesh record seen


def make_record(items):
    """A plain record: u16 0 | u16 k | k x {u64 ID | 3-byte tail}. `items` = [(ID, tail bytes)].
    Vanilla: a Mesh lists its MaterialTemplates (tail 01 00 00) and TextureMaps (02 00 00);
    TextureMaps and CompiledMips have empty records (make_record([]) = 00 00 00 00)."""
    return struct.pack("<HH", 0, len(items)) + b"".join(struct.pack("<Q", i) + t for i, t in items)


def record_of(wrapped, fid):
    rows, data = parse(wrapped)
    for f, s, o in rows:
        if f == fid:
            return data[o:o + s]
    return None


def add_raw(wrapped, records):
    """New wrapped 145 bytes with `records` ({ID: record bytes}) added; existing rows untouched."""
    rows, data = parse(wrapped)
    have = {fid for fid, _, _ in rows}
    data = bytearray(data)
    for fid, rec in records.items():
        if fid in have:
            raise ValueError(f"{fid} already has a record")
        bisect.insort(rows, (fid, len(rec), len(data)))   # tables are ID-sorted
        data += rec
    return wrap(build(rows, bytes(data)))


def add_records(wrapped, donor_wrapped, ids):
    """New wrapped 145 bytes with the donor's records for `ids` added (existing rows untouched)."""
    recs = {}
    for fid in ids:
        r = record_of(donor_wrapped, fid)
        if r is None:
            raise ValueError(f"donor has no record for {fid}")
        recs[fid] = r
    return add_raw(wrapped, recs)


def check_blocks(wrapped):
    """True if every block's check is Adler-32 seeded 0 over its compressed bytes."""
    o, ok = 15, []
    while o < len(wrapped) and wrapped[o]:
        comp, unc, chk = struct.unpack_from("<III", wrapped, o + 1)
        blk = wrapped[o + 13:o + 13 + comp]
        ok.append(zlib.adler32(blk, 0) & 0xFFFFFFFF == chk)
        o += 13 + comp
    return ok


def _load(path):
    if path.lower().endswith(".forge"):
        b = pi.read_pfi(path)
        if b is None:
            raise SystemExit(f"{path}: no entry 145")
        return b
    return open(path, "rb").read()


def main(argv):
    if "-o" not in argv or len(argv) < 6:
        print(__doc__); return 2
    k = argv.index("-o"); out = argv[k + 1]; args = argv[1:k] + argv[k + 2:]
    src, donor, ids = args[0], args[1], [int(x, 0) for x in args[2:]]
    w = _load(src); dw = _load(donor)
    new = add_records(w, dw, ids)
    rows, data = parse(new)
    orows, odata = parse(w)
    drows, ddata = parse(dw)
    dmap = {f: (s, o) for f, s, o in drows}
    nmap = {f: (s, o) for f, s, o in rows}
    assert [r[0] for r in rows] == sorted(r[0] for r in rows)
    assert all(data[o:o + s] == odata[oo:oo + s] for f, s, oo in orows for o in [nmap[f][1]])
    assert all(data[nmap[f][1]:nmap[f][1] + nmap[f][0]] == ddata[dmap[f][1]:dmap[f][1] + dmap[f][0]] for f in ids)
    assert all(check_blocks(new))
    open(out, "wb").write(new)
    print(f"{len(orows)} -> {len(rows)} records; {len(w):,} -> {len(new):,} B; wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
