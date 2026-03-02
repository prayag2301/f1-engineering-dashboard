# 3D Reconstruction Playbook

## Overview

The reconstruction pipeline converts multi-view images of F1 car components into 3D models for comparison analysis.

## Pipeline Stages

### 1. Image Collection
- Minimum 20 images per component from different angles
- Prefer images from pit lane, garage, and on-track (telephoto)
- Include overhead shots when available

### 2. Trainability Assessment
Before running reconstruction, the system scores the image set:

| Factor | Weight | What it measures |
|--------|--------|-----------------|
| Angle diversity | 0.3 | Coverage of viewing angles |
| Blur score | 0.2 | Sharpness of images |
| Occlusion | 0.2 | How much of the component is visible |
| Lighting consistency | 0.15 | Uniform lighting across images |
| Resolution | 0.15 | Minimum effective resolution |

**Minimum trainability score: 0.3** (below this, the system warns and falls back to 2D evidence).

### 3. Pose Estimation (COLMAP)
- Run structure-from-motion to estimate camera poses
- Validate reconstruction quality (reprojection error < 1.0 px)

### 4. Reconstruction
Preferred methods (in order):
1. **Gaussian Splatting** (splatfacto) — Best quality for car surfaces
2. **Nerfacto** — Good general quality, slower
3. **Instant-NGP** — Fastest, lower quality

### 5. Export
- `.ply` point cloud for comparison
- Preview renders (8 canonical views)
- GLB mesh for web viewer

## When Splats Fail

Common failure modes and fixes:

| Problem | Symptom | Fix |
|---------|---------|-----|
| Too few images | Holes in reconstruction | Collect more images from missing angles |
| Motion blur | Floaty/noisy geometry | Filter blurry images before training |
| Reflections | Ghost geometry | Mask out highly reflective surfaces |
| Occlusion | Missing surfaces | Use inpainting or add synthetic views |
| Scale drift | Wrong absolute size | Add known-dimension reference object |

## Comparison (MeshOps)

After reconstructing the same component from two weekends:

1. **Alignment**: ICP registration to align meshes
2. **Delta computation**: Per-vertex distance calculation
3. **Heatmap**: Color-coded distance map on the mesh surface
4. **Changed regions**: Automatically identify areas with significant delta

The web viewer shows:
- Side-by-side comparison
- Slider overlay
- Heatmap toggle
- "What changed" auto-summary from the annotation service
