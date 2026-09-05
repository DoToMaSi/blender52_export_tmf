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
from .game_profiles import GAME_TARGET_ITEMS, get_profile
from .importer import do_import


def _imported_shadow(names):
    for n in names:
        base = n.rsplit(".", 1)[0] if "." in n and n.rsplit(".", 1)[1].isdigit() else n
        if base.casefold() in ("projshad", "fakeshad"):
            return base
    return None


class Import_tmf(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import 3DS model for TrackMania Forever or TrackMania 2 (round-trip)"""

    bl_idname = "import_scene.tmf"
    bl_label = "Import 3DS for TrackMania (.3ds)"
    bl_options = {"PRESET", "UNDO"}

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

    prepare_scene: bpy.props.BoolProperty(
        name="Prepare Scene",
        description=(
            "Switch the Blender workspace to car scale: Metric units with unit scale "
            "1.0 (1 Blender unit ≈ 1 mm), and tightened viewport clips. "
            "Enable only on a clean file dedicated to car editing"
        ),
        default=False,
    )

    create_maxbox: bpy.props.BoolProperty(
        name="Create MaxBox",
        description=(
            "Add the wire MaxBox guide for the selected game when none exists. "
            "Never exported"
        ),
        default=True,
    )

    create_name_collections: bpy.props.BoolProperty(
        name="Create Name Collections",
        description=(
            "Add empty Outliner collections for every canonical mesh name for the "
            "selected game. Collections are never exported"
        ),
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "game_target")
        layout.prop(self, "prepare_scene")
        layout.prop(self, "create_maxbox")
        layout.prop(self, "create_name_collections")

    def execute(self, context):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        start = time.time()
        profile = get_profile(self.game_target)
        try:
            context.window.cursor_set("WAIT")
            result = do_import(
                context,
                filepath,
                prepare_workspace=self.prepare_scene,
                create_maxbox=self.create_maxbox,
                create_name_collections=self.create_name_collections,
                game_target=self.game_target,
                profile=profile,
            )
        except Exception as exc:
            self.report({"ERROR"}, f"Import failed: {exc}")
            raise
        finally:
            context.window.cursor_set("DEFAULT")

        n = len(result["objects"])
        elapsed = time.time() - start
        msg = (
            f"Imported {n} objects ({profile.id}) — "
            f"{ADDON_NAME} v{ADDON_VERSION} ({elapsed:.2f}s)"
        )
        self.report({"INFO"}, msg)
        shadow = _imported_shadow(result["objects"])
        if result.get("projshad_restored") and shadow:
            self.report(
                {"INFO"},
                f"{shadow} restored to flat Blender ground orientation",
            )
        elif shadow:
            self.report({"INFO"}, f"{shadow} imported flat (hub rotation cleared)")
        maxbox_info = result.get("maxbox")
        if maxbox_info and maxbox_info.get("created_maxbox"):
            self.report({"INFO"}, f"Created {maxbox_info['maxbox']} scale guide")
        coll_info = result.get("collections")
        if coll_info and coll_info.get("created"):
            self.report(
                {"INFO"},
                f"Added {len(coll_info['created'])} name collections under "
                f"{profile.names_root_collection}",
            )
        elif self.prepare_scene:
            self.report({"INFO"}, "Workspace units and view clips applied")
        if result["skipped"]:
            self.report({"WARNING"}, f"Skipped: {', '.join(result['skipped'][:5])}")
        print(f"\n[{ADDON_NAME} v{ADDON_VERSION}] {msg}")
        print(filepath)
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(Import_tmf.bl_idname, text="3DS for TrackMania (.3ds)")


def register():
    bpy.utils.register_class(Import_tmf)
    bpy.types.TOPBAR_MT_file_import.append(menu_func)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func)
    bpy.utils.unregister_class(Import_tmf)
