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
from .tmf_validation import ABS_Y_MM, ABS_Z_MM, TMF_NAME_GUIDE_MESHES, TMF_NAMES_ROOT_COLLECTION, validate_export

# MaxBox guide: Blender Z-up box matching the TMF car envelope (~3 wide × 6 long × 2.5 tall).
MAXBOX_SIZE = (3.0, 6.0, 2.5)


def _collection_in_parent(name, parent):
    for child in parent.children:
        if child.name == name:
            return child
    return None


def create_tmf_name_collections(context):
    """
    Empty Outliner collections for every canonical TMF mesh name.

    Skips names that already exist under the guide root. No meshes are created.
    """
    scene = context.scene
    root = bpy.data.collections.get(TMF_NAMES_ROOT_COLLECTION)
    created_root = False
    if root is None:
        root = bpy.data.collections.new(TMF_NAMES_ROOT_COLLECTION)
        scene.collection.children.link(root)
        created_root = True

    created = []
    skipped = []
    for mesh_name in TMF_NAME_GUIDE_MESHES:
        if _collection_in_parent(mesh_name, root) is not None:
            skipped.append(mesh_name)
            continue
        coll = bpy.data.collections.new(mesh_name)
        root.children.link(coll)
        created.append(mesh_name)

    return {
        "root": root.name,
        "created": created,
        "skipped": skipped,
        "created_root": created_root,
    }


def _find_maxbox(scene):
    for ob in scene.objects:
        base = ob.name.rsplit(".", 1)[0] if "." in ob.name and ob.name.rsplit(".", 1)[1].isdigit() else ob.name
        if base.casefold() == "maxbox":
            return ob
    return None


def prepare_tmf_workspace(context):
    """
    Metric units and viewport clips for TMF car scale (~1 Blender unit = 1 mm).

    Does not spawn helpers or MaxBox — safe to call from import when the user opts in.
    """
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


def create_maxbox_guide(context, update_if_exists=True):
    """
    Create or refresh the wire MaxBox scale guide (never exported).

    When update_if_exists is False and a MaxBox is already in the scene, returns
    immediately without creating or moving it (import default).
    """
    scene = context.scene
    maxbox = _find_maxbox(scene)
    created = False

    if maxbox is not None and not update_if_exists:
        return {
            "maxbox": maxbox.name,
            "created_maxbox": False,
            "skipped_existing": True,
        }

    if maxbox is None:
        mesh = bpy.data.meshes.new("MaxBox")
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
    maxbox.scale = MAXBOX_SIZE
    maxbox.display_type = "WIRE"
    maxbox.hide_render = True
    maxbox.show_in_front = True

    return {
        "maxbox": maxbox.name,
        "created_maxbox": created,
        "skipped_existing": False,
        "y_limits": ABS_Y_MM,
        "z_limits": ABS_Z_MM,
    }


def prepare_tmf_scene(context, create_maxbox=True, create_name_collections=False):
    """Metric units, tight view clips, optional MaxBox and name-guide collections."""
    prepare_tmf_workspace(context)
    info = {"collections": None}
    if create_maxbox:
        info = create_maxbox_guide(context, update_if_exists=True)
    if create_name_collections:
        info["collections"] = create_tmf_name_collections(context)
    return info


class TMF_OT_prepare_scene(bpy.types.Operator):
    """Set metric units, view clips, and create MaxBox guide for TMF car scale"""

    bl_idname = "tmf.prepare_scene"
    bl_label = "Prepare TMF Scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = getattr(context.scene, "tmf_settings", None)
        create_maxbox = True
        create_name_collections = True
        if settings is not None:
            create_maxbox = settings.prepare_create_maxbox
            create_name_collections = settings.prepare_create_collections

        info = prepare_tmf_scene(
            context,
            create_maxbox=create_maxbox,
            create_name_collections=create_name_collections,
        )
        parts = ["TMF units and view clips applied"]
        if create_maxbox:
            if info.get("created_maxbox"):
                parts.append(f"created {info['maxbox']}")
            else:
                parts.append(f"updated {info.get('maxbox', 'MaxBox')}")
        coll_info = info.get("collections")
        if coll_info:
            n_new = len(coll_info["created"])
            if n_new:
                parts.append(f"{n_new} name collections added")
            else:
                parts.append("name collections already present")
        self.report({"INFO"}, "; ".join(parts))
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

            lines = []
            for error in validation.errors:
                lines.append(f"[ERR] {error}")
            for warn in validation.warnings:
                lines.append(f"[WARN] {warn}")
            if not lines:
                lines.append("OK — MaxBox clear; no advisories")

            if settings is not None:
                settings.last_validation = "\n".join(lines)

            for error in validation.errors[:8]:
                self.report({"ERROR"}, error)
            for warn in validation.warnings[:8]:
                self.report({"WARNING"}, warn)
            if len(validation.warnings) > 8:
                self.report(
                    {"WARNING"},
                    f"...and {len(validation.warnings) - 8} more warnings (see N-panel)",
                )

            n = len(mesh_objects) + len(empty_objects)
            if validation.ok:
                self.report(
                    {"INFO"},
                    f"MaxBox OK ({n} objects, {len(validation.warnings)} warning(s))",
                )
                return {"FINISHED"}

            if len(validation.errors) > 8:
                self.report(
                    {"ERROR"},
                    f"...and {len(validation.errors) - 8} more MaxBox errors (see N-panel)",
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
