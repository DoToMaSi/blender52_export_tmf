# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
from mathutils import Vector

from .exporter import cleanup_mesh_objects, collect_mesh_data
from .tmf_validation import ABS_Y_MM, ABS_Z_MM, validate_export

# MaxBox guide: Blender Z-up box matching the TMF car envelope (~3 wide × 6 long × 2.5 tall).
MAXBOX_SIZE = (3.0, 6.0, 2.5)


def _find_maxbox(scene):
    for ob in scene.objects:
        base = ob.name.rsplit(".", 1)[0] if "." in ob.name and ob.name.rsplit(".", 1)[1].isdigit() else ob.name
        if base.casefold() == "maxbox":
            return ob
    return None


def prepare_tmf_scene(context):
    """Metric units, tight view clips, and MaxBox scale guide."""
    scene = context.scene
    units = scene.unit_settings
    units.system = "METRIC"
    units.scale_length = 1.0
    units.length_unit = "METERS"
    units.use_separate = False

    # Tiny TMF cars (~6 units): avoid vanishing under default clip_start.
    for area in context.screen.areas if context.screen else []:
        if area.type != "VIEW_3D":
            continue
        for space in area.spaces:
            if space.type != "VIEW_3D":
                continue
            space.clip_start = 0.001
            space.clip_end = 100.0
            if hasattr(space, "overlay") and hasattr(space.overlay, "grid_scale"):
                space.overlay.grid_scale = 1.0

    created = False
    maxbox = _find_maxbox(scene)
    if maxbox is None:
        mesh = bpy.data.meshes.new("MaxBox")
        # Unit cube centered, then scale to MaxBox size.
        verts = [
            Vector((x, y, z))
            for z in (-0.5, 0.5)
            for y in (-0.5, 0.5)
            for x in (-0.5, 0.5)
        ]
        # Correct corner order for a box (8 verts).
        verts = [
            Vector((-0.5, -0.5, -0.5)),
            Vector((0.5, -0.5, -0.5)),
            Vector((0.5, 0.5, -0.5)),
            Vector((-0.5, 0.5, -0.5)),
            Vector((-0.5, -0.5, 0.5)),
            Vector((0.5, -0.5, 0.5)),
            Vector((0.5, 0.5, 0.5)),
            Vector((-0.5, 0.5, 0.5)),
        ]
        faces = [
            (0, 1, 2, 3),
            (4, 7, 6, 5),
            (0, 4, 5, 1),
            (1, 5, 6, 2),
            (2, 6, 7, 3),
            (3, 7, 4, 0),
        ]
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        maxbox = bpy.data.objects.new("MaxBox", mesh)
        scene.collection.objects.link(maxbox)
        created = True

    maxbox.location = (0.0, 0.0, MAXBOX_SIZE[2] * 0.5 - 0.2)
    # Sit so Z covers roughly [-0.2, 2.3] like engine height band.
    maxbox.scale = MAXBOX_SIZE
    maxbox.display_type = "WIRE"
    maxbox.hide_render = True
    maxbox.show_in_front = True

    return {
        "maxbox": maxbox.name,
        "created_maxbox": created,
        "y_limits": ABS_Y_MM,
        "z_limits": ABS_Z_MM,
    }


class TMF_OT_prepare_scene(bpy.types.Operator):
    """Set metric units, view clips, and create MaxBox guide for TMF car scale"""

    bl_idname = "tmf.prepare_scene"
    bl_label = "Prepare TMF Scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        info = prepare_tmf_scene(context)
        if info["created_maxbox"]:
            self.report({"INFO"}, f"Created {info['maxbox']} guide + TMF units/clips")
        else:
            self.report({"INFO"}, f"Updated TMF units/clips; {info['maxbox']} already present")
        return {"FINISHED"}


class TMF_OT_validate_scene(bpy.types.Operator):
    """Validate allowlisted TMF car meshes without writing a .3ds file"""

    bl_idname = "tmf.validate_scene"
    bl_label = "Validate TMF Scene"
    bl_options = {"REGISTER"}

    poly_target: bpy.props.EnumProperty(
        name="Poly Target",
        items=(
            ("HIGH", "High Poly", "Up to 100,000 vertices"),
            ("LOW", "Low Poly", "Up to 3,600 vertices"),
        ),
        default="HIGH",
    )
    use_selection: bpy.props.BoolProperty(
        name="Selection Only",
        default=False,
    )

    def execute(self, context):
        mesh_objects = []
        empty_objects = []
        try:
            mesh_objects, empty_objects, _mats, _tex = collect_mesh_data(
                context,
                self.use_selection,
                verbose=False,
            )
            if not mesh_objects and not empty_objects:
                self.report({"ERROR"}, "No allowlisted TMF meshes found")
                return {"CANCELLED"}

            validation = validate_export(context, mesh_objects, self.poly_target)
            settings = getattr(context.scene, "tmf_settings", None)
            if validation.ok:
                msg = "OK — Strict checks passed"
                if settings is not None:
                    settings.last_validation = msg
                n = len(mesh_objects) + len(empty_objects)
                self.report({"INFO"}, f"TMF validation OK ({n} objects, {self.poly_target})")
                return {"FINISHED"}

            if settings is not None:
                settings.last_validation = "\n".join(validation.errors)
            for error in validation.errors[:8]:
                self.report({"ERROR"}, error)
            if len(validation.errors) > 8:
                self.report(
                    {"ERROR"},
                    f"...and {len(validation.errors) - 8} more errors (see N-panel)",
                )
            return {"CANCELLED"}
        finally:
            cleanup_mesh_objects(mesh_objects)


classes = (
    TMF_OT_prepare_scene,
    TMF_OT_validate_scene,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
