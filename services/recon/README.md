# Service: Recon

Python GPU worker for 3D reconstruction (NeRF/Gaussian Splat).

## Queue

Consumes from: `recon` (Redis)

## Responsibilities

- Accept image sets with poses (or run COLMAP)
- Train reconstruction model (Nerfstudio splat preferred)
- Export .ply + preview renders
- Report trainability score (angle diversity, blur, occlusion)
