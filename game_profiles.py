# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""Per-game naming, MaxBox, poly targets, and texture rules (Forever vs TM2)."""

from dataclasses import dataclass, field


def strip_blender_suffix(name):
    if "." in name and name.rsplit(".", 1)[1].isdigit():
        return name.rsplit(".", 1)[0]
    return name


def strip_damage_prefix(name):
    """TM2 damage morphs use a leading underscore (_dBody)."""
    base = strip_blender_suffix(name)
    if base.startswith("_") and len(base) > 1:
        return base[1:], True
    return base, False


# ---------------------------------------------------------------------------
# Forever (TMF)
# ---------------------------------------------------------------------------

TMF_RECOMMENDED = (
    "sBody",
    "dBody",
    "gBody",
    "dFLWheel",
    "sFLWheel",
    "dFRWheel",
    "sFRWheel",
    "dRLWheel",
    "sRLWheel",
    "dRRWheel",
    "sRRWheel",
)

TMF_OPTIONAL_CAR = (
    "sPilHead",
    "dPilHead",
)

# Suspension / hubs / guards — exported as real meshes (ugghost / United set).
# Previously only listed in the Outliner name guide, so collect skipped them.
TMF_SUSPENSION = (
    "dFLArmBot",
    "dFLArmDir",
    "dFLArmTop",
    "dFLGuard",
    "dFLHub",
    "dFRArmBot",
    "dFRArmDir",
    "dFRArmTop",
    "dFRGuard",
    "dFRHub",
    "dRLArmBot",
    "dRLArmTop",
    "dRLCardan",
    "dRLHub",
    "dRRArmBot",
    "dRRArmTop",
    "dRRCardan",
    "dRRHub",
    # Skin-prefixed variants if authored that way
    "sFLHub",
    "sFRHub",
    "sRLHub",
    "sRRHub",
)

TMF_PROJECTORS = (
    "ProjShad",
    "LightFProj",
)

TMF_LIGHTS = (
    "LightFL1",
    "LightFR1",
    "LightFL2",
    "LightFR2",
    "LightFL3",
    "LightFR3",
    "LightRL",
    "LightRR",
    "FLlight1",
    "FRlight1",
    "FLlight2",
    "FRlight2",
    "FLlight3",
    "FRlight3",
    "RLlight",
    "RRlight",
    "FLLight1",
    "FRLight1",
    "FLLight2",
    "FRLight2",
    "FLLight3",
    "FRLight3",
    "RLLight",
    "RRLight",
)

TMF_NAME_GUIDE = (
    "dBody",
    "dFLArmBot",
    "dFLArmDir",
    "dFLArmTop",
    "dFLGuard",
    "dFLHub",
    "dFLWheel",
    "dFRArmBot",
    "dFRArmDir",
    "dFRArmTop",
    "dFRGuard",
    "dFRHub",
    "dFRWheel",
    "dRLArmBot",
    "dRLArmTop",
    "dRLCardan",
    "dRLHub",
    "dRLWheel",
    "dRRArmBot",
    "dRRArmTop",
    "dRRCardan",
    "dRRHub",
    "dRRWheel",
    "gBody",
    "LightFL1",
    "LightFL2",
    "LightFL3",
    "LightFR1",
    "LightFR2",
    "LightFR3",
    "LightFProj",
    "LightRL",
    "LightRR",
    "ProjShad",
    "dPilHead",
    "sBody",
    "sFLWheel",
    "sFRWheel",
    "sPilHead",
    "sRLWheel",
    "sRRWheel",
)

TMF_VERTEX_LIMITS = {
    "HIGH": 100_000,
    "LOW": 3_600,
}

# ---------------------------------------------------------------------------
# TrackMania 2 (ManiaPlanet) — Nadeo forum + hideou.se tutorial
# ---------------------------------------------------------------------------

_TM2_WHEEL_CORNERS = ("FL", "FR", "RL", "RR")
_TM2_WHEEL_KINDS = ("Wheel", "Hub", "Guard")
_TM2_SUSP = (
    "FLArmBot",
    "FLArmDir",
    "FLArmTop",
    "FLSusp",
    "FRArmBot",
    "FRArmDir",
    "FRArmTop",
    "FRSusp",
    "RLArmBot",
    "RLArmTop",
    "RLCardan",
    "RLSusp",
    "RRArmBot",
    "RRArmTop",
    "RRCardan",
    "RRSusp",
)
# Detachable / animated parts shared by d/s/w (and some g) primitives
_TM2_OPENABLE = ("LDoor", "RDoor", "Hood", "Trunk", "Exhaust")
_TM2_GLASS = (
    "gBody",
    "gFWShield",
    "gRWShield",
    "gLDoor",
    "gRDoor",
    "gHood",
    "gTrunk",
)
# Flame dummies — pivot marks exhaust plume (Exhaust1 … Exhaust8)
_TM2_EXHAUST_HELPERS = tuple(f"Exhaust{i}" for i in range(1, 9))


def _tm2_build_mesh_names():
    names = {
        "sBody",
        "dBody",
        "gBody",
        "pBody",
        "FakeShad",
        "LightFProj",
        "RLLight",
        "RRLight",
        "FLLight",
        "FRLight",
        "LightFL1",
        "LightFR1",
        "LightFL2",
        "LightFR2",
        "LightFL3",
        "LightFR3",
        "LightRL",
        "LightRR",
        "WheelMin",
        *_TM2_EXHAUST_HELPERS,
    }
    for part in _TM2_OPENABLE:
        names.add(f"d{part}")
        names.add(f"s{part}")
        names.add(f"w{part}")
    for g in _TM2_GLASS:
        names.add(g)
    for corner in _TM2_WHEEL_CORNERS:
        for kind in _TM2_WHEEL_KINDS:
            # dFLWheel / wFLWheel (Details vs WheelsDiffuse sheets)
            names.add(f"d{corner}{kind}")
            names.add(f"w{corner}{kind}")
            names.add(f"s{corner}{kind}")
    for susp in _TM2_SUSP:
        names.add(f"d{susp}")
        names.add(susp)
    # Explicit damage morphs for common bodies (any _* twin also accepted at runtime)
    for base in list(names):
        if not base.startswith("_"):
            names.add(f"_{base}")
    return tuple(sorted(names))


TM2_MESH_NAMES = _tm2_build_mesh_names()

TM2_PROJECTORS = (
    "FakeShad",
    "LightFProj",
)

TM2_LIGHTS = (
    "LightFL1",
    "LightFR1",
    "LightFL2",
    "LightFR2",
    "LightFL3",
    "LightFR3",
    "LightRL",
    "LightRR",
    "RLLight",
    "RRLight",
    "FLLight",
    "FRLight",
    "FLLight1",
    "FRLight1",
    *_TM2_EXHAUST_HELPERS,
)

TM2_NAME_GUIDE = tuple(
    sorted(
        {
            "sBody",
            "dBody",
            "pBody",
            "_dBody",
            "dHood",
            "_dHood",
            "dLDoor",
            "_dLDoor",
            "dRDoor",
            "_dRDoor",
            "dTrunk",
            "_dTrunk",
            "dExhaust",
            "sExhaust",
            "wExhaust",
            *_TM2_GLASS,
            "_gBody",
            "_gFWShield",
            "_gRWShield",
            "dFLWheel",
            "dFRWheel",
            "dRLWheel",
            "dRRWheel",
            "wFLWheel",
            "wFRWheel",
            "wRLWheel",
            "wRRWheel",
            "dFLHub",
            "dFRHub",
            "dRLHub",
            "dRRHub",
            "dFLGuard",
            "dFRGuard",
            "dRLGuard",
            "dRRGuard",
            *[f"d{s}" for s in _TM2_SUSP],
            "FakeShad",
            "LightFProj",
            "LightFL1",
            "LightFR1",
            "RLLight",
            "RRLight",
            "WheelMin",
            "Exhaust1",
        }
    )
)

TM2_VERTEX_LIMITS = {
    "VERY_HIGH": 60_000,
    "HIGH": 20_000,
    "LOW": 4_250,
}


@dataclass(frozen=True)
class GameProfile:
    id: str
    label: str
    mesh_chunk_names: frozenset
    optional_light_names: frozenset
    projector_names: frozenset
    name_guide_meshes: tuple
    names_root_collection: str
    # MaxBox guide size in Blender (width X, length Y, height Z)
    maxbox_size: tuple
    # Strict world extents (None = do not check that axis)
    abs_x: tuple | None
    abs_y: tuple
    abs_z: tuple
    vertex_limits: dict
    poly_target_items: tuple
    default_poly_target: str
    origin_mesh_names: frozenset
    shadow_mesh_name: str  # ProjShad or FakeShad
    allow_damage_prefix: bool
    check_abs_x: bool

    _light_fold: frozenset = field(init=False, repr=False)
    _projector_fold: frozenset = field(init=False, repr=False)
    _chunk_fold: frozenset = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(
            self, "_light_fold", frozenset(n.casefold() for n in self.optional_light_names)
        )
        object.__setattr__(
            self,
            "_projector_fold",
            frozenset(n.casefold() for n in self.projector_names),
        )
        object.__setattr__(
            self, "_chunk_fold", frozenset(n.casefold() for n in self.mesh_chunk_names)
        )

    def is_optional_light_helper(self, name):
        base, _dmg = strip_damage_prefix(name)
        return base.casefold() in self._light_fold

    def is_projector_mesh(self, name):
        base, _dmg = strip_damage_prefix(name)
        folded = base.casefold()
        if folded in self._projector_fold:
            return True
        if folded.startswith("lightfproj"):
            return True
        if folded in ("projshad", "fakeshad"):
            return folded in self._projector_fold or folded == self.shadow_mesh_name.casefold()
        return False

    def is_shadow_projector(self, name):
        base, _ = strip_damage_prefix(name)
        return base.casefold() == self.shadow_mesh_name.casefold()

    def is_mesh_chunk_name(self, name):
        """True if this object should get a full mesh OBJECT chunk."""
        base, is_dmg = strip_damage_prefix(name)
        folded = base.casefold()
        if folded in self._chunk_fold:
            return True
        if self.allow_damage_prefix and is_dmg and folded in self._chunk_fold:
            return True
        # Forever: also accept s/d + known suspension stems (Arm/Hub/Guard/Cardan/Susp)
        if self.id == "TMF" and len(base) >= 2 and base[0] in "sdSD":
            stem = base[1:]
            for corner in ("FL", "FR", "RL", "RR"):
                for kind in (
                    "ArmBot",
                    "ArmDir",
                    "ArmTop",
                    "Hub",
                    "Guard",
                    "Cardan",
                    "Susp",
                ):
                    if stem == f"{corner}{kind}":
                        return True
        # TM2: accept s/d/g/w/p + known openable/wheel/susp/pilot stems
        if self.id == "TM2":
            if self.is_projector_mesh(name) or self.is_optional_light_helper(name):
                return True
            if folded == "wheelmin":
                return True
            # Exhaust1 … Exhaust8 flame helpers
            if folded.startswith("exhaust") and folded[7:].isdigit():
                return True
            # Pilot sheet — any p[Name] (pBody, …)
            if len(base) >= 2 and base[0] in "pP":
                return True
            if len(base) >= 2 and base[0] in "sdgwSDGW":
                stem = base[1:]
                if stem in _TM2_OPENABLE or stem in _TM2_SUSP:
                    return True
                for corner in _TM2_WHEEL_CORNERS:
                    for kind in _TM2_WHEEL_KINDS:
                        if stem == f"{corner}{kind}":
                            return True
                if base in _TM2_GLASS or folded in {g.casefold() for g in _TM2_GLASS}:
                    return True
                if stem in ("Body",):
                    return True
        return False

    def subject_to_strict_extents(self, name):
        from .tmf_validation import is_export_blacklisted

        if is_export_blacklisted(name):
            return False
        if self.is_projector_mesh(name) or self.is_optional_light_helper(name):
            return False
        base = strip_blender_suffix(name)
        folded = base.casefold()
        if folded == "wheelmin":
            return False
        if folded.startswith("exhaust") and folded[7:].isdigit():
            return False
        return True

    def expected_texture(self, object_name):
        base, _ = strip_damage_prefix(object_name)
        folded = base.casefold()
        if folded == "projshad":
            return "ProjShad.dds"
        if folded == "fakeshad":
            return "FakeShad.dds"
        if folded.startswith("lightfproj"):
            return "LightFProj.dds"
        if self.id == "TM2":
            if folded.startswith("exhaust") and folded[7:].isdigit():
                return None
            if base.startswith("w") or base.startswith("W"):
                return "WheelsDiffuse.dds"
            if base.startswith("p") or base.startswith("P"):
                return "Pilot.dds"
            if base.startswith("s") or base.startswith("S"):
                return "SkinDiffuse.dds"
            if base.startswith("d") or base.startswith("D"):
                return "DetailsDiffuse.dds"
            if base.startswith("g") or base.startswith("G"):
                return "DetailsDiffuse.dds"
            return None
        # Forever
        if base.startswith("s"):
            return "Diffuse.dds"
        if base.startswith("d") or base.startswith("g"):
            return "Details.dds"
        return None

    def mesh_export_names(self):
        return self.mesh_chunk_names | self.projector_names


def _make_tmf_profile():
    chunk = (
        frozenset(TMF_RECOMMENDED)
        | frozenset(TMF_OPTIONAL_CAR)
        | frozenset(TMF_SUSPENSION)
        | frozenset(TMF_PROJECTORS)
    )
    return GameProfile(
        id="TMF",
        label="TrackMania Forever",
        mesh_chunk_names=chunk,
        optional_light_names=frozenset(TMF_LIGHTS),
        projector_names=frozenset(TMF_PROJECTORS),
        name_guide_meshes=TMF_NAME_GUIDE,
        names_root_collection="TMF Mesh Names",
        maxbox_size=(3.0, 6.0, 2.5),
        abs_x=None,
        abs_y=(-3.0, 3.0),
        abs_z=(-0.3, 2.2),
        vertex_limits=dict(TMF_VERTEX_LIMITS),
        poly_target_items=(
            ("HIGH", "High Poly", "Up to 100,000 vertices (MainBodyHigh)"),
            ("LOW", "Low Poly", "Up to 3,600 vertices (MainBody)"),
        ),
        default_poly_target="HIGH",
        origin_mesh_names=frozenset({"sBody"}),
        shadow_mesh_name="ProjShad",
        allow_damage_prefix=False,
        check_abs_x=False,
    )


def _make_tm2_profile():
    chunk = frozenset(TM2_MESH_NAMES)
    return GameProfile(
        id="TM2",
        label="TrackMania 2",
        mesh_chunk_names=chunk,
        optional_light_names=frozenset(TM2_LIGHTS),
        projector_names=frozenset(TM2_PROJECTORS),
        name_guide_meshes=TM2_NAME_GUIDE,
        names_root_collection="TM2 Mesh Names",
        # Official box Min (-1.5,-3,-0.2) Max (1.5,3,2.5) → size 3×6×2.7
        maxbox_size=(3.0, 6.0, 2.7),
        abs_x=(-1.5, 1.5),
        abs_y=(-3.0, 3.0),
        abs_z=(-0.2, 2.5),
        vertex_limits=dict(TM2_VERTEX_LIMITS),
        poly_target_items=(
            ("VERY_HIGH", "Very High", "Up to 60,000 vertices (MainBodyVeryHigh)"),
            ("HIGH", "High Poly", "Up to 20,000 vertices (MainBodyHigh)"),
            ("LOW", "Low Poly", "Up to 4,250 vertices (MainBody)"),
        ),
        default_poly_target="HIGH",
        origin_mesh_names=frozenset({"dBody", "sBody"}),
        shadow_mesh_name="FakeShad",
        allow_damage_prefix=True,
        check_abs_x=True,
    )


PROFILES = {
    "TMF": _make_tmf_profile(),
    "TM2": _make_tm2_profile(),
}

DEFAULT_GAME_TARGET = "TMF"


def get_profile(game_target):
    return PROFILES.get(game_target, PROFILES[DEFAULT_GAME_TARGET])


def profile_from_context(context):
    settings = getattr(getattr(context, "scene", None), "tmf_settings", None)
    target = getattr(settings, "game_target", None) if settings else None
    return get_profile(target or DEFAULT_GAME_TARGET)


GAME_TARGET_ITEMS = (
    ("TMF", "TrackMania Forever", "Nations / United Forever car geometry"),
    ("TM2", "TrackMania 2", "ManiaPlanet / TrackMania 2 car skins"),
)
