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


class TMF_PG_settings(bpy.types.PropertyGroup):
    poly_target: bpy.props.EnumProperty(
        name="Poly Target",
        items=(
            ("HIGH", "High Poly", "Up to 100,000 vertices"),
            ("LOW", "Low Poly", "Up to 3,600 vertices"),
        ),
        default="HIGH",
    )
    use_selection: bpy.props.BoolProperty(
        name="Selection Only",
        default=False,
    )
    replace_helpers: bpy.props.BoolProperty(
        name="Replace Existing Helpers",
        default=False,
    )
    last_validation: bpy.props.StringProperty(
        name="Last Validation",
        default="",
        options={"HIDDEN"},
    )


class VIEW3D_PT_tmf(bpy.types.Panel):
    """TrackMania Forever authoring tools"""

    bl_label = "TrackMania Forever"
    bl_idname = "VIEW3D_PT_tmf"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "TMF"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.tmf_settings

        layout.label(text=f"{ADDON_NAME} v{ADDON_VERSION}")

        box = layout.box()
        box.label(text="Scene")
        box.operator("tmf.prepare_scene", icon="SCENE_DATA")

        box = layout.box()
        box.label(text="Validate")
        box.prop(settings, "poly_target")
        box.prop(settings, "use_selection")
        op = box.operator("tmf.validate_scene", icon="CHECKMARK")
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
        op = row.operator("tmf.add_projshad", text="ProjShad")
        op.replace = settings.replace_helpers
        op = row.operator("tmf.add_lightfproj", text="LightFProj")
        op.replace = settings.replace_helpers
        op = box.operator("tmf.add_light_helpers", text="Light FL/FR/RL/RR")
        op.replace = settings.replace_helpers
        op = box.operator("tmf.add_all_helpers", icon="ADD", text="Add All Helpers")
        op.replace = settings.replace_helpers

        box = layout.box()
        box.label(text="Import / Export")
        box.operator("import_scene.tmf", text="Import 3DS for TMF", icon="IMPORT")
        box.operator("export_scene.tmf", text="Export 3DS for TMF", icon="EXPORT")


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
