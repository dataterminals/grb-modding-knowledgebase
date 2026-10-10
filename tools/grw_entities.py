#!/usr/bin/env python3
"""
grw_entities.py - convert Ghost Recon Wildlands world objects (the entity layer) into Ghost Recon
Breakpoint's serialization: Entity, EntityGroup, LODSelector, GridCellDataBlock, SpotLight,
OmniLight, AreaLight, and the components and inline objects they carry.

Companion to grw2grb.py, which converts meshes and textures. The rules here were derived the
same way: from resources both games ship under one ClassID ("twins"). `selftest` re-checks
them by converting each Wildlands twin and comparing the result with Breakpoint's own bytes.

    python grw_entities.py selftest [--world-step 60] [--grb-ghostroom PATH]
    python grw_entities.py scan    <GRW forge> [--step 60]       # how much of a forge converts
    python grw_entities.py convert <GRW entry name|id> -o out_dir  # converted payloads, one file each
        [--drop-grw-only]   leave out GRW-only gameplay components (respawn points, ...) instead of
                            refusing the Entity
        [--strip-physics]   leave out RigidBody, Inert, MergedPhysics and GameplayDestructible components
        [--strip-physics-at MeshShape,...]   only for Entities whose physics reaches one of these shape types
                            (through ReferenceListShape children), or whose body shape is not found
        [--material-remap OLD=NEW,...]   re-point references to OLD at NEW (IDs hex or decimal), e.g. a GRW
                            CollisionMaterial at a GRB-native one; counts per resource go into converted.json
        [--types A,B,...]   convert only these resource types (e.g. BoxShape,CapsuleShape,ConvexVerticesShape)
                            Writes <ClassID>_<type>_<name>.payload per resource and an index, converted.json
                            Dropped components are listed in out_dir/dropped_components.json; an Entity whose
                            ResetData names one gets a null ResetData

Read-only on both installs. Install paths: --grw / --grb, $GRW_INSTALL / $GRB_INSTALL, or the
defaults below. Standard library only (+ the game's Oodle DLL, ATK's lzo.dll for Wildlands blocks,
through data_inspect). Caps its own memory (--max-mb, default 1500) and streams forges entry by entry.

As a library:  decode(payload, "grw"|"grb") -> Obj tree;  encode(obj, game) -> bytes;
               convert(grw_payload, drop_grw_only=False, strip_physics=False, manifest=None,
                       strip_physics_at=None, shape_of=None, remap=None, remapped=None)
                   (raises NeedLayout / Unsupported)

SERIALIZATION (both games; see meta/notes-entities.md)
  object      u64 ClassID | u32 type hash | u8 IsManaged (ManagedObject types) | fields
  pointers    ObjectPtr: u8 ptype (0/4 inline object, 1/2/5 u64 id, 3 null)
              Reference: u8 ptype (0/4 inline, 1 u8 reftype + u64, 2/5 u64, 3 u8 + u64)
              Handle: u8 + u64.   Arrays: u32 count + items.
  anonymous   inline objects without an ID carry 0xF8000000 | ordinal (serialization order).
              GRB renumbers them when objects are dropped, and Link pointers (ptype 2) to them
              follow: `encode` assigns ordinals in output order and remaps links (two passes).

WHAT CONVERTS (2026-10-10; GRW Bolivia world sample, every 60th forge entry)
  LODSelector        100%   twins: 239 = 17 byte-identical + 222 content-only
  GridCellDataBlock  100%   twins: 4 content-only (same layout in both games)
  Spot/Omni/AreaLight 100%  twins: 30 = 2 byte-identical + 27 content-only (+1 GRB-added flare)
  Entity             ~94%   twins: 103 decodable = 21 byte-identical + 82 content-only
  EntityGroup        ~87%   no twin decodable yet
  "content-only": every differing field is one GRB re-baked per asset (bounds, intensities, LOD
  distances, re-pointed references). Component types without a layout raise NeedLayout.
"""
import sys, os, re, glob, struct, zlib, ctypes, collections
from collections import OrderedDict
from ctypes import wintypes

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import data_inspect as di                                              # noqa: E402
import forge_inspect as fi                                             # noqa: E402

GRW_DEFAULT = r"D:\SteamLibrary\steamapps\common\Wildlands"
GRB_DEFAULT = r"H:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint"


def memory_cap(mb):
    """Cap this process's memory (Windows Job Object): past `mb`, allocations raise
    MemoryError instead of swapping the machine."""
    if os.name != "nt":
        return
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class Basic(ctypes.Structure):
        _fields_ = [("a", ctypes.c_longlong), ("b", ctypes.c_longlong), ("LimitFlags", wintypes.DWORD),
                    ("c", ctypes.c_size_t), ("d", ctypes.c_size_t), ("e", wintypes.DWORD),
                    ("f", ctypes.c_size_t), ("g", wintypes.DWORD), ("h", wintypes.DWORD)]

    class Ext(ctypes.Structure):
        _fields_ = [("Basic", Basic), ("IoInfo", ctypes.c_ulonglong * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcess", ctypes.c_size_t), ("PeakJob", ctypes.c_size_t)]

    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    job = k32.CreateJobObjectW(None, None)
    info = Ext(); info.Basic.LimitFlags = 0x100; info.ProcessMemoryLimit = mb << 20
    k32.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))
    k32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(k32.GetCurrentProcess()))
    memory_cap._job = job


# =========================================================================== reader / writer
#
# A layout is a list of (field, kind):
#   fixed      'u8' 'u16' 'u32' 'f32' 'u64' 'v3' 'v4' 'm44' ('raw', n)
#   ('ref',) ('optr',) ('handle',)          pointers, as above
#   ('obj', name|None)                       inline object (header + fields); None = by hash
#   ('arr', kind) ('sarr', n, kind)          SmallArray / StaticArray
#   ('struct', [(field, kind), ...])         an unnamed run of fields (array elements)
#   ('bytes',) ('string',)                   BigArray<u8>; u32 length + bytes (+NUL)

def crc(s):
    return zlib.crc32(s.encode())

FIXED = {"u8": "<B", "u16": "<H", "u32": "<I", "s32": "<i", "f32": "<f", "u64": "<Q"}
RAWN = {"v3": 12, "v4": 16, "m44": 64}
LAYOUT = {"grw": {}, "grb": {}}
MANAGED = set()
NAMES = {}
NEW_ID = 0xF8FFFFFF          # id for objects a converter creates (anonymous, never linked to)


# names of component types seen in the worlds that have no layout yet (for NeedLayout messages)
KNOWN = {crc(n): n for n in (
    "cGameplayDestructibleComponent", "PilotActorComponent", "cSmallLifeTargetComponent",
    "cReactiveResponseComponent", "SoundPropsComponent", "PropsPropertiesComponent", "cElectricDeviceComponent",
    "GR_cSpawnedEntityPhysicActivator_Terrain", "PlayerSpawnActivatorComponent", "cInterestAreaComponent",
    "EventListenerComponent", "HoudiniInstancerComponent", "HoudiniDecalInstancerComponent", "SpaceComponent",
    "GIProbeIndoorVolumeComponent", "SkeletonComponent", "cEntityMessengerDispatcherComponent", "FXComponent",
    "SoundDynEchoReflectorComponent", "SoundWindContextComponent", "cVehicleParkComponent", "AutoFakeEntityComponent",
    "BulkComponent", "SilexNetComponent_LootChest", "SilexNetComponent_InteractiveElement", "cCampComponent",
    "DominoComponent", "cReactionResponseComponent", "SoundRadioReceiverComponent", "AnimComponent")}


def define(game, name, fields, managed=False, h=None):
    """h: the type hash, for types whose real name is unknown (name is then a placeholder)."""
    LAYOUT[game][name] = fields
    NAMES[crc(name) if h is None else h] = name
    if managed:
        MANAGED.add(name)


def is_anon(id_):
    return id_ >> 24 == 0xF8


class NeedLayout(Exception):
    """The payload holds an object type this module has no layout for."""


class Unsupported(Exception):
    """Decodes, but no rule converts this value (e.g. an unknown enum value)."""


class Obj:
    __slots__ = ("id", "hash", "managed", "f")

    def __init__(self, id_, h, managed=None, f=None):
        self.id, self.hash, self.managed = id_, h, managed
        self.f = f if f is not None else OrderedDict()

    @property
    def name(self):
        return NAMES.get(self.hash, f"#{self.hash:08x}")

    def __repr__(self):
        return f"Obj({self.name}, {self.id:#x})"


class Ptr:
    __slots__ = ("ptype", "rtype", "id", "obj")

    def __init__(self, ptype, rtype=None, id_=None, obj=None):
        self.ptype, self.rtype, self.id, self.obj = ptype, rtype, id_, obj

    def __repr__(self):
        return f"Ptr({self.ptype}, r={self.rtype}, id={self.id}, obj={self.obj})"


class Reader:
    def __init__(self, b, game):
        self.b, self.o, self.game = b, 0, game

    def fx(self, fmt):
        v = struct.unpack_from(fmt, self.b, self.o)[0]
        self.o += struct.calcsize(fmt)
        return v

    def raw(self, n):
        if self.o + n > len(self.b):
            raise ValueError(f"read past end at {self.o}+{n}")
        v = self.b[self.o:self.o + n]; self.o += n
        return v

    def value(self, kind):
        if isinstance(kind, str):
            return self.fx(FIXED[kind]) if kind in FIXED else self.raw(RAWN[kind])
        k = kind[0]
        if k == "raw":
            return self.raw(kind[1])
        if k in ("ref", "optr"):
            pt = self.fx("<B")
            if pt in (0, 4):
                return Ptr(pt, obj=self.obj(None))
            if k == "ref" and pt in (1, 3):
                return Ptr(pt, self.fx("<B"), self.fx("<Q"))
            if pt in (1, 2, 5):
                return Ptr(pt, id_=self.fx("<Q"))
            if pt == 3:
                return Ptr(pt)
            raise ValueError(f"bad pointer type {pt} at {self.o - 1}")
        if k == "handle":
            return Ptr(self.fx("<B"), id_=self.fx("<Q"))
        if k == "obj":
            return self.obj(kind[1])
        if k == "struct":
            return OrderedDict((n, self.value(kk)) for n, kk in kind[1])
        if k == "arr":
            n = self.fx("<i")
            if not 0 <= n <= 1_000_000:
                raise ValueError(f"bad array count {n} at {self.o - 4}")
            return [self.value(kind[1]) for _ in range(n)]
        if k == "sarr":
            return [self.value(kind[2]) for _ in range(kind[1])]
        if k == "bytes":
            n = self.fx("<i")
            if not 0 <= n <= 50_000_000:
                raise ValueError(f"bad byte-array length {n} at {self.o - 4}")
            return self.raw(n)
        if k == "string":
            n = self.fx("<i"); s = self.raw(n)
            if n:
                self.raw(1)
            return s
        raise ValueError(f"unknown kind {kind}")

    def obj(self, expect=None):
        start = self.o
        id_ = self.fx("<Q"); h = self.fx("<I")
        name = NAMES.get(h)
        if expect is not None and NAMES.get(h) != expect:     # by name: placeholder-named types have no CRC
            raise ValueError(f"expected {expect} at {start}, got {name or hex(h)}")
        if name is None or name not in LAYOUT[self.game]:
            e = NeedLayout(f"{self.game}:{name or KNOWN.get(h) or format(h, '#010x')}")
            e.type_hash, e.at = h, start
            raise e
        o = Obj(id_, h)
        if name in MANAGED:
            o.managed = self.fx("<B")
        for fname, kind in LAYOUT[self.game][name]:
            o.f[fname] = self.value(kind)
        return o


def decode(payload, game):
    """Payload bytes -> Obj tree, under `game`'s layouts ("grw" or "grb"). Must consume it all."""
    r = Reader(payload, game)
    o = r.obj(None)
    if r.o != len(payload):
        raise ValueError(f"decode stopped at {r.o} of {len(payload)}")
    return o


class Writer:
    def __init__(self, game, order, remap):
        self.game, self.out, self.order, self.remap = game, bytearray(), order, remap

    def value(self, kind, v):
        if isinstance(kind, str):
            if kind in FIXED:
                self.out += struct.pack(FIXED[kind], v)
            else:
                assert len(v) == RAWN[kind]; self.out += v
            return
        k = kind[0]
        if k == "raw":
            assert len(v) == kind[1]; self.out += v
        elif k in ("ref", "optr", "handle"):
            self.out += struct.pack("<B", v.ptype)
            if k == "handle":
                self.out += struct.pack("<Q", v.id)
            elif v.ptype in (0, 4):
                self.obj(v.obj)
            elif k == "ref" and v.ptype in (1, 3):
                self.out += struct.pack("<BQ", v.rtype, v.id)
            elif v.ptype in (2, 5) and is_anon(v.id):       # link to an anonymous object
                if v.id not in self.remap:
                    raise ValueError(f"link to {v.id:#x}, which is not in the output")
                self.out += struct.pack("<Q", 0xF8000000 | self.remap[v.id])
            elif v.ptype in (1, 2, 5):
                self.out += struct.pack("<Q", v.id)
        elif k == "obj":
            self.obj(v)
        elif k == "struct":
            for n, kk in kind[1]:
                self.value(kk, v[n])
        elif k == "arr":
            self.out += struct.pack("<i", len(v))
            for x in v:
                self.value(kind[1], x)
        elif k == "sarr":
            assert len(v) == kind[1], (kind, len(v))
            for x in v:
                self.value(kind[2], x)
        elif k == "bytes":
            self.out += struct.pack("<i", len(v)) + v
        elif k == "string":
            self.out += struct.pack("<i", len(v)) + v + (b"\x00" if v else b"")
        else:
            raise ValueError(kind)

    def obj(self, o):
        name = NAMES.get(o.hash)
        id_ = 0xF8000000 | self.order[id(o)] if is_anon(o.id) else o.id
        self.out += struct.pack("<QI", id_, o.hash)
        if name in MANAGED:
            self.out += struct.pack("<B", o.managed)
        lay = LAYOUT[self.game][name]
        if list(o.f) != [n for n, _ in lay]:
            raise ValueError(f"{name}: fields {list(o.f)} do not match the {self.game} layout")
        for fname, kind in lay:
            self.value(kind, o.f[fname])


def _walk(o, game, visit):
    visit(o)
    for fname, kind in LAYOUT[game][NAMES[o.hash]]:
        _walk_value(kind, o.f[fname], game, visit)


def _walk_value(kind, v, game, visit):
    if isinstance(kind, str):
        return
    k = kind[0]
    if k in ("ref", "optr") and v.obj is not None:
        _walk(v.obj, game, visit)
    elif k == "obj":
        _walk(v, game, visit)
    elif k == "struct":
        for n, kk in kind[1]:
            _walk_value(kk, v[n], game, visit)
    elif k == "arr":
        for x in v:
            _walk_value(kind[1], x, game, visit)
    elif k == "sarr":
        for x in v:
            _walk_value(kind[2], x, game, visit)


def encode(o, game):
    """Obj tree -> payload bytes under `game`'s layouts. Pass 1 numbers the anonymous objects in
    output order (and maps each original id to its new ordinal), pass 2 writes, remapping links."""
    order, remap = {}, {}

    def visit(x):
        if is_anon(x.id):
            order[id(x)] = len(order)
            if x.id != NEW_ID:
                remap[x.id] = order[id(x)]
    _walk(o, game, visit)
    w = Writer(game, order, remap)
    w.obj(o)
    return bytes(w.out)


# =========================================================================== layouts
# Field names follow ATK's AC schemas (ACOrigins ~ Wildlands, ACOdyssey ~ Breakpoint) where the
# bytes agree with them; short names (x0, b3, ...) are fields whose meaning is not known.

def _both(name, fields, managed=False):
    define("grw", name, fields, managed)
    define("grb", name, fields, managed)


# ---- LODSelector
_both("LODDescriptor", [("Object", ("ref",)), ("SwitchDistance", "f32"), ("TransitionZoneSize", "f32"),
                        ("FadeTimeMultiplier", "f32"), ("x22", "u8"), ("x23", "u8")])
_both("SkeletonLODBakedInfos", [("x0", "u32"), ("x4", "u8"), ("x5", "u8")])
LOD_FLAGS_GRW = ["t0", "t1", "t2", "t3", "t4"]
LOD_FLAGS_GRB = ["b0", "b1", "b2", "b3", "b4", "b5", "b6"]
for _g, _head, _n, _flags in (("grw", [("h13", "u8"), ("h14", "u8"), ("h15", "u32")], 5, LOD_FLAGS_GRW),
                              ("grb", [("h13", "u8"), ("h14", "u8")], 8, LOD_FLAGS_GRB)):
    define(_g, "LODSelector", _head + [("LODDescs", ("sarr", _n, ("obj", "LODDescriptor"))),
                                       ("StreamHandles", ("arr", ("handle",))), ("U32s", ("arr", "u32"))]
           + [(n, "u8") for n in _flags] + [("tf", "f32"),
                                            ("Baked", ("arr", ("obj", "SkeletonLODBakedInfos")))], managed=True)

# ---- GridCellDataBlock (same in both, and as in the AC schema)
_both("GridCellDataBlock", [("Objects", ("arr", ("ref",))), ("NumberOfObjectsToActivate", "u32"),
                            ("OwnerRelatedIndex", "u64")], managed=True)

# ---- Entity
ENT_SCAL_GRW = ([(f"s{i}", "u8") for i in range(21)] + [("Category", "u32"), ("z25", ("raw", 10)),
                ("f35", "f32"), ("u39", "u16"), ("Scale", "f32")])
ENT_SCAL_GRB = ([(f"s{i}", "u8") for i in range(20)] + [("Category", "u32"), ("z24", ("raw", 10)),
                ("f34", "f32"), ("f38", "f32"), ("r42", ("raw", 8)), ("r50", ("raw", 8)),
                ("u58", "u32"), ("Scale", "f32")])
ENT_TAIL = [("BoundingVolume", ("obj", "BoundingVolume")), ("EntityDescriptor", ("obj", "EntityDescriptor")),
            ("DataLayerFilter", ("obj", "DataLayerFilter")), ("ResetData", ("optr",))]
EG_TAIL = [("Entities", ("arr", ("ref",))), ("UIEntitiesDisplayOrder", ("arr", ("handle",))), ("eg4", "u32")]
for _g, _s in (("grw", ENT_SCAL_GRW), ("grb", ENT_SCAL_GRB)):
    _ent = [("Hierarchy", ("optr",)), ("GlobalMatrix", "m44"), ("Components", ("arr", ("optr",)))] + _s + ENT_TAIL
    define(_g, "Entity", _ent, managed=True)
    define(_g, "EntityGroup", _ent + EG_TAIL, managed=True)
_both("BoundingVolume", [("Min", "v3"), ("Max", "v3"), ("Type", "u32")])
_both("EntityDescriptor", [])
_both("DataLayerFilter", [("LayerActions", ("arr", ("obj", "DataLayerAction")))])
_both("DataLayerAction", [("Layer", ("handle",)), ("Action", "u32")])
_both("GameStateData", [("PropertyCount", "u32"), ("DescBuffer", ("bytes",)), ("DataBuffer", ("bytes",))])

# ---- components: managed byte, then Active, OptimizedForHardwareInstancing, ComponentLOD
COMPONENT = [("Active", "u8"), ("OptimizedForHardwareInstancing", "u8"), ("ComponentLOD", "u8")]
_both("Visual", COMPONENT + [("Object", ("ref",)), ("InstanceData", ("optr",)),
                             ("VisualTail", ("raw", 15)), ("BVScale", "v4")], managed=True)
for _g, _n in (("grw", 5), ("grb", 8)):
    define(_g, "LODSelectorInstance", [("LODSelector", ("optr",)), ("LODInstanceData", ("sarr", _n, ("optr",)))])
    define(_g, "MeshInstanceData", [("Mesh", ("handle",)), ("m7", ("raw", 7)), ("CompiledMeshInstance", ("optr",)),
                                    ("MaterialInfos", ("arr", ("optr",))), ("InstanceMatrices", ("arr", "m44"))]
           + ([("InstanceVec4s", ("arr", "v4"))] if _g == "grb" else [])
           + [("InstanceBVs", ("arr", ("obj", "BoundingVolume")))])
define("grw", "CompiledMeshInstance", [("VertexFormat", "u8"), ("Streams", ("arr", ("obj", None))),
                                       ("PlatformVersion", "u32"), ("SDKVersion", "u32"), ("MeshHash", "u64")])
define("grb", "CompiledMeshInstance", [("VertexFormat", "u8")])
_both("MeshInstanceMaterialInfo", [("GraphicObjectInstance", ("optr",)), ("MeshMaterial", ("handle",)),
                                   ("InstanceMaterial", ("ref",))])
_both("SplashFXInstanceData", [("ParentSplashFX", ("optr",))])
define("grw", "LightFlare", [("Enabled", "u8"), ("FlareTexture", ("ref",)), ("FlareWidth", "f32"),
                             ("FlareHeight", "f32"), ("OcclusionWidth", "f32"), ("OcclusionHeight", "f32"),
                             ("FlareIntensity", "f32"), ("Scale", "u8"), ("Fade", "u8"), ("FlareOffset", "f32"),
                             ("BlendMode", "u32"), ("lf0", "f32"), ("lf1", "f32"), ("lf2", "u32")])
define("grw", "LightInstance", [("Light", ("optr",)), ("li0", "u8"), ("Flare", ("ref",)),
                                ("Flare2", ("obj", "LightFlare"))])
define("grb", "LightInstance", [("Light", ("optr",))] + [(f"g{i}", "u8") for i in range(6)]
       + [("ClipPlanes", ("arr", ("optr",))), ("Flare", ("ref",))])
define("grb", "LightClippingPlane", [("c0", "u8"), ("Plane", "v4"), ("c1", "f32")])
_both("MaterialOverrider", COMPONENT + [("MaterialOverrides", ("arr", ("obj", "OverrideDefinition"))),
                                       ("mo", ("raw", 10))], managed=True)
define("grb", "MaterialOverrider", COMPONENT + [("MaterialOverrides", ("arr", ("obj", "OverrideDefinition"))),
                                               ("mo", ("raw", 11))], managed=True)
_both("OverrideDefinition", [("MaterialToReplace", ("handle",)), ("NewMaterial", ("ref",))])
define("grw", "SoundAmbienceStamperComponent", COMPONENT + [("Ambience", ("handle",))], managed=True)
# GRB wraps the Handle in an array of inline objects of an unnamed type: Handle + 16 bytes (a Vec3 offset and 4 more
# bytes, by their values; all zero in 156 of 177). Parses all 172 GRB sample instances (count 1 x167, 2 x2, 3 x3) up to
# the next component header; GRW's 323 are all 25 bytes
define("grb", "SoundAmbienceStamp_fb359006", [("Ambience", ("handle",)), ("st", ("raw", 16))], h=0xfb359006)
define("grb", "SoundAmbienceStamperComponent",
       COMPONENT + [("Stamps", ("arr", ("obj", "SoundAmbienceStamp_fb359006")))], managed=True)
define("grw", "cReactiveResponseComponent", COMPONENT + [("Targets", ("arr", ("handle",))),
                                                          ("Targets2", ("arr", ("handle",))),
                                                          ("Settings", ("arr", ("optr",)))], managed=True)
define("grb", "cReactiveResponseComponent", COMPONENT + [("Targets", ("arr", ("handle",))),
                                                          ("Targets2", ("arr", ("handle",)))], managed=True)
define("grw", "PilotActorComponent", COMPONENT + [(f"p{i}", "u8") for i in range(3)] + [("Actor", ("ref",))],
       managed=True)
define("grb", "PilotActorComponent", COMPONENT + [(f"q{i}", "u8") for i in range(7)] + [("Actor", ("ref",))],
       managed=True)
_both("EventListener", [], managed=True)
_both("EventListenerComponent", COMPONENT + [("Listener", ("obj", "EventListener"))], managed=True)
_both("GR_cSpawnedEntityPhysicActivator_Terrain", COMPONENT + [("sa0", "u32"), ("Spawned", ("handle",))],
      managed=True)
define("grw", "WindForce", [("Active", "u8"), ("TurbulenceFactor", "f32")])
define("grw", "SkeletonComponent", COMPONENT + [("MainSkeleton", ("ref",)), ("AddonSkeletons", ("arr", ("ref",))),
       ("WindForce", ("obj", "WindForce")), ("sk0", "u8"), ("sk1", "u8")], managed=True)
define("grb", "SkeletonComponent", COMPONENT + [("MainSkeleton", ("ref",)), ("AddonSkeletons", ("arr", ("ref",)))],
       managed=True)
_both("cEntityMessengerDispatcherComponent", COMPONENT, managed=True)
_both("cProjectileGeneratorComponent", COMPONENT + [("Projectile", ("handle",))], managed=True)
_both("GR_cVehicleDebrisComponent", COMPONENT + [("d0", "f32")], managed=True)
_both("cSmallLifeTargetComponent", COMPONENT + [("t0", "u32")], managed=True)   # inferred, no twin
_both("PlayerSpawnActivatorComponent", COMPONENT + [("ps", ("raw", 5))], managed=True)  # 0 in all 65 GRW + twin
# ---- PropsPropertiesComponent: no AC schema, no twin. Field boundaries hold in all 309 GRW and 162 GRB instances.
# PropsImposterProperties is a fixed 7,437-byte struct in both games (217 GRW / 69 GRB instances measured to the
# next component). GRW's bytes 512-3072 hold uninitialized memory (shader text, heap values) where GRB bakes atlas
# grids, so the converter drops the imposter (null pointer, flag 0: GRB's own form in 93 of 162 instances).
_both("PropsImposterProperties", [("blob", ("raw", 7437))])
_PP_HEAD = [("p0", "f32"), ("p1", "f32"), ("b0", "u8"), ("b1", "u8"), ("b2", "u8")] + [(f"s{i}", "f32") for i in range(6)]
_PP_TAIL = [("c3", "u8"), ("FarDistance", "f32"), ("HasImposter", "u8"), ("Imposter", ("optr",))]
define("grw", "PropsPropertiesComponent", COMPONENT + _PP_HEAD + [("c0", "u8"), ("c1", "u8"), ("c2", "f32")] + _PP_TAIL,
       managed=True)
define("grb", "PropsPropertiesComponent", COMPONENT + _PP_HEAD + [("g0", "u32"), ("g4", "u8"), ("g5", "u8"), ("g6", "u8"),
       ("g7", "f32"), ("g8", "f32"), ("g9", "f32")] + _PP_TAIL
       + [("pp", "u8"), ("PropsOnProps", ("optr",)), ("Source", ("ref",))], managed=True)

# cInterestAreaComponent (inferred, no twin): 195 GRW and 97 GRB world instances; full decodes past it, no errors
_IA = [("Type", "u32"), ("ia1", "f32"), ("ia2", "u8"), ("H1", ("handle",))]
define("grw", "cInterestAreaComponent", COMPONENT + _IA + [("H2", ("handle",)), ("F1", ("raw", 32)), ("Z1", ("raw", 20)),
       ("ia3", "u32"), ("F2", ("raw", 32)), ("Z2", ("raw", 20))], managed=True)
define("grb", "cInterestAreaComponent", COMPONENT + _IA + [("F1", ("raw", 32)), ("Z1", ("raw", 20)),
       ("ia3", "u32"), ("F2", ("raw", 32)), ("Z2", ("raw", 24))], managed=True)
# GRB keeps its respawn points in Bootstrap's TGT_WorldMap entry, not in cells: 1,593 instances there, all 26 bytes,
# the GRW layout without the trailing u32. GRW: 46 world instances, all 30 bytes
define("grw", "GR_cRespawnPointComponent", COMPONENT + [("Point", ("handle",)), ("rp0", "u8"), ("rp1", "u32")],
       managed=True)
define("grb", "GR_cRespawnPointComponent", COMPONENT + [("Point", ("handle",)), ("rp0", "u8")], managed=True)
define("grb", "cBallisticProjectileComponent", COMPONENT + [("Ballistics", ("ref",))], managed=True)  # GRB-added
# vehicles: GRW keeps the nav whiskers in their own component (type 0x31cd6959, name unknown, its id one below
# the PilotMovingNavMeshComponent's); GRB moved the links into PilotMovingNavMeshComponent itself
_both("NavMeshWhiskerSpot", [("LocalPosition", "v4")])
_both("NavMeshWhiskerLink", [("w0", "u32"), ("Spot0", ("obj", "NavMeshWhiskerSpot")),
                             ("Spot1", ("obj", "NavMeshWhiskerSpot")), ("LinkType", "u32"), ("Length", "f32")])
define("grw", "NavMeshWhiskers_31cd6959", COMPONENT + [("Links", ("arr", ("obj", "NavMeshWhiskerLink")))],
       managed=True, h=0x31cd6959)
define("grw", "PilotPatchingComponent", COMPONENT + [("pp0", "u8"), ("pp1", "u8"), ("Radius", "f32"),
       ("pp2", "u8"), ("pp3", "u8"), ("pp4", "u8")], managed=True)
define("grb", "PilotPatchingComponent", COMPONENT + [("pp0", "u8"), ("pp1", "u8"), ("pp5", "u32"), ("Radius", "f32"),
       ("pp2", "u8"), ("pp3", "u8"), ("pp4", "u8")], managed=True)
define("grw", "PilotMovingNavMeshComponent", COMPONENT + [("NavMesh", ("ref",))], managed=True)
define("grb", "PilotMovingNavMeshComponent", COMPONENT + [("NavMesh", ("ref",)), ("n0", "u8"), ("n1", "u8"),
       ("n2", "u8"), ("Links", ("arr", ("obj", "NavMeshWhiskerLink")))], managed=True)
_both("SoundPointsPosition", [("v", "u32"), ("pos", "v4"), ("p0", "u8")])
_both("SoundPointsComponent", COMPONENT + [("Points", ("arr", ("obj", "SoundPointsPosition"))),
                                          ("Point", ("obj", "SoundPointsPosition"))], managed=True)

# ---- physics
for _g, _nb in (("grw", 11), ("grb", 12)):
    define(_g, "CollisionFilterInfo", [("Layer", "u32"), ("Part", "u32")] + [(f"cb{i}", "u8") for i in range(_nb)])
_both("GameplaySurfaceNavType", [])
_both("PhysicsActivityZone", [("Zones", ("arr", ("obj", "ActivityZoneDesc")))])
_both("ActivityZoneDesc", [("a0", "u32"), ("a1", "f32"), ("a2", "f32"), ("a3", "u8"), ("a4", "u8"), ("a5", "u8")])
# Shape: the collision shape (ConvexVertices/Box/Capsule/Mesh/ReferenceListShape). All 36 in Cell02757 resolve to
# one: 28 in the cell's DataBlock, 8 to MeshShapes in separate _RT entries of DataPC_GRN_WorldMap.forge
RB_HEAD = [("FilterInfo", ("obj", "CollisionFilterInfo")), ("Shape", ("ref",))]
RB_PHYS = [("Mass", "f32"), ("LinearDamping", "f32"), ("AngularDamping", "f32"), ("GravityFactor", "f32")]
define("grw", "RigidBody", RB_HEAD + RB_PHYS + [("x0", "u8"), ("x1", "u8"), ("x2", "u32"), ("x3", "u8"), ("x4", "u32")])
define("grb", "RigidBody", RB_HEAD + [("Ref2", ("ref",))] + RB_PHYS + [(f"y{i}", "u8") for i in range(7)]
       + [("x2", "u32"), ("x4", "u32")])
RBC_TAIL = [("EntityInitTransform", "m44"), ("MaxLinearVelocity", "f32"), ("MaxAngularVelocity", "f32"),
            ("LinearConstraint", "v4"), ("AngularConstraint", "v4"), ("ActivityZone", ("obj", "PhysicsActivityZone"))]
for _g, _flags in (("grw", ["x5", "x6", "x7", "x8", "x9"]), ("grb", ["z0", "z1", "z2", "z3", "z4"])):
    define(_g, "RigidBodyComponent", COMPONENT + [("rc0", "u32"), ("rc1", "u32"), ("rc2", "u32"),
           ("GPSurfaceNavType", ("obj", "GameplaySurfaceNavType")), ("RigidBody", ("obj", "RigidBody")),
           ("ImpactData", ("ref",))] + [(k, "u8") for k in _flags] + RBC_TAIL, managed=True)
_INERT = {"grw": COMPONENT + [("i0", "u32"), ("i1", "u32"), ("RigidBody", ("obj", "RigidBody")),
                              ("GPSurfaceNavType", ("obj", "GameplaySurfaceNavType")), ("i2", "u8"),
                              ("iref", ("ref",)), ("i3", "u32")],
          "grb": COMPONENT + [("i0", "u32"), ("i1", "u32"), ("RigidBody", ("obj", "RigidBody")),
                              ("GPSurfaceNavType", ("obj", "GameplaySurfaceNavType")), ("i2", "u8"), ("i3", "u32")]}
for _g in ("grw", "grb"):
    define(_g, "InertComponent", _INERT[_g], managed=True)
    define(_g, "MergedCollisionInfo", [("h0", ("handle",)), ("r0", ("ref",)), ("h1", ("handle",)), ("c0", "u32"),
                                       ("Shapes", ("arr", ("handle",))), ("c1", "u32"), ("c2", "u32"),
                                       ("Transforms", ("arr", ("struct", [("Matrix", "m44"), ("Ids", ("arr", "u32"))]
                                                               + ([("tb", "u8")] if _g == "grb" else []))))])
    define(_g, "MergedPhysicsComponent", _INERT[_g] + [("U32s", ("arr", "u32")),
                                                       ("Infos", ("arr", ("obj", "MergedCollisionInfo")))],
           managed=True)

# ---- sound objects (ACO schema names; GRW and GRB agree on these bytes)
_both("SoundID", [("ShortID", "u32")])
_both("SoundEvent", [("ID", ("obj", "SoundID")), ("ExternalSourceID", "u32"), ("MaxSqrDistance", "f32"),
                     ("IsOccludable", "u8")])
# SoundInstance ends with 5 bytes whose layout differs between the games (conv_soundinstance). In GRB each
# container then adds 16 bytes of its own right after the sound (destructible: zeros; sound props: Vec3 + u32;
# electric device: the start of its 71-byte block)
_both("SoundInstance", [(f"si{i}", "u8") for i in range(8)] + [("SoundEvent", ("obj", "SoundEvent")),
                                                               ("j", ("raw", 5))])
# GRB sound-bank lists. 0x6290d74a is named SoundBank in ATK's dictionaries but is not CRC32("SoundBank")
define("grb", "SoundBank", [("ID", ("obj", "SoundID")), ("sb0", "u8"), ("Name", ("string",))], h=0x6290d74a)
define("grb", "SoundBankDependencies", [("SoundBanks", ("arr", ("optr",)))])
# SoundPropsComponent: no AC schema; bracketed on 289 GRW and 216 GRB world instances (all decode)
define("grw", "SoundPropsComponentParams", [("sp0", "u8"), ("Sound", ("obj", "SoundInstance")),
                                            ("Sound2", ("obj", "SoundInstance")), ("Offset", "v3"), ("sp1", "f32")])
define("grb", "SoundPropsComponentParams", [("sp0", "u8"), ("Sound", ("obj", "SoundInstance")), ("Offset", "v3"),
                                            ("sp4", "u32"), ("sp2", ("ref",))])
define("grw", "SoundPropsComponent", COMPONENT + [("Params", ("arr", ("obj", "SoundPropsComponentParams"))),
                                                 ("sp3", "u8")], managed=True)
define("grb", "SoundPropsComponent", COMPONENT + [("Params", ("arr", ("obj", "SoundPropsComponentParams"))),
                                                 ("Deps", ("obj", "SoundBankDependencies"))], managed=True)

# ---- cElectricDeviceComponent: no AC schema. Bracketed on 564 GRW and 1,553 GRB world instances (full decodes
# past it: 30 Entities + 112 EntityGroups GRW, 376 EntityGroups GRB; no error at or after it in either game)
define("grw", "MaterialSetting", [("ms0", "u32"), ("Name", ("string",)), ("ms1", ("raw", 29))])
define("grb", "MaterialSetting", [("Name", ("string",)), ("ms0", "u32"), ("ms1", ("raw", 29))])
_both("cReactionResponseComponent_ReactionMaterialSetting", [("A", ("optr",)), ("B", ("optr",)),
                                                              ("Targets", ("arr", ("handle",)))])
_ED_HEAD = [("e0", "u8"), ("FX", ("arr", ("optr",)))]
_ED_MID = [("e2", "u32"), ("e3", "u32"), ("e4", "u32"), ("Lights", ("arr", ("handle",))), ("e5", ("arr", ("handle",))),
           ("e6", "u8"), ("e7", "u8"), ("Settings", ("arr", ("optr",)))]
_ED_TAIL = [("X1", ("arr", ("handle",))), ("X2", ("arr", ("handle",))), ("t1", "u8")]
define("grw", "cElectricDeviceComponent", COMPONENT + _ED_HEAD + _ED_MID + [("t0", ("arr", ("handle",)))] + _ED_TAIL,
       managed=True)
# cReactionResponseComponent (GRW): cElectricDevice's GRW layout minus its final u8 (cElectricDevice looks like a
# subclass that adds that byte). No instance in GRB's world sample or twins, so it has no GRB layout and its
# conversion raises Unsupported
define("grw", "cReactionResponseComponent", COMPONENT + _ED_HEAD + _ED_MID + [("t0", ("arr", ("handle",)))]
       + _ED_TAIL[:-1], managed=True)
define("grb", "cElectricDeviceComponent", COMPONENT + _ED_HEAD + [("ex", "u8")] + _ED_MID + _ED_TAIL
       + [(f"b{i}", "u8") for i in range(8)] + [("Sound", ("obj", "SoundInstance")), ("blk", ("raw", 71))],
       managed=True)
# GRB's 71-byte block after the sound has no GRW counterpart: u32 flag, RGBA f32 colour, ints (-5, 5), f32s
# 0.75 / 1.25 / 1.0, an id-like tail. 419 variants in 1,553 GRB instances. This is the most common one (67) with
# the flag at +0 cleared and the tail set to ff ff ff ff (none), as in all 5 twin pairs; the other tail values look
# like baked pointers
ED_BLOCK_GRB = bytes.fromhex("000000000000000000000000803f0000803f0000803f0000803f00000000000000000000fbffffff05000000"
                             "00000000000000403f0000a03f0000803f000000000000ffffffff")

# ---- cGameplayDestructibleComponent: no AC schema. Bracketed on 2,383 GRW and 302 GRB world instances
# (every field boundary below holds in all of them) and one twin. t is a run GRB re-laid.
_DESTR_HEAD = COMPONENT + [("gd0", "u32"), ("gd1", "u32"), ("RigidBody", ("obj", "RigidBody")),
                           ("Parts", ("arr", ("ref",))), ("PartMatrices", ("arr", "m44")),
                           ("Parts2", ("arr", ("ref",))), ("gd5", "f32"),
                           ("GPSurfaceNavType", ("obj", "GameplaySurfaceNavType"))] \
    + [(f"e{i}", "u8") for i in range(4)] + [("f0", "f32"), ("f1", "f32"), ("f2", "f32"), ("g", "u32")] \
    + [(f"h{i}", "u8") for i in range(7)]
_DESTR_MID = [("i0", "u8"), ("i1", "u8"), ("r0", ("ref",)), ("Sound", ("obj", "SoundInstance"))]
_DESTR_SND_GRB = [("sd", ("raw", 16))]      # GRB only, 0 in all 302 GRB world instances
_DESTR_TAIL = [("R1", ("ref",)), ("R2", ("ref",)), ("k0", "f32"), ("k1", "u32"), ("k2", "f32"), ("k3", "u32"),
               ("R3", ("ref",)), ("k4", "f32")]
define("grw", "cGameplayDestructibleComponent", _DESTR_HEAD + _DESTR_MID + _DESTR_TAIL
       + [("t", ("raw", 64))], managed=True)
define("grb", "cGameplayDestructibleComponent", _DESTR_HEAD + [("X1", ("ref",)), ("x", "u8"), ("X2", ("ref",))]
       + _DESTR_MID + _DESTR_SND_GRB + _DESTR_TAIL + [("t", ("raw", 64))], managed=True)

# ---- physics shape resources (top-level). ConvexVerticesShape: ATK's GRB reader (AnvilToolkit.FileTypes.AnvilNext.
# Physics.ConvexVerticesShape) and exact decodes of 11 GRW shapes agree. The others: exact decodes of every GRW shape in
# Cell02757 (Box 3, Capsule 2, Mesh 4, ReferenceList 6); MeshShape also on its Ghost Room twin (same layout in GRB).
# The GRB side of Box / Capsule / ReferenceList is not yet checked on GRB samples.
_both("ConvexVerticesShape", [("UserCategory", "u32"), ("Vertices", ("arr", "v3")), ("Indices", ("arr", "u16")),
                              ("Material", ("ref",)), ("ConvexRadius", "f32"), ("ShrinkByRadius", "u8")], managed=True)
_both("BoxShape", [("UserCategory", "u32"), ("HalfExtents", "v4"), ("Matrix", "m44"), ("Material", ("ref",))],
      managed=True)
_both("MeshShapeTriangleMaterialData", [("Material", ("ref",)), ("FilterInfo", ("obj", "CollisionFilterInfo"))])
_both("PhysicsSDKDataPack", [("SerializedRawData", ("bytes",))])      # a Havok tagfile (TAG0 / SDKV / DATA)
_MESHTRIS = [("Vertices", ("arr", "v3")), ("Indices", ("arr", "u16")), ("IndicesMaterialData", ("arr", "u8")),
             ("TriangleMaterialData", ("arr", ("obj", "MeshShapeTriangleMaterialData")))]
_both("CapsuleShape", [("UserCategory", "u32"), ("Bottom", "v4"), ("Top", "v4"), ("Radius", "f32")] + _MESHTRIS
      + [("Material", ("ref",))], managed=True)
_both("MeshShape", [("UserCategory", "u32"), ("Wrapper", ("obj", "PhysicsSDKDataPack")),
                    ("OneCollisionMaterialOnly", "u8"), ("MaterialUniqeIndex", "u8")] + _MESHTRIS
      + [("MinLocalAABBox", "v4"), ("MaxLocalAABBox", "v4")], managed=True)
_both("ReferenceListShape", [("UserCategory", "u32"), ("List", ("arr", ("ref",))), ("LocalMatrices", ("arr", "m44")),
                             ("LocalScales", ("arr", "v4")), ("FilterInfos", ("arr", ("obj", "CollisionFilterInfo"))),
                             ("MinLocalAABBox", "v4"), ("MaxLocalAABBox", "v4")], managed=True)
# CollisionMaterial: GRW 92 B / GRB 97 B on one sample each: GRB's filter info is 1 byte longer (as everywhere) and 4
# bytes follow it before the Color (0 in the one GRB sample; their position is inferred)
define("grw", "CollisionMaterial", [("Physics", ("ref",)), ("cm0", ("ref",)), ("FilterInfo", ("obj", "CollisionFilterInfo")),
                                    ("Color", ("obj", "Color"))], managed=True)
define("grb", "CollisionMaterial", [("Physics", ("ref",)), ("cm0", ("ref",)), ("FilterInfo", ("obj", "CollisionFilterInfo")),
                                    ("cm1", "u32"), ("Color", ("obj", "Color"))], managed=True)

# ---- lights: fixed runs of fields between the inline objects (byte maps in conv_light)
_both("Color", [("RGBA", "v4")])
_both("TimeOscillatorData", [("Type", "u32"), ("Frequency", "f32"), ("Min", "f32"), ("Max", "f32"),
                             ("TimeOffset", "f32"), ("IntensityOffset", "f32")])
_both("LightCommonShadowSettings", [("Quality", "u32"), ("NoiseRadius", "f32"), ("DepthBias", "f32"),
                                    ("DepthBiasSlopeScale", "f32")])
_both("OmniLightShadowSettings", [("FaceMask", "u32"), ("os", "u8")])
for _t, (_ew, _eb) in {"SpotLight": (34, 38), "OmniLight": (131, 135), "AreaLight": (131, 135)}.items():
    _shadow = [] if _t == "SpotLight" else [("ShadowSettings", ("obj", None))]
    if _t == "AreaLight":
        _shadow.append(("f", ("raw", 8)))
    define("grw", _t, [("pre", ("raw", 19)), ("LightColor", ("obj", "Color")), ("a", ("raw", 15)),
                       ("IntensityOscillator", ("obj", "TimeOscillatorData")), ("b", ("raw", 9)),
                       ("Flare1", ("obj", "LightFlare")), ("Flare2", ("obj", "LightFlare")), ("c", ("raw", 41)),
                       ("Color2", ("obj", "Color")), ("d", ("raw", 8)),
                       ("CommonShadowSettings", ("obj", "LightCommonShadowSettings")), ("e", ("raw", _ew))]
           + _shadow, managed=True)
    define("grb", _t, [("pre", ("raw", 20)), ("LightColor", ("obj", "Color")), ("a", ("raw", 50)),
                       ("IntensityOscillator", ("obj", "TimeOscillatorData")), ("b", ("raw", 66)),
                       ("Color2", ("obj", "Color")), ("d", ("raw", 8)),
                       ("CommonShadowSettings", ("obj", "LightCommonShadowSettings")), ("e", ("raw", _eb))]
           + _shadow, managed=True)


# =========================================================================== converters (GRW tree -> GRB tree)

def _new(name, fields):
    return Obj(NEW_ID, crc(name), None, OrderedDict(fields))


def _conv_ptr(p, fn):
    if p.obj is not None:
        p.obj = fn(p.obj)
    return p


# ---- LODSelector
LOD_EXTRA = (640.0, 1280.0, 2560.0)


def conv_lodselector(o):
    """5 -> 8 LOD slots (empty slots at 640/1280/2560); drop the GRW-only u32; external LOD
    references: reference-type 0 -> 1; flags 5 -> 7 (t0, t1, 0, t2, 0, t4, 0)."""
    g = o.f; out = OrderedDict()
    out["h13"] = 0
    out["h14"] = g["h14"]
    descs = []
    for d in g["LODDescs"]:
        ref = d.f["Object"]
        if ref.ptype == 1 and ref.rtype == 0:
            ref.rtype = 1
        descs.append(d)
    for dist in LOD_EXTRA:
        descs.append(_new("LODDescriptor", [("Object", Ptr(3, 0, 0)), ("SwitchDistance", dist),
                                            ("TransitionZoneSize", 0.0), ("FadeTimeMultiplier", 0.0),
                                            ("x22", 0), ("x23", 1)]))
    out["LODDescs"] = descs
    out["StreamHandles"] = g["StreamHandles"]; out["U32s"] = g["U32s"]
    t = [g[k] for k in LOD_FLAGS_GRW]
    for k, v in zip(LOD_FLAGS_GRB, (t[0], t[1], 0, t[2], 0, t[4], 0)):
        out[k] = v
    out["tf"] = g["tf"]; out["Baked"] = g["Baked"]
    return Obj(o.id, o.hash, o.managed, out)


# ---- Entity
CATEGORY = {0: 0, 9: 4, 29: 20}       # u32 at scalar offset 21 (twins: 16x 29->20, 1x 9->4)
FORMAT_MAP = {0: 0, 1: 2, 2: 4, 6: 10, 8: 12, 9: 13}   # vertex formats, as grw2grb.py's meshes
INSTANCE_FORMAT_MAP = {**FORMAT_MAP, 7: 10}          # grw2grb ports format-7 meshes with drop_uv1: 7 -> 6 -> 10


def conv_cmi(o):
    vf = o.f["VertexFormat"]
    if vf not in INSTANCE_FORMAT_MAP:
        raise Unsupported(f"CompiledMeshInstance vertex format {vf}")
    if o.f["Streams"]:
        raise Unsupported("CompiledMeshInstance with streams")
    return Obj(o.id, o.hash, o.managed, OrderedDict([("VertexFormat", INSTANCE_FORMAT_MAP[vf])]))


def conv_instance(o):
    n = o.name
    if n == "LODSelectorInstance":
        o.f["LODInstanceData"] = [_conv_ptr(p, conv_instance) for p in o.f["LODInstanceData"]] + [Ptr(3)] * 3
        return o
    if n == "MeshInstanceData":
        _conv_ptr(o.f["CompiledMeshInstance"], conv_cmi)
        f = o.f                         # GRB: one vec4 per instance matrix, before the instance BVs
        o.f = OrderedDict([(k, f[k]) for k in ("Mesh", "m7", "CompiledMeshInstance", "MaterialInfos",
                                               "InstanceMatrices")]
                          + [("InstanceVec4s", [bytes(16)] * len(f["InstanceMatrices"])),
                             ("InstanceBVs", f["InstanceBVs"])])
        return o
    if n == "SplashFXInstanceData":
        return o
    if n == "LightInstance":            # GRB: no flares (null Flare in all twins), 5 new flags, clip planes
        f = o.f
        out = OrderedDict([("Light", f["Light"]), ("g0", f["li0"])] + [(f"g{i}", 0) for i in range(1, 6)]
                          + [("ClipPlanes", []), ("Flare", Ptr(3, 0, 0))])
        return Obj(o.id, o.hash, o.managed, out)
    raise Unsupported(f"instance data {n}")


def conv_visual(o):
    _conv_ptr(o.f["InstanceData"], conv_instance)
    o.f["VisualTail"] = bytes(15)       # GRW: an f32 at +7 in ~2% of world Visuals; GRB: 0 in all
    return o


def conv_rigidbody(o):
    """Collision layer 12 (vehicles): GRB clears filter bytes cb2 and cb3 (24 of 24 twin pairs; meaning unknown)."""
    g = o.f
    fi = g["FilterInfo"]; fi.f["cb11"] = 0
    if fi.f["Layer"] == 12:
        fi.f["cb2"] = fi.f["cb3"] = 0
    out = OrderedDict([("FilterInfo", fi), ("Shape", g["Shape"]), ("Ref2", Ptr(3, 0, 0))])
    for k in ("Mass", "LinearDamping", "AngularDamping", "GravityFactor"):
        out[k] = g[k]
    for k, v in zip(("y0", "y1", "y2", "y3", "y4", "y5", "y6"), (g["x0"], g["x1"], 0, 0, 0, g["x3"], 1)):
        out[k] = v
    out["x2"] = g["x2"]; out["x4"] = g["x4"]
    return Obj(o.id, o.hash, o.managed, out)


def conv_rbc(o):
    """A vehicle's main body (collision layer 12, RigidBody x1 = 1) goes rc0 1 -> 2 (14 of 15 twin pairs;
    the UAV drone is the exception, retuned throughout). Turrets and other layer-12 bodies keep rc0."""
    g = o.f; out = OrderedDict()
    for k in ("Active", "OptimizedForHardwareInstancing", "ComponentLOD", "rc0", "rc1", "rc2", "GPSurfaceNavType"):
        out[k] = g[k]
    if g["RigidBody"].f["FilterInfo"].f["Layer"] == 12 and g["RigidBody"].f["x1"] == 1 and g["rc0"] == 1:
        out["rc0"] = 2
    out["RigidBody"] = conv_rigidbody(g["RigidBody"])
    out["ImpactData"] = g["ImpactData"]
    for k, v in zip(("z0", "z1", "z2", "z3", "z4"), (g["x5"], g["x6"], g["x8"], g["x9"], 0)):
        out[k] = v
    for k, _ in RBC_TAIL:
        out[k] = g[k]
    return Obj(o.id, o.hash, o.managed, out)


def conv_inert(o):
    """Inferred (no comparable twin): same RigidBody rules; GRB drops the reference before i3."""
    o.f["RigidBody"] = conv_rigidbody(o.f["RigidBody"])
    del o.f["iref"]
    return o


def conv_mergedphysics(o):
    """Inferred: InertComponent rules, plus a new GRB byte per collision transform (written 0)."""
    o = conv_inert(o)
    for mci in o.f["Infos"]:
        for t in mci.f["Transforms"]:
            t["tb"] = 0
    return o


def conv_matoverrider(o):
    """mo = u8 flag + Handle in GRW; GRB inserts a byte after the flag, 1 in all 428 GRB world instances and
    in both twin pairs (which come out byte-identical)."""
    m = o.f["mo"]
    o.f["mo"] = m[:1] + b"\x01" + m[1:]
    return o


def conv_reactive(o):
    """Two handle arrays in both games. GRW then has a SmallArray<ObjectPtr<MaterialSetting>>, usually empty (one
    on_off setting on some destructible lamps); GRB has no such array, so it is dropped."""
    del o.f["Settings"]
    return o


def conv_pilotactor(o):
    """3 -> 7 flags: (p0, p1, 1, 1, 1, 1, p2). The four new flags are 1 in 14 of 15 twins (q5 = 0 once)."""
    g = o.f; out = OrderedDict((k, g[k]) for k, _ in COMPONENT)
    for i, v in enumerate((g["p0"], g["p1"], 1, 1, 1, 1, g["p2"])):
        out[f"q{i}"] = v
    out["Actor"] = g["Actor"]
    return Obj(o.id, o.hash, o.managed, out)


def conv_skeleton(o):
    """GRB drops the inline WindForce and the two bytes after it (WindForce {1, 1.0}, bytes 0, 0 in all
    36 GRW twins)."""
    for k in ("WindForce", "sk0", "sk1"):
        del o.f[k]
    return o


def conv_soundinstance(o):
    """The 5 bytes after SoundEvent: the has-sound flag moves from GRW j[2] to GRB j[1]. Each equals si5 (the
    instance has a sound) in every decoded SoundInstance of its own game (1,283 GRW, 234 GRB). GRB j[0] is 0
    except 3 times (6, with IsOccludable 2); GRW's j[0] (0/3/4) and j[1] have no GRB counterpart."""
    o.f["j"] = bytes([0, o.f["j"][2], 0, 0, 0])
    return o


def conv_materialsetting(o):
    """Same fields in both games; GRB writes the name first. Names are copied (GRW's on_off / 3: Emissive Color
    against GRB's Switch / ColorTemp: they name the material's own parameters, which a port brings along)."""
    return Obj(o.id, o.hash, o.managed, OrderedDict([("Name", o.f["Name"]), ("ms0", o.f["ms0"]), ("ms1", o.f["ms1"])]))


def conv_electricdevice(o):
    """GRB inserts a byte after the FX array (0 in all 1,553 GRB instances; position inside the zero run
    inferred) and has two handle arrays at the end where GRW has three: GRB X1 = GRW t0 + X1 (inferred from the one
    twin; t0 is empty in all 546 decoded GRW world instances); GRB's X2 is written empty. GRB then appends 8 flag bytes (written 0, GRB's most
    common), an empty SoundInstance (identical in all 1,553 GRB instances) and the 71-byte block above."""
    g = o.f; out = OrderedDict()
    for k, _ in LAYOUT["grb"]["cElectricDeviceComponent"]:
        if k == "ex" or k.startswith("b") and k[1:].isdigit():
            out[k] = 0
        elif k == "Settings":
            out[k] = [_conv_ptr(p, lambda r: Obj(r.id, r.hash, r.managed, OrderedDict([
                ("A", _conv_ptr(r.f["A"], conv_materialsetting)), ("B", _conv_ptr(r.f["B"], conv_materialsetting)),
                ("Targets", r.f["Targets"])]))) for p in g[k]]
        elif k == "X1":
            out[k] = g["t0"] + g["X1"]
        elif k == "X2":
            out[k] = []          # empty in all 1,553 GRB world instances and 4 of 5 twins
        elif k == "Sound":
            out[k] = _new("SoundInstance", [("si0", 7), ("si1", 1)] + [(f"si{i}", 0) for i in range(2, 8)]
                          + [("SoundEvent", _new("SoundEvent", [("ID", _new("SoundID", [("ShortID", 0)])),
                                                               ("ExternalSourceID", 0), ("MaxSqrDistance", 0.0),
                                                               ("IsOccludable", 0)])),
                             ("j", bytes(5))])
        elif k == "blk":
            out[k] = ED_BLOCK_GRB
        else:
            out[k] = g[k]
    return Obj(o.id, o.hash, o.managed, out)


def conv_propsproperties(o):
    """Head (two f32, three flags, six f32) and tail (u8, FarDistance, imposter flag + pointer) keep their places.
    GRW's middle run (u8, u8, f32: 0/50/75/100) has no known GRB counterpart; GRB's (u32 0, 3 u8, 3 f32 ending in
    0.25) is written with GRB's most common values. The imposter is dropped (see the layout comment). GRB then has
    a u8 + ObjectPtr<PropsOnPropsProperties> (0 / null in 92 of 93 GRB instances without imposter) and a Reference
    in the form (ClassID << 20) | 1 << 63, pointing at the component itself (20), its Entity (29) or a shared
    template (43); the converter points it at the component itself."""
    g = o.f; out = OrderedDict((k, g[k]) for k, _ in COMPONENT)
    for k, _ in _PP_HEAD:
        out[k] = g[k]
    out.update(g0=0, g4=0, g5=0, g6=0, g7=0.0, g8=0.0, g9=0.25)
    out.update(c3=g["c3"], FarDistance=g["FarDistance"], HasImposter=0, Imposter=Ptr(3))
    # ClassIDs with bit 63 set are already in that form (generated sub-objects: owner << 20 | index); point those at
    # the owner (index cleared), the way GRB points some components at their Entity
    if o.id >> 63:
        src = Ptr(1, 0, o.id & ~0xFFFFF)
    elif o.id < 1 << 43:
        src = Ptr(1, 0, (o.id << 20) | (1 << 63))
    else:
        raise Unsupported(f"PropsPropertiesComponent ClassID {o.id:#x} does not fit the Source reference form")
    out.update(pp=0, PropsOnProps=Ptr(3), Source=src)
    return Obj(o.id, o.hash, o.managed, out)


def conv_interestarea(o):
    """GRB drops the second Handle and ends 4 bytes later (0 in all 97 GRB instances). The two 8-float runs and
    the words between them keep their places; values copied (inferred, no twin)."""
    del o.f["H2"]
    o.f["Z2"] = o.f["Z2"] + bytes(4)
    return o


def conv_soundprops(o):
    """GRB keeps the first SoundInstance and the Vec3 offset of each params entry, then a u32 (0 in all 216 GRB
    instances) and a null reference; GRW's second SoundInstance, its f32 and the trailing u8 are dropped. GRB lists
    the sound banks to load in a SoundBankDependencies after the array; the converter writes it empty (GRB's bank
    names can't be derived)."""
    params = []
    for e in o.f["Params"]:
        params.append(Obj(e.id, e.hash, e.managed, OrderedDict([("sp0", e.f["sp0"]),
                          ("Sound", conv_soundinstance(e.f["Sound"])), ("Offset", e.f["Offset"]),
                          ("sp4", 0), ("sp2", Ptr(3, 0, 0))])))
    out = OrderedDict((k, o.f[k]) for k, _ in COMPONENT)
    out["Params"] = params
    out["Deps"] = _new("SoundBankDependencies", [("SoundBanks", [])])
    return Obj(o.id, o.hash, o.managed, out)


def conv_destructible(o):
    """Head, arrays, flags, sound and the three references after it: same bytes in both games (RigidBody and
    SoundInstance rules apply). GRB adds two null references and a 0 byte after h6 (null/0 in all 302 GRB world
    instances). Re-laid run, inferred:
      t (64 bytes in both): GRB f32 1.0 at +16 and +46 (GRW's f32 at +38 is 1.0 in every instance),
        GRB +21 = GRW +44 and GRB +51 = GRW +16 (the twin pairs 2 <-> 2 and 1 <-> 1), a null reference at +52."""
    g = o.f; out = OrderedDict()
    for k, _ in LAYOUT["grb"]["cGameplayDestructibleComponent"]:
        if k == "RigidBody":
            out[k] = conv_rigidbody(g[k])
        elif k in ("X1", "X2"):
            out[k] = Ptr(3, 0, 0)
        elif k == "x":
            out[k] = 0
        elif k == "Sound":
            out[k] = conv_soundinstance(g[k])
        elif k == "sd":
            out[k] = bytes(16)
        elif k == "t":
            t = bytearray(64); w = g["t"]
            t[16:20] = t[46:50] = struct.pack("<f", 1.0)
            t[21] = w[44]; t[51] = w[16]; t[52] = 3
            out[k] = bytes(t)
        else:
            out[k] = g[k]
    return Obj(o.id, o.hash, o.managed, out)


def conv_pilotpatching(o):
    """GRB inserts a u32 after the two leading flags (0 in all 16 twins)."""
    g = o.f; out = OrderedDict((k, g[k]) for k, _ in COMPONENT)
    out["pp0"] = g["pp0"]; out["pp1"] = g["pp1"]; out["pp5"] = 0
    for k in ("Radius", "pp2", "pp3", "pp4"):
        out[k] = g[k]
    return Obj(o.id, o.hash, o.managed, out)


def conv_movingnavmesh(o):
    """GRB adds three flags (1, 1, 1 in all 10 twins) and takes the whisker links GRW keeps in a separate
    component; conv_entity moves them in (merge_whiskers)."""
    o.f.update(n0=1, n1=1, n2=1, Links=[])
    return o


def conv_respawnpoint(o):
    """GRB drops the trailing u32 (4-12 in GRW). Point (a Handle a few IDs below the component's own, -2 in most of
    both games) and the u8 (0 in all of both) are copied. Inferred: no twin. GRB places respawn points in Bootstrap's
    TGT_WorldMap entry, so whether GRB registers one inside a transplanted cell is untested."""
    del o.f["rp1"]
    return o


def conv_ambiencestamper(o):
    """GRW's one Ambience Handle -> GRB's array of one stamp object, with the 16 trailing bytes zero (GRB's most
    common value). Inferred: no twin; the GRB layout is from GRB world samples only."""
    stamp = Obj(0xF8000000, 0xfb359006, None, OrderedDict([("Ambience", o.f["Ambience"]), ("st", bytes(16))]))
    out = OrderedDict((k, o.f[k]) for k, _ in COMPONENT)
    out["Stamps"] = [stamp]
    return Obj(o.id, o.hash, o.managed, out)


def merge_whiskers(comps_grw, comps_grb):
    """GRW's NavMeshWhiskers_31cd6959 component -> the Links of GRB's PilotMovingNavMeshComponent."""
    whisk = [p for p in comps_grw if p.obj is not None and p.obj.name == "NavMeshWhiskers_31cd6959"]
    if not whisk:
        return comps_grb
    nav = [p for p in comps_grb if p.obj is not None and p.obj.name == "PilotMovingNavMeshComponent"]
    if len(whisk) != 1 or len(nav) != 1:
        raise Unsupported(f"{len(whisk)} whisker components, {len(nav)} PilotMovingNavMeshComponent")
    nav[0].obj.f["Links"] = whisk[0].obj.f["Links"]
    return [p for p in comps_grb if p.obj is None or p.obj.name != "NavMeshWhiskers_31cd6959"]


COMPONENTS = {"PilotPatchingComponent": conv_pilotpatching, "PilotMovingNavMeshComponent": conv_movingnavmesh,
              "NavMeshWhiskers_31cd6959": lambda o: o, "cEntityMessengerDispatcherComponent": lambda o: o,
              "cProjectileGeneratorComponent": lambda o: o,
              "GR_cVehicleDebrisComponent": lambda o: o, "cGameplayDestructibleComponent": conv_destructible,
              "cSmallLifeTargetComponent": lambda o: o,
              "PlayerSpawnActivatorComponent": lambda o: o,
              "cInterestAreaComponent": conv_interestarea,
              "PropsPropertiesComponent": conv_propsproperties,
              "SoundPropsComponent": conv_soundprops,
              "cElectricDeviceComponent": conv_electricdevice,
              "SkeletonComponent": conv_skeleton, "PilotActorComponent": conv_pilotactor,
              "cReactiveResponseComponent": conv_reactive,
              "EventListenerComponent": lambda o: o,
              "GR_cSpawnedEntityPhysicActivator_Terrain": lambda o: o, "Visual": conv_visual, "RigidBodyComponent": conv_rbc, "InertComponent": conv_inert,
              "MergedPhysicsComponent": conv_mergedphysics, "MaterialOverrider": conv_matoverrider,
              "SoundAmbienceStamperComponent": conv_ambiencestamper, "SoundPointsComponent": lambda o: o,
              "GR_cRespawnPointComponent": conv_respawnpoint}
# twin-validated; the others in COMPONENTS were inferred from world samples of both games
VALIDATED = {"Visual", "RigidBodyComponent", "cReactiveResponseComponent", "PilotActorComponent",
             "SkeletonComponent", "EventListenerComponent", "GR_cSpawnedEntityPhysicActivator_Terrain",
             "cEntityMessengerDispatcherComponent", "cProjectileGeneratorComponent", "GR_cVehicleDebrisComponent",
             "PilotPatchingComponent", "PilotMovingNavMeshComponent", "NavMeshWhiskers_31cd6959",
             "MaterialOverrider", "OverrideDefinition", "cElectricDeviceComponent", "MaterialSetting",
             "cReactionResponseComponent_ReactionMaterialSetting"}


def conv_component(o):
    fn = COMPONENTS.get(o.name)
    if fn is None:
        raise Unsupported(f"component {o.name}")
    return fn(o)


# GRW gameplay components with no GRB counterpart (none in GRB's world sample or twins). convert() refuses an
# Entity holding one unless drop_grw_only=True; then they are left out and listed in the manifest, so the port can
# re-add GRB-native equivalents. Only types with a GRW layout can be skipped (rally points have none yet).
# cReactionResponseComponent: 0 hits in a 1-in-5 entry sample of every GRB world forge. Rally points exist in GRB
# (Bootstrap) but have no layout in either game yet.
GRW_ONLY = {"GR_cRallyPointComponent", "cReactionResponseComponent"}
# strip_physics=True leaves these out (collision then needs GRB-native shapes, or none)
PHYSICS = {"RigidBodyComponent", "cGameplayDestructibleComponent", "InertComponent", "MergedPhysicsComponent"}
_dropped = None          # a list while convert() drops components
_drop_types = {}         # component type -> reason, for the running convert()
_strip_at = None         # (shape types, shape_of) for strip_physics_at, for the running convert()


def _ptr_ids(v, out):
    """Append every ID that a pointer or handle in v refers to (inline objects are walked, not counted)."""
    if isinstance(v, Obj):
        for x in v.f.values():
            _ptr_ids(x, out)
    elif isinstance(v, Ptr):
        if v.obj is not None:
            _ptr_ids(v.obj, out)
        elif v.id:
            out.append(v.id)
    elif isinstance(v, (list, tuple)):
        for x in v:
            _ptr_ids(x, out)
    elif isinstance(v, dict):
        for x in v.values():
            _ptr_ids(x, out)
    return out


def _body_shape_ids(v, out):
    """IDs a physics component must find to be complete: each RigidBody's Shape and MergedCollisionInfo's Shapes."""
    if isinstance(v, Obj):
        if v.name == "RigidBody" and isinstance(v.f.get("Shape"), Ptr) and v.f["Shape"].id:
            out.append(v.f["Shape"].id)
        if v.name == "MergedCollisionInfo":
            out.extend(p.id for p in v.f["Shapes"] if p.id)
        for x in v.f.values():
            _body_shape_ids(x, out)
    elif isinstance(v, Ptr) and v.obj is not None:
        _body_shape_ids(v.obj, out)
    elif isinstance(v, (list, tuple)):
        for x in v:
            _body_shape_ids(x, out)
    return out


def _physics_hit(c, types, shape_of):
    """Why physics component c reaches one of `types`, or None. shape_of(id) -> (type name, child IDs) or None if
    the ID is not found. ReferenceListShape children are followed; a body Shape that is not found counts as a hit,
    since the converted body would point at nothing."""
    seen, todo = set(), _ptr_ids(c, [])
    while todo:
        i = todo.pop()
        if i in seen:
            continue
        seen.add(i)
        s = shape_of(i)
        if s is None:
            continue
        if s[0] in types:
            return f"reaches {s[0]} {i:#x}"
        todo.extend(s[1])
    for i in _body_shape_ids(c, []):
        if shape_of(i) is None:
            return f"shape {i:#x} not found"
    return None


def conv_entity(o):
    g = o.f; out = OrderedDict()
    out["Hierarchy"] = g["Hierarchy"]; out["GlobalMatrix"] = g["GlobalMatrix"]
    comps = g["Components"]; null_reset = False
    if _dropped is not None:
        # the Entity's ResetData (GameStateData) DescBuffer lists component ClassIDs. When it names a removed
        # component, ResetData is nulled (its DataBuffer is not mapped, so the record can't be cut out)
        rd = g.get("ResetData"); rd = rd.obj if isinstance(rd, Ptr) else rd
        desc = rd.f.get("DescBuffer", b"") if isinstance(rd, Obj) else b""
        why = {}                                         # component ClassID -> reason
        for p in comps:
            if p.obj is not None and p.obj.name in _drop_types:
                why[p.obj.id] = _drop_types[p.obj.name]
        if _strip_at is not None:
            # one physics component reaching a stripped shape type takes all of the Entity's physics with it, so
            # no remaining component points at a removed RigidBody
            hits = [h for p in comps if p.obj is not None and p.obj.name in PHYSICS
                    for h in [_physics_hit(p.obj, *_strip_at)] if h]
            if hits:
                for p in comps:
                    if p.obj is not None and p.obj.name in PHYSICS and p.obj.id not in why:
                        why[p.obj.id] = "physics: " + hits[0]
        keep = []
        for p in comps:
            if p.obj is not None and p.obj.id in why:
                in_reset = struct.pack("<Q", p.obj.id) in desc
                null_reset |= in_reset
                _dropped.append({"entity_class_id": o.id, "component": p.obj.name, "reason": why[p.obj.id],
                                 "component_hash": f"{p.obj.hash:#010x}", "component_class_id": p.obj.id,
                                 "reset_data_nulled": in_reset})
            else:
                keep.append(p)
        comps = keep
    out["Components"] = merge_whiskers(comps, [_conv_ptr(p, conv_component) for p in comps])
    for i in range(20):                                 # GRW s17 (always 1) dropped
        out[f"s{i}"] = g[f"s{i}" if i < 17 else f"s{i + 1}"]
    if g["Category"] not in CATEGORY:
        raise Unsupported(f"Entity category {g['Category']}")
    out["Category"] = CATEGORY[g["Category"]]
    out["z24"] = g["z25"]; out["f34"] = g["f35"]; out["f38"] = 1.0
    out["r42"] = bytes(8); out["r50"] = bytes(8)
    out["u58"] = 0xFFFFFFFF if g["u39"] == 0xFFFF else g["u39"]
    out["Scale"] = g["Scale"]
    for k, _ in ENT_TAIL:
        out[k] = g[k]
    if null_reset:
        out["ResetData"] = Ptr(3)
    return Obj(o.id, o.hash, o.managed, out)


def conv_entitygroup(o):
    tail = {k: o.f[k] for k, _ in EG_TAIL}
    out = conv_entity(o)
    for p in tail["Entities"]:
        if p.obj is None:
            continue
        if p.obj.name == "Entity":
            p.obj = conv_entity(p.obj)
        elif p.obj.name == "EntityGroup":
            p.obj = conv_entitygroup(p.obj)
        else:
            raise Unsupported(f"EntityGroup child {p.obj.name}")
    out.f.update(tail)
    return out


# ---- lights
def _f(x):
    return struct.pack("<f", x)

LIGHT_A_CONST = bytes(16) + _f(-1.0) + _f(0.0) + _f(1.0) + _f(1.0) + b"\x03" + bytes(9)


def conv_light(o):
    """Byte maps per run (29 light twins). Both GRW LightFlares are dropped."""
    g = o.f; out = OrderedDict()
    pw = g["pre"]
    out["pre"] = pw[0:2] + pw[6:11] + bytes(2) + pw[12:17] + bytes(3) + pw[17:19] + b"\x00"
    out["LightColor"] = g["LightColor"]
    out["a"] = g["a"][3:11] + LIGHT_A_CONST
    out["IntensityOscillator"] = g["IntensityOscillator"]
    c = g["c"]
    out["b"] = g["b"] + bytes(8) + c[0:24] + c[0:8] + c[24:41]
    out["Color2"] = g["Color2"]; out["d"] = g["d"]
    out["CommonShadowSettings"] = g["CommonShadowSettings"]
    e = g["e"]
    out["e"] = e + _f(10.0) if o.name == "SpotLight" else e[0:12] + _f(10.0) + e[12:]
    for k in ("ShadowSettings", "f"):
        if k in g:
            out[k] = g[k]
    return Obj(o.id, o.hash, o.managed, out)


def conv_filterinfo(fi):
    """CollisionFilterInfo outside RigidBodies: GRB appends a byte (written 0)."""
    fi.f["cb11"] = 0
    return fi


def conv_shape(o):
    """Shapes keep their layout; inline CollisionFilterInfos (per-triangle materials, per-child filters) get GRB's
    extra byte. MeshShape's Havok tagfile is copied as is: GRW's is SDK 2016.1, GRB's 2018.2 (KNOWN_GAPS)."""
    for e in o.f.get("TriangleMaterialData", []):
        conv_filterinfo(e.f["FilterInfo"])
    for fi in o.f.get("FilterInfos", []):
        conv_filterinfo(fi)
    return o


def conv_collisionmaterial(o):
    g = o.f
    return Obj(o.id, o.hash, o.managed, OrderedDict([("Physics", g["Physics"]), ("cm0", g["cm0"]),
               ("FilterInfo", conv_filterinfo(g["FilterInfo"])), ("cm1", 0), ("Color", g["Color"])]))


CONVERTERS = {"ConvexVerticesShape": lambda o: o, "BoxShape": lambda o: o, "CapsuleShape": conv_shape,
              "MeshShape": conv_shape, "ReferenceListShape": conv_shape, "CollisionMaterial": conv_collisionmaterial,
              "LODSelector": conv_lodselector, "GridCellDataBlock": lambda o: o, "Entity": conv_entity,
              "EntityGroup": conv_entitygroup, "SpotLight": conv_light, "OmniLight": conv_light,
              "AreaLight": conv_light}


def _remap_refs(v, remap, hits):
    """Point every by-ID pointer whose target is a key of `remap` at remap[target] instead; count each in `hits`.
    Pointer and reference-type bytes are kept, and so are links to anonymous objects."""
    if isinstance(v, Obj):
        for x in v.f.values():
            _remap_refs(x, remap, hits)
    elif isinstance(v, Ptr):
        if v.obj is not None:
            _remap_refs(v.obj, remap, hits)
        elif v.id in remap and not is_anon(v.id):
            hits[v.id] = hits.get(v.id, 0) + 1
            v.id = remap[v.id]
    elif isinstance(v, (list, tuple)):
        for x in v:
            _remap_refs(x, remap, hits)
    elif isinstance(v, dict):
        for x in v.values():
            _remap_refs(x, remap, hits)


def convert(payload_grw, drop_grw_only=False, strip_physics=False, manifest=None, strip_physics_at=None,
            shape_of=None, remap=None, remapped=None):
    """Wildlands payload of a supported type -> Breakpoint payload. drop_grw_only: leave out GRW_ONLY components
    instead of refusing the Entity. strip_physics: leave out PHYSICS components. strip_physics_at (a set of shape
    type names, e.g. {"MeshShape"}) with shape_of(id) -> (type, child IDs) | None: leave out an Entity's PHYSICS
    components only when one of them reaches such a shape (or a body shape is not found). Each dropped component is
    appended to `manifest` (a list) if given; an Entity whose ResetData names one gets a null ResetData.
    remap ({old ID: new ID}): re-point references, e.g. a shape's Material at a GRB-native CollisionMaterial; the
    count per old ID is added to `remapped` (a dict) if given. A resource whose own ClassID is an old ID is still
    converted as is."""
    global _dropped, _drop_types, _strip_at
    o = decode(payload_grw, "grw")
    fn = CONVERTERS.get(o.name)
    if fn is None:
        raise Unsupported(f"type {o.name}")
    _drop_types = {**({t: "grw-only" for t in GRW_ONLY} if drop_grw_only else {}),
                   **({t: "physics" for t in PHYSICS} if strip_physics else {})}
    _strip_at = (set(strip_physics_at), shape_of) if strip_physics_at and not strip_physics else None
    _dropped = [] if _drop_types or _strip_at else None
    try:
        tree = fn(o)
        if remap:
            hits = {}
            _remap_refs(tree, remap, hits)
            if remapped is not None:
                for k, n in hits.items():
                    remapped[k] = remapped.get(k, 0) + n
        out = encode(tree, "grb")
        dropped = _dropped or []
    finally:
        _dropped = None; _drop_types = {}; _strip_at = None
    if manifest is not None:
        manifest.extend(dropped)
    return out


# =========================================================================== validation

# Fields GRB re-baked per asset, by generalized path (see flatten): a twin whose differences all
# fall under these is "content-only".
_ENT_CONTENT = ({".BoundingVolume", ".GlobalMatrix", ".Category", ".Scale", ".f34", ".r42", ".r50"}
                | {f".s{i}" for i in range(20)}
                | {".Components[*]@.Active", ".Components[*]@.RigidBody.y2", ".Components[*]@.RigidBody.y3",
                   ".Components[*]@.RigidBody.y4", ".Components[*]@.RigidBody.Ref2",
                   ".Components[*]@.Object@rtype", ".Components[*]@.q2", ".Components[*]@.q3",
                   # GRB flips some components between inline (ptype 0, managed 1) and inline-managed
                   # (ptype 4, managed 0), in both directions; and fills or empties single LOD slots
                   ".Components[*]@ptype", ".Components[*]@#managed",
                   ".Components[*]@.InstanceData@.LODInstanceData",
                   ".Components[*]@.q4", ".Components[*]@.q5",
                   ".Components[*]@.InstanceData@.LODInstanceData[*]@.CompiledMeshInstance@.VertexFormat"})
_LIGHT_CONTENT = {".a", ".e", ".LightColor", ".IntensityOscillator", ".CommonShadowSettings"}
CONTENT = {
    "Entity": _ENT_CONTENT,
    "EntityGroup": _ENT_CONTENT | {".Entities[*]@" + c[1:] for c in _ENT_CONTENT},
    "LODSelector": {".LODDescs[*].Object@id", ".LODDescs[*].Object@ptype", ".LODDescs[*].Object@rtype",
                    ".LODDescs[*].SwitchDistance", ".LODDescs[*].TransitionZoneSize",
                    ".LODDescs[*].FadeTimeMultiplier", ".LODDescs[*].x22", ".LODDescs[*].x23",
                    ".StreamHandles", ".U32s", ".Baked", ".b0", ".b1", ".b3", ".b4", ".b5", ".tf"},
    "GridCellDataBlock": {".Objects", ".NumberOfObjectsToActivate", ".OwnerRelatedIndex"},
    "SpotLight": _LIGHT_CONTENT, "OmniLight": _LIGHT_CONTENT, "AreaLight": _LIGHT_CONTENT,
}


def flatten(v, path="", out=None):
    """Tree -> {path: leaf}. Anonymous ids are left out (ordinals are layout, not content)."""
    if out is None:
        out = {}
    if isinstance(v, Obj):
        out[path + "#type"] = v.name
        if not is_anon(v.id):
            out[path + "#id"] = v.id
        if v.managed is not None:
            out[path + "#managed"] = v.managed
        for k, x in v.f.items():
            flatten(x, f"{path}.{k}", out)
    elif isinstance(v, Ptr):
        out[path + "@ptype"] = v.ptype
        if v.rtype is not None:
            out[path + "@rtype"] = v.rtype
        if v.id is not None:
            out[path + "@id"] = v.id
        if v.obj is not None:
            flatten(v.obj, path + "@", out)
    elif isinstance(v, dict):
        for k, x in v.items():
            flatten(x, f"{path}.{k}", out)
    elif isinstance(v, list):
        out[path + "#len"] = len(v)
        for i, x in enumerate(v):
            flatten(x, f"{path}[{i}]", out)
    else:
        out[path] = v
    return out


def _under(p, prefixes):
    return any(p == c or p.startswith(c + "[") or p.startswith(c + ".") or p.startswith(c + "@")
               or p.startswith(c + "#") for c in prefixes)


def classify(pw, pb):
    """Compare convert(GRW twin) with the GRB twin -> (verdict, unexplained paths)."""
    out = convert(pw)
    if out == pb:
        return "identical", []
    oa, ob = decode(out, "grb"), decode(pb, "grb")
    if "Components" in oa.f:
        ta = [c.obj.name if c.obj else c.ptype for c in oa.f["Components"]]
        tb = [c.obj.name if c.obj else c.ptype for c in ob.f["Components"]]
        if ta != tb:
            return "content-only", []                    # GRB added or removed a component
    a, b = flatten(oa), flatten(ob)
    diffs = sorted({re.sub(r"\[\d+\]", "[*]", p) for p in set(a) | set(b) if a.get(p, "<none>") != b.get(p, "<none>")})
    content = CONTENT.get(oa.name, set())
    # re-pointed references (@id) and re-allocated object ClassIDs (#id) are content
    unexpl = [d for d in diffs if not _under(d, content) and not d.endswith(("@id", "#id"))]
    gaps = [d for d in unexpl if _under(d, KNOWN_GAPS.get(oa.name, set()))]
    if unexpl and len(gaps) == len(unexpl):
        return "known gap", gaps
    return ("content-only" if not unexpl else "unexplained"), unexpl


# format differences the converter knows about and does not convert (reported, not counted as unexplained)
KNOWN_GAPS = {"MeshShape": {".Wrapper"}}     # Havok tagfile: SDK 2016.1 (GRW) vs 2018.2 (GRB), copied as is


TYPES = ["Entity", "LODSelector", "GridCellDataBlock", "SpotLight", "OmniLight", "AreaLight", "EntityGroup",
         "ConvexVerticesShape", "BoxShape", "CapsuleShape", "MeshShape", "ReferenceListShape", "CollisionMaterial"]
_TYPE_IDS = {crc(t): t for t in TYPES}
_TWIN_ENTRIES = {crc(t) for t in ("Entity", "LODSelector", "EntityGroup", "EntityBuilder", "MeshShape")}


def _resources(path, off, ln, oodle):
    with open(path, "rb") as f:
        f.seek(off); b = f.read(ln)
    meta, files = di.read_container_bytes(b, oodle)
    res, _ = di.walk(files)
    return res


def _shape_map(loaded, paths, oodle):
    """shape_of(id) for convert --strip-physics-at: (type name, ReferenceListShape child IDs) for every resource in
    the converted entries, plus each top-level forge entry that their physics components reach (typed from the
    forge index's type hash; out-of-cell ReferenceListShapes are read for their children). None = not found."""
    known, need = {}, set()

    def add(r):
        t = NAMES.get(r.type_id, f"#{r.type_id:08x}"); kids = []
        if t == "ReferenceListShape":
            kids = [p.id for p in decode(r.payload, "grw").f["List"] if p.obj is None and p.id]
            need.update(kids)
        known[di.class_id(r)] = (t, kids)

    def physics(v):
        if isinstance(v, Obj):
            if v.name in PHYSICS:
                need.update(_ptr_ids(v, []))
            for x in v.f.values():
                physics(x)
        elif isinstance(v, Ptr) and v.obj is not None:
            physics(v.obj)
        elif isinstance(v, (list, tuple)):
            for x in v:
                physics(x)

    for _, rs in loaded:
        for r in rs:
            add(r)
            if _TYPE_IDS.get(r.type_id) in ("Entity", "EntityGroup"):
                try:
                    physics(decode(r.payload, "grw"))
                except (NeedLayout, Unsupported, ValueError, struct.error):
                    pass                                   # convert() reports these
    for _ in range(4):                                     # RefList children can lead to more entries
        todo = need - set(known)
        if not todo:
            break
        found = {}
        for p in paths:
            for fid, ext, name, off, ln in fi.forge_entries(p):
                if ext and fid in todo:
                    found[fid] = (p, off, ln, ext)         # later forges (patches) win
        need = set()
        for fid, (p, off, ln, ext) in found.items():
            if NAMES.get(ext) == "ReferenceListShape":
                for r in _resources(p, off, ln, oodle):
                    if di.class_id(r) == fid:
                        add(r)
            else:
                known[fid] = (NAMES.get(ext, f"#{ext:08x}"), [])
    return known.get


def _forge_resources(paths, oodle, types):
    """{ClassID: (type, name, payload)} of the given types over forges (later ones win)."""
    out = {}
    for p in paths:
        for fid, ext, name, off, ln in fi.forge_entries(p):
            if not ext:
                continue
            for r in _resources(p, off, ln, oodle):
                t = _TYPE_IDS.get(r.type_id)
                if t in types:
                    out[di.class_id(r)] = (t, r.name, r.payload)
    return out


def twins(grw_root, grb_root, oodle, grb_ghostroom=None):
    """Yield (type, name, grw payload, grb payload) for target-type resources under one ClassID:
    the Ghost Room forges, plus every entry ID both installs share whose type is a likely holder."""
    def index(root):
        idx = {}
        paths = glob.glob(os.path.join(root, "*.forge")) + glob.glob(os.path.join(root, "dlc_*", "*.forge"))
        for p in sorted(paths, key=lambda q: ("_patch_" in q, q)):
            if "GhostRoom" in os.path.basename(p):
                continue
            for fid, ext, name, off, ln in fi.forge_entries(p):
                if ext in _TWIN_ENTRIES:
                    idx[fid] = (p, off, ln)
                elif fid in idx:
                    del idx[fid]
        return idx
    seen = set()
    gw = _forge_resources([os.path.join(grw_root, "DataPC_GRN_GhostRoom.forge"),
                           os.path.join(grw_root, "DataPC_GRN_GhostRoom_patch_01.forge")], oodle, set(TYPES))
    gb = _forge_resources([grb_ghostroom or os.path.join(grb_root, "DataPC_GRN_GhostRoom.forge")], oodle, set(TYPES))
    for cid in sorted(set(gw) & set(gb)):
        if gw[cid][0] == gb[cid][0]:
            seen.add(cid)
            yield gw[cid][0], gw[cid][1], gw[cid][2], gb[cid][2]
    del gw, gb
    iw, ib = index(grw_root), index(grb_root)
    for fid in sorted(set(iw) & set(ib)):
        a = {di.class_id(r): r for r in _resources(*iw[fid], oodle) if r.type_id in _TYPE_IDS}
        b = {di.class_id(r): r for r in _resources(*ib[fid], oodle) if r.type_id in _TYPE_IDS}
        for cid in sorted(set(a) & set(b)):
            if cid not in seen and a[cid].type_id == b[cid].type_id:
                seen.add(cid)
                yield _TYPE_IDS[a[cid].type_id], a[cid].name, a[cid].payload, b[cid].payload


def scan(forges, oodle, step=60, per_type=4000):
    """Share of target-type resources that convert, over every `step`-th entry of the forges
    (at most `per_type` per type, spread evenly). Returns {type: Counter}, {blocker: n}."""
    seen = collections.Counter(); c = collections.defaultdict(collections.Counter)
    blockers = collections.Counter()
    stride = {"Entity": 5, "LODSelector": 6, "EntityGroup": 2}
    for p in forges:
        for k, (fid, ext, name, off, ln) in enumerate(fi.forge_entries(p)):
            if not ext or k % step:
                continue
            for r in _resources(p, off, ln, oodle):
                t = _TYPE_IDS.get(r.type_id)
                if t is None:
                    continue
                seen[t] += 1
                if (seen[t] - 1) % stride.get(t, 1) or sum(c[t].values()) >= per_type:
                    continue
                try:
                    decode(convert(r.payload), "grb"); c[t]["converts"] += 1
                except NeedLayout as e:
                    c[t]["needs layout"] += 1; blockers[f"{t}: layout {e}"] += 1
                except Unsupported as e:
                    c[t]["unsupported"] += 1; blockers[f"{t}: {e}"] += 1
                except Exception as e:                      # a rule or layout is wrong somewhere
                    c[t]["ERROR"] += 1; blockers[f"{t}: error {str(e)[:60]}"] += 1
    return c, blockers


def selftest(grw_root, grb_root, oodle, world_step=60, grb_ghostroom=None):
    c = collections.defaultdict(collections.Counter); unexpl = collections.Counter()
    for typ, name, pw, pb in twins(grw_root, grb_root, oodle, grb_ghostroom):
        try:
            k, u = classify(pw, pb)
        except NeedLayout:
            k, u = "needs layout", []
        except Unsupported:
            k, u = "unsupported", []
        except Exception as e:
            k, u = "grb-side decode error" if "expected" in str(e) else "error", []
        c[typ][k] += 1
        for x in u:
            unexpl[f"{typ} {x}"] += 1
    forges = sorted(glob.glob(os.path.join(grw_root, "DataPC_GRN_WorldMap*.forge")))
    w, blockers = scan(forges, oodle, world_step) if world_step else ({}, {})
    ok = True
    for t in TYPES:
        n = sum(w.get(t, {}).values()) if w else 0
        conv = w[t]["converts"] if w else 0
        print(f"{t:18s} twins {sum(c[t].values()):4d}: " + ", ".join(f"{k} {v}" for k, v in c[t].most_common())
              + (f"   | world {n}: converts {conv} ({100 * conv / n:.1f}%)" if n else ""))
        ok &= c[t]["unexplained"] == 0 and c[t]["error"] == 0 and (not w or w[t]["ERROR"] == 0)
    for k, v in unexpl.most_common(20):
        print(f"   unexplained {k}: {v}")
    if blockers:
        print("top world blockers:")
        for k, v in collections.Counter(blockers).most_common(12):
            print(f"   {v:5d} {k}")
    print("PASS" if ok else "FAIL", "- no unexplained twin difference and no conversion error")
    return ok


# =========================================================================== CLI

def main(argv):
    def opt(flag, default=None):
        if flag in argv:
            i = argv.index(flag); v = argv[i + 1]; del argv[i:i + 2]; return v
        return default
    memory_cap(int(opt("--max-mb", "1500")))
    grw_root = opt("--grw", os.environ.get("GRW_INSTALL", GRW_DEFAULT))
    grb_root = opt("--grb", os.environ.get("GRB_INSTALL", GRB_DEFAULT))
    out_dir = opt("-o", ".")
    step = int(opt("--step", opt("--world-step", "60")))
    ghost = opt("--grb-ghostroom")
    only_types = set(filter(None, opt("--types", "").split(",")))
    strip_at = set(filter(None, opt("--strip-physics-at", "").split(",")))
    try:
        remap = {int(a, 0): int(b, 0) for a, b in (kv.split("=") for kv in
                                                    filter(None, opt("--material-remap", "").split(",")))}
    except ValueError:
        raise SystemExit("--material-remap takes OLD=NEW[,OLD=NEW...], IDs in hex (0x...) or decimal")
    drop, strip = "--drop-grw-only" in argv, "--strip-physics" in argv
    for f in ("--drop-grw-only", "--strip-physics"):
        if f in argv:
            argv.remove(f)
    manifest = []
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    oodle = di.Oodle(os.path.join(grb_root, "oo2core_7_win64.dll"))
    if not oodle.ok:
        raise SystemExit(f"Oodle DLL not found in {grb_root} (pass --grb <GRB install>)")
    cmd, args = argv[0], argv[1:]
    if cmd == "selftest":
        return 0 if selftest(grw_root, grb_root, oodle, step, ghost) else 1
    if cmd == "scan":
        c, blockers = scan(args, oodle, step)
        for t in TYPES:
            n = sum(c[t].values())
            if n:
                print(f"{t:18s} {n:5d}: " + ", ".join(f"{k} {v} ({100 * v / n:.1f}%)" for k, v in c[t].most_common()))
        for k, v in blockers.most_common(25):
            print(f"   {v:5d} {k}")
        return 0
    if cmd == "convert":
        os.makedirs(out_dir, exist_ok=True)
        paths = sorted(glob.glob(os.path.join(grw_root, "*.forge")), key=lambda q: ("_patch_" in q, q))
        index = []
        hits = {}
        for p in paths:
            for fid, ext, name, off, ln in fi.forge_entries(p):
                for key in (name, str(fid)):
                    if ext and key in args:
                        hits[key] = (p, off, ln, name)         # later forges (patches) win
        missing = [k for k in args if k not in hits]
        if missing:
            raise SystemExit(f"no entry {missing[0]!r} in {grw_root}")
        loaded = [(hits[k], list(_resources(*hits[k][:3], oodle))) for k in args]
        shape_of = _shape_map(loaded, paths, oodle) if strip_at else None
        for hit, rs in loaded:
            for r in rs:
                t = _TYPE_IDS.get(r.type_id)
                if t is None or (only_types and t not in only_types):
                    continue
                dropped, hits = [], {}
                cid = di.class_id(r)
                try:
                    data = convert(r.payload, drop_grw_only=drop, strip_physics=strip, manifest=dropped,
                                   strip_physics_at=strip_at, shape_of=shape_of, remap=remap, remapped=hits)
                except (NeedLayout, Unsupported) as e:
                    print(f"  skip {t} {r.name}: {e}")
                    index.append({"class_id": cid, "class_id_hex": f"{cid:#x}", "type": t, "name": r.name,
                                  "entry": hit[3], "skipped": str(e)})
                    continue
                for d in dropped:
                    d.update(resource=r.name, resource_class_id=di.class_id(r))
                    print(f"  dropped {d['component']} ({d['reason']}) from entity {d['entity_class_id']:#x} in {r.name}"
                          + ("; ResetData nulled" if d["reset_data_nulled"] else ""))
                manifest.extend(dropped)
                safe = re.sub(r'[<>:"/\\|?*]', "_", r.name)
                fn = os.path.join(out_dir, f"{cid}_{t}_{safe}.payload")
                open(fn, "wb").write(data)
                index.append({"class_id": cid, "class_id_hex": f"{cid:#x}", "type": t, "name": r.name,
                              "entry": hit[3], "file": os.path.basename(fn), "bytes": len(data)})
                if hits:
                    index[-1]["remapped_refs"] = {f"{k:#x}->{remap[k]:#x}": n for k, n in hits.items()}
                print(f"  wrote {fn} ({len(data):,} B)")
        import json
        json.dump(index, open(os.path.join(out_dir, "converted.json"), "w"), indent=1)
        print(f"  index of {sum('file' in x for x in index)} converted / {sum('skipped' in x for x in index)} skipped"
              f" resources in {os.path.join(out_dir, 'converted.json')}")
        for k, v in remap.items():
            n = sum(x.get("remapped_refs", {}).get(f"{k:#x}->{v:#x}", 0) for x in index)
            print(f"  --material-remap {k:#x} -> {v:#x}: {n} reference(s) re-pointed"
                  + ("" if n else " (none found: check the old ID)"))
        if manifest:
            mf = os.path.join(out_dir, "dropped_components.json")
            json.dump(manifest, open(mf, "w"), indent=1)
            print(f"  {len(manifest)} component(s) dropped; listed in {mf}")
        return 0
    raise SystemExit(f"unknown command {cmd!r}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
