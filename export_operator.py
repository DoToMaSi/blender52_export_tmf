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
from .exporter import cleanup_mesh_objects, collect_mesh_data, do_export
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
            "Export selected objects only. Required body/wheel meshes are still "
            "included when visible so they cannot be dropped by accident"
        ),
        default=False,
    )

    use_strict: bpy.props.BoolProperty(
        name="Strict",
        description=(
            "Enforce TrackMania Forever / Nations / United car-geometry rules before writing "
            "the .3ds file. When enabled, export is blocked unless all of the following pass: "
            "exact required mesh names (sBody, dBody, gBody, and eight wheel parts); "
            "sBody origin at (0, 0, 0); applied scale/rotation on required meshes; "
            "no loose/disconnected vertices; absolute world extents Y in [-3, 3] mm and "
            "Z in [-0.3, 2.2] mm; vertex count within Poly Target. "
            "ProjShad / LightFProj / MaxBox are never exported (engine uses .dds / guide). "
            "Disable Strict to test incomplete WIP scenes; the game importer may still fail "
            "silently on invalid files"
        ),
        default=True,
    )

    use_verbose: bpy.props.BoolProperty(
        name="Verbose Log",
        description=(
            "Write a detailed System Console report and a sidecar .tmf-export.log next to "
            "the .3ds: per-object transforms/bounds, exact 3DS material names + mapfiles, "
            "face material refs, 2.79-style name comparison, and a fix checklist. "
            "Open Window → Toggle System Console"
        ),
        default=True,
    )

    poly_target: bpy.props.EnumProperty(
        name="Poly Target",
        description="Vertex budget for the exported car geometry (used by Strict validation)",
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

        mesh_objects = []
        empty_objects = []
        try:
            mesh_objects, empty_objects, material_dict, texture_info = collect_mesh_data(
                context,
                self.use_selection,
                verbose=verbose,
                log_lines=log_lines,
            )

            if not mesh_objects and not empty_objects:
                self.report({"ERROR"}, "Nothing to export (no allowlisted meshes found)")
                return {"CANCELLED"}

            if self.use_strict:
                validation = validate_export(
                    context,
                    mesh_objects,
                    self.poly_target,
                )
                if not validation.ok:
                    if verbose:
                        print("----- Strict validation FAILED -----")
                        log_lines.append("----- Strict validation FAILED -----")
                        for error in validation.errors:
                            line = f"  [ERR] {error}"
                            print(line)
                            log_lines.append(line)
                    for error in validation.errors[:8]:
                        self.report({"ERROR"}, error)
                    if len(validation.errors) > 8:
                        self.report(
                            {"ERROR"},
                            f"...and {len(validation.errors) - 8} more validation errors",
                        )
                    return {"CANCELLED"}
                if verbose:
                    print("----- Strict validation OK -----")
                    log_lines.append("----- Strict validation OK -----")
            else:
                self.report(
                    {"WARNING"},
                    "Strict validation off — incomplete TMF geometry may fail in-game",
                )

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
            finally:
                context.window.cursor_set("DEFAULT")
        except Exception as exc:
            self.report({"ERROR"}, f"Export failed: {exc}")
            raise
        finally:
            cleanup_mesh_objects(mesh_objects)

        elapsed = time.time() - start_time
        names = sorted({ob.name for ob, _ in mesh_objects} | {ob.name for ob in empty_objects})
        print(f"[{ADDON_NAME} v{ADDON_VERSION}] finished export in {elapsed:.3f} seconds")
        print(f"Objects ({len(names)}): {', '.join(names)}")
        print(filepath)
        if verbose:
            print("_____END VERBOSE_____")
            log_path = filepath.rsplit(".", 1)[0] + ".tmf-export.log"
            self.report({"INFO"}, f"Verbose log: {log_path}")
        self.report(
            {"INFO"},
            f"Exported {len(names)} objects — {ADDON_NAME} v{ADDON_VERSION}",
        )
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(Export_tmf.bl_idname, text="3DS for TMF (.3ds)")


def register():
    bpy.utils.register_class(Export_tmf)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)


def unregister():
    bpy.utils.unregister_class(Export_tmf)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)
