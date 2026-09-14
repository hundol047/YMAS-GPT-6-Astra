# Production anatomy GLB replacement

No third-party anatomy asset is bundled. The default surfaces are original procedural reference placeholders, not patient segmentation and not anatomical ground truth.

To supply a licensed asset, put `anatomy.glb` here and set frontend `.env.local`:

```
VITE_ANATOMY_MODEL_URL=/models/anatomy/anatomy.glb
```

Build again. The optional useGLTF loader falls back to the procedural model on load failure or invalid/missing meshes. The GLB must contain indexed, non-degenerate meshes named exactly:
brain, rightLung, leftLung, heart, liver, stomach, rightKidney, leftKidney, vascular, spine.

Bake mesh rotation into vertex geometry before export; the reference coordinate convention is +Y superior, +Z anterior, +X patient left. Each mesh is normalized independently into the dimensions and placement in src/data/anatomyMap.js. This intentionally does not preserve patient dimensions: patient-specific segmentation requires a different adapter, consistent image affine transforms, and validated measurement handling. Both 3D and reference intersections consume the same normalized geometry.

Include the source URL, author, license text, required attribution and redistribution permissions with any added asset. Do not put patient scans or unlicensed meshes in this folder.
