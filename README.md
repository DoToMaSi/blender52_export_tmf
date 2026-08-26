# TrackMania Forever 3DS

Blender **5.2** extension for authoring **TrackMania Nations / United Forever** car geometry: import/export `.3ds`, scene setup, validation, and helper spawners.

Based on the original Blender 2.81 exporter by Glauco Bacchi, Campbell Barton, Bob Holcomb, Richard Lärkäng, Damien McGinnes, Mark Stijnman, and Sergey Savkin. Updated for Blender 5.2 by Douglas Tomacheski.

TMF workflow reference: car model conversion tutorial by trick@ugghost.com (2008).

## Requirements

- Blender **5.2.0** or newer
- Models modeled at **0.1% of real-world scale** (millimeter scene units)

## Installation

### From built package

```powershell
cd D:\WORKSPACE\PERSONAL\blender_export_tmf
blender --command extension build
```

In Blender: **Edit → Preferences → Get Extensions → Install from Disk** → select `export_3ds_tmf-2.3.0.zip`.

### Development (symlink)

Link this folder into a local extensions repository for live reload during development.

## Build and validate

```powershell
blender --command extension validate
blender --command extension build
```

## Usage

### N-panel (View3D → Sidebar → **TMF**)

| Tool | Action |
|---|---|
| **Prepare TMF Scene** | Metric units, tight view clips, wire **MaxBox** guide (3×6×2.5) |
| **Validate TMF Scene** | Same Strict checks as export, without writing a file |
| **Helpers** | Spawn `ProjShad`, `LightFProj`, `LightFL1/FR1/RL/RR` as meshes |
| **Import / Export** | Shortcuts to the File menu operators |

### Import

1. **File → Import → 3DS for TMF (.3ds)** (or N-panel button).
2. Prefer files produced by this extension — import reverses our export rules (world-baked verts → hub `location` + local verts).
3. Stock Max/Nadeo cars may misplace pivots; that is a later stretch goal.

### Export

1. Prepare the scene (naming, scale, helpers).
2. **File → Export → 3DS for TMF (.3ds)**.
3. Choose **Poly Target** (High: 100k verts, Low: 3.6k verts).
4. Leave **Strict** enabled for final car exports. Disable only to test incomplete WIP scenes.
5. Import the `.3ds` in-game: **Help → Custom data → Car geometry**.

Export is **blocked** when **Strict** is on and validation fails. Errors appear in the Info header, System Console, and N-panel.

## Blender scene setup (Max equivalent)

| 3ds Max 7 setup | Blender equivalent |
|---|---|
| Units: Metric, Millimeters | **Prepare TMF Scene** or Scene Properties → Units → Metric |
| System unit: 1 unit = 1 mm | Unit Scale **1.0**; scene numbers are already mm (bumper ≈ `1.5`) |
| Maxbox.3ds (6×3×2.5 mm) | Wire **MaxBox** guide (never exported) |

Model at **0.1% of real size** (e.g. 2800 mm wheelbase → 2.8 mm in scene).

## Required object names

### Meshes (exact spelling)

| Name | Purpose |
|---|---|
| `sBody` | Paintable body |
| `dBody` | Details (lights, interior, trim) |
| `gBody` | Glass / transparent parts |
| `dFLWheel`, `sFLWheel`, … | Tires (d) and rims (s) per corner |

Wheel suffixes: `FL`, `FR`, `RL`, `RR`. Keep **hub origins** on wheels (do not Apply Location).

### Exported helpers (meshes)

| Name | Role |
|---|---|
| `ProjShad` | Ground fake-shadow plane (flat Z-up OK; export auto +90° X if needed) |
| `LightFProj` | Headlight projector |
| `LightFL1` / `LightFR1` / `LightRL` / `LightRR` | Flare origins (tiny meshes; rear often rot Z = π) |

**Never exported:** `MaxBox` (scale guide only).

## Pre-export checklist

- Object names spelled exactly; only allowlisted parts are exported
- **sBody** origin / location at `(0, 0, 0)`
- **Apply Scale** on required meshes (rotation may stay unapplied for light aim)
- No loose vertices
- Absolute extents (mm): **Y ∈ [-3, 3]**, **Z ∈ [-0.3, 2.2]**
- Vertex count within poly target after triangulation
- Car zip still needs `Diffuse.dds` / `Details.dds` / `ProjShad.dds` / `Icon.dds`

## UV mapping rules

- `sBody`, `sXXWheel` → Diffuse.dds (no overlapping UVs on sBody)
- `dBody`, `gBody`, `dXXWheel` → Details.dds
- Map glass and tires to empty areas of the details texture

## Car.zip contents

Required for in-game use:

- `Icon.dds`
- `Diffuse.dds`
- `Details.dds`
- `MainBodyHigh.Solid.gbx` and/or `MainBody.Solid.gbx`

Optional: horn/engine sounds, `ProjShad.dds`, dirty variants, `Credits.txt`.

## Troubleshooting

| Problem | Check |
|---|---|
| Export / validate blocked | Read N-panel or console errors — naming, scale, extents |
| Model invisible in game | Object spelling, vertex count, scale |
| Wrong paint/details | UV layout and Diffuse vs Details assignment |
| Import hubs wrong | Round-trip is tuned for this exporter’s files |
| Vert count increased after export | Normal for UV splits; validate uses export vertex count |

## Project layout

```
blender_export_tmf/
├── blender_manifest.toml
├── __init__.py
├── export_operator.py      # File > Export
├── import_operator.py      # File > Import
├── exporter.py             # 3DS binary export
├── importer.py             # 3DS import + hub un-bake
├── format_3ds.py           # Chunk read/write
├── material_utils.py       # Principled BSDF + texture helpers
├── tmf_validation.py       # Strict validation
├── tmf_scene.py            # Prepare scene + validate operator
├── tmf_helpers.py          # ProjShad / light spawners
└── ui_panel.py             # View3D N-panel (TMF tab)
```

## License

GPL-2.0-or-later

## Authors

Glauco Bacchi, Campbell Barton, Bob Holcomb, Richard Lärkäng, Damien McGinnes, Mark Stijnman, Sergey Savkin, Douglas Tomacheski
