# TrackMania Forever 3DS — Tutorial

Practical guide for authoring TMF car geometry in **Blender 5.2** with the **TrackMania Forever 3DS** extension.

Classic reference: [3D Model Conversion for TrackMania United](https://www.ugghost.com/tutorials/tmu-f/3d_model_conversion_for_tmu.htm) by trick@ugghost.com (2008). This tutorial adapts those rules to Blender and documents extension-specific tools.

---

## 1. Quick start

1. Unzip the release **bundle** (`export_3ds_tmf-<version>-bundle.zip`).
2. Open **`template/base-tmf-scene.blend`** in Blender 5.2+.
   - Metric units, tight viewport clips, wire **MaxBox** guide, and **TMF Mesh Names** collections are already set up.
3. Install the extension from **`script/export_3ds_tmf-<version>.zip`**:
   - **Edit → Preferences → Get Extensions → Install from Disk**
4. In the 3D Viewport sidebar, open the **TMF** tab.
5. Model your car, validate, export `.3ds`, then import in-game.

---

## 2. Scale and MaxBox

TMF cars use **0.1% of real-world size** ([Scale tutorial](https://www.ugghost.com/tutorials/tmu-f/Scale.htm)):

| Real world | Scene (mm) |
|---|---|
| 2800 mm wheelbase | 2.8 |
| 1500 mm track width | 1.5 |
| 660 mm wheel diameter | 0.66 (center ~0.33 above ground) |

The engine envelope is roughly **6 mm long (Y) × 3 mm wide (X) × 2.5 mm tall (Z)** — the same size as the classic Maxbox.3ds guide ([conversion guide](https://www.ugghost.com/tutorials/tmu-f/3d_model_conversion_for_tmu.htm)).

In Blender:

- **1 Blender unit ≈ 1 mm** (Unit Scale 1.0, Metric).
- Use the wire **MaxBox** object as a visual limit while modeling.
- **Strict** export mode blocks only when **body/wheel** vertices fall outside Y ∈ [-3, 3] and Z ∈ [-0.3, 2.2].

---

## 3. Mesh names

### Core body and wheels (classic United set)

| Name | Role |
|---|---|
| `sBody` | Paintable body (Diffuse.dds) |
| `dBody` | Details — lights, trim, interior (Details.dds) |
| `gBody` | Glass / transparent parts (Details.dds) |
| `dFLWheel`, `sFLWheel`, … | Tires (`d`) and rims (`s`) per corner |

Suffixes: **FL**, **FR**, **RL**, **RR**.

**TrackMania Forever** can import a **partial** car (even a single `sBody`). The full United set above is recommended for complete cars but is not a hard export blocker — missing parts show as **warnings** only.

### Suspension (optional)

From the [conversion guide](https://www.ugghost.com/tutorials/tmu-f/3d_model_conversion_for_tmu.htm):

- `dxxHub`, `dxxArmTop`, `dxxArmBot`, `dxxArmDir`, `dxxSusp`, `dxxGuard`, `dxxCardan` (xx = FL, FR, RL, RR as applicable)

Use the **TMF Mesh Names** collections (created by **Prepare TMF Scene**) as a spelling guide — drag meshes into the matching collection.

### Shadows, lights, and projectors

| Name | Role |
|---|---|
| `ProjShad` | Ground shadow projector mesh (uses ProjShad.dds in car zip) |
| `LightFProj` | Headlight beam projector |
| `LightFL1` … `LightFR3` | Front flare origins |
| `LightRL`, `LightRR` | Rear flare origins |

These are **meshes** in this extension (not Empties), matching working TMF export practice.

**Never exported:** `MaxBox` (scale guide only).

---

## 4. Pivots and transforms

See [Placing the Pivots](https://www.ugghost.com/tutorials/tmu-f/pivots.htm).

| Object | Pivot / transform notes |
|---|---|
| **Wheels** | Pivot at hub center; keep **location** at the hub (do not Apply Location — wheels must spin in-game) |
| **sBody** | Prefer origin at `(0, 0, 0)` for suspension anchoring (warning if not) |
| **Light helpers** | Tiny meshes aimed so local **+Y points toward the car center**; rear lights often use rot Z = π |
| **ProjShad** | Flat ground plane in Blender (Z-up); export applies TM Y-up orient automatically |

**Apply Scale** on body/wheel meshes when practical. **Rotation** may stay unapplied where needed for light aim.

After moving pivots in 3ds Max, an XForm reset was required. In Blender, use **Apply Scale** and keep hub **location** on wheels instead of applying all transforms.

---

## 5. UV mapping

From the [conversion guide](https://www.ugghost.com/tutorials/tmu-f/3d_model_conversion_for_tmu.htm):

| Meshes | Texture |
|---|---|
| `sBody`, `sXXWheel` | **Diffuse.dds** — no overlapping UVs on `sBody` |
| `dBody`, `gBody`, `dXXWheel` | **Details.dds** — glass/tires in empty areas of the details map |

The game binds textures from the **car zip**, not from the `.3ds` file alone.

---

## 6. Vertex counts

See [Counting Vertices](https://www.ugghost.com/tutorials/tmu-f/vertices.htm).

| Target | Limit | In-game solid |
|---|---|---|
| **High Poly** | ~100,000 vertices | MainBodyHigh.Solid.gbx |
| **Low Poly** | ~3,600 vertices | MainBody.Solid.gbx |

Vertex count may **increase after export** (UV splits). Use **Validate TMF Scene** or export with **Verbose Log** to see the count the exporter will write.

Poly target is an **advisory warning** — it does not block Strict mode.

---

## 7. Extension tools (TMF N-panel)

### Prepare TMF Scene

- Sets metric units and viewport clip range for tiny cars.
- Optional **Create MaxBox** — wire scale guide.
- Optional **Create Name Collections** — empty Outliner folders for every canonical TMF mesh name.

### Validate TMF Scene

Runs the same checks as export **without writing a file**:

- **Strict (errors):** body/wheel verts outside MaxBox Y/Z only.
- **Warnings:** missing recommended parts, loose verts, unapplied scale, poly budget, missing ProjShad, etc.

### Helpers

Spawn common meshes (does not replace your body work):

- **ProjShad** — flat shadow plane
- **LightFProj** — headlight projector
- **Light FL/FR/RL/RR** — tiny flare-origin meshes

### Import 3DS for TMF

- Round-trip files from this extension reliably.
- **Create MaxBox** / **Create Name Collections** available on import.
- **Prepare Scene for TMF** — only for clean, TMF-only `.blend` files.
- `ProjShad` imports flat with hub rotation cleared to 0.

### Export 3DS for TMF

**File → Export → 3DS for TMF (.3ds)**

| Option | Purpose |
|---|---|
| **Strict** | Block export only on MaxBox Y/Z failures (body/wheels) |
| **Poly Target** | High / Low — advisory vertex budget |
| **Selection Only** | Export only selected allowlisted meshes |
| **Verbose Log** | Writes `.tmf-export.log` next to the `.3ds` |

Warnings always appear whether Strict is on or off.

---

## 8. Export workflow

1. Finish modeling at TMF scale inside MaxBox.
2. Name meshes exactly (use name collections as a guide).
3. UV-map to Diffuse / Details as above.
4. Add optional helpers (`ProjShad`, lights) if needed.
5. **Validate TMF Scene** — fix MaxBox errors; review warnings.
6. **File → Export → 3DS for TMF (.3ds)** with **Strict** on for final exports.
7. In TrackMania: **Help → Custom data → Car geometry** — browse to your `.3ds` ([model example notes](https://www.ugghost.com/tutorials/tmu-f/model3d.htm)).

The in-game importer may **fail silently** on bad geometry — always test in-game after export.

---

## 9. Car.zip checklist

Required for in-game use ([conversion guide](https://www.ugghost.com/tutorials/tmu-f/3d_model_conversion_for_tmu.htm)):

- `Icon.dds`
- `Diffuse.dds`
- `Details.dds`
- `MainBodyHigh.Solid.gbx` and/or `MainBody.Solid.gbx`

Optional:

- `ProjShad.dds`, `Illum.dds`, dirty variants, horn/engine sounds, `Credits.txt`

The `.3ds` from this extension is imported in-game to produce the `.Solid.gbx` files.

---

## 10. Troubleshooting

| Problem | What to check |
|---|---|
| Export blocked | MaxBox Y/Z on **body/wheels** — read N-panel / console errors |
| Warnings only | Missing wheels/glass, loose verts, scale — export still allowed |
| Model invisible in game | Object naming, vertex count, scale, silent `.3ds` import failure |
| Wrong paint / details | UV layout; Diffuse vs Details assignment |
| Wheels float or don’t spin | Hub **location** must stay at wheel center |
| Lights wrong way | Light helper local +Y toward car center; rear often rot Z = π |
| ProjShad wrong in game | Need **ProjShad** mesh in `.3ds` + `ProjShad.dds` in zip |
| Vert count jumped | Normal after UV splits — validate uses export vertex count |

General checks from the [conversion guide](https://www.ugghost.com/tutorials/tmu-f/3d_model_conversion_for_tmu.htm): spelling, vertex count, scale, pivots/transforms, zip file names.

---

## Further reading

- [3D Model Conversion for TMU](https://www.ugghost.com/tutorials/tmu-f/3d_model_conversion_for_tmu.htm)
- [Example 3D model](https://www.ugghost.com/tutorials/tmu-f/model3d.htm)
- [Placing the Pivots](https://www.ugghost.com/tutorials/tmu-f/pivots.htm)
- [Counting Vertices](https://www.ugghost.com/tutorials/tmu-f/vertices.htm)
- [Scale](https://www.ugghost.com/tutorials/tmu-f/Scale.htm)
