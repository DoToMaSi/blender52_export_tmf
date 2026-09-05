# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

import bpy

from .addon_info import ADDON_NAME, ADDON_VERSION
from .game_profiles import GAME_TARGET_ITEMS, get_profile


def _poly_target_items(self, context):
    profile = get_profile(getattr(self, "game_target", "TMF"))
    return profile.poly_target_items


class TMF_PG_settings(bpy.types.PropertyGroup):
    game_target: bpy.props.EnumProperty(
        name="Game Target",
        description="Which TrackMania game naming, MaxBox, and textures to use",
        items=GAME_TARGET_ITEMS,
        default="TMF",
    )
    poly_target: bpy.props.EnumProperty(
        name="Poly Target",
        items=_poly_target_items,
    )
    use_selection: bpy.props.BoolProperty(
        name="Selection Only",
        default=False,
    )
    replace_helpers: bpy.props.BoolProperty(
        name="Replace Existing Helpers",
        default=False,
    )
    prepare_create_maxbox: bpy.props.BoolProperty(
        name="Create MaxBox",
        description=(
            "When preparing the scene: create or refresh the wire MaxBox guide "
            "for the selected game. Never exported"
        ),
        default=True,
    )
    prepare_create_collections: bpy.props.BoolProperty(
        name="Create Name Collections",
        description=(
            "When preparing the scene: add empty Outliner collections for every "
            "canonical mesh name for the selected game. Drag meshes in and match "
            "the name — collections are never exported"
        ),
        default=True,
    )
    last_validation: bpy.props.StringProperty(
        name="Last Validation",
        default="",
        options={"HIDDEN"},
    )


class VIEW3D_PT_tmf(bpy.types.Panel):
    """TrackMania Forever / TM2 authoring tools"""

    bl_label = "TrackMania 3DS"
    bl_idname = "VIEW3D_PT_tmf"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "TMF"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.tmf_settings
        profile = get_profile(settings.game_target)

        layout.label(text=f"{ADDON_NAME} v{ADDON_VERSION}")
        layout.prop(settings, "game_target", text="Game")

        box = layout.box()
        box.label(text="Scene")
        box.prop(settings, "prepare_create_maxbox")
        box.prop(settings, "prepare_create_collections")
        box.operator("tmf.prepare_scene", icon="SCENE_DATA")

        box = layout.box()
        box.label(text="Validate")
        box.prop(settings, "poly_target")
        box.prop(settings, "use_selection")
        op = box.operator("tmf.validate_scene", icon="CHECKMARK")
        op.game_target = settings.game_target
        op.poly_target = settings.poly_target
        op.use_selection = settings.use_selection
        if settings.last_validation:
            col = box.column(align=True)
            for line in settings.last_validation.split("\n")[:12]:
                col.label(text=line)

        box = layout.box()
        box.label(text="Helpers")
        box.prop(settings, "replace_helpers")
        row = box.row(align=True)
        if profile.id == "TM2":
            op = row.operator("tmf.add_fakeshad", text="FakeShad")
        else:
            op = row.operator("tmf.add_projshad", text="ProjShad")
        op.replace = settings.replace_helpers
        op = row.operator("tmf.add_lightfproj", text="LightFProj")
        op.replace = settings.replace_helpers
        op = box.operator("tmf.add_light_helpers", text="Light Helpers")
        op.replace = settings.replace_helpers
        op.game_target = settings.game_target
        op = box.operator("tmf.add_all_helpers", icon="ADD", text="Add All Helpers")
        op.replace = settings.replace_helpers
        op.game_target = settings.game_target

        box = layout.box()
        box.label(text="Import / Export")
        op = box.operator("import_scene.tmf", text="Import 3DS", icon="IMPORT")
        op = box.operator("export_scene.tmf", text="Export 3DS", icon="EXPORT")


classes = (
    TMF_PG_settings,
    VIEW3D_PT_tmf,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.tmf_settings = bpy.props.PointerProperty(type=TMF_PG_settings)


def unregister():
    del bpy.types.Scene.tmf_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
