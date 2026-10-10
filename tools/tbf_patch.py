#!/usr/bin/env python3
"""
tbf_patch.py - lay a piece of Wildlands terrain into Breakpoint's terrain (.tbf heights), as a reversible patch.

A transplanted GRW block (grw_cell.py) is moved rigidly by (dx, dy, dz). This tool moves GRW's ground under it by the
same shift, feathered into GRB's own ground at the edges, so every prop sits where Ubisoft put it relative to its
terrain. Only heights change: every other layer of every touched node (material IDs, FE / 00 rasters, BC1 colour,
BC7 parameters, trailer) is kept byte for byte, and nodes outside the feathered region are not touched.

    python tbf_patch.py build --src-rect 512,-5632,896,-5248 --shift -5005.068,11668.535,-734.5 --feather 64 -o patch_dir
    python tbf_patch.py check patch_dir                     # re-verify a built patch against the vanilla files
    python tbf_patch.py apply patch_dir --backup-dir DIR    # MUTATES GRB's .tbf files; needs verified backups
    python tbf_patch.py revert patch_dir --backup-dir DIR

HOW (formats in meta/notes-terrain-tbf.md, all verified byte-exact by tbf_read.py's selftest):
- GRB level L tile = 32768 / 2^L m, 132 samples per node side at tile/128 m spacing, 2-sample apron. Every node of
  levels 0-9 whose samples fall in the feathered region gets new heights: w * bolivia + (1 - w) * its own sample,
  w = smoothstep across the feather band. Same function at every level, point-sampled, so a child's sample 2k still
  equals its parent's 1 + k wherever w is 0 or the data is smooth.
- bolivia(X, Y) = GRW ground at (X - dx, Y - dy) + dz, bilinear on GRW's leaf level (16,000 m world, 0.488 m).
- A node is rewritten as frame + re-encoded height chunk (zlib, Python's default level; the game's own level differs,
  untested in game) + the original bytes after the old chunk. Its min/max table entry is recomputed (all three
  files carry the same table, so all three get it).
- apply appends the new nodes to the file that holds each node and overwrites its 8-byte offset entry, plus the
  8-byte min/max entries in every file. revert truncates back and restores those entries. Both refuse to run unless
  the files match the manifest and a backup with the vanilla SHA-256 exists.

UNKNOWN (only a game test can tell): whether GRB derives terrain collision from these heights at run time, and
whether anything else (navmesh, GI, baked cell data) assumes the old ground.
build and check are READ-ONLY on both installs.
"""
import sys, os, json, struct, zlib, hashlib, argparse, shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import tbf_read as tr                          # noqa: E402

GRW_DEFAULT = r"D:\SteamLibrary\steamapps\common\Wildlands"
GRB_DEFAULT = r"H:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint"
MIN_FLOOR = 0.015                              # GRB's table floors node minima near sea level at 0.015 m


def sha256(path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        left = os.path.getsize(path) if limit is None else limit
        while left:
            b = f.read(min(left, 1 << 24))
            if not b:
                break
            h.update(b); left -= len(b)
    return h.hexdigest()


class GrwGround:
    """Vectorized bilinear GRW ground (metres) over a rectangle, from a mosaic of GRW leaf nodes."""
    def __init__(self, grw_root, x0, y0, x1, y1):
        import numpy as np
        self.np = np
        self.hf = tr.Heightfield(tr.find_files(grw_root, "gr"))
        gx0, gy0 = self.hf.grid_coords(x0, y0); gx1, gy1 = self.hf.grid_coords(x1, y1)
        self.c0, self.r0 = int(gx0 // 128) - 1, int(gy0 // 128) - 1
        c1, r1 = int(gx1 // 128) + 1, int(gy1 // 128) + 1
        nc, nr = c1 - self.c0 + 1, r1 - self.r0 + 1
        m = np.zeros((nr * 128, nc * 128), dtype=np.float64)
        for r in range(nr):
            for c in range(nc):
                h = np.array(self.hf.node(self.r0 + r, self.c0 + c), dtype=np.float64).reshape(132, 132)
                m[r * 128:(r + 1) * 128, c * 128:(c + 1) * 128] = h[2:130, 2:130]
        self.m = m * self.hf.scale

    def z(self, x, y):
        np = self.np
        gx, gy = self.hf.grid_coords(x, y)
        ix, iy = gx - 128 * self.c0, gy - 128 * self.r0
        x0, y0 = np.floor(ix).astype(int), np.floor(iy).astype(int)
        if (x0 < 0).any() or (y0 < 0).any() or (x0 + 1 >= self.m.shape[1]).any() or (y0 + 1 >= self.m.shape[0]).any():
            raise ValueError("sample outside the GRW mosaic")
        fx, fy = ix - x0, iy - y0
        m = self.m
        return (m[y0, x0] * (1 - fx) * (1 - fy) + m[y0, x0 + 1] * fx * (1 - fy)
                + m[y0 + 1, x0] * (1 - fx) * fy + m[y0 + 1, x0 + 1] * fx * fy)


def smooth(t):
    return t * t * (3 - 2 * t)


def build(a):
    import numpy as np
    files = tr.find_files(a.grb, "tgt")
    t0 = files[0]
    if t0.version < 2:
        raise SystemExit("not a GRB (v2) .tbf set")
    extent, levels = float(t0.a), t0.levels
    sx0, sy0, sx1, sy1 = a.src_rect
    dx, dy, dz = a.shift
    F = a.feather
    core = (sx0 + dx, sy0 + dy, sx1 + dx, sy1 + dy)                 # GRB metres
    outer = (core[0] - F, core[1] - F, core[2] + F, core[3] + F)
    grw = GrwGround(a.grw, outer[0] - dx - 4, outer[1] - dy - 4, outer[2] - dx + 4, outer[3] - dy + 4)
    scale = t0.height_range / 2 ** 20

    def weight(X, Y):
        ddx = np.maximum(np.maximum(core[0] - X, X - core[2]), 0.0)
        ddy = np.maximum(np.maximum(core[1] - Y, Y - core[3]), 0.0)
        d = np.sqrt(ddx * ddx + ddy * ddy)
        return np.where(d >= F, 0.0, 1.0 - smooth(np.clip(d / F, 0.0, 1.0)))

    os.makedirs(os.path.join(a.out, "nodes"), exist_ok=True)
    manifest = {"tool": "tbf_patch.py", "grb": a.grb, "src_rect": a.src_rect, "shift": a.shift, "feather": F,
                "files": {}, "nodes": []}
    for t in files:
        manifest["files"][os.path.basename(t.path)] = {"size": t.size, "count": t.count}
    for L in range(levels):
        tiles = 2 ** L; tile = extent / tiles; s = tile / 128
        c_lo = max(0, int((outer[0] + extent / 2) // tile) - 1); c_hi = min(tiles - 1, int((outer[2] + extent / 2) // tile) + 1)
        r_lo = max(0, int((outer[1] + extent / 2) // tile) - 1); r_hi = min(tiles - 1, int((outer[3] + extent / 2) // tile) + 1)
        for r in range(r_lo, r_hi + 1):
            for c in range(c_lo, c_hi + 1):
                j = np.arange(132)
                X = -extent / 2 + (c * 128 + j - 2) * s
                Y = -extent / 2 + (r * 128 + j - 2) * s
                XX, YY = np.meshgrid(X, Y)                       # [row = y, col = x], raster order like the node
                w = weight(XX, YY)
                if not (w > 0).any():
                    continue
                i = t0.index(L, r, c)
                holders = [t for t in files if t.has(i)]
                if not holders:
                    raise SystemExit(f"node L{L} ({r}, {c}) is in no .tbf file")
                d = holders[0].node_bytes(i)
                for t in holders[1:]:
                    if t.node_bytes(i) != d:
                        raise SystemExit(f"node L{L} ({r}, {c}) differs between files; not handled")
                magic, ver, flag, zlen = struct.unpack_from("<HHBI", d, 0)
                if magic != tr.FEED or ver != 16 or flag != 1:
                    raise SystemExit(f"node L{L} ({r}, {c}): unexpected frame")
                old = np.array(tr.decode_heights(tr.zexact(d[9:9 + zlen])), dtype=np.float64).reshape(132, 132)
                on = w > 0
                new = old.copy()
                bol = (grw.z(XX[on] - dx, YY[on] - dy) + dz) / scale      # raw units, only where it is blended in
                new[on] = np.rint(w[on] * bol + (1 - w[on]) * old[on])
                new = new.astype(np.int64)
                if new.min() < 0 or new.max() >= 2 ** 20:
                    raise SystemExit(f"node L{L} ({r}, {c}): heights leave GRB's 0..{t0.height_range} m range")
                hv = [int(v) for v in new.reshape(-1)]
                enc = tr.encode_heights(hv)
                assert tr.decode_heights(enc) == hv
                z = zlib.compress(enc)
                nd = struct.pack("<HHBI", tr.FEED, 16, 1, len(z)) + z + d[9 + zlen:]
                chk = tr.parse_node(nd)                          # strict re-parse (Oodle textures not decoded)
                assert chk["height"] == hv
                lo, hi = float(new.min()) * scale, float(new.max()) * scale
                if lo < MIN_FLOOR:
                    lo = MIN_FLOOR
                name = f"L{L}_{r}_{c}.bin"
                open(os.path.join(a.out, "nodes", name), "wb").write(nd)
                manifest["nodes"].append({
                    "level": L, "row": r, "col": c, "index": i, "file": name, "size": len(nd),
                    "sha256": hashlib.sha256(nd).hexdigest(),
                    "holders": {os.path.basename(t.path): t.offsets[i] for t in holders},
                    "old_size": len(d), "old_sha256": hashlib.sha256(d).hexdigest(),
                    "old_minmax": [t0.minmax[2 * i], t0.minmax[2 * i + 1]], "new_minmax": [lo, hi],
                    "changed_samples": int((new != old.astype(np.int64)).sum()),
                    "max_change_m": float(np.abs(new - old).max() * scale)})
    if not manifest["nodes"]:
        raise SystemExit("the region touches no node")
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    by_level = {}
    for n in manifest["nodes"]:
        by_level[n["level"]] = by_level.get(n["level"], 0) + 1
    print(f"core {tuple(round(v, 1) for v in core)}, feather {F} m; {len(manifest['nodes'])} nodes rewritten "
          f"(per level {dict(sorted(by_level.items()))}); largest change "
          f"{max(n['max_change_m'] for n in manifest['nodes']):.1f} m; wrote {a.out}")
    return 0


def _load(pdir):
    m = json.load(open(os.path.join(pdir, "manifest.json")))
    for n in m["nodes"]:
        b = open(os.path.join(pdir, "nodes", n["file"]), "rb").read()
        if hashlib.sha256(b).hexdigest() != n["sha256"]:
            raise SystemExit(f"{n['file']} does not match the manifest")
    return m


def _state(m, grb):
    """'vanilla', 'patched' or 'unknown' per file, by size and the touched table entries."""
    out = {}
    for fn, info in m["files"].items():
        p = os.path.join(grb, fn); size = os.path.getsize(p)
        t = tr.Tbf(p)
        mine = [n for n in m["nodes"] if fn in n["holders"]]
        if size == info["size"] and all(t.offsets[n["index"]] == n["holders"][fn] for n in mine):
            out[fn] = "vanilla"
        elif size == info["size"] + sum(n["size"] for n in mine) and all(t.offsets[n["index"]] >= info["size"] for n in mine):
            out[fn] = "patched"
        else:
            out[fn] = "unknown"
    return out


def check(a):
    m = _load(a.patch)
    for n in m["nodes"]:
        nd = open(os.path.join(a.patch, "nodes", n["file"]), "rb").read()
        tr.parse_node(nd)
    st = _state(m, m["grb"] if not a.grb else a.grb)
    print(f"{len(m['nodes'])} nodes parse; install state: {st}")
    return 0


def _backup_ok(m, grb, bdir):
    for fn, info in m["files"].items():
        b = os.path.join(bdir, fn)
        if not os.path.exists(b) or os.path.getsize(b) != info["size"]:
            raise SystemExit(f"no backup of {fn} in {bdir} (copy the vanilla file there first)")
        if sha256(b) != sha256(os.path.join(grb, fn), info["size"]):
            raise SystemExit(f"backup {b} differs from the install's vanilla part of {fn}")


def apply(a):
    m = _load(a.patch); grb = a.grb or m["grb"]
    st = _state(m, grb)
    if set(st.values()) != {"vanilla"}:
        raise SystemExit(f"install is not in the vanilla state this patch was built on: {st}")
    _backup_ok(m, grb, a.backup_dir)
    for fn, info in m["files"].items():
        p = os.path.join(grb, fn)
        with open(p, "r+b") as f:
            f.seek(0, 2); end = f.tell()
            for n in m["nodes"]:
                if fn in n["holders"]:
                    nd = open(os.path.join(a.patch, "nodes", n["file"]), "rb").read()
                    f.seek(end); f.write(nd)
                    f.seek(28 + 8 * n["index"]); f.write(struct.pack("<Q", end))
                    end += len(nd)
                f.seek(28 + 8 * info["count"] + 8 * n["index"]); f.write(struct.pack("<2f", *n["new_minmax"]))
    st = _state(m, grb)
    print(f"applied: {st}")
    return 0 if set(st.values()) == {"patched"} else 1


def revert(a):
    m = _load(a.patch); grb = a.grb or m["grb"]
    for fn, info in m["files"].items():
        p = os.path.join(grb, fn)
        with open(p, "r+b") as f:
            for n in m["nodes"]:
                if fn in n["holders"]:
                    f.seek(28 + 8 * n["index"]); f.write(struct.pack("<Q", n["holders"][fn]))
                f.seek(28 + 8 * info["count"] + 8 * n["index"]); f.write(struct.pack("<2f", *n["old_minmax"]))
            f.truncate(info["size"])
    _backup_ok(m, grb, a.backup_dir)                     # full-file SHA equality with the vanilla backup
    print(f"reverted: {_state(m, grb)}; every file matches its backup")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    fl = lambda s: tuple(float(v) for v in s.split(","))
    p = sub.add_parser("build")
    p.add_argument("--src-rect", type=fl, required=True, help="GRW world x0,y0,x1,y1 (metres) to bring")
    p.add_argument("--shift", type=fl, required=True, help="dx,dy,dz from GRW to GRB metres (grw_cell.py --shift)")
    p.add_argument("--feather", type=float, default=64.0)
    p.add_argument("--grw", default=os.environ.get("GRW_INSTALL", GRW_DEFAULT))
    p.add_argument("--grb", default=os.environ.get("GRB_INSTALL", GRB_DEFAULT))
    p.add_argument("-o", "--out", required=True)
    for name in ("check", "apply", "revert"):
        p = sub.add_parser(name); p.add_argument("patch"); p.add_argument("--grb")
        if name != "check":
            p.add_argument("--backup-dir", required=True)
    a = ap.parse_args(argv[1:])
    return {"build": build, "check": check, "apply": apply, "revert": revert}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
