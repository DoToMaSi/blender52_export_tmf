# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

from dataclasses import dataclass, field

from .game_profiles import (
    TMF_LIGHTS,
    TMF_NAME_GUIDE,
    TMF_OPTIONAL_CAR,
    TMF_PROJECTORS,
    TMF_RECOMMENDED,
    TMF_VERTEX_LIMITS,
    get_profile,
    profile_from_context,
    strip_blender_suffix,
    strip_damage_prefix,
)

# Back-compat aliases (Forever / TMF) — prefer get_profile() for new code.
RECOMMENDED_MESHES = TMF_RECOMMENDED
OPTIONAL_CAR_MESHES = TMF_OPTIONAL_CAR
REQUIRED_MESHES = RECOMMENDED_MESHES
PROJECTOR_MESHES = TMF_PROJECTORS
OPTIONAL_MESHES = TMF_LIGHTS
TMF_NAME_GUIDE_MESHES = TMF_NAME_GUIDE
TMF_NAMES_ROOT_COLLECTION = "TMF Mesh Names"

_OPTIONAL_MESHES_FOLD = frozenset(n.casefold() for n in OPTIONAL_MESHES)

EXPORT_HELPER_BLACKLIST = frozenset({
    "maxbox",
})

MIN_PROJSHAD_FOOTPRINT = 1.0
MIN_LIGHTFPROJ_EXTENT = 0.5

# Forever defaults (used when no profile passed)
ABS_Y_MM = (-3.0, 3.0)
ABS_Z_MM = (-0.3, 2.2)

VERTEX_LIMITS = dict(TMF_VERTEX_LIMITS)

MAX_MESH_VERTICES = 65_535

TRANSFORM_TOLERANCE = 1e-4
ORIGIN_TOLERANCE = 1e-5
MESH_TYPES = {"MESH", "CURVE", "SURFACE", "FONT", "META"}


def _strip_blender_suffix(name):
    return strip_blender_suffix(name)


def is_optional_light_helper(name, profile=None):
    """True for light flare helpers (any common casing / .001 suffix)."""
    if profile is not None:
        return profile.is_optional_light_helper(name)
    return _strip_blender_suffix(name).casefold() in _OPTIONAL_MESHES_FOLD


def is_export_blacklisted(name):
    """True if this object must never be written to the .3ds (any casing / .001)."""
    return _strip_blender_suffix(name).casefold() in EXPORT_HELPER_BLACKLIST


def is_projector_mesh(name, profile=None):
    """True for shadow / headlight projector meshes."""
    if profile is not None:
        return profile.is_projector_mesh(name)
    folded = _strip_blender_suffix(name).casefold()
    return folded == "projshad" or folded.startswith("lightfproj") or folded == "fakeshad"


def subject_to_strict_extents(name, profile=None):
    """
    Strict MaxBox checks apply to car body / wheel meshes only.

    Projectors and light helpers are excluded (large shadow planes / flare origins).
    """
    if profile is not None:
        return profile.subject_to_strict_extents(name)
    if is_export_blacklisted(name):
        return False
    if is_projector_mesh(name) or is_optional_light_helper(name):
        return False
    return True


def mesh_export_names(profile=None):
    """Object names that receive a full mesh chunk in the .3ds."""
    if profile is not None:
        return profile.mesh_export_names()
    return (
        frozenset(RECOMMENDED_MESHES)
        | frozenset(OPTIONAL_CAR_MESHES)
        | frozenset(PROJECTOR_MESHES)
    )


@dataclass
class ValidationResult:
    ok: bool = True
    format_ok: bool = True
    errors: list = field(default_factory=list)
    format_errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def add_error(self, message):
        """Strict-only blocker (MaxBox extents). Skipped when Strict is off."""
        self.ok = False
        self.errors.append(message)

    def add_format_error(self, message):
        """Hard format blocker — always cancels export (Strict on or off)."""
        self.format_ok = False
        self.format_errors.append(message)

    def add_warning(self, message):
        """Advisory only — never blocks Strict or export."""
        self.warnings.append(message)


def to_tmf_mm(value):
    """Coordinate as written to the .3ds (TMF Maxbox millimeters)."""
    return value


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
    """Count vertices that are not referenced by any polygon."""
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

    if not any(used):
        try:
            for tri in mesh.loop_triangles:
                for vi in tri.vertices:
                    if 0 <= vi < len(used):
                        used[vi] = True
        except (AttributeError, ReferenceError):
            pass

    return sum(1 for flag in used if not flag)


def check_absolute_extents_mm(scene, mesh, ob=None, profile=None):
    """
    Return error suffixes if any vertex is outside the profile MaxBox.

    Export mesh copies are world-baked; vert.co is already in world space.
    """
    verts = _safe_mesh_vertices(mesh)
    if verts is None or len(verts) == 0:
        return ["has no evaluable mesh geometry"]

    if profile is None:
        abs_x = None
        abs_y = ABS_Y_MM
        abs_z = ABS_Z_MM
        check_x = False
    else:
        abs_x = profile.abs_x
        abs_y = profile.abs_y
        abs_z = profile.abs_z
        check_x = profile.check_abs_x

    y_min, y_max = abs_y
    z_min, z_max = abs_z
    errors = []
    worst = {
        "x_low": None,
        "x_high": None,
        "y_low": None,
        "y_high": None,
        "z_low": None,
        "z_high": None,
    }

    for vert in verts:
        co = vert.co
        x_mm = to_tmf_mm(co.x)
        y_mm = to_tmf_mm(co.y)
        z_mm = to_tmf_mm(co.z)

        if check_x and abs_x is not None:
            x_min, x_max = abs_x
            if x_mm < x_min - TRANSFORM_TOLERANCE:
                if worst["x_low"] is None or x_mm < worst["x_low"]:
                    worst["x_low"] = x_mm
            elif x_mm > x_max + TRANSFORM_TOLERANCE:
                if worst["x_high"] is None or x_mm > worst["x_high"]:
                    worst["x_high"] = x_mm

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

    if check_x and abs_x is not None:
        x_min, x_max = abs_x
        if worst["x_low"] is not None:
            errors.append(
                f"X vertex {worst['x_low']:.4f} mm is below absolute min {x_min} mm"
            )
        if worst["x_high"] is not None:
            errors.append(
                f"X vertex {worst['x_high']:.4f} mm is above absolute max {x_max} mm"
            )
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


def count_export_vertices(mesh_objects, exclude_damage=False):
    """Count vertices the same way the exporter will after triangulation/UV split."""
    from .exporter import count_mesh_export_vertices

    total = 0
    for ob, mesh in mesh_objects:
        if mesh is None:
            continue
        if exclude_damage:
            _base, is_dmg = strip_damage_prefix(ob.name)
            if is_dmg:
                continue
        total += count_mesh_export_vertices(mesh)
    return total


def count_mesh_export_vertices_safe(mesh):
    """Per-mesh export vertex count (after UV splits), or 0 if unavailable."""
    from .exporter import count_mesh_export_vertices

    if mesh is None:
        return 0
    return count_mesh_export_vertices(mesh)


def _local_y_world_up_dot(ob):
    """How much the object's local +Y aligns with world +Z (Blender up)."""
    from mathutils import Vector

    y_axis = ob.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))
    if y_axis.length < TRANSFORM_TOLERANCE:
        return 0.0
    y_axis.normalize()
    return float(y_axis.z)


def _check_damage_morph_twins(mesh_objects, result):
    """Warn when TM2 _damage mesh vert count differs from undamaged twin."""
    by_base = {}
    for ob, mesh in mesh_objects:
        base, is_dmg = strip_damage_prefix(ob.name)
        key = base.casefold()
        by_base.setdefault(key, {"undamaged": None, "damaged": None})
        entry = by_base[key]
        try:
            count = count_mesh_export_vertices_safe(mesh)
        except Exception:
            count = None
        if is_dmg:
            entry["damaged"] = (ob.name, count)
        else:
            entry["undamaged"] = (ob.name, count)

    for _key, pair in by_base.items():
        und = pair["undamaged"]
        dmg = pair["damaged"]
        if und is None or dmg is None:
            continue
        und_name, und_count = und
        dmg_name, dmg_count = dmg
        if und_count is None or dmg_count is None:
            continue
        if und_count != dmg_count:
            result.add_warning(
                f"{dmg_name}: damage morph has {dmg_count} verts but "
                f"{und_name} has {und_count} — indices must match for morphing"
            )


def validate_export(context, mesh_objects, poly_target, profile=None):
    """
    Validate collected export meshes for the active game profile.

    Hard format blockers always cancel export (even Strict off):
    - Any single mesh exceeding MAX_MESH_VERTICES (65,535)

    Strict blockers (when Strict on): MaxBox extents for body/wheel meshes.
    """
    if profile is None:
        profile = profile_from_context(context)

    result = ValidationResult()
    scene = context.scene
    shadow_name = profile.shadow_mesh_name.casefold()

    checked = set()
    for ob, mesh in mesh_objects:
        if ob.name in checked:
            continue
        checked.add(ob.name)

        verts = _safe_mesh_vertices(mesh)
        if verts is None or len(verts) == 0:
            if subject_to_strict_extents(ob.name, profile):
                result.add_error(f"{ob.name}: has no evaluable mesh geometry")
            else:
                result.add_warning(f"{ob.name}: has no evaluable mesh geometry")
            continue

        if not _scale_is_identity(ob):
            result.add_warning(
                f"{ob.name}: unapplied scale {tuple(round(s, 4) for s in ob.scale)} "
                f"(Apply Scale recommended)"
            )

        if is_projector_mesh(ob.name, profile) or is_optional_light_helper(ob.name, profile):
            up_dot = _local_y_world_up_dot(ob)
            base = _strip_blender_suffix(ob.name)
            if base.casefold() == shadow_name:
                if up_dot < 0.7:
                    result.add_warning(
                        f"{ob.name}: local Y should point up "
                        f"(world-up alignment {up_dot:.2f}; "
                        f"use Helpers → {profile.shadow_mesh_name} or rotate so Y is up)"
                    )
            elif abs(up_dot) < 0.15 and base.casefold().startswith("lightfproj"):
                result.add_warning(
                    f"{ob.name}: local Y is nearly horizontal "
                    f"(world-up alignment {up_dot:.2f})"
                )

        if subject_to_strict_extents(ob.name, profile):
            try:
                for msg in check_absolute_extents_mm(scene, mesh, ob, profile=profile):
                    result.add_error(f"{ob.name}: {msg}")
            except Exception as exc:
                result.add_error(f"{ob.name}: absolute extent check failed ({exc})")

        try:
            mesh_vert_count = count_mesh_export_vertices_safe(mesh)
        except Exception as exc:
            result.add_warning(f"{ob.name}: per-mesh vertex count failed ({exc})")
            mesh_vert_count = 0
        if mesh_vert_count > MAX_MESH_VERTICES:
            result.add_format_error(
                f"{ob.name}: {mesh_vert_count} vertices exceeds per-mesh limit "
                f"of {MAX_MESH_VERTICES} (3DS uint16 — split the mesh)"
            )

        if is_projector_mesh(ob.name, profile):
            dims = ob.dimensions
            footprint = max(float(dims.x), float(dims.y), float(dims.z))
            base = _strip_blender_suffix(ob.name)
            if base.casefold() == shadow_name:
                if footprint < MIN_PROJSHAD_FOOTPRINT:
                    result.add_warning(
                        f"{ob.name}: footprint {footprint:.4f} too small "
                        f"(need ≥ {MIN_PROJSHAD_FOOTPRINT})"
                    )
            elif footprint < MIN_LIGHTFPROJ_EXTENT:
                result.add_warning(
                    f"{ob.name}: extent {footprint:.4f} too small "
                    f"(need ≥ {MIN_LIGHTFPROJ_EXTENT})"
                )

    for ob, _mesh in mesh_objects:
        base = _strip_blender_suffix(ob.name)
        if base not in profile.origin_mesh_names:
            continue
        loc = ob.location
        if (
            abs(loc.x) > ORIGIN_TOLERANCE
            or abs(loc.y) > ORIGIN_TOLERANCE
            or abs(loc.z) > ORIGIN_TOLERANCE
        ):
            result.add_warning(
                f"{base}: origin preferably at (0, 0, 0), found "
                f"({loc.x:.6f}, {loc.y:.6f}, {loc.z:.6f})"
            )

    if profile.allow_damage_prefix:
        _check_damage_morph_twins(mesh_objects, result)

    if not mesh_objects:
        result.add_error("No objects selected for export")

    return result
