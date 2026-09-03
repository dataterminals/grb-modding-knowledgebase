#!/usr/bin/env python3
"""
rebind_check.py - will this rebound garment actually move in game?

The pre-flight check for [`meta/project-goal.md`](../meta/project-goal.md): you
have taken a vanilla garment's weight painting onto a NEW mesh (lane 2B, the
bone-physics route) and you are about to import the GLB and repack. Launching the
game is the expensive step - a hung GRB needs `taskkill /F /T` - so this answers,
from files alone, the question a rebind actually fails on:

    Does the new mesh's weight painting reach the bones Reflex3 actually drives?

    python rebind_check.py --skeleton Tsec_Trench_AddonSkeleton.data ^
                           --mesh MyPoncho.glb
    python rebind_check.py --skeleton Player_Kilt_Addon.data --mesh New.glb ^
                           --donor 87874_-_TP_Tacvest_Walker_Coat_LOD0.data

READ-ONLY. Reads a skeleton `.data`, a `.glb`, and optionally a donor mesh
`.data`. Writes nothing, launches nothing, and never touches a forge.

WHY THIS TOOL CAN EXIST HERE AND NOWHERE ELSE
ATK reads GRB meshes and skeletons but **cannot parse Reflex3** - its parser
validates Mirage's constants and is gated behind `Version != Game.Mirage`, so for
GRB it keeps the constraint blob as an opaque Base64 lump. This repo decodes it
([`reflex3.py`](reflex3.py)). Answering the question above needs BOTH halves at
once: ATK's mesh reading (via [`atk_bridge.py`](atk_bridge.py), optional) and the
Reflex3 decode. See `reference/skeleton-reflex3-physics.md`.

WHAT IT CHECKS
  1. Influences per vertex <= 4. GRB garment meshes are `Joint4` - four indices
     then four weights at vertex bytes 24-31 (VERIFIED 2026-09-01 against ATK's
     own reader; the KB previously said two-bone, which was reading the colour
     channel). A JOINTS_1 set in the GLB means influences glTF will carry but
     GRB's vertex format will not.
  2. Weight coverage. A vertex with no weight does not deform - it stays put
     while the garment moves around it.
  3. UV sets and vertex colours. The failure modes `docs/10-meshes-and-skeletons.md`
     names: missing UVs, >5 UV sets, missing vertex colours.
  4. **The physics check.** Every bone Reflex3 drives, cross-referenced against
     the bones your mesh actually weights to. A driven bone with no weight is a
     dangle chain that will not move, and is also the bone most at risk of being
     dropped: ATK "removes unused bones" on GRB import.

HOW BONE NAMES ARE MATCHED - the bit that makes this work at all
Reflex3 addresses bones by **CRC32 of the exact-case bone name**. Most of GRB's
per-garment dangle bones are NOT in ATK's 820,037-name dictionary (only 8 of 30
resolve on the Walker coat), so ATK writes those glTF nodes with the *number* as
the name - `HashedData.GetHashedString` falls back to `id.ToString()`.

That fallback is load-bearing here: **a numeric node name IS the bone hash.** So
this tool resolves a node name by taking it literally when it is all digits, and
CRC32-ing it (exact, then lower, then upper, matching how ATK builds its map)
when it is not. Unresolvable names are reported rather than silently skipped.

> **Inferred, not verified:** that a GLB round-tripped through Blender preserves
> those numeric node names verbatim. Blender is free to rename nodes (`.001`
> suffixes on collision, for one). A `name.001` is stripped before matching, but
> if your exporter mangles names further this check degrades to "cannot match" -
> which it will say, loudly, rather than passing you.

> **Not verified by this tool:** that the import then repack then load actually
> works. This checks the geometry and the rigging. It cannot tell you whether a
> modified skeleton loads at all - that is still the open both-patch-forge
> question in `meta/next-session.md`.
"""
import sys
import os
import json
import struct
import zlib
import importlib.util

_HERE = os.path.dirname(os.path.abspath(__file__))

# glTF component types -> (struct code, size, is_int)
_CTYPE = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
          5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
          "MAT2": 4, "MAT3": 9, "MAT4": 16}


def _sibling(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(_HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- glTF reading

class GLB:
    """Minimal glTF/GLB reader - stdlib only, no Blender, no dependencies."""

    def __init__(self, path):
        self.path = path
        blob = open(path, "rb").read()
        if blob[:4] == b"glTF":                      # binary .glb
            _magic, _ver, _len = struct.unpack_from("<III", blob, 0)
            self.json, self.bin, off = None, b"", 12
            while off < len(blob) - 8:
                clen, ctype = struct.unpack_from("<II", blob, off)
                data = blob[off + 8:off + 8 + clen]
                if ctype == 0x4E4F534A:              # 'JSON'
                    self.json = json.loads(data.decode("utf-8"))
                elif ctype == 0x004E4942:            # 'BIN\0'
                    self.bin = data
                off += 8 + clen + ((4 - clen % 4) % 4 if clen % 4 else 0)
            if self.json is None:
                raise ValueError(f"{path}: no JSON chunk - not a valid GLB")
        else:                                        # plain .gltf
            self.json = json.loads(blob.decode("utf-8"))
            self.bin = b""

    def _buffer(self, i):
        buf = self.json["buffers"][i]
        if "uri" not in buf:
            return self.bin
        uri = buf["uri"]
        if uri.startswith("data:"):
            import base64
            return base64.b64decode(uri.split(",", 1)[1])
        return open(os.path.join(os.path.dirname(self.path), uri), "rb").read()

    def accessor(self, i):
        """Read accessor i as a list of tuples (or scalars)."""
        acc = self.json["accessors"][i]
        n = acc["count"]
        ncomp = _NCOMP[acc["type"]]
        code, size = _CTYPE[acc["componentType"]]
        norm = acc.get("normalized", False)
        if "bufferView" not in acc:
            return [(0,) * ncomp] * n
        bv = self.json["bufferViews"][acc["bufferView"]]
        data = self._buffer(bv.get("buffer", 0))
        base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = bv.get("byteStride") or ncomp * size
        out = []
        for k in range(n):
            vals = struct.unpack_from("<" + code * ncomp, data, base + k * stride)
            if norm and code in ("B", "H"):
                mx = 255.0 if code == "B" else 65535.0
                vals = tuple(v / mx for v in vals)
            elif norm and code in ("b", "h"):
                mx = 127.0 if code == "b" else 32767.0
                vals = tuple(max(v / mx, -1.0) for v in vals)
            out.append(vals[0] if ncomp == 1 else vals)
        return out

    def primitives(self):
        for mi, mesh in enumerate(self.json.get("meshes", [])):
            for pi, prim in enumerate(mesh.get("primitives", [])):
                yield mesh.get("name", f"mesh{mi}"), pi, prim

    def skin_joint_names(self):
        """-> list of node names, indexed the way JOINTS_n values index them."""
        nodes = self.json.get("nodes", [])
        skins = self.json.get("skins", [])
        if not skins:
            return []
        return [nodes[j].get("name", str(j)) if j < len(nodes) else str(j)
                for j in skins[0].get("joints", [])]


# ------------------------------------------------------------ name <-> hash

def name_to_hashes(name):
    """Candidate CRC32 hashes for a glTF node name.

    A purely numeric name IS the hash - that is ATK's `GetHashedString` fallback
    for the (many) GRB bones its dictionary does not know. Otherwise hash the
    name exact/lower/upper, matching how ATK builds its map."""
    base = name.split(".")[0] if _blender_suffix(name) else name
    if base.isdigit():
        v = int(base)
        if v <= 0xFFFFFFFF:
            return {v}, True
    cands = {zlib.crc32(v.encode("ascii", "replace")) & 0xFFFFFFFF
             for v in (base, base.lower(), base.upper())}
    return cands, False


def _blender_suffix(name):
    """True for Blender's collision-avoidance suffix, e.g. `Spine2.001`."""
    tail = name.rsplit(".", 1)
    return len(tail) == 2 and len(tail[1]) == 3 and tail[1].isdigit()


# ------------------------------------------------------------------- checks

class Report:
    def __init__(self):
        self.rows = []
        self.worst = "PASS"

    def add(self, level, title, detail=""):
        order = {"PASS": 0, "INFO": 0, "WARN": 1, "FAIL": 2}
        if order[level] > order[self.worst]:
            self.worst = level
        self.rows.append((level, title, detail))

    def render(self):
        icon = {"PASS": "  ok  ", " INFO": "      ",
                "INFO": "      ", "WARN": " WARN ", "FAIL": " FAIL "}
        for level, title, detail in self.rows:
            print(f"[{icon[level]}] {title}")
            for line in (detail.splitlines() if detail else []):
                print(f"           {line}")


def check_mesh(glb, rep):
    """Influences, coverage, UV sets, vertex colours."""
    joint_sets = uv_sets = color_sets = 0
    total_verts = unweighted = 0
    infl_hist = {}
    weighted_joints = {}
    names = glb.skin_joint_names()

    if not names:
        rep.add("FAIL", "No skin in the GLB",
                "There is no armature binding, so nothing can be driven by bones.\n"
                "A rebind needs the new mesh weighted to the donor's rig.")
        return names, weighted_joints, 0

    for mname, pi, prim in glb.primitives():
        attrs = prim.get("attributes", {})
        js = sorted(k for k in attrs if k.startswith("JOINTS_"))
        ws = sorted(k for k in attrs if k.startswith("WEIGHTS_"))
        joint_sets = max(joint_sets, len(js))
        uv_sets = max(uv_sets, len([k for k in attrs if k.startswith("TEXCOORD_")]))
        # ATK/SharpGLTF writes the 2nd..5th colour set as the custom attributes
        # `_COLOR_1`..`_COLOR_4` - glTF only standardises COLOR_n, so extras take
        # the underscore prefix. Counting only "COLOR_" undercounts a real GRB
        # garment 5 sets down to 1. (Seen on TP_Tacvest_Walker_Coat_LOD0.)
        color_sets = max(color_sets, len([k for k in attrs
                                          if k.startswith("COLOR_")
                                          or k.startswith("_COLOR_")]))
        if not js or not ws:
            rep.add("FAIL", f"Primitive {mname}[{pi}] has no joints/weights",
                    "Unrigged geometry cannot follow a physics bone.")
            continue
        jdata = [glb.accessor(attrs[k]) for k in js]
        wdata = [glb.accessor(attrs[k]) for k in ws]
        count = len(jdata[0])
        total_verts += count
        for v in range(count):
            n = 0
            for jset, wset in zip(jdata, wdata):
                for j, w in zip(jset[v], wset[v]):
                    if w > 0.0:
                        n += 1
                        weighted_joints[int(j)] = weighted_joints.get(int(j), 0.0) + float(w)
            infl_hist[n] = infl_hist.get(n, 0) + 1
            if n == 0:
                unweighted += 1

    if joint_sets > 1:
        rep.add("FAIL", f"{joint_sets} JOINTS sets = up to {joint_sets * 4} influences per vertex",
                "GRB's garment vertex format is Joint4 - four influences, full stop.\n"
                "glTF will carry these; the GRB mesh will not. Limit to 4 in Blender\n"
                "(Weight Paint > Weights > Limit Total, or the Limit Total modifier).")
    elif joint_sets == 1:
        rep.add("PASS", "Influences per vertex within GRB's Joint4 limit")

    over = {k: v for k, v in infl_hist.items() if k > 4}
    if over:
        rep.add("FAIL", f"{sum(over.values())} vertices carry more than 4 non-zero weights",
                f"histogram of over-limit vertices: {dict(sorted(over.items()))}")

    if total_verts:
        pct = 100.0 * (total_verts - unweighted) / total_verts
        if unweighted:
            rep.add("FAIL", f"Weight coverage {pct:.2f}% - {unweighted} of {total_verts} "
                            f"vertices have NO weight",
                    "Those vertices will not deform. They stay rigidly in place while\n"
                    "the rest of the garment moves - the classic torn-looking result.")
        else:
            rep.add("PASS", f"Weight coverage 100% ({total_verts} vertices)")
        rep.add("INFO", f"Influences per vertex: {dict(sorted(infl_hist.items()))}")

    if uv_sets == 0:
        rep.add("FAIL", "No UV set", "GRB garments need UVs; the material will not map.")
    elif uv_sets > 5:
        rep.add("FAIL", f"{uv_sets} UV sets (GRB accepts at most 5)")
    else:
        rep.add("PASS", f"{uv_sets} UV set{'s' if uv_sets != 1 else ''}")

    if color_sets == 0:
        rep.add("WARN", "No vertex colours",
                "A GRB garment slot that expects vertex colours and does not get them\n"
                "renders with corrupted shading - see docs/10. If the donor had them,\n"
                "re-run the transfer with --with-colors.")
    else:
        rep.add("PASS", f"{color_sets} vertex colour set{'s' if color_sets != 1 else ''}")

    return names, weighted_joints, total_verts


def check_physics(skel_path, names, weighted_joints, rep, oodle_override=None,
                  donor_bones=None):
    """The money check: do the weights reach the bones Reflex3 drives?

    `donor_bones` is the set of bone-name hashes the vanilla garment actually
    weighted. Supplying it scopes the check to bones this garment is *supposed*
    to drive; without it the whole rig is in scope and findings are WARNs."""
    r3 = _sibling("reflex3")
    di = _sibling("data_inspect")
    oodle = di.Oodle(di.find_oodle(skel_path, oodle_override))
    blob, skel_bones = r3.load_blob(skel_path, oodle)
    if not blob:
        rep.add("FAIL", f"No Reflex3 constraints in {os.path.basename(skel_path)}",
                "This skeleton carries no bone physics, so there is nothing for a\n"
                "rebound mesh to inherit. Only 512 of GRB's 2,469 skeletons do.\n"
                "See reference/skeleton-reflex3-physics.md for ones that work.")
        return

    phys_type = getattr(r3, "PHYSICS_TYPE", None)
    driven, physics_driven = {}, set()
    for rec in r3.parse_blob(blob):
        if rec.get("error") or rec.get("bone") is None:
            continue
        driven.setdefault(rec["bone"], set()).add(rec["type"])
        if phys_type is not None and rec["type"] == phys_type:
            physics_driven.add(rec["bone"])
    if not driven:
        rep.add("FAIL", "Reflex3 blob present but no constraint records decoded")
        return

    # map every glTF joint slot -> candidate hashes
    slot_hashes, unmatchable = [], []
    for idx, nm in enumerate(names):
        cands, literal = name_to_hashes(nm)
        slot_hashes.append((idx, nm, cands, literal))
        if not literal and not (cands & set(driven)) and not (cands & skel_bones):
            unmatchable.append(nm)

    def weight_of(hashval):
        total = 0.0
        for idx, _nm, cands, _lit in slot_hashes:
            if hashval in cands:
                total += weighted_joints.get(idx, 0.0)
        return total

    def present(hashval):
        return any(hashval in cands for _i, _n, cands, _l in slot_hashes)

    # Which driven bones is THIS garment supposed to use? A character rig drives
    # hair, straps and everything else; a coat is never meant to weight them all.
    # The donor's own bone usage is the honest reference set - without it we
    # cannot tell "you lost the coat's physics" from "the rig also drives hair".
    scoped = sorted(set(driven) & donor_bones) if donor_bones else sorted(driven)
    out_of_scope = len(driven) - len(scoped)

    missing, dead, live = [], [], []
    for bone in scoped:
        label = _label(bone, skel_bones)
        if not present(bone):
            missing.append(label)
        elif weight_of(bone) <= 0.0:
            dead.append(label)
        else:
            live.append((label, weight_of(bone)))

    kinds = sorted({t for ts in driven.values() for t in ts})
    rep.add("INFO", f"Reflex3 drives {len(driven)} bones in "
                    f"{os.path.basename(skel_path)}",
            f"constraint types present: {kinds}"
            + (f"; {len(physics_driven)} bone(s) under Reflex3Physics (type {phys_type})"
               if phys_type is not None else ""))

    if donor_bones and not scoped:
        rep.add("FAIL", "This skeleton drives NONE of the bones your donor uses",
                f"{os.path.basename(skel_path)} drives {len(driven)} bones and the\n"
                "donor weights none of them - so there is no physics here to\n"
                "inherit. Almost certainly the wrong skeleton for this garment.\n"
                "Nothing below would have been checked, so this is a hard stop.")
        return

    if out_of_scope:
        rep.add("INFO", f"{out_of_scope} driven bones ignored - the donor does not "
                        f"use them either",
                "A character rig drives hair, straps and other garments' bones too.\n"
                "Only the ones your donor actually weighted are your problem.")

    # Severity depends on whether we know the donor's bone set. Without it, an
    # unweighted driven bone may simply be one this garment never used - a WARN,
    # not a FAIL, because the tool genuinely cannot tell the difference.
    sev = "FAIL" if donor_bones else "WARN"
    scope = "the donor uses" if donor_bones else "the rig drives"

    if live:
        top = ", ".join(f"{n}" for n, _w in sorted(live, key=lambda x: -x[1])[:8])
        rep.add("PASS", f"{len(live)} of the {len(scoped)} bones {scope} carry weight "
                        f"from your mesh", f"e.g. {top}")
    if dead:
        rep.add(sev, f"{len(dead)} bones {scope} are in the rig but carry NO weight",
                "These chains will not move, and ATK 'removes unused bones' on GRB\n"
                "import - so they may vanish from the mesh entirely and take the\n"
                "physics with them. Weight-paint the new mesh onto them.\n"
                + "  " + ", ".join(dead[:16]) + (" ..." if len(dead) > 16 else ""))
    if missing:
        rep.add(sev, f"{len(missing)} bones {scope} are absent from the GLB's skin",
                "The rig you transferred from is not the rig this skeleton drives,\n"
                "or the export dropped them.\n"
                + "  " + ", ".join(missing[:16]) + (" ..." if len(missing) > 16 else ""))
    if not dead and not missing:
        rep.add("PASS", f"Every bone {scope} is present and weighted in your mesh")
    if not donor_bones:
        rep.add("INFO", "No --donor given, so the checks above are scoped to the "
                        "WHOLE rig",
                "Pass --donor <vanilla garment .data> to scope them to the bones the\n"
                "original garment actually used. Without it, a full character rig\n"
                "will report dozens of bones your garment was never meant to touch.")

    if unmatchable:
        rep.add("WARN", f"{len(unmatchable)} bone names could not be matched to a hash",
                "Neither numeric (ATK's fallback form) nor CRC32-matching any bone in\n"
                "this skeleton. Most likely your exporter renamed them, which would\n"
                "make the results above unreliable.\n"
                + "  " + ", ".join(unmatchable[:12]) + (" ..." if len(unmatchable) > 12 else ""))


def _label(bone_hash, skel_bones):
    return str(bone_hash) + ("" if bone_hash in skel_bones else " (?)")


def check_donor(donor_path, rep):
    """Profile the vanilla garment -> the set of bone hashes it actually weights.

    That set is what scopes the physics check: it is the difference between
    'you lost the coat's physics' and 'the rig also drives somebody's hair'."""
    try:
        sys.path.insert(0, _HERE)
        import atk_bridge as ab
        mesh = ab.read_mesh(donor_path)
    except Exception as e:
        rep.add("WARN", "Donor profile unavailable",
                f"atk_bridge could not read it: {str(e).splitlines()[0][:90]}\n"
                "Falling back to whole-rig scope for the physics check.")
        return None
    vb = bytes(mesh.VertexBuffer)
    stride = mesh.VertexStride
    bone_hashes = [b.Name for b in mesh.Bones]
    hist, used = {}, set()
    for k in range(len(vb) // stride):
        n = 0
        for i in range(4):
            if vb[k * stride + 28 + i] > 0:          # weight byte non-zero
                n += 1
                slot = vb[k * stride + 24 + i]       # bone index into mesh.Bones
                if slot < len(bone_hashes):
                    used.add(bone_hashes[slot])
        hist[n] = hist.get(n, 0) + 1
    rep.add("INFO", f"Donor {os.path.basename(donor_path)}: "
                    f"{mesh.Vertices.Count} verts, {mesh.Faces.Count} tris, "
                    f"{mesh.Bones.Count} bones ({len(used)} actually weighted)",
            f"influences per vertex: {dict(sorted(hist.items()))}\n"
            f"vertex format: {mesh.VertexFormat}")
    return used


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = {}
    rest = list(argv[1:])
    for flag in ("--skeleton", "--mesh", "--donor", "--oodle"):
        if flag in rest:
            k = rest.index(flag)
            args[flag] = rest[k + 1]
            del rest[k:k + 2]
    if "--mesh" not in args or "--skeleton" not in args:
        print(__doc__)
        return 1

    print("=" * 70)
    print(f"MESH      {os.path.basename(args['--mesh'])}")
    print(f"SKELETON  {os.path.basename(args['--skeleton'])}")
    print("=" * 70)

    rep = Report()
    glb = GLB(args["--mesh"])
    names, weighted, _n = check_mesh(glb, rep)
    # Donor first: its bone usage scopes the physics check below.
    donor_bones = check_donor(args["--donor"], rep) if "--donor" in args else None
    if names:
        check_physics(args["--skeleton"], names, weighted, rep,
                      args.get("--oodle"), donor_bones)
    rep.render()

    print("=" * 70)
    verdict = {"PASS": "PASS - nothing here says this will fail in game.",
               "WARN": "WARN - importable, but read the warnings first.",
               "FAIL": "FAIL - fix these before repacking."}[rep.worst]
    print(verdict)
    print("Reminder: this checks files, not the game. Whether a modified skeleton")
    print("loads at all is still open - see meta/next-session.md.")
    return 0 if rep.worst != "FAIL" else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
