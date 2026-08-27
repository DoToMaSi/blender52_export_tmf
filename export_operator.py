# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

import time

import bpy
import bpy_extras

from .addon_info import ADDON_NAME, ADDON_VERSION
from .exporter import (
    cleanup_mesh_objects,
    collect_mesh_data,
    do_export,
    write_verbose_log,
)
from .format_3ds import reset_name_tables
from .tmf_validation import validate_export


class Export_tmf(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    """Export 3DS model for TrackMania Forever"""

    bl_idname = "export_scene.tmf"
    bl_label = "Export 3DS for TMF (.3ds)"
    bl_options = {"PRESET"}

    filename_ext = ".3ds"
    filter_glob: bpy.props.StringProperty(
        default="*.3ds",
        options={"HIDDEN"},
    )

    use_selection: bpy.props.BoolProperty(
        name="Selection Only",
        description=(
            "Export only selected visible objects — nothing is force-included. "
            "Missing classic United parts are warnings only (Forever accepts partial cars)"
        ),
        default=False,
    )

    use_strict: bpy.props.BoolProperty(
        name="Strict",
        description=(
            "Block export only when car body/wheel world vertices fall outside the TMF "
            "MaxBox (Y in [-3, 3] mm, Z in [-0.3, 2.2] mm). Forever does not require a "
            "full United mesh set — missing parts, loose verts, scale, ProjShad, and "
            "vertex budget are always reported as warnings and never block Strict. "
            "ProjShad / light helpers are excluded from MaxBox checks (large shadow "
            "planes are valid). Rotation is not checked except via resulting world verts"
        ),
        default=True,
    )

    use_verbose: bpy.props.BoolProperty(
        name="Verbose Log",
        description=(
            "Write a detailed .tmf-export.log next to the .3ds (full detail) and a short "
            "System Console summary. Prefer the log file over the console — flooding the "
            "Windows console can freeze Blender"
        ),
        default=True,
    )

    poly_target: bpy.props.EnumProperty(
        name="Poly Target",
        description=(
            "Advisory vertex budget (warnings only — does not block Strict). "
            "High ≈ MainBodyHigh.Solid.gbx, Low ≈ MainBody.Solid.gbx"
        ),
        items=(
            ("HIGH", "High Poly", "Up to 100,000 vertices (MainBodyHigh.Solid.gbx)"),
            ("LOW", "Low Poly", "Up to 3,600 vertices (MainBody.Solid.gbx)"),
        ),
        default="HIGH",
    )

    def execute(self, context):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        start_time = time.time()
        verbose = self.use_verbose
        log_lines = []
        mesh_objects = []
        empty_objects = []
        result = {"CANCELLED"}
        export_ok = False

        print(f"\n_____START_____ [{ADDON_NAME} v{ADDON_VERSION}]")
        if verbose:
            header = (
                f"Options: selection={self.use_selection}  "
                f"strict={self.use_strict}  poly_target={self.poly_target}  "
                f"verbose={verbose}"
            )
            print(header)
            log_lines.append(f"_____START_____ [{ADDON_NAME} v{ADDON_VERSION}]")
            log_lines.append(header)

        try:
            mesh_objects, empty_objects, material_dict, texture_info = collect_mesh_data(
                context,
                self.use_selection,
                verbose=verbose,
                log_lines=log_lines,
            )

            if not mesh_objects and not empty_objects:
                self.report({"ERROR"}, "Nothing to export (no allowlisted meshes found)")
                if verbose:
                    log_lines.append("Nothing to export (no allowlisted meshes found)")
                return {"CANCELLED"}

            validation = validate_export(
                context,
                mesh_objects,
                self.poly_target,
            )

            # Soft advisories always (Strict on or off).
            if validation.warnings:
                if verbose:
                    print("----- Validation warnings -----")
                    log_lines.append("----- Validation warnings -----")
                    for warn in validation.warnings:
                        line = f"  [WARN] {warn}"
                        print(line)
                        log_lines.append(line)
                for warn in validation.warnings[:8]:
                    self.report({"WARNING"}, warn)
                if len(validation.warnings) > 8:
                    self.report(
                        {"WARNING"},
                        f"...and {len(validation.warnings) - 8} more warnings",
                    )

            if self.use_strict:
                if not validation.ok:
                    if verbose:
                        print("----- Strict MaxBox FAILED -----")
                        log_lines.append("----- Strict MaxBox FAILED -----")
                        for error in validation.errors:
                            line = f"  [ERR] {error}"
                            print(line)
                            log_lines.append(line)
                    for error in validation.errors[:8]:
                        self.report({"ERROR"}, error)
                    if len(validation.errors) > 8:
                        self.report(
                            {"ERROR"},
                            f"...and {len(validation.errors) - 8} more MaxBox errors",
                        )
                    return {"CANCELLED"}
                if verbose:
                    print("----- Strict MaxBox OK -----")
                    log_lines.append("----- Strict MaxBox OK -----")
            elif verbose:
                log_lines.append(
                    "Strict off — MaxBox errors (if any) were not enforced"
                )
                if validation.errors:
                    for error in validation.errors:
                        line = f"  [ERR skipped] {error}"
                        print(line)
                        log_lines.append(line)
                    for error in validation.errors[:4]:
                        self.report({"WARNING"}, f"[Strict off] {error}")

            context.window.cursor_set("WAIT")
            try:
                do_export(
                    context,
                    filepath,
                    mesh_objects,
                    empty_objects,
                    material_dict,
                    verbose=verbose,
                    texture_info=texture_info,
                    log_lines=log_lines,
                )
                export_ok = True
            finally:
                context.window.cursor_set("DEFAULT")

            elapsed = time.time() - start_time
            names = sorted(
                {ob.name for ob, _ in mesh_objects} | {ob.name for ob in empty_objects}
            )
            print(f"[{ADDON_NAME} v{ADDON_VERSION}] finished export in {elapsed:.3f} seconds")
            print(f"Objects ({len(names)}): {', '.join(names)}")
            print(filepath)
            if verbose:
                log_lines.append(
                    f"[{ADDON_NAME} v{ADDON_VERSION}] finished export in {elapsed:.3f} seconds"
                )
                log_lines.append(f"Objects ({len(names)}): {', '.join(names)}")
                log_lines.append(filepath)
            self.report(
                {"INFO"},
                f"Exported {len(names)} objects — {ADDON_NAME} v{ADDON_VERSION}",
            )
            result = {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, f"Export failed: {exc}")
            if verbose:
                log_lines.append(f"Export failed: {exc}")
            raise
        finally:
            cleanup_mesh_objects(mesh_objects)
            reset_name_tables()
            if verbose:
                log_lines.append("_____END VERBOSE_____")
                print("_____END VERBOSE_____")
                log_path = write_verbose_log(filepath, log_lines)
                if log_path and export_ok:
                    self.report({"INFO"}, f"Verbose log: {log_path}")
                elif log_path:
                    print(f"Verbose log: {log_path}")

        return result


def menu_func(self, context):
    self.layout.operator(Export_tmf.bl_idname, text="3DS for TMF (.3ds)")


def register():
    bpy.utils.register_class(Export_tmf)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)


def unregister():
    bpy.utils.unregister_class(Export_tmf)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)
    reset_name_tables()
