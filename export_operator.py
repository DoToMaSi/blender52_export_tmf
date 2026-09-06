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
from .game_profiles import GAME_TARGET_ITEMS, get_profile
from .tmf_validation import validate_export


def _export_poly_items(self, context):
    return get_profile(getattr(self, "game_target", "TMF")).poly_target_items


class Export_tmf(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    """Export 3DS model for TrackMania Forever or TrackMania 2"""

    bl_idname = "export_scene.tmf"
    bl_label = "Export 3DS for TrackMania (.3ds)"
    bl_options = {"PRESET"}

    filename_ext = ".3ds"
    filter_glob: bpy.props.StringProperty(
        default="*.3ds",
        options={"HIDDEN"},
    )

    game_target: bpy.props.EnumProperty(
        name="Game Target",
        items=GAME_TARGET_ITEMS,
        default="TMF",
    )

    use_selection: bpy.props.BoolProperty(
        name="Selection Only",
        description=(
            "Export only selected visible objects — nothing is force-included"
        ),
        default=False,
    )

    use_strict: bpy.props.BoolProperty(
        name="Strict",
        description=(
            "Block export when body/wheel world vertices fall outside the game MaxBox. "
            "Per-mesh vertex overflow (over 65,535 — 3DS uint16) always blocks export "
            "even when Strict is off. Warnings always cover unknown/invalid names, "
            "scale, locations, and shadow projector rotation (local Y should point up)"
        ),
        default=True,
    )

    use_verbose: bpy.props.BoolProperty(
        name="Verbose Log",
        description=(
            "Write a detailed .tmf-export.log next to the .3ds (full detail) and a short "
            "System Console summary"
        ),
        default=True,
    )

    poly_target: bpy.props.EnumProperty(
        name="Poly Target",
        description="Advisory whole-car vertex budget (does not block export)",
        items=_export_poly_items,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "game_target")
        layout.prop(self, "use_selection")
        layout.prop(self, "use_strict")
        layout.prop(self, "poly_target")
        layout.prop(self, "use_verbose")

    def execute(self, context):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        start_time = time.time()
        verbose = self.use_verbose
        log_lines = []
        mesh_objects = []
        empty_objects = []
        result = {"CANCELLED"}
        export_ok = False
        profile = get_profile(self.game_target)

        print(f"\n_____START_____ [{ADDON_NAME} v{ADDON_VERSION}]")
        if verbose:
            header = (
                f"Options: game={self.game_target}  selection={self.use_selection}  "
                f"strict={self.use_strict}  poly_target={self.poly_target}  "
                f"verbose={verbose}"
            )
            print(header)
            log_lines.append(f"_____START_____ [{ADDON_NAME} v{ADDON_VERSION}]")
            log_lines.append(header)

        try:
            mesh_objects, empty_objects, material_dict, texture_info, name_warnings = (
                collect_mesh_data(
                    context,
                    self.use_selection,
                    verbose=verbose,
                    log_lines=log_lines,
                    game_target=self.game_target,
                    profile=profile,
                )
            )

            if not mesh_objects and not empty_objects:
                self.report({"ERROR"}, "Nothing to export (no allowlisted meshes found)")
                if verbose:
                    log_lines.append("Nothing to export (no allowlisted meshes found)")
                if name_warnings:
                    for warn in name_warnings[:8]:
                        self.report({"WARNING"}, warn)
                return {"CANCELLED"}

            validation = validate_export(
                context,
                mesh_objects,
                self.poly_target,
                profile=profile,
            )
            # Unknown/invalid names are always advisory (Strict on or off).
            for warn in name_warnings:
                validation.add_warning(warn)

            # Soft advisories always (Strict on or off), including unknown names.
            if validation.warnings:
                print("----- Validation warnings -----")
                if verbose:
                    log_lines.append("----- Validation warnings -----")
                for warn in validation.warnings:
                    line = f"  [WARN] {warn}"
                    print(line)
                    if verbose:
                        log_lines.append(line)
                for warn in validation.warnings[:8]:
                    self.report({"WARNING"}, warn)
                if len(validation.warnings) > 8:
                    self.report(
                        {"WARNING"},
                        f"...and {len(validation.warnings) - 8} more warnings",
                    )

            # Hard 3DS format limits — always block (Strict on or off).
            if not validation.format_ok:
                if verbose:
                    print("----- Format limit FAILED -----")
                    log_lines.append("----- Format limit FAILED -----")
                    for error in validation.format_errors:
                        line = f"  [ERR] {error}"
                        print(line)
                        log_lines.append(line)
                for error in validation.format_errors[:8]:
                    self.report({"ERROR"}, error)
                if len(validation.format_errors) > 8:
                    self.report(
                        {"ERROR"},
                        f"...and {len(validation.format_errors) - 8} more format errors",
                    )
                return {"CANCELLED"}

            if self.use_strict:
                if not validation.ok:
                    if verbose:
                        print("----- Strict FAILED -----")
                        log_lines.append("----- Strict FAILED -----")
                        for error in validation.errors:
                            line = f"  [ERR] {error}"
                            print(line)
                            log_lines.append(line)
                    for error in validation.errors[:8]:
                        self.report({"ERROR"}, error)
                    if len(validation.errors) > 8:
                        self.report(
                            {"ERROR"},
                            f"...and {len(validation.errors) - 8} more Strict errors",
                        )
                    return {"CANCELLED"}
                if verbose:
                    print("----- Strict OK -----")
                    log_lines.append("----- Strict OK -----")
            elif verbose:
                log_lines.append(
                    "Strict off — MaxBox errors (if any) were not enforced "
                    "(per-mesh 65,535 vertex limit still enforced)"
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
                    profile=profile,
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
    self.layout.operator(Export_tmf.bl_idname, text="3DS for TrackMania (.3ds)")


def register():
    bpy.utils.register_class(Export_tmf)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)


def unregister():
    bpy.utils.unregister_class(Export_tmf)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)
    reset_name_tables()
