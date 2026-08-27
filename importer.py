# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""Import .3ds files produced by this extension (TMF round-trip)."""

import math

import bpy
from mathutils import Matrix, Quaternion, Vector

from .format_3ds import parse_3ds_file
from .tmf_scene import create_maxbox_guide, create_tmf_name_collections, prepare_tmf_workspace


def _base_name(name):
    if "." in name and name.rsplit(".", 1)[1].isdigit():
        return name.rsplit(".", 1)[0]
    return name


def _is_maxbox(name):
    return _base_name(name).casefold() == "maxbox"


def _is_projshad_name(name):
    return _base_name(name).casefold() == "projshad"


def _mesh_aabb_size_from_verts(verts):
    if not verts:
        return None
    xs = [v[0] if not hasattr(v, "x") else v.x for v in verts]
    ys = [v[1] if not hasattr(v, "y") else v.y for v in verts]
    zs = [v[2] if not hasattr(v, "z") else v.z for v in verts]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def _mesh_aabb_size(mesh):
    return _mesh_aabb_size_from_verts(mesh.vertices)


def _is_near_identity_rotation(q_blender, tolerance=0.02):
    return abs(q_blender.angle) < tolerance or abs(q_blender.angle - 2.0 * math.pi) < tolerance


def _is_tm_export_shadow_world(verts):
    """True when world verts look like post-export TM orient (+90° X baked, hub rot ≈ 0)."""
    size = _mesh_aabb_size_from_verts(verts)
    if size is None:
        return False
    sx, sy, sz = size
    thin_y = sy <= sx * 0.15 and sy <= sz * 0.15
    not_flat_z = not (sz <= sx * 0.15 and sz <= sy * 0.15)
    return thin_y and not_flat_z


def restore_projshad_blender_orientation(mesh):
    """
    Undo export +90° X (TM Y-up shadow plane) back to a Blender Z-up ground plane.

    Pivot stays at the mesh origin — only local vertex positions change.
    """
    size = _mesh_aabb_size(mesh)
    if size is None:
        return False
    sx, sy, sz = size
    if sz <= sx * 0.15 and sz <= sy * 0.15:
        return False
    if sy <= sx * 0.15 and sy <= sz * 0.15:
        mesh.transform(Matrix.Rotation(math.radians(-90.0), 4, "X"))
        mesh.update()
        return True
    return False


def _projshad_import_verts(obj_data, kf_node):
    """
    ProjShad: flat Z-up local mesh, hub location, rotation always cleared to 0.

    Export stores world-baked verts plus hub rotation when the plane was authored
    with +90° X. Un-baking recovers local geometry; clearing rotation avoids a
    vertical plane in the viewport. When hub rot ≈ 0, also undo export +90° X.
    """
    loc, _rot_euler, q_blender = _hub_transform(obj_data, kf_node)
    local_verts = _unbake_verts(obj_data.verts, loc, q_blender)
    restored = False

    if _is_near_identity_rotation(q_blender):
        world_verts = obj_data.verts
        if _is_tm_export_shadow_world(local_verts) or _is_tm_export_shadow_world(world_verts):
            rot = Matrix.Rotation(math.radians(-90.0), 4, "X")
            local_verts = [tuple(rot @ Vector(v)) for v in local_verts]
            restored = True
    elif _is_tm_export_shadow_world(local_verts):
        # Hub had rotation but local coords are still TM wall layout — flatten.
        rot = Matrix.Rotation(math.radians(-90.0), 4, "X")
        local_verts = [tuple(rot @ Vector(v)) for v in local_verts]
        restored = True

    return local_verts, loc, restored


def _ensure_material(name, mapfile=None, search_dir=None):
    mat_name = name or (mapfile.rsplit(".", 1)[0] if mapfile else "Material")
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    if mapfile and search_dir:
        # Optional: load DDS/PNG next to the .3ds if present.
        from pathlib import Path

        candidate = Path(search_dir) / mapfile
        if candidate.is_file():
            try:
                img = bpy.data.images.load(str(candidate), check_existing=True)
            except RuntimeError:
                img = None
            if img is not None:
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links
                bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
                if bsdf is not None:
                    tex = nodes.new("ShaderNodeTexImage")
                    tex.image = img
                    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def _kf_by_name(parsed):
    mapping = {}
    for node in parsed.kf_nodes:
        if node.name:
            mapping[node.name] = node
    return mapping


def _materials_by_name(parsed):
    mapping = {}
    for mat in parsed.materials:
        if mat.name:
            mapping[mat.name] = mat
    return mapping


def _hub_transform(obj_data, kf_node):
    """
    Hub location + Blender rotation from KF / mesh matrix.

    Our exporter stores:
      - world-baked verts
      - POS_TRACK / matrix translation = Blender location
      - ROT_TRACK = inverted Blender quaternion as axis-angle
    """
    loc = Vector(obj_data.matrix_translation)
    if kf_node and kf_node.pos is not None:
        loc = Vector(kf_node.pos)

    rot_euler = (0.0, 0.0, 0.0)
    q_blender = Quaternion()
    q_blender.identity()

    if kf_node and kf_node.rot is not None:
        angle, ax, ay, az = kf_node.rot
        axis = Vector((ax, ay, az))
        if axis.length_squared > 1e-12 and abs(angle) > 1e-12:
            q_stored = Quaternion(axis.normalized(), angle)
            q_blender = q_stored.inverted()
            rot_euler = tuple(q_blender.to_euler())
    elif obj_data.matrix_rotation is not None:
        rows = obj_data.matrix_rotation
        mat3 = Matrix((
            (rows[0][0], rows[0][1], rows[0][2]),
            (rows[1][0], rows[1][1], rows[1][2]),
            (rows[2][0], rows[2][1], rows[2][2]),
        ))
        # Exporter wrote inverted rotation into the matrix; invert back.
        try:
            q_blender = mat3.to_quaternion().inverted()
            rot_euler = tuple(q_blender.to_euler())
        except ValueError:
            pass

    return loc, rot_euler, q_blender


def _unbake_verts(verts, loc, q_blender):
    """Undo world bake: local = inv(T * R) * world_vert."""
    mat = Matrix.Translation(loc) @ q_blender.to_matrix().to_4x4()
    try:
        inv = mat.inverted()
    except ValueError:
        inv = Matrix.Identity(4)
        inv.translation = -loc
    return [tuple(inv @ Vector(v)) for v in verts]


def do_import(
    context,
    filepath,
    link_collection=None,
    prepare_workspace=False,
    create_maxbox=False,
    create_name_collections=False,
):
    """
    Import a TMF .3ds into the current scene.

    prepare_workspace: metric units + view clips (no helpers).
    create_maxbox: wire MaxBox guide when none exists in the scene.
    create_name_collections: empty Outliner name-guide collections.

    Returns dict with keys: objects, skipped, materials, projshad_restored, maxbox, collections.
    """
    if prepare_workspace:
        prepare_tmf_workspace(context)

    parsed = parse_3ds_file(filepath)
    from pathlib import Path

    search_dir = str(Path(filepath).parent)
    kf_map = _kf_by_name(parsed)
    mat_lib = _materials_by_name(parsed)
    coll = link_collection or context.collection or context.scene.collection

    created = []
    skipped = []
    projshad_restored = False

    for obj_data in parsed.objects:
        name = obj_data.name or "Object"
        if _is_maxbox(name):
            skipped.append(f"{name} (MaxBox guide ignored)")
            continue
        if not obj_data.verts or not obj_data.faces:
            skipped.append(f"{name} (no mesh)")
            continue

        kf = kf_map.get(name)
        projshad_restored_this = False
        if _is_projshad_name(name):
            local_verts, loc, projshad_restored_this = _projshad_import_verts(obj_data, kf)
            rot_euler = (0.0, 0.0, 0.0)
            if projshad_restored_this:
                projshad_restored = True
        else:
            loc, rot_euler, q_blender = _hub_transform(obj_data, kf)
            local_verts = _unbake_verts(obj_data.verts, loc, q_blender)

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(local_verts, [], obj_data.faces)
        mesh.update()

        if obj_data.uvs and len(obj_data.uvs) == len(local_verts):
            uv_layer = mesh.uv_layers.new(name="UVMap")
            # Assign per-loop from vertex UVs (3DS stores one UV per vertex after split).
            for poly in mesh.polygons:
                for loop_idx in poly.loop_indices:
                    vi = mesh.loops[loop_idx].vertex_index
                    uv_layer.data[loop_idx].uv = obj_data.uvs[vi]

        # Materials from face material chunks or mapfile library.
        mat_names = list(obj_data.face_materials.keys())
        if not mat_names and name in mat_lib:
            mat_names = [name]
        for mat_name in mat_names:
            lib = mat_lib.get(mat_name)
            mapfile = lib.mapfile if lib else None
            mat = _ensure_material(mat_name, mapfile, search_dir)
            mesh.materials.append(mat)

        ob = bpy.data.objects.new(name, mesh)
        ob.location = loc
        ob.rotation_euler = rot_euler
        coll.objects.link(ob)
        created.append(ob.name)

    # KF-only nodes (light Empties exported without OBJECT mesh) — rare in 2.2.21+.
    mesh_names = {_base_name(n) for n in created}
    for node in parsed.kf_nodes:
        if not node.name or _is_maxbox(node.name):
            continue
        if _base_name(node.name) in mesh_names or node.name in mesh_names:
            continue
        # Only spawn Empty for known light helper names without mesh.
        lower = node.name.casefold()
        if not (lower.startswith("light") or "light" in lower):
            continue
        empty = bpy.data.objects.new(node.name, None)
        empty.empty_display_type = "PLAIN_AXES"
        empty.empty_display_size = 0.05
        if node.pos is not None:
            empty.location = node.pos
        if node.rot is not None:
            angle, ax, ay, az = node.rot
            axis = Vector((ax, ay, az))
            if axis.length_squared > 1e-12 and abs(angle) > 1e-12:
                q = Quaternion(axis.normalized(), angle).inverted()
                empty.rotation_euler = q.to_euler()
        coll.objects.link(empty)
        created.append(empty.name)

    maxbox_info = None
    if create_maxbox:
        maxbox_info = create_maxbox_guide(context, update_if_exists=False)

    collections_info = None
    if create_name_collections:
        collections_info = create_tmf_name_collections(context)

    return {
        "objects": created,
        "skipped": skipped,
        "materials": [m.name for m in parsed.materials if m.name],
        "projshad_restored": projshad_restored,
        "maxbox": maxbox_info,
        "collections": collections_info,
    }
