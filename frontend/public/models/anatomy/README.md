# Production anatomy GLB replacement

No third-party anatomy asset is bundled. The default surfaces are original procedural reference
placeholders (including the sex-differentiated body silhouette in `AnatomyModel.jsx`, built from
a lathed torso profile per `src/data/anatomyMap.js` `BODY_PROFILES`), not patient segmentation and
not anatomical ground truth, and not a licensed scan.

## Single shared model

Put `anatomy.glb` here and set frontend `.env.local`:

```
VITE_ANATOMY_MODEL_URL=/models/anatomy/anatomy.glb
```

## Sex-specific models (recommended)

To show a distinct male and female mesh, put each under its own folder and point the env vars at
them instead:

```
frontend/public/models/anatomy/male/body.glb
frontend/public/models/anatomy/female/body.glb
```

```
VITE_ANATOMY_MODEL_URL_MALE=/models/anatomy/male/body.glb
VITE_ANATOMY_MODEL_URL_FEMALE=/models/anatomy/female/body.glb
```

`VITE_ANATOMY_MODEL_URL` (no sex suffix) is used as the fallback when a patient's `sex` field is
missing or not `male`/`female` -- the app never guesses a sex-specific asset for an unsupported
value; it shows a "Sex-specific anatomy unavailable" notice and falls back to the neutral
procedural body instead.

Build again after setting either. The `useGLTF` loader falls back to the procedural model per
organ on load failure, an invalid mesh, or a missing mesh name -- a GLB does not need to cover
every organ; anything it omits stays procedural. The GLB may contain indexed, non-degenerate
meshes named from this set (all optional, mix and match):
brain, rightLung, leftLung, heart, liver, stomach, rightKidney, leftKidney, vascular, spine,
pancreas, spleen, bladder, smallIntestine, largeIntestine.

Bake mesh rotation into vertex geometry before export; the reference coordinate convention is +Y
superior, +Z anterior, +X patient left. Each mesh is normalized independently into the dimensions
and placement in `src/data/anatomyMap.js`. This intentionally does not preserve patient
dimensions: patient-specific segmentation requires a different adapter, consistent image affine
transforms, and validated measurement handling. Both 3D and reference intersections consume the
same normalized geometry.

The whole-body skin shell falls back to the procedural lathe body only when `extras.glb`'s
`skinBody` mesh isn't present -- see the real-data section below for the shipped real skin/
skeleton/vascular GLB.

Include the source URL, author, license text, required attribution and redistribution permissions
with any added asset. Do not put patient scans or unlicensed meshes in this folder.

## Real anatomy build (BodyParts3D)

`anatomy.glb` and `extras.glb` in this folder are committed to the repo (real BodyParts3D 4.3
mesh data, DBCLS Anatomography, CC BY-SA 2.1 Japan, merged per-organ with `trimesh`) so the app
serves real anatomy data out of the box. `build_real_anatomy.py` (repo root) regenerates them:

```
python build_real_anatomy.py --fetch --build --extras-fetch --extras-build
```

This requires a local clone (with Git LFS content pulled) of a BodyParts3D mesh source repo --
see the script's `REPO_URL`/`REPO_DIR` and `bp3d_subset.py` for the exact fetch mechanism.

`anatomy.glb` covers the 10 organs listed above. `extras.glb` additionally carries the full
skeleton (`skeletonFull`, ~365 merged bone meshes), full arterial/venous tree (`vascularFull`,
~1466 merged vessel meshes), and the whole-body skin surface (`skinBody`, single mesh,
FMA55665 "Skin", ~203k faces), each preserving BodyParts3D's original relative positions (not
individually normalized, so the whole-body shape survives) -- see `AnatomyExtrasAssets.jsx`.
`.env.local` already points at both:

```
VITE_ANATOMY_MODEL_URL=/models/anatomy/anatomy.glb
VITE_ANATOMY_EXTRAS_URL=/models/anatomy/extras.glb
```

BodyParts3D ships in millimetres on a Z-up axis; `extrasTransform` in `src/data/anatomyMap.js`
(scale/position/rotation) converts the merged extras mesh once into this app's Y-up model-unit
space. The 10 real organs' `p`/`s` in `anatomyMap.js` are *derived* from this same transform
(each organ's raw, unnormalized bounding box run through the identical rotation+scale), so the
organ meshes, skin, and skeleton all share one consistent, real-world-scaled coordinate system --
see the comment above `organs` in `anatomyMap.js` for the exact math. All three real-data layers
(`RealBodyShell`/`Skeleton`/`VascularFull` in `AnatomyModel.jsx`) are independently optional and
fall back to their procedural equivalent if their mesh isn't present in the loaded GLB.

Since BodyParts3D ships one reference specimen (no separate male/female full-body sets),
`SEX_BODY_SCALE` in `anatomyMap.js` applies a uniform anthropometric size scale (average adult
height ratio) to that one real scan when a patient's sex is known, pivoted from the feet. This is
explicitly not a distinct female segmentation -- never present it as one in UI copy or docs.

**Required attribution (CC BY-SA 2.1 Japan) -- do not remove:**

> BodyParts3D, © Database Center for Life Science, CC BY-SA 2.1 Japan

This is surfaced on screen automatically (`ANATOMY_ATTRIBUTION` in `anatomyMap.js`, rendered in
`AnatomyWorkspace.jsx`) whenever a real GLB is loaded.
