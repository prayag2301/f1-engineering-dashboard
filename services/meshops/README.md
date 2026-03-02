# Service: MeshOps

Python worker for mesh alignment, delta computation, and heatmap generation.

## Queue

Consumes from: `meshops` (Redis)

## Responsibilities

- Align mesh_v1 to mesh_v2
- Compute vertex distances and generate heatmap textures
- Produce comparison artifacts (GLB, preview renders)
- Register transforms and asset metadata
