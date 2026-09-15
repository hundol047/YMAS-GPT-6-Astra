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

The whole-body skin/skeleton shell (as opposed to the individual organ meshes above) is not yet a
GLB extension point -- it is always the procedural lathe body. Wiring a full-body GLB skin in is a
follow-up if a licensed asset is sourced.

Include the source URL, author, license text, required attribution and redistribution permissions
with any added asset. Do not put patient scans or unlicensed meshes in this folder.
