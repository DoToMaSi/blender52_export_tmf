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
from .game_profiles import GAME_TARGET_ITEMS, get_profile, profile_from_context
from .tmf_validation import validate_export


def _collection_in_parent(name, parent):
    for child in parent.children:
        if child.name == name:
            return child
    return None


def create_tmf_name_collections(context, profile=None):
    """
    Empty Outliner collections for every canonical mesh name for the game profile.
    """
    if profile is None:
        profile = profile_from_context(context)
    scene = context.scene
    root_name = profile.names_root_collection
    root = bpy.data.collections.get(root_name)
    created_root = False
    if root is None:
        root = bpy.data.collections.new(root_name)
        scene.collection.children.link(root)
        created_root = True

    created = []
    skipped = []
    for mesh_name in profile.name_guide_meshes:
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
    Metric units and viewport clips for car scale (~1 Blender unit = 1 mm).
    """
    scene = context.scene
    units = scene.unit_settings
    units.system = "METRIC"
    units.scale_length = 1.0
    units.length_unit = "METERS"
    units.use_separate = False

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


def create_maxbox_guide(context, update_if_exists=True, profile=None):
    """
    Create or refresh the wire MaxBox scale guide (never exported).
    """
    if profile is None:
        profile = profile_from_context(context)
    scene = context.scene
    maxbox = _find_maxbox(scene)
    created = False
    size = profile.maxbox_size

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

    # Sit the box so Z min matches profile abs_z low.
    z_min = profile.abs_z[0]
    maxbox.location = (0.0, 0.0, size[2] * 0.5 + z_min)
    maxbox.scale = size
    maxbox.display_type = "WIRE"
    maxbox.hide_render = True
    maxbox.show_in_front = True

    return {
        "maxbox": maxbox.name,
        "created_maxbox": created,
        "skipped_existing": False,
        "x_limits": profile.abs_x,
        "y_limits": profile.abs_y,
        "z_limits": profile.abs_z,
    }


def prepare_tmf_scene(
    context,
    create_maxbox=True,
    create_name_collections=False,
    profile=None,
):
    """Metric units, tight view clips, optional MaxBox and name-guide collections."""
    if profile is None:
        profile = profile_from_context(context)
    prepare_tmf_workspace(context)
    info = {"collections": None}
    if create_maxbox:
        info = create_maxbox_guide(context, update_if_exists=True, profile=profile)
    if create_name_collections:
        info["collections"] = create_tmf_name_collections(context, profile=profile)
    return info


class TMF_OT_prepare_scene(bpy.types.Operator):
    """Set metric units, view clips, and create MaxBox guide for the game target"""

    bl_idname = "tmf.prepare_scene"
    bl_label = "Prepare Scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = getattr(context.scene, "tmf_settings", None)
        create_maxbox = True
        create_name_collections = True
        profile = profile_from_context(context)
        if settings is not None:
            create_maxbox = settings.prepare_create_maxbox
            create_name_collections = settings.prepare_create_collections
            profile = get_profile(settings.game_target)

        info = prepare_tmf_scene(
            context,
            create_maxbox=create_maxbox,
            create_name_collections=create_name_collections,
            profile=profile,
        )
        parts = [f"{profile.label}: units and view clips applied"]
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


def _validate_poly_items(self, context):
    return get_profile(getattr(self, "game_target", "TMF")).poly_target_items


class TMF_OT_validate_scene(bpy.types.Operator):
    """Validate allowlisted car meshes without writing a .3ds file"""

    bl_idname = "tmf.validate_scene"
    bl_label = "Validate Scene"
    bl_options = {"REGISTER"}

    game_target: bpy.props.EnumProperty(
        name="Game Target",
        items=GAME_TARGET_ITEMS,
        default="TMF",
    )
    poly_target: bpy.props.EnumProperty(
        name="Poly Target",
        items=_validate_poly_items,
    )
    use_selection: bpy.props.BoolProperty(
        name="Selection Only",
        default=False,
    )

    def execute(self, context):
        mesh_objects = []
        empty_objects = []
        profile = get_profile(self.game_target)
        try:
            mesh_objects, empty_objects, _mats, _tex = collect_mesh_data(
                context,
                self.use_selection,
                verbose=False,
                game_target=self.game_target,
                profile=profile,
            )
            if not mesh_objects and not empty_objects:
                self.report({"ERROR"}, "No allowlisted meshes found for this game target")
                return {"CANCELLED"}

            validation = validate_export(
                context, mesh_objects, self.poly_target, profile=profile
            )
            settings = getattr(context.scene, "tmf_settings", None)

            lines = []
            for error in validation.format_errors:
                lines.append(f"[FORMAT] {error}")
            for error in validation.errors:
                lines.append(f"[ERR] {error}")
            for warn in validation.warnings:
                lines.append(f"[WARN] {warn}")
            if not lines:
                lines.append("OK — format + Strict clear; no advisories")

            if settings is not None:
                settings.last_validation = "\n".join(lines)

            for error in validation.format_errors[:8]:
                self.report({"ERROR"}, error)
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
            if validation.format_ok and validation.ok:
                self.report(
                    {"INFO"},
                    f"OK ({n} objects, {len(validation.warnings)} warning(s))",
                )
                return {"FINISHED"}

            extra = (
                len(validation.format_errors)
                + len(validation.errors)
                - 8
            )
            if extra > 0:
                self.report(
                    {"ERROR"},
                    f"...and {extra} more errors (see N-panel)",
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
