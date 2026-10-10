#!/usr/bin/env python3
"""
tbf_read.py - read (and re-encode) Anvil terrain `.tbf` files: Ghost Recon
Wildlands (`PCgr_terrainlin0/1.tbf`, file v1, node v14) and Breakpoint
(`PCtgt_terrainlin0/1/2.tbf`, file v2, node v16). Read-only on the game files.

    python tbf_read.py info  <file.tbf>
    python tbf_read.py node  <install_dir> <level> <row> <col> [--world gr|tgt] [--png out.png]
    python tbf_read.py selftest [--grw <Wildlands dir>] [--grb <Breakpoint dir>] [--n 200]

`node` finds the node in whichever `<prefix>_terrainlin*.tbf` holds it, prints
every block, and with --png writes a contact sheet of its layers (needs Pillow
and numpy; GRB's colour/parameter textures also need the game's
`oo2core_7_win64.dll`, found like data_inspect.py finds it). `selftest` parses
random nodes strictly and checks that heights and run-length rasters re-encode
byte-for-byte.

Background and provenance: meta/notes-terrain-tbf.md (2026-10-10).

FORMAT (verified against both installs unless marked):
- File: `FBT\\0 | u32 ver | u32 a | u32 b | u32 c | f32 heightRange | u32 nodes`,
  then `u64 offset[nodes]` (0 = not in this file). File v2 (GRB) follows with
  `f32 minHeight, f32 maxHeight` per node, in metres. Nodes form a full quadtree,
  row-major within each level: index = (4^L - 1)/3 + row * 2^L + col.
- Node: `u16 0xFEED | u16 ver | u8 1 | u32 zlen | zlib heights`, then
  `u32 len | payload` blocks, then a 40-byte trailer.
- Heights: 132x132 int32 (128 own samples + a 2-sample apron each side), raster
  order, as int16 tokens: 0x7FFF = restart, two int32 literals follow; else
  h[i] = 2h[i-1] - h[i-2] + token. Metres = h * heightRange / 2^20 (verified in
  both games against terrain-placed rock entities, and on GRB against its min/max
  table). Heights stay below 2^20 in both games.
- World mapping (verified against rocks): the terrain is centred on the origin and
  spans GRW 16,000 m (not the 16,384 m cell grid; 0.48828125 m samples) and GRB
  32,768 m (0.5 m). gx = (x + extent/2) / extent * samplesAcross; node col =
  gx // 128; in-node sample = gx - 128*col + 2. Same for y -> row (row-major).
- Run-length raster: 132x132 u8, literal bytes plus `marker count value`
  (count 1-255). The marker is fixed by the block's slot, not stored.
- Trailer: f32 a, f32 b (meaning unknown, a <= b), then a 256-bit mask = the set
  of material IDs in the material raster.
- v14 blocks: [4 zlib sizes + 4 zlib image layers 33808/8452/8452/33808],
  material RLE(0xFF), [u32 zlen | 12 stale bytes | zlib image layer 33808],
  RLE(0xFE), 5 x RLE(0x00).
- v16 blocks: material RLE(0xFF), RLE(0xFE), 2 x RLE(0x00),
  [u32 8712 | Oodle] = BC1 132x132, [u32 17424 | Oodle] = BC7 132x132.
- v14 image layers are a u8 block (1040 or 260 bytes; layout unknown) then a
  128x128 (or 64x64) grid of int16 residual tokens with literal seeds at the
  top-left 2x2. The predictor is NOT yet known, so this tool returns those
  layers split but undecoded.
"""
import argparse
import array
import bisect
import glob
import os
import random
import re
import struct
import sys
import zlib

N = 132 * 132
FEED = 0xFEED


# ---------------------------------------------------------------- codecs

def decode_heights(x):
    """zlib-decompressed height chunk -> list of 17,424 int32 (raw units)."""
    o, h = 0, []
    while len(h) < N:
        t = struct.unpack_from("<h", x, o)[0]
        o += 2
        if t == 0x7FFF:
            a, b = struct.unpack_from("<ii", x, o)
            o += 8
            h += (a, b)
        else:
            h.append(2 * h[-1] - h[-2] + t)
    if o != len(x):
        raise ValueError(f"height stream: used {o} of {len(x)} bytes")
    return h


def encode_heights(h):
    """Inverse of decode_heights; reproduces the game's token stream exactly."""
    out, i = bytearray(), 0
    while i < len(h):
        r = None if i < 2 else h[i] - (2 * h[i - 1] - h[i - 2])
        if r is None or not -32768 <= r <= 32766:
            out += struct.pack("<hii", 0x7FFF, h[i], h[i + 1])
            i += 2
        else:
            out += struct.pack("<h", r)
            i += 1
    return bytes(out)


def rle_decode(p, marker, n=N):
    out, o = bytearray(), 0
    while o < len(p):
        if p[o] == marker:
            out += bytes((p[o + 2],)) * p[o + 1]
            o += 3
        else:
            out.append(p[o])
            o += 1
    if len(out) != n:
        raise ValueError(f"RLE({marker:#04x}) gave {len(out)} bytes, expected {n}")
    return bytes(out)


def rle_encode(raw, marker):
    """Runs of 4+ (max 255) and every marker-valued byte become run tokens."""
    out, i = bytearray(), 0
    while i < len(raw):
        v, j = raw[i], i
        while j < len(raw) and raw[j] == v and j - i < 255:
            j += 1
        if j - i >= 4 or v == marker:
            out += bytes((marker, j - i, v))
        else:
            out += bytes((v,)) * (j - i)
        i = j
    return bytes(out)


def zexact(p):
    d = zlib.decompressobj()
    x = d.decompress(p)
    if not d.eof or d.unused_data:
        raise ValueError("zlib stream does not fill its block exactly")
    return x


def split_image_layer(x):
    """v14 image layer -> (u8 block, int16 residual tokens, grid side)."""
    for side, head in ((128, 1040), (64, 260)):
        if len(x) == head + 2 * side * side:
            return x[:head], array.array("h", x[head:]), side
    raise ValueError(f"unexpected image layer size {len(x)}")


# ---------------------------------------------------------------- files

class Tbf:
    def __init__(self, path):
        self.path, self.size = path, os.path.getsize(path)
        with open(path, "rb") as f:
            hdr = f.read(28)
            (self.magic, self.version, self.a, self.b, self.c,
             self.height_range, self.count) = struct.unpack("<4sIIIIfI", hdr)
            if self.magic != b"FBT\0":
                raise ValueError(f"{path}: not a .tbf (magic {self.magic!r})")
            self.offsets = array.array("Q")
            self.offsets.frombytes(f.read(8 * self.count))
            self.minmax = None
            if self.version >= 2:
                mm = array.array("f")
                mm.frombytes(f.read(8 * self.count))
                self.minmax = mm
        self.levels = 0
        while (4 ** (self.levels + 1) - 1) // 3 <= self.count:
            self.levels += 1
        self._sorted = sorted(set(o for o in self.offsets if 0 < o < self.size))

    def index(self, level, row, col):
        return (4 ** level - 1) // 3 + row * 2 ** level + col

    def has(self, i):
        return 0 < self.offsets[i] < self.size

    def node_bytes(self, i):
        o = self.offsets[i]
        if not 0 < o < self.size:
            return None
        k = bisect.bisect_right(self._sorted, o)
        end = self._sorted[k] if k < len(self._sorted) else self.size
        with open(self.path, "rb") as f:
            f.seek(o)
            return f.read(end - o)

    def metres(self, raw):
        return raw * self.height_range / 2 ** 20


def find_files(install_dir, world=None):
    files = sorted(glob.glob(os.path.join(install_dir, "*_terrainlin*.tbf")))
    if world:
        files = [p for p in files if os.path.basename(p).lower().startswith(("pc" + world).lower() + "_")]
    if not files:
        raise SystemExit(f"no *_terrainlin*.tbf in {install_dir}" + (f" for world {world}" if world else ""))
    prefixes = {re.sub(r"_terrainlin\d+\.tbf$", "", os.path.basename(p), flags=re.I) for p in files}
    if len(prefixes) > 1:
        raise SystemExit(f"several worlds here ({', '.join(sorted(prefixes))}); pass --world")
    return [Tbf(p) for p in files]


# ---------------------------------------------------------------- nodes

def parse_node(d, oodle=None):
    """Strictly parse one node. Raises on any deviation from the known layout."""
    magic, ver, flag, zlen = struct.unpack_from("<HHBI", d, 0)
    if magic != FEED or flag != 1 or ver not in (14, 16):
        raise ValueError(f"node frame {magic:#x} v{ver} flag {flag}")
    n = {"version": ver, "height": decode_heights(zexact(d[9:9 + zlen]))}
    o = 9 + zlen

    def block():
        nonlocal o
        ln = struct.unpack_from("<I", d, o)[0]
        p = d[o + 4:o + 4 + ln]
        if len(p) != ln:
            raise ValueError("block runs past the node")
        o += 4 + ln
        return p

    if ver == 14:
        p = block()
        sizes = struct.unpack_from("<4I", p, 0)
        if 16 + sum(sizes) != len(p):
            raise ValueError("image-layer size table mismatch")
        q, n["image"] = 16, []
        for s in sizes:
            n["image"].append(zexact(p[q:q + s]))
            q += s
        n["material"] = rle_decode(block(), 0xFF)
        p = block()
        zl = struct.unpack_from("<I", p, 0)[0]
        if 16 + zl != len(p):
            raise ValueError("Z layer size mismatch")
        n["image"].append(zexact(p[16:]))          # p[4:16] is stale buffer content
        n["fe"] = rle_decode(block(), 0xFE)
        n["zero"] = [rle_decode(block(), 0x00) for _ in range(5)]
    else:
        n["material"] = rle_decode(block(), 0xFF)
        n["fe"] = rle_decode(block(), 0xFE)
        n["zero"] = [rle_decode(block(), 0x00) for _ in range(2)]
        n["textures"] = []
        for want in (8712, 17424):
            p = block()
            raw = struct.unpack_from("<I", p, 0)[0]
            if raw != want or p[5] != 0x0A or p[4] not in (0x8C, 0xCC):
                raise ValueError(f"expected an Oodle block of {want}, got {raw} {p[4:6].hex()}")
            n["textures"].append(oodle.decompress(p[4:], raw) if oodle and oodle.ok else None)
    if len(d) - o != 40:
        raise ValueError(f"trailer is {len(d) - o} bytes, expected 40")
    t = d[o:]
    n["trailer_floats"] = struct.unpack_from("<2f", t, 0)
    n["trailer_materials"] = {k for k in range(256) if t[8 + k // 8] >> (k % 8) & 1}
    return n


def load_oodle(near):
    tools = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, tools)
    import data_inspect
    return data_inspect.Oodle(data_inspect.find_oodle(near))


# ---------------------------------------------------------------- commands

def cmd_info(a):
    t = Tbf(a.file)
    print(f"{os.path.basename(t.path)}: {t.size:,} B, file v{t.version}, "
          f"a={t.a} b={t.b} c={t.c} heightRange={t.height_range} nodes={t.count:,} ({t.levels} levels)")
    for L in range(t.levels):
        s = (4 ** L - 1) // 3
        here = sum(1 for i in range(s, s + 4 ** L) if t.has(i))
        line = f"  L{L}: {here:,} of {4 ** L:,} nodes here"
        if t.minmax:
            mx = max(t.minmax[2 * i + 1] for i in range(s, s + 4 ** L))
            line += f", max height {mx:.1f} m"
        print(line)


def cmd_node(a):
    files = find_files(a.install_dir, a.world)
    i = files[0].index(a.level, a.row, a.col)
    t = next((t for t in files if t.has(i)), None)
    if not t:
        raise SystemExit(f"node L{a.level} ({a.row},{a.col}) is in none of the files")
    d = t.node_bytes(i)
    oodle = load_oodle(t.path) if d[2] == 16 else None
    n = parse_node(d, oodle)
    h = n["height"]
    print(f"{os.path.basename(t.path)} node {i} = L{a.level} ({a.row},{a.col}), {len(d):,} B, node v{n['version']}")
    print(f"  heights: raw {min(h)}..{max(h)} = {t.metres(min(h)):.2f}..{t.metres(max(h)):.2f} m")
    if t.minmax:
        print(f"  table min/max: {t.minmax[2 * i]:.3f}..{t.minmax[2 * i + 1]:.3f} m")
    print(f"  material IDs: {sorted(set(n['material']))}  (trailer mask agrees: {set(n['material']) == n['trailer_materials']})")
    print(f"  fe raster values: {sorted(set(n['fe']))[:16]}")
    for k, z in enumerate(n["zero"]):
        print(f"  00 raster {k}: {len(set(z))} distinct, max {max(z)}")
    for k, x in enumerate(n.get("image", [])):
        head, core, side = split_image_layer(x)
        print(f"  v14 image layer {k}: {len(x):,} B = u8 block {len(head)} + {side}x{side} int16 tokens (predictor unknown)")
    for k, x in enumerate(n.get("textures", [])):
        print(f"  v16 texture {k}: {'BC1' if k == 0 else 'BC7'} 132x132, "
              + ("decoded" if x else "not decoded (no Oodle DLL)"))
    print(f"  trailer floats: {n['trailer_floats']}")
    if a.png:
        write_png(n, a.png)
        print(f"  wrote {a.png}")


def write_png(n, path):
    import io
    import numpy as np
    from PIL import Image, ImageDraw

    def grey(a):
        a = np.asarray(a, np.float64)
        lo, hi = a.min(), a.max()
        return Image.fromarray(((a - lo) / max(hi - lo, 1e-9) * 255).astype(np.uint8)).convert("RGB")

    def dds(data, dxgi):
        hdr = (struct.pack("<4sI", b"DDS ", 124)
               + struct.pack("<IIIIII", 0x81007, 132, 132, len(data), 0, 1) + b"\0" * 44
               + struct.pack("<II4sIIIII", 32, 4, b"DX10", 0, 0, 0, 0, 0)
               + struct.pack("<IIIII", 0x1000, 0, 0, 0, 0)
               + struct.pack("<IIIII", dxgi, 3, 0, 1, 0))
        return Image.open(io.BytesIO(hdr + data)).convert("RGBA")

    sq = lambda b: np.frombuffer(b, np.uint8).reshape(132, 132)
    tiles = [("height", grey(np.array(n["height"]).reshape(132, 132))),
             ("material", grey(sq(n["material"]))), ("fe", grey(sq(n["fe"])))]
    tiles += [(f"00 raster {k}", grey(sq(z))) for k, z in enumerate(n["zero"])]
    for k, x in enumerate(n.get("textures", [])):
        if x:
            im = dds(x, 71 if k == 0 else 98)
            tiles.append(("BC1 colour" if k == 0 else "BC7 rgb", im.convert("RGB")))
            if k == 1:
                tiles.append(("BC7 alpha", im.getchannel("A").convert("RGB")))
    w = 270
    sheet = Image.new("RGB", (w * 4, 280 * ((len(tiles) + 3) // 4)), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    for k, (name, im) in enumerate(tiles):
        x, y = (k % 4) * w, (k // 4) * 280
        sheet.paste(im.resize((264, 264), Image.NEAREST), (x, y + 14))
        draw.text((x + 2, y), name, fill=(255, 255, 255))
    sheet.save(path)


def cmd_selftest(a):
    random.seed(a.seed)
    for label, d in (("Wildlands", a.grw), ("Breakpoint", a.grb)):
        if not d:
            continue
        files = find_files(d)
        oodle = load_oodle(files[0].path) if files[0].version >= 2 else None
        t0 = files[0]
        stats = dict(nodes=0, heights_exact=0, rle_exact=0, rle=0, mask_ok=0)
        if t0.minmax:
            stats["minmax_ok"] = 0
        for _ in range(a.n):
            L = t0.levels - 1 if random.random() < 0.6 else random.randrange(t0.levels)
            i = t0.index(L, random.randrange(2 ** L), random.randrange(2 ** L))
            t = next((t for t in files if t.has(i)), None)
            if not t:
                continue
            d = t.node_bytes(i)
            n = parse_node(d, oodle)
            stats["nodes"] += 1
            zlen = struct.unpack_from("<I", d, 5)[0]
            stats["heights_exact"] += encode_heights(n["height"]) == zlib.decompress(d[9:9 + zlen])
            stats["mask_ok"] += set(n["material"]) == n["trailer_materials"]
            if t.minmax:
                stats["minmax_ok"] += abs(t.metres(max(n["height"])) - t.minmax[2 * i + 1]) < 1e-2
            o = 9 + zlen
            blocks = []
            while len(d) - o > 40:
                ln = struct.unpack_from("<I", d, o)[0]
                blocks.append(d[o + 4:o + 4 + ln])
                o += 4 + ln
            pairs = ([(blocks[1], 0xFF), (blocks[3], 0xFE)] + [(b, 0) for b in blocks[4:9]]
                     if n["version"] == 14 else
                     [(blocks[0], 0xFF), (blocks[1], 0xFE), (blocks[2], 0), (blocks[3], 0)])
            for p, m in pairs:
                stats["rle"] += 1
                stats["rle_exact"] += rle_encode(rle_decode(p, m), m) == p
        print(f"{label}: {stats}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info"); p.add_argument("file")
    p = sub.add_parser("node"); p.add_argument("install_dir"); p.add_argument("level", type=int)
    p.add_argument("row", type=int); p.add_argument("col", type=int)
    p.add_argument("--world", help="world prefix after 'PC', e.g. gr or tgt"); p.add_argument("--png")
    p = sub.add_parser("selftest"); p.add_argument("--grw"); p.add_argument("--grb")
    p.add_argument("--n", type=int, default=200); p.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    {"info": cmd_info, "node": cmd_node, "selftest": cmd_selftest}[a.cmd](a)


if __name__ == "__main__":
    main()
