# TrackMania Forever 3DS

Blender **5.2** extension for authoring **TrackMania Nations / United Forever** car geometry: import/export `.3ds`, scene setup, validation, and helper spawners.

Based on the original Blender 2.81 exporter by Glauco Bacchi, Campbell Barton, Bob Holcomb, Richard Lärkäng, Damien McGinnes, Mark Stijnman, and Sergey Savkin. Updated for Blender 5.2 by Douglas Tomacheski.

TMF workflow reference: car model conversion tutorial by trick@ugghost.com (2008).

## Requirements

- Blender **5.2.0** or newer
- Models modeled at **0.1% of real-world scale** (millimeter scene units)

## Installation

### From GitHub Release — full bundle (recommended for new users)

1. Open [Releases](https://github.com/DoToMaSi/blender52_export_tmf/releases) and download **`export_3ds_tmf-<version>-bundle.zip`**.
2. Unzip. Layout:

```
export_3ds_tmf-<version>-bundle.zip
├── template/
│   └── base-tmf-scene.blend    # Preconfigured TMF workspace
├── script/
│   └── export_3ds_tmf-<version>.zip
├── README.MD
└── TUTORIAL.MD                 # Step-by-step authoring guide
```

3. Open **`template/base-tmf-scene.blend`** in Blender 5.2+ (metric units, MaxBox, name collections).
4. Install the extension: **Edit → Preferences → Get Extensions → Install from Disk** → select **`script/export_3ds_tmf-<version>.zip`**.

See **`TUTORIAL.MD`** in the bundle (source: [`docs/TUTORIAL.md`](docs/TUTORIAL.md)) for scale, naming, pivots, and export workflow.

### From GitHub Release — extension only

If you already have a TMF scene, download **`export_3ds_tmf-<version>.zip`** (no template or tutorial) and install from disk as above.

### Build locally

```powershell
# Windows — builds extension zip + bundle at repo root
.\scripts\package-release.ps1

# Linux / macOS (Blender 5.2+ on PATH)
./scripts/package-release.sh
```

Wrappers `scripts/ci-build.ps1` / `scripts/ci-build.sh` call the same packaging scripts.

Then install `export_3ds_tmf-<version>.zip` from the repo root, or use the full `-bundle.zip` for distribution.

### Development (symlink)

Link this folder into a local extensions repository for live reload during development.

## CI and releases

| Workflow | Trigger | Result |
|---|---|---|
| **CI** | Push / PR to `master` | Builds and verifies both zips; uploads them as **Actions artifacts** (PRs stop here) |
| **CI → release** | Push to `master` after CI passes | Tags `v{version}` if needed, then **publishes a GitHub Release** with both zips attached |
| **Release (manual)** | Actions → Run workflow | Re-publish assets for an existing tag (recovery only) |

**Cutting a release**

1. Bump `version` in `blender_manifest.toml`.
2. Commit and push to `master` (include `docs/TUTORIAL.md` updates if any).
3. CI builds the zips, tags `v{version}` if it does not exist yet, and publishes the GitHub Release with both assets attached.

**Do not** use the GitHub **“Create a new release”** page to upload zips manually — that bypasses CI. If a draft release was started by hand, delete it and re-run the **CI** workflow on `master` instead.

**Where to download builds**

| Location | What |
|---|---|
| **Releases** tab | Official downloads for end users (`export_3ds_tmf-*.zip` + `-bundle.zip`) |
| **Actions → CI run → Artifacts** | Same zips from the build job (useful for PR verification) |

To re-release the same version: delete the GitHub Release (and tag if needed), then re-run CI or use **Release (manual)** with the tag name.

Build artifacts (`*.zip`, `build/`) are not stored in git — only produced by CI or `scripts/package-release.*`.

## Build and validate (manual)

Extension build uses a **staged copy** of runtime files only (no template, docs, or scripts in the install zip):

```powershell
.\scripts\package-release.ps1
```

Or stage manually and run from `build/extension/`:

```powershell
blender --command extension validate
blender --command extension build
```

## Usage

### N-panel (View3D → Sidebar → **TMF**)

| Tool | Action |
|---|---|
| **Prepare TMF Scene** | Metric units, tight view clips, optional **MaxBox** and **Name Collections** |
| **Validate TMF Scene** | Same Strict checks as export (MaxBox + per-mesh 65,536 verts), without writing a file |
| **Helpers** | Spawn `ProjShad`, `LightFProj`, `LightFL1/FR1/RL/RR` as meshes |
| **Import / Export** | Shortcuts to the File menu operators |

### Import

1. **File → Import → 3DS for TMF (.3ds)** (or N-panel button).
2. **Create MaxBox** / **Create Name Collections** (import defaults on): scale guide and/or empty Outliner folders under **TMF Mesh Names** for every canonical part name (3ds Max list).
3. **Prepare Scene for TMF** (default off): sets metric units and view clips for a clean TMF-only file — leave off when other meshes use different units.
4. `ProjShad` imports as a flat ground plane at the hub origin with **rotation cleared to 0** (export TM +90° X and/or authored +90° X on the object are absorbed into the mesh).
5. Prefer files produced by this extension — stock Max/Nadeo cars may misplace pivots.

### Export

1. Prepare the scene (naming, scale, helpers).
2. **File → Export → 3DS for TMF (.3ds)**.
3. Choose **Poly Target** (High: 100k verts, Low: 3.6k verts) — advisory only.
4. Leave **Strict** on to block exports when **body/wheel** verts fall outside MaxBox (Y ∈ [-3, 3], Z ∈ [-0.3, 2.2]) **or** any single mesh exceeds **65,536** vertices after UV splits (3DS uint16 limit). There is no hard total vertex budget for the whole car. Forever accepts partial cars. Warnings cover **unapplied scale**, **bad locations** (e.g. sBody origin), and **ProjShad rotation** (local Y should point up) — not missing mesh names. `ProjShad` / light helpers are excluded from MaxBox checks.
5. Import the `.3ds` in-game: **Help → Custom data → Car geometry**.

Strict blocks on MaxBox failures and per-mesh vertex overflow. Warnings always appear (Info header / console / N-panel) whether Strict is on or off.

## Blender scene setup (Max equivalent)

| 3ds Max 7 setup | Blender equivalent |
|---|---|
| Units: Metric, Millimeters | **Prepare TMF Scene** or Scene Properties → Units → Metric |
| System unit: 1 unit = 1 mm | Unit Scale **1.0**; scene numbers are already mm (bumper ≈ `1.5`) |
| Maxbox.3ds (6×3×2.5 mm) | Wire **MaxBox** guide (never exported) |

Model at **0.1% of real size** (e.g. 2800 mm wheelbase → 2.8 mm in scene).

## Recommended object names

### Meshes (classic United set — Forever can use a subset)

| Name | Purpose |
|---|---|
| `sBody` | Paintable body |
| `dBody` | Details (lights, interior, trim) |
| `gBody` | Glass / transparent parts |
| `dFLWheel`, `sFLWheel`, … | Tires (d) and rims (s) per corner |
| `sPilHead`, `dPilHead` | Driver head (bobbing physics); Diffuse / Details |

Wheel suffixes: `FL`, `FR`, `RL`, `RR`. Keep **hub origins** on wheels (do not Apply Location).

### Exported helpers (meshes)

| Name | Role |
|---|---|
| `ProjShad` | Ground fake-shadow plane — helper spawns with **local Y up** (+90° X); export auto-orients for TM |
| `LightFProj` | Headlight projector |
| `LightFL1` / `LightFR1` / `LightRL` / `LightRR` | Flare origins (tiny meshes; rear often rot Z = π) |

**Never exported:** `MaxBox` (scale guide only).

## Pre-export checklist

- Object names spelled correctly for parts you want exported (allowlist)
- Forever can ship with a **partial** mesh set (even only `sBody`); classic United names are recommended
- Keep body/wheel world verts inside MaxBox: **Y ∈ [-3, 3]**, **Z ∈ [-0.3, 2.2]** (Strict)
- Keep **each mesh** at or below **65,536** export vertices after UV splits (Strict)
- Apply Scale when practical; rotation may stay unapplied for light aim
- **ProjShad**: local **Y should point up** (Helpers spawn this correctly)
- Prefer `sBody` at `(0, 0, 0)` for suspension anchoring (warning only)
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
| Export / validate blocked | MaxBox Y/Z on body/wheels, or any mesh over 65,536 verts — ProjShad excluded from MaxBox |
| Soft warnings | Unapplied scale, sBody origin, ProjShad Y-up rotation / footprint — not missing meshes |
| Model invisible in game | Object spelling, vertex count, scale |
| Wrong paint/details | UV layout and Diffuse vs Details assignment |
| Import hubs wrong | Round-trip is tuned for this exporter’s files |
| Vert count increased after export | Normal for UV splits; validate uses export vertex count |

## Project layout

```
blender_export_tmf/
├── .github/workflows/         # CI + release pipelines
├── docs/
│   └── TUTORIAL.md            # Copied to TUTORIAL.MD in release bundle
├── template/
│   └── base-tmf-scene.blend   # Starter scene (in release bundle)
├── scripts/
│   ├── package-release.ps1    # Local build + bundle (Windows)
│   ├── package-release.sh     # Local build + bundle (Linux/macOS)
│   ├── ci-build.ps1           # Wrapper → package-release.ps1
│   └── ci-build.sh            # Wrapper → package-release.sh
├── blender_manifest.toml
├── __init__.py
├── export_operator.py         # File > Export
├── import_operator.py         # File > Import
├── exporter.py                # 3DS binary export
├── importer.py                # 3DS import + hub un-bake
├── format_3ds.py              # Chunk read/write
├── material_utils.py          # Principled BSDF + texture helpers
├── tmf_validation.py          # Strict validation
├── tmf_scene.py               # Prepare scene + validate operator
├── tmf_helpers.py             # ProjShad / light spawners
└── ui_panel.py                # View3D N-panel (TMF tab)
```

## License

GPL-2.0-or-later

## Authors

Glauco Bacchi, Campbell Barton, Bob Holcomb, Richard Lärkäng, Damien McGinnes, Mark Stijnman, Sergey Savkin, Douglas Tomacheski
