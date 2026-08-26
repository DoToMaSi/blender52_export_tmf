# Export 3DS for TrackMania Forever

Blender 5.2 extension for exporting validated 3DS car geometry for **TrackMania Nations** and **TrackMania United**.

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

In Blender: **Edit → Preferences → Get Extensions → Install from Disk** → select `export_3ds_tmf-2.0.1.zip`.

### Development (symlink)

Link this folder into a local extensions repository for live reload during development.

## Build and validate

```powershell
blender --command extension validate
blender --command extension build
```

## Usage

1. Prepare the scene using TMF naming and scale rules (see below).
2. Select all car objects (meshes + light empties).
3. **File → Export → 3DS for TMF (.3ds)**.
4. Choose **Poly Target** (High: 100k verts, Low: 3.6k verts).
5. Import the `.3ds` in-game: **Help → Custom data → Car geometry**.

Export is **blocked** if validation fails. Errors appear in the Info header and System Console.

## Blender scene setup (Max equivalent)

| 3ds Max 7 setup | Blender equivalent |
|---|---|
| Units: Metric, Millimeters | Scene Properties → Units → Metric, Length: Millimeters |
| System unit: 1 unit = 1 mm | Unit Scale: **1.0** (1 BU = 1 mm) |
| Grid spacing 0.01 mm | Viewport overlays → scale grid as needed |
| Maxbox.3ds (6×3×2.5 mm) | Optional scale reference object |

Model at **0.1% of real size** (e.g. 2800 mm wheelbase → 2.8 mm in scene).

## Required object names

### Meshes (exact spelling)

| Name | Purpose | Texture |
|---|---|---|
| `sBody` | Paintable body | Diffuse.dds |
| `dBody` | Details (lights, interior, trim) | Details.dds |
| `gBody` | Glass / transparent parts | Details.dds |
| `dFLWheel`, `sFLWheel`, … | Tires (d) and rims (s) per corner | Details / Diffuse |

Wheel suffixes: `FL`, `FR`, `RL`, `RR`.

### Empty helpers (exact spelling)

`LightFL1`, `LightFR1`, `LightFL2`, `LightFR2`, `LightFL3`, `LightFR3`, `LightRL`, `LightRR`

Optional: suspension parts (`dxxHub`, `dxxArmTop`, …), `pPilHead`, `ProjShad`, `LightFProj`.

## Pre-export checklist

- Object names spelled exactly (case-sensitive)
- **Apply Scale** and **Apply Rotation** on all required meshes (Reset Xform equivalent)
- Pivot / origin at object center
- Per-object bounding box ≤ **3 mm (X) × 6 mm (Y) × 2.5 mm (Z)**
- Vertex count within poly target after triangulation
- Materials use Image Texture nodes referencing `Diffuse.dds` or `Details.dds`

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
| Export blocked | Read error messages — naming, scale, transforms, textures |
| Model invisible in game | Object spelling, vertex count, scale |
| Wrong paint/details | UV layout and Diffuse vs Details assignment |
| Vert count increased after export | Normal for UV splits; validate uses export vertex count |

## Project layout

```
blender_export_tmf/
├── blender_manifest.toml
├── __init__.py
├── export_operator.py      # Export operator + UI
├── exporter.py             # 3DS binary export logic
├── format_3ds.py           # 3DS chunk writer
├── material_utils.py       # Principled BSDF + texture helpers
└── tmf_validation.py       # Strict TMF pre-export validation
```

## License

GPL-2.0-or-later

## Authors

Glauco Bacchi, Campbell Barton, Bob Holcomb, Richard Lärkäng, Damien McGinnes, Mark Stijnman, Sergey Savkin, Douglas Tomacheski
