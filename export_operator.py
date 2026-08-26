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
        description="Export selected objects only",
        default=True,
    )

    use_strict: bpy.props.BoolProperty(
        name="Strict",
        description=(
            "Enforce TrackMania Forever / Nations / United car-geometry rules before writing "
            "the .3ds file. When enabled, export is blocked unless all of the following pass: "
            "exact required mesh names (sBody, dBody, gBody, and all eight wheel parts), "
            "exact required light Empties (LightFL1–3, LightFR1–3, LightRL, LightRR), "
            "applied scale and rotation on required meshes (location may remain for pivots), "
            "per-object world size within the max box (3 mm X × 6 mm Y × 2.5 mm Z), "
            "vertex count within the selected Poly Target limit, and Diffuse.dds / Details.dds "
            "texture references on paintable vs detail parts. "
            "Disable Strict to test incomplete WIP scenes; the game importer may still fail "
            "silently on invalid files"
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
        print("\n_____START_____")

        mesh_objects = []
        try:
            mesh_objects, empty_objects, material_dict = collect_mesh_data(
                context,
                self.use_selection,
            )

            if not mesh_objects and not empty_objects:
                self.report({"ERROR"}, "Nothing to export (no meshes or empties found)")
                return {"CANCELLED"}

            if self.use_strict:
                validation = validate_export(
                    context,
                    mesh_objects,
                    empty_objects,
                    self.poly_target,
                )
                if not validation.ok:
                    for error in validation.errors[:8]:
                        self.report({"ERROR"}, error)
                    if len(validation.errors) > 8:
                        self.report(
                            {"ERROR"},
                            f"...and {len(validation.errors) - 8} more validation errors",
                        )
                    return {"CANCELLED"}
            else:
                self.report(
                    {"WARNING"},
                    "Strict validation off — incomplete TMF geometry may fail in-game",
                )

            context.window.cursor_set("WAIT")
            try:
                do_export(context, filepath, mesh_objects, empty_objects, material_dict)
            finally:
                context.window.cursor_set("DEFAULT")
        except Exception as exc:
            self.report({"ERROR"}, f"Export failed: {exc}")
            raise
        finally:
            cleanup_mesh_objects(mesh_objects)

        print(f"finished export in {time.time() - start_time:.3f} seconds")
        print(filepath)
        self.report({"INFO"}, f"Exported {filepath}")
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(Export_tmf.bl_idname, text="3DS for TMF (.3ds)")


def register():
    bpy.utils.register_class(Export_tmf)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)


def unregister():
    bpy.utils.unregister_class(Export_tmf)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)
