# Deployment

The replacement viewer is developed on `codex/github-pages-release`. GitHub Pages serves the static Next.js viewer, immutable reviewed release snapshots, GLBs, comparison, and PNG downloads. Docker Compose runs the local authoring workflow: PostgreSQL, Redis, FastAPI, review, collection, and the native Blender worker.

The database and immutable release assets live in named volumes. Still rendering uses CPU on macOS; the browser viewer uses the Mac’s graphics hardware. Publication requires the maintainer’s visual and evidence review.

The current `demo/static` deployment remains live until the replacement passes CI and both car baselines complete visual review. The first pinned approved snapshot enables the new workflow to replace the site. See [the Pages deployment and rollback guide](docs/github-pages.md) and [local setup](README.md#run-locally).
