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
import mathutils

from .format_3ds import (
    KFDATA,
    KFDATA_KFCURTIME,
    KFDATA_KFHDR,
    KFDATA_KFSEG,
    KFDATA_OBJECT_NODE_TAG,
    MATERIAL,
    MATAMBIENT,
    MATDIFFUSE,
    MATMAPFILE,
    MATNAME,
    MATSHIN2,
    MATSHINESS,
    MATSPECULAR,
    MATTRANS,
    MAT_DIFFUSEMAP,
    MASTERSCALE,
    OBJECT,
    OBJECT_FACES,
    OBJECT_MATERIAL,
    OBJECT_MESH,
    OBJECT_NODE_HDR,
    OBJECT_NODE_ID,
    OBJECT_PIVOT,
    OBJECT_SMOOTH,
    OBJECT_TRANS_MATRIX,
    OBJECT_UV,
    OBJECT_VERTICES,
    OBJECTINFO,
    POS_TRACK_TAG,
    PRIMARY,
    PCT,
    RGB1,
    RGB2,
    ROT_TRACK_TAG,
    SCL_TRACK_TAG,
    VERSION,
    _3ds_array,
    _3ds_chunk,
    _3ds_face,
    _3ds_float,
    _3ds_point_3d,
    _3ds_point_4d,
    _3ds_point_uv,
    _3ds_rgb_color,
    _3ds_string,
    _3ds_uint,
    _3ds_ushort,
    reset_name_tables,
    sane_name,
    uv_key,
)
from .material_utils import (
    expected_texture_filename,
    get_material_export_data,
    get_object_texture_reference,
)
from .tmf_validation import (
    OPTIONAL_MESHES,
    REQUIRED_MESHES,
    is_export_blacklisted,
    to_tmf_mm,
)

ALLOWED_MESH_NAMES = frozenset(REQUIRED_MESHES) | frozenset(OPTIONAL_MESHES)


def forced_material_name(object_name, material=None):
    """Canonical 3DS material name for TMF projector / body maps."""
    if object_name == "ProjShad":
        return "ProjShad"
    if object_name.startswith("LightFProj"):
        return "LightFProj"
    if material is not None:
        return material.name
    expected = expected_texture_filename(object_name)
    if expected:
        return expected.rsplit(".", 1)[0]
    return None


def resolve_3ds_material_binding(ob, mesh, texture_filename, image=None):
    """
    Compute the exact MATERIAL / OBJECT_MATERIAL / MAPFILE strings written to .3ds,
    plus a 2.79-style name for comparison and diagnostic WARN flags.
    """
    slots = _material_slot_names(ob, mesh)
    primary_mat = None
    if mesh is not None:
        for mat in mesh.materials:
            if mat is not None:
                primary_mat = mat
                break

    force = forced_material_name(ob.name, primary_mat)
    if force:
        mat_name = force
    elif primary_mat is not None:
        mat_name = primary_mat.name
    elif texture_filename:
        mat_name = texture_filename.rsplit(".", 1)[0]
    else:
        mat_name = None

    image_name = None
    if image is not None:
        image_name = bpy.path.basename(image.filepath) or image.name

    expected = expected_texture_filename(ob.name)
    mapfile = texture_filename

    # 2.79 face-UV convention: material chunk name = mat.name + image.name
    legacy_279 = None
    if primary_mat is not None or image_name:
        legacy_279 = (primary_mat.name if primary_mat else "None")
        if image_name:
            legacy_279 += image_name

    face_names = []
    if mesh is not None:
        for mat in mesh.materials:
            if mat is None:
                continue
            face_names.append(forced_material_name(ob.name, mat) or mat.name)
    if not face_names and mat_name:
        face_names = [mat_name]

    has_uv = bool(mesh and mesh.uv_layers)

    warns = []
    if expected and not mapfile:
        warns.append(f"missing mapfile (expected {expected})")
    if expected and mapfile and mapfile.casefold() != expected.casefold():
        warns.append(f"mapfile '{mapfile}' != expected '{expected}'")
    if mat_name and face_names and mat_name not in face_names:
        warns.append(
            f"library mat '{mat_name}' not in face refs {face_names} "
            f"(TM may miss the texture bind)"
        )
    if not has_uv and ob.name in REQUIRED_MESHES:
        warns.append("no UV layer")
    if not slots and ob.name in REQUIRED_MESHES:
        warns.append("no material slots (using synthetic/fallback mat name)")
    if legacy_279 and mat_name and sane_name(legacy_279) != sane_name(mat_name):
        warns.append(
            f"differs from 2.79-style name '{sane_name(legacy_279)}' "
            f"(we write '{sane_name(mat_name)}')"
        )

    return {
        "blender_slots": slots,
        "blender_image": image_name,
        "expected_map": expected,
        "3ds_mat_name": sane_name(mat_name) if mat_name else None,
        "3ds_mapfile": sane_name(mapfile) if mapfile else None,
        "face_mat_names": [sane_name(n) for n in face_names],
        "legacy_279_name": sane_name(legacy_279) if legacy_279 else None,
        "has_uv": has_uv,
        "warns": warns,
    }


def _fmt_vec(vec, digits=4):
    return f"({vec[0]:.{digits}f}, {vec[1]:.{digits}f}, {vec[2]:.{digits}f})"


def _vlog(verbose, message, log_lines=None):
    if verbose:
        print(message)
        if log_lines is not None:
            log_lines.append(message)


def _mesh_world_bounds(ob, mesh):
    """Axis-aligned world bounds from local verts + matrix_world (export space)."""
    try:
        verts = mesh.vertices
    except (AttributeError, ReferenceError):
        return None
    if not verts:
        return None

    matrix = ob.matrix_world
    xs, ys, zs = [], [], []
    for vert in verts:
        co = matrix @ vert.co
        xs.append(to_tmf_mm(co.x))
        ys.append(to_tmf_mm(co.y))
        zs.append(to_tmf_mm(co.z))
    return {
        "min": (min(xs), min(ys), min(zs)),
        "max": (max(xs), max(ys), max(zs)),
        "size": (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)),
    }


def _material_slot_names(ob, mesh):
    names = []
    for mat in mesh.materials if mesh is not None else ():
        names.append(mat.name if mat else "<empty slot>")
    if not names and ob.type == "MESH" and ob.data is not None:
        for mat in ob.data.materials:
            names.append(mat.name if mat else "<empty slot>")
    return names


def log_export_object(ob, mesh, texture_filename, image, verbose, status="OK", log_lines=None):
    """Print one verbose line block for a collected / written object."""
    if not verbose:
        return

    dims = ob.dimensions
    loc = ob.location
    rot = ob.rotation_euler
    scale = ob.scale
    parent = ob.parent.name if ob.parent else "<none>"
    n_verts = len(mesh.vertices) if mesh is not None else 0
    n_tris = len(mesh.loop_triangles) if mesh is not None else 0
    bounds = _mesh_world_bounds(ob, mesh) if mesh is not None else None
    bind = resolve_3ds_material_binding(ob, mesh, texture_filename, image)

    def out(msg):
        _vlog(True, msg, log_lines)

    out(f"  [{status}] {ob.name}  type={ob.type}")
    out(f"         parent={parent}")
    out(f"         location={_fmt_vec(loc)}  rotation={_fmt_vec(rot)}  scale={_fmt_vec(scale)}")
    out(f"         dimensions={_fmt_vec(dims)}  verts={n_verts}  tris={n_tris}")
    if bounds is not None:
        out(
            f"         world_bounds min={_fmt_vec(bounds['min'])} "
            f"max={_fmt_vec(bounds['max'])} size={_fmt_vec(bounds['size'])}"
        )
    out(f"         blender_slots={bind['blender_slots'] or '<none>'}")
    out(f"         has_uv={bind['has_uv']}")
    out(
        f"         3ds_material_name={bind['3ds_mat_name'] or '<none>'}  "
        f"3ds_mapfile={bind['3ds_mapfile'] or '<none>'}"
    )
    out(f"         faces_reference_materials={bind['face_mat_names'] or '<none>'}")
    out(
        f"         expected_map={bind['expected_map'] or '<none>'}  "
        f"blender_image={bind['blender_image'] or '<none>'}  "
        f"legacy_279_name={bind['legacy_279_name'] or '<n/a>'}"
    )
    out(f"         kf_pivot=(0.0, 0.0, 0.0)  pos_track={_fmt_vec(loc)}")
    for warn in bind["warns"]:
        out(f"         [WARN] {warn}")



class tri_wrapper:
    __slots__ = ("vertex_index", "mat", "image", "faceuvs", "offset", "group")

    def __init__(self, vindex=(0, 0, 0), mat=None, image=None, faceuvs=None, group=0):
        self.vertex_index = vindex
        self.mat = mat
        self.image = image
        self.faceuvs = faceuvs
        self.offset = [0, 0, 0]
        self.group = group


def make_material_subchunk(chunk_id, color):
    mat_sub = _3ds_chunk(chunk_id)
    col1 = _3ds_chunk(RGB1)
    col1.add_variable("color1", _3ds_rgb_color(color))
    mat_sub.add_subchunk(col1)
    col2 = _3ds_chunk(RGB2)
    col2.add_variable("color2", _3ds_rgb_color(color))
    mat_sub.add_subchunk(col2)
    return mat_sub


def make_percent_subchunk(chunk_id, percentval):
    pct_sub = _3ds_chunk(chunk_id)
    pct1 = _3ds_chunk(PCT)
    pct1.add_variable("percent", _3ds_ushort(int(round(percentval * 100, 0))))
    pct_sub.add_subchunk(pct1)
    return pct_sub


def make_material_texture_chunk(chunk_id, texture_filename):
    mat_sub = make_percent_subchunk(chunk_id, 1)
    mat_sub_file = _3ds_chunk(MATMAPFILE)
    mat_sub_file.add_variable("mapfile", _3ds_string(sane_name(texture_filename)))
    mat_sub.add_subchunk(mat_sub_file)
    return mat_sub


def make_material_chunk(material, texture_filename=None, material_name=None):
    material_chunk = _3ds_chunk(MATERIAL)
    name = _3ds_chunk(MATNAME)

    if material_name:
        name_str = material_name
    elif material:
        name_str = material.name
    elif texture_filename:
        name_str = texture_filename.rsplit(".", 1)[0]
    else:
        name_str = "None"

    name.add_variable("name", _3ds_string(sane_name(name_str)))
    material_chunk.add_subchunk(name)

    if not material:
        material_chunk.add_subchunk(make_material_subchunk(MATAMBIENT, (0, 0, 0)))
        material_chunk.add_subchunk(make_material_subchunk(MATDIFFUSE, (0.8, 0.8, 0.8)))
        material_chunk.add_subchunk(make_material_subchunk(MATSPECULAR, (1, 1, 1)))
        material_chunk.add_subchunk(make_percent_subchunk(MATSHINESS, 0.2))
        material_chunk.add_subchunk(make_percent_subchunk(MATSHIN2, 1))
        material_chunk.add_subchunk(make_percent_subchunk(MATTRANS, 0))
    else:
        data = get_material_export_data(material)
        material_chunk.add_subchunk(make_material_subchunk(MATAMBIENT, data["ambient_color"]))
        material_chunk.add_subchunk(make_material_subchunk(MATDIFFUSE, data["diffuse_color"]))
        material_chunk.add_subchunk(make_material_subchunk(MATSPECULAR, data["specular_color"]))
        material_chunk.add_subchunk(make_percent_subchunk(MATSHINESS, data["roughness"]))
        material_chunk.add_subchunk(make_percent_subchunk(MATSHIN2, data["specular_intensity"]))
        material_chunk.add_subchunk(make_percent_subchunk(MATTRANS, 1 - data["alpha"]))

    # Always attach the map when we have a filename (including synthetic mats).
    if texture_filename:
        material_chunk.add_subchunk(
            make_material_texture_chunk(MAT_DIFFUSEMAP, texture_filename)
        )

    return material_chunk


def extract_triangles(mesh):
    poly_group, _group_count = mesh.calc_smooth_groups(use_bitflags=True)
    tri_list = []
    do_uv = mesh.uv_layers

    for face in mesh.loop_triangles:
        f_v = face.vertices
        uf = mesh.uv_layers.active.data if do_uv else None

        if do_uv:
            f_uv = [uf[loop_index].uv for loop_index in face.loops]

        smooth_group = poly_group[face.polygon_index]
        new_tri = tri_wrapper((f_v[0], f_v[1], f_v[2]), face.material_index, None)
        if do_uv:
            new_tri.faceuvs = uv_key(f_uv[0]), uv_key(f_uv[1]), uv_key(f_uv[2])
        new_tri.group = smooth_group
        tri_list.append(new_tri)

    return tri_list


def remove_face_uv(verts, tri_list):
    unique_uvs = [{} for _i in range(len(verts))]

    for tri in tri_list:
        for i in range(3):
            context_uv_vert = unique_uvs[tri.vertex_index[i]]
            uvkey = tri.faceuvs[i]
            offset_index__uv_3ds = context_uv_vert.get(uvkey)
            if not offset_index__uv_3ds:
                offset_index__uv_3ds = context_uv_vert[uvkey] = (
                    len(context_uv_vert),
                    _3ds_point_uv(uvkey),
                )
            tri.offset[i] = offset_index__uv_3ds[0]

    vert_index = 0
    vert_array = _3ds_array()
    uv_array = _3ds_array()
    index_list = []
    for i, vert in enumerate(verts):
        index_list.append(vert_index)
        pt = _3ds_point_3d(vert.co)
        uvmap = [None] * len(unique_uvs[i])
        for ii, uv_3ds in unique_uvs[i].values():
            vert_array.add(pt)
            uvmap[ii] = uv_3ds

        for uv_3ds in uvmap:
            if uv_3ds is not None:
                uv_array.add(uv_3ds)

        vert_index += len(unique_uvs[i])

    for tri in tri_list:
        for i in range(3):
            tri.offset[i] += index_list[tri.vertex_index[i]]
        tri.vertex_index = tri.offset

    return vert_array, uv_array, tri_list


def count_mesh_export_vertices(mesh):
    if mesh is None:
        return 0
    try:
        tri_list = extract_triangles(mesh)
        if mesh.uv_layers:
            vert_array, _uv_array, _tri_list = remove_face_uv(mesh.vertices, tri_list)
            return len(vert_array.values)
        return len(mesh.vertices)
    except (AttributeError, ReferenceError, TypeError, RuntimeError):
        return 0


def make_faces_chunk(tri_list, mesh, material_dict, fallback_mat_name=None, force_mat_name=None):
    materials = mesh.materials
    face_chunk = _3ds_chunk(OBJECT_FACES)
    face_list = _3ds_array()

    obj_material_faces = []
    obj_material_names = []
    for m in materials:
        if m:
            mat_name = force_mat_name or m.name
            obj_material_names.append(_3ds_string(sane_name(mat_name)))
            obj_material_faces.append(_3ds_array())

    use_fallback = len(obj_material_names) == 0 and (fallback_mat_name or force_mat_name)
    if use_fallback:
        obj_material_names.append(
            _3ds_string(sane_name(force_mat_name or fallback_mat_name))
        )
        obj_material_faces.append(_3ds_array())

    n_materials = len(obj_material_names)

    for i, tri in enumerate(tri_list):
        face_list.add(_3ds_face(tri.vertex_index))
        if use_fallback:
            obj_material_faces[0].add(_3ds_ushort(i))
        elif tri.mat < n_materials:
            obj_material_faces[tri.mat].add(_3ds_ushort(i))

    face_chunk.add_variable("faces", face_list)
    for i in range(n_materials):
        obj_material_chunk = _3ds_chunk(OBJECT_MATERIAL)
        obj_material_chunk.add_variable("name", obj_material_names[i])
        obj_material_chunk.add_variable("face_list", obj_material_faces[i])
        face_chunk.add_subchunk(obj_material_chunk)

    smooth_chunk = _3ds_chunk(OBJECT_SMOOTH)
    for i, tri in enumerate(tri_list):
        smooth_chunk.add_variable(f"face_{i}", _3ds_uint(tri.group))
    face_chunk.add_subchunk(smooth_chunk)

    return face_chunk


def make_vert_chunk(vert_array):
    vert_chunk = _3ds_chunk(OBJECT_VERTICES)
    vert_chunk.add_variable("vertices", vert_array)
    return vert_chunk


def make_uv_chunk(uv_array):
    uv_chunk = _3ds_chunk(OBJECT_UV)
    uv_chunk.add_variable("uv coords", uv_array)
    return uv_chunk


def make_mesh_chunk(mesh, material_dict, ob, name_to_id, name_to_scale, name_to_pos, name_to_rot):
    tri_list = extract_triangles(mesh)

    if mesh.uv_layers:
        vert_array, uv_array, tri_list = remove_face_uv(mesh.vertices, tri_list)
    else:
        vert_array = _3ds_array()
        for vert in mesh.vertices:
            vert_array.add(_3ds_point_3d(vert.co))
        uv_array = None

    mesh_chunk = _3ds_chunk(OBJECT_MESH)
    mesh_chunk.add_subchunk(make_vert_chunk(vert_array))
    fallback_mat = expected_texture_filename(ob.name)
    if fallback_mat:
        fallback_mat = fallback_mat.rsplit(".", 1)[0]
    force_mat = forced_material_name(ob.name)
    mesh_chunk.add_subchunk(
        make_faces_chunk(
            tri_list,
            mesh,
            material_dict,
            fallback_mat,
            force_mat_name=force_mat,
        )
    )

    mesh1 = _3ds_chunk(OBJECT_TRANS_MATRIX)

    if (ob.parent is None) or (ob.parent.name not in name_to_id):
        matrix_pos = (
            name_to_pos[ob.name][0],
            name_to_pos[ob.name][1],
            name_to_pos[ob.name][2],
        )
    else:
        matrix_pos = mathutils.Vector(
            (
                name_to_pos[ob.parent.name][0] - name_to_pos[ob.name][0],
                name_to_pos[ob.parent.name][1] - name_to_pos[ob.name][1],
                name_to_pos[ob.parent.name][2] - name_to_pos[ob.name][2],
            )
        ) * name_to_rot[ob.parent.name].to_matrix()

    ob_matrix = mathutils.Matrix()
    ob_matrix.identity()
    ob_matrix.resize_4x4()
    ob_matrix[3][0] = matrix_pos[0]
    ob_matrix[3][1] = matrix_pos[1]
    ob_matrix[3][2] = matrix_pos[2]

    one_minus_cos = 1.0 - math.cos(name_to_rot[ob.name].angle)
    sin_angle = math.sin(name_to_rot[ob.name].angle)
    cos_angle = math.cos(name_to_rot[ob.name].angle)
    axis = name_to_rot[ob.name].axis

    ob_matrix[0][0] = cos_angle + one_minus_cos * axis[0] * axis[0]
    ob_matrix[0][1] = one_minus_cos * axis[1] * axis[0] - axis[2] * sin_angle
    ob_matrix[0][2] = one_minus_cos * axis[2] * axis[0] + axis[1] * sin_angle

    ob_matrix[1][0] = one_minus_cos * axis[0] * axis[1] + axis[2] * sin_angle
    ob_matrix[1][1] = cos_angle + one_minus_cos * axis[1] * axis[1]
    ob_matrix[1][2] = one_minus_cos * axis[2] * axis[1] - axis[0] * sin_angle

    ob_matrix[2][0] = one_minus_cos * axis[0] * axis[2] - axis[1] * sin_angle
    ob_matrix[2][1] = one_minus_cos * axis[1] * axis[2] + axis[0] * sin_angle
    ob_matrix[2][2] = cos_angle + one_minus_cos * axis[2] * axis[2]

    mesh1.add_variable("w1", _3ds_float(ob_matrix[0][0]))
    mesh1.add_variable("w2", _3ds_float(ob_matrix[0][1]))
    mesh1.add_variable("w3", _3ds_float(ob_matrix[0][2]))
    mesh1.add_variable("x1", _3ds_float(ob_matrix[1][0]))
    mesh1.add_variable("x2", _3ds_float(ob_matrix[1][1]))
    mesh1.add_variable("x3", _3ds_float(ob_matrix[1][2]))
    mesh1.add_variable("y1", _3ds_float(ob_matrix[2][0]))
    mesh1.add_variable("y2", _3ds_float(ob_matrix[2][1]))
    mesh1.add_variable("y3", _3ds_float(ob_matrix[2][2]))
    mesh1.add_variable("z1", _3ds_float(ob_matrix[3][0]))
    mesh1.add_variable("z2", _3ds_float(ob_matrix[3][1]))
    mesh1.add_variable("z3", _3ds_float(ob_matrix[3][2]))

    mesh_chunk.add_subchunk(mesh1)

    if uv_array:
        mesh_chunk.add_subchunk(make_uv_chunk(uv_array))

    return mesh_chunk


def make_kfdata(start=0, stop=0, curtime=0, rev=0):
    kfdata = _3ds_chunk(KFDATA)

    kfhdr = _3ds_chunk(KFDATA_KFHDR)
    kfhdr.add_variable("revision", _3ds_ushort(rev))
    kfhdr.add_variable("filename", _3ds_string(b"Blender"))
    kfhdr.add_variable("animlen", _3ds_uint(stop - start))

    kfseg = _3ds_chunk(KFDATA_KFSEG)
    kfseg.add_variable("start", _3ds_uint(start))
    kfseg.add_variable("stop", _3ds_uint(stop))

    kfcurtime = _3ds_chunk(KFDATA_KFCURTIME)
    kfcurtime.add_variable("curtime", _3ds_uint(curtime))

    kfdata.add_subchunk(kfhdr)
    kfdata.add_subchunk(kfseg)
    kfdata.add_subchunk(kfcurtime)
    return kfdata


def make_track_chunk(track_id, obj, obj_size, obj_pos, obj_rot):
    track_chunk = _3ds_chunk(track_id)
    track_chunk.add_variable("track_flags", _3ds_ushort())
    track_chunk.add_variable("unknown", _3ds_uint(0))
    track_chunk.add_variable("unknown", _3ds_uint(0))
    track_chunk.add_variable("nkeys", _3ds_uint(1))
    track_chunk.add_variable("tcb_frame", _3ds_uint(0))
    track_chunk.add_variable("tcb_flags", _3ds_ushort())

    if track_id == POS_TRACK_TAG:
        track_chunk.add_variable("position", _3ds_point_3d(obj_pos))
    elif track_id == ROT_TRACK_TAG:
        track_chunk.add_variable(
            "rotation",
            _3ds_point_4d(
                (obj_rot.angle, obj_rot.axis[0], obj_rot.axis[1], obj_rot.axis[2])
            ),
        )
    elif track_id == SCL_TRACK_TAG:
        track_chunk.add_variable("scale", _3ds_point_3d(obj_size))

    return track_chunk


def make_kf_obj_node(obj, name_to_id, name_to_scale, name_to_pos, name_to_rot):
    name = obj.name
    kf_obj_node = _3ds_chunk(KFDATA_OBJECT_NODE_TAG)

    obj_id_chunk = _3ds_chunk(OBJECT_NODE_ID)
    obj_id_chunk.add_variable("node_id", _3ds_ushort(name_to_id[name]))

    obj_node_header_chunk = _3ds_chunk(OBJECT_NODE_HDR)
    obj_node_header_chunk.add_variable("name", _3ds_string(sane_name(name)))
    obj_node_header_chunk.add_variable("flags1", _3ds_ushort(0x0040))
    obj_node_header_chunk.add_variable("flags2", _3ds_ushort(0))

    parent = obj.parent
    if (parent is None) or (parent.name not in name_to_id):
        obj_node_header_chunk.add_variable("parent", _3ds_ushort(-1))
    else:
        obj_node_header_chunk.add_variable("parent", _3ds_ushort(name_to_id[parent.name]))

    kf_obj_node.add_subchunk(obj_id_chunk)
    kf_obj_node.add_subchunk(obj_node_header_chunk)

    if (parent is None) or (parent.name not in name_to_id):
        # Original 4KEX (fdae86a): unparented pivot is always (0,0,0).
        # World placement comes from POS_TRACK (+ mesh matrix for meshes).
        pivot_pos = (0.0, 0.0, 0.0)
    else:
        pivot_pos = mathutils.Vector(
            (
                name_to_pos[name][0] - name_to_pos[parent.name][0],
                name_to_pos[name][1] - name_to_pos[parent.name][1],
                name_to_pos[name][2] - name_to_pos[parent.name][2],
            )
        ) * name_to_rot[parent.name].to_matrix()

    obj_pivot_chunk = _3ds_chunk(OBJECT_PIVOT)
    obj_pivot_chunk.add_variable("pivot", _3ds_point_3d(pivot_pos))
    kf_obj_node.add_subchunk(obj_pivot_chunk)

    if (parent is None) or (parent.name not in name_to_id):
        obj_size = (1.0, 1.0, 1.0)
        obj_pos = name_to_pos[name]
        obj_rot = name_to_rot[name]
    else:
        obj_size = (1.0, 1.0, 1.0)
        obj_pos = mathutils.Vector(
            (
                name_to_pos[name][0] - name_to_pos[parent.name][0],
                name_to_pos[name][1] - name_to_pos[parent.name][1],
                name_to_pos[name][2] - name_to_pos[parent.name][2],
            )
        ) * name_to_rot[parent.name].to_matrix()
        obj_rot = name_to_rot[name].cross(name_to_rot[parent.name].copy().inverted())

    kf_obj_node.add_subchunk(make_track_chunk(SCL_TRACK_TAG, obj, obj_size, obj_pos, obj_rot))
    kf_obj_node.add_subchunk(make_track_chunk(ROT_TRACK_TAG, obj, obj_size, obj_pos, obj_rot))
    kf_obj_node.add_subchunk(make_track_chunk(POS_TRACK_TAG, obj, obj_size, obj_pos, obj_rot))

    return kf_obj_node


def re_create_derived_objects(context, ob):
    if ob.parent and ob.parent.instance_type in {"VERTS", "FACES"}:
        return None

    depsgraph = context.evaluated_depsgraph_get()
    if ob.instance_type != "NONE":
        return [
            (dob.instance_object.original, dob.matrix_world.copy())
            for dob in depsgraph.object_instances
            if dob.parent and dob.parent.original == ob
        ]
    return [(ob, ob.matrix_world)]


def _register_materials(material_dict, ob, mesh, texture_filename):
    mat_ls = mesh.materials
    mat_ls_len = len(mat_ls)
    force_name = forced_material_name(ob.name)

    if mat_ls:
        for mat in mat_ls:
            if mat:
                key_name = force_name or mat.name
                material_dict.setdefault(
                    (key_name, texture_filename),
                    (mat, texture_filename, key_name),
                )
    elif texture_filename:
        stem = force_name or texture_filename.rsplit(".", 1)[0]
        material_dict.setdefault(
            (stem, texture_filename),
            (None, texture_filename, stem),
        )

    if mat_ls_len:
        for face in mesh.loop_triangles:
            if face.material_index >= mat_ls_len:
                face.material_index = 0


def cleanup_mesh_objects(mesh_objects):
    for _ob, mesh in list(mesh_objects):
        if mesh is None:
            continue
        try:
            bpy.data.meshes.remove(mesh)
        except ReferenceError:
            pass


def _evaluated_mesh_copy(obj, depsgraph):
    """Create an independent Mesh datablock from an evaluated object."""
    obj_eval = obj.evaluated_get(depsgraph)
    try:
        return bpy.data.meshes.new_from_object(
            obj_eval,
            preserve_all_data_layers=True,
            depsgraph=depsgraph,
        )
    except (RuntimeError, TypeError):
        pass

    # Fallback without preserving all layers (still includes UVs needed for 3DS).
    try:
        return bpy.data.meshes.new_from_object(obj_eval)
    except (RuntimeError, TypeError):
        return None


def collect_mesh_data(context, use_selection, verbose=False, log_lines=None):
    """Gather allowlisted meshes and optional light Empties for export.

    ProjShad / LightFProj / MaxBox are always stripped (engine uses .dds only for
    the projectors — same as working 2.1.2). Required meshes are still force-
    included when Selection Only is on.
    """
    scene = context.scene
    visible = [ob for ob in scene.objects if ob.visible_get()]
    if use_selection:
        objects = [
            ob
            for ob in visible
            if ob.select_get() or ob.name in REQUIRED_MESHES
        ]
    else:
        objects = visible

    mesh_objects = []
    empty_objects = []
    material_dict = {}
    texture_info = {}

    depsgraph = context.evaluated_depsgraph_get()

    _vlog(verbose, "----- Collect -----", log_lines)
    _vlog(
        verbose,
        f"Candidates: {len(objects)} visible"
        f"{' (selection + required)' if use_selection else ''}",
        log_lines,
    )

    for ob in objects:
        if is_export_blacklisted(ob.name):
            _vlog(
                verbose,
                f"  [SKIP] {ob.name}  reason=blacklisted "
                f"(ProjShad/LightFProj/MaxBox — .dds / guide only)",
                log_lines,
            )
            continue

        if ob.type == "EMPTY":
            if ob.name in ALLOWED_MESH_NAMES:
                empty_objects.append(ob)
                _vlog(
                    verbose,
                    f"  [COLLECTED] {ob.name}  type=EMPTY  "
                    f"loc={_fmt_vec(ob.location)}  (KFDATA light helper)",
                    log_lines,
                )
            else:
                _vlog(
                    verbose,
                    f"  [SKIP] {ob.name}  reason=Empty (not on light allowlist)",
                    log_lines,
                )
            continue

        if ob.name not in ALLOWED_MESH_NAMES:
            _vlog(
                verbose,
                f"  [SKIP] {ob.name}  reason=not on allowlist  type={ob.type}",
                log_lines,
            )
            continue

        derived = re_create_derived_objects(context, ob)
        if derived is None:
            _vlog(
                verbose,
                f"  [SKIP] {ob.name}  reason=instancer child / no derived",
                log_lines,
            )
            continue

        for ob_derived, _matrix_world in derived:
            if is_export_blacklisted(ob_derived.name):
                _vlog(
                    verbose,
                    f"  [SKIP] {ob_derived.name}  reason=blacklisted (derived)",
                    log_lines,
                )
                continue
            if ob_derived.type not in {"MESH", "CURVE", "SURFACE", "FONT", "META"}:
                _vlog(
                    verbose,
                    f"  [SKIP] {ob_derived.name}  reason=unsupported type "
                    f"{ob_derived.type}",
                    log_lines,
                )
                continue
            if ob_derived.name not in ALLOWED_MESH_NAMES:
                _vlog(
                    verbose,
                    f"  [SKIP] {ob_derived.name}  reason=not on allowlist (derived)",
                    log_lines,
                )
                continue

            data = _evaluated_mesh_copy(ob_derived, depsgraph)
            if data is None or len(data.vertices) == 0:
                if data is not None:
                    bpy.data.meshes.remove(data)
                _vlog(
                    verbose,
                    f"  [FAIL] {ob_derived.name}  reason=no evaluable mesh geometry",
                    log_lines,
                )
                continue

            data.calc_loop_triangles()
            mesh_objects.append((ob_derived, data))

            texture_filename, image = get_object_texture_reference(ob_derived, data)
            texture_info[ob_derived.name] = (texture_filename, image)
            _register_materials(material_dict, ob_derived, data, texture_filename)
            log_export_object(
                ob_derived,
                data,
                texture_filename,
                image,
                verbose,
                status="COLLECTED",
                log_lines=log_lines,
            )

    _vlog(
        verbose,
        f"Collected {len(mesh_objects)} mesh(es), {len(empty_objects)} empty helper(s)",
        log_lines,
    )
    return mesh_objects, empty_objects, material_dict, texture_info


def do_export(
    context,
    filename,
    mesh_objects,
    empty_objects,
    material_dict,
    verbose=False,
    texture_info=None,
    log_lines=None,
):
    """Save the Blender scene to a 3DS file."""
    reset_name_tables()
    texture_info = texture_info or {}

    primary = _3ds_chunk(PRIMARY)
    version_chunk = _3ds_chunk(VERSION)
    version_chunk.add_variable("version", _3ds_uint(3))
    primary.add_subchunk(version_chunk)

    object_info = _3ds_chunk(OBJECTINFO)
    kfdata = make_kfdata(0, 100, 0, 1)

    _vlog(verbose, "----- 3DS Material Library -----", log_lines)
    for mat_and_texture in material_dict.values():
        if len(mat_and_texture) == 3:
            material, texture_filename, mat_name = mat_and_texture
        else:
            material, texture_filename = mat_and_texture
            mat_name = material.name if material else (
                texture_filename.rsplit(".", 1)[0] if texture_filename else "None"
            )
        sane_mat = sane_name(mat_name)
        sane_map = sane_name(texture_filename) if texture_filename else None
        _vlog(
            verbose,
            f"  [MAT] name={sane_mat}  mapfile={sane_map or '<none>'}  "
            f"blender_mat={material.name if material else '<synthetic>'}",
            log_lines,
        )
        object_info.add_subchunk(
            make_material_chunk(material, texture_filename, material_name=mat_name)
        )

    mscale = _3ds_chunk(MASTERSCALE)
    mscale.add_variable("scale", _3ds_float(1))
    object_info.add_subchunk(mscale)

    name_to_id = {}
    name_to_scale = {}
    name_to_pos = {}
    name_to_rot = {}

    for ob, _data in mesh_objects:
        name_to_id[ob.name] = len(name_to_id)
        name_to_scale[ob.name] = ob.dimensions
        name_to_pos[ob.name] = ob.location
        name_to_rot[ob.name] = ob.rotation_euler.to_quaternion().inverted()

    for ob in empty_objects:
        name_to_id[ob.name] = len(name_to_id)
        name_to_scale[ob.name] = ob.dimensions
        name_to_pos[ob.name] = ob.location
        name_to_rot[ob.name] = ob.rotation_euler.to_quaternion().inverted()

    _vlog(verbose, "----- Write .3ds -----", log_lines)
    all_warns = []
    for ob, blender_mesh in mesh_objects:
        try:
            object_chunk = _3ds_chunk(OBJECT)
            object_chunk.add_variable("name", _3ds_string(sane_name(ob.name)))
            object_chunk.add_subchunk(
                make_mesh_chunk(
                    blender_mesh,
                    material_dict,
                    ob,
                    name_to_id,
                    name_to_scale,
                    name_to_pos,
                    name_to_rot,
                )
            )
            object_info.add_subchunk(object_chunk)
            kfdata.add_subchunk(
                make_kf_obj_node(ob, name_to_id, name_to_scale, name_to_pos, name_to_rot)
            )
            tex, image = texture_info.get(ob.name, (None, None))
            if tex is None:
                tex, image = get_object_texture_reference(ob, blender_mesh)
            bind = resolve_3ds_material_binding(ob, blender_mesh, tex, image)
            for warn in bind["warns"]:
                all_warns.append(f"{ob.name}: {warn}")
            log_export_object(
                ob,
                blender_mesh,
                tex,
                image,
                verbose,
                status="WRITTEN",
                log_lines=log_lines,
            )
        except Exception as exc:
            _vlog(verbose, f"  [FAIL] {ob.name}  reason=write error: {exc}", log_lines)
            raise

    for ob in empty_objects:
        kfdata.add_subchunk(
            make_kf_obj_node(ob, name_to_id, name_to_scale, name_to_pos, name_to_rot)
        )
        _vlog(
            verbose,
            f"  [WRITTEN] {ob.name}  type=EMPTY  "
            f"kf_pivot=(0.0, 0.0, 0.0)  pos_track={_fmt_vec(ob.location)}",
            log_lines,
        )

    primary.add_subchunk(object_info)
    primary.add_subchunk(kfdata)
    primary.get_size()

    with open(filename, "wb") as file:
        primary.write(file)

    exported = ", ".join(sorted(name_to_id.keys()))
    print(f"Exported {len(name_to_id)} objects: {exported}")
    _vlog(verbose, f"File written: {filename}", log_lines)

    if verbose:
        _vlog(verbose, "----- Diagnostics / Fix Checklist -----", log_lines)
        if all_warns:
            for warn in all_warns:
                _vlog(verbose, f"  [WARN] {warn}", log_lines)
        else:
            _vlog(verbose, "  No material/UV warnings.", log_lines)

        present = set(name_to_id.keys())
        missing_req = [n for n in REQUIRED_MESHES if n not in present]
        if missing_req:
            _vlog(
                verbose,
                f"  [WARN] missing required meshes in file: {', '.join(missing_req)}",
                log_lines,
            )
        for banned in ("ProjShad", "LightFProj", "MaxBox", "Maxbox"):
            if banned in present:
                _vlog(
                    verbose,
                    f"  [WARN] {banned} was written (should be blacklisted)",
                    log_lines,
                )
            else:
                _vlog(
                    verbose,
                    f"  [OK] {banned} not in .3ds (correct — use .dds / guide only)",
                    log_lines,
                )

        log_path = filename.rsplit(".", 1)[0] + ".tmf-export.log"
        try:
            with open(log_path, "w", encoding="utf-8") as log_file:
                log_file.write("\n".join(log_lines or []) + "\n")
            _vlog(verbose, f"Verbose log also saved: {log_path}", log_lines)
            # Append the path line to the file as well
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"Verbose log also saved: {log_path}\n")
        except OSError as exc:
            _vlog(verbose, f"  [WARN] could not write log file: {exc}", log_lines)

    reset_name_tables()
    return True
