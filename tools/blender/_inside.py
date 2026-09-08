"""
_inside.py - the half of the bridge that runs INSIDE Blender.

You do not run this yourself. `grbblend.py` runs it for you, like this:

    blender.exe --background --factory-startup --python _inside.py -- <json>

It reads one JSON argument (the command and its options), does the work with
Blender's Python API, and prints a JSON report between two sentinel lines so the
host side can find it in among Blender's own console chatter.

Nothing here touches your GRB install. It only reads and writes the files you
point it at.
"""

import bpy
import bmesh          # noqa: F401  (kept importable for `run` snippets)
import sys
import os
import json
import traceback
from collections import Counter

BEGIN = "<<<GRBBLEND-JSON"
END = "GRBBLEND-JSON>>>"

# A weight below this counts as "not really weighted to that bone".
WEIGHT_EPS = 1e-5


# --------------------------------------------------------------------------
# plumbing
# --------------------------------------------------------------------------

def emit(payload):
    """Print the report where the host side can find it."""
    sys.stdout.write("\n" + BEGIN + "\n")
    sys.stdout.write(json.dumps(payload, indent=2, default=str))
    sys.stdout.write("\n" + END + "\n")
    sys.stdout.flush()


def get_args():
    """Everything after the bare `--` is ours."""
    argv = sys.argv
    if "--" not in argv:
        return {}
    return json.loads(argv[argv.index("--") + 1])


def op_kwargs(op, kwargs):
    """
    Drop any keyword the installed Blender's version of `op` does not know.

    This is the compatibility layer proper: glTF export options get renamed and
    added between Blender releases, so we ask the operator what it actually
    accepts instead of assuming.
    """
    try:
        known = set(op.get_rna_type().properties.keys())
    except Exception:
        return kwargs
    return {k: v for k, v in kwargs.items() if k in known}


def reset_scene():
    """Empty scene, no default cube."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def load_file(path):
    """Import one file into the current scene. Returns the objects it added."""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    before = set(bpy.data.objects)
    ext = os.path.splitext(path)[1].lower()

    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".blend":
        with bpy.data.libraries.load(path) as (src, dst):
            dst.objects = list(src.objects)
        for obj in dst.objects:
            if obj is not None:
                bpy.context.scene.collection.objects.link(obj)
    else:
        raise ValueError("do not know how to import %r" % ext)

    return [o for o in bpy.data.objects if o not in before]


def is_importer_scaffolding(obj):
    """True for objects Blender's glTF importer added for display, not content.

    Importing a *skinned* GLB makes Blender synthesise a bone-display mesh - a
    42-vertex icosphere - which is scaffolding, not part of the file. Verified
    2026-09-08: a rigged GLB produces one, an unrigged GLB does not, and the
    exported GLB's own JSON contains only the single real mesh.

    Left unfiltered it was reported as a second mesh and raised a spurious
    "no vertex colors" warning on *every* rigged GRB garment - i.e. on exactly
    the files this tool exists to validate. See meta/research-log.md 2026-09-08.

    Matched on two structural signals rather than the name, which a real mesh
    could legitimately share: membership of the importer's own
    `glTF_not_exported` collection, and being referenced as a pose bone's
    custom shape.
    """
    if any(c.name == "glTF_not_exported" for c in obj.users_collection):
        return True
    for arm in bpy.data.objects:
        if arm.type != "ARMATURE" or arm.pose is None:
            continue
        for pbone in arm.pose.bones:
            if pbone.custom_shape is obj:
                return True
    return False


# --------------------------------------------------------------------------
# inspection - the checklist from docs/10-meshes-and-skeletons.md
# --------------------------------------------------------------------------

def influence_stats(obj):
    """
    How many bones pull on each vertex, and how many distinct bones the mesh
    uses in total.

    Both matter for GRB: ATK enforces a per-primitive bone limit, and glTF
    itself carries 4 influences per vertex per JOINTS set - so a vertex with 7
    influences quietly loses 3 of them unless the exporter writes a second set.
    """
    mesh = obj.data
    per_vertex = Counter()
    used_groups = set()
    unweighted = 0

    for v in mesh.vertices:
        live = [g for g in v.groups if g.weight > WEIGHT_EPS]
        per_vertex[len(live)] += 1
        if not live:
            unweighted += 1
        for g in live:
            used_groups.add(g.group)

    return {
        "influences_per_vertex": {str(k): v for k, v in sorted(per_vertex.items())},
        "max_influences": max(per_vertex) if per_vertex else 0,
        "distinct_bones_used": len(used_groups),
        "vertices_with_no_weight": unweighted,
    }


def describe_mesh(obj):
    mesh = obj.data
    tris = sum(max(len(p.vertices) - 2, 0) for p in mesh.polygons)

    info = {
        "object": obj.name,
        "mesh": mesh.name,
        "vertices": len(mesh.vertices),
        "polygons": len(mesh.polygons),
        "triangles": tris,
        "uv_layers": [uv.name for uv in mesh.uv_layers],
        "color_attributes": [
            {"name": c.name, "domain": c.domain, "type": c.data_type}
            for c in mesh.color_attributes
        ],
        "materials": [m.name if m else None for m in mesh.materials],
        "modifiers": [{"name": m.name, "type": m.type} for m in obj.modifiers],
        "vertex_groups": [g.name for g in obj.vertex_groups],
        "vertex_group_count": len(obj.vertex_groups),
        "parent": obj.parent.name if obj.parent else None,
        "shape_keys": (
            [k.name for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else []
        ),
    }

    if obj.vertex_groups:
        info.update(influence_stats(obj))

    # The doc's named failure modes, checked.
    warnings = []
    if not mesh.uv_layers:
        warnings.append(
            "no UV layer - ATK warns and fills (0,0); shading and tangents will be wrong")
    if len(mesh.uv_layers) > 5:
        warnings.append(
            "%d UV sets - GRB meshes carry up to 5" % len(mesh.uv_layers))
    if not mesh.color_attributes:
        warnings.append(
            "no vertex colors - GRB uses them; match the donor mesh or ATK warns")
    if info.get("max_influences", 0) > 4:
        warnings.append(
            "up to %d bone influences per vertex - glTF carries 4 per JOINTS set"
            % info["max_influences"])
    if info.get("vertices_with_no_weight"):
        warnings.append(
            "%d vertices carry no bone weight at all - they will not deform"
            % info["vertices_with_no_weight"])
    if len(mesh.materials) > 1:
        warnings.append(
            "%d materials - each becomes its own primitive, each with its own "
            "bone limit" % len(mesh.materials))
    info["warnings"] = warnings
    return info


def describe_armature(obj):
    arm = obj.data
    bones = list(arm.bones)
    return {
        "object": obj.name,
        "armature": arm.name,
        "bone_count": len(bones),
        "root_bones": [b.name for b in bones if b.parent is None],
        "bones": [
            {"name": b.name, "parent": b.parent.name if b.parent else None}
            for b in bones
        ],
    }


def describe_scene():
    meshes, armatures, others, scaffolding = [], [], [], []
    for obj in bpy.data.objects:
        if is_importer_scaffolding(obj):
            scaffolding.append(obj.name)
            continue
        if obj.type == "MESH":
            meshes.append(describe_mesh(obj))
        elif obj.type == "ARMATURE":
            armatures.append(describe_armature(obj))
        else:
            others.append({"object": obj.name, "type": obj.type})
    return {"meshes": meshes, "armatures": armatures, "other_objects": others,
            "ignored_scaffolding": scaffolding}


# --------------------------------------------------------------------------
# scene helpers
# --------------------------------------------------------------------------

def pick_mesh(objs, name=None):
    cands = [o for o in objs if o.type == "MESH"]
    if name:
        # An explicit name is honoured even if it names scaffolding.
        for o in cands:
            if o.name == name:
                return o
        raise ValueError(
            "no mesh named %r (have: %s)" % (name, ", ".join(o.name for o in cands)))
    # Never auto-pick the glTF importer's bone-display mesh.
    real = [o for o in cands if not is_importer_scaffolding(o)]
    if not real:
        raise ValueError(
            "no mesh objects found"
            if not cands
            else "the only meshes present are glTF importer scaffolding (%s); "
                 "pass an explicit mesh name to override"
                 % ", ".join(o.name for o in cands))
    # Biggest mesh wins - the garment, not a stray attachment.
    return max(real, key=lambda o: len(o.data.vertices))


def pick_armature(objs):
    for o in objs:
        if o.type == "ARMATURE":
            return o
    return None


def select_only(objs, active):
    for o in bpy.data.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


#: Which mapping argument each transferable data type wants. Vertex groups live
#: on points; UVs and corner colours live on face corners ("loops"), and Blender
#: takes a different keyword for each.
LOOP_DOMAIN_TYPES = {"UV", "COLOR_CORNER", "CUSTOM_NORMAL"}


def run_transfer(src, dst, data_type, mapping):
    """One data_transfer pass from `src` onto `dst`."""
    kwargs = {
        "data_type": data_type,
        "use_create": True,
        "layers_select_src": "ALL",
        "layers_select_dst": "NAME",
        "mix_mode": "REPLACE",
        "use_object_transform": True,
    }
    if data_type in LOOP_DOMAIN_TYPES:
        kwargs["loop_mapping"] = (
            "POLYINTERP_NEAREST" if mapping.startswith("POLYINTERP")
            else "NEAREST_POLYNOR")
    else:
        kwargs["vert_mapping"] = mapping

    with bpy.context.temp_override(
        active_object=src, object=src,
        selected_objects=[src, dst], selected_editable_objects=[src, dst],
    ):
        bpy.ops.object.data_transfer(
            **op_kwargs(bpy.ops.object.data_transfer, kwargs))


def export_glb(path, **overrides):
    """
    Export the scene to GLB with settings that survive the trip into ATK.

    Tangents go out because missing ones were a classic ATK import crash; it
    recalculates now, but shipping them costs nothing. Vertex colours and every
    UV set go too - GRB reads them.
    """
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    wanted = {
        "filepath": path,
        "export_format": "GLB",
        "export_yup": True,
        "export_apply": False,
        "export_texcoords": True,
        "export_normals": True,
        "export_tangents": True,
        "export_colors": True,
        "export_attributes": True,
        "export_skins": True,
        "export_all_influences": True,
        "export_materials": "EXPORT",
        "use_selection": False,
    }
    wanted.update(overrides)
    bpy.ops.export_scene.gltf(**op_kwargs(bpy.ops.export_scene.gltf, wanted))
    return path


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_inspect(args):
    reset_scene()
    loaded = []
    for path in args["files"]:
        added = load_file(path)
        loaded.append({"file": path, "objects_added": len(added)})
    report = describe_scene()
    report["loaded"] = loaded
    report["blender"] = bpy.app.version_string
    return report


def cmd_transfer_weights(args):
    """
    Sami's move, scripted: take the weight painting off an in-game garment and
    put it onto an outside-source mesh.

    Source = the vanilla garment (rigged, weight-painted).
    Target = the new mesh (usually bare geometry).
    """
    reset_scene()

    src_objs = load_file(args["source"])
    src_mesh = pick_mesh(src_objs, args.get("source_mesh"))
    armature = pick_armature(src_objs)

    tgt_objs = load_file(args["target"])
    tgt_mesh = pick_mesh(tgt_objs, args.get("target_mesh"))

    before = {
        "source": describe_mesh(src_mesh),
        "target": describe_mesh(tgt_mesh),
        "armature": describe_armature(armature) if armature else None,
    }

    if not src_mesh.vertex_groups:
        raise ValueError(
            "source mesh %r has no vertex groups - nothing to transfer. Is it the "
            "rigged vanilla garment?" % src_mesh.name)

    if args.get("clear_target_groups", True):
        for g in list(tgt_mesh.vertex_groups):
            tgt_mesh.vertex_groups.remove(g)

    # data_transfer runs FROM the active object TO the other selected ones.
    select_only([src_mesh, tgt_mesh], active=src_mesh)

    mapping = args.get("vert_mapping", "POLYINTERP_NEAREST")
    transferred = ["weights"]
    run_transfer(src_mesh, tgt_mesh, "VGROUP_WEIGHTS", mapping)

    # Weights are not the only per-vertex data GRB reads. Vertex colours drive
    # shading and are a documented source of corrupted-looking imports, and a
    # new mesh usually wants the donor's UV layout too. Both are opt-in: they
    # overwrite whatever the new mesh already had.
    if args.get("with_colors"):
        if src_mesh.data.color_attributes:
            run_transfer(src_mesh, tgt_mesh, "COLOR_CORNER", mapping)
            transferred.append("vertex colors")
    if args.get("with_uvs"):
        if src_mesh.data.uv_layers:
            run_transfer(src_mesh, tgt_mesh, "UV", mapping)
            transferred.append("UVs")

    # Hook the new mesh to the same rig, or it still will not move in game.
    if armature is not None and args.get("bind_armature", True):
        if not any(m.type == "ARMATURE" for m in tgt_mesh.modifiers):
            mod = tgt_mesh.modifiers.new(name="Armature", type="ARMATURE")
            mod.object = armature
        tgt_mesh.parent = armature
        tgt_mesh.matrix_parent_inverse = armature.matrix_world.inverted()

    if args.get("drop_source", True):
        bpy.data.objects.remove(src_mesh, do_unlink=True)

    after = describe_mesh(tgt_mesh)

    out = export_glb(args["out"]) if args.get("out") else None

    coverage = None
    if after.get("vertices_with_no_weight") is not None:
        total = after["vertices"]
        covered = total - after["vertices_with_no_weight"]
        coverage = round(100.0 * covered / total, 2) if total else 0.0

    return {
        "blender": bpy.app.version_string,
        "before": before,
        "after": after,
        "transferred": transferred,
        "groups_transferred": after["vertex_group_count"],
        "weight_coverage_percent": coverage,
        "exported": out,
    }


def cmd_run(args):
    """Run an arbitrary Python snippet inside Blender. The escape hatch."""
    reset_scene()
    for path in args.get("files", []):
        load_file(path)

    scope = {
        "bpy": bpy,
        "bmesh": bmesh,
        "describe_scene": describe_scene,
        "describe_mesh": describe_mesh,
        "describe_armature": describe_armature,
        "pick_mesh": pick_mesh,
        "pick_armature": pick_armature,
        "select_only": select_only,
        "export_glb": export_glb,
        "load_file": load_file,
        "result": None,
    }
    code = args.get("code")
    if not code and args.get("script"):
        with open(args["script"], "r", encoding="utf-8") as fh:
            code = fh.read()
    exec(compile(code, "<grbblend-snippet>", "exec"), scope)
    return {"blender": bpy.app.version_string, "result": scope.get("result")}


def cmd_selftest(args):
    """
    Prove the whole path works, without touching a single game file.

    Builds a fake "coat" (rigged, weight-painted cylinder) and a fake "poncho"
    (a differently-shaped, differently-tessellated cone), writes both to GLB,
    runs the real transfer-weights code on them, then reloads the result and
    checks the weights actually survived.
    """
    workdir = os.path.abspath(args["workdir"])
    os.makedirs(workdir, exist_ok=True)
    coat = os.path.join(workdir, "_selftest_coat.glb")
    poncho = os.path.join(workdir, "_selftest_poncho.glb")
    result_path = os.path.join(workdir, "_selftest_result.glb")

    # --- the "coat": a cylinder on a 3-bone chain -------------------------
    reset_scene()
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.5, depth=2.0)
    body = bpy.context.active_object
    body.name = "Coat"
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.subdivide(number_cuts=6)
    bpy.ops.object.mode_set(mode="OBJECT")
    body.data.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")

    bpy.ops.object.armature_add(location=(0, 0, -1))
    arm = bpy.context.active_object
    arm.name = "CoatRig"
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    root = eb[0]
    root.name = "Coat_Root"
    root.head, root.tail = (0, 0, 0), (0, 0, 0.7)
    prev = root
    for i in range(2):
        b = eb.new("Coat_Panel_%d" % (i + 1))
        b.head = prev.tail
        b.tail = (0, 0, prev.tail.z + 0.7)
        b.parent = prev
        b.use_connect = True
        prev = b
    bpy.ops.object.mode_set(mode="OBJECT")

    select_only([body, arm], active=arm)
    with bpy.context.temp_override(
        active_object=arm, object=arm,
        selected_objects=[body, arm], selected_editable_objects=[body, arm],
    ):
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")

    # `armature_add` leaves a bone-widget mesh lying around in some Blender
    # versions. Ship only the two objects the test is about.
    for obj in list(bpy.data.objects):
        if obj not in (body, arm):
            bpy.data.objects.remove(obj, do_unlink=True)

    coat_desc = describe_mesh(body)
    export_glb(coat)

    # --- the "poncho": different shape, different topology, no rig --------
    reset_scene()
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.7, depth=2.0)
    pon = bpy.context.active_object
    pon.name = "Poncho"
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.subdivide(number_cuts=4)
    bpy.ops.object.mode_set(mode="OBJECT")
    export_glb(poncho)

    # --- the real thing ---------------------------------------------------
    transfer = cmd_transfer_weights({
        "source": coat,
        "target": poncho,
        "out": result_path,
        "with_colors": True,
    })

    # --- read it back and check ------------------------------------------
    verify = cmd_inspect({"files": [result_path]})
    vmesh = next((m for m in verify["meshes"] if m["object"].startswith("Poncho")),
                 verify["meshes"][0] if verify["meshes"] else {})

    checks = {
        "coat_was_rigged": coat_desc["vertex_group_count"] >= 3,
        "weights_landed_on_poncho": transfer["groups_transferred"] >= 3,
        "every_poncho_vertex_weighted":
            transfer["after"].get("vertices_with_no_weight", -1) == 0,
        "vertex_colors_came_across":
            len(transfer["after"]["color_attributes"]) >= 1,
        "survived_glb_round_trip": vmesh.get("vertex_group_count", 0) >= 3,
        "weights_still_complete_after_round_trip":
            vmesh.get("vertices_with_no_weight", -1) == 0,
        "result_has_armature": len(verify["armatures"]) >= 1,
    }

    return {
        "blender": bpy.app.version_string,
        "workdir": workdir,
        "coat": coat_desc,
        "transfer": transfer,
        "reloaded": vmesh,
        "checks": checks,
        "passed": all(checks.values()),
    }


COMMANDS = {
    "inspect": cmd_inspect,
    "transfer-weights": cmd_transfer_weights,
    "run": cmd_run,
    "selftest": cmd_selftest,
}


def main():
    try:
        args = get_args()
        cmd = args.get("command")
        if cmd not in COMMANDS:
            raise ValueError(
                "unknown command %r (have: %s)" % (cmd, ", ".join(COMMANDS)))
        payload = COMMANDS[cmd](args)
        emit({"ok": True, "command": cmd, "report": payload})
    except Exception as exc:
        emit({
            "ok": False,
            "error": "%s: %s" % (type(exc).__name__, exc),
            "traceback": traceback.format_exc(),
        })


main()
