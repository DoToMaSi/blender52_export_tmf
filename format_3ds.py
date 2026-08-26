# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import struct

# Chunk identifiers
PRIMARY = 0x4D4D
OBJECTINFO = 0x3D3D
VERSION = 0x0002
KFDATA = 0xB000

MATERIAL = 45055
OBJECT = 16384

MATNAME = 0xA000
MATAMBIENT = 0xA010
MATDIFFUSE = 0xA020
MATSPECULAR = 0xA030
MATSHINESS = 0xA040
MATSHIN2 = 0xA041

MAT_DIFFUSEMAP = 0xA200
MAT_OPACMAP = 0xA210
MAT_BUMPMAP = 0xA230
MAT_SPECMAP = 0xA204

MATMAPFILE = 0xA300
MAT_MAP_TILING = 0xA351
MAT_MAP_USCALE = 0xA354
MAT_MAP_VSCALE = 0xA356
MAT_MAP_UOFFSET = 0xA358
MAT_MAP_VOFFSET = 0xA35A
MAT_MAP_ANG = 0xA35C

MATTRANS = 0xA050
PCT = 0x0030
MASTERSCALE = 0x0100

RGB1 = 0x0011
RGB2 = 0x0012

OBJECT_MESH = 0x4100
OBJECT_LIGHT = 0x4600
OBJECT_CAMERA = 0x4700
OBJECT_CAM_RANGES = 0x4720

OBJECT_VERTICES = 0x4110
OBJECT_FACES = 0x4120
OBJECT_MATERIAL = 0x4130
OBJECT_UV = 0x4140
OBJECT_SMOOTH = 0x4150
OBJECT_TRANS_MATRIX = 0x4160

KFDATA_KFHDR = 0xB00A
KFDATA_KFSEG = 0xB008
KFDATA_KFCURTIME = 0xB009
KFDATA_OBJECT_NODE_TAG = 0xB002

OBJECT_NODE_ID = 0xB030
OBJECT_NODE_HDR = 0xB010
OBJECT_PIVOT = 0xB013
OBJECT_INSTANCE_NAME = 0xB011
POS_TRACK_TAG = 0xB020
ROT_TRACK_TAG = 0xB021
SCL_TRACK_TAG = 0xB022

BOUNDBOX = 0xB014

SZ_SHORT = 2
SZ_INT = 4
SZ_FLOAT = 4

name_unique = []
name_mapping = {}


def reset_name_tables():
    del name_unique[:]
    name_mapping.clear()


def preview_sane_name(name):
    """Non-mutating 12-char ASCII preview for logs (does not touch name tables)."""
    if name is None:
        return None
    if isinstance(name, bytes):
        name = name.decode("ASCII", "replace")
    return name.encode("ASCII", "replace").decode("ASCII")[:12]


def sane_name(name):
    if isinstance(name, bytes):
        name_key = name.decode("ASCII", "replace")
    else:
        name_key = name

    name_fixed = name_mapping.get(name_key)
    if name_fixed is not None:
        return name_fixed

    new_name_clean = new_name = name_key.encode("ASCII", "replace").decode("ASCII")[:12]
    i = 0

    while new_name in name_unique:
        new_name = f"{new_name_clean}.{i:03d}"
        i += 1
        # Hard cap — a runaway collision loop must never hang Blender.
        if i > 10_000:
            new_name = f"{new_name_clean[:8]}.{i:03d}"[:12]
            break

    name_unique.append(new_name)
    name_mapping[name_key] = new_name = new_name.encode("ASCII", "replace")
    return new_name


def uv_key(uv):
    return round(uv[0], 6), round(uv[1], 6)


class _3ds_ushort:
    __slots__ = ("value",)

    def __init__(self, val=0):
        self.value = val

    def get_size(self):
        return SZ_SHORT

    def write(self, file):
        file.write(struct.pack("<H", self.value & 0xFFFF))

    def __str__(self):
        return str(self.value)


class _3ds_uint:
    __slots__ = ("value",)

    def __init__(self, val):
        self.value = val

    def get_size(self):
        return SZ_INT

    def write(self, file):
        file.write(struct.pack("<I", self.value & 0xFFFFFFFF))

    def __str__(self):
        return str(self.value)


class _3ds_float:
    __slots__ = ("value",)

    def __init__(self, val):
        self.value = val

    def get_size(self):
        return SZ_FLOAT

    def write(self, file):
        file.write(struct.pack("<f", self.value))

    def __str__(self):
        return str(self.value)


class _3ds_string:
    __slots__ = ("value",)

    def __init__(self, val=""):
        if isinstance(val, str):
            val = val.encode("ASCII", "replace")
        self.value = val

    def get_size(self):
        return len(self.value) + 1

    def write(self, file):
        binary_format = f"<{len(self.value) + 1}s"
        file.write(struct.pack(binary_format, self.value))

    def __str__(self):
        return str(self.value)


class _3ds_point_3d:
    __slots__ = ("x", "y", "z")

    def __init__(self, point=(0.0, 0.0, 0.0)):
        self.x, self.y, self.z = point

    def get_size(self):
        return 3 * SZ_FLOAT

    def write(self, file):
        file.write(struct.pack("<3f", self.x, self.y, self.z))

    def __str__(self):
        return f"({self.x}, {self.y}, {self.z})"


class _3ds_point_4d:
    __slots__ = ("x", "y", "z", "w")

    def __init__(self, point=(0.0, 0.0, 0.0, 0.0)):
        self.x, self.y, self.z, self.w = point

    def get_size(self):
        return 4 * SZ_FLOAT

    def write(self, file):
        file.write(struct.pack("<4f", self.x, self.y, self.z, self.w))

    def __str__(self):
        return f"({self.x}, {self.y}, {self.z}, {self.w})"


class _3ds_point_uv:
    __slots__ = ("uv",)

    def __init__(self, point):
        self.uv = point

    def get_size(self):
        return 2 * SZ_FLOAT

    def write(self, file):
        file.write(struct.pack("<2f", self.uv[0], self.uv[1]))

    def __str__(self):
        return f"({self.uv[0]}, {self.uv[1]})"


class _3ds_rgb_color:
    __slots__ = ("r", "g", "b")

    def __init__(self, col):
        if len(col) >= 3:
            self.r, self.g, self.b = col[0], col[1], col[2]
        else:
            self.r = self.g = self.b = 0.0

    def get_size(self):
        return 3

    def write(self, file):
        file.write(struct.pack(
            "<3B",
            int(255 * self.r),
            int(255 * self.g),
            int(255 * self.b),
        ))

    def __str__(self):
        return f"{{{self.r}, {self.g}, {self.b}}}"


class _3ds_face:
    __slots__ = ("vindex",)

    def __init__(self, vindex):
        self.vindex = vindex

    def get_size(self):
        return 4 * SZ_SHORT

    def write(self, file):
        file.write(struct.pack("<4H", self.vindex[0], self.vindex[1], self.vindex[2], 0))

    def __str__(self):
        return f"[{self.vindex[0]} {self.vindex[1]} {self.vindex[2]}]"


class _3ds_array:
    __slots__ = ("values", "size")

    def __init__(self):
        self.values = []
        self.size = SZ_SHORT

    def add(self, item):
        self.values.append(item)
        self.size += item.get_size()

    def get_size(self):
        return self.size

    def validate(self):
        return len(self.values) <= 65535

    def write(self, file):
        _3ds_ushort(len(self.values)).write(file)
        for value in self.values:
            value.write(file)

    def __str__(self):
        return f"({len(self.values)} items)"


class _3ds_named_variable:
    __slots__ = ("value", "name")

    def __init__(self, name, val=None):
        self.name = name
        self.value = val

    def get_size(self):
        if self.value is None:
            return 0
        return self.value.get_size()

    def write(self, file):
        if self.value is not None:
            self.value.write(file)

    def dump(self, indent):
        if self.value is not None:
            print(indent * " ", self.name if self.name else "[unnamed]", " = ", self.value)


class _3ds_chunk:
    __slots__ = ("ID", "size", "variables", "subchunks")

    def __init__(self, chunk_id=0):
        self.ID = _3ds_ushort(chunk_id)
        self.size = _3ds_uint(0)
        self.variables = []
        self.subchunks = []

    def add_variable(self, name, var):
        self.variables.append(_3ds_named_variable(name, var))

    def add_subchunk(self, chunk):
        self.subchunks.append(chunk)

    def get_size(self):
        tmpsize = self.ID.get_size() + self.size.get_size()
        for variable in self.variables:
            tmpsize += variable.get_size()
        for subchunk in self.subchunks:
            tmpsize += subchunk.get_size()
        self.size.value = tmpsize
        return self.size.value

    def validate(self):
        for var in self.variables:
            func = getattr(var.value, "validate", None)
            if func is not None and not func():
                return False

        for chunk in self.subchunks:
            func = getattr(chunk, "validate", None)
            if func is not None and not func():
                return False

        return True

    def write(self, file):
        self.ID.write(file)
        self.size.write(file)
        for variable in self.variables:
            variable.write(file)
        for subchunk in self.subchunks:
            subchunk.write(file)

    def dump(self, indent=0):
        print(indent * " ", f"ID={hex(self.ID.value)!r}", f"size={self.get_size()!r}")
        for variable in self.variables:
            variable.dump(indent + 1)
        for subchunk in self.subchunks:
            subchunk.dump(indent + 1)
