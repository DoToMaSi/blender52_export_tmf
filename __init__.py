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
    material_utils,
    tmf_validation,
)

_MODULES = (
    format_3ds,
    material_utils,
    tmf_validation,
    addon_info,
    exporter,
    export_operator,
)

if _needs_reload:
    import importlib

    for mod in _MODULES:
        importlib.reload(mod)


def register():
    export_operator.register()


def unregister():
    export_operator.unregister()
    # Drop mutable 3DS name tables so a reinstall / F8 reload cannot leak state.
    try:
        format_3ds.reset_name_tables()
    except Exception:
        pass
