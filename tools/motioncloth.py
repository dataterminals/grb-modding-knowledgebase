#!/usr/bin/env python3
"""
motioncloth.py - accurate reader/writer for GRB MotionCloth (`ClothPackage`) data.

This is the *precise* engine (unlike the approximate cloth_inspect.py magic-scan):
it locates every ClothPackage in a cloth resource, walks its MotionBody sections
by their self-declared sizes (validating the 0xECD7 marker), decodes the pieces
that matter, and can re-serialize byte-for-byte. That exactness is what a
render<->sim remap needs (edit a few sections, rewrite, keep everything else).

What it's for (plain version): a GRB "cloth" file describes the *simulated* cloth
(a mesh of points + springs) and, for some garments, how the *visible* garment is
pinned onto that simulated mesh. This reads all of that out reliably, and lets a
program change it and write it back.

Works on:
  * a decompressed cloth resource - the `*.Cloth` file ATK writes when you unpack
    a cloth `.data` (recommended input), or
  * a cloth `.data` directly (it will Oodle-decompress via the game DLL; pass
    --oodle <path to oo2core_7_win64.dll> or let it auto-find).

    python motioncloth.py  30091_-_..._Cloth        # or a .Cloth / .data file
    python motioncloth.py  foo.Cloth --roundtrip     # verify byte-exact rewrite

Format (verified from ATK v1.3.1 ClothPackage / MotionBody / MotionSectionFactory):
ClothPackage = int32 bodyCount, then per body: int32 blobLen + blob. A blob is a
run of TLV sections until it ends: uint16 type, uint16 0xECD7, int32 sizeInclHdr,
payload[size-8]. See docs/11-cloth-and-physics.md and reference/cloth-section-types.md.
"""
import sys, os, struct

MAGIC = 0xECD7

SECTION_NAMES = {
    513: "NamedObjectName", 4353: "ClothType", 4354: "ClothUserData",
    4356: "ClothDefinition", 4357: "ClothProperties",
    4363: "ClothVerticesCurrentPosition", 4364: "ClothConstraintsSizes",
    4365: "ClothConstraints", 4370: "ClothMeshIndexBufferSize",
    4371: "ClothMeshIndexBuffer", 4381: "ClothStretchingConstraintsCount",
    4394: "ClothStretchingConstraints", 4395: "ClothPropertiesMeshMappings",
    4397: "ClothPropertiesWind", 4433: "ClothPresets",
    4529: "ClothPerVertexDataDefinition", 4530: "ClothPerVertexDataCounters",
    4531: "ClothPerVertexDataBuffer",
    4561: "ClothAdditionalVerticesCounters",
    4562: "ClothAdditionalVerticesTriangleVerticesCount",
    4563: "ClothAdditionalVerticesTriangleFirstVertexIndex",
    4564: "ClothAdditionalVerticesBarycentricCoordinatesParameters",
    4565: "ClothAdditionalVerticesBarycentricCoordinatesData",
    4658: "ClothEditorDataClothID",
}


class Section:
    __slots__ = ("type", "payload")

    def __init__(self, type_, payload):
        self.type = type_
        self.payload = payload

    def to_bytes(self):
        return struct.pack("<HHi", self.type, MAGIC, len(self.payload) + 8) + self.payload

    @property
    def name(self):
        return SECTION_NAMES.get(self.type, f"#{self.type}")


class MotionBody:
    def __init__(self, sections):
        self.sections = sections

    def to_bytes(self):
        return b"".join(s.to_bytes() for s in self.sections)

    def find(self, type_):
        return next((s for s in self.sections if s.type == type_), None)


class ClothPackage:
    """One ClothPackage (one cloth LOD) located within a resource, with its byte span."""
    def __init__(self, start, end, bodies):
        self.start = start        # byte offset of the int32 bodyCount, in the resource
        self.end = end            # byte offset just past the last body
        self.bodies = bodies      # list[MotionBody]

    def to_bytes(self):
        out = bytearray(struct.pack("<i", len(self.bodies)))
        for body in self.bodies:
            blob = body.to_bytes()
            out += struct.pack("<i", len(blob)) + blob
        return bytes(out)


def _parse_body(buf, start, end):
    """Walk sections from start..end; must consume exactly to end. Return list[Section] or None."""
    sections = []
    p = start
    while p < end:
        if p + 8 > end:
            return None
        t, mg, size = struct.unpack_from("<HHi", buf, p)
        if mg != MAGIC or size < 8 or p + size > end:
            return None
        sections.append(Section(t, buf[p + 8:p + size]))
        p += size
    return sections if p == end else None


def _try_clothpackage_at(buf, first_section_off):
    """Given a candidate first-section offset, validate a whole ClothPackage. Return ClothPackage or None."""
    cps = first_section_off - 8            # int32 count + int32 body0len precede the first section
    if cps < 0:
        return None
    count = struct.unpack_from("<i", buf, cps)[0]
    if not (1 <= count <= 16):
        return None
    q = cps + 4
    bodies = []
    for _ in range(count):
        if q + 4 > len(buf):
            return None
        blen = struct.unpack_from("<i", buf, q)[0]
        q += 4
        if blen < 8 or q + blen > len(buf):
            return None
        secs = _parse_body(buf, q, q + blen)
        if secs is None:
            return None
        bodies.append(MotionBody(secs))
        q += blen
    return ClothPackage(cps, q, bodies)


def locate_clothpackages(buf):
    """Find every ClothPackage in a resource payload (one per cloth LOD)."""
    packages = []
    p = 2
    n = len(buf)
    while p < n - 4:
        if buf[p + 2] == 0xD7 and buf[p + 3] == 0xEC:   # a section's 0xECD7 marker
            pkg = _try_clothpackage_at(buf, p)
            if pkg is not None:
                packages.append(pkg)
                p = pkg.end            # skip past it; next scan finds the next LOD
                continue
        p += 1
    return packages


def splice(buf, package, new_bytes):
    """Return a new resource payload with `package`'s bytes replaced by new_bytes."""
    return buf[:package.start] + new_bytes + buf[package.end:]


# ---- convenience decoders (only the fields we currently need) ----

def body_name(body):
    s = body.find(513)
    if not s:
        return None
    z = s.payload.find(b"\0")
    return s.payload[:z if z >= 0 else len(s.payload)].decode("latin-1", "replace")


def sim_vertex_count(body):
    s = body.find(4354)
    return struct.unpack_from("<i", s.payload, 0)[0] if s else None


def sim_triangle_count(body):
    s = body.find(4370)
    return struct.unpack_from("<i", s.payload, 0)[0] if s else None


def uses_barycentric(body):
    return body.find(4565) is not None


def additional_vertices_count(body):
    s = body.find(4561)
    return struct.unpack_from("<i", s.payload, 0)[0] if s else None


# ---- input loading (.Cloth payload, or .data via Oodle) ----

def load_resource_payload(path, oodle_dll=None):
    """Return the decompressed resource bytes for a .Cloth file or a cloth .data."""
    raw = open(path, "rb").read()
    if raw[:8] == b"scimitar":
        raise ValueError("that's a .forge, not a cloth resource")
    # A .data begins with the CompressedFileData magic; a .Cloth resource does not.
    magic = struct.unpack_from("<Q", raw, 0)[0] if len(raw) >= 8 else 0
    if magic != 1154322941026740787:
        return raw                     # already a decompressed resource (.Cloth)
    # It's a .data: decompress its two blocks and pull the single resource payload.
    import ctypes
    if oodle_dll is None:
        d = os.path.dirname(os.path.abspath(path))
        for _ in range(8):
            c = os.path.join(d, "oo2core_7_win64.dll")
            if os.path.isfile(c):
                oodle_dll = c
                break
            nd = os.path.dirname(d)
            if nd == d:
                break
            d = nd
    if not oodle_dll:
        raise RuntimeError("cloth .data is Oodle-compressed; pass --oodle <oo2core_7_win64.dll>")
    oo = ctypes.WinDLL(oodle_dll)
    dec = oo.OodleLZ_Decompress
    dec.restype = ctypes.c_longlong
    dec.argtypes = [ctypes.c_char_p, ctypes.c_longlong, ctypes.c_char_p, ctypes.c_longlong,
                    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_longlong,
                    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_longlong, ctypes.c_int]
    off = [0]

    def rd(fmt):
        v = struct.unpack_from("<" + fmt, raw, off[0]); off[0] += struct.calcsize("<" + fmt); return v

    def cfd():
        rd("Q"); rd("h"); rd("B"); rd("H"); rd("H"); nb = rd("i")[0]
        infos = [(rd("i")[0], rd("i")[0]) for _ in range(nb)]
        out = bytearray()
        for un, cn in infos:
            rd("I"); blk = raw[off[0]:off[0] + cn]; off[0] += cn
            if un == cn:
                out += blk
            else:
                dst = ctypes.create_string_buffer(un)
                if dec(blk, cn, dst, un, 1, 0, 0, None, 0, None, None, None, 0, 3) != un:
                    raise RuntimeError("Oodle decompress failed")
                out += dst.raw[:un]
        return bytes(out)

    cfd()
    files = cfd()
    p = 0
    struct.unpack_from("<I", files, p); p += 4
    L = struct.unpack_from("<i", files, p)[0]; p += 4
    sl = struct.unpack_from("<i", files, p)[0]; p += 4; p += sl
    return files[p:p + L]


def roundtrip_ok(payload):
    """True if re-serializing every located ClothPackage from decoded sections reproduces the bytes."""
    for pkg in locate_clothpackages(payload):
        if pkg.to_bytes() != payload[pkg.start:pkg.end]:
            return False
    return True


def report(path, oodle_dll=None):
    payload = load_resource_payload(path, oodle_dll)
    pkgs = locate_clothpackages(payload)
    L = ["=" * 68, f"CLOTH: {os.path.basename(path)}"]
    if not pkgs:
        L.append("  No ClothPackage found - is this a GRB cloth resource?")
        return "\n".join(L) + "\n"
    L.append(f"  {len(pkgs)} cloth LOD(s) in this file.")
    for i, pkg in enumerate(pkgs):
        for body in pkg.bodies:
            nm = body_name(body) or "(unnamed)"
            sv, tr = sim_vertex_count(body), sim_triangle_count(body)
            L.append(f"  - LOD{i}: {nm}")
            L.append(f"      simulated mesh: {sv} points, {tr} triangles   ({len(body.sections)} data sections)")
            if uses_barycentric(body):
                L.append(f"      binding: the visible garment is pinned onto the sim mesh "
                         f"(barycentric). A new mesh needs its pinning recomputed.")
            else:
                L.append(f"      binding: DIRECT - the visible mesh IS the sim mesh. A new mesh "
                         f"must keep the same {sv} points in the same order.")
    L.append(f"  rewrite check (byte-for-byte): {'OK' if roundtrip_ok(payload) else 'FAILED'}")
    return "\n".join(L) + "\n"


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    oodle = None
    if "--oodle" in argv:
        k = argv.index("--oodle"); oodle = argv[k + 1]; del argv[k:k + 2]
    do_rt = "--roundtrip" in argv
    if do_rt:
        argv.remove("--roundtrip")
    args = argv[1:]
    if not args:
        print(__doc__); return
    for p in args:
        if do_rt:
            payload = load_resource_payload(p, oodle)
            n = len(locate_clothpackages(payload))
            print(f"{os.path.basename(p)}: {n} ClothPackage(s), round-trip "
                  f"{'OK' if roundtrip_ok(payload) else 'FAILED'}")
        else:
            print(report(p, oodle))


if __name__ == "__main__":
    main(sys.argv)
