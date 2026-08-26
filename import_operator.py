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
from .importer import do_import


class Import_tmf(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import 3DS model produced by Export 3DS for TMF (round-trip)"""

    bl_idname = "import_scene.tmf"
    bl_label = "Import 3DS for TMF (.3ds)"
    bl_options = {"PRESET", "UNDO"}

    filename_ext = ".3ds"
    filter_glob: bpy.props.StringProperty(
        default="*.3ds",
        options={"HIDDEN"},
    )

    def execute(self, context):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        start = time.time()
        try:
            context.window.cursor_set("WAIT")
            result = do_import(context, filepath)
        except Exception as exc:
            self.report({"ERROR"}, f"Import failed: {exc}")
            raise
        finally:
            context.window.cursor_set("DEFAULT")

        n = len(result["objects"])
        elapsed = time.time() - start
        msg = f"Imported {n} objects — {ADDON_NAME} v{ADDON_VERSION} ({elapsed:.2f}s)"
        self.report({"INFO"}, msg)
        if result["skipped"]:
            self.report({"WARNING"}, f"Skipped: {', '.join(result['skipped'][:5])}")
        print(f"\n[{ADDON_NAME} v{ADDON_VERSION}] {msg}")
        print(filepath)
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(Import_tmf.bl_idname, text="3DS for TMF (.3ds)")


def register():
    bpy.utils.register_class(Import_tmf)
    bpy.types.TOPBAR_MT_file_import.append(menu_func)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func)
    bpy.utils.unregister_class(Import_tmf)
