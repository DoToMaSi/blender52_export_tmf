# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

from dataclasses import dataclass, field

# Classic United tutorial car parts. Forever can import a single mesh (e.g. only
# sBody); these names are recommended completeness checks (warnings), not Strict
# blockers.
RECOMMENDED_MESHES = (
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

# Back-compat alias used by exporter allowlist / logs.
REQUIRED_MESHES = RECOMMENDED_MESHES

# Projector meshes written into the .3ds (geometry defines Quality 2 / headlight
# projection). ProjShad.dds alone in the zip is not enough — missing mesh →
# "Quality 2's bounding box (0 ...".
PROJECTOR_MESHES = (
    "ProjShad",
    "LightFProj",
)

# Optional light helpers (tiny meshes or Empties). Exported as KFDATA-only.
# Matching is case-insensitive via is_optional_light_helper() — stock blends use
# mixed casings (FLlight1 vs FLLight1 vs LightFL1).
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
    # Stock Nadeo / MainBodyHigh style (e.g. MainBed(High).blend)
    "FLlight1",
    "FRlight1",
    "FLlight2",
    "FRlight2",
    "FLlight3",
    "FRlight3",
    "RLlight",
    "RRlight",
    # Alternate capitalizations seen in docs / older exports
    "FLLight1",
    "FRLight1",
    "FLLight2",
    "FRLight2",
    "FLLight3",
    "FRLight3",
    "RLLight",
    "RRLight",
)

# Full stock-car name set (3ds Max Select Objects / Nadeo reference). Used for empty
# Outliner collections as a naming guide — collections are never exported.
TMF_NAME_GUIDE_MESHES = (
    "dBody",
    "dFLArmBot",
    "dFLArmDir",
    "dFLArmTop",
    "dFLGuard",
    "dFLHub",
    "dFLWheel",
    "dFRArmBot",
    "dFRArmDir",
    "dFRArmTop",
    "dFRGuard",
    "dFRHub",
    "dFRWheel",
    "dRLArmBot",
    "dRLArmTop",
    "dRLCardan",
    "dRLHub",
    "dRLWheel",
    "dRRArmBot",
    "dRRArmTop",
    "dRRCardan",
    "dRRHub",
    "dRRWheel",
    "gBody",
    "LightFL1",
    "LightFL2",
    "LightFL3",
    "LightFR1",
    "LightFR2",
    "LightFR3",
    "LightFProj",
    "LightRL",
    "LightRR",
    "ProjShad",
    "sBody",
    "sFLWheel",
    "sFRWheel",
    "sRLWheel",
    "sRRWheel",
)

TMF_NAMES_ROOT_COLLECTION = "TMF Mesh Names"

_OPTIONAL_MESHES_FOLD = frozenset(n.casefold() for n in OPTIONAL_MESHES)


def _strip_blender_suffix(name):
    if "." in name and name.rsplit(".", 1)[1].isdigit():
        return name.rsplit(".", 1)[0]
    return name


def is_optional_light_helper(name):
    """True for light flare helpers (any common casing / .001 suffix)."""
    return _strip_blender_suffix(name).casefold() in _OPTIONAL_MESHES_FOLD


# Only MaxBox is never written (in-scene scale guide).
EXPORT_HELPER_BLACKLIST = frozenset({
    "maxbox",
})

# ProjShad must have a usable ground footprint or Quality 2 collapses to 0.
MIN_PROJSHAD_FOOTPRINT = 1.0
MIN_LIGHTFPROJ_EXTENT = 0.5


def is_export_blacklisted(name):
    """True if this object must never be written to the .3ds (any casing / .001)."""
    return _strip_blender_suffix(name).casefold() in EXPORT_HELPER_BLACKLIST


def is_projector_mesh(name):
    """True for ProjShad / LightFProj (any casing / .001)."""
    folded = _strip_blender_suffix(name).casefold()
    return folded == "projshad" or folded.startswith("lightfproj")


def subject_to_strict_extents(name):
    """
    Strict MaxBox Y/Z checks apply to car body / wheel meshes only.

    ProjShad is often a large ground plane (or rotated +90° X so footprint lies
    in XZ) and intentionally exceeds the car height band — excluding it avoids
    false Strict failures on working cars. Light helpers are tiny flare origins.
    """
    if is_export_blacklisted(name):
        return False
    if is_projector_mesh(name) or is_optional_light_helper(name):
        return False
    return True


def mesh_export_names():
    """Object names that receive a full mesh chunk in the .3ds."""
    return frozenset(RECOMMENDED_MESHES) | frozenset(PROJECTOR_MESHES)

# Absolute world-space limits in millimeters (TMF Maxbox / engine space).
# These are real engine limits (~6×3×2.5 mm box) — NOT meters×1000.
# A real-world bumper at 1.5 m must be authored at ~1.5 mm (0.1% scale).
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
    warnings: list = field(default_factory=list)

    def add_error(self, message):
        """Strict blocker (absolute MaxBox extents)."""
        self.ok = False
        self.errors.append(message)

    def add_warning(self, message):
        """Advisory only — never blocks Strict or export."""
        self.warnings.append(message)


def to_tmf_mm(value):
    """Coordinate as written to the .3ds (TMF Maxbox millimeters).

    The exporter writes Blender floats as-is (MASTERSCALE = 1). TMF cars are
    authored at 0.1% scale with 1 scene unit = 1 mm, so validation must use the
    same numbers — never multiply by 1000 (that falsely treats Maxbox mm as meters).
    """
    return value


# Back-compat alias (scene argument ignored — kept for older call sites).
def bu_to_mm(scene, value):
    return to_tmf_mm(value)


def gather_export_objects(context, use_selection):
    scene = context.scene
    if use_selection:
        return [ob for ob in scene.objects if ob.visible_get() and ob.select_get()]
    return [ob for ob in scene.objects if ob.visible_get()]


def _scale_is_identity(ob, tolerance=TRANSFORM_TOLERANCE):
    return all(abs(s - 1.0) < tolerance for s in ob.scale)


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

    Export mesh copies are world-baked via data.transform(matrix_world) (2.1.2);
    vert.co is already in world space — do not multiply by matrix_world again.

    Rotation is not checked separately: only the resulting world verts vs MaxBox.
    """
    verts = _safe_mesh_vertices(mesh)
    if verts is None or len(verts) == 0:
        return ["has no evaluable mesh geometry"]

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
        co = vert.co
        y_mm = to_tmf_mm(co.y)
        z_mm = to_tmf_mm(co.z)

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
    """
    Validate collected export meshes.

    Strict blockers (``errors`` / ``ok=False``): world verts of car body/wheel
    meshes outside MaxBox Y/Z. Forever does not require a full United mesh set.

    Advisories (``warnings``): missing recommended parts, ProjShad, scale,
    loose verts, sBody origin, vertex budget, naming typos — never block Strict.
    """
    result = ValidationResult()
    scene = context.scene

    mesh_names = {ob.name for ob, _ in mesh_objects}

    for recommended in RECOMMENDED_MESHES:
        if recommended not in mesh_names:
            result.add_warning(
                f"Missing recommended mesh: {recommended} "
                f"(Forever can still import a partial car)"
            )

    has_projshad = any(
        _strip_blender_suffix(n).casefold() == "projshad" for n in mesh_names
    )
    if not has_projshad:
        result.add_warning(
            "Missing ProjShad mesh (Quality 2 shadow may be wrong — "
            "ProjShad.dds in the zip is not enough)"
        )

    checked = set()
    for ob, mesh in mesh_objects:
        if ob.name in checked:
            continue
        checked.add(ob.name)

        verts = _safe_mesh_vertices(mesh)
        if verts is None or len(verts) == 0:
            if subject_to_strict_extents(ob.name):
                result.add_error(f"{ob.name}: has no evaluable mesh geometry")
            else:
                result.add_warning(f"{ob.name}: has no evaluable mesh geometry")
            continue

        if not _scale_is_identity(ob):
            result.add_warning(
                f"{ob.name}: unapplied scale {tuple(round(s, 4) for s in ob.scale)} "
                f"(Apply Scale recommended)"
            )

        # Rotation is never a separate check — only world-space verts vs MaxBox.

        if not is_projector_mesh(ob.name) and not is_optional_light_helper(ob.name):
            loose = count_loose_vertices(mesh)
            if loose > 0:
                result.add_warning(
                    f"{ob.name}: has {loose} loose/disconnected vertices "
                    f"not used by any face"
                )

        if subject_to_strict_extents(ob.name):
            try:
                for msg in check_absolute_extents_mm(scene, mesh, ob):
                    result.add_error(f"{ob.name}: {msg}")
            except Exception as exc:
                result.add_error(f"{ob.name}: absolute extent check failed ({exc})")

        # Projector footprint — advisory (zero size → Quality 2 bbox 0).
        if is_projector_mesh(ob.name):
            dims = ob.dimensions
            # Rotated ProjShad (+90° X) has footprint on X/Z, not X/Y.
            footprint = max(float(dims.x), float(dims.y), float(dims.z))
            base = _strip_blender_suffix(ob.name)
            if base.casefold() == "projshad":
                if footprint < MIN_PROJSHAD_FOOTPRINT:
                    result.add_warning(
                        f"{ob.name}: footprint {footprint:.4f} too small "
                        f"(need ≥ {MIN_PROJSHAD_FOOTPRINT}; Quality 2 bbox → 0)"
                    )
            elif footprint < MIN_LIGHTFPROJ_EXTENT:
                result.add_warning(
                    f"{ob.name}: extent {footprint:.4f} too small "
                    f"(need ≥ {MIN_LIGHTFPROJ_EXTENT})"
                )

    # Engine anchors suspension / tires from sBody origin — advisory for Forever.
    for ob, _mesh in mesh_objects:
        if ob.name != "sBody":
            continue
        loc = ob.location
        if (
            abs(loc.x) > ORIGIN_TOLERANCE
            or abs(loc.y) > ORIGIN_TOLERANCE
            or abs(loc.z) > ORIGIN_TOLERANCE
        ):
            result.add_warning(
                f"sBody: origin preferably at (0, 0, 0), found "
                f"({loc.x:.6f}, {loc.y:.6f}, {loc.z:.6f})"
            )

    vertex_limit = VERTEX_LIMITS.get(poly_target, VERTEX_LIMITS["HIGH"])
    try:
        vertex_count = count_export_vertices(mesh_objects)
    except Exception as exc:
        result.add_warning(f"Vertex count failed ({exc})")
        vertex_count = 0
    if vertex_count > vertex_limit:
        result.add_warning(
            f"Vertex count {vertex_count} exceeds {poly_target} poly target "
            f"({vertex_limit}) — may fail Low/High Solid compile"
        )

    if not mesh_objects:
        result.add_error("No objects selected for export")

    known = RECOMMENDED_MESHES + PROJECTOR_MESHES + OPTIONAL_MESHES
    for name in sorted(mesh_names):
        for recommended in known:
            if recommended not in mesh_names and name.lower() == recommended.lower():
                result.add_warning(
                    f"Object '{name}' looks like '{recommended}' but spelling/case differs"
                )

    return result
