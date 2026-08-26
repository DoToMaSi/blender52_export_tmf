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

from . import export_operator

if _needs_reload:
    import importlib

    export_operator = importlib.reload(export_operator)


def register():
    export_operator.register()


def unregister():
    export_operator.unregister()
