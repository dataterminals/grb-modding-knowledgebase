"""
GRB Modding Helper - a Blender add-on.

Puts a "GRB" tab in the 3D viewport sidebar (press N) with the checks that
decide whether a mesh will survive the trip into Ghost Recon: Breakpoint, plus
one-click versions of the two operations you'll actually repeat.

Install: Blender > Edit > Preferences > Add-ons > the v dropdown, top right >
Install from Disk... > pick this file > tick the checkbox.

Then press N in the 3D viewport and click the GRB tab.

Nothing here touches your GRB install. It only looks at what's open in Blender.

Background: tools/blender/README.md and docs/10-meshes-and-skeletons.md in the
GRB Modding Knowledgebase.
"""

bl_info = {
    "name": "GRB Modding Helper",
    "author": "GRB Modding Knowledgebase",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar (N) > GRB",
    "description": "Mesh checks and weight transfer for Ghost Recon: Breakpoint modding",
    "category": "Object",
}

import bpy
import bmesh
from bpy.props import (BoolProperty, EnumProperty, IntProperty, StringProperty,
                       PointerProperty)
from bpy.types import Operator, Panel, PropertyGroup
from bpy_extras.io_utils import ExportHelper

WEIGHT_EPS = 1e-5

# GRB meshes carry up to 5 UV sets; glTF carries 4 bone influences per JOINTS
# set. Both numbers come from docs/10-meshes-and-skeletons.md.
MAX_UV_SETS = 5
MAX_INFLUENCES = 4


# --------------------------------------------------------------------------
# stored results
# --------------------------------------------------------------------------

class GRBAnalysis(PropertyGroup):
    """Where the expensive per-vertex pass parks its answers."""
    valid: BoolProperty(default=False)
    analyzed_object: StringProperty(default="")
    max_influences: IntProperty(default=0)
    unweighted: IntProperty(default=0)
    bones_used: IntProperty(default=0)
    over_limit: IntProperty(default=0)


class GRBSettings(PropertyGroup):
    with_colors: BoolProperty(
        name="Also copy vertex colors",
        description="GRB reads vertex colors. A weight transfer alone leaves "
                    "the donor's colors behind, which is the classic "
                    "corrupted-shading import",
        default=True)
    with_uvs: BoolProperty(
        name="Also copy UVs",
        description="Overwrites the target's own UV layout with the donor's",
        default=False)
    vert_mapping: EnumProperty(
        name="Mapping",
        description="How the new mesh's vertices find the old mesh's",
        items=[
            ('POLYINTERP_NEAREST', "Nearest face (smooth)",
             "Blends across the nearest face. Best default"),
            ('NEAREST', "Nearest vertex",
             "Straight nearest-vertex copy. Try this if the smooth one smears"),
            ('POLY_NEAREST', "Nearest face (flat)",
             "Nearest face, no blending"),
        ],
        default='POLYINTERP_NEAREST')


# --------------------------------------------------------------------------
# the expensive pass
# --------------------------------------------------------------------------

def analyze(obj):
    """Count bone influences per vertex. O(vertices), so it lives behind a button."""
    mesh = obj.data
    max_inf = 0
    unweighted = 0
    over = 0
    used = set()

    for v in mesh.vertices:
        live = [g for g in v.groups if g.weight > WEIGHT_EPS]
        n = len(live)
        if n > max_inf:
            max_inf = n
        if n == 0:
            unweighted += 1
        if n > MAX_INFLUENCES:
            over += 1
        for g in live:
            used.add(g.group)

    return {"max_influences": max_inf, "unweighted": unweighted,
            "bones_used": len(used), "over_limit": over}


class GRB_OT_analyze(Operator):
    bl_idname = "grb.analyze"
    bl_label = "Check Weights"
    bl_description = ("Count bone influences per vertex and find vertices with "
                      "no weight at all")
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        res = analyze(obj)
        a = context.scene.grb_analysis
        a.valid = True
        a.analyzed_object = obj.name
        a.max_influences = res["max_influences"]
        a.unweighted = res["unweighted"]
        a.bones_used = res["bones_used"]
        a.over_limit = res["over_limit"]

        if res["unweighted"]:
            self.report({'WARNING'},
                        "%d vertices have no weight - they will not deform"
                        % res["unweighted"])
        else:
            self.report({'INFO'}, "Every vertex is weighted")
        return {'FINISHED'}


class GRB_OT_select_unweighted(Operator):
    """Jump into Edit Mode with the problem vertices already selected."""
    bl_idname = "grb.select_unweighted"
    bl_label = "Select Unweighted"
    bl_description = ("Enter Edit Mode with every vertex that has no bone "
                      "weight selected, so you can see where the gaps are")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None and obj.type == 'MESH'
                and len(obj.vertex_groups) > 0)

    def execute(self, context):
        obj = context.active_object

        bad = set()
        for v in obj.data.vertices:
            if not any(g.weight > WEIGHT_EPS for g in v.groups):
                bad.add(v.index)

        if not bad:
            self.report({'INFO'}, "Nothing to select - every vertex is weighted")
            return {'CANCELLED'}

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')
        context.tool_settings.mesh_select_mode = (True, False, False)

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        for v in bm.verts:
            v.select = v.index in bad
        bm.select_flush(False)
        bmesh.update_edit_mesh(obj.data)

        self.report({'WARNING'}, "Selected %d unweighted vertices" % len(bad))
        return {'FINISHED'}


# --------------------------------------------------------------------------
# the north-star operation
# --------------------------------------------------------------------------

class GRB_OT_transfer_weights(Operator):
    """Copy weight painting from the active object onto the other selected one."""
    bl_idname = "grb.transfer_weights"
    bl_label = "Transfer Weights to Selected"
    bl_description = ("Copy the ACTIVE mesh's weight painting onto the other "
                      "selected mesh. Select your new mesh first, then "
                      "shift-select the vanilla garment last so it is active")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        act = context.active_object
        return (len(sel) == 2 and act is not None and act.type == 'MESH'
                and len(act.vertex_groups) > 0)

    def execute(self, context):
        settings = context.scene.grb_settings
        src = context.active_object
        dst = next(o for o in context.selected_objects
                   if o.type == 'MESH' and o is not src)

        for g in list(dst.vertex_groups):
            dst.vertex_groups.remove(g)

        def transfer(data_type, loop_domain):
            kwargs = {
                "data_type": data_type,
                "use_create": True,
                "layers_select_src": 'ALL',
                "layers_select_dst": 'NAME',
                "mix_mode": 'REPLACE',
                "use_object_transform": True,
            }
            if loop_domain:
                kwargs["loop_mapping"] = 'POLYINTERP_NEAREST'
            else:
                kwargs["vert_mapping"] = settings.vert_mapping
            bpy.ops.object.data_transfer(**kwargs)

        transfer('VGROUP_WEIGHTS', False)
        done = ["weights"]

        if settings.with_colors and src.data.color_attributes:
            transfer('COLOR_CORNER', True)
            done.append("colors")
        if settings.with_uvs and src.data.uv_layers:
            transfer('UV', True)
            done.append("UVs")

        # Hook the new mesh to the same rig, or it still will not move in game.
        arm = next((m.object for m in src.modifiers
                    if m.type == 'ARMATURE' and m.object), None)
        if arm is None and src.parent and src.parent.type == 'ARMATURE':
            arm = src.parent
        if arm is not None:
            if not any(m.type == 'ARMATURE' for m in dst.modifiers):
                mod = dst.modifiers.new(name="Armature", type='ARMATURE')
                mod.object = arm
            dst.parent = arm
            dst.matrix_parent_inverse = arm.matrix_world.inverted()

        res = analyze(dst)
        a = context.scene.grb_analysis
        a.valid = True
        a.analyzed_object = dst.name
        a.max_influences = res["max_influences"]
        a.unweighted = res["unweighted"]
        a.bones_used = res["bones_used"]
        a.over_limit = res["over_limit"]

        total = len(dst.data.vertices)
        covered = total - res["unweighted"]
        pct = (100.0 * covered / total) if total else 0.0

        msg = "Copied %s: %d groups, %.1f%% of vertices weighted" % (
            " + ".join(done), len(dst.vertex_groups), pct)
        self.report({'WARNING'} if res["unweighted"] else {'INFO'}, msg)
        return {'FINISHED'}


class GRB_OT_export_glb(Operator, ExportHelper):
    """Export to GLB with the settings ATK expects."""
    bl_idname = "grb.export_glb"
    bl_label = "Export GLB for ATK"
    bl_description = ("Export the scene to GLB with tangents, vertex colors and "
                      "every UV set switched on - what ATK wants on import")

    filename_ext = ".glb"
    filter_glob: StringProperty(default="*.glb", options={'HIDDEN'})

    def execute(self, context):
        wanted = {
            "filepath": self.filepath,
            "export_format": 'GLB',
            "export_yup": True,
            "export_texcoords": True,
            "export_normals": True,
            "export_tangents": True,
            "export_colors": True,
            "export_attributes": True,
            "export_skins": True,
            "export_all_influences": True,
            "export_materials": 'EXPORT',
            "use_selection": False,
        }
        try:
            known = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
            wanted = {k: v for k, v in wanted.items() if k in known}
        except Exception:
            pass
        bpy.ops.export_scene.gltf(**wanted)
        self.report({'INFO'}, "Wrote %s" % self.filepath)
        return {'FINISHED'}


# --------------------------------------------------------------------------
# the panel
# --------------------------------------------------------------------------

class GRB_PT_main(Panel):
    bl_label = "GRB Mesh Check"
    bl_idname = "GRB_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GRB"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if obj is None or obj.type != 'MESH':
            layout.label(text="Select a mesh", icon='INFO')
            return

        mesh = obj.data
        box = layout.box()
        box.label(text=obj.name, icon='MESH_DATA')

        # Cheap facts, live on every redraw.
        col = box.column(align=True)
        col.label(text="%s verts, %s faces" % (
            f"{len(mesh.vertices):,}", f"{len(mesh.polygons):,}"))

        n_uv = len(mesh.uv_layers)
        row = col.row()
        row.alert = (n_uv == 0 or n_uv > MAX_UV_SETS)
        row.label(text="UV sets: %d" % n_uv,
                  icon='ERROR' if (n_uv == 0 or n_uv > MAX_UV_SETS) else 'CHECKMARK')

        n_col = len(mesh.color_attributes)
        row = col.row()
        row.alert = (n_col == 0)
        row.label(text="Vertex colors: %d" % n_col,
                  icon='ERROR' if n_col == 0 else 'CHECKMARK')

        n_mat = len(mesh.materials)
        row = col.row()
        row.alert = (n_mat > 1)
        row.label(text="Materials: %d" % n_mat,
                  icon='ERROR' if n_mat > 1 else 'CHECKMARK')

        col.label(text="Vertex groups: %d" % len(obj.vertex_groups))

        # Expensive facts, behind a button.
        layout.separator()
        layout.operator("grb.analyze", icon='VIEWZOOM')

        a = context.scene.grb_analysis
        if a.valid and a.analyzed_object == obj.name:
            box = layout.box()
            box.label(text="Weight check", icon='GROUP_VERTEX')
            col = box.column(align=True)
            col.label(text="Bones actually used: %d" % a.bones_used)

            row = col.row()
            row.alert = a.max_influences > MAX_INFLUENCES
            row.label(text="Max influences/vertex: %d" % a.max_influences)
            if a.max_influences > MAX_INFLUENCES:
                col.label(text="glTF carries %d - %d verts over"
                               % (MAX_INFLUENCES, a.over_limit), icon='ERROR')

            row = col.row()
            row.alert = a.unweighted > 0
            row.label(text="Unweighted: %d" % a.unweighted,
                      icon='ERROR' if a.unweighted else 'CHECKMARK')
            if a.unweighted:
                box.operator("grb.select_unweighted", icon='RESTRICT_SELECT_OFF')
        elif a.valid:
            layout.label(text="(results are for %s)" % a.analyzed_object,
                         icon='INFO')


class GRB_PT_transfer(Panel):
    bl_label = "Weight Transfer"
    bl_idname = "GRB_PT_transfer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GRB"
    bl_parent_id = "GRB_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        s = context.scene.grb_settings

        box = layout.box()
        box.scale_y = 0.7
        box.label(text="1. Click your NEW mesh", icon='DOT')
        box.label(text="2. Shift-click the vanilla one", icon='DOT')
        box.label(text="   (it goes last = active)", icon='BLANK1')

        layout.prop(s, "vert_mapping", text="")
        layout.prop(s, "with_colors")
        layout.prop(s, "with_uvs")

        layout.separator()
        row = layout.row()
        row.scale_y = 1.4
        row.operator("grb.transfer_weights", icon='MOD_VERTEX_WEIGHT')

        if not GRB_OT_transfer_weights.poll(context):
            layout.label(text="Need exactly 2 meshes selected,", icon='INFO')
            layout.label(text="active one carrying the weights.", icon='BLANK1')


class GRB_PT_export(Panel):
    bl_label = "Export"
    bl_idname = "GRB_PT_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GRB"
    bl_parent_id = "GRB_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.operator("grb.export_glb", icon='EXPORT')
        box = layout.box()
        box.scale_y = 0.7
        box.label(text="Tangents, colors and every", icon='INFO')
        box.label(text="UV set switched on.", icon='BLANK1')


# --------------------------------------------------------------------------

CLASSES = (
    GRBAnalysis, GRBSettings,
    GRB_OT_analyze, GRB_OT_select_unweighted, GRB_OT_transfer_weights,
    GRB_OT_export_glb,
    GRB_PT_main, GRB_PT_transfer, GRB_PT_export,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.grb_analysis = PointerProperty(type=GRBAnalysis)
    bpy.types.Scene.grb_settings = PointerProperty(type=GRBSettings)


def unregister():
    del bpy.types.Scene.grb_settings
    del bpy.types.Scene.grb_analysis
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
