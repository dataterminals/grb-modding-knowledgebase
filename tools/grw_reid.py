#!/usr/bin/env python3
"""
grw_reid.py - deterministic re-ID of Ghost Recon Wildlands (GRW) objects that are
ported into Breakpoint (GRB), and a rewriter for the 64-bit references inside
converted payloads.

    import grw_reid
    new = grw_reid.reid(old_id)                    # pure function, stable across runs
    data, hits, skipped = grw_reid.rewrite(payload, remap)
    python grw_reid.py selftest

WHY: GRW and GRB draw ClassIDs from the same allocator families. An object Bolivia
ships can therefore reuse an ID that GRB already gives to a different object.
meta/notes-id-collisions.md measures this on both installs and classifies every
shared ID. Only the "different object" class must be re-IDed.

THE SCHEME (2026-10-10, see the notes for the census behind it):
- Plain IDs (bit 63 clear): every GRB plain ID is below 2^42, as are the GRW ones,
  so bits 42..62 are unused by both games. reid(i) = i | (1 << 46). It is
  reversible (clear bit 46) and can never land on a GRB or GRW ID.
- Derived IDs (bit 63 set; 0x8000.. | base << 20 | k): GRB never sets bit 62 on
  them, and neither does GRW. reid(i) = i | (1 << 62).
- An ID is only re-IDed if it is in the remap you pass to rewrite(). reid() alone
  changes nothing on disk.

REWRITING: rewrite() replaces every 8-byte little-endian occurrence of a remapped
ID. By default it only replaces an occurrence that sits at payload offset 0 (the
ClassID) or right after a reference prefix that the GR formats use (01 00, 01 01,
01 02, 03 00, or a single 00 byte as in a TerrainMaterial's TextureMap list).
Other occurrences are returned in `skipped` for review, because a raw 8-byte match
inside vertex or pixel data can be a coincidence. Pass strict=False to replace
everything.
"""
import struct
import sys

TAG_PLAIN = 1 << 46
TAG_DERIVED = 1 << 62
PLAIN_LIMIT = 1 << 42           # both games' plain IDs stay below this (census)
PREFIXES = (b"\x01\x00", b"\x01\x01", b"\x01\x02", b"\x03\x00")


def reid(i):
    """Stable new ID for a GRW ID that collides with a different GRB object."""
    if i >> 63:
        if i & TAG_DERIVED:
            raise ValueError(f"{i:#x} already carries the derived tag")
        return i | TAG_DERIVED
    if i >= PLAIN_LIMIT:
        raise ValueError(f"{i:#x} is outside the plain range the scheme was checked for")
    return i | TAG_PLAIN


def unreid(i):
    return i & ~TAG_DERIVED if i >> 63 else i & ~TAG_PLAIN


def _occurrences(payload, keys):
    """Offsets of every 8-byte window equal to one of `keys` (sorted uint64 array)."""
    import numpy as np
    out = []
    n = len(payload)
    for k in range(8):
        m = (n - k) // 8
        if m <= 0:
            continue
        v = np.frombuffer(payload, dtype="<u8", count=m, offset=k)
        pos = np.searchsorted(keys, v)
        pos[pos >= len(keys)] = 0
        hit = np.nonzero(keys[pos] == v)[0]
        out.extend(int(k + 8 * h) for h in hit)
    return sorted(out)


def rewrite(payload, remap, strict=True, extra_prefixes=()):
    """Return (new payload, [(offset, old, new)], [skipped (offset, old, context)]).

    `extra_prefixes`: more byte strings accepted right before an ID. Example: the GRW
    root cell's `x[ENV]_Cloud_*` entities reference their FX template as a 4-byte
    value `8a b0 b8 01` + u64 (a typed handle); strict mode reports those 12 as
    skipped until that prefix is passed here."""
    import numpy as np
    if not remap:
        return payload, [], []
    keys = np.array(sorted(remap), dtype=np.uint64)
    buf = bytearray(payload)
    done, skipped, last = [], [], -8
    extra = tuple(extra_prefixes)
    for off in _occurrences(bytes(payload), keys):
        if off < last + 8:
            continue                                   # overlaps a replaced window
        old = struct.unpack_from("<Q", payload, off)[0]
        ok = (off == 0 or (off >= 2 and payload[off - 2:off] in PREFIXES)
              or (off >= 1 and payload[off - 1] == 0)
              or any(off >= len(x) and payload[off - len(x):off] == x for x in extra))
        if strict and not ok:
            skipped.append((off, old, payload[max(0, off - 4):off + 12].hex(" ")))
            continue
        struct.pack_into("<Q", buf, off, remap[old])
        done.append((off, old, remap[old]))
        last = off
    return bytes(buf), done, skipped


def selftest():
    import random
    random.seed(0)
    ok = True
    for _ in range(10000):
        i = random.randrange(1 << 35, PLAIN_LIMIT)
        ok &= unreid(reid(i)) == i and reid(i) >= PLAIN_LIMIT and not reid(i) >> 63
        d = (1 << 63) | (random.randrange(1 << 41) << 20) | random.randrange(1 << 20)
        ok &= unreid(reid(d)) == d and reid(d) >> 62 == 3
    print("reid/unreid round trip and range:", ok)
    a, b = 0x10EB8A262E, 0x1B133A5010
    p = (struct.pack("<Q", a) + b"\x88\x41\x72\x01" + b"\x01\x00" + struct.pack("<Q", b)
         + b"\xAA\xBB" + struct.pack("<Q", b))
    out, done, skipped = rewrite(p, {a: reid(a), b: reid(b)})
    print("rewrite: replaced", [(o, hex(n)) for o, _, n in done], "skipped", [o for o, _, _ in skipped])
    ok &= len(done) == 2 and len(skipped) == 1
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        sys.exit(0 if selftest() else 1)
    print(__doc__)
