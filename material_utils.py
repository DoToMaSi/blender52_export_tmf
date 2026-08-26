# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

import bpy


def get_principled_bsdf(material):
    if material is None or material.node_tree is None:
        return None
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    return None


def _input_value(bsdf, names, default):
    if bsdf is None:
        return default
    for name in names:
        sock = bsdf.inputs.get(name)
        if sock is not None:
            return sock.default_value
    return default


def get_material_export_data(material):
    """Extract material colors and factors from the Principled BSDF node."""
    bsdf = get_principled_bsdf(material)

    base_color = _input_value(bsdf, ("Base Color",), (0.8, 0.8, 0.8, 1.0))
    if len(base_color) == 3:
        base_color = (base_color[0], base_color[1], base_color[2], 1.0)

    roughness = _input_value(bsdf, ("Roughness",), 0.5)
    specular = _input_value(bsdf, ("Specular IOR Level", "Specular"), 0.5)
    alpha = _input_value(bsdf, ("Alpha",), 1.0)

    tint = _input_value(bsdf, ("Tint", "Specular Tint"), (1.0, 1.0, 1.0, 1.0))
    if len(tint) >= 3:
        specular_color = (tint[0], tint[1], tint[2])
    else:
        specular_color = (1.0, 1.0, 1.0)

    ambient = tuple(c * 0.2 for c in base_color[:3])

    return {
        "diffuse_color": base_color,
        "ambient_color": ambient,
        "specular_color": specular_color,
        "roughness": roughness,
        "specular_intensity": specular,
        "alpha": alpha,
    }


def get_material_image(material):
    """Find the first image texture linked to or placed in the material."""
    if material is None or material.node_tree is None:
        return None
    for node in material.node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.image is not None:
            return node.image
    return None


def _iter_object_materials(obj, mesh=None):
    """Yield materials from mesh slots, then object data slots."""
    seen = set()
    sources = []
    if mesh is not None:
        sources.append(mesh.materials)
    if obj.type == "MESH" and obj.data is not None:
        sources.append(obj.data.materials)
    for material_slots in sources:
        for mat in material_slots:
            if mat is None:
                continue
            mat_id = mat.as_pointer()
            if mat_id in seen:
                continue
            seen.add(mat_id)
            yield mat


def get_object_texture_reference(obj, mesh=None):
    """
    Resolve an optional texture filename from the object's materials.

    Trackmania binds Diffuse.dds / Details.dds by object name in the car zip,
    not from Blender material assignments — so we never invent or enforce those
    names here. If a material has an image, its basename is passed through as-is.
    """
    image = None
    for mat in _iter_object_materials(obj, mesh):
        image = get_material_image(mat)
        if image is not None:
            break

    if image is None:
        return None, None

    basename = bpy.path.basename(image.filepath)
    if not basename:
        basename = image.name
    return basename or None, image
