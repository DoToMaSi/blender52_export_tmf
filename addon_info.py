# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

from pathlib import Path
import tomllib

_manifest_path = Path(__file__).parent / "blender_manifest.toml"
with _manifest_path.open("rb") as _manifest_file:
    _manifest = tomllib.load(_manifest_file)

ADDON_ID = _manifest["id"]
ADDON_NAME = _manifest["name"]
ADDON_VERSION = _manifest["version"]
