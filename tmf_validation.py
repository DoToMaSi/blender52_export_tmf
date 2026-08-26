# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

from dataclasses import dataclass, field

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

# Optional car meshes (exported when present; not required for Strict validation).
OPTIONAL_MESHES = (
    # Tutorial / manual naming
    "LightFL1",
    "LightFR1",
    "LightFL2",
    "LightFR2",
    "LightFL3",
    "LightFR3",
    "LightRL",
    "LightRR",
    # Stock Nadeo mesh naming (tiny helper meshes)
    "FLLight1",
    "FRLight1",
    "FLLight2",
    "FRLight2",
    "FLLight3",
    "FRLight3",
    "RLLight",
    "RRLight",
    "ProjShad",
    "LightFProj",
)

# Not exported: Maxbox is an in-scene scale reference only.
EXPORT_HELPER_BLACKLIST = frozenset({
    "Maxbox",
})

# Absolute world-space limits in millimeters (TMF Maxbox / engine space).
ABS_Y_MM = (-3.0, 3.0)
ABS_Z_MM = (-0.3, 2.2)

VERTEX_LIMITS = {
    "HIGH": 100_000,
    "LOW": 3_600,
}

TRANSFORM_TOLERANCE = 1e-4
ORIGIN_TOLERANCE = 1e-5
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


def count_loose_vertices(mesh):
    """Count vertices that are not referenced by any polygon (shattered / loose verts)."""
    verts = _safe_mesh_vertices(mesh)
    if verts is None or len(verts) == 0:
        return 0

    used = [False] * len(verts)
    try:
        polygons = mesh.polygons
    except (AttributeError, ReferenceError):
        polygons = ()

    for poly in polygons:
        for vi in poly.vertices:
            if 0 <= vi < len(used):
                used[vi] = True

    # Also mark triangle verts if polygons were empty but loop_triangles exist.
    if not any(used):
        try:
            for tri in mesh.loop_triangles:
                for vi in tri.vertices:
                    if 0 <= vi < len(used):
                        used[vi] = True
        except (AttributeError, ReferenceError):
            pass

    return sum(1 for flag in used if not flag)


def check_absolute_extents_mm(scene, mesh, ob=None):
    """
    Return error suffixes if any vertex is outside absolute TMF world space.
    Mesh vertices are in local/object space; world position uses matrix_world.
    """
    verts = _safe_mesh_vertices(mesh)
    if verts is None or len(verts) == 0:
        return ["has no evaluable mesh geometry"]

    matrix_world = ob.matrix_world if ob is not None else None
    y_min, y_max = ABS_Y_MM
    z_min, z_max = ABS_Z_MM
    errors = []
    worst = {
        "y_low": None,
        "y_high": None,
        "z_low": None,
        "z_high": None,
    }

    for vert in verts:
        co = matrix_world @ vert.co if matrix_world is not None else vert.co
        y_mm = bu_to_mm(scene, co.y)
        z_mm = bu_to_mm(scene, co.z)

        if y_mm < y_min - TRANSFORM_TOLERANCE:
            if worst["y_low"] is None or y_mm < worst["y_low"]:
                worst["y_low"] = y_mm
        elif y_mm > y_max + TRANSFORM_TOLERANCE:
            if worst["y_high"] is None or y_mm > worst["y_high"]:
                worst["y_high"] = y_mm

        if z_mm < z_min - TRANSFORM_TOLERANCE:
            if worst["z_low"] is None or z_mm < worst["z_low"]:
                worst["z_low"] = z_mm
        elif z_mm > z_max + TRANSFORM_TOLERANCE:
            if worst["z_high"] is None or z_mm > worst["z_high"]:
                worst["z_high"] = z_mm

    if worst["y_low"] is not None:
        errors.append(
            f"Y vertex {worst['y_low']:.4f} mm is below absolute min {y_min} mm"
        )
    if worst["y_high"] is not None:
        errors.append(
            f"Y vertex {worst['y_high']:.4f} mm is above absolute max {y_max} mm"
        )
    if worst["z_low"] is not None:
        errors.append(
            f"Z vertex {worst['z_low']:.4f} mm is below absolute min {z_min} mm"
        )
    if worst["z_high"] is not None:
        errors.append(
            f"Z vertex {worst['z_high']:.4f} mm is above absolute max {z_max} mm"
        )

    return errors


def count_export_vertices(mesh_objects):
    """Count vertices the same way the exporter will after triangulation/UV split."""
    from .exporter import count_mesh_export_vertices

    total = 0
    for _ob, mesh in mesh_objects:
        if mesh is None:
            continue
        total += count_mesh_export_vertices(mesh)
    return total


def validate_export(context, mesh_objects, poly_target):
    result = ValidationResult()
    scene = context.scene

    mesh_names = {ob.name for ob, _ in mesh_objects}

    for required in REQUIRED_MESHES:
        if required not in mesh_names:
            result.add_error(f"Missing required mesh object: {required}")

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

        loose = count_loose_vertices(mesh)
        if loose > 0:
            result.add_error(
                f"{ob.name}: has {loose} loose/disconnected vertices not used by any face"
            )

        try:
            for msg in check_absolute_extents_mm(scene, mesh, ob):
                result.add_error(f"{ob.name}: {msg}")
        except Exception as exc:
            result.add_error(f"{ob.name}: absolute extent check failed ({exc})")

    # Engine anchors suspension / tires from sBody origin.
    for ob, _mesh in mesh_objects:
        if ob.name != "sBody":
            continue
        loc = ob.location
        if (
            abs(loc.x) > ORIGIN_TOLERANCE
            or abs(loc.y) > ORIGIN_TOLERANCE
            or abs(loc.z) > ORIGIN_TOLERANCE
        ):
            result.add_error(
                f"sBody: origin must be at (0, 0, 0), found "
                f"({loc.x:.6f}, {loc.y:.6f}, {loc.z:.6f})"
            )

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

    if not mesh_objects:
        result.add_error("No objects selected for export")

    for name in sorted(mesh_names):
        for required in REQUIRED_MESHES + OPTIONAL_MESHES:
            if required not in mesh_names and name.lower() == required.lower():
                result.add_error(
                    f"Object '{name}' looks like '{required}' but spelling/case differs"
                )

    return result
