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

Input/output: a decompressed *.Cloth resource (what ATK writes when you unpack a
cloth's .data), or a cloth .data (auto-Oodle via the game DLL). Diagnostic edits
are same-size and in-place, so everything outside the sim-index bytes is preserved
byte-for-byte.

Usage:
  python clothwrap.py cloth.Cloth                         # inspect the wrap
  python clothwrap.py cloth.Cloth --diagnostic twist   --out broken.Cloth
  python clothwrap.py cloth.Cloth --diagnostic collapse --out broken.Cloth
  python clothwrap.py cloth.data  --oodle oo2core_7_win64.dll --diagnostic twist --out broken.Cloth
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
    args = argv[1:]
    if not args:
        print(__doc__); return
    payload = mc.load_resource_payload(args[0], oodle)
    if mode:
        newp = diagnostic(payload, mode)
        if not out:
            out = os.path.splitext(args[0])[0] + f".{mode}.Cloth"
        open(out, "wb").write(newp)
        print(f"  wrote {out}")
        print("  Re-import this with ATK (repack into a PATCH forge on a backed-up")
        print("  install), load GRB, and view the garment. Visible distortion")
        print("  confirms the wrap drives the visible mesh.")
    else:
        print(inspect(payload))


if __name__ == "__main__":
    main(sys.argv)
