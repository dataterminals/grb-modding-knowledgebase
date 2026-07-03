#!/usr/bin/env python3
"""
clothwrap.py - read and experiment with a GRB cloth's render<->sim WRAP.

Background (see docs/11-cloth-and-physics.md):
A GRB physics garment is two meshes - a low-res *simulation cage* and the high-res
*visible mesh*. The visible mesh follows the cage via a stored "wrap": one 20-byte
record per bound visible vertex, each binding it to 3 nearby cage (sim) vertices
plus weights. This tool locates that wrap and can produce DIAGNOSTIC test cloths
that deliberately mis-point the wrap, so you can confirm in-game that the wrap
really drives the visible mesh (a decisive check before building a full reskin
encoder). It also just inspects the wrap.

*** THIS IS AN EXPERIMENTAL / RESEARCH TOOL. It edits cloth internals. ***
*** ALWAYS work on a copy and keep a verified backup of your forge. ***

Record layout (verified on TP_WalkerCoat_Cloth):
  [u16 flag] [6x u16 weight data] [3x u16 sim-vertex index]   = 20 bytes
The 3 sim indices (last 6 bytes) are what we edit for the diagnostic - those byte
positions are certain. The weight encoding is not yet fully decoded (that's what
the in-game test helps settle), so this tool does NOT yet rebind a new mesh.

Input/output: a cloth **.data** (the entry ATK writes when you unpack a forge; pass
`--oodle <oo2core_7_win64.dll>`) or a decompressed **.Cloth**. When the input is a
.data, the output is a drop-in .data (rebuilt as a proper Oodle-compressed
.data — raw/uncompressed blocks parse in ATK but crash GRB at load) — put it back in your unpacked forge folder under the SAME filename
and repack the forge in ATK. All edits are same-size, so everything else is
byte-identical.

  --diagnostic twist|collapse   mis-point the wrap (twist = shift cage indices;
                                collapse = all -> cage vertex 0). Tests whether the
                                wrap actually drives the visible mesh.
  --gravity X,Y,Z               set the DEDICATED gravity vector (ClothPropertiesGravity,
                                section 4398) on every LOD. NOTE: the gravity field inside
                                ClothProperties (section 4357) is verified INERT at GRB
                                runtime (2026-07-02), so this tool now edits 4398 - the
                                live-candidate. Whether 4398 is itself runtime-effective is
                                the current OPEN in-game test (see meta/next-session.md);
                                do NOT treat gravity as a proven control until 4398 is
                                confirmed to move a loose garment in-game.

*** IN-GAME STATUS (2026-07-02): the wrap-as-render-driver hypothesis is NOT yet
    validated in-game (ghillie tests were inconclusive). Gravity is also unsettled: the
    ClothProperties (4357) gravity field is verified INERT at runtime; the dedicated
    ClothPropertiesGravity (4398) is the untested live-candidate this tool now edits.
    See docs/11-cloth-and-physics.md and meta/next-session.md. ***

Usage:
  python clothwrap.py cloth.data --oodle oo2core_7_win64.dll                    # inspect
  python clothwrap.py cloth.data --oodle oo2core_7_win64.dll --gravity 0,0,10 --out g.data   # reverse gravity (4398)
  python clothwrap.py cloth.data --oodle oo2core_7_win64.dll --diagnostic collapse --out c.data
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motioncloth as mc

REC = 20  # bytes per wrap record


def _i32(b, o): return struct.unpack_from("<i", b, o)[0]
def _u16(b, o): return struct.unpack_from("<H", b, o)[0]


def _after_sim_fields(payload, body, pkg_end):
    """Forward-parse the sim fields that follow a ClothPackage; return the offset
    just past them (start of the header+table+records visual block), and counts."""
    o = pkg_end
    def buf(o, elt):
        c = _i32(payload, o); return o + 4 + c * elt
    o = buf(o, 2)    # TriQuadIndex   u16[]
    o = buf(o, 12)   # sim VertexPos  vec3[]
    o = buf(o, 12)   # sim VertexNormals vec3[]
    o = buf(o, 2)    # sim Indices    u16[]
    o += 4           # empty list (VisualVertexMappings count, =0 on GRB)
    rcount = _i32(payload, o); o += 4   # visible (render) vertex count
    return o, rcount


def _detect_records(payload, data_start, V, search=8000):
    """Locate the wrap-record run: the longest stretch of 20-byte records whose
    last 3 u16 are valid sim indices (< V)."""
    best = None
    limit = min(len(payload), data_start + search)
    for start in range(data_start, limit, 2):
        n, o = 0, start
        while o + REC <= len(payload) and all(_u16(payload, o + 14 + 2 * k) < V for k in range(3)):
            n += 1; o += REC
        if n >= 50 and (best is None or n > best[0]):
            best = (n, start)
    return best  # (n_records, start_offset) or None


def find_wraps(payload):
    """Return a list of {lod, sim_verts, render_verts, rec_start, n_records} for
    every LOD that has a wrap."""
    out = []
    for lod, pkg in enumerate(mc.locate_clothpackages(payload)):
        body = pkg.bodies[0]
        V = mc.sim_vertex_count(body)
        data_start, rcount = _after_sim_fields(payload, body, pkg.end)
        det = _detect_records(payload, data_start, V)
        if det:
            n, start = det
            out.append(dict(lod=lod, sim_verts=V, render_verts=rcount,
                            rec_start=start, n_records=n))
    return out


def _indices(payload, rec_start, i):
    o = rec_start + i * REC
    return (_u16(payload, o + 14), _u16(payload, o + 16), _u16(payload, o + 18))


def inspect(payload):
    L = ["=" * 66, "CLOTH WRAP (render<->sim binding)"]
    wraps = find_wraps(payload)
    if not wraps:
        L.append("  No wrap records found - this cloth may bind the visible mesh")
        L.append("  directly (sim mesh == visible mesh), or isn't a GRB garment cloth.")
        return "\n".join(L) + "\n"
    for w in wraps:
        pct = 100.0 * w["n_records"] / w["render_verts"] if w["render_verts"] else 0
        L.append(f"  LOD{w['lod']}: sim cage = {w['sim_verts']} points; "
                 f"visible mesh = {w['render_verts']} points")
        L.append(f"     wrap: {w['n_records']} bound visible points "
                 f"({pct:.0f}% of the mesh) each tied to 3 cage points")
        L.append(f"     (records at offset {w['rec_start']}, 20 bytes each)")
    L.append("")
    L.append("  Plain terms: the visible garment follows the low-res cage through")
    L.append("  this baked list. A brand-new mesh needs this list rebuilt for it.")
    return "\n".join(L) + "\n"


def diagnostic(payload, mode):
    """Return a modified payload that deliberately mis-points the wrap, for an
    in-game confirmation that the wrap drives the visible mesh. Same size, so
    everything else is byte-identical."""
    buf = bytearray(payload)
    wraps = find_wraps(payload)
    if not wraps:
        raise SystemExit("no wrap records to modify")
    edited = 0
    for w in wraps:
        V = w["sim_verts"]
        for i in range(w["n_records"]):
            o = w["rec_start"] + i * REC
            i0, i1, i2 = _u16(payload, o + 14), _u16(payload, o + 16), _u16(payload, o + 18)
            if mode == "collapse":
                # every bound visible point follows a single cage point -> the
                # bound region should visibly bunch/collapse in-game.
                n0 = n1 = n2 = 0
            elif mode == "twist":
                # shift each binding to a different cage point -> the bound region
                # should look scrambled/torn if the wrap drives rendering.
                n0 = (i0 + 40) % V; n1 = (i1 + 40) % V; n2 = (i2 + 40) % V
            else:
                raise SystemExit(f"unknown diagnostic mode: {mode}")
            struct.pack_into("<H", buf, o + 14, n0)
            struct.pack_into("<H", buf, o + 16, n1)
            struct.pack_into("<H", buf, o + 18, n2)
            edited += 1
    print(f"  diagnostic '{mode}': mis-pointed {edited} wrap records "
          f"(same file size; all other bytes unchanged)")
    return bytes(buf)


def set_gravity(payload, gx, gy, gz):
    """Return a modified payload with every ClothPropertiesGravity (section 4398,
    a bare Vector3) set to (gx,gy,gz). Section 4398 is the DEDICATED gravity field and
    the live-candidate; the gravity inside ClothProperties (4357) is verified INERT at
    GRB runtime (2026-07-02), so this edits 4398 instead. Whether 4398 is runtime-
    effective is the current open in-game test (meta/next-session.md). Same size.
    (Tip: reverse gravity by negating the vanilla vector, e.g. (0,0,-10) -> (0,0,10),
    for an unmissable hem-up vs hem-down tell on a loose garment.)"""
    buf = payload; n = 0
    for pkg in mc.locate_clothpackages(buf):
        changed = False
        for body in pkg.bodies:
            s = body.find(4398)                       # ClothPropertiesGravity (dedicated)
            if s and len(s.payload) >= 12:
                pl = bytearray(s.payload)
                struct.pack_into("<3f", pl, 0, gx, gy, gz)   # bare Vector3 @ offset 0
                s.payload = bytes(pl); changed = True; n += 1
        if changed:
            nb = pkg.to_bytes()
            assert len(nb) == pkg.end - pkg.start, "gravity edit changed length"
            buf = buf[:pkg.start] + nb + buf[pkg.end:]
    print(f"  gravity set to ({gx},{gy},{gz}) in {n} ClothPropertiesGravity (4398) section(s)")
    if n == 0:
        print("  (note: no section-4398 found in this cloth; nothing changed. 4357 is inert - not edited.)")
    return buf


# ---- write the modified resource back into a .data container GRB can LOAD ----
# GRB REQUIRES Oodle-compressed blocks: a raw/uncompressed .data parses in ATK but the
# game crashes/hangs at load. So we re-compress each 32 KB chunk (Oodle Mermaid) with
# per-block checksum = adler32(compressed, seed=0). See docs/02 + meta/research-log.md
# (2026-07-02: "the real load-blocker was RAW vs Oodle-compressed .data").

_DATA_MAGIC = 1154322941026740787
_BLK = 32768


def _split_cfds(raw, oodle):
    """Return (cfd1_bytes_verbatim, files_content) from a compressed cloth .data."""
    import ctypes
    oo = ctypes.WinDLL(oodle); dec = oo.OodleLZ_Decompress; dec.restype = ctypes.c_longlong
    dec.argtypes = [ctypes.c_char_p, ctypes.c_longlong, ctypes.c_char_p, ctypes.c_longlong,
                    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_longlong,
                    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_longlong, ctypes.c_int]
    off = [0]
    def rd(fmt):
        v = struct.unpack_from("<" + fmt, raw, off[0]); off[0] += struct.calcsize("<" + fmt); return v
    def read_cfd():
        start = off[0]
        rd("Q"); rd("h"); rd("B"); rd("H"); rd("H"); nb = rd("i")[0]
        infos = [(rd("i")[0], rd("i")[0]) for _ in range(nb)]
        out = bytearray()
        for un, cn in infos:
            rd("I"); blk = raw[off[0]:off[0] + cn]; off[0] += cn
            if un == cn:
                out += blk
            else:
                dst = ctypes.create_string_buffer(un)
                dec(blk, cn, dst, un, 1, 0, 0, None, 0, None, None, None, 0, 3)
                out += dst.raw[:un]
        return start, off[0], bytes(out)
    s1, e1, _meta = read_cfd()
    s2, e2, files = read_cfd()
    return raw[s1:e1], files


def _build_compressed_cfd(files_content, oodle):
    """Build a CompressedFileData block GRB can LOAD: each 32 KB chunk Oodle-Mermaid-
    compressed via the game's oo2core DLL, per-block checksum = adler32(compressed,
    seed=0). (zlib's default adler seed is 1 — GRB seeds 0; that detail matters.)"""
    import zlib, ctypes
    oo = ctypes.WinDLL(oodle)
    comp = oo.OodleLZ_Compress
    comp.restype = ctypes.c_longlong
    comp.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_longlong, ctypes.c_char_p,
                     ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                     ctypes.c_void_p, ctypes.c_longlong]

    def _c(chunk):
        dst = ctypes.create_string_buffer(len(chunk) + 1024)
        n = comp(9, chunk, len(chunk), dst, 4, None, None, None, None, 0)  # 9=Mermaid, 4=Normal
        return chunk if (n <= 0 or n >= len(chunk)) else dst.raw[:n]        # store raw if no gain

    chunks = [files_content[i:i + _BLK] for i in range(0, len(files_content), _BLK)] or [b""]
    stored = [(len(c), _c(c)) for c in chunks]
    hdr = struct.pack("<Q", _DATA_MAGIC) + struct.pack("<hBHH", 3, 3, 0, _BLK)  # ver=3, algo=3
    hdr += struct.pack("<i", len(stored))
    for un, cc in stored:
        hdr += struct.pack("<ii", un, len(cc))
    body = bytearray()
    for un, cc in stored:
        body += struct.pack("<I", zlib.adler32(cc, 0) & 0xffffffff) + cc    # adler seed=0
    return bytes(hdr) + bytes(body)


def write_data(orig_data_path, new_resource, out_path, oodle):
    """Rebuild `orig_data_path` (a compressed cloth .data) with `new_resource`
    (same-length modified resource bytes) and write to out_path. Verifies it reads
    back. Drop the result into your unpacked forge folder (same filename) and
    repack the forge in ATK."""
    raw = open(orig_data_path, "rb").read()
    cfd1, files = _split_cfds(raw, oodle)
    p = 0
    struct.unpack_from("<I", files, p); p += 4
    L = struct.unpack_from("<i", files, p)[0]; p += 4
    sl = struct.unpack_from("<i", files, p)[0]; p += 4; p += sl
    if len(new_resource) != L:
        raise SystemExit(f"resource length changed ({len(new_resource)} != {L}); edits must be same-size")
    new_files = files[:p] + new_resource + files[p + L:]
    open(out_path, "wb").write(cfd1 + _build_compressed_cfd(new_files, oodle))
    if mc.load_resource_payload(out_path, oodle) != new_resource:
        raise SystemExit("round-trip check FAILED - not writing a bad .data")
    return out_path


def _is_data(path):
    raw = open(path, "rb").read(8)
    return len(raw) >= 8 and struct.unpack("<Q", raw)[0] == _DATA_MAGIC


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    oodle = None
    if "--oodle" in argv:
        k = argv.index("--oodle"); oodle = argv[k + 1]; del argv[k:k + 2]
    out = None
    if "--out" in argv:
        k = argv.index("--out"); out = argv[k + 1]; del argv[k:k + 2]
    mode = None
    if "--diagnostic" in argv:
        k = argv.index("--diagnostic"); mode = argv[k + 1]; del argv[k:k + 2]
    grav = None
    if "--gravity" in argv:
        k = argv.index("--gravity"); grav = tuple(float(x) for x in argv[k + 1].split(",")); del argv[k:k + 2]
    args = argv[1:]
    if not args:
        print(__doc__); return
    src = args[0]
    payload = mc.load_resource_payload(src, oodle)

    if not mode and grav is None:
        print(inspect(payload)); return

    # apply the requested edit(s)
    tag = "edit"
    newp = payload
    if grav is not None:
        newp = set_gravity(newp, *grav); tag = "grav"
    if mode:
        newp = diagnostic(newp, mode); tag = mode

    # write out - a .data if the source was a .data (drop-in for forge repack), else a .Cloth
    is_data = _is_data(src)
    if not out:
        base = os.path.splitext(src)[0]
        out = f"{base}.{tag}.data" if is_data else f"{base}.{tag}.Cloth"
    if is_data:
        write_data(src, newp, out, oodle)
    else:
        open(out, "wb").write(newp)
    print(f"  wrote {out}")
    print("  -> put this in your unpacked forge folder (same filename as the original")
    print("     entry), repack the forge in ATK on a BACKED-UP install, and load GRB.")
    print("     NOTE: --gravity edits the dedicated 4398 section (4357 is inert at runtime);")
    print("     whether 4398 moves a loose garment in-game is the current open test.")


if __name__ == "__main__":
    main(sys.argv)
