# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

_needs_reload = "bpy" in locals()

import bpy

from . import (
    addon_info,
    export_operator,
    exporter,
    format_3ds,
    import_operator,
    importer,
    material_utils,
    tmf_helpers,
    tmf_scene,
    tmf_validation,
    ui_panel,
)

_MODULES = (
    format_3ds,
    material_utils,
    tmf_validation,
    addon_info,
    exporter,
    export_operator,
    importer,
    import_operator,
    tmf_scene,
    tmf_helpers,
    ui_panel,
)

if _needs_reload:
    import importlib

    for mod in _MODULES:
        importlib.reload(mod)


def register():
    export_operator.register()
    import_operator.register()
    tmf_scene.register()
    tmf_helpers.register()
    ui_panel.register()


def unregister():
    ui_panel.unregister()
    tmf_helpers.unregister()
    tmf_scene.unregister()
    import_operator.unregister()
    export_operator.unregister()
    # Drop mutable 3DS name tables so a reinstall / F8 reload cannot leak state.
    try:
        format_3ds.reset_name_tables()
    except Exception:
        pass
