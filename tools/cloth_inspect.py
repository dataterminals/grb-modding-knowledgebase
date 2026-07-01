#!/usr/bin/env python3
"""
cloth_inspect.py — inspect / diff GRB MotionCloth (.cloth) resources.

Reads a raw unpacked `<id>_-_<name>.data` cloth resource (uncompressed GRB data)
and reports its MotionCloth structure: body names, ClothIDs, and a histogram of
section types. Pass two files to diff them.

    python cloth_inspect.py cloth_a.data [cloth_b.data]

HOW IT WORKS / LIMITATIONS (read this):
- MotionCloth sections are TLV chunks: [type u16][magic 0xECD7][size ...][payload].
  See docs/11-cloth-and-physics.md.
- This tool finds sections by scanning for the 0xECD7 magic and keeping matches
  whose preceding u16 is a KNOWN section type. That is robust for enumerating
  which sections/bodies exist and for reading string fields (names, ClothIDs),
  which is what you usually want.
- It is APPROXIMATE for exact section counts: the byte 0xECD7 can occur by chance
  inside a payload (e.g. float/index buffers), producing a few false positives.
  A fully accurate parser must implement MotionSectionFactory's counter->buffer
  size dependencies (buffer section lengths come from earlier counter sections),
  which is tracked as future work in meta/research-log.md.
- Cloth "weight" is VertexMaxDistance, exported by ATK to GLB vertex color Color1
  (0 = pinned, higher = free). It is not stored as a section value here.
"""
import struct, sys, os

def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def i32(b, o): return struct.unpack_from('<i', b, o)[0]

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

def cstr(b, o):
    e = o
    while e < len(b) and b[e] != 0: e += 1
    return b[o:e].decode('latin-1', 'replace')

def scan(b):
    """Yield (type, payload_offset) for magics preceded by a known section type."""
    for q in range(2, len(b) - 1):
        if b[q] == 0xD7 and b[q + 1] == 0xEC and u16(b, q - 2) in SEC:
            yield u16(b, q - 2), q + 4     # payload starts 4 bytes past the magic byte

def inspect(path):
    b = open(path, 'rb').read()
    hist, names, ids = {}, [], []
    for t, po in scan(b):
        hist[t] = hist.get(t, 0) + 1
        if t == 513:  names.append(cstr(b, po))
        if t == 4658: ids.append(cstr(b, po))
    print('=' * 78)
    print(f'{os.path.basename(path)}  ({len(b)} bytes)')
    print(f'  bodies (NamedObjectName): {len(names)}')
    for n in names: print(f'    - {n}')
    if any(ids): print(f'  ClothIDs: {[x for x in ids if x]}')
    print(f'  section types seen: {len(hist)}  (approx counts)')
    return hist

def main(argv):
    if len(argv) < 2:
        print(__doc__); return
    ha = inspect(argv[1])
    if len(argv) >= 3:
        hb = inspect(argv[2])
        print('=' * 78); print('SECTION-TYPE HISTOGRAM DIFF  (A vs B, approximate)')
        for t in sorted(set(ha) | set(hb)):
            a, bb = ha.get(t, 0), hb.get(t, 0)
            print(f'  {t:5} {SECN[t]:40} A={a:3} B={bb:3}{"" if a == bb else "  <-- differs"}')

if __name__ == '__main__':
    main(sys.argv)
