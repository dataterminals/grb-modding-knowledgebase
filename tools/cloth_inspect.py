#!/usr/bin/env python3
"""
cloth_inspect.py — inspect / diff GRB MotionCloth (.cloth) resources.

Reads a raw unpacked `<id>_-_<name>.data` cloth resource (uncompressed GRB data)
and reports its MotionCloth structure: body names, ClothIDs, and a histogram of
section types. Pass two files to diff them.

    python cloth_inspect.py cloth_a.data [cloth_b.data]

Prefer the friendly GUI (no command line needed): run cloth_inspect_gui.py,
or the "Cloth Inspector (GUI).bat" launcher. See tools/README.md.

HOW IT WORKS / LIMITATIONS (read this):
- MotionCloth sections are TLV chunks: [type u16][magic 0xECD7][size][payload].
  See docs/11-cloth-and-physics.md.
- This tool finds sections by scanning for the 0xECD7 magic and keeping matches
  whose preceding u16 is a KNOWN section type. That is robust for enumerating
  which bodies exist and for reading string fields (names, ClothIDs) — usually
  exactly what you want.
- It is APPROXIMATE for exact section counts: the byte 0xECD7 can occur by chance
  inside a payload (float/index buffers), producing a few false positives. A
  fully accurate parser must implement MotionSectionFactory's counter->buffer
  size dependencies (buffer section lengths come from earlier counter sections),
  tracked as future work in meta/research-log.md.
- Cloth "weight" is VertexMaxDistance, exported by ATK to GLB vertex color Color1
  (0 = pinned, higher = free). It is not shown as a section value here.
"""
import struct, sys, os

def u16(b, o): return struct.unpack_from('<H', b, o)[0]

SECN = {
 513:'NamedObjectName', 3073:'BodyType', 3074:'BodyIndexInIsland', 3076:'BodyUserData',
 3077:'BodyBroadPhase', 3078:'BodyData', 3080:'BodyColor', 3083:'BodyTransform',
 3085:'BodyIndexInIslandExtra', 4353:'ClothType', 4354:'ClothUserData', 4356:'ClothDefinition',
 4357:'ClothProperties', 4359:'ClothPropConstraintsEnable', 4360:'ClothPropConstraintsStiffness',
 4361:'ClothEngineLoopStepCount', 4362:'ClothEngineLoop', 4363:'ClothVerticesCurrentPosition',
 4364:'ClothConstraintsSizes', 4365:'ClothConstraints', 4366:'ClothConstraintsSIMDF8',
 4369:'ClothMeshConstraintsOptCount', 4370:'ClothMeshIndexBufferSize', 4371:'ClothMeshIndexBuffer',
 4373:'ClothAABox', 4378:'ClothPropCorrectionFactors', 4381:'ClothStretchConstraintsCount',
 4382:'ClothMeshAABBTree', 4384:'ClothMeshHasVertexAABBTree', 4385:'ClothMeshHasTriangleAABBTree',
 4387:'ClothMeshConstraintsSizes', 4388:'ClothMeshConstraints', 4394:'ClothStretchingConstraints',
 4395:'ClothPropMeshMappings', 4396:'ClothPropLod', 4397:'ClothPropWind', 4398:'ClothPropGravity',
 4399:'ClothPropAzimuthAnim', 4400:'ClothPropInclinationAnim', 4401:'ClothPropRadiusAnim',
 4415:'ClothConstraintsScaleFactor', 4433:'ClothPresets', 4434:'ClothPresetsCount',
 4435:'ClothPresetDefinition', 4436:'ClothPresetBufferSize', 4443:'ClothPresetDefPerVertexData',
 4444:'ClothPresetPerVertexDataSize', 4465:'ClothRegisteredCollidersCount',
 4529:'ClothPerVertexDataDefinition', 4530:'ClothPerVertexDataCounters', 4531:'ClothPerVertexDataBuffer',
 4532:'ClothPerVertexDataSIMDF8', 4561:'ClothAddVertsCounters', 4562:'ClothAddVertsTriVertCount',
 4563:'ClothAddVertsTriFirstVertIdx', 4564:'ClothAddVertsBaryParams', 4565:'ClothAddVertsBaryData',
 4657:'ClothEditorData', 4658:'ClothEditorDataClothID', 4659:'ClothEditorDataVisibility',
 4661:'ClothEditorDataCollisionEnabledColliders', 4662:'ClothEditorDataPresetsNames',
 4833:'ClothStripsUntwistIdxCount', 4834:'ClothStripsUntwistIdx',
}
SEC = set(SECN)

# What plain-English lesson each body-name pattern hints at.
def read_body_purpose(name):
    n = name.lower()
    if '_cin' in n or 'cinematic' in n: return 'cinematic (cutscene) cloth'
    if n.startswith('sim_tp') or '_tp_' in n or n.startswith('sim_ftp'): return 'gameplay / wearable cloth'
    return ''

def cstr(b, o):
    e = o
    while e < len(b) and b[e] != 0: e += 1
    return b[o:e].decode('latin-1', 'replace')

def scan(b):
    """Yield (type, payload_offset) for magics preceded by a known section type."""
    for q in range(2, len(b) - 1):
        if b[q] == 0xD7 and b[q + 1] == 0xEC and u16(b, q - 2) in SEC:
            yield u16(b, q - 2), q + 4     # payload starts 4 bytes past the magic byte

def parse(path):
    """Return a dict describing the cloth resource. Raises on read errors."""
    b = open(path, 'rb').read()
    hist, names, ids = {}, [], []
    for t, po in scan(b):
        hist[t] = hist.get(t, 0) + 1
        if t == 513:  names.append(cstr(b, po))
        if t == 4658:
            s = cstr(b, po).strip('\x00\x01\x02\x03\x04\x05 ')
            if s: ids.append(s)
    return dict(path=path, size=len(b), names=names, ids=ids, hist=hist)

def _clean_name(n):
    # body names look like Sim_<Mesh>_LOD<n>_0x<hash>_<i>; trim the trailing hash/index
    import re
    m = re.match(r'(.*?_LOD\d+)', n)
    return m.group(1) if m else n

def report(path):
    """Human-readable single-file report as a string."""
    try:
        d = parse(path)
    except Exception as e:
        return f"Could not read:\n  {path}\n  {e}\n"
    L = []
    L.append("=" * 70)
    L.append(f"FILE: {os.path.basename(path)}   ({d['size']:,} bytes)")
    if not d['names'] and not d['hist']:
        L.append("  No MotionCloth sections found.")
        L.append("  Is this actually a .cloth resource? (It should be a GRB")
        L.append("  cloth .data, e.g. a file named like *_Cloth or Cloth_*.)")
        return "\n".join(L) + "\n"
    L.append(f"  Cloth bodies (simulated pieces): {len(d['names'])}")
    for n in d['names']:
        clean = _clean_name(n)
        purpose = read_body_purpose(n)
        tail = f"   [{purpose}]" if purpose else ""
        L.append(f"    - {clean}{tail}")
        if clean != n:
            L.append(f"        (full name: {n})")
    L.append("")
    L.append("  A body name reads as  Sim_<TargetMesh>_LOD<n>  - it tells you the")
    L.append("  exact mesh + LOD this cloth is bound to. Match your mod to that.")
    if d['ids']:
        L.append("")
        L.append("  ClothID / collider data:")
        for s in d['ids']:
            L.append(f"    - {s[:120]}")
    L.append("")
    L.append(f"  Section types present (approximate counts):")
    for t in sorted(d['hist']):
        L.append(f"    {SECN[t]:40} x{d['hist'][t]}")
    # a couple of friendly highlights
    hl = []
    if 4397 in d['hist']: hl.append("has WIND response (ClothPropWind)")
    if 4365 in d['hist'] or 4364 in d['hist']: hl.append("carries constraint buffers")
    if 4433 in d['hist']: hl.append("has tuning presets")
    if hl:
        L.append("")
        L.append("  Highlights: " + "; ".join(hl))
    return "\n".join(L) + "\n"

def diff(path_a, path_b):
    """Report for both files plus a section-type histogram diff."""
    out = [report(path_a), report(path_b)]
    try:
        a, b = parse(path_a), parse(path_b)
    except Exception as e:
        return "\n".join(out) + f"\n(diff skipped: {e})\n"
    ha, hb = a['hist'], b['hist']
    out.append("=" * 70)
    out.append("SIDE-BY-SIDE SECTION COMPARISON  (A = first file, B = second)")
    out.append(f"  A = {os.path.basename(path_a)}")
    out.append(f"  B = {os.path.basename(path_b)}")
    out.append("")
    out.append(f"  {'section type':40} {'A':>4} {'B':>4}")
    out.append(f"  {'-'*40} {'-'*4} {'-'*4}")
    for t in sorted(set(ha) | set(hb)):
        ca, cb = ha.get(t, 0), hb.get(t, 0)
        mark = "" if ca == cb else "   <- differs"
        out.append(f"  {SECN[t]:40} {ca:>4} {cb:>4}{mark}")
    return "\n".join(out) + "\n"

def main(argv):
    if len(argv) == 2:
        print(report(argv[1]))
    elif len(argv) >= 3:
        print(diff(argv[1], argv[2]))
    else:
        print(__doc__)

if __name__ == '__main__':
    main(sys.argv)
