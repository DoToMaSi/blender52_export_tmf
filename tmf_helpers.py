# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

import math

import bpy
from mathutils import Vector

def _ensure_unique_object(name):
    """Return False if an object with this base name already exists."""
    for ob in bpy.data.objects:
        base = ob.name.rsplit(".", 1)[0] if "." in ob.name and ob.name.rsplit(".", 1)[1].isdigit() else ob.name
        if base.casefold() == name.casefold():
            return False
    return True


def _link_object(context, ob):
    coll = context.collection or context.scene.collection
    coll.objects.link(ob)
    return ob


def _make_material(name, mapfile=None):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat


def _plane_mesh(name, size_x, size_y):
    """XY plane centered at origin, facing +Z (Blender ground)."""
    mesh = bpy.data.meshes.new(name)
    hx, hy = size_x * 0.5, size_y * 0.5
    verts = [
        Vector((-hx, -hy, 0.0)),
        Vector((hx, -hy, 0.0)),
        Vector((hx, hy, 0.0)),
        Vector((-hx, hy, 0.0)),
    ]
    faces = [(0, 1, 2, 3)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    # Simple UV covering 0..1
    mesh.uv_layers.new(name="UVMap")
    uv = mesh.uv_layers.active.data
    # 4 loops for one face
    uv[0].uv = (0.0, 0.0)
    uv[1].uv = (1.0, 0.0)
    uv[2].uv = (1.0, 1.0)
    uv[3].uv = (0.0, 1.0)
    return mesh


def _box_mesh(name, size):
    mesh = bpy.data.meshes.new(name)
    hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    verts = [
        Vector((-hx, -hy, -hz)),
        Vector((hx, -hy, -hz)),
        Vector((hx, hy, -hz)),
        Vector((-hx, hy, -hz)),
        Vector((-hx, -hy, hz)),
        Vector((hx, -hy, hz)),
        Vector((hx, hy, hz)),
        Vector((-hx, hy, hz)),
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
    mesh.uv_layers.new(name="UVMap")
    return mesh


def create_projshad(context, size=(2.6, 5.6), replace=False):
    name = "ProjShad"
    if not replace and not _ensure_unique_object(name):
        return None, f"{name} already exists"
    if replace:
        for ob in list(bpy.data.objects):
            base = ob.name.rsplit(".", 1)[0] if "." in ob.name and ob.name.rsplit(".", 1)[1].isdigit() else ob.name
            if base.casefold() == name.casefold():
                bpy.data.objects.remove(ob, do_unlink=True)

    mesh = _plane_mesh(name, size[0], size[1])
    ob = bpy.data.objects.new(name, mesh)
    ob.location = (0.0, 0.0, 0.0114)
    mat = _make_material("ProjShad", "ProjShad.dds")
    if mesh.materials:
        mesh.materials[0] = mat
    else:
        mesh.materials.append(mat)
    _link_object(context, ob)
    return ob, None


def create_lightfproj(context, location=(0.0, -2.2707, 0.5505), size=0.5, replace=False):
    name = "LightFProj"
    if not replace and not _ensure_unique_object(name):
        return None, f"{name} already exists"
    if replace:
        for ob in list(bpy.data.objects):
            base = ob.name.rsplit(".", 1)[0] if "." in ob.name and ob.name.rsplit(".", 1)[1].isdigit() else ob.name
            if base.casefold() == name.casefold():
                bpy.data.objects.remove(ob, do_unlink=True)

    mesh = _box_mesh(name, (size, size, size))
    ob = bpy.data.objects.new(name, mesh)
    ob.location = location
    mat = _make_material("LightFProj", "LightFProj.dds")
    mesh.materials.append(mat)
    _link_object(context, ob)
    return ob, None


# Defaults from successful Burnout Factory GT export log (2.2.21).
_LIGHT_DEFAULTS = (
    ("LightFL1", (0.6752, -2.1395, 0.6279), (0.0, 0.0, 0.0)),
    ("LightFR1", (-0.6213, -2.1395, 0.6279), (0.0, 0.0, 0.0)),
    ("LightRL", (0.5333, 2.3143, 0.7461), (0.0, 0.0, math.pi)),
    ("LightRR", (-0.5533, 2.3143, 0.7461), (0.0, 0.0, math.pi)),
)


def create_light_helper(context, name, location, rotation_euler, size=0.02, replace=False):
    if not replace and not _ensure_unique_object(name):
        return None, f"{name} already exists"
    if replace:
        for ob in list(bpy.data.objects):
            base = ob.name.rsplit(".", 1)[0] if "." in ob.name and ob.name.rsplit(".", 1)[1].isdigit() else ob.name
            if base.casefold() == name.casefold():
                bpy.data.objects.remove(ob, do_unlink=True)

    # Tiny XZ card (thin on Y) so export has non-zero area like the working log.
    mesh = bpy.data.meshes.new(name)
    h = size * 0.5
    verts = [
        Vector((-h, 0.0, -h)),
        Vector((h, 0.0, -h)),
        Vector((h, 0.0, h)),
        Vector((-h, 0.0, h)),
    ]
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    mesh.uv_layers.new(name="UVMap")
    ob = bpy.data.objects.new(name, mesh)
    ob.location = location
    ob.rotation_euler = rotation_euler
    _link_object(context, ob)
    return ob, None


def create_all_light_helpers(context, replace=False):
    created = []
    skipped = []
    for name, loc, rot in _LIGHT_DEFAULTS:
        ob, err = create_light_helper(context, name, loc, rot, replace=replace)
        if ob:
            created.append(ob.name)
        else:
            skipped.append(err or name)
    return created, skipped


def create_all_helpers(context, replace=False):
    messages = []
    ob, err = create_projshad(context, replace=replace)
    messages.append(f"ProjShad: {'created' if ob else err}")
    ob, err = create_lightfproj(context, replace=replace)
    messages.append(f"LightFProj: {'created' if ob else err}")
    created, skipped = create_all_light_helpers(context, replace=replace)
    if created:
        messages.append(f"Lights created: {', '.join(created)}")
    if skipped:
        messages.append(f"Lights skipped: {', '.join(skipped)}")
    return messages


class TMF_OT_add_projshad(bpy.types.Operator):
    """Create a flat ProjShad ground plane (export applies TM Y-up orient)"""

    bl_idname = "tmf.add_projshad"
    bl_label = "Add ProjShad"
    bl_options = {"REGISTER", "UNDO"}

    replace: bpy.props.BoolProperty(name="Replace Existing", default=False)

    def execute(self, context):
        ob, err = create_projshad(context, replace=self.replace)
        if err:
            self.report({"WARNING"}, err)
            return {"CANCELLED"}
        self.report({"INFO"}, f"Created {ob.name}")
        return {"FINISHED"}


class TMF_OT_add_lightfproj(bpy.types.Operator):
    """Create LightFProj projector mesh at the front of the car"""

    bl_idname = "tmf.add_lightfproj"
    bl_label = "Add LightFProj"
    bl_options = {"REGISTER", "UNDO"}

    replace: bpy.props.BoolProperty(name="Replace Existing", default=False)

    def execute(self, context):
        ob, err = create_lightfproj(context, replace=self.replace)
        if err:
            self.report({"WARNING"}, err)
            return {"CANCELLED"}
        self.report({"INFO"}, f"Created {ob.name}")
        return {"FINISHED"}


class TMF_OT_add_light_helpers(bpy.types.Operator):
    """Create LightFL1/FR1/RL/RR tiny meshes (flare origins)"""

    bl_idname = "tmf.add_light_helpers"
    bl_label = "Add Light Helpers"
    bl_options = {"REGISTER", "UNDO"}

    replace: bpy.props.BoolProperty(name="Replace Existing", default=False)

    def execute(self, context):
        created, skipped = create_all_light_helpers(context, replace=self.replace)
        if created:
            self.report({"INFO"}, f"Created: {', '.join(created)}")
        if skipped and not created:
            self.report({"WARNING"}, f"Skipped: {', '.join(skipped)}")
            return {"CANCELLED"}
        if skipped:
            self.report({"WARNING"}, f"Skipped: {', '.join(skipped)}")
        return {"FINISHED"}


class TMF_OT_add_all_helpers(bpy.types.Operator):
    """Create ProjShad, LightFProj, and LightFL1/FR1/RL/RR"""

    bl_idname = "tmf.add_all_helpers"
    bl_label = "Add All TMF Helpers"
    bl_options = {"REGISTER", "UNDO"}

    replace: bpy.props.BoolProperty(name="Replace Existing", default=False)

    def execute(self, context):
        for line in create_all_helpers(context, replace=self.replace):
            self.report({"INFO"}, line)
        return {"FINISHED"}


classes = (
    TMF_OT_add_projshad,
    TMF_OT_add_lightfproj,
    TMF_OT_add_light_helpers,
    TMF_OT_add_all_helpers,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
