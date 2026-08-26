# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

from dataclasses import dataclass, field

from .material_utils import expected_texture_filename, texture_reference_matches

REQUIRED_MESHES = (
    "sBody",
    "dBody",
    "gBody",
    "dFLWheel",
    "sFLWheel",
    "dFRWheel",
    "sFRWheel",
    "dRLWheel",
    "sRLWheel",
    "dRRWheel",
    "sRRWheel",
)

# Optional light helpers (exported when present; not required for Strict validation).
OPTIONAL_LIGHT_EMPTIES = (
    "LightFL1",
    "LightFR1",
    "LightFL2",
    "LightFR2",
    "LightFL3",
    "LightFR3",
    "LightRL",
    "LightRR",
)

MAX_BOX_MM = {
    "x": 3.0,
    "y": 6.0,
    "z": 2.5,
}

VERTEX_LIMITS = {
    "HIGH": 100_000,
    "LOW": 3_600,
}

TRANSFORM_TOLERANCE = 1e-4
MESH_TYPES = {"MESH", "CURVE", "SURFACE", "FONT", "META"}


@dataclass
class ValidationResult:
    ok: bool = True
    errors: list = field(default_factory=list)

    def add_error(self, message):
        self.ok = False
        self.errors.append(message)


def bu_to_mm(scene, value):
    """Convert a Blender-unit distance to millimeters."""
    scale = scene.unit_settings.scale_length
    if scale <= 0.0:
        scale = 1.0
    return value * scale * 1000.0


def gather_export_objects(context, use_selection):
    scene = context.scene
    if use_selection:
        return [ob for ob in scene.objects if ob.visible_get() and ob.select_get()]
    return [ob for ob in scene.objects if ob.visible_get()]


def _scale_is_identity(ob, tolerance=TRANSFORM_TOLERANCE):
    return all(abs(s - 1.0) < tolerance for s in ob.scale)


def _rotation_is_identity(ob, tolerance=TRANSFORM_TOLERANCE):
    euler = ob.rotation_euler
    return (
        abs(euler.x) < tolerance
        and abs(euler.y) < tolerance
        and abs(euler.z) < tolerance
    )


def _safe_mesh_vertices(mesh):
    """Return mesh.vertices, or None if the datablock is missing/invalid."""
    if mesh is None:
        return None
    try:
        return mesh.vertices
    except (AttributeError, ReferenceError, TypeError):
        return None


def mesh_bounds_mm(scene, mesh):
    """Axis-aligned size of a mesh already transformed into world space."""
    verts = _safe_mesh_vertices(mesh)
    if verts is None or len(verts) == 0:
        return None

    min_co = [float("inf")] * 3
    max_co = [float("-inf")] * 3
    for vert in verts:
        co = vert.co
        for i in range(3):
            min_co[i] = min(min_co[i], co[i])
            max_co[i] = max(max_co[i], co[i])

    return {
        "x": bu_to_mm(scene, max_co[0] - min_co[0]),
        "y": bu_to_mm(scene, max_co[1] - min_co[1]),
        "z": bu_to_mm(scene, max_co[2] - min_co[2]),
    }


def count_export_vertices(mesh_objects):
    """Count vertices the same way the exporter will after triangulation/UV split."""
    from .exporter import count_mesh_export_vertices

    total = 0
    for _ob, mesh in mesh_objects:
        if mesh is None:
            continue
        total += count_mesh_export_vertices(mesh)
    return total


def validate_export(context, mesh_objects, empty_objects, poly_target):
    result = ValidationResult()
    scene = context.scene

    mesh_names = {ob.name for ob, _ in mesh_objects}
    empty_names = {ob.name for ob in empty_objects}
    all_names = mesh_names | empty_names

    for required in REQUIRED_MESHES:
        if required not in mesh_names:
            result.add_error(f"Missing required mesh object: {required}")

    for name in OPTIONAL_LIGHT_EMPTIES:
        if name not in empty_names:
            continue
        ob = next(ob for ob in empty_objects if ob.name == name)
        if ob.type != "EMPTY":
            result.add_error(f"{name}: light helpers must be Empty objects, found {ob.type}")

    for ob, mesh in mesh_objects:
        if ob.name not in REQUIRED_MESHES:
            continue

        verts = _safe_mesh_vertices(mesh)
        if verts is None or len(verts) == 0:
            result.add_error(f"{ob.name}: has no evaluable mesh geometry")
            continue

        if not _scale_is_identity(ob):
            result.add_error(
                f"{ob.name}: unapplied scale {tuple(round(s, 4) for s in ob.scale)} "
                f"(Apply Scale before export)"
            )

        if not _rotation_is_identity(ob):
            rot = tuple(round(r, 4) for r in ob.rotation_euler)
            result.add_error(
                f"{ob.name}: unapplied rotation {rot} (Apply Rotation before export)"
            )

        try:
            bounds = mesh_bounds_mm(scene, mesh)
        except Exception as exc:
            result.add_error(f"{ob.name}: bounding box failed ({exc})")
            continue

        if bounds is None:
            result.add_error(f"{ob.name}: could not compute bounding box")
            continue

        for axis, limit in MAX_BOX_MM.items():
            if bounds[axis] > limit + TRANSFORM_TOLERANCE:
                result.add_error(
                    f"{ob.name}: {axis}-axis size {bounds[axis]:.4f} mm "
                    f"exceeds max {limit} mm"
                )

        if expected_texture_filename(ob.name) is not None:
            ok, message = texture_reference_matches(ob, mesh)
            if not ok:
                result.add_error(message)

    vertex_limit = VERTEX_LIMITS.get(poly_target, VERTEX_LIMITS["HIGH"])
    try:
        vertex_count = count_export_vertices(mesh_objects)
    except Exception as exc:
        result.add_error(f"Vertex count failed ({exc})")
        vertex_count = 0
    if vertex_count > vertex_limit:
        result.add_error(
            f"Vertex count {vertex_count} exceeds {poly_target} poly limit ({vertex_limit})"
        )

    if not mesh_objects and not empty_objects:
        result.add_error("No objects selected for export")

    for name in sorted(all_names):
        for required in REQUIRED_MESHES + OPTIONAL_LIGHT_EMPTIES:
            if required not in all_names and name.lower() == required.lower():
                result.add_error(
                    f"Object '{name}' looks like '{required}' but spelling/case differs"
                )

    return result
